#!/usr/bin/env python3
"""One fixed host diagnostic; this parent retains every uncertain owner."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "apps/pi/app"))
from nsealr_vault.qr_owner_adapter import RgbOwnerRuntime, _keys, _record
from nsealr_vault.qr_worker import live_fds
from nsealr_vault.synthetic_inspection import SCENARIOS, EXPECTED_STATUS, SCOPE, CONFIG_ENV, HASH_ENV, load_config


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def fd_identity(fd):
    stat = os.fstat(fd)
    return {"dev": str(stat.st_dev), "ino": str(stat.st_ino),
            "target": os.readlink(f"/proc/self/fd/{fd}"), "inheritable": os.get_inheritable(fd)}


class Composition:
    def __init__(self, args):
        self.args = args
        self.output = Path(args.output)
        self.output.mkdir(parents=True, exist_ok=False,
                          mode=0o700 if getattr(args, "case", "positive") == "fixture_request_engine" else 0o777)
        self.engine_initialization = None
        self.engine_environment = None
        self.inspection_config = None
        self.inspection_sources = None
        if getattr(args, "case", "positive") == "fixture_request_engine":
            self.engine_environment = dict(os.environ)  # Fixed before RGB/Node; never mutate process-global env.
            require(CONFIG_ENV not in self.engine_environment and HASH_ENV not in self.engine_environment,
                    "synthetic selector must come from explicit trusted CLI only")
            library = Path(args.engine_library).resolve(strict=True)
            module = Path(args.engine_module).resolve(strict=True)
            require(library.is_file() and sha(library.read_bytes()) == args.engine_sha256, "trusted actual native library SHA")
            require(module.is_file() and sha(module.read_bytes()) == args.engine_module_sha256, "trusted emitted native helper SHA")
            receipt = json.loads(Path(args.engine_preparation).read_text())
            source = "docs/restart/implementation/QP01/request-engine/native-leaf.ts"
            source_sha = sha((ROOT / source).read_bytes())
            _keys(receipt["source_before"], [source, "package.json", "pnpm-lock.yaml"])
            _keys(receipt["source_after"], [source, "package.json", "pnpm-lock.yaml"])
            _keys(receipt["outputs"], ["native-leaf.js", "native-leaf.d.ts"])
            for name, item in receipt["outputs"].items():
                artifact = Path(item["path"]).resolve(strict=True)
                require(artifact == module.parent / name and type(item["bytes"]) is int
                        and artifact.stat().st_size == item["bytes"] and sha(artifact.read_bytes()) == item["sha256"],
                        "complete current-root emitted helper artifacts")
            require(type(receipt["v"]) is int and receipt["v"] == 1 and receipt["scope"] == "QH01_NATIVE_LEAF_PREPARATION_V1"
                    and type(receipt["status"]) is int and receipt["status"] == 0 and receipt["cwd"] == str(ROOT)
                    and receipt["source_before"] == receipt["source_after"]
                    and receipt["source_before"][source] == source_sha
                    and Path(receipt["receipt"]).resolve() == Path(args.engine_preparation).resolve()
                    and Path(receipt["output_dir"]).resolve() == module.parent
                    and all(sha((ROOT / path).read_bytes()) == value for path, value in receipt["source_before"].items())
                    and Path(receipt["outputs"]["native-leaf.js"]["path"]).resolve() == module
                    and receipt["outputs"]["native-leaf.js"]["sha256"] == args.engine_module_sha256,
                    "current source-bound joined helper preparation")
            compiler = (ROOT / "node_modules/typescript/bin/tsc").resolve(strict=True)
            require(Path(receipt["compiler"]["path"]).resolve() == compiler and receipt["compiler"]["version"] == "6.0.3"
                    and json.loads((ROOT / "node_modules/typescript/package.json").read_text())["version"] == "6.0.3"
                    and sha(compiler.read_bytes()) == receipt["compiler"]["sha256"], "current pinned native helper compiler")
            require(Path(receipt["package_context"]["path"]).resolve() == module.parent / "package.json"
                    and sha((module.parent / "package.json").read_bytes()) == receipt["package_context"]["sha256"],
                    "native helper package context receipt")
            require(json.loads((module.parent / "package.json").read_text()) == {"type": "module"}, "helper ESM context")
            child_sha = args.engine_sha256
            if args.engine_refusal:
                child_sha = ("1" if child_sha[0] == "0" else "0") + child_sha[1:]
            self.engine_initialization = {"v": 1, "scope": "QH01_RGB_ENGINE_OPT_IN_V1",
                  "mode": "loaded-sha-refusal" if args.engine_refusal else "positive", "source_root": str(ROOT),
                  "output_dir": str(self.output.resolve()), "python": str(Path(sys.executable).absolute()),
                  "library": str(library), "library_sha256": args.engine_sha256, "child_expected_sha256": child_sha,
                  "module": str(module), "module_sha256": args.engine_module_sha256, "module_source_sha256": source_sha}
            if getattr(args, "synthetic_inspection", None):
                callback = ROOT / "apps/pi/app/nsealr_vault/synthetic_inspection.py"
                config_path = self.output.resolve() / "synthetic-inspection-config.json"
                self.inspection_config = {"v": 1, "scope": SCOPE, "scenario": args.synthetic_inspection,
                    "callback_source_sha256": sha(callback.read_bytes()),
                    "trace_path": str(self.output.resolve() / "inspection-trace.json")}
                write(config_path, self.inspection_config)
                config_sha = sha(config_path.read_bytes())
                load_config(str(config_path), config_sha)  # Same strict input before any actor.
                self.engine_initialization["mode"] = "synthetic-inspection"
                self.engine_initialization["synthetic_inspection"] = {"config": str(config_path), "sha256": config_sha,
                    "scenario": args.synthetic_inspection, "callback_source_sha256": self.inspection_config["callback_source_sha256"],
                    "expected_status": EXPECTED_STATUS[args.synthetic_inspection]}
                source_paths = ["apps/pi/app/nsealr_vault/" + name for name in ("synthetic_inspection.py", "engine_adapter.py")]
                source_paths += ["docs/restart/implementation/QP01/request-engine/" + name for name in ("exchange.py", "native-leaf.ts")]
                source_paths += [str(Path(__file__).relative_to(ROOT)),
                    str(Path(__file__).with_name("bridge-child.mjs").relative_to(ROOT)),
                    "crates/nsealr-pi-engine-fixture/src/lib.rs", "Cargo.lock"]
                self.inspection_sources = {name: sha((ROOT / name).read_bytes()) for name in source_paths}
                write(self.output / "inspection-source-before.json", self.inspection_sources)
            write(self.output / "engine-initialization.json", self.engine_initialization)
        self.baseline_fds = live_fds()
        self.runtime = RgbOwnerRuntime()
        self.op = self.runtime.reserve(args.worker, args.sha256)
        self.node = None
        self.selector = None
        self.raw_wait = None
        self.eof = set()
        self.observed = {"stdout": 0, "stderr": 0}
        self.buffers = {"stdout": bytearray(), "stderr": bytearray()}
        self.tail = bytearray()
        self.rows = []
        self.failure = None
        self.reply_sent = False

    def engine_receipt(self, name, cap):
        raw = (self.output / name).read_bytes()
        require(len(raw) <= cap, "bounded native artifact")
        return json.loads(raw)

    def engine_known(self):
        if self.engine_initialization is None or self.node is None:
            return True
        try:
            outcome = self.engine_receipt("engine-outcome.json", 16384)["qh01_engine_leaf_outcome"]
            require(outcome["scope"] == "QH01_RGB_ENGINE_OPT_IN_V1" and outcome["node_pid"] == self.node.pid,
                    "exact Node native owner")
            for name in ("spawned", "collected", "capability_calls"):
                require(type(outcome[name]) is int, "typed native ownership counters")
            if outcome["spawned"] == outcome["collected"] == outcome["capability_calls"] == 0:
                return outcome["spawn"] is None  # Actual guarded no-C path; never a fabricated PID/status.
            require(outcome["spawned"] == outcome["collected"] == outcome["capability_calls"] == 1, "one C owner collected")
            status = self.engine_receipt("engine-settlement.json", 2048)["qh01_engine_leaf_settlement"]
            _keys(status, ["pid", "code", "signal", "synthetic_handshake_control", "sent", "readiness_hex",
                           "stdout_bytes", "stderr_bytes", "overflow", "initialization_ns", "request_to_close_ns"])
            require(type(status["pid"]) is int and status["pid"] > 1 and status["pid"] == outcome["spawn"]["pid"],
                    "exact actual C identity")
            require((type(status["code"]) is int and status["signal"] is None)
                    or (status["code"] is None and type(status["signal"]) is str), "actual C code/signal, not raw wait")
            return True
        except (OSError, ValueError, KeyError, TypeError, RuntimeError):
            return False

    def record_node_wait(self):
        if self.node is not None and self.raw_wait is None:
            try:
                pid, raw, _usage = os.wait4(self.node.pid, os.WNOHANG)
            except ChildProcessError:
                self.attention("Node wait status unavailable; never substitute zero")
            if pid:
                require(pid == self.node.pid and (os.WIFEXITED(raw) or os.WIFSIGNALED(raw)), "exact terminal Node child wait")
                self.raw_wait = raw
                self.node.returncode = os.waitstatus_to_exitcode(raw)

    def pump(self, strict=True):
        if self.node is None:
            return
        for key, _event in self.selector.select(0):
            name = key.data
            data = os.read(key.fd, 4097)
            if not data:
                self.eof.add(name)
                self.selector.unregister(key.fileobj)
                key.fileobj.close()
                continue
            self.observed[name] += len(data)
            remaining = max(0, 4097 - len(self.buffers[name]))
            self.buffers[name].extend(data[:remaining])
            if strict:
                require(self.observed[name] <= 4096, f"Node {name} total cap")
                if name == "stdout":
                    self.tail.extend(data)
                    while b"\n" in self.tail:
                        end = self.tail.index(10) + 1
                        require(end <= 2048, "Node record cap")
                        row = _record(bytes(self.tail[:end]))
                        del self.tail[:end]
                        require(type(row) is dict and type(row.get("v")) is int and row["v"] == 1,
                                "typed v1 Node record")
                        require(len(self.rows) < 5, "Node record count")
                        self.rows.append(row)
                        write(self.output / "node-records.json", self.rows)
                        require(row.get("event") != "error", f"Node refused: {row}")
                    require(len(self.tail) < 2048, "Node partial record cap")
        self.record_node_wait()

    def attention(self, reason):
        # Diagnostic failure must never prevent entry into the ownership hold.
        # Keep these guards separate so either report can succeed independently.
        try:
            write(self.output / "attention.json", {"reason": reason,
                  "parent_pid": os.getpid(), "node_pid": self.node.pid if self.node else None,
                  "node_wait_raw": self.raw_wait, "node_EOF": sorted(self.eof),
                  "B3": self.op.observation(), "runtime_strong_reference": self.runtime.operation is self.op})
        except BaseException:
            pass
        try:
            print("UNCERTAIN OWNERS RETAINED; exact invoker handle must remain live; notify root", flush=True)
        except BaseException:
            pass
        while True:
            try:
                if self.op._child is not None:
                    self.op.poll(50)
                self.pump(strict=False)
            except Exception:
                pass
            time.sleep(0.1)

    def until(self, predicate, label):
        end = time.monotonic() + 20
        while True:
            if self.op._child is not None:
                self.op.poll(50)
            self.pump()
            if self.op.state == "quarantined":
                self.attention(f"B3 quarantine during {label}")
            if predicate():
                return
            if time.monotonic() >= end:
                self.attention(f"observation expired during {label}; not a cleanup proof")
            time.sleep(0.001)

    def cleanup(self):
        # Cooperative closure, actual collection and strong ownership on failure.
        if self.op._child is None:
            self.op.close()
        elif self.op.state != "settled":
            self.op.cancel()
        if self.node is not None and not self.node.stdin.closed:
            self.node.stdin.close()
        end = time.monotonic() + 20
        while True:
            if self.op._child is not None:
                self.op.poll(50)
            self.pump(strict=False)
            if self.op.state == "quarantined":
                self.attention("cleanup quarantine; no replacement or successful teardown")
            owner_known = self.op.state == "settled"
            node_known = self.node is None or (self.raw_wait is not None and self.eof == {"stdout", "stderr"})
            engine_known = node_known and self.engine_known()
            if owner_known and node_known and engine_known:
                self.op.close()
                if self.selector is not None:
                    self.selector.close()
                return
            if time.monotonic() >= end:
                self.attention("cleanup observation expired; no owner killed")
            time.sleep(0.001)

    def run(self):
        case = getattr(self.args, "case", "positive")
        cancelled = case == "fixture_cancel_B3_verified_preG"
        timed_out = case == "scan_pending_timeout_after_settlement"
        engine_case = case == "fixture_request_engine"
        engine_refusal = engine_case and self.args.engine_refusal
        inspection_refusal = self.inspection_config is not None and EXPECTED_STATUS[self.args.synthetic_inspection] != 0
        engine_failed = engine_refusal or inspection_refusal
        native = ROOT / "docs/restart/implementation/QH01/native-qr-probe"
        request_raw = (native / "expected/request-kind-1-basic.envelope").read_bytes()
        response_raw = (native / "expected/response-kind-1-basic.envelope").read_bytes()
        image = (native / "execution-01/request-kind-1-basic.rgb").read_bytes()
        vector = json.loads((ROOT / "protocols/contracts/v1/vectors/transports/qr-envelope-kind-1-basic.json").read_text())
        require(len(image) == 172800 and sha(image) == "64d9be602c821c31c0dfd6e952199a328325acdbf9a7e1b3494921942a11055f", "fixed RGB input")
        require(len(request_raw) == 259 and sha(request_raw) == "88a16190a1b1ed033fc9bebe5452af70e9a9783fd6b92305add2ac7134039ff7", "original request frame")
        require(len(response_raw) == 611 and sha(response_raw) == "f27dbe54785a9510e43f05d27dbb67c488c77def150e0110d51264762cdeec1b", "original scanner frame")
        baseline_fds = self.baseline_fds
        command = [self.args.node, str(Path(__file__).with_name("bridge-child.mjs")), str(ROOT), self.args.bridge, self.args.reuse]
        if case != "positive":
            command.append(case)
        if engine_case:
            command.append(str((self.output / "engine-initialization.json").resolve()))
        try:
            self.node = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, close_fds=True,
                                         **({"env": self.engine_environment} if engine_case else {}))
            self.selector = selectors.DefaultSelector()
            for name in ("stdout", "stderr"):
                stream = getattr(self.node, name)
                os.set_blocking(stream.fileno(), False)
                self.selector.register(stream, selectors.EVENT_READ, name)
            write(self.output / "invocation.json", {"command": command, "parent_pid": os.getpid(),
                  "node_pid": self.node.pid, "worker": self.args.worker, "worker_sha256": self.args.sha256})
            self.until(lambda: len(self.rows) >= 1, "present")
            present = self.rows[0]
            _keys(present, ["v", "event", "frame", "timer_args", "clock"])
            require(type(present["v"]) is int and present["v"] == 1 and present["event"] == "present", "present shape")
            require(present["frame"].encode("ascii") == request_raw and present["timer_args"] == [100]
                    and all(type(x) is int for x in present["timer_args"])
                    and type(present["clock"]) is int and present["clock"] == 99, "present request/clock binding")
            # B3 owns its own selector from reserve(); all other live descriptors
            # belong to this caller and must survive B3 settlement unchanged.
            adapter_selector = self.op._selector.fileno()
            parent_live = {str(fd): fd_identity(fd) for fd in live_fds() if fd != adapter_selector}
            self.op.open()
            self.until(lambda: self.op.state == "owner-ready", "owner ready")
            self.op.start(image)
            self.until(lambda: self.op.state == "verified-worker-ready", "verified worker phase")
            phase = self.op.observation()["phase"]
            worker_pid = phase["worker_pid"]
            require(sha(Path(f"/proc/{worker_pid}/exe").read_bytes()) == self.args.sha256, "actual live worker ELF")
            write(self.output / "worker-ready.json", {"observation": self.op.observation(),
                  "proc_status": Path(f"/proc/{worker_pid}/status").read_text(),
                  "proc_limits": Path(f"/proc/{worker_pid}/limits").read_text()})
            if cancelled:
                self.op.cancel()
            else:
                self.op.acknowledge()
            self.until(lambda: self.op.state == "settled", "actual O/W settlement")
            observation = self.op.observation()
            terminal = observation["terminal"]
            wait = terminal["worker_wait"]
            if cancelled:
                require(observation["owner_wait_raw"] == 512 and observation["owner_exit_code"] == 2,
                        "actual cancelled O2 collection")
                require((wait["exit_code"], wait["raw_status"]) in {(71, 18176), (-9, 9)}, "exact preG W collection")
                require(wait["collector_pid"] == observation["owner_pid"], "actual O collects W")
                require(terminal["outcome"] == "cancelled" and terminal["cancel_observed"] is True,
                        "actual fixture cancellation")
                require(observation["commands"] == ["P", "X"] and terminal["G_bytes"] == 0
                        and terminal["image_bytes_sent"] == 0 and terminal["result_bytes"] == 0
                        and observation["output_bytes"] == 0, "no G/W image/result exposure")
            else:
                require(observation["owner_wait_raw"] == 0 and observation["owner_exit_code"] == 0, "actual O0 collection")
                require(wait["exit_code"] == 0 and wait["raw_status"] == 0, "actual W0 collection")
            require(observation["EOF"] == [1, 2, 4, 5] and observation["parent_owned_fds"] == [], "B3 EOF/FD closure")
            require(self.runtime.operation is self.op, "retained owning runtime")
            require({fd: fd_identity(int(fd)) for fd in parent_live} == parent_live, "caller live FDs unchanged")
            if cancelled:
                try:
                    self.op.take_result()
                except ValueError:
                    pass
                else:
                    raise RuntimeError("cancelled operation released a result")
                try:
                    self.runtime.reserve(self.args.worker, self.args.sha256)
                except ValueError:
                    pass
                else:
                    raise RuntimeError("reservation reused before actual close")
                self.op.close()
                require(self.op._closed and self.runtime.operation is self.op, "known closed retained operation")
                write(self.output / "cancel-refusals.json", {"take_result_refused": True,
                      "reservation_before_close_refused": True, "caller_released_bytes": 0})
                reply_row = {"v": 1, "event": "cancelled"}
            else:
                raw, parsed = self.op.take_result()
                require(raw == request_raw and parsed == vector["decoded"] and type(parsed["version"]) is int, "released raw/parsed request binding")
                (self.output / "decoded.envelope").write_bytes(raw)
                write(self.output / "decoded.json", parsed)
                reply_row = {"v": 1, "event": "decoded", "frame": raw.decode("ascii")}
            write(self.output / "owner-settled.json", {"observation": self.op.observation(), "parent_live_preserved": parent_live})
            reply = (json.dumps(reply_row, separators=(",", ":")) + "\n").encode("ascii")
            require(len(reply) <= 512, "reply cap")
            if cancelled:
                require(reply == b'{"v":1,"event":"cancelled"}\n' and len(reply) == 28, "fixed cancelled reply")
            (self.output / "parent-reply.jsonl").write_bytes(reply)
            self.node.stdin.write(reply)
            self.node.stdin.close()
            self.reply_sent = True
            self.until(lambda: self.raw_wait is not None and self.eof == {"stdout", "stderr"}, "Node collection/EOF")
            require(self.raw_wait == 0 and self.node.returncode == 0 and not self.buffers["stderr"], "actual Node0 collection")
            require(not self.tail and len(self.rows) == (3 if cancelled or engine_failed else 5 if timed_out else 4), "exact complete case records")
            result = self.rows[-1]
            close = self.rows[-2]
            if timed_out:
                pending, timeout = self.rows[1:3]
                _keys(pending, ["v", "event", "clock"])
                require(pending["event"] == "scan_pending" and type(pending["clock"]) is int and pending["clock"] == 99, "actual pending scan at99")
                _keys(timeout, ["v", "event", "native_response_base64", "timer_args", "clear_calls", "deadline_fires", "clock",
                                "opens", "scans", "closes", "abort_observed", "underlying_settled", "pending_retry_error"])
                require(timeout["event"] == "timeout" and timeout["native_response_base64"] == result["native_response_base64"], "timeout response cannot be replaced")
                for name, value in {"clear_calls": 1, "deadline_fires": 1, "clock": 100, "opens": 1, "scans": 1, "closes": 0}.items():
                    require(type(timeout[name]) is int and timeout[name] == value, "typed timeout-stage counters")
                require(timeout["timer_args"] == [100] and timeout["abort_observed"] is True
                        and timeout["underlying_settled"] is False and timeout["pending_retry_error"] == "runtime_unavailable", "actual timeout before late settlement")
            elif not cancelled and not engine_failed:
                scan = self.rows[1]
                _keys(scan, ["v", "event", "frame"])
                require(scan["event"] == "scan", "single scan event")
                if case == "scan_null_after_settlement":
                    require(scan["frame"] is None, "actual null scan")
                elif engine_case:
                    produced = (self.output / "engine-response.envelope").read_bytes()
                    require(len(produced) == 611 and sha(produced) == "250167d1137f6da25676b00b62913a3d8f29391a1ff5331d64f7079d953f5ded"
                            and scan["frame"].encode("ascii") == produced, "actual C-produced scan611")
                else:
                    require(scan["frame"].encode("ascii") == response_raw, "host scanner611 binding")
            _keys(close, ["v", "event"])
            require(close == {"v": 1, "event": "close"}, "actual port close")
            result_keys = ["v", "event", "native_response_base64", "timer_args", "clear_calls", "deadline_fires", "clock_steps"]
            _keys(result, result_keys + (["engine"] if engine_case else [] if case == "positive" else ["lifecycle"]))
            require(result["v"] == 1 and result["event"] == "result" and result["timer_args"] == [100]
                    and all(type(x) is int for x in result["timer_args"])
                    and type(result["clear_calls"]) is int and result["clear_calls"] == 1
                    and type(result["deadline_fires"]) is int and result["deadline_fires"] == (1 if timed_out else 0)
                    and result["clock_steps"] == [0, 99, 100]
                    and all(type(x) is int for x in result["clock_steps"]), "synthetic actual timer evidence")
            wire = base64.b64decode(result["native_response_base64"], validate=True)
            require(base64.b64encode(wire).decode("ascii") == result["native_response_base64"], "canonical native base64")
            require(len(wire) >= 4 and int.from_bytes(wire[:4], "little") == len(wire) - 4, "native response framing")
            service = json.loads(wire[4:])
            expected_response = json.loads((ROOT / "protocols/contracts/v1/examples/response-kind-1-basic.json").read_text())
            require(service["request_id"] == "qh01.composition", "actual native response request binding")
            if case == "positive" or engine_case and not engine_failed:
                if engine_case:
                    expected = json.loads((ROOT / "docs/restart/implementation/QP01/request-engine/expectations.json").read_text())
                    expected_response["result"]["event"] = next(row for row in expected["independent_positive_expectations"] if row["id"] == "basic")["expected_complete_event"]
                require(service["ok"] is True and service["result"]["signer_response"] == expected_response, "actual client verified response")
            else:
                require(service["ok"] is False and "result" not in service
                        and service["error"]["code"] == ("signer_transport_timeout" if timed_out else "signer_transport_failed"), "exact native refusal")
                lifecycle = result.get("lifecycle")
            if case != "positive" and not engine_case:
                _keys(lifecycle, ["case", "opens", "scans", "closes", "abort_observed", "underlying_settled",
                                  "late_scan_bytes", "late_scan_sha256", "pending_retry_error"])
                require(lifecycle["case"] == case and lifecycle["abort_observed"] is True
                        and lifecycle["underlying_settled"] is True, "actual underlying settlement after refusal")
                for name, value in {"opens": 1, "scans": 0 if cancelled else 1, "closes": 1,
                                    "late_scan_bytes": 611 if timed_out else 0}.items():
                    require(type(lifecycle[name]) is int and lifecycle[name] == value, "typed lifecycle counters")
                require(lifecycle["late_scan_sha256"] == (sha(response_raw) if timed_out else None)
                        and lifecycle["pending_retry_error"] == ("runtime_unavailable" if timed_out else None), "late scan/retry binding")
            if engine_case:
                require(self.engine_known(), "known native C close before successful harness teardown")
                outcome = self.engine_receipt("engine-outcome.json", 16384)["qh01_engine_leaf_outcome"]
                status = self.engine_receipt("engine-settlement.json", 2048)["qh01_engine_leaf_settlement"]
                require(outcome["spawned"] == outcome["collected"] == outcome["capability_calls"] == 1
                        and outcome["timer_args"] == [5000] and outcome["timer_clears"] == 1
                        and outcome["children_before"] == outcome["children_after"] == ""
                        and outcome["fds_before"] == outcome["fds_after"], "actual C count/timer/Node FD accounting")
                require(status["code"] == (1 if engine_failed else 0) and status["signal"] is None
                        and status["sent"] is (not engine_refusal) and status["readiness_hex"] == ("" if engine_refusal else "52")
                        and status["stdout_bytes"] == (0 if engine_failed else 611) and status["overflow"] is False,
                        "actual native readiness/refusal and terminal status")
                require(type(outcome["response_bytes"]) is int and outcome["response_bytes"] == (0 if engine_failed else 611)
                        and type(outcome["observation_count"]) is int and outcome["observation_count"] == (0 if engine_failed else 1)
                        and outcome["readiness_refusal"] is engine_refusal
                        and outcome["response_sha256"] == (None if engine_failed else sha(produced)), "actual response artifact accounting")
                _keys(result["engine"], ["mode", "spawned", "collected", "capability_calls", "pid", "code", "signal",
                                         "timer_args", "timer_clears", "children_after", "fd_restored"])
                for name in ("spawned", "collected", "capability_calls", "timer_clears"):
                    require(type(result["engine"][name]) is int and type(outcome[name]) is int, "typed native counters")
                require(type(result["engine"]["pid"]) is int and type(result["engine"]["code"]) is int
                        and result["engine"]["fd_restored"] is True
                        and result["engine"] == {"mode": self.engine_initialization["mode"], "spawned": 1, "collected": 1,
                            "capability_calls": 1, "pid": status["pid"], "code": status["code"], "signal": status["signal"],
                            "timer_args": outcome["timer_args"], "timer_clears": outcome["timer_clears"],
                            "children_after": outcome["children_after"], "fd_restored": True}, "actual wire/artifact native binding")
                if engine_refusal:
                    require(not (self.output / "engine-observation.json").exists() and not (self.output / "engine-response.envelope").exists()
                            and outcome["observation_count"] == 0, "refused initialization sends no request/response")
                    refusal = self.engine_receipt("engine-refusal.json", 4096)["qh01_engine_leaf_refusal"]
                    require(type(refusal["message"]) is str and "native library SHA256 mismatch" in refusal["message"],
                            "actual loaded-SHA readiness refusal")
                elif inspection_refusal:
                    require(not (self.output / "engine-observation.json").exists()
                            and not (self.output / "engine-response.envelope").exists(), "synthetic UI refusal releases no frame")
                    require((self.output / "inspection-refusal-error.txt").stat().st_size <= 262144,
                            "actual bounded helper error retained")
                else:
                    trace = self.engine_receipt("engine-observation.json", 262144)["qh01_engine_leaf_observation"]
                    require(trace["sha256"] == self.args.engine_sha256 and trace["input_bytes"] == 259
                            and trace["input_sha256"] == sha(request_raw) and trace["output_bytes"] == 611
                            and trace["output_sha256"] == sha(produced), "real native input/output binding")
                    pages = trace["synthetic_complete_review"]
                    require(len(pages) == 31 and [p["index"] for p in pages] == list(range(31))
                            and all(p["total"] == 31 for p in pages) and [p["kind"] for p in pages] == [0] * 30 + [1],
                            "complete actual indexed basic Rust review")
                if self.inspection_config is not None:
                    ui = self.engine_receipt("inspection-trace.json", 131072)
                    expected_status = EXPECTED_STATUS[self.args.synthetic_inspection]
                    require(ui["scope"] == SCOPE and ui["scenario"] == self.args.synthetic_inspection
                            and type(ui["native_status"]) is int and ui["native_status"] == expected_status,
                            "actual synthetic callback native status")
                    require(ui["config_sha256"] == self.engine_initialization["synthetic_inspection"]["sha256"]
                            and ui["callback_source_sha256"] == self.inspection_config["callback_source_sha256"]
                            and ui["input_bytes"] == 259 and ui["input_sha256"] == sha(request_raw)
                            and ui["library_sha256"] == self.args.engine_sha256
                            and ui["output_bytes"] == (0 if inspection_refusal else 611)
                            and ui["output_sha256"] == (None if inspection_refusal else sha(produced)), "source/raw/native UI trace binding")
                    events = ui["events"]
                    require(type(events) is list and [event["seq"] for event in events] == list(range(len(events))), "actual event order")
                    clocks = [event for event in events if event["event"] == "clock"]
                    require(clocks and all(event["source"] == "MonotonicSeconds" and type(event["tick"]) is int
                            and type(event["observed_monotonic_ns"]) is str and event["observed_monotonic_ns"].isdigit() for event in clocks),
                            "actual real-clock observations")
                    entered = [event["page"] for event in events if event["event"] == "enter"]
                    aux = [event for event in events if event["event"] == "auxiliary_callback_enter"]
                    require(len(aux) == (0 if inspection_refusal else 1), "actual zeroaux callback entry count")
                    if not inspection_refusal:
                        require(entered == pages, "same actual Rust pages reached new callback")
                        for epoch in range(1, 32):
                            group = [event for event in events if event.get("epoch") == epoch]
                            labels = [event["event"] for event in group]
                            require(labels[0:3] == ["enter", "baseline", "fit"]
                                    and labels[-4:] == ["commit", "arm", "input", "consume"]
                                    and set(labels[3:-4]) == {"draw"}, "draw commit precedes one actual fresh event")
                            for role in ("label", "body", "position"):
                                drawn = "\n".join(event["text"] for event in group if event["event"] == "draw" and event["role"] == role)
                                require(drawn == entered[epoch - 1][role], "all indexed bytes drawn without clipping")
                    after = {name: sha((ROOT / name).read_bytes()) for name in self.inspection_sources}
                    require(after == self.inspection_sources, "synthetic fixture sources unchanged")
                    write(self.output / "inspection-source-after.json", after)
            (self.output / "native-response.bin").write_bytes(wire)
            write(self.output / "service-response.json", service)
        except BaseException as error:
            self.failure = {"type": type(error).__name__, "message": str(error)}
            write(self.output / "failure.json", self.failure)
        finally:
            try:
                self.cleanup()
            except BaseException as error:
                self.attention(f"cleanup property unavailable: {type(error).__name__}: {error}")
            (self.output / "node.stdout.jsonl").write_bytes(self.buffers["stdout"])
            (self.output / "node.stderr").write_bytes(self.buffers["stderr"])
            write(self.output / "collection.json", {"node_pid": self.node.pid if self.node else None,
                  "node_wait_raw": self.raw_wait, "node_EOF": sorted(self.eof), "node_observed": self.observed,
                  "B3": self.op.observation(), "runtime_strong_reference": self.runtime.operation is self.op,
                  "parent_fd_before": sorted(baseline_fds), "parent_fd_after": sorted(live_fds())})
        require(live_fds() == baseline_fds, "final parent FD restoration")
        if self.failure:
            raise RuntimeError(self.failure)
        # ECHILD is checked only after actual status collection above.
        for pid in (self.node.pid, self.op.observation()["owner_pid"]):
            try:
                os.wait4(pid, os.WNOHANG)
            except ChildProcessError:
                continue
            raise RuntimeError("known child unexpectedly waitable")
        result = {"result": "PASS_FIRST_HOST_COMPOSITION_ONLY", "parent_pid": os.getpid(),
                  "node_pid": self.node.pid, "owner_pid": self.op.observation()["owner_pid"],
                  "worker_pid": worker_pid, "worker_sha256": self.args.sha256,
                  "presented_bytes": 259, "decoded_bytes": 259, "scanned_bytes": 611,
                  "client_clock": "synthetic0/99/100; actual setTimeout argument100",
                  "O_clocks": "actual8s/shared4s unchanged", "physical_claim": False}
        if engine_case:
            result.update({"result": "PASS_FIRST_HOST_RGB_REQUEST_ENGINE_ONLY", "case": case,
                           "mode": self.engine_initialization["mode"], "scanned_bytes": 0 if engine_failed else 611,
                           "C_pid": status["pid"], "C_code": status["code"], "C_signal": status["signal"],
                           "C_scope": "Node-owned existing fixture leaf; code/signal/stdio-close, no raw wait",
                           "service_error": service.get("error", {}).get("code"), "caller_released_bytes": 259})
        elif case != "positive":
            result.update({"result": "PASS_HOST_COMPOSITION_LIFECYCLE_CASE", "case": case,
                           "decoded_bytes": 0 if cancelled else 259,
                           "scanned_bytes": 611 if timed_out else 0,
                           "service_error": service["error"]["code"],
                           "B3_outcome": self.op.observation()["terminal"]["outcome"],
                           "caller_released_bytes": 0 if cancelled else 259})
        if self.inspection_config is not None:
            result.update({"result": "PASS_HOST_SYNTHETIC_INSPECTION_ONLY", "scenario": self.args.synthetic_inspection,
                           "native_status": ui["native_status"], "trace_sha256": sha((self.output / "inspection-trace.json").read_bytes()),
                           "human_clock_property": "OPEN; no physical consent or human timing claim"})
        write(self.output / "result.json", result)
        print("\n" + json.dumps({"qp01_synthetic_inspection_result": result}) if self.inspection_config is not None else "\n" + json.dumps({"qh01_request_engine_result": result}) if engine_case else json.dumps(result) if case == "positive" else "\n" + json.dumps({"qh01_lifecycle_result": result}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "worker", "sha256", "node", "bridge", "reuse"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--case", choices=("positive", "scan_null_after_settlement",
                        "scan_pending_timeout_after_settlement", "fixture_cancel_B3_verified_preG", "fixture_request_engine"), default="positive")
    for name in ("engine-library", "engine-sha256", "engine-module", "engine-module-sha256", "engine-preparation"):
        parser.add_argument("--" + name)
    parser.add_argument("--engine-refusal", action="store_true")
    parser.add_argument("--synthetic-inspection", choices=SCENARIOS)
    args = parser.parse_args()
    if args.synthetic_inspection and (args.case != "fixture_request_engine" or args.engine_refusal):
        parser.error("synthetic inspection is exclusive to its trusted engine fixture")
    engine_fields = [args.engine_library, args.engine_sha256, args.engine_module, args.engine_module_sha256, args.engine_preparation]
    if args.case == "fixture_request_engine":
        if not all(engine_fields):
            parser.error("fixture_request_engine requires all explicit native initialization arguments")
    elif any(engine_fields) or args.engine_refusal:
        parser.error("native initialization/refusal is exclusive to fixture_request_engine")
    Composition(args).run()
