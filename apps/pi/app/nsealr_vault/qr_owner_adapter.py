"""Opt-in Linux RGB/O/W diagnostic consumer; no camera, signer or default route.

Calls belong to one thread, while unrelated process/library threads may exist.
The owning runtime must remain alive on quarantine. Neither object destruction
nor an observation timeout can prove collection or authorize replacement.
"""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys

from .qr import decode_qr_envelope


RAW = 172800
CAP = 512
STATUS_CAP = 4096
MAX_SAFE = 9007199254740991
OWNER_SHA = "d7a245a9a558cce3ec8271ec42fc49664c094320c6465a537aa3a49c83558d50"
PHASE_KEYS = ["v", "kind", "owner_pid", "worker_pid", "ppid", "sid", "pgid",
              "exe_sha256", "limits", "G_bytes", "image_bytes_sent", "fds"]
TERMINAL_KEYS = ["v", "kind", "owner_pid", "outcome", "ownership", "worker_pid",
                 "worker_wait", "worker_io", "session_policy_verified", "input_bytes_received",
                 "input_sha256", "G_bytes", "image_bytes_sent", "stdout_observed",
                 "stdout_retained", "stderr_observed", "stderr_retained", "worker_stderr_base64",
                 "result_bytes", "result_sha256", "final_worker_eligible", "cancel_observed", "timing"]
OUTCOMES = {"decoded", "unused", "cancelled", "input_invalid", "control_lost",
            "control_malformed", "setup_error", "worker_error", "wall", "cleanup_unknown"}

