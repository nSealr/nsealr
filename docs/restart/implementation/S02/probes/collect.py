#!/usr/bin/env python3
"""Record S02 integration and exercised core-link evidence; no device execution."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(os.environ.get("NSEALR_S02_EVIDENCE_ROOT",
                          str(ROOT / "docs/restart/implementation/S02/evidence/integration"))).resolve()
OUT.mkdir(parents=True, exist_ok=True)
manifest = {
    "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "candidate_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "dirty_at_start": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True),
    "runs": [],
}


def run(name, command, env=None):
    print(f"{name}: starting", flush=True)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(command, cwd=ROOT, env=os.environ | (env or {}),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    log = OUT / f"{name}.log"
    log.write_text(result.stdout)
    row = {"name": name, "started_utc": started, "command": command,
           "cwd": str(ROOT), "env_overrides": env or {}, "exit_code": result.returncode,
           "log": str(log.relative_to(ROOT)),
           "sha256": hashlib.sha256(log.read_bytes()).hexdigest()}
    manifest["runs"].append(row)
    (OUT / "commands.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{name}: exit {result.returncode}", flush=True)
    return result


run("rustc", ["rustc", "-vV"])
run("cargo-tree-core", ["cargo", "tree", "--locked", "-p", "nsealr-core", "-e", "features",
                        "--target", "riscv32imafc-unknown-none-elf"])
run("workspace-tests", ["cargo", "test", "--workspace", "--locked"])
run("full-ci", ["make", "ci"])
probe = "docs/restart/implementation/S02/probes/core-link/Cargo.toml"
target = ROOT / "target/s02-core-link"
env = {"CARGO_TARGET_DIR": str(target)}
linked = run("core-final-link", ["cargo", "rustc", "--manifest-path", probe, "--locked",
                               "--offline", "--release", "--target", "riscv32imafc-unknown-none-elf",
                               "--", "-C", "link-arg=--entry=_start"], env)
passed = all(row["exit_code"] == 0 for row in manifest["runs"])
if linked.returncode == 0:
    binary = target / "riscv32imafc-unknown-none-elf/release/s02-core-link"
    manifest["core_elf_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    for name, args in [("readelf", ["-hSW"]), ("nm", ["-u"]), ("size", ["-A"])]:
        inspected = run(f"core-{name}", [name, *args, str(binary)])
        passed = passed and inspected.returncode == 0
        if name == "nm":
            manifest["no_undefined_symbols"] = inspected.returncode == 0 and not inspected.stdout.strip()
            passed = passed and manifest["no_undefined_symbols"]
manifest["passed"] = passed
(OUT / "commands.json").write_text(json.dumps(manifest, indent=2) + "\n")
raise SystemExit(0 if passed else 1)
