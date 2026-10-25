"""Pure synthetic draw/input/config controls. No native library or child process."""
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "apps/pi/app"))
from nsealr_vault import synthetic_inspection as ui


@dataclass(frozen=True)
class Page:
    kind: int = 0
    index: int = 0
    total: int = 31
    label: bytes = b"role"
    body: bytes = b'"value"'
    position: bytes = b"1/31"


class Input(ui.ScenarioInput):
    def __init__(self):
        super().__init__("basic-fresh")
        self.calls = 0
        self.override = None

    def acquire(self, invocation, epoch, page):
        self.calls += 1
        if self.override is not None:
            return self.override(invocation, epoch, page)
        return super().acquire(invocation, epoch, page)


def setup(inputs=None, scenario="basic-fresh"):
    trace = ui.Trace()
    source = inputs or ui.ScenarioInput(scenario)
    return ui.InspectionIo(ui.CellSink(trace, scenario), source, trace), trace


class Layout(unittest.TestCase):
    def test_exact_full_boundary_and_byte_order(self):
        page = Page(label=b"L" * 32, body=b"\n".join([b"B" * 32] * 6), position=b"P" * 32)
        calls = ui.plan(page)
        self.assertEqual([c["role"] for c in calls], ["header", "label"] + ["body"] * 6 + ["position", "footer"])
        self.assertEqual([c["text"] for c in calls[1:-1]], ["L" * 32] + ["B" * 32] * 6 + ["P" * 32])
        self.assertEqual([c["y"] for c in calls[1:-1]], [48, 64, 80, 96, 112, 128, 144, 160])
        self.assertTrue(all(c["x"] == 24 and c["width"] == 192 and c["height"] == 8 for c in calls[1:-1]))

    def test_preserves_literal_escapes_and_blank_lines(self):
        page = Page(label=b"a\n\nb", body=b'"\\u000a"')
        calls = ui.plan(page)
        self.assertEqual([c["text"] for c in calls if c["role"] == "label"], ["a", "", "b"])
        self.assertEqual([c["text"] for c in calls if c["role"] == "body"], ['"\\u000a"'])

    def test_unfit_or_unsupported_before_any_draw_or_input(self):
        pages = [Page(label=b"L" * 33), Page(body=b"\n".join([b"B"] * 7)),
                 Page(body=b"\x80"), Page(label=b"\x00"), Page(kind=True), Page(total=0)]
        for page in pages:
            with self.subTest(page=page):
                inputs = Input()
                adapter, trace = setup(inputs)
                with self.assertRaises(ui.DisplayRefusal):
                    adapter(page)
                self.assertFalse(any(e["event"] in ("draw", "commit", "consume") for e in trace.events))
                self.assertEqual(inputs.calls, 0)
        with self.assertRaises(ui.DisplayRefusal):
            ui.plan(Page(), width=239)

    def test_draw_and_presenter_failures_never_commit_or_request_input(self):
        for scenario, page in [("draw-before", Page()), ("draw-partial", Page()),
                               ("draw-decision", Page(kind=1, index=30)), ("presenter-error", Page())]:
            with self.subTest(scenario=scenario):
                inputs = Input()
                adapter, trace = setup(inputs, scenario)
                with self.assertRaises((ui.DisplayRefusal, RuntimeError)):
                    adapter(page)
                self.assertEqual(inputs.calls, 0)
                self.assertFalse(any(e["event"] in ("commit", "arm", "consume") for e in trace.events))
                if scenario == "draw-partial":
                    self.assertTrue(any(e["event"] == "draw" and e["role"] == "label" for e in trace.events))


