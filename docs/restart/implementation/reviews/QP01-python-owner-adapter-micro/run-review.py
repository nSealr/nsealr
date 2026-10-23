"""One independent replay of unchanged micro invoker with managed Python3.12.15."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CANDIDATE = "9bf83d998f16723abf4774f60e04ad75d22f8bab"
AUTHOR = ROOT / "docs/restart/implementation/QP01/python-owner-adapter/micro"
BASELINE = Path("/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final")
TOOLS = BASELINE / ".tools"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def require(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    runtime = HERE / ".runtime"
    require(not runtime.exists(), "one fresh reviewer runtime only")
    require(not (ROOT / "apps/pi/qr-worker/target").exists(), "fresh default target")
    require(not git("status", "--porcelain=v1", "--untracked-files=all"), "clean source")
    runtime.mkdir()
    inputs = json.loads((AUTHOR / "inputs.json").read_text())
    manifest = json.loads((AUTHOR / "artifact-manifest.json").read_text())
    for row in inputs["source_bindings"] + [inputs["image"], inputs["expected"]] + manifest["members"]:
        body = (ROOT / row["path"]).read_bytes()
        require(len(body) == row["bytes"] and sha(body) == row["sha256"], row["path"])
        require(body == git("show", CANDIDATE + ":" + row["path"]), "source correspondence")
    vendor = git("ls-tree", "-r", "--full-tree", "HEAD", "vendor/")
    require(vendor == git("ls-tree", "-r", "--full-tree", CANDIDATE, "vendor/"), "vendor identity")
    env = json.loads((BASELINE / "environment.json").read_text())
    for key in ("CARGO_TARGET_DIR", "CARGO_BUILD_TARGET", "PYTHONPATH", "PYTHONOPTIMIZE"):
        env.pop(key, None)
    env["PYTHONNOUSERSITE"] = "1"
    for key, name in (("XDG_CACHE_HOME", "cache"), ("XDG_CONFIG_HOME", "config"),
                      ("XDG_DATA_HOME", "data"), ("TMPDIR", "tmp")):
        path = runtime / name
        path.mkdir()
        env[key] = str(path)
    # CARGO_HOME is replaced by the unchanged micro invoker with its fresh local
    # directory before any Cargo call. Existing RUSTUP_HOME is read, not installed.
    python = TOOLS / "python/bin/python3"
    toolchain = TOOLS / "rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin"
    paths = {"python": python, "cargo": toolchain / "cargo", "rustc": toolchain / "rustc",
             "rustup": TOOLS / "cargo/bin/rustup", "cc": Path(shutil.which("cc", path=env["PATH"])),
             "ld": Path(shutil.which("ld", path=env["PATH"]))}
    tools = {name: {"path": str(path), "resolved": str(path.resolve()),
                    "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
             for name, path in paths.items()}
    prior = json.loads((ROOT / "docs/restart/implementation/reviews/QP01-owner-cold/tool-artifact-identities.json").read_text())
    for name in ("cargo", "rustc"):
        require(tools[name]["sha256"] == prior["tools"][name]["sha256"], "pinned tool " + name)
    version = subprocess.check_output([str(python), "--version"], env=env, text=True).strip()
    require(version == "Python 3.12.15", "managed Python3.12.15")
    head = git("rev-parse", "HEAD").decode().strip()
    argv = [str(python), "-B", str(AUTHOR / "run-micro.py"), str(runtime / "micro-01"), head]
    write(runtime / "preflight.json", {"candidate": CANDIDATE, "review_source": head,
          "review_tree": git("rev-parse", "HEAD^{tree}").decode().strip(),
          "input_bindings": len(inputs["source_bindings"]), "author_manifest_members": len(manifest["members"]),
          "image": inputs["image"], "expected": inputs["expected"],
          "vendor_entries": len(vendor.splitlines()), "vendor_listing_sha256": sha(vendor),
          "tools": tools, "python_version": version, "environment": env,
          "host": dict(platform.uname()._asdict()), "argv": argv,
          "default_target_initially_absent": True,
          "role": "One independent W-only build and O/W replay, no Node/C/negative matrix/Pi CI"})
    started = datetime.now(timezone.utc).isoformat()
    before = time.monotonic()
    with (runtime / "stdout.log").open("wb") as out, (runtime / "stderr.log").open("wb") as err:
        # No timeout/kill wrapper: unchanged invoker retains exact ownership if
        # attention/quarantine occurs. Root must be told, never silently retried.
        result = subprocess.run(argv, cwd=ROOT, env=env, stdout=out, stderr=err)
    write(runtime / "command.json", {"argv": argv, "cwd": str(ROOT), "started_utc": started,
          "ended_utc": datetime.now(timezone.utc).isoformat(), "seconds": time.monotonic() - before,
          "exit": result.returncode, "stdout_sha256": sha((runtime / "stdout.log").read_bytes()),
          "stderr_sha256": sha((runtime / "stderr.log").read_bytes()),
          "source_status_after": git("status", "--porcelain=v1", "--untracked-files=all").decode()})
    print(json.dumps({"exit": result.returncode, "runtime": str(runtime)}), flush=True)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
