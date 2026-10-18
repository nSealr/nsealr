#!/usr/bin/env python3
"""Check the exact public admission package without exposing protected names."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def read(path):
    return json.loads(path.read_bytes())


root = Path.cwd()
base = root / "docs/restart/implementation/A02"
out = root / "docs/restart/implementation/reviews/A02-admission"
runtime = Path("/home/tux/nsealr/.restart-tools/goal/a02/tools/migration/.runtime")
candidate = "732f742422cb26e7f215613f56a6c90acc6f73dc"
assert git(root, "rev-parse", "HEAD").decode().strip() == candidate
summary = read(base / "admission-evidence/summary.json")
assert sha((base / "admission-evidence/summary.json").read_bytes()) == "2b33ec8f10bac814963c747747a5b5540306e95510e9fcca0bef6d51bfc7e898"
for record in summary["artifacts"] + summary["source_bindings"]:
    assert sha((root / record["path"]).read_bytes()) == record["sha256"]
for name in ("brief.md", "input-notes.json", "source-observations.json", "preparation-validation.json"):
    assert (base / name).read_bytes() == git(root, "show", "709f09183e7d54937a8562151dd5ac1fbeefc615:docs/restart/implementation/A02/" + name)
for name in ("file-dispositions.json", "case-dispositions.json", "closed-evidence.json", "before-gates.json"):
    assert (base / "admission-evidence" / name).read_bytes() == (runtime / "public-records-04" / name).read_bytes()
privacy = read(base / "privacy-review/provenance.json")
for record in privacy["files"]:
    data = (root / record["copy_path"]).read_bytes()
    assert sha(data) == record["sha256"]
    assert data == git(root, "show", privacy["source_commit"] + ":" + record["source_path"])
commands = 0
for path in (base / "admission-evidence").rglob("commands.json"):
    for row in read(path):
        assert row["exit_code"] == 0 and sha((path.parent / row["log"]).read_bytes()) == row["sha256"]
        commands += 1
core = read(base / "admission-evidence/core-python-cases.json")
assert Counter(r["group"] for r in core["cases"]) == {"plan": 18, "bootstrap": 11}
ledger = read(base / "admission-evidence/case-dispositions.json")
assert len(ledger["cases"]) + len(core["cases"]) == summary["counts"]["public_named_cases"]
assert not ({(r["source"], r["case_id"]) for r in core["cases"]}
            & {(r["source"], r["case_id"]) for r in ledger["cases"]})
for row in core["cases"]:
    data = git(Path("/home/tux/nsealr/firmware"), "show", row["commit"] + ":" + row["path"])
    assert sha(data) == row["source_sha256"]
core_commands = read(base / "admission-evidence/core-python-cases-01/commands.json")
collected = {(r["path"], r["id"]) for command in core_commands
             for r in read(base / "admission-evidence/core-python-cases-01" / command["log"])}
assert collected == {(r["path"], r["case_id"]) for r in core["cases"]}
private_cases = read(runtime / "public-records-04-private-cases.json")
assert sha((runtime / "public-records-04-private-cases.json").read_bytes()) == summary["privacy"]["private_case_record_sha256"]
original = git(Path("/home/tux/nsealr/lab"), "show", "3303ab17a28ed32419576627d5abb93db3999635:scripts/integration_feature_matrix.py")
assignment = next(n for n in ast.parse(original).body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "LAB_DOCS" for t in n.targets))
private_addresses = [n.value for n in ast.walk(assignment.value) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
forbidden = {s.encode() for v in private_addresses for s in (v, Path(v).name)}
forbidden.update(r["case_id"].encode() for r in private_cases)
forbidden.update(r["path"].encode() for r in private_cases)
commits = git(root, "rev-list", "709f09183e7d54937a8562151dd5ac1fbeefc615.." + candidate).decode().splitlines()
blobs = set()
for commit in commits:
    for raw in git(root, "ls-tree", "-rz", commit, "docs/restart/implementation/A02", "tools/migration").split(b"\0"):
        if raw:
            meta, _ = raw.split(b"\t", 1)
            mode, kind, oid = meta.decode().split()
            if kind == "blob":
                blobs.add(oid)
for oid in blobs:
    data = git(root, "cat-file", "blob", oid)
    assert not any(value in data for value in forbidden), "protected name in public candidate history"
assert git(root, "ls-remote", "origin", "refs/heads/main").decode().split()[0] == summary["canonical_core_commit"]
assert summary["import_executed"] is False and summary["after_migration_tests_executed"] is False
(out / "final-package-probe.json").write_text(json.dumps({
    "candidate": candidate, "summary_sha256": sha((base / "admission-evidence/summary.json").read_bytes()),
    "artifact_bindings_verified": len(summary["artifacts"]), "source_bindings_verified": len(summary["source_bindings"]),
    "copied_privacy_review_files_verified": len(privacy["files"]), "command_log_bindings_verified": commands,
    "core_python_case_bindings_verified": len(collected), "public_history_commits_scanned": len(commits),
    "unique_public_history_blobs_scanned": len(blobs), "protected_address_basename_case_id_path_matches": 0,
    "public_main_still_exact_f2": True, "original_four_spec_files_unchanged": True,
    "complete_generated_maps_copied_exactly": True, "import_or_after_execution_claim": False
}, indent=2) + "\n")
print("PASS: exact package/source/log bindings, copied distinct review, complete core Python cases and protected-name history scan.")
