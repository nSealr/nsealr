"""Finite admitted O/W negatives, exact no-W helpers, and pure wire controls.

Normal Pi discovery runs these tests using the existing producer's required
worker path/hash. No test builds a worker or silently skips missing inputs.
"""
import base64
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest

from nsealr_vault.qr_owner_adapter import (RgbOwnerRuntime, _decimal, _integer,
                                         _record)


ROOT = Path(__file__).resolve().parents[3]
PREFIX = ROOT / "docs/restart/implementation/QP01/python-owner-adapter/negative"
EXPECTATIONS = json.loads((PREFIX / "expectations.json").read_text())
IMAGE = ROOT / "docs/restart/implementation/QH01/native-qr-probe/execution-01/request-kind-1-basic.rgb"
ENVELOPE = ROOT / "docs/restart/implementation/QH01/native-qr-probe/expected/request-kind-1-basic.envelope"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def configured_worker():
    path = os.environ.get("NSEALR_QP01_QR_WORKER")
    sha = os.environ.get("NSEALR_QP01_QR_WORKER_SHA256")
    require(path is not None and sha is not None, "required provisioned W path/SHA missing; no skip")
    require(Path(path).is_absolute() and digest(Path(path).read_bytes()) == sha,
            "trusted provisioned actual W binding")
    return path, sha


def save(case, event, role, op=None, **extra):
    record = {"id": case, "event": event, "role": role, **extra}
    if op is not None:
        record["observation"] = op.observation()
    directory = os.environ.get("NSEALR_QP01_OWNER_EVIDENCE")
    if directory:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        with (path / f"{case}-{event}.json").open("x") as target:
            json.dump(record, target, indent=2)
            target.write("\n")
    # unittest's preceding stderr progress dot has no LF in the merged CI
    # stream. Start a fresh line before every structured evidence record.
    print("\n" + json.dumps({"python_owner_case": record}), flush=True)


def hold_uncertain(case, op, reason):
    save(case, "attention", "UNCERTAIN_REAL_OWNER_RETAINED_NO_RECOVERY", op, reason=reason)
    print("LIVE OWNER/EXACT RUNTIME RETAINED: notify root; no kill/restart/exit", flush=True)
    while True:
        op.poll(50)
        time.sleep(0.1)


def until(case, op, predicate, *, helper=False):
    end = time.monotonic() + 20
    while True:
        op.poll(50)
        if predicate():
            return
        if op.state == "quarantined" and not helper:
            hold_uncertain(case, op, "real lifecycle unexpectedly quarantined")
        if time.monotonic() >= end:
            hold_uncertain(case, op, "observation expired, never a cleanup proof")


class OwnerAdapterLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = configured_worker()
        cls.runtime = RgbOwnerRuntime()
        cls.image = IMAGE.read_bytes()
        require(len(cls.image) == 172800 and digest(cls.image) ==
                "64d9be602c821c31c0dfd6e952199a328325acdbf9a7e1b3494921942a11055f", "independent RGB")

    def begin(self, case):
        op = self.runtime.reserve(*self.worker)
        self.addCleanup(self.cleanup_owned, case, op)
        op.open()
        until(case, op, lambda: op.state == "owner-ready")
        self.assertIs(self.runtime.operation, op)
        with self.assertRaises(ValueError):
            self.runtime.reserve(*self.worker)
        with self.assertRaises(ValueError):
            op.take_result()
        save(case, "ready", "actual_O_W_lifecycle", op)
        return op

    def phase(self, case, op):
        op.start(self.image)
        until(case, op, lambda: op.state == "verified-worker-ready")
        save(case, "phase", "actual_O_W_lifecycle", op)

    def cleanup_owned(self, case, op):
        if op._closed:
            return
        if not op._settled:
            op.cancel()
            until(case, op, lambda: op._settled)
            save(case, "exception-cleanup", "actual_owned_cleanup_not_case_PASS", op)
        op.close()

    def finish(self, case, op):
        until(case, op, lambda: op.state == "settled")
        record = op.observation()
        save(case, "observed-terminal", "actual_O_W_lifecycle_not_yet_case_PASS", op)
        expected = next(row for row in EXPECTATIONS["real_lifecycle_cases"] if row["id"] == case)
        self.assertEqual(record["terminal"]["outcome"], expected["terminal_outcome"])
        self.assertEqual(record["owner_exit_code"], expected["O_exit"])
        self.assertEqual(record["output_bytes"], expected["O_private_bytes"])
        self.assertEqual(record["EOF"], [1, 2, 4, 5])
        self.assertEqual(record["parent_owned_fds"], [])
        self.assertIsNotNone(record["owner_wait_raw"])
        if expected["W_count"]:
            wait = record["terminal"]["worker_wait"]
            if "accepted_W_wait_pairs" in expected:
                self.assertIn({"exit_code": wait["exit_code"], "raw_status": wait["raw_status"]},
                              expected["accepted_W_wait_pairs"])
                self.assertEqual(record["terminal"]["G_bytes"], 0)
                self.assertEqual(record["terminal"]["image_bytes_sent"], 0)
            else:
                self.assertEqual(wait["exit_code"], expected["W_exit"])
            self.assertEqual(record["terminal"]["worker_wait"]["collector_pid"], record["owner_pid"])
            self.assertIsNotNone(record["phase"])
        else:
            self.assertIsNone(record["terminal"]["worker_pid"])
            self.assertIsNone(record["phase"])
        with self.assertRaises(ChildProcessError):
            os.wait4(record["owner_pid"], os.WNOHANG)
        with self.assertRaises(ValueError):
            op.take_result()
        self.assertFalse(op._taken)
        self.assertEqual(record["terminal"]["cancel_observed"], expected["O_cancel_observed"])
        save(case, "settled", "actual_O_W_lifecycle", op, caller_released_bytes=0)
        op.close()
        self.assertIs(self.runtime.operation, op)

    def test_01_unused_Q(self):
        op = self.begin("unused_Q")
        op.close()
        self.finish("unused_Q", op)

    def test_02_cancel_preP(self):
        op = self.begin("cancel_preP")
        op.cancel()
        op.cancel()
        self.finish("cancel_preP", op)
        self.assertEqual(op.observation()["commands"], ["X"])

    def test_03_cancel_preG(self):
        op = self.begin("cancel_preG")
        self.phase("cancel_preG", op)
        op.cancel()
        self.finish("cancel_preG", op)
        self.assertEqual(op.observation()["commands"], ["P", "X"])
        self.assertEqual(op.observation()["terminal"]["image_bytes_sent"], 0)

    def test_04_late_discard(self):
        op = self.begin("late_discard")
        self.phase("late_discard", op)
        op.acknowledge()
        until("late_discard", op, lambda: op.state == "settled")
        self.assertEqual(bytes(op._buffers[1]), ENVELOPE.read_bytes())  # Private test observation, not API release.
        before = deepcopy(op.observation()["terminal"])
        op.cancel()
        self.finish("late_discard", op)
        self.assertEqual(op.observation()["terminal"], before)
        self.assertEqual(op.observation()["commands"], ["P", "G"])

    def test_05_wall8_preG(self):
        op = self.begin("wall8_preG")
        self.phase("wall8_preG", op)
        self.finish("wall8_preG", op)  # Continue polling, deliberately withhold G.
        row = op.observation()["terminal"]
        timing = row["timing"]
        self.assertGreaterEqual(int(timing["invalidated_ns"]), int(timing["begin_ns"]) + 8000000000)
        self.assertEqual(int(timing["cleanup_deadline_ns"]), int(timing["invalidated_ns"]) + 4000000000)
        self.assertEqual(row["G_bytes"], 0)
        self.assertEqual(row["image_bytes_sent"], 0)
        self.assertFalse(row["cancel_observed"])

    def malformed(self, case, wire):
        op = self.begin(case)
        self.assertEqual(os.write(op._channels[3], wire), len(wire))
        save(case, "wire-injected", "actual_control_fault_test_only_no_image", op, actual_wire_hex=wire.hex())
        self.finish(case, op)

    def test_06_invalid_Z(self):
        self.malformed("invalid_Z", b"Z")

    def test_07_duplicate_PP(self):
        self.malformed("duplicate_PP", b"PP")

    def test_08_premature_G(self):
        self.malformed("premature_G", b"G")

    def test_09_control_EOF_preG(self):
        op = self.begin("control_EOF_preG")
        self.phase("control_EOF_preG", op)
        op._close_fd(op._channels[3])  # Actual private fault injection; never present a second image.
        self.finish("control_EOF_preG", op)
        self.assertEqual(op.observation()["terminal"]["image_bytes_sent"], 0)


