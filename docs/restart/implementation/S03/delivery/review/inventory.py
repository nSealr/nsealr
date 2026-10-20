#!/usr/bin/env python3
"""Exact current candidate, source/proof, lock/vendor and projection checks."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
C = "c358229777d2582964a4f326ce8d15709841a395"
B = "b1c90139a651895284b2624da7d12903cf16bc9d"
S = "03216fba02d229bcdb5c81d0573bbe26c6f35abc"
P = "7eee22fbc269033756e53020b1370fc6671da3ab"
F = "dda66f3e4d0d25f2fa3f3ee2b5cb5aacfdd122d3"
E = "docs/restart/implementation/S03/integration/evidence/"

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def body(commit, path):
    return git("show", commit + ":" + path)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    return (ROOT / path).read_bytes()

def load(path):
    return json.loads(read(path))

def tree(commit):
    result = {}
    for row in git("ls-tree", "-rz", commit).split(b"\0"):
        if row:
            entry, path = row.decode().split("\t")
            mode, kind, blob = entry.split()
            result[path] = (mode, kind, blob)
    return result

trees = {c: tree(c) for c in (C, B, S, P, F)}
assert git("rev-parse", "HEAD").decode().strip() == C
assert git("rev-parse", C + "^{tree}").decode().strip() == "ffd6f5b0bb667ff33ef6a7d65eabab874bdfa596"
assert sha(read(E + "result.json")) == "7d997d3f737b7ff3df2ca0f7af9b48b351ff26819f6f6927d232615ac9e05d5c"
assert sha(read(E + "artifact-manifest.json")) == "2cea7e29561d5268fb214aea1bb760b76ec3a0112e78befad829e543af584964"
manifest = load(E + "artifact-manifest.json")["artifacts"]
assert len(manifest) == len({r["path"] for r in manifest}) == 211
for row in manifest:
    raw = read(row["path"])
    assert sha(raw) == row["sha256"] and len(raw) == row["bytes"]
    assert trees[C][row["path"]][0] == row["mode"]
    assert (ROOT / row["path"]).is_file() and not (ROOT / row["path"]).is_symlink()
manifest_set = {r["path"] for r in manifest} | {E + "artifact-manifest.json"}

copies = load(E + "input-copy-inventory.json")["files"]
assert len(copies) == len({r["destination"] for r in copies}) == 87
groups = {}
for row in copies:
    raw = read(row["destination"])
    assert sha(raw) == row["sha256"] and len(raw) == row["bytes"]
    assert trees[C][row["destination"]][0] == row["mode"]
    if "commit" in row:
        original = body(row["commit"], row["path"])
        original_entry = git("ls-tree", row["commit"], "--", row["path"]).decode().split("\t")[0].split()
        assert original == raw and original_entry == [row["mode"], "blob", row["blob"]]
    else:
        assert Path(row["source_path"]).read_bytes() == raw
    groups[row["group"]] = groups.get(row["group"], 0) + 1
assert groups == {"original_historical_public_copy": 80, "distinct_preimplementation_review": 6, "root_implementation_admission": 1}
for manifest_path, member_key in [("docs/restart/implementation/S03/evidence/artifact-manifest.json", "artifacts"),
                                 ("docs/restart/implementation/reviews/S03-security/artifact-manifest.json", "files")]:
    old = load(manifest_path)
    # Both historical manifests bind exact copies; inspect all actual members.
    for row in old[member_key]:
        raw = read(row["path"])
        assert sha(raw) == row["sha256"] and len(raw) == row["bytes"]

product = load(E + "final-product-source.json")["source_postimage_sha256"]
assert len(product) == 26
for path, digest in product.items():
    assert sha(read(path)) == digest and trees[C][path] == trees[P][path]
tail = git("diff", "--name-only", P, C).decode().splitlines()
assert tail and all(p.startswith(E) for p in tail)
serial = "crates/nsealr-core/src/review/serial.rs"
actual_after_full = [p for p in trees[C] if not p.startswith("docs/") and trees[C].get(p) != trees[F].get(p)]
assert actual_after_full == [serial]
def no_rustdoc(raw):
    return b"\n".join(line for line in raw.splitlines() if not line.lstrip().startswith(b"///"))
assert no_rustdoc(body(F, serial)) == no_rustdoc(read(serial))
for path in ["crates/nsealr-core/src/authorization.rs", "crates/nsealr-core/src/event.rs", "crates/nsealr-core/src/review/event.rs"]:
    assert trees[C][path] == trees[S][path]
changed = [row.split("\t") for row in git("diff", "--name-status", B, C).decode().splitlines()]
assert {p for _, p in changed if p.startswith("docs/")} == manifest_set
assert all(trees[C][p][0] in ("100644", "100755") for _, p in changed)
for path in ["plan/work-items.json", "plan/evidence-index.json", "docs/restart/README.md",
             "docs/restart/implementation/handoff.md", "scripts/verify_contracts.py", "scripts/test_contracts.py",
             "scripts/check_product_gates.py", "scripts/test_product_gates.py", "tests/integration/run.py",
             "ci/ratchet.json", "ci/core-test-projections.json", "rust-toolchain.toml",
             "apps/desktop-simulator/rust-toolchain.toml", "Cargo.toml", ".cargo/config.toml",
             "apps/desktop-simulator/Cargo.toml", "apps/desktop-simulator/.cargo/config.toml"]:
    assert trees[C][path] == trees[B][path], path
assert all(trees[C][p] == entry for p, entry in trees[B].items() if p.startswith(("protocols/contracts/v1/", ".github/", "vendor/")))
vendor_rows = [r for r in load("docs/restart/implementation/S03/integration/source-reconciliation.json")["source_changed_files"] if r["group"] == "vendor"]
assert len(vendor_rows) == 686
assert {p for _, p in changed if p.startswith("vendor/")} == {r["path"] for r in vendor_rows}
assert all(trees[C][r["path"]] == trees[S][r["path"]] for r in vendor_rows)

def packages(commit):
    result = set()
    for path in ["Cargo.lock", "apps/desktop-simulator/Cargo.lock"]:
        for p in tomllib.loads(body(commit, path).decode())["package"]:
            if p.get("source", "").startswith("registry+"):
                result.add((p["name"], p["version"], p["checksum"]))
    return result
old, current = packages(B), packages(C)
source = {(p["name"], p["version"], p["checksum"]) for p in tomllib.loads(body(S, "Cargo.lock").decode())["package"] if p.get("source", "").startswith("registry+")}
assert len(old) == 24 and len(current) == 45 and old < current == source
vendor_files = 0
for name, version, checksum in sorted(current):
    directory = ROOT / "vendor" / name
    if not directory.exists():
        directory = ROOT / "vendor" / (name + "-" + version)
    metadata = json.loads((directory / ".cargo-checksum.json").read_bytes())
    assert metadata["package"] == checksum
    for rel, digest in metadata["files"].items():
        assert sha((directory / rel).read_bytes()) == digest
        vendor_files += 1
for row in load(E + "vendor-union-check.json")["license_notices"]:
    for notice in row["notices"]:
        assert read("vendor/" + notice)

commands = []
for command_path in sorted((ROOT / E / "commands").glob("*/command.json")):
    row = json.loads(command_path.read_bytes())
    for log in row["files"]:
        raw = (command_path.parent / log["path"]).read_bytes()
        assert sha(raw) == log["sha256"] and len(raw) == log["bytes"]
    commands.append(dict(path=str(command_path.relative_to(ROOT)), exit_code=row["exit_code"], source_commit=row.get("source_commit"),
                         source_role="Explicit checkpoint where recorded; earlier uncommitted preparation receipts retain no source_commit field."))
full = load(E + "commands/combined-make-ci/command.json")
assert full["exit_code"] == 0 and full["source_commit"] == F
assert full["initial_worktree_status_sha256"] == sha(b"")
stdout = read(E + "commands/combined-make-ci/stdout.log").decode()
assert "All 17 retained product integration steps passed." in stdout
assert "246 passed; 0 failed" in stdout and "247 passed; 0 failed" in stdout and "20 passed; 0 failed" in stdout
assert "15 passed; 0 failed" in stdout and "100.00%  100.00%  ok" in stdout
assert "76.76%   76.70%  ok" in stdout
assert "590e38bc45a96e78ff81b83b130e4dac31576b4d8e5c58705c5734b96cca2ee5" in read(E + "commands/serial-comments-repro/stdout.log").decode()

projection = load(E + "projection-checks.json")
assert len(load("ci/core-test-projections.json")) == 170 and len(projection["outputs"]) == 174
with tempfile.TemporaryDirectory(prefix="projection-", dir=OUT / "build") as temp:
    temp = Path(temp)
    subprocess.run(["python3", str(ROOT / "ci/project_core_fixtures.py"), str(temp / "current")], check=True)
    actual = {p.name: sha(p.read_bytes()) for p in (temp / "current").iterdir()}
    assert actual == projection["outputs"]
    baseline = temp / "baseline"
    (baseline / "ci").mkdir(parents=True)
    shutil.copytree(ROOT / "protocols/contracts/v1", baseline / "protocols/contracts/v1")
    for path in ["ci/project_core_fixtures.py", "ci/core-test-projections.json"]:
        (baseline / path).write_bytes(body(B, path))
    subprocess.run(["python3", str(baseline / "ci/project_core_fixtures.py"), str(temp / "old")], check=True)
    old_outputs = {p.name: p.read_bytes() for p in (temp / "old").iterdir()}
    assert len(old_outputs) == 173
    assert all((temp / "current" / name).read_bytes() == raw for name, raw in old_outputs.items())
    assert (temp / "current/s03-vectors.json").read_bytes() == body(S, "docs/restart/implementation/S03/vectors.json")

later = load(E + "later-main-metadata-observation.json")
later_delta = [dict(status=s, path=p) for s, p in (r.split("\t") for r in git("diff", "--name-status", B, later["later_actual_main"]).decode().splitlines())]
assert later_delta == later["exact_delta"] and len(later_delta) == 129
assert sha(git("diff", "--name-status", B, later["later_actual_main"])) == later["delta_name_status_sha256"]
result = dict(candidate=C, tree=git("rev-parse", C + "^{tree}").decode().strip(), recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status="PASS_exact_inventory_and_retained_inputs", manifest_members=211, exact_input_copies=groups,
    product_bindings=26, source_vendor_files=686, registry_packages=dict(old=24,current=45,added=21), vendor_checksum_file_members=vendor_files,
    checked_command_receipts=commands, full_run_clean_checkpoint=F, product_after_full_run="Two Rustdoc blocks only; no non-Rustdoc line change",
    independent_projected_outputs=174, old_outputs_byte_identical=173, original_source_vectors_copied_exactly=True,
    graph_frozen_checkers_gates_runner_toolchains_workspaces_unchanged=True, later_main_metadata_paths=129,
    changed_candidate_paths=len(changed), final_tail_paths=len(tail), no_future_CI_or_physical_or_task_closure=True)
(OUT / "inventory-result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "checked_command_receipts"}, sort_keys=True))
