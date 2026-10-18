#!/usr/bin/env python3
"""Run reviewer-authored checks without writing to the candidate worktree."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REVIEW_ROOT = HERE.parents[4]
CANDIDATE = Path(sys.argv[1]).resolve()
WORK = REVIEW_ROOT / "target/security-review-s02"
WORK.mkdir(parents=True, exist_ok=True)
OUT = HERE / "independent-results"
OUT.mkdir(exist_ok=True)
manifest = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "candidate": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=CANDIDATE, text=True).strip(), "runs": []}

def run(name, command, cwd=CANDIDATE, overrides=None):
    env = {"CARGO_TARGET_DIR": str(WORK / "build")} | (overrides or {})
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    p = subprocess.run(command, cwd=cwd, env=os.environ | env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = OUT / (name + ".log")
    log.write_text(p.stdout)
    manifest["runs"].append({"name": name, "started_utc": start, "command": command, "cwd": str(cwd), "env_overrides": env, "exit_code": p.returncode, "log": str(log.relative_to(REVIEW_ROOT)), "sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
    (OUT / "commands.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(name, p.returncode, flush=True)
    return p

# Independent oracle: assemble ENT||CS as an integer, then use CPython/OpenSSL
# hashlib, without importing candidate code or its expected fixture values.
lines = ["count,last,valid,entropy_hex"]
for count in [12, 15, 18, 21, 24]:
    checksum_bits = count // 3
    entropy_length = (count * 11 - checksum_bits) // 8
    for last in range(2048):
        entropy = (last >> checksum_bits).to_bytes(entropy_length, "big")
        expected = hashlib.sha256(entropy).digest()[0] >> (8 - checksum_bits)
        valid = int(last & ((1 << checksum_bits) - 1) == expected)
        lines.append(f"{count},{last},{valid},{entropy.hex()}")
oracle = WORK / "checksum-oracle.csv"
oracle.write_text("\n".join(lines) + "\n")
manifest["oracle"] = {"algorithm": "All 2048 final words for each BIP39 size; preceding words zero. ENT||CS split by integer shift; CPython hashlib SHA256 oracle.", "rows": 10240, "sha256": hashlib.sha256(oracle.read_bytes()).hexdigest()}
probe = WORK / "Cargo.toml"
probe.write_text('[package]\nname="s02-independent-adversarial"\nversion="0.0.0"\nedition="2021"\n[workspace]\n[dependencies]\nnsealr-core={path=' + json.dumps(str(CANDIDATE / 'crates/nsealr-core')) + '}\n[[bin]]\nname="s02-independent-adversarial"\npath=' + json.dumps(str(HERE / 'adversarial.rs')) + '\n')
run("environment", ["rustc", "+1.95.0", "-vV"])
run("adversarial", ["cargo", "+1.95.0", "run", "--manifest-path", str(probe), "--offline", "--release", "--", str(oracle)])
run("public-contract-doctests", ["cargo", "+1.95.0", "test", "-p", "nsealr-core", "--locked", "--offline", "--doc"])
run("target-features", ["cargo", "+1.95.0", "tree", "--locked", "--offline", "-p", "nsealr-core", "-e", "features", "--target", "riscv32imafc-unknown-none-elf"])
run("core-final-link", ["cargo", "+1.95.0", "rustc", "--manifest-path", "docs/restart/implementation/S02/probes/core-link/Cargo.toml", "--locked", "--offline", "--release", "--target", "riscv32imafc-unknown-none-elf", "--", "-C", "link-arg=--entry=_start"])
elf = WORK / "build/riscv32imafc-unknown-none-elf/release/s02-core-link"
if elf.exists():
    manifest["reviewer_core_elf_sha256"] = hashlib.sha256(elf.read_bytes()).hexdigest()
    run("core-undefined", ["nm", "-u", str(elf)])
    run("core-sections", ["readelf", "-hSW", str(elf)])
manifest["candidate_dirty_after"] = subprocess.check_output(["git", "status", "--porcelain"], cwd=CANDIDATE, text=True)
manifest["passed"] = all(r["exit_code"] == 0 for r in manifest["runs"]) and not manifest["candidate_dirty_after"]
(OUT / "commands.json").write_text(json.dumps(manifest, indent=2) + "\n")
raise SystemExit(0 if manifest["passed"] else 1)