class OwnerAdapterWireHelperTests(unittest.TestCase):
    def cleanup_known_no_W_helper(self, case, op):
        if op._child is not None and (op._raw_wait is None or op._eof != {1, 2, 4, 5}):
            op.cancel()
            until(case, op, lambda: op._raw_wait is not None and op._eof == {1, 2, 4, 5}, helper=True)
        # Exact no-fork source, actually collected helper: parent test resources
        # may close. This never resets poison/admission or touches a live owner.
        for fd in list(op._fds):
            op._close_fd(fd)
        op._selector.close()

    def test_11_exact_no_W_helpers_reject_and_actually_complete(self):
        worker = configured_worker()
        self.retained_runtimes = []
        for row in EXPECTATIONS["helper_cases"]:
            with self.subTest(mode=row["mode"]):
                case = "FG7_" + row["mode"]
                path = ROOT / row["path"]
                source = path.read_bytes()
                self.assertEqual(len(source), row["bytes"])
                self.assertEqual(digest(source), row["sha256"])
                runtime = RgbOwnerRuntime()
                self.retained_runtimes.append(runtime)
                op = runtime.reserve(*worker)
                self.addCleanup(self.cleanup_known_no_W_helper, case, op)
                # Trusted test-only source override, never a selectable runtime
                # bootstrap/provider. The exact original helper cannot spawn W.
                op._owner = path
                op.open()
                if row["mode"].startswith("ready-"):
                    until(case, op, lambda: op._raw_wait is not None and op._eof == {1, 2, 4, 5}, helper=True)
                else:
                    until(case, op, lambda: op.state == "owner-ready", helper=True)
                    op.close()  # Existing helper must actually observe its Q.
                    until(case, op, lambda: op._raw_wait is not None and op._eof == {1, 2, 4, 5}, helper=True)
                observation = op.observation()
                save(case, "observed-collected", "actual_exact_no_W_helper_not_yet_case_PASS", op,
                     helper_sha256=row["sha256"], actual_W_count=0)
                self.assertEqual(observation["owner_wait_raw"], 0)
                self.assertEqual(observation["owner_exit_code"], 0)
                self.assertEqual(observation["diagnostic_base64"], "")
                self.assertEqual(observation["output_bytes"], 0)
                self.assertEqual(observation["ready_hex"], row["expected_ready_hex"])
                self.assertEqual(observation["commands"], [row["intended_control"]])
                self.assertEqual(observation["state"], "quarantined")
                self.assertIs(runtime.operation, op)
                with self.assertRaises(ValueError):
                    op.take_result()
                with self.assertRaises(ValueError):
                    runtime.reserve(*worker)
                wire = base64.b64decode(observation["status_wire_base64"])
                mode = row["mode"]
                if mode.startswith("ready-") or mode == "status-missing":
                    self.assertEqual(wire, b"")
                elif mode == "status-truncated":
                    self.assertTrue(wire and not wire.endswith(b"\n"))
                elif mode == "status-overflow":
                    self.assertEqual(wire, b"x" * 4097)
                elif mode == "duplicate-key":
                    self.assertIn(b'{"v":1,"v":1,', wire)
                elif mode == "duplicate-terminal":
                    self.assertEqual(wire.splitlines()[0], wire.splitlines()[1])
                elif mode == "phase-after-terminal":
                    self.assertTrue(wire.endswith(b'{"kind":"worker_ready"}\n'))
                elif mode == "wrong-owner":
                    self.assertNotEqual(observation["terminal"]["owner_pid"], observation["owner_pid"])
                elif mode == "wrong-worker":
                    self.assertEqual(observation["terminal"]["worker_pid"], 99)
                    self.assertIsNone(observation["terminal"]["worker_wait"])
                else:
                    self.assertFalse(observation["terminal"]["worker_io"]["owned_fds_closed"])
                save(case, "rejected-collected", "actual_exact_no_W_helper_only_not_worker_PASS", op,
                     helper_sha256=row["sha256"], actual_W_count=0, caller_released_bytes=0)
                with self.assertRaises(ChildProcessError):
                    os.wait4(observation["owner_pid"], os.WNOHANG)
                # Only known dead, exact no-fork test helpers: close the test's
                # remaining parent descriptors. Keep the runtime poisoned and
                # retain its exact operation/child record; never admit reuse.
                self.cleanup_known_no_W_helper(case, op)
                self.assertEqual(op.state, "quarantined")
                self.assertIs(runtime.operation, op)
                with self.assertRaises(ValueError):
                    runtime.reserve(*worker)
        self.assertEqual(len(self.retained_runtimes), 11)