# Only this literal bootstrap runs before the fixed O. Popen closes all other
# descriptors in its native child setup, without a Python preexec_fn. Every
# source FD is >=6, so the child-only dup2 operations cannot overwrite a source.
_BOOTSTRAP = """import os,sys
sources=[int(value) for value in sys.argv[1:7]]
for target,source in enumerate(sources):
    os.dup2(source,target)
for source in sources:
    os.close(source)
os.execv(sys.executable,[sys.executable,'-B',sys.argv[7],'--worker',sys.argv[8],'--sha256',sys.argv[9]])
"""


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _file_sha(path):
    with open(path, "rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _keys(value, names):
    _require(type(value) is dict and list(value) == names, "record keys/order")


def _integer(value, low=0, high=MAX_SAFE):
    _require(type(value) is int and low <= value <= high, "integer type/range")


def _decimal(value):
    _require(type(value) is str and re.fullmatch(r"0|[1-9][0-9]{0,19}", value) is not None,
             "canonical decimal")
    _require(int(value) <= 18446744073709551615, "unsigned64 decimal")


def _digest(value):
    _require(type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None, "SHA256")


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        _require(key not in value, "duplicate status key")
        value[key] = item
    return value


def _not_number(_value):
    raise ValueError("status float/nonfinite")


def _record(wire):
    _require(wire.endswith(b"\n") and wire.isascii(), "status ASCII/LF")
    value = json.loads(wire, object_pairs_hook=_pairs, parse_float=_not_number,
                       parse_constant=_not_number)
    _require((json.dumps(value, ensure_ascii=True, separators=(",", ":")) + "\n").encode("ascii")
             == wire, "noncanonical status")
    return value


class RgbOwnerRuntime:
    """Explicit admission owner; strong reference survives loss of caller op refs."""

    def __init__(self):
        self._operation = None

    @property
    def operation(self):
        return self._operation

    def reserve(self, worker_path, worker_sha256):
        return RgbOwnerDecode(self, worker_path, worker_sha256)

    def _require_free(self):
        if self._operation is not None:
            _require(self._operation._closed and self._operation._settled
                     and not self._operation._poisoned, "prior operation not known closed")


class RgbOwnerDecode:
    """One O and one RGB presentation, retained by its explicit runtime."""

    def __init__(self, runtime, worker_path, worker_sha256):
        _require(type(runtime) is RgbOwnerRuntime, "explicit owning runtime")
        runtime._require_free()
        _require(type(worker_path) is str and os.path.isabs(worker_path), "absolute worker path")
        _digest(worker_sha256)
        worker = Path(worker_path).resolve(strict=True)
        _require(worker.is_file() and os.access(worker, os.X_OK), "regular executable worker")
        _require(_file_sha(worker) == worker_sha256, "worker SHA256 mismatch")
        self._runtime = runtime
        self._worker = str(worker)
        self._digest = worker_sha256
        self._owner = Path(__file__).with_name("qr_worker.py").resolve(strict=True)
        _require(_file_sha(self._owner) == OWNER_SHA, "unreviewed owner source")
        self._child = None
        self._fds = set()
        self._channels = {}
        self._pipe_identities = []
        self._buffers = {key: bytearray() for key in (1, 2, 4, 5)}
        self._observed = {key: 0 for key in (1, 2, 4, 5)}
        self._eof = set()
        self._status_tail = bytearray()
        self._records = 0
        self._phase = self._terminal = None
        self._ready = self._presented = self._ack = self._cancelled = False
        self._unused = self._closed = self._settled = self._poisoned = False
        self._fault = self._transport_error = None
        self._raw_wait = self._exit_code = None
        self._commands = []
        self._pending_control = bytearray()
        self._image = None
        self._sent = 0
        self._input_sha = None
        self._taken = False
        runtime._operation = self
        self._selector = selectors.DefaultSelector()

    def _watch(self, fd, event, channel):
        os.set_blocking(fd, False)
        self._selector.register(fd, event, channel)

    def _close_fd(self, fd):
        if fd in self._fds:
            try:
                self._selector.unregister(fd)
            except KeyError:
                pass
            os.close(fd)
            self._fds.remove(fd)

    def open(self):
        _require(self._child is None and not self._closed and not self._poisoned
                 and not self._cancelled, "open state")
        sources = []
        try:
            _require(_file_sha(self._worker) == self._digest, "worker changed before spawn")
            for target in range(6):
                read, write = os.pipe2(os.O_CLOEXEC)
                self._fds.update((read, write))
                child_end, parent_end = (read, write) if target in (0, 3) else (write, read)
                source = fcntl.fcntl(child_end, fcntl.F_DUPFD_CLOEXEC, 6)
                self._fds.add(source)
                sources.append(source)
                self._close_fd(child_end)
                self._channels[target] = parent_end
                stat = os.fstat(source)
                self._pipe_identities.append({"fd": target, "dev": str(stat.st_dev),
                                              "ino": str(stat.st_ino),
                                              "target": os.readlink(f"/proc/self/fd/{source}")})
            argv = [sys.executable, "-B", "-c", _BOOTSTRAP, *map(str, sources),
                    str(self._owner), self._worker, self._digest]
            self._child = subprocess.Popen(argv, close_fds=True, pass_fds=tuple(sources))
            for source in sources:
                self._close_fd(source)
            os.set_blocking(self._channels[3], False)
            for channel in (1, 2, 4, 5):
                self._watch(self._channels[channel], selectors.EVENT_READ, channel)
            os.set_blocking(self._channels[0], False)
        except BaseException as error:
            self._fault = f"open: {error}"
            self._poisoned = True
            # Retain reservation/FDs, including partial setup. No destructor or
            # exception path silently abandons a possibly created child.
            raise

    def start(self, rgb):
        _require(type(rgb) is bytes and len(rgb) == RAW, "exact packed RGB888 bytes")
        _require(self._ready and not self._presented and not self._cancelled
                 and not self._unused and not self._poisoned and not self._settled, "start state")
        self._presented = True
        self._image = rgb
        self._input_sha = _sha(rgb)
        self._queue("P")
        self._watch(self._channels[0], selectors.EVENT_WRITE, 0)

    def acknowledge(self):
        _require(self._phase is not None and not self._ack and not self._cancelled
                 and not self._poisoned and not self._settled, "G requires verified phase")
        self._ack = True
        self._queue("G")

    def _queue(self, opcode):
        _require(len(self._commands) + len(self._pending_control) < 3, "control capacity")
        self._pending_control.extend(opcode.encode("ascii"))

    def cancel(self):
        if self._cancelled:
            return
        self._cancelled = True
        self._image = None
        if not self._unused:
            self._pending_control.clear()  # No queued P/G after local invalidation.
        if self._child is not None and self._raw_wait is None and not self._unused:
            self._queue("X")
        else:
            self._close_fd(self._channels.get(0))

    def close(self):
        if self._settled:
            self._closed = True
        elif self._child is None and not self._poisoned:
            self._closed = self._settled = True
            self._selector.close()
        elif not self._presented and not self._cancelled and not self._unused:
            self._unused = True
            self._queue("Q")
        elif not self._unused:
            self.cancel()
        return self.state

    def _flush_control(self):
        while self._pending_control:
            try:
                count = os.write(self._channels[3], self._pending_control[:1])
            except BlockingIOError:
                return
            except OSError as error:
                self._transport_error = str(error)
                self._pending_control.clear()
                self._close_fd(self._channels.get(0))
                return
            _require(count == 1, "control short write")
            opcode = chr(self._pending_control.pop(0))
            self._commands.append(opcode)
            if opcode in ("X", "Q"):
                self._close_fd(self._channels.get(0))

    def _fail(self, error):
        if self._fault is None:
            self._fault = str(error)
        self._poisoned = True
        self.cancel()

    def _validate_phase(self, row):
        _require(self._presented and "P" in self._commands and not self._unused, "phase requires P")
        _keys(row, PHASE_KEYS)
        for key in ("v", "owner_pid", "worker_pid", "ppid", "sid", "pgid", "G_bytes", "image_bytes_sent"):
            _integer(row[key])
        _require(row["v"] == 1 and row["kind"] == "worker_ready", "phase version/kind")
        _require(row["owner_pid"] == self._child.pid and row["ppid"] == self._child.pid
                 and row["worker_pid"] > 1 and row["sid"] == row["worker_pid"]
                 and row["pgid"] == row["worker_pid"], "phase identity/session")
        _require(row["exe_sha256"] == self._digest, "phase executable")
        _keys(row["limits"], ["AS", "CPU", "CORE"])
        for key, expected in (("AS", [268435456, 268435456]), ("CPU", [1, 2]), ("CORE", [0, 0])):
            value = row["limits"][key]
            _require(type(value) is list and len(value) == 2, "phase limits shape")
            for item in value:
                _integer(item)
            _require(value == expected, "phase limits value")
        _require(row["G_bytes"] == 0 and row["image_bytes_sent"] == 0, "phase pre-G")
        _require(type(row["fds"]) is list and len(row["fds"]) == 3, "phase fd count")
        for index, fd in enumerate(row["fds"]):
            _keys(fd, ["fd", "target", "dev", "ino"])
            _integer(fd["fd"], index, index)
            _decimal(fd["dev"])
            _decimal(fd["ino"])
            _require(fd["target"] == f"pipe:[{fd['ino']}]" and len(fd["target"]) <= 27, "phase pipe")

    def _status(self, block):
        self._status_tail.extend(block)
        while b"\n" in self._status_tail:
            end = self._status_tail.index(10) + 1
            wire = bytes(self._status_tail[:end])
            del self._status_tail[:end]
            self._records += 1
            _require(self._records <= 2 and self._terminal is None, "extra status record")
            row = _record(wire)
            _require(type(row) is dict, "status object required")
            if row.get("kind") == "worker_ready":
                _require(self._phase is None, "duplicate phase")
                self._validate_phase(row)
                self._phase = row
            else:
                _require(row.get("kind") == "terminal", "unknown status kind")
                self._terminal = row
                if row.get("ownership") == "quarantined":
                    self._fail("owner reports unknown cleanup")

    def _read(self, channel):
        cap = STATUS_CAP if channel == 5 else 1 if channel == 4 else CAP
        retained = self._buffers[channel]
        size = min(4096, max(1, cap + 1 - len(retained)))
        try:
            block = os.read(self._channels[channel], size)
        except BlockingIOError:
            return
        if not block:
            self._eof.add(channel)
            self._close_fd(self._channels[channel])
            if channel == 4:
                _require(retained == b"R" and not self._poisoned, "R then EOF required")
                self._ready = True
            return
        self._observed[channel] += len(block)
        retained.extend(block[:max(0, cap + 1 - len(retained))])
        _require(self._observed[channel] <= cap, "channel overrun")
        if channel == 5:
            self._status(block)

    def _write_image(self):
        if self._cancelled or self._poisoned or "P" not in self._commands or self._image is None:
            return
        try:
            count = os.write(self._channels[0], self._image[self._sent:self._sent + 4096])
        except BlockingIOError:
            return
        self._sent += count
        if self._sent == RAW:
            self._image = None
            self._close_fd(self._channels[0])

    def _collect(self):
        if self._child is None or self._raw_wait is not None:
            return
        try:
            pid, status, _usage = os.wait4(self._child.pid, os.WNOHANG)
        except ChildProcessError:
            self._fail("O status unavailable; never substitute zero")
            return
        if pid:
            _require(pid == self._child.pid and (os.WIFEXITED(status) or os.WIFSIGNALED(status)), "O terminal wait")
            self._raw_wait = status
            self._exit_code = os.waitstatus_to_exitcode(status)
            self._child.returncode = self._exit_code  # This exact wait4 already collected it.

    def _validate_terminal(self):
        row = self._terminal
        _keys(row, TERMINAL_KEYS)
        _integer(row["v"], 1, 1)
        _integer(row["owner_pid"], self._child.pid, self._child.pid)
        _require(row["kind"] == "terminal" and row["outcome"] in OUTCOMES, "terminal kind/outcome")
        _require(row["ownership"] == "settled", "unknown ownership")
        for key in ("session_policy_verified", "final_worker_eligible", "cancel_observed"):
            _require(type(row[key]) is bool, "terminal boolean")
        io = row["worker_io"]
        _keys(io, ["stdin_closed", "stdout_eof", "stderr_eof", "owned_fds_closed"])
        _require(io["owned_fds_closed"] is True, "worker FDs not closed")
        if row["worker_pid"] is None:
            _require(self._phase is None and row["worker_wait"] is None, "no-worker phase/wait")
            _require(all(io[key] is None for key in ("stdin_closed", "stdout_eof", "stderr_eof")), "no-worker IO")
            _require(row["session_policy_verified"] is False, "no-worker policy")
            _require(all(type(row[key]) is int and row[key] == 0 for key in
                         ("G_bytes", "image_bytes_sent", "stdout_observed", "stderr_observed")), "no-worker counters")
        else:
            _integer(row["worker_pid"], 2)
            if self._phase is not None:
                _require(row["worker_pid"] == self._phase["worker_pid"], "worker replaced")
            _require(row["session_policy_verified"] == (self._phase is not None), "policy phase relation")
            wait = row["worker_wait"]
            _keys(wait, ["raw_status", "exit_code", "collector_pid"])
            _integer(wait["raw_status"], 0, 65535)
            _integer(wait["exit_code"], -127, 255)
            _integer(wait["collector_pid"], self._child.pid, self._child.pid)
            _require(os.WIFEXITED(wait["raw_status"]) or os.WIFSIGNALED(wait["raw_status"]), "W terminal wait")
            _require(os.waitstatus_to_exitcode(wait["raw_status"]) == wait["exit_code"], "wait code relation")
            _require(all(io[key] is True for key in ("stdin_closed", "stdout_eof", "stderr_eof")), "W IO unsettled")
        for key in ("stdout_observed", "stderr_observed"):
            _integer(row[key])
        _integer(row["input_bytes_received"], 0, RAW + 1)
        _integer(row["G_bytes"], 0, 1)
        _integer(row["image_bytes_sent"], 0, RAW)
        for key in ("stdout_retained", "stderr_retained", "result_bytes"):
            _integer(row[key], 0, CAP)
        _require(row["stdout_retained"] <= row["stdout_observed"] and
                 row["stderr_retained"] <= row["stderr_observed"], "retention counters")
        if row["input_sha256"] is not None:
            _digest(row["input_sha256"])
            _require(row["input_bytes_received"] == RAW, "input hash/count")
        _require(type(row["worker_stderr_base64"]) is str, "stderr type")
        stderr = base64.b64decode(row["worker_stderr_base64"], validate=True)
        _require(base64.b64encode(stderr).decode("ascii") == row["worker_stderr_base64"]
                 and len(stderr) == row["stderr_retained"], "stderr canonical/count")
        output = bytes(self._buffers[1])
        _require(row["result_bytes"] == len(output) and row["result_sha256"] == (_sha(output) if output else None),
                 "result count/hash")
        timing = row["timing"]
        _keys(timing, ["begin_ns", "invalidated_ns", "cleanup_deadline_ns", "settled_ns", "final_admission_ns"])
        for value in timing.values():
            if value is not None:
                _decimal(value)
        _require(timing["settled_ns"] is not None and timing["final_admission_ns"] is not None
                 and int(timing["settled_ns"]) <= int(timing["final_admission_ns"]), "settlement timing")
        expected_cleanup = None if timing["invalidated_ns"] is None else str(int(timing["invalidated_ns"]) + 4000000000)
        _require(timing["cleanup_deadline_ns"] == expected_cleanup, "shared cleanup deadline")
        if row["outcome"] == "unused":
            _require(row["worker_pid"] is None and self._phase is None and
                     row["input_bytes_received"] == 0 and row["G_bytes"] == 0 and
                     row["image_bytes_sent"] == 0, "unused relations")
        if row["outcome"] == "decoded":
            _require(row["result_bytes"] > 0, "decoded empty result")
            _require(self._phase is not None and row["worker_wait"]["exit_code"] == 0, "decoded phase/status")
            _require(row["stdout_observed"] == row["stdout_retained"] == row["result_bytes"] <= CAP,
                     "decoded stdout counters")
            _require(row["stderr_observed"] == row["stderr_retained"] <= CAP, "decoded stderr counters")
            _require(row["final_worker_eligible"] is True and row["cancel_observed"] is False, "decoded eligibility")
            _require(row["G_bytes"] == 1 and row["image_bytes_sent"] == RAW and
                     row["input_bytes_received"] == RAW and row["input_sha256"] == self._input_sha,
                     "decoded input binding")
            _require(timing["invalidated_ns"] is None and timing["begin_ns"] is not None and
                     int(timing["final_admission_ns"]) < int(timing["begin_ns"]) + 8000000000, "decoded deadline")
            _require(self._ack and "G" in self._commands and self._sent == RAW, "caller G/image relation")
        else:
            _require(not output and row["final_worker_eligible"] is False, "refusal output")
        _require(self._exit_code == (0 if row["outcome"] in ("decoded", "unused") else 2), "O exit/outcome")
        _require(not self._buffers[2], "O diagnostic")

    def poll(self, wait_ms=0):
        _integer(wait_ms, 0, 50)
        if self._settled:
            return self.state
        _require(self._child is not None, "poll before open")
        try:
            self._flush_control()
            events = self._selector.select(wait_ms / 1000)
            # Drain trusted control/status before any more image input.
            for key, _event in sorted(events, key=lambda event: (event[0].data == 0, event[0].data)):
                if key.fd not in self._fds:
                    continue
                try:
                    self._write_image() if key.data == 0 else self._read(key.data)
                except (ValueError, OSError, TypeError, KeyError, RecursionError) as error:
                    self._fail(error)
            self._flush_control()
            self._collect()
            if self._raw_wait is not None and self._eof == {1, 2, 4, 5}:
                _require(not self._status_tail and self._terminal is not None, "complete terminal/EOF")
                self._validate_terminal()
                if not self._poisoned:
                    self._settled = True
                for fd in list(self._fds):
                    self._close_fd(fd)
                self._selector.close()
        except (ValueError, OSError, TypeError, KeyError, RecursionError) as error:
            self._fail(error)
        return self.state

    @property
    def state(self):
        if self._poisoned:
            return "quarantined"
        if self._settled:
            return "settled"
        if self._phase is not None and not self._ack:
            return "verified-worker-ready"
        if self._ready and not self._presented:
            return "owner-ready"
        return "pending"

    def take_result(self):
        _require(self._settled and not self._poisoned and not self._cancelled and not self._closed
                 and not self._taken and self._terminal["outcome"] == "decoded", "no releasable result")
        raw = bytes(self._buffers[1])
        try:
            parsed = decode_qr_envelope(raw.decode("ascii"))
        except ValueError:
            self._cancelled = True  # Known collected framing refusal; no release/retry.
            raise
        # No callback or await between final local guard and this one release.
        _require(not self._cancelled, "cancelled before release")
        self._taken = True
        return raw, parsed

    def observation(self):
        """Source/status evidence only; never exposes the private decoded frame."""
        return json.loads(json.dumps({"state": self.state, "owner_pid": self._child.pid if self._child else None,
                "owner_wait_raw": self._raw_wait, "owner_exit_code": self._exit_code,
                "pipe_identities": self._pipe_identities, "commands": self._commands,
                "phase": self._phase, "terminal": self._terminal, "EOF": sorted(self._eof),
                "image_bytes_written": self._sent, "output_bytes": len(self._buffers[1]),
                "output_sha256": _sha(self._buffers[1]) if self._buffers[1] else None,
                "status_wire_base64": base64.b64encode(self._buffers[5]).decode("ascii"),
                "diagnostic_base64": base64.b64encode(self._buffers[2]).decode("ascii"),
                "ready_hex": self._buffers[4].hex(), "fault": self._fault,
                "transport_error": self._transport_error, "parent_owned_fds": sorted(self._fds),
                "taken": self._taken, "closed": self._closed}))
