"""Pure control-flow fixtures only: no O/W/Node, cleanup or process recovery."""
from contextlib import ExitStack
import gc
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import weakref


class HoldSentinel(BaseException):
    """Only this pure test clock can interrupt the retention loop."""


class ReportingAbort(BaseException):
    """A reporting failure must be contained even for a BaseException."""


class Fixture:
    pass


class AttentionReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guards = ExitStack()
        cls.spawns = []
        for target in ["subprocess.Popen", "os.fork", "os.forkpty", "os.posix_spawn", "os.posix_spawnp"]:
            cls.spawns.append(cls.guards.enter_context(patch(target, side_effect=AssertionError("ZERO_CHILD fixture"))))
        spec = importlib.util.spec_from_file_location("fixed_composition_under_test", Path(__file__).with_name("run-composition.py"))
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        try:
            for mocked in cls.spawns:
                if mocked.call_count:
                    raise AssertionError("a child creation API was attempted")
        finally:
            cls.guards.close()

    def fixture(self, output):
        owner = self.module.Composition.__new__(self.module.Composition)
        runtime, op, handle, child = (Fixture() for _ in range(4))
        runtime.operation = op
        op._child = child
        op.observation = Mock(return_value={"role": "SYNTHETIC_NO_PROCESS"})
        op.poll = Mock(side_effect=[RuntimeError("pure existing-loop exception"), None])
        handle.pid = "SYNTHETIC_NO_REAL_PID"
        owner.runtime, owner.op, owner.node = runtime, op, handle
        owner.raw_wait, owner.eof, owner.output = None, set(), output
        owner.pump = Mock()
        refs = {name: weakref.ref(value) for name, value in
                zip(("runtime", "op", "handle", "child"), (runtime, op, handle, child))}
        return owner, refs

    def exercise(self, case):
        snapshots = []
        caught = None
        with tempfile.TemporaryDirectory(prefix="qh01-attention-pure-") as temporary:
            owner, refs = self.fixture(Path(temporary))
            def clock(_seconds):
                gc.collect()
                snapshots.append({"runtime": owner.runtime is refs["runtime"](),
                                  "op": owner.op is refs["op"](),
                                  "handle": owner.node is refs["handle"](),
                                  "child": owner.op._child is refs["child"](),
                                  "runtime_retains_operation": owner.runtime.operation is refs["op"]()})
                if len(snapshots) == 2:
                    raise HoldSentinel("PURE_FIXTURE_CLOCK_ONLY")
            with ExitStack() as patches:
                write = patches.enter_context(patch.object(self.module, "write", wraps=self.module.write))
                printing = patches.enter_context(patch("builtins.print"))
                sleeping = patches.enter_context(patch.object(self.module.time, "sleep", side_effect=clock))
                if case in ("write", "both"):
                    write.side_effect = OSError("forced reporting write failure")
                if case in ("print", "both"):
                    printing.side_effect = BrokenPipeError("forced reporting print failure")
                if case == "observation":
                    owner.op.observation.side_effect = ValueError("forced reporting observation failure")
                if case == "serialization":
                    patches.enter_context(patch.object(self.module.json, "dumps", side_effect=TypeError("forced reporting serialization failure")))
                if case == "report_base_exception":
                    write.side_effect = ReportingAbort("write reporting abort")
                    printing.side_effect = ReportingAbort("print reporting abort")
                try:
                    owner.attention("pure fixture only; no actual quarantine")
                except BaseException as error:
                    caught = error
                observed = {"case": case, "role": "PURE_MOCK_CONTROL_FLOW_ZERO_CHILD",
                            "escaped_type": type(caught).__name__, "hold_iterations": len(snapshots),
                            "poll_calls": owner.op.poll.call_count, "pump_calls": owner.pump.call_count,
                            "sleep_calls": sleeping.call_count, "write_calls": write.call_count,
                            "print_calls": printing.call_count, "retained_identity_snapshots": snapshots,
                            "child_creation_API_calls": sum(m.call_count for m in self.spawns),
                            "cleanup_or_recovery_exercised": False}
            directory = os.environ.get("NSEALR_QH01_ATTENTION_EVIDENCE")
            if directory:
                with (Path(directory) / (case + ".json")).open("x") as target:
                    json.dump(observed, target, indent=2)
                    target.write("\n")
            self.assertEqual(len(snapshots), 2, f"report escaped before retention: {observed}")
            self.assertIsInstance(caught, HoldSentinel)
            self.assertTrue(all(all(row.values()) for row in snapshots))
            self.assertEqual(owner.op.poll.call_count, 2)
            self.assertEqual(owner.pump.call_count, 1)
            self.assertEqual(sum(m.call_count for m in self.spawns), 0)

    def test_write_failure(self):
        self.exercise("write")

    def test_print_failure(self):
        self.exercise("print")

    def test_both_fail(self):
        self.exercise("both")

    def test_observation_failure(self):
        self.exercise("observation")

    def test_serialization_failure(self):
        self.exercise("serialization")

    def test_reporting_base_exception(self):
        self.exercise("report_base_exception")


if __name__ == "__main__":
    unittest.main()