@contextmanager
def synthetic_fixture():
    """Fabricated records only: no Popen, wait, signal, or kernel PID claim."""
    runtime = RgbOwnerRuntime()
    executable = str(Path(sys.executable).resolve())
    op = runtime.reserve(executable, digest(Path(executable).read_bytes()))
    phase = {"v": 1, "kind": "worker_ready", "owner_pid": 10001, "worker_pid": 10002,
             "ppid": 10001, "sid": 10002, "pgid": 10002, "exe_sha256": op._digest,
             "limits": {"AS": [268435456, 268435456], "CPU": [1, 2], "CORE": [0, 0]},
             "G_bytes": 0, "image_bytes_sent": 0,
             "fds": [{"fd": fd, "target": f"pipe:[{100 + fd}]", "dev": "1", "ino": str(100 + fd)}
                     for fd in (0, 1, 2)]}
    raw = ENVELOPE.read_bytes()
    decoded = {"v": 1, "kind": "terminal", "owner_pid": 10001, "outcome": "decoded", "ownership": "settled",
               "worker_pid": 10002, "worker_wait": {"raw_status": 0, "exit_code": 0, "collector_pid": 10001},
               "worker_io": {"stdin_closed": True, "stdout_eof": True, "stderr_eof": True, "owned_fds_closed": True},
               "session_policy_verified": True, "input_bytes_received": 172800,
               "input_sha256": "64d9be602c821c31c0dfd6e952199a328325acdbf9a7e1b3494921942a11055f",
               "G_bytes": 1, "image_bytes_sent": 172800, "stdout_observed": len(raw), "stdout_retained": len(raw),
               "stderr_observed": 0, "stderr_retained": 0, "worker_stderr_base64": "", "result_bytes": len(raw),
               "result_sha256": digest(raw), "final_worker_eligible": True, "cancel_observed": False,
               "timing": {"begin_ns": "1", "invalidated_ns": None, "cleanup_deadline_ns": None,
                          "settled_ns": "2", "final_admission_ns": "3"}}
    unused = deepcopy(decoded)
    unused.update(outcome="unused", worker_pid=None, worker_wait=None,
                  worker_io={"stdin_closed": None, "stdout_eof": None, "stderr_eof": None, "owned_fds_closed": True},
                  session_policy_verified=False, input_bytes_received=0, input_sha256=None,
                  G_bytes=0, image_bytes_sent=0, stdout_observed=0, stdout_retained=0,
                  result_bytes=0, result_sha256=None, final_worker_eligible=False,
                  timing={"begin_ns": None, "invalidated_ns": "1", "cleanup_deadline_ns": "4000000001",
                          "settled_ns": "2", "final_admission_ns": "3"})
    op._child = SimpleNamespace(pid=10001)
    op._presented = op._ack = True
    op._commands = ["P", "G"]
    op._sent = 172800
    op._input_sha = decoded["input_sha256"]
    op._buffers[1].extend(raw)
    op._phase = phase
    op._exit_code = 0
    op._terminal = decoded
    try:
        op._validate_phase(phase)
        op._validate_terminal()
        yield op, phase, decoded, unused
    finally:
        op._child = None  # It was always fabricated data, never an owned process.
        op.close()


