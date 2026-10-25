"""Opt-in synthetic cell/input fixture. No GPIO, font, display or consent claim.

The Rust owner retains every semantic/currentness/authorization decision. Local
epochs below associate synthetic draw calls and events; they are not FFI handles.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import time

SCOPE = "QP01_SYNTHETIC_INSPECTION_V1"
CONFIG_ENV = "NSEALR_QP01_SYNTHETIC_INSPECTION_CONFIG"
HASH_ENV = "NSEALR_QP01_SYNTHETIC_INSPECTION_CONFIG_SHA256"
TRACE_CAP = 131072
SCENARIOS = (
    "basic-fresh", "reject-data", "reject-decision", "approve-data", "next-decision",
    "draw-before", "draw-partial", "draw-decision", "presenter-error",
    "input-error", "input-baseexception", "preheld", "queued", "stale-page",
    "duplicate-event", "simultaneous", "back-refused", "none-refused",
    "bool-refused", "unknown-refused", "cancel-after-commit", "clock-unavailable",
)
EXPECTED_STATUS = {name: -6 for name in SCENARIOS}
EXPECTED_STATUS.update({"basic-fresh": 0, "reject-data": -5, "reject-decision": -5,
                        "approve-data": -9, "next-decision": -9,
                        "cancel-after-commit": -11, "clock-unavailable": -7})


class DisplayRefusal(ValueError):
    pass


def require(value, reason):
    if not value:
        raise DisplayRefusal(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate config key")
        result[key] = value
    return result


def load_config(path, digest):
    """Validate only the literal callback/config/output, before native readiness."""
    require(type(path) is str and Path(path).is_absolute(), "absolute config")
    config_path = Path(path)
    require(config_path.resolve(strict=True) == config_path and config_path.is_file(), "regular non-symlink config")
    require(config_path.name == "synthetic-inspection-config.json", "fixed config name")
    with config_path.open("rb") as stream:
        raw = stream.read(4097)
    require(len(raw) <= 4096 and raw.isascii() and type(digest) is str and sha(raw) == digest, "config bytes/hash")
    value = json.loads(raw, object_pairs_hook=_pairs)
    require(type(value) is dict and list(value) == ["v", "scope", "scenario", "callback_source_sha256", "trace_path"], "config shape")
    require(type(value["v"]) is int and value["v"] == 1 and value["scope"] == SCOPE, "config version/scope")
    require(type(value["scenario"]) is str and value["scenario"] in SCENARIOS, "fixed synthetic selector")
    require(value["callback_source_sha256"] == sha(Path(__file__).read_bytes()), "callback source hash")
    trace = config_path.parent / "inspection-trace.json"
    require(type(value["trace_path"]) is str and value["trace_path"] == str(trace), "fixed trace sibling")
    require(not trace.exists() and not trace.is_symlink(), "trace must be absent")
    return value, sha(raw)


class Trace:
    def __init__(self):
        self.events = []
        self.retained = 2

    def add(self, event, **fields):
        row = {"seq": len(self.events), "event": event, **fields}
        size = len(json.dumps(row, ensure_ascii=True, separators=(",", ":")).encode("ascii")) + 1
        require(self.retained + size <= TRACE_CAP - 8192, "trace cap before retain")
        self.events.append(row)
        self.retained += size


def plan(page, width=240, height=240):
    """Whole-frame preflight; returned calls contain full text, never clipping."""
    require(type(width) is int and type(height) is int and (width, height) == (240, 240), "trusted viewport")
    require(type(page.kind) is int and page.kind in (0, 1), "kind")
    require(type(page.index) is int and type(page.total) is int and 0 <= page.index < page.total <= 1024, "page identity")
    fields = (("label", page.label), ("body", page.body), ("position", page.position))
    lines = []
    for role, raw in fields:
        require(type(raw) is bytes and all(byte == 10 or 32 <= byte <= 126 for byte in raw), "printable ASCII/LF bytes")
        for line in raw.split(b"\n"):
            require(len(line) <= 32 and len(lines) < 8, "32x8 whole-frame fit")
            lines.append((role, line))
    header = f"kind={page.kind} index={page.index} total={page.total}"
    footer = "NEXT/REJECT" if page.kind == 0 else "APPROVE/REJECT"
    require(len(header) * 6 <= width - 48 and len(footer) * 6 <= width - 48, "header/footer fit")
    # Only fully validated fields reach decoding, commands or retained diagnostics.
    commands = [{"role": role, "text": line.decode("ascii"), "x": 24, "y": 48 + index * 16,
                 "width": len(line) * 6, "height": 8} for index, (role, line) in enumerate(lines)]
    commands = [{"role": "header", "text": header, "x": 24, "y": 16,
                 "width": len(header) * 6, "height": 8}, *commands,
                {"role": "footer", "text": footer, "x": 24, "y": 208,
                 "width": len(footer) * 6, "height": 8}]
    for row in commands:
        require(row["x"] + row["width"] <= width - 24 and row["y"] + row["height"] <= height - 24,
                "glyph ink bounds")
    return commands


@dataclass(frozen=True)
class Cycle:
    invocation: object
    epoch: int
    serial: int
    actions: tuple
    states: tuple = ("neutral", "press", "release")


class CellSink:
    """Synthetic draw-call recorder with fixed 6x8 glyph metrics, no glyph raster."""
    def __init__(self, trace, scenario="basic-fresh"):
        self.trace = trace
        self.scenario = scenario

    def draw(self, epoch, page, command):
        if (self.scenario == "draw-before" and page.index == 0 or
                self.scenario == "draw-partial" and page.index == 0 and command["role"] == "body" or
                self.scenario == "draw-decision" and page.kind == 1):
            raise DisplayRefusal("injected synthetic draw fault")
        self.trace.add("draw", epoch=epoch, **command)

    def commit(self, epoch):
        if self.scenario == "presenter-error":
            raise RuntimeError("injected synthetic presenter exception")
        self.trace.add("commit", epoch=epoch)


class ScenarioInput:
    """Fixed synthetic scripts. Input is produced when requested, after commit."""
    def __init__(self, scenario):
        require(scenario in SCENARIOS, "synthetic scenario")
        self.scenario = scenario
        self.previous = None
        self.serial = 0

    def baseline(self, page):
        return (("approve",) if self.scenario == "preheld" and page.index == 0 else (),
                1 if self.scenario == "queued" and page.index == 0 else 0)

    def acquire(self, invocation, epoch, page):
        if self.scenario == "input-error":
            raise RuntimeError("injected synthetic input exception")
        if self.scenario == "input-baseexception":
            raise KeyboardInterrupt("injected synthetic input BaseException")
        self.serial += 1
        action = "approve" if page.kind == 1 else "next"
        if self.scenario == "reject-data" and page.index == 0 or self.scenario == "reject-decision" and page.kind == 1:
            action = "reject"
        if self.scenario == "approve-data" and page.index == 0:
            action = "approve"
        if self.scenario == "next-decision" and page.kind == 1:
            action = "next"
        special = {"back-refused": "back", "none-refused": None,
                   "bool-refused": True, "unknown-refused": 99}
        if self.scenario in special:
            action = special[self.scenario]
        if self.scenario == "duplicate-event" and page.index == 1:
            return self.previous
        cycle = Cycle(invocation, epoch - 1 if self.scenario == "stale-page" and page.index == 1 else epoch,
                      self.serial, ("approve", "reject") if self.scenario == "simultaneous" and page.kind == 1 else (action,))
        self.previous = cycle
        return cycle


class InspectionIo:
    def __init__(self, sink, inputs, trace):
        self.sink, self.inputs, self.trace = sink, inputs, trace
        self.invocation = object()
        self.epoch = 0
        self.used = set()
        self.cancelled = False
        self.callback_returned = False

    def __call__(self, page):
        self.epoch += 1
        epoch = self.epoch
        try:
            commands = plan(page)
            self.trace.add("enter", epoch=epoch, page={"kind": page.kind, "index": page.index, "total": page.total,
                           "label": page.label.decode("ascii"), "body": page.body.decode("ascii"),
                           "position": page.position.decode("ascii")})
            pressed, queued = self.inputs.baseline(page)
            self.trace.add("baseline", epoch=epoch, pressed=list(pressed), queued=queued)
            require(not pressed and type(queued) is int and queued == 0, "preheld/queued input")
            self.trace.add("fit", epoch=epoch, command_count=len(commands), glyph_width=6, glyph_height=8)
            for command in commands:
                self.sink.draw(epoch, page, command)
            self.sink.commit(epoch)
            self.trace.add("arm", epoch=epoch)
            if self.inputs.scenario == "cancel-after-commit" and page.index == 0:
                self.cancelled = True
            cycle = self.inputs.acquire(self.invocation, epoch, page)
            require(type(cycle) is Cycle, "actual local cycle")
            self.trace.add("input", epoch=epoch, invocation_match=cycle.invocation is self.invocation,
                           event_epoch=cycle.epoch, serial=cycle.serial, states=list(cycle.states), actions=list(cycle.actions))
            require(cycle.invocation is self.invocation and type(cycle.epoch) is int and cycle.epoch == epoch,
                    "stale invocation/presentation")
            require(type(cycle.serial) is int and cycle.serial > 0 and cycle.serial not in self.used, "duplicate event")
            require(cycle.states == ("neutral", "press", "release") and len(cycle.actions) == 1, "fresh single cycle")
            action = cycle.actions[0]
            require(type(action) is str and action in ("next", "approve", "reject"), "scoped action")
            self.used.add(cycle.serial)
            result = {"next": 0, "approve": 1, "reject": 2}[action]
            self.trace.add("consume", epoch=epoch, serial=cycle.serial, action=result)
            self.callback_returned = True
            return result
        except BaseException as error:
            self.trace.add("display_error", epoch=epoch, error=type(error).__name__, reason=str(error)[:160])
            raise


class Fixture:
    def __init__(self, config, config_sha, raw, real_clock):
        self.config, self.config_sha, self.raw, self.real_clock = config, config_sha, raw, real_clock
        self.trace = Trace()
        self.io = InspectionIo(CellSink(self.trace, config["scenario"]), ScenarioInput(config["scenario"]), self.trace)

    def clock(self):
        if self.config["scenario"] == "clock-unavailable" and self.io.callback_returned:
            self.trace.add("clock_unavailable", source="explicit_fault_injection")
            raise RuntimeError("injected unavailable clock")
        tick = self.real_clock()
        self.trace.add("clock", source="MonotonicSeconds", tick=tick, observed_monotonic_ns=str(time.monotonic_ns()))
        return tick

    def cancel(self):
        value = self.io.cancelled
        self.trace.add("cancel_sample", value=value)
        return value

    def auxiliary(self):
        self.trace.add("auxiliary_callback_enter", role="explicit_public_fixture_zeroaux")
        return bytes(32)

    def finish(self, status, output, library, library_sha):
        document = {"v": 1, "scope": SCOPE, "scenario": self.config["scenario"],
                    "callback_source_sha256": self.config["callback_source_sha256"], "config_sha256": self.config_sha,
                    "input_bytes": len(self.raw), "input_sha256": sha(self.raw),
                    "library": str(library), "library_sha256": library_sha,
                    "native_status": status, "output_bytes": len(output), "output_sha256": sha(output) if output else None,
                    "events": self.trace.events, "claim": "synthetic_cell_draw_and_input_only_no_physical_consent"}
        raw = (json.dumps(document, ensure_ascii=True, separators=(",", ":")) + "\n").encode("ascii")
        require(len(raw) <= TRACE_CAP, "final trace cap")
        fd = os.open(self.config["trace_path"], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            require(stream.write(raw) == len(raw), "complete trace write before output")
        return {"scope": SCOPE, "scenario": self.config["scenario"], "config_sha256": self.config_sha,
                "callback_source_sha256": self.config["callback_source_sha256"],
                "trace_sha256": sha(raw), "native_status": status}
