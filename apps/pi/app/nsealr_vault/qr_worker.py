"""Finite experimental RGB owner. No fixture oracle, key or native signer input.

CLI descriptors: image0, result1, diagnostic2, commands3, ready4, status5.
The caller retains this process until actual worker status and IO are settled.
Unknown cleanup deliberately retains the live owner; no watchdog kills it.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import time

RAW = 172800
CHUNK = 4096
CAP = 512
WALL_NS = 8_000_000_000
CLEANUP_NS = 4_000_000_000
LIMITS = {"AS": (resource.RLIMIT_AS, (268435456, 268435456)),
          "CPU": (resource.RLIMIT_CPU, (1, 2)), "CORE": (resource.RLIMIT_CORE, (0, 0))}


def sha(path):
    with open(path, "rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def live_fds():
    # listdir's temporary directory descriptor is already closed on return.
    answer = set()
    for name in os.listdir("/proc/self/fd"):
        try:
            os.fstat(int(name))
            answer.add(int(name))
        except OSError:
            pass
    return answer


class Owner:
    def __init__(self, executable, digest):
        self.executable, self.digest = str(Path(executable).resolve(strict=True)), digest
        self.selector = selectors.DefaultSelector()
        self.fds = set()
        self.pid = self.pidfd = self.wait = None
        self.stdin_fd = None
        self.eof = set()
        self.streams = {"stdout": bytearray(), "stderr": bytearray()}
        self.totals = {"stdout": 0, "stderr": 0}
        self.image = bytearray()
        self.input_count = 0
        self.input_eof = False
        self.sequence = ""
        self.phase = self.ack = self.killed = self.cancel = False
        self.lost = False
        self.g = self.sent = 0
        self.begin = self.invalidated = self.cleanup = self.settled = self.admission = None
        self.reason = None
        self.status_bytes = 0
        self.expected_fds = {}

    def watch(self, fd, event, name):
        os.set_blocking(fd, False)
        self.selector.register(fd, event, name)

    def unwatch(self, fd):
        try:
            self.selector.unregister(fd)
        except (KeyError, ValueError):
            pass

    def close(self, fd):
        if fd in self.fds:
            self.unwatch(fd)
            os.close(fd)
            self.fds.remove(fd)

    def invalidate(self, reason):
        if self.reason is None:
            self.reason = reason
            self.invalidated = time.monotonic_ns()
            self.cleanup = self.invalidated + CLEANUP_NS
        self.unwatch(0)
        self.unwatch(3)  # No further control allocation/reads after irreversible invalidation.
        if self.stdin_fd is not None:
            self.close(self.stdin_fd)

    def emit(self, value):
        wire = (json.dumps(value, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")
        if len(wire) + self.status_bytes > 4096:
            raise RuntimeError("status capacity")
        # At most4096 total; the active parent drains this private channel.
        view = memoryview(wire)
        while view:
            view = view[os.write(5, view):]
        self.status_bytes += len(wire)

    def commands(self):
        try:
            block = os.read(3, max(1, 4 - len(self.sequence)))
        except BlockingIOError:
            return
        if not block:
            self.unwatch(3)
            if self.sequence not in ("X", "Q", "PX", "PGX"):
                self.invalidate("control_lost")
            return
        for byte in block:
            candidate = self.sequence + chr(byte)
            if candidate not in ("P", "PG", "PX", "PGX", "X", "Q") or (byte == 71 and not self.phase):
                self.invalidate("control_malformed")
                return
            self.sequence = candidate
            if byte == 80:
                self.begin = time.monotonic_ns()
            elif byte == 71:
                self.ack = True
                if self.reason is None and self.stdin_fd in self.fds:
                    self.watch(self.stdin_fd, selectors.EVENT_WRITE, "worker_input")
            elif byte == 88:
                self.cancel = True
                self.invalidate("cancelled")
            else:
                self.invalidate("unused")

    def ingress(self):
        if self.reason is not None:
            return
        try:
            block = os.read(0, min(CHUNK, RAW - len(self.image) + 1))
        except BlockingIOError:
            return
        self.input_count += len(block)
        if not self.sequence.startswith("P") or self.input_count > RAW:
            self.invalidate("input_invalid")
            return
        if not block:
            self.input_eof = True
            self.unwatch(0)
            if len(self.image) != RAW:
                self.invalidate("input_invalid")
            return
        self.image.extend(block)

    def spawn_worker(self):
        # No descriptor inherited from Node (control/ready/status included) may
        # leak to W; only three explicit dup2 actions become inheritable there.
        for fd in live_fds():
            if fd > 2:
                os.set_inheritable(fd, False)
        pipes = []
        for _ in range(3):
            pair = os.pipe2(os.O_CLOEXEC)
            self.fds.update(pair)  # Partial setup is owned immediately.
            pipes.append(pair)
        child_in, self.stdin_fd = pipes[0]
        outfd, child_out = pipes[1]
        errfd, child_err = pipes[2]
        for fd, child_fd in enumerate((child_in, child_out, child_err)):
            stat = os.fstat(child_fd)
            self.expected_fds[str(fd)] = {"fd": fd, "target": os.readlink(f"/proc/self/fd/{child_fd}"),
                                          "dev": str(stat.st_dev), "ino": str(stat.st_ino)}
        actions = [(os.POSIX_SPAWN_DUP2, child_in, 0), (os.POSIX_SPAWN_DUP2, child_out, 1),
                   (os.POSIX_SPAWN_DUP2, child_err, 2)]
        actions += [(os.POSIX_SPAWN_CLOSE, fd) for fd in sorted(self.fds)]
        self.pid = os.posix_spawn(self.executable, [self.executable], {"LANG": "C", "LC_ALL": "C"},
                                 file_actions=actions, setsigmask=(),
                                 setsigdef=(signal.SIGPIPE, signal.SIGXCPU, signal.SIGTERM))
        for fd in (child_in, child_out, child_err):
            self.close(fd)
        os.set_blocking(self.stdin_fd, False)
        self.watch(outfd, selectors.EVENT_READ, "stdout")
        self.watch(errfd, selectors.EVENT_READ, "stderr")
        self.pidfd = os.pidfd_open(self.pid)
        self.fds.add(self.pidfd)

    def policy(self):
        if (os.getsid(self.pid), os.getpgid(self.pid)) != (self.pid, self.pid):
            return
        status = Path(f"/proc/{self.pid}/status").read_text().splitlines()
        parent = next(int(s.split()[1]) for s in status if s.startswith("PPid:"))
        vm = next(int(s.split()[1]) * 1024 for s in status if s.startswith("VmSize:"))
        if parent != os.getpid() or vm >= 268435456 or sha(f"/proc/{self.pid}/exe") != self.digest:
            raise RuntimeError("worker bootstrap identity")
        actual = {}
        for name, (key, limit) in LIMITS.items():
            resource.prlimit(self.pid, key, limit)
            actual[name] = list(resource.prlimit(self.pid, key))
            if actual[name] != list(limit):
                raise RuntimeError("policy readback")
        names = sorted(os.listdir(f"/proc/{self.pid}/fd"))
        if names != ["0", "1", "2"]:
            raise RuntimeError("unexpected inherited worker descriptors")
        identities = []
        for name in names:
            path = f"/proc/{self.pid}/fd/{name}"
            stat = os.stat(path)
            record = {"fd": int(name), "target": os.readlink(path), "dev": str(stat.st_dev), "ino": str(stat.st_ino)}
            if record != self.expected_fds[name]:
                raise RuntimeError("worker descriptor identity")
            identities.append(record)
        self.emit({"v": 1, "kind": "worker_ready", "owner_pid": os.getpid(), "worker_pid": self.pid,
                   "ppid": parent, "sid": os.getsid(self.pid), "pgid": os.getpgid(self.pid),
                   "exe_sha256": self.digest, "limits": actual, "G_bytes": 0, "image_bytes_sent": 0,
                   "fds": identities})
        self.phase = True

    def poll_wait(self):
        if self.pid is None or self.wait is not None or self.lost:
            return
        try:
            waited, status, _usage = os.wait4(self.pid, os.WNOHANG)
        except ChildProcessError:
            self.lost = True
            self.invalidate("cleanup_unknown")
            return
        if waited:
            if waited != self.pid or not (os.WIFEXITED(status) or os.WIFSIGNALED(status)):
                raise RuntimeError("nonterminal wait")
            self.wait = {"raw_status": status, "exit_code": os.waitstatus_to_exitcode(status),
                         "collector_pid": os.getpid()}
            self.close(self.stdin_fd)
            self.close(self.pidfd)
            if self.wait["exit_code"] != 0:
                self.invalidate("worker_error")

    def kill_owned(self):
        if self.pid is None or self.wait is not None or self.killed or self.lost:
            return
        if self.pid <= 1 or self.pid == os.getpid():
            self.invalidate("cleanup_unknown")
            self.lost = True
            return
        # pidfd refers to the unreaped direct child opened immediately at spawn.
        # No group signal or PID rediscovery is used on an uncertain handle.
        if self.pidfd is not None:
            signal.pidfd_send_signal(self.pidfd, signal.SIGKILL)
        else:
            parent = next(int(s.split()[1]) for s in Path(f"/proc/{self.pid}/status").read_text().splitlines() if s.startswith("PPid:"))
            if parent != os.getpid():
                self.lost = True
                return
            os.kill(self.pid, signal.SIGKILL)
        self.killed = True

    def worker_io(self, fd, name):
        if name == "worker_input":
            if self.reason is not None or not self.ack:
                return
            if (os.getsid(self.pid), os.getpgid(self.pid)) != (self.pid, self.pid):
                raise RuntimeError("worker session changed before write")
            block = memoryview(b"G") if not self.g else memoryview(self.image)[self.sent:self.sent + CHUNK]
            try:
                count = os.write(fd, block)
            except BlockingIOError:
                return
            if not self.g:
                self.g = count
            else:
                self.sent += count
            if self.sent == RAW:
                self.close(fd)
        else:
            try:
                block = os.read(fd, min(CHUNK, max(1, CAP - len(self.streams[name]) + 1)))
            except BlockingIOError:
                return
            if not block:
                self.eof.add(name)
                self.close(fd)
                return
            self.totals[name] += len(block)
            remaining = CAP - len(self.streams[name])
            self.streams[name].extend(block[:remaining])
            if len(block) > remaining:
                self.invalidate("worker_error")

    def known(self):
        return self.pid is None or (self.wait is not None and not self.lost and self.eof == {"stdout", "stderr"})

    def terminal(self, eligible, quarantine=False):
        result = bytes(self.streams["stdout"]) if eligible else b""
        return {"v": 1, "kind": "terminal", "owner_pid": os.getpid(),
                "outcome": "cleanup_unknown" if quarantine else ("decoded" if eligible else self.reason),
                "ownership": "quarantined" if quarantine else "settled", "worker_pid": self.pid,
                "worker_wait": self.wait,
                "worker_io": {"stdin_closed": None if self.pid is None else self.stdin_fd not in self.fds,
                              "stdout_eof": None if self.pid is None else "stdout" in self.eof,
                              "stderr_eof": None if self.pid is None else "stderr" in self.eof,
                              "owned_fds_closed": not self.fds},
                "session_policy_verified": self.phase, "input_bytes_received": self.input_count,
                "input_sha256": hashlib.sha256(self.image).hexdigest() if self.input_eof and len(self.image) == RAW else None,
                "G_bytes": self.g, "image_bytes_sent": self.sent,
                "stdout_observed": self.totals["stdout"], "stdout_retained": len(self.streams["stdout"]),
                "stderr_observed": self.totals["stderr"], "stderr_retained": len(self.streams["stderr"]),
                "worker_stderr_base64": base64.b64encode(self.streams["stderr"]).decode("ascii"),
                "result_bytes": len(result), "result_sha256": hashlib.sha256(result).hexdigest() if result else None,
                "final_worker_eligible": eligible, "cancel_observed": self.cancel,
                "timing": {"begin_ns": None if self.begin is None else str(self.begin),
                           "invalidated_ns": None if self.invalidated is None else str(self.invalidated),
                           "cleanup_deadline_ns": None if self.cleanup is None else str(self.cleanup),
                           "settled_ns": None if self.settled is None else str(self.settled),
                           "final_admission_ns": None if self.admission is None else str(self.admission)}}

    def run(self):
        try:
            if len(self.digest) != 64 or sha(self.executable) != self.digest:
                raise ValueError("worker SHA256 mismatch")
            for fd in live_fds():
                if fd > 2:
                    os.set_inheritable(fd, False)
            self.watch(3, selectors.EVENT_READ, "control")
            self.watch(0, selectors.EVENT_READ, "image")
            if os.write(4, b"R") != 1:
                raise RuntimeError("ready write")
            os.close(4)
        except BaseException:
            self.invalidate("setup_error")
        while True:
            try:
                # Drain control before image or W data, including before a commit.
                if self.reason is not None and self.known():
                    break
                if self.reason is None:
                    self.commands()
                now = time.monotonic_ns()
                if self.reason is None and self.begin is not None and now >= self.begin + WALL_NS:
                    self.invalidate("wall")
                self.poll_wait()
                if self.reason:
                    self.kill_owned()
                    if self.known():
                        break
                    if time.monotonic_ns() >= self.cleanup:
                        try:
                            self.emit(self.terminal(False, quarantine=True))
                        except OSError:
                            pass  # Broken parent channel cannot release ownership.
                        os.close(5)
                        # Unknown status/IO never becomes successful close. Preserve
                        # owner/handles, no automatic restart or last-owner kill.
                        while True:
                            time.sleep(1)
                elif self.pid is None and self.input_eof:
                    self.spawn_worker()
                elif self.pid is not None and not self.phase and self.wait is None:
                    self.policy()
                if self.pid is not None and self.known():
                    break
                events = self.selector.select(0.001)
                for key, _mask in sorted(events, key=lambda item: item[0].data != "control"):
                    if key.data == "control":
                        if self.reason is None:
                            self.commands()
                    elif key.data == "image":
                        self.ingress()
                    elif key.fd in self.fds:
                        self.worker_io(key.fd, key.data)
            except BaseException:
                self.invalidate("setup_error")
        for fd in list(self.fds):
            self.close(fd)
        self.settled = time.monotonic_ns()
        eligible = (self.reason is None and self.phase and self.wait is not None and self.wait["exit_code"] == 0
                    and self.g == 1 and self.sent == RAW and bool(self.streams["stdout"]))
        self.admission = time.monotonic_ns()
        if eligible and self.admission >= self.begin + WALL_NS:
            self.invalidate("wall")
            eligible = False
        if not eligible and self.reason is None:
            self.invalidate("worker_error")
        self.selector.close()
        record = self.terminal(eligible)
        try:
            self.emit(record)
            if eligible:
                view = memoryview(self.streams["stdout"])
                while view:
                    view = view[os.write(1, view):]
        except OSError:
            return 2  # W already collected; parent must reject incomplete channels.
        return 0 if eligible or self.reason == "unused" else 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    return Owner(args.worker, args.sha256).run()


if __name__ == "__main__":
    raise SystemExit(main())
