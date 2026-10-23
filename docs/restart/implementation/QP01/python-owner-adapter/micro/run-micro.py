#!/usr/bin/env python3
"""One admitted real worker-only positive. An uncertain owner is never killed."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import traceback
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "apps/pi/app"))
from nsealr_vault.qr_owner_adapter import RgbOwnerRuntime
from nsealr_vault.qr_worker import live_fds


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*argv):
    return subprocess.check_output(["git", *argv], cwd=ROOT, text=True).strip()


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def fd_record(path):
    stat = os.stat(path)
    return {"dev": str(stat.st_dev), "ino": str(stat.st_ino), "target": os.readlink(path)}


def wait_for(op, wanted, output):
    until = time.monotonic() + 20
    while True:
        state = op.poll(50)
        if state == wanted:
            return
        require(state not in ("quarantined", "settled"), f"unexpected state {state}: {op.observation()}")
        if time.monotonic() >= until:
            write(output / "attention.json", op.observation())
            print("OBSERVATION EXPIRED: retaining exact live runtime/owner; no watchdog kill", flush=True)
            # Keep owning runtime/frame/child references, never restart the run.
            while True:
                op.poll(50)


def main():
    output = Path(sys.argv[1]).resolve()
    require(not output.exists(), "fresh output directory required")
    output.mkdir(parents=True)
    require(len(sys.argv) == 3 and git("rev-parse", "HEAD") == sys.argv[2], "exact frozen HEAD")
    require(git("status", "--porcelain", "--untracked-files=all") == "", "source must start clean")
    require("CARGO_TARGET_DIR" not in os.environ and "CARGO_BUILD_TARGET" not in os.environ,
            "no target override may mask the actual default")
    inputs = json.loads(Path(__file__).with_name("inputs.json").read_text())
    for row in inputs["source_bindings"]:
        data = (ROOT / row["path"]).read_bytes()
        require(len(data) == row["bytes"] and sha(data) == row["sha256"], row["path"])
    image = (ROOT / inputs["image"]["path"]).read_bytes()
    expected = (ROOT / inputs["expected"]["path"]).read_bytes()
    require(len(image) == 172800 and sha(image) == inputs["image"]["sha256"], "frozen RGB")
    require(len(expected) == 259 and sha(expected) == inputs["expected"]["sha256"], "frozen envelope")
    vector = json.loads((ROOT / inputs["transport_vector"]).read_text())
    require(vector["envelope"].encode("ascii") == expected and
            type(vector["decoded"]["version"]) is int and vector["decoded"]["version"] == 2,
            "independent original transport vector/version2")
    target = ROOT / "apps/pi/qr-worker/target"
    require(not target.exists(), "fresh actual default target required")
    ignored = git("-c", "core.excludesFile=/dev/null", "check-ignore", "--no-index", "-v", "--",
                  "apps/pi/qr-worker/target/release/nsealr-qr-worker")
    cargo_home = output / "cargo-home"
    cargo_home.mkdir()
    os.environ["CARGO_HOME"] = str(cargo_home)
    command = ["cargo", "build", "--manifest-path", "apps/pi/qr-worker/Cargo.toml", "--locked",
               "--offline", "--release", "--message-format=json"]
    versions = {name: subprocess.check_output(argv, cwd=ROOT, text=True).strip() for name, argv in
                (("rustc", ["rustc", "--version"]), ("cargo", ["cargo", "--version"]))}
    require(versions["rustc"].startswith("rustc 1.95.0 "), "pinned Rust1.95.0")
    write(output / "command.json", {"argv": sys.argv, "cwd": str(ROOT), "head": git("rev-parse", "HEAD"),
          "tree": git("rev-parse", "HEAD^{tree}"), "source_status_before": "", "build": command,
          "CARGO_HOME": str(cargo_home), "CARGO_TARGET_DIR": None, "CARGO_BUILD_TARGET": None,
          "actual_default_target": str(target), "declared_ignore": ignored, "versions": versions,
          "python": sys.version, "python_executable": sys.executable,
          "python_sha256": sha(Path(sys.executable).read_bytes()),
          "role": "ONE host O/W positive only; no Node/C/signature/physical result"})
    producer_path = ROOT / "docs/restart/implementation/QP01/request-engine/exchange.py"
    spec = importlib.util.spec_from_file_location("existing_worker_producer", producer_path)
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)

    def record_actual_build(argv, **kwargs):
        # Transparent recording of the existing producer's actual Cargo call.
        try:
            result = subprocess.run(argv, **kwargs)
        except subprocess.CalledProcessError as error:
            (output / "cargo-messages.jsonl").write_text(error.stdout or "")
            raise
        (output / "cargo-messages.jsonl").write_text(result.stdout)
        return result

    producer.subprocess = SimpleNamespace(run=record_actual_build, PIPE=subprocess.PIPE)
    paths = ["apps/pi/qr-worker/" + p for p in ("Cargo.toml", "Cargo.lock", "src/main.rs", "rust-toolchain.toml")]
    paths += [".cargo/config.toml", "rust-toolchain.toml"]
    worker, digest, bindings = producer.build_artifact(command, ROOT / "apps/pi/qr-worker/src/main.rs",
                 ROOT / "apps/pi/qr-worker/Cargo.toml", "nsealr-qr-worker", "bin", paths)
    require(worker == target / "release/nsealr-qr-worker", "actual default executable path")
    write(output / "artifact.json", {"worker": str(worker), "sha256": digest,
          "bytes": worker.stat().st_size, "source_binding": bindings,
          "producer_sha256": sha(producer_path.read_bytes()), "default_target_was_absent": True})

    sentinels = [os.pipe2(os.O_CLOEXEC) for _ in range(2)]
    require({3, 4, 5}.issubset({fd for pair in sentinels for fd in pair}), "actual live parent3/4/5")
    for _read, writefd in sentinels:
        os.write(writefd, b"parent-preserved")
    parent_before = {str(fd): {**fd_record(f"/proc/self/fd/{fd}"), "inheritable": os.get_inheritable(fd)}
                     for fd in (3, 4, 5)}
    baseline_fds = live_fds()
    stop = threading.Event()
    unrelated = threading.Thread(target=stop.wait, name="unrelated-live-library-thread")
    unrelated.start()
    runtime = RgbOwnerRuntime()
    op = runtime.reserve(str(worker), digest)
    try:
        op.open()
        wait_for(op, "owner-ready", output)
        observation = op.observation()
        owner = observation["owner_pid"]
        child_fds = {name: fd_record(f"/proc/{owner}/fd/{name}")
                     for name in os.listdir(f"/proc/{owner}/fd")}
        for expected_pipe in observation["pipe_identities"]:
            fd = str(expected_pipe["fd"])
            if fd == "4":
                require(fd not in child_fds and observation["ready_hex"] == "52" and
                        4 in observation["EOF"], "fd4 wrote R and closed")
            else:
                require(child_fds[fd] == {k: expected_pipe[k] for k in ("dev", "ino", "target")},
                        "actual child-only mapping")
        write(output / "owner-ready.json", {"observation": observation, "actual_proc_fds": child_fds,
              "parent_live_before": parent_before, "unrelated_thread_alive": unrelated.is_alive()})
        require(unrelated.is_alive(), "no globally single-threaded process assumption")
        op.start(image)
        wait_for(op, "verified-worker-ready", output)
        phase = op.observation()["phase"]
        worker_pid = phase["worker_pid"]
        actual_worker_fds = {name: fd_record(f"/proc/{worker_pid}/fd/{name}")
                             for name in os.listdir(f"/proc/{worker_pid}/fd")}
        require(set(actual_worker_fds) == {"0", "1", "2"}, "actual W fd hygiene")
        for fd in phase["fds"]:
            require(actual_worker_fds[str(fd["fd"])] == {k: fd[k] for k in ("dev", "ino", "target")},
                    "actual W pipe identities")
        require(sha(Path(f"/proc/{worker_pid}/exe").read_bytes()) == digest, "actual live W ELF")
        write(output / "worker-ready.json", {"observation": op.observation(),
              "actual_proc_fds": actual_worker_fds,
              "actual_status": Path(f"/proc/{worker_pid}/status").read_text(),
              "actual_limits": Path(f"/proc/{worker_pid}/limits").read_text()})
        op.acknowledge()
        wait_for(op, "settled", output)
        raw, parsed = op.take_result()
        require(raw == expected and parsed == vector["decoded"], "independent actual frame and framing")
        observation = op.observation()
        require(observation["commands"] == ["P", "G"] and observation["owner_wait_raw"] == 0
                and observation["owner_exit_code"] == 0 and observation["parent_owned_fds"] == [],
                "actual O collection/FD closure")
        (output / "decoded.envelope").write_bytes(raw)
        (output / "status-wire.jsonl").write_bytes(base64.b64decode(observation["status_wire_base64"]))
        write(output / "settlement.json", observation)
        op.close()
        require(runtime.operation is op and live_fds() == baseline_fds, "retained runtime; FD baseline restored")
        parent_after = {str(fd): {**fd_record(f"/proc/self/fd/{fd}"), "inheritable": os.get_inheritable(fd)}
                        for fd in (3, 4, 5)}
        require(parent_after == parent_before, "parent3/4/5 unchanged")
        for readfd, _write in sentinels:
            require(os.read(readfd, 16) == b"parent-preserved", "parent sentinel content preserved")
        try:
            os.wait4(owner, os.WNOHANG)
        except ChildProcessError:
            already_collected = True
        else:
            already_collected = False
        require(already_collected, "O already actually collected, not wait-status default")
        after = git("status", "--porcelain", "--untracked-files=all")
        require(after == "", "source clean after real default build/runtime")
        write(output / "result.json", {"status": "PASS_ONE_REAL_HOST_OW_POSITIVE_ONLY", "owner_pid": owner,
              "worker_pid": worker_pid, "worker_sha256": digest, "image_bytes": len(image),
              "image_sha256": sha(image), "decoded_bytes": len(raw), "decoded_sha256": sha(raw),
              "numeric_version": parsed["version"], "parent_live_after": parent_after,
              "parent_sentinel_content_preserved": True, "fd_baseline_restored": True,
              "O_already_collected_ECHILD": already_collected, "source_status_after": after,
              "runtime_strong_reference": runtime.operation is op, "unrelated_thread_alive": unrelated.is_alive(),
              "native_C_count": 0, "Node_count": 0, "no_physical_or_production_claim": True})
        print(json.dumps({"status": "PASS_ONE_REAL_HOST_OW_POSITIVE_ONLY", "output": str(output),
                          "O": owner, "W": worker_pid, "worker_sha256": digest}), flush=True)
    except BaseException:
        write(output / "failure.json", {"traceback": traceback.format_exc(), "observation": op.observation()})
        op.cancel()
        while op.state not in ("settled", "quarantined"):
            op.poll(50)
        write(output / "failure-settlement.json", op.observation())
        if op.state == "quarantined":
            print("QUARANTINE: exact runtime/owner retained; notify root; do not kill/restart", flush=True)
            while True:
                time.sleep(1)
        raise
    finally:
        stop.set()
        unrelated.join()
        for pair in sentinels:
            for fd in pair:
                os.close(fd)


if __name__ == "__main__":
    main()
