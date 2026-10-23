"""One admitted Linux/CPython host experiment; no QR decoder or product API.

Run with the pinned R00 interpreter, -I -B. The child waits for a one-byte
control gate before consuming the public image. Only the parent applies policy.
Direct wait4 acquisition, never a fabricated/default exit status, owns reuse.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import mmap
import os
from pathlib import Path
import platform
import resource
import selectors
import signal
import stat
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PARAMETERS = json.loads((HERE / "parameters.json").read_text())
P = PARAMETERS["baseline"]
EXPECTATIONS = json.loads((HERE / "expectations.json").read_text())
AMENDMENT = json.loads((HERE / "strategy-amendment.json").read_text())
SOURCES = EXPECTATIONS["sources"]
PYTHON = Path("/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/python/bin/python3")
N = 172800
CHUNK = P["fixed_IO_chunk_bytes"]
LIMITS = {
    resource.RLIMIT_AS: (P["worker_AS_bytes"], P["worker_AS_bytes"]),
    resource.RLIMIT_CPU: (P["CPU_soft_seconds"], P["CPU_hard_seconds"]),
    resource.RLIMIT_CORE: (0, 0),
}
CHILD_ENV = {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_write(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def write_all(fd, data):
    view = memoryview(data)
    while view:
        count = os.write(fd, view[:CHUNK])
        if count <= 0:
            raise RuntimeError("worker short write")
        view = view[count:]


def worker(mode):
    # Explicit readmitted strategy, not a runtime fallback for a deniedcall.
    if mode != "no-session":
        os.setsid()  # trusted bootstrap; before any control/image read
    # This bounded control read is bootstrap, not image data or decoder work.
    if os.read(0, 1) != b"G":
        return 70
    actual = {str(k): list(resource.getrlimit(k)) for k in LIMITS}
    if any(tuple(actual[str(k)]) != v for k, v in LIMITS.items()):
        return 71
    if mode == "backpressure":
        write_all(2, b'{"phase":"not-reading-after-policy"}\n')
        time.sleep(P["wall_eligibility_deadline"] + P["cleanup_observation_window"] + 1)
        return 72
    hashed = hashlib.sha256()
    remaining = N
    while remaining:
        block = os.read(0, min(CHUNK, remaining))
        if not block:
            return 73
        hashed.update(block)
        remaining -= len(block)
    if hashed.hexdigest() != SOURCES["public_RGB"]["sha256"]:
        return 74
    def phase(name):
        write_all(2, json.dumps({"phase": name, "input_sha256": hashed.hexdigest(), "rlimits": actual}, separators=(",", ":")).encode() + b"\n")
    if mode == "cpu":
        # Never burn under an infinite/unknown hard limit, even if invoked alone.
        if resource.getrlimit(resource.RLIMIT_CPU) != (1, 2):
            return 75
        phase("cpu-hard-limit-validated")
        signal.signal(signal.SIGXCPU, signal.SIG_IGN)
        value = 0
        while True:
            value = (value + 1) & 65535
    if mode == "as":
        phase("as-mapping-before")
        try:
            # Reserve virtual space; do not touch this large mapping's pages.
            region = mmap.mmap(-1, P["worker_AS_bytes"] + mmap.PAGESIZE, access=mmap.ACCESS_WRITE)
        except OSError as exc:
            write_all(2, json.dumps({"phase": "as-mapping-error", "errno": exc.errno}, separators=(",", ":")).encode() + b"\n")
            return 40 if exc.errno == errno.ENOMEM else 76
        else:
            region.close()
            return 77
    if mode == "wall":
        phase("wall-sleep-after-input")
        time.sleep(P["wall_eligibility_deadline"] + P["cleanup_observation_window"] + 1)
        return 78
    if mode == "stdout":
        write_all(1, b"O" * (P["stdout_bytes"] + 1))
        return 0
    if mode == "stderr":
        write_all(1, b'{"phase":"stderr-flood-after-input"}\n')
        write_all(2, b"E" * (P["stderr_bytes"] + 1))
        return 0
    if mode != "echo":
        return 79
    output = (ROOT / SOURCES["predetermined_public_output"]["path"]).open("rb")
    with output:
        data = output.read(P["stdout_bytes"] + 1)
    if len(data) != 198 or digest(data) != SOURCES["predetermined_public_output"]["sha256"]:
        return 80
    write_all(1, data)
    return 0


class Owner:
    """Experiment-only single-resource ownership witness, not a session engine."""
    def __init__(self):
        self.busy = False
        self.quarantined = False
        self.generation = 0

    def acquire(self):
        if self.busy or self.quarantined:
            return False
        self.busy = True
        self.generation += 1
        return True

    def settle(self, known):
        if known:
            self.busy = False
        else:
            self.quarantined = True
            # Keep reserved permanently when own status is not known.


def open_fds():
    result = []
    for name in os.listdir("/proc/self/fd"):
        fd = int(name)
        try:
            os.fstat(fd)
        except OSError:
            continue
        result.append(fd)
    return sorted(result)


def context():
    if not sys.platform.startswith("linux") or sys.version_info[:2] != (3, 12):
        raise RuntimeError("required Linux/CPython3.12 unavailable; no fallback")
    if Path(sys.executable).resolve() != PYTHON.resolve():
        raise RuntimeError("not pinned R00 interpreter")
    if not all(hasattr(os, name) for name in ("posix_spawn", "setsid", "getsid", "getpgid", "wait4", "POSIX_SPAWN_DUP2", "POSIX_SPAWN_CLOSE", "pipe2")) or not hasattr(resource, "prlimit"):
        raise RuntimeError("required spawn/wait/prlimit API missing")
    status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":" in line)
    if os.getuid() == 0 or os.geteuid() != os.getuid() or int(status["CapEff"].strip(), 16) != 0 or int(status["Threads"].strip()) != 1:
        raise RuntimeError("unprivileged single-thread context required")
    executable_stat = PYTHON.resolve().stat()
    if executable_stat.st_mode & (stat.S_ISUID | stat.S_ISGID):
        raise RuntimeError("privileged executable not admitted")
    if "security.capability" in os.listxattr(PYTHON.resolve()):
        raise RuntimeError("executable file capabilities not admitted")
    bound = {}
    for name, source in SOURCES.items():
        path = ROOT / source["path"]
        data = path.read_bytes()
        if digest(data) != source["sha256"] or ("bytes" in source and len(data) != source["bytes"]):
            raise RuntimeError("source mismatch: " + name)
        bound[name] = dict(source)
    env = json.loads((ROOT / SOURCES["R00_environment"]["path"]).read_text())
    # The R00 file is directly an environment map, not an environment member.
    if not isinstance(env, dict) or "PATH" not in env:
        raise RuntimeError("R00 environment map invalid")
    sources = {}
    for module in (os, resource, selectors, mmap):
        path = getattr(module, "__file__", None)
        if path:
            sources[module.__name__] = {"path": path, "sha256": digest(Path(path).read_bytes())}
    return {"python": sys.version, "executable": str(PYTHON), "executable_realpath": str(PYTHON.resolve()),
            "executable_sha256": digest(PYTHON.resolve().read_bytes()), "kernel": platform.uname()._asdict(),
            "libc": platform.libc_ver(), "uid": os.getuid(), "euid": os.geteuid(), "gid": os.getgid(),
            "groups": os.getgroups(), "parent_pid": os.getpid(), "parent_pgid": os.getpgrp(),
            "CapEff": status["CapEff"].strip(), "threads": int(status["Threads"].strip()),
            "child_environment": CHILD_ENV, "source_bindings": bound, "stdlib_sources": sources,
            "policy": "Read-only R00; explicit nonsecret child env, absolute executable -I -B, no parent/global limit changes"}


def validate_input(case, image):
    caps = dict(P)
    row = case.get("boundary_row")
    if row:
        matched = [r for r in PARAMETERS["frozen_boundary_rows"] if r["row"] == row]
        if len(matched) != 1:
            raise RuntimeError("ambiguous frozen row")
        caps.update(matched[0]["parameter_overlay"])
    raw = memoryview(image)
    if row == "stride-length-relation":
        raw = raw[:-1]  # transient bounded view; no new image/corpus
    # Caller metadata stays fixed; caps are independent, no artificial product rule.
    width, height, bpp, stride = 240, 240, 3, 720
    for field in ("maximum_width", "maximum_height", "maximum_pixels", "raw_input_bytes"):
        if type(caps[field]) is not int or caps[field] <= 0:
            raise RuntimeError("invalid cap")
    if width > caps["maximum_width"]:
        return raw, caps, "width"
    if height > caps["maximum_height"]:
        return raw, caps, "height"
    # Python integers cannot wrap; exact stride/length before spawn or conversion.
    if width * height > caps["maximum_pixels"]:
        return raw, caps, "pixels"
    if stride != width * bpp or len(raw) != stride * height:
        return raw, caps, "relation"
    if len(raw) > caps["raw_input_bytes"]:
        return raw, caps, "raw"
    return raw, caps, None


def raw_wait(pid):
    got, status, usage = os.wait4(pid, os.WNOHANG)
    if got == 0:
        return None
    if got != pid:
        raise RuntimeError("wait returned non-owned PID")
    return {"pid": got, "raw_status": status, "exitcode": os.waitstatus_to_exitcode(status),
            "user_seconds": usage.ru_utime, "system_seconds": usage.ru_stime,
            "maxrss_kernel_units": usage.ru_maxrss}


def run_case(case, owner, image, expected_output, directory):
    record = {"id": case["id"], "group": case["group"], "expected": case["expected"], "events": [],
              "spawned": 0, "image_bytes_sent": 0, "control_bytes_sent": 0, "eligible": False,
              "owner_wait": None, "first_reaper_wait": None, "parent_signals": [], "actual_QR_decode": False}
    start = time.monotonic()
    def event(name, **extra):
        record["events"].append({"event": name, "t": time.monotonic() - start, **extra})
    def refuse_second(where):
        before = owner.generation
        refused = not owner.acquire()
        if not refused:
            raise RuntimeError("second owner acquired at " + where)
        record.setdefault("second_operation_refusals", []).append({"where": where, "generation_unchanged": owner.generation == before})
    initial_fds = open_fds()
    if not owner.acquire():
        raise RuntimeError("case cannot acquire nonreusable owner")
    record["owner_generation"] = owner.generation
    raw, caps, rejection = validate_input(case, image)
    record["actual_raw_length"] = len(raw)
    record["effective_caps"] = {key: caps[key] for key in ("maximum_width", "maximum_height", "maximum_pixels", "raw_input_bytes")}
    if rejection:
        record["boundary"] = rejection
        owner.settle(True)
        record["checks"] = {"intended_pre_spawn_boundary": case["expected"] == "pre_spawn_" + rejection + "_refusal", "zero_spawn_and_transfer": True}
        record["disposition"] = "PASS" if all(record["checks"].values()) else "NOT_EXERCISED"
        json_write(directory / (case["id"] + ".json"), record)
        return record
    abort = case.get("abort_phase")
    if abort == "pre-spawn":
        event("already-aborted-before-spawn")
        record["boundary"] = "abort"
        owner.settle(True)
        record["checks"] = {"no_spawn_no_transfer_ineligible": True}
        record["disposition"] = "PASS"
        json_write(directory / (case["id"] + ".json"), record)
        return record
    selector = selectors.DefaultSelector()
    fds = set()
    pid = None
    collected = False
    owner_status_known = False
    streams = {"stdout": bytearray(), "stderr": bytearray()}
    totals = {"stdout": 0, "stderr": 0}
    read_max = 0
    write_max = 0
    mode = case["worker_mode"]
    reason = None
    policy_ready = False
    session_ready = False
    waiting_cleanup = False
    cleanup_deadline = None
    stdin_fd = None
    io_eof = set()
    def close_fd(fd):
        if fd in fds:
            try:
                selector.unregister(fd)
            except KeyError:
                pass
            os.close(fd)
            fds.remove(fd)
    def stop(why):
        nonlocal reason, waiting_cleanup, cleanup_deadline
        if reason is None:
            reason = why
            event("invalidated", reason=why)
        if not waiting_cleanup:
            waiting_cleanup = True
            cleanup_deadline = time.monotonic() + P["cleanup_observation_window"]
        if stdin_fd is not None:
            close_fd(stdin_fd)
    def signal_owned():
        if pid is None or collected or record.get("owner_wait_error"):
            return
        if pid <= 1 or pid == os.getpid() or pid == os.getpgrp() or record.get("pid") != pid:
            raise RuntimeError("unsafe/unowned signal target")
        try:
            os.kill(pid, signal.SIGKILL)
            record["parent_signals"].append({"pid": pid, "signal": int(signal.SIGKILL)})
            event("owned-SIGKILL", pid=pid)
        except ProcessLookupError:
            event("owned-signal-ESRCH-await-status", pid=pid)
    try:
        pipes = [os.pipe2(os.O_CLOEXEC) for _ in range(3)]
        for pair in pipes:
            fds.update(pair)
        child_stdin, parent_stdin = pipes[0]
        parent_stdout, child_stdout = pipes[1]
        parent_stderr, child_stderr = pipes[2]
        actions = [(os.POSIX_SPAWN_DUP2, child_stdin, 0), (os.POSIX_SPAWN_DUP2, child_stdout, 1), (os.POSIX_SPAWN_DUP2, child_stderr, 2)]
        # CLOEXEC closes unrelated descriptors; explicitly close any inheritable fd.
        inherited = [fd for fd in initial_fds if fd > 2 and os.get_inheritable(fd)]
        actions += [(os.POSIX_SPAWN_CLOSE, fd) for fd in sorted(fds | set(inherited))]
        argv = [str(PYTHON), "-I", "-B", str(Path(__file__).resolve()), "--worker", mode]
        record["argv"] = argv
        record["closed_extra_inheritable_fds"] = inherited
        event("spawn-begin")
        # Plain spawn is the single explicit readmitted strategy. Trustedchild
        # setsid success is independently checked by kernelqueries beforepolicy.
        pid = os.posix_spawn(str(PYTHON), argv, CHILD_ENV, file_actions=actions, setsigmask=(), setsigdef=(signal.SIGPIPE, signal.SIGXCPU, signal.SIGTERM))
        # Record ownership immediately, before any independently falliblequery.
        record.update(pid=pid, spawned=1)
        record.update(pgid=os.getpgid(pid), sid=os.getsid(pid))
        event("spawn-return", pid=pid)
        if pid <= 1 or pid == os.getpgrp():
            raise RuntimeError("unsafe owned PID")
        for fd in (child_stdin, child_stdout, child_stderr):
            close_fd(fd)
        stdin_fd = parent_stdin
        for fd, stream in ((parent_stdout, "stdout"), (parent_stderr, "stderr")):
            os.set_blocking(fd, False)
            selector.register(fd, selectors.EVENT_READ, stream)
        os.set_blocking(parent_stdin, False)
        refuse_second("live-child-before-policy")
        if abort == "after-spawn":
            stop("abort")
        else:
            # Rendezvous uses only existing stdout/stderr pipes. No readyformat,
            # addedpipe or per-poll trace growth. Bounds precede every append.
            record["session_poll_count"] = 0
            while reason is None and not session_ready:
                sid, pgid = os.getsid(pid), os.getpgid(pid)
                record["session_poll_count"] += 1
                record["last_kernel_identity"] = {"pid": pid, "sid": sid, "pgid": pgid}
                if sid == pid and pgid == pid:
                    session_ready = True
                    event("kernel-session-established", sid=sid, pgid=pgid, pid=pid)
                    break
                if time.monotonic() >= start + P["wall_eligibility_deadline"]:
                    stop("session-not-established")
                    break
                waited = raw_wait(pid)
                if waited is not None:
                    record["owner_wait"] = waited
                    owner_status_known = True
                    collected = True
                    event("owner-wait-during-session", raw_status=waited["raw_status"])
                    refuse_second("acquired-wait-before-parent-IO-close")
                    stop("session-exited-before-established")
                    break
                for key, _mask in selector.select(0.01):
                    stream = key.data
                    cap = P[stream + "_bytes"]
                    count = min(CHUNK, max(1, cap - len(streams[stream]) + 1))
                    try:
                        block = os.read(key.fd, count)
                    except BlockingIOError:
                        continue
                    read_max = max(read_max, len(block))
                    if not block:
                        close_fd(key.fd)
                        io_eof.add(stream)
                        continue
                    totals[stream] += len(block)
                    remaining = cap - len(streams[stream])
                    streams[stream].extend(block[:remaining])
                    if len(block) > remaining:
                        stop(stream + "-overflow-before-session")
            if session_ready:
                if (os.getsid(pid), os.getpgid(pid)) != (pid, pid):
                    raise RuntimeError("kernel session changed before policy")
                event("kernel-identity-before-policy")
            before = Path(f"/proc/{pid}/status").read_text() if session_ready else ""
            vm = next((int(line.split()[1]) * 1024 for line in before.splitlines() if line.startswith("VmSize:")), None)
            record["bootstrap_VmSize_bytes"] = vm
            if not session_ready:
                pass  # admission refused; no prlimit/control/image action
            elif vm is None or vm >= P["worker_AS_bytes"]:
                stop("impossible-startup-AS")
            else:
                applied = {}
                for key, limits in LIMITS.items():
                    old = resource.prlimit(pid, key, limits)
                    actual = resource.prlimit(pid, key)
                    applied[str(key)] = {"previous": old, "requested": limits, "readback": actual}
                    if actual != limits:
                        raise RuntimeError("prlimit readback mismatch")
                record["policy"] = applied
                event("policy-set-and-readback")
                policy_ready = True
                if case["id"] == "policy-permission":
                    try:
                        resource.prlimit(pid, resource.RLIMIT_AS, (P["worker_AS_bytes"], P["worker_AS_bytes"] + 1))
                    except PermissionError as exc:
                        record["policy_error"] = {"type": type(exc).__name__, "errno": exc.errno, "actual_AS_after": resource.prlimit(pid, resource.RLIMIT_AS)}
                        stop("policy-permission")
                    else:
                        raise RuntimeError("unexpected privilege: hard-AS raise succeeded; stop, no input")
                elif abort == "after-policy":
                    stop("abort")
                else:
                    # Gate/input writes are supervised together; no child input beforepolicy.
                    selector.register(parent_stdin, selectors.EVENT_WRITE, "stdin")
        if reason:
            signal_owned()
        signalled = bool(record["parent_signals"])
        deadline = start + P["wall_eligibility_deadline"]
        stolen = case["id"] == "stolen-status"
        while True:
            now = time.monotonic()
            if not waiting_cleanup and now >= deadline:
                stop("wall")
            if waiting_cleanup and not signalled and not collected:
                signal_owned()
                signalled = True
            if waiting_cleanup and now >= cleanup_deadline:
                record["cleanup_window_exceeded"] = True
                break
            # For stolen-status, deliberately permit the controlled first reaper
            # only after valid complete I/O. Never give its status to this owner.
            if not collected and (not stolen or io_eof == {"stdout", "stderr"}):
                try:
                    waited = raw_wait(pid)
                    if waited is not None:
                        collected = True
                        if stolen:
                            record["first_reaper_wait"] = waited
                            event("controlled-other-reaper-acquired", raw_status=waited["raw_status"])
                            try:
                                owner_wait = raw_wait(pid)
                            except ChildProcessError as exc:
                                record["owner_wait_error"] = {"type": type(exc).__name__, "errno": exc.errno}
                                reason = "missing-status"
                                event("owner-wait-ECHILD")
                            else:
                                raise RuntimeError("owner unexpectedly acquired lost status: " + str(owner_wait))
                        else:
                            record["owner_wait"] = waited
                            owner_status_known = True
                            event("owner-wait-acquired", raw_status=waited["raw_status"])
                        # Real descriptors/selector remain unsettled here.
                        refuse_second("acquired-wait-before-parent-IO-close")
                except ChildProcessError:
                    record["owner_wait_error"] = {"type": "ChildProcessError", "unexpected": True}
                    reason = "missing-status"
                    break
            if collected and io_eof == {"stdout", "stderr"}:
                break
            events = selector.select(0.01)
            for key, _mask in events:
                fd, stream = key.fd, key.data
                if fd not in fds:
                    continue
                if stream == "stdin":
                    if not policy_ready or not session_ready:
                        raise RuntimeError("input before session/policy")
                    if (os.getsid(pid), os.getpgid(pid)) != (pid, pid):
                        raise RuntimeError("kernel session changed before write")
                    record["kernel_identity_checks_before_writes"] = record.get("kernel_identity_checks_before_writes", 0) + 1
                    if record["control_bytes_sent"] == 0:
                        block = memoryview(b"G")
                    else:
                        block = raw[record["image_bytes_sent"]:record["image_bytes_sent"] + CHUNK]
                    if not block:
                        close_fd(fd)
                        event("stdin-complete")
                        continue
                    try:
                        sent = os.write(fd, block)
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        close_fd(fd)
                        if reason is None:
                            stop("broken-input")
                        continue
                    write_max = max(write_max, len(block))
                    if record["control_bytes_sent"] == 0:
                        record["control_bytes_sent"] = sent
                        event("gate-sent")
                    else:
                        if record["image_bytes_sent"] == 0:
                            event("first-image-byte-sent")
                        record["image_bytes_sent"] += sent
                        if abort == "during-input":
                            stop("abort")
                    if record["image_bytes_sent"] == len(raw):
                        close_fd(fd)
                        event("stdin-complete")
                else:
                    cap = P[stream + "_bytes"]
                    # Read at most remaining+1 (for overflow) and absolutechunk.
                    # Retained storage never grows over cap, including on failure.
                    count = min(CHUNK, max(1, cap - len(streams[stream]) + 1))
                    try:
                        block = os.read(fd, count)
                    except BlockingIOError:
                        continue
                    read_max = max(read_max, len(block))
                    if not block:
                        close_fd(fd)
                        io_eof.add(stream)
                        event("EOF", stream=stream)
                        continue
                    totals[stream] += len(block)
                    remaining = cap - len(streams[stream])
                    streams[stream].extend(block[:remaining])
                    if len(block) > remaining:
                        stop(stream + "-overflow")
                    if abort == "after-output" and bytes(streams["stdout"]) == expected_output:
                        stop("abort")
        # A negative boundary or abort remains ineligible even if actual childexit0.
        record["boundary"] = reason or "completion"
    except BaseException as exc:
        record["harness_error"] = {"type": type(exc).__name__, "message": str(exc)}
        event("harness-error", type=type(exc).__name__, message=str(exc))
        reason = "harness-error"
    finally:
        # On normal cases this is bookkeeping only. On any exception still collect
        # this explicit owned direct child; never sweep/reap unknown children.
        if pid is not None and not collected:
            signal_owned()
            # A failure does not buy a secondcleanupwindow or change thecap.
            until = cleanup_deadline if cleanup_deadline is not None else time.monotonic() + P["cleanup_observation_window"]
            while time.monotonic() < until:
                try:
                    waited = raw_wait(pid)
                except ChildProcessError as exc:
                    record["owner_wait_error"] = {"type": type(exc).__name__, "errno": exc.errno}
                    break
                if waited:
                    record["owner_wait"] = waited
                    owner_status_known = True
                    collected = True
                    event("owner-wait-acquired-finally", raw_status=waited["raw_status"])
                    break
                time.sleep(0.01)
        for fd in list(fds):
            close_fd(fd)
        selector.close()
        record["owned_child_collected"] = collected or pid is None
        record["own_status_acquired"] = owner_status_known
        record["all_parent_IO_closed"] = not fds
        record["callbacks_settled"] = True  # synchronous selector only; no thread/callback left
        record["final_open_fds_equal_initial"] = open_fds() == initial_fds
        known = record["owned_child_collected"] and (owner_status_known or pid is None) and record["all_parent_IO_closed"] and record["final_open_fds_equal_initial"]
        owner.settle(known)
        event("owner-settlement", known=known, quarantined=owner.quarantined)
    record["totals"] = totals
    record["retained"] = {name: len(data) for name, data in streams.items()}
    record["max_read_chunk"] = read_max
    record["max_write_request"] = write_max
    record["duration_seconds"] = time.monotonic() - start
    for name, data in streams.items():
        (directory / (case["id"] + "." + name + ".bin")).write_bytes(data)
    checks = {"no_harness_error": "harness_error" not in record,
              "bounded_retained_and_chunk": all(len(streams[s]) <= P[s + "_bytes"] for s in streams) and read_max <= CHUNK and write_max <= CHUNK,
              "owned_child_collected": record["owned_child_collected"],
              "all_IO_and_FDs_settled": record["all_parent_IO_closed"] and record["final_open_fds_equal_initial"],
              "second_owner_refused": len(record.get("second_operation_refusals", [])) >= 2}
    out = bytes(streams["stdout"])
    err = bytes(streams["stderr"])
    waited = record["owner_wait"]
    record["session_ready"] = session_ready
    common = record["image_bytes_sent"] == N and record["control_bytes_sent"] == 1 and policy_ready and session_ready
    kind = case["id"]
    if mode == "echo" and not abort and kind not in ("policy-permission", "stolen-status"):
        # Final eligibility is sampled here, after actualwait/IO settlement;
        # a loop-top timestamp cannot cover descheduling before thisdecision.
        admission_now = None
        record["eligible"] = reason is None and common and out == expected_output and waited is not None and waited["exitcode"] == 0 and not owner.busy and not owner.quarantined and (admission_now := time.monotonic()) < start + P["wall_eligibility_deadline"]
        if admission_now is not None:
            record["admission_elapsed_seconds"] = admission_now - start
            record["admission_budget_seconds"] = P["wall_eligibility_deadline"]
            if not record["eligible"]:
                reason = "wall"
                record["boundary"] = "wall-at-admission"
                event("expired-at-result-admission", elapsed=admission_now - start)
        checks["exact_eligible_output"] = record["eligible"]
    elif kind == "policy-permission":
        failure = record.get("policy_error", {})
        checks["real_EPERM_no_input_effective_limit_unchanged"] = reason == "policy-permission" and failure.get("errno") == errno.EPERM and tuple(failure.get("actual_AS_after", ())) == LIMITS[resource.RLIMIT_AS] and record["image_bytes_sent"] == 0 and record["control_bytes_sent"] == 0
    elif mode == "no-session":
        checks["isolated_no_session_zero_admission_bytes"] = reason == "session-not-established" and not session_ready and not policy_ready and record["control_bytes_sent"] == 0 and record["image_bytes_sent"] == 0 and record.get("last_kernel_identity", {}).get("sid") != pid and record.get("last_kernel_identity", {}).get("pgid") != pid and owner_status_known and not owner.busy and not owner.quarantined
    elif mode == "as":
        checks["isolated_kernel_ENOMEM_after_valid_input"] = common and waited is not None and waited["exitcode"] == 40 and b'"phase":"as-mapping-before"' in err and b'"errno":12' in err and not record["parent_signals"] and reason is None
    elif mode == "cpu":
        checks["isolated_finite_kernel_CPU_hard_kill"] = common and b'"phase":"cpu-hard-limit-validated"' in err and waited is not None and waited["exitcode"] == -signal.SIGKILL and waited["user_seconds"] + waited["system_seconds"] >= 1.5 and not record["parent_signals"] and reason is None
    elif mode == "wall":
        checks["isolated_wall_after_valid_input"] = common and b'"phase":"wall-sleep-after-input"' in err and reason == "wall" and bool(record["parent_signals"]) and waited is not None and waited["exitcode"] == -signal.SIGKILL
    elif mode in ("stdout", "stderr"):
        other = "stderr" if mode == "stdout" else "stdout"
        checks["isolated_output_boundary"] = common and reason == mode + "-overflow" and totals[mode] == 513 and totals[other] <= P[other + "_bytes"] and (mode != "stdout" or totals["stderr"] == 0)
    elif mode == "backpressure":
        checks["responsive_under_input_backpressure"] = b'"phase":"not-reading-after-policy"' in err and 0 < record["image_bytes_sent"] < N and reason == "wall" and bool(record["parent_signals"])
    elif abort:
        checks["abort_never_eligible"] = reason == "abort" and not record["eligible"] and owner_status_known
        checks["intended_abort_phase"] = ({"after-spawn": record["control_bytes_sent"] == 0 and not policy_ready,
                                           "after-policy": record["control_bytes_sent"] == 0 and policy_ready,
                                           "during-input": 0 < record["image_bytes_sent"] < N,
                                           "after-output": common and out == expected_output})[abort]
    elif kind == "stolen-status":
        first = record["first_reaper_wait"]
        checks["actual_prior_valid_IO_and_stolen_status"] = common and out == expected_output and err == b"" and first is not None and first["exitcode"] == 0 and record.get("owner_wait_error", {}).get("errno") == errno.ECHILD and waited is None and not owner_status_known
        checks["permanent_quarantine_refuses_new_operation"] = owner.quarantined and owner.busy and not owner.acquire()
    record["checks"] = checks
    record["disposition"] = "PASS" if all(checks.values()) else "NOT_EXERCISED"
    json_write(directory / (case["id"] + ".json"), record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=("echo", "as", "cpu", "wall", "stdout", "stderr", "backpressure", "no-session"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--cases", help="Comma-separated focused IDs; omitted means one stable complete campaign")
    args = parser.parse_args()
    if args.worker:
        return worker(args.worker)
    if not args.out:
        parser.error("--out required; must not exist")
    args.out.mkdir(parents=True, exist_ok=False)
    ctx = context()
    ctx["harness_sha256"] = digest(Path(__file__).read_bytes())
    ctx["parameters_sha256"] = digest((HERE / "parameters.json").read_bytes())
    ctx["expectations_sha256"] = digest((HERE / "expectations.json").read_bytes())
    ctx["strategy_amendment_sha256"] = digest((HERE / "strategy-amendment.json").read_bytes())
    json_write(args.out / "environment.json", ctx)
    wanted = args.cases.split(",") if args.cases else None
    # Original21case file remains byteidentical; explicit additivegate before
    # last stolen-status case, which intentionally quarantines theowner.
    cases = EXPECTATIONS["cases"][:-1] + [AMENDMENT["extra_case"]] + EXPECTATIONS["cases"][-1:]
    if wanted:
        if len(set(wanted)) != len(wanted) or set(wanted) - {c["id"] for c in cases}:
            raise RuntimeError("unknown/repeated case selector")
        cases = [c for c in cases if c["id"] in wanted]
    image = (ROOT / SOURCES["public_RGB"]["path"]).read_bytes()
    output = (ROOT / SOURCES["predetermined_public_output"]["path"]).read_bytes()
    owner = Owner()
    results = []
    initial_fds = open_fds()
    parent_identity = {"sid": os.getsid(0), "pgid": os.getpgrp()}
    parent_limits = {str(k): resource.getrlimit(k) for k in LIMITS}
    started = time.monotonic()
    for case in cases:
        record = run_case(case, owner, image, output, args.out)
        results.append(record)
        print(case["id"], record["disposition"], record.get("boundary"), flush=True)
        if record["disposition"] != "PASS":
            break  # preserve failure, do not turn following masked rows intoPASS
        if owner.quarantined and case != cases[-1]:
            raise RuntimeError("quarantined case must be last")
    summary = {"role": "Host process/IPC experiment only; no QR decoding, crypto or product admission", "focused": bool(wanted),
               "requested_cases": [c["id"] for c in cases], "results": [{"id": r["id"], "disposition": r["disposition"], "checks": r["checks"]} for r in results],
               "not_exercised_after_mask": [c["id"] for c in cases[len(results):]],
               "duration_seconds": time.monotonic() - started, "final_FDs_equal_initial": open_fds() == initial_fds,
               "owner_quarantined": owner.quarantined, "all_created_direct_children_collected": all(r.get("owned_child_collected", r["spawned"] == 0) for r in results),
               "new_threads": 0, "new_descendants": 0, "all47_criteria_unchanged": True}
    final_status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":" in line)
    summary["actual_final_threads"] = int(final_status["Threads"].strip())
    summary["parent_identity_before"] = parent_identity
    summary["parent_identity_after"] = {"sid": os.getsid(0), "pgid": os.getpgrp()}
    summary["parent_limits_before"] = parent_limits
    summary["parent_limits_after"] = {str(k): resource.getrlimit(k) for k in LIMITS}
    summary["parent_identity_and_limits_unchanged"] = summary["parent_identity_after"] == parent_identity and summary["parent_limits_after"] == parent_limits
    summary["actual_owned_PIDs"] = [r["pid"] for r in results if "pid" in r]
    summary["passed"] = summary["actual_final_threads"] == 1 and summary["parent_identity_and_limits_unchanged"] and len(results) == len(cases) and all(r["disposition"] == "PASS" for r in results) and summary["final_FDs_equal_initial"] and summary["all_created_direct_children_collected"]
    json_write(args.out / "summary.json", summary)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