class Events(unittest.TestCase):
    def test_fresh_full_draw_precedes_single_consumption(self):
        adapter, trace = setup()
        self.assertEqual(adapter(Page()), 0)
        self.assertEqual(adapter(Page(kind=1, index=30, position=b"31/31")), 1)
        for epoch in (1, 2):
            group = [e["event"] for e in trace.events if e.get("epoch") == epoch]
            self.assertEqual(group[:3], ["enter", "baseline", "fit"])
            self.assertEqual(group[-4:], ["commit", "arm", "input", "consume"])
            self.assertTrue(all(x == "draw" for x in group[3:-4]))
        self.assertEqual(len(adapter.used), 2)

    def test_preheld_and_queued_refuse_before_draw(self):
        for scenario in ("preheld", "queued"):
            with self.subTest(scenario=scenario):
                adapter, trace = setup(scenario=scenario)
                with self.assertRaises(ui.DisplayRefusal):
                    adapter(Page())
                self.assertFalse(any(e["event"] in ("draw", "commit", "input", "consume") for e in trace.events))

    def test_stale_page_and_duplicate_cannot_advance(self):
        for scenario in ("stale-page", "duplicate-event"):
            with self.subTest(scenario=scenario):
                adapter, trace = setup(scenario=scenario)
                self.assertEqual(adapter(Page()), 0)
                with self.assertRaises(ui.DisplayRefusal):
                    adapter(Page(index=1, position=b"2/31"))
                self.assertEqual(len([e for e in trace.events if e["event"] == "consume"]), 1)

    def test_simultaneous_and_unsupported_actions_refuse(self):
        for scenario in ("simultaneous", "back-refused", "none-refused", "bool-refused", "unknown-refused"):
            with self.subTest(scenario=scenario):
                adapter, trace = setup(scenario=scenario)
                with self.assertRaises(ui.DisplayRefusal):
                    adapter(Page(kind=1, index=30) if scenario == "simultaneous" else Page())
                self.assertFalse(any(e["event"] == "consume" for e in trace.events))

    def test_incomplete_cycle_is_not_fresh(self):
        inputs = Input()
        inputs.override = lambda invocation, epoch, _page: ui.Cycle(invocation, epoch, 1, ("approve",), ("neutral", "press"))
        adapter, trace = setup(inputs)
        with self.assertRaises(ui.DisplayRefusal):
            adapter(Page(kind=1, index=30))
        self.assertFalse(adapter.used)

    def test_redisplay_and_new_request_require_new_event(self):
        inputs = Input()
        first, _trace = setup(inputs)
        self.assertEqual(first(Page()), 0)
        old = inputs.previous
        inputs.override = lambda *_args: old
        with self.assertRaises(ui.DisplayRefusal):
            first(Page())  # Same tuple, a different presentation epoch.
        inputs.override = None
        self.assertEqual(first(Page()), 0)
        second, _trace = setup(inputs)
        inputs.override = lambda *_args: old
        with self.assertRaises(ui.DisplayRefusal):
            second(Page())  # A new native fixture invocation has different local state.
        inputs.override = None
        self.assertEqual(second(Page()), 0)

    def test_wrong_phase_actions_are_passed_to_rust_not_authorized_here(self):
        adapter, _trace = setup(scenario="approve-data")
        self.assertEqual(adapter(Page()), 1)
        adapter, _trace = setup(scenario="next-decision")
        self.assertEqual(adapter(Page(kind=1, index=30)), 0)
        # These numeric outputs are not native authorization/status evidence.

    def test_input_exception_and_baseexception_do_not_consume(self):
        for scenario, error in (("input-error", RuntimeError), ("input-baseexception", KeyboardInterrupt)):
            adapter, trace = setup(scenario=scenario)
            with self.assertRaises(error):
                adapter(Page())
            self.assertTrue(any(e["event"] == "commit" for e in trace.events))
            self.assertFalse(adapter.used)

    def test_trace_overflow_refuses_before_retaining(self):
        trace = ui.Trace()
        with self.assertRaises(ui.DisplayRefusal):
            trace.add("overflow", text="x" * ui.TRACE_CAP)
        self.assertEqual(trace.events, [])


class Configuration(unittest.TestCase):
    def test_exact_source_bound_config_and_closed_mutations(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder).resolve()
            config = directory / "synthetic-inspection-config.json"
            value = {"v": 1, "scope": ui.SCOPE, "scenario": "basic-fresh",
                     "callback_source_sha256": ui.sha(Path(ui.__file__).read_bytes()),
                     "trace_path": str(directory / "inspection-trace.json")}
            def load(candidate):
                raw = (json.dumps(candidate) + "\n").encode()
                config.write_bytes(raw)
                return ui.load_config(str(config), ui.sha(raw))
            self.assertEqual(load(value)[0], value)
            mutations = [{**value, "v": True}, {**value, "scenario": "physical"},
                         {**value, "callback_source_sha256": "0" * 64},
                         {**value, "trace_path": str(directory.parent / "escape.json")},
                         {**value, "module": "arbitrary"}, {**value, "scope": None}]
            for candidate in mutations:
                with self.subTest(candidate=candidate), self.assertRaises(ui.DisplayRefusal):
                    load(candidate)
            raw = json.dumps(value).replace('"v": 1', '"v": 1, "v": 1').encode()
            config.write_bytes(raw)
            with self.assertRaises(ui.DisplayRefusal):
                ui.load_config(str(config), ui.sha(raw))
            load(value)
            alias = directory / "alias.json"
            alias.symlink_to(config)
            with self.assertRaises(ui.DisplayRefusal):
                ui.load_config(str(alias), ui.sha(config.read_bytes()))
            (directory / "inspection-trace.json").write_bytes(b"existing")
            with self.assertRaises(ui.DisplayRefusal):
                load(value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
