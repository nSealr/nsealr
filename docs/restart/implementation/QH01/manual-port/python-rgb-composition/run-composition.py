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
        self.output.mkdir(parents=True, exist_ok=False)
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
        write(self.output / "attention.json", {"reason": reason,
              "parent_pid": os.getpid(), "node_pid": self.node.pid if self.node else None,
              "node_wait_raw": self.raw_wait, "node_EOF": sorted(self.eof),
              "B3": self.op.observation(), "runtime_strong_reference": self.runtime.operation is self.op})
        print("UNCERTAIN OWNERS RETAINED; exact invoker handle must remain live; notify root", flush=True)
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
            if owner_known and node_known:
                self.op.close()
                if self.selector is not None:
                    self.selector.close()
                return
            if time.monotonic() >= end:
                self.attention("cleanup observation expired; no owner killed")
            time.sleep(0.001)

    def run(self):
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
        try:
            self.node = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, close_fds=True)
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
            self.op.acknowledge()
            self.until(lambda: self.op.state == "settled", "actual O/W settlement")
            observation = self.op.observation()
            require(observation["owner_wait_raw"] == 0 and observation["owner_exit_code"] == 0, "actual O0 collection")
            require(observation["terminal"]["worker_wait"]["exit_code"] == 0 and observation["terminal"]["worker_wait"]["raw_status"] == 0, "actual W0 collection")
            require(observation["EOF"] == [1, 2, 4, 5] and observation["parent_owned_fds"] == [], "B3 EOF/FD closure")
            require(self.runtime.operation is self.op, "retained owning runtime")
            require({fd: fd_identity(int(fd)) for fd in parent_live} == parent_live, "caller live FDs unchanged")
            raw, parsed = self.op.take_result()
            require(raw == request_raw and parsed == vector["decoded"] and type(parsed["version"]) is int, "released raw/parsed request binding")
            (self.output / "decoded.envelope").write_bytes(raw)
            write(self.output / "decoded.json", parsed)
            write(self.output / "owner-settled.json", {"observation": self.op.observation(), "parent_live_preserved": parent_live})
            reply = (json.dumps({"v": 1, "event": "decoded", "frame": raw.decode("ascii")}, separators=(",", ":")) + "\n").encode("ascii")
            require(len(reply) <= 512, "reply cap")
            (self.output / "parent-reply.jsonl").write_bytes(reply)
            self.node.stdin.write(reply)
            self.node.stdin.close()
            self.reply_sent = True
            self.until(lambda: self.raw_wait is not None and self.eof == {"stdout", "stderr"}, "Node collection/EOF")
            require(self.raw_wait == 0 and self.node.returncode == 0 and not self.buffers["stderr"], "actual Node0 collection")
            require(not self.tail and len(self.rows) == 4, "exact four complete Node records")
            scan, close, result = self.rows[1:]
            _keys(scan, ["v", "event", "frame"])
            require(scan["v"] == 1 and scan["event"] == "scan" and scan["frame"].encode("ascii") == response_raw, "host scanner611 binding")
            _keys(close, ["v", "event"])
            require(close == {"v": 1, "event": "close"}, "actual port close")
            _keys(result, ["v", "event", "native_response_base64", "timer_args", "clear_calls", "deadline_fires", "clock_steps"])
            require(result["v"] == 1 and result["event"] == "result" and result["timer_args"] == [100]
                    and all(type(x) is int for x in result["timer_args"])
                    and type(result["clear_calls"]) is int and result["clear_calls"] == 1
                    and type(result["deadline_fires"]) is int and result["deadline_fires"] == 0
                    and result["clock_steps"] == [0, 99, 100]
                    and all(type(x) is int for x in result["clock_steps"]), "synthetic actual timer evidence")
            wire = base64.b64decode(result["native_response_base64"], validate=True)
            require(base64.b64encode(wire).decode("ascii") == result["native_response_base64"], "canonical native base64")
            require(len(wire) >= 4 and int.from_bytes(wire[:4], "little") == len(wire) - 4, "native response framing")
            service = json.loads(wire[4:])
            expected_response = json.loads((ROOT / "protocols/contracts/v1/examples/response-kind-1-basic.json").read_text())
            require(service["ok"] is True and service["request_id"] == "qh01.composition" and service["result"]["signer_response"] == expected_response, "actual client verified response")
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
        write(self.output / "result.json", result)
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "worker", "sha256", "node", "bridge", "reuse"):
        parser.add_argument("--" + name, required=True)
    Composition(parser.parse_args()).run()