class OwnerAdapterWirePureTests(unittest.TestCase):
    def test_original_nine_relation_mutations(self):
        for case in EXPECTATIONS["pure_relation_cases"]:
            with self.subTest(case=case), synthetic_fixture() as (op, phase, decoded, unused):
                if case.startswith("phase-"):
                    op._presented = case != "phase-before-P"
                    op._unused = case == "phase-after-Q"
                    with self.assertRaises(ValueError):
                        op._validate_phase(phase)
                elif case.startswith("unused-"):
                    op._phase = None
                    op._buffers[1].clear()
                    op._terminal = unused
                    op._validate_terminal()  # Independent valid unused baseline.
                    if case == "unused-with-phase":
                        op._phase = phase
                    else:
                        unused.update(worker_pid=10002, worker_wait=decoded["worker_wait"], worker_io=decoded["worker_io"])
                    with self.assertRaises(ValueError):
                        op._validate_terminal()
                else:
                    if case == "decoded-stdout-count-mismatch":
                        decoded["stdout_observed"] += 1
                    elif case == "decoded-stdout-overflow":
                        decoded.update(stdout_observed=513, stdout_retained=512)
                    elif case == "decoded-stdout-retained-result-mismatch":
                        decoded.update(stdout_observed=258, stdout_retained=258)
                    elif case == "decoded-stderr-overflow":
                        decoded.update(stderr_observed=513, stderr_retained=512,
                                       worker_stderr_base64=base64.b64encode(bytes(512)).decode("ascii"))
                    else:
                        decoded.update(stderr_observed=10, stderr_retained=9,
                                       worker_stderr_base64=base64.b64encode(bytes(9)).decode("ascii"))
                    with self.assertRaises(ValueError):
                        op._validate_terminal()
                save(case, "rejected", "PURE_SYNTHETIC_RELATION_ZERO_PROCESSES", fabricated_PIDs=[10001, 10002])

    def test_wire_types_canonicality_and_relations(self):
        self.assertEqual(_record(b'{"v":1}\n'), {"v": 1})
        bad_wires = [b'{"v":1,"v":1}\n', b'{"v":1.0}\n', b'{"v":NaN}\n', b'{"v":Infinity}\n',
                     b'{"v":"\xc3\xa9"}\n', b'{"v":1}', b'{"v": 1}\n', b'{"v":1}\n\n']
        for wire in bad_wires:
            with self.subTest(wire=wire), self.assertRaises(ValueError):
                _record(wire)
        for value in (True, -1, 9007199254740992, 1.0):
            with self.subTest(integer=value), self.assertRaises(ValueError):
                _integer(value)
        _decimal("18446744073709551615")
        for value in ("00", "01", "-1", "18446744073709551616"):
            with self.subTest(decimal=value), self.assertRaises(ValueError):
                _decimal(value)
        for key, value in (("v", True), ("result_bytes", 258), ("result_sha256", "0" * 64)):
            with self.subTest(terminal=key), synthetic_fixture() as (op, _phase, decoded, _unused):
                decoded[key] = value
                with self.assertRaises(ValueError):
                    op._validate_terminal()
        for field, value in (("raw_status", 127), ("raw_status", 65535), ("exit_code", 1)):
            with self.subTest(wait=field, value=value), synthetic_fixture() as (op, _phase, decoded, _unused):
                decoded["worker_wait"][field] = value
                with self.assertRaises(ValueError):
                    op._validate_terminal()
        with synthetic_fixture() as (op, phase, decoded, _unused):
            decoded["worker_io"]["stdin_closed"] = 1
            with self.assertRaises(ValueError):
                op._validate_terminal()
            phase["limits"]["CPU"] = [True, 2]
            with self.assertRaises(ValueError):
                op._validate_phase(phase)
        with synthetic_fixture() as (op, phase, _decoded, _unused):
            phase["extra"] = 1
            with self.assertRaises(ValueError):
                op._validate_phase(phase)
            del phase["extra"]
            with self.assertRaises(ValueError):
                op._validate_phase(dict(reversed(list(phase.items()))))
            with self.assertRaises(ValueError):
                op._status(b'[]\n')
        save("types-canonicality", "rejected", "PURE_WIRE_DATA_ZERO_PROCESSES", rejected_controls=27)

    def test_real_pipe_retention_limit_not_process_evidence(self):
        runtime = RgbOwnerRuntime()
        executable = str(Path(sys.executable).resolve())
        op = runtime.reserve(executable, digest(Path(executable).read_bytes()))
        read, write = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
        op._fds.update((read, write))
        op._channels[1] = read
        try:
            self.assertEqual(os.write(write, b"x" * 513), 513)
            with self.assertRaisesRegex(ValueError, "channel overrun"):
                op._read(1)
            self.assertEqual(op._observed[1], 513)
            self.assertEqual(len(op._buffers[1]), 513)
            self.assertIsNone(op._child)
            save("pipe-cap", "rejected", "REAL_PIPE_ONLY_ZERO_CHILDREN", retained_bytes=513, payload_cap=512)
        finally:
            for fd in list(op._fds):
                op._close_fd(fd)
            op.close()


if __name__ == "__main__":
    unittest.main()
