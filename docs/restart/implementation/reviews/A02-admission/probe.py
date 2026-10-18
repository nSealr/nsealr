#!/usr/bin/env python3
"""Independent, read-only checks of A02 admission records; no target assembly."""
import argparse
import ast
import copy
import fnmatch
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def git(repo, *args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    assert p.returncode == 0, (repo.name, args[0], p.returncode)
    return p.stdout


def read(path):
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--author-runtime", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--obligations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    m = read(args.manifest)
    entries = {e["name"]: e for e in m["sources"]}
    trees, contents = {}, {}
    for name, e in entries.items():
        repo = args.source_root / e["directory"]
        assert git(repo, "rev-parse", e["commit"] + "^{tree}").decode().strip() == e["tree"]
        rows = {}
        for raw in git(repo, "ls-tree", "-rz", e["commit"]).split(b"\0"):
            if not raw:
                continue
            meta, path = raw.split(b"\t", 1)
            mode, kind, oid = meta.decode().split()
            rows[path.decode()] = (mode, kind, oid)
        trees[name] = rows
    def blob(name, path):
        key = (name, path)
        if key not in contents:
            contents[key] = git(args.source_root / entries[name]["directory"], "cat-file", "blob", trees[name][path][2])
        return contents[key]
    files = read(args.records / "file-dispositions.json")
    expected_files = {}
    for name, tree in trees.items():
        e = entries[name]
        for path in tree:
            rule = next((r for r in e["rules"] if r.get("path") == path
                         or ("prefix" in r and path.startswith(r["prefix"]))
                         or ("glob" in r and fnmatch.fnmatchcase(path, r["glob"]))), e["default"])
            if e["visibility"] != "private" or rule["action"] != "exclude":
                expected_files[(name, path)] = rule
    seen = set()
    file_map = {}
    for row in files["files"]:
        key = row["source"], row["path"]
        assert key not in seen
        seen.add(key)
        file_map[key] = row
        assert row["action"] == expected_files[key]["action"]
        mode, kind, oid = trees[key[0]][key[1]]
        assert row["commit"] == entries[key[0]]["commit"]
        assert (row["mode"], row["blob"]) == (mode, oid)
        if row["action"] != "exclude":
            assert kind == "blob" and sha(blob(*key)) == row["sha256"]
    assert files["manifest_sha256"] == sha(canonical(m))
    assert seen == set(expected_files)
    case_root = args.author_runtime / "cases-01"
    case_summary = read(case_root / "summary.json")
    case_commands = read(case_root / "commands.json")
    assert sha(canonical(case_commands)) == case_summary["commands_sha256"]
    dispositions = read(args.records / "case-dispositions.json")
    public_cases = {(r["source"], r["path"], r["case_id"]): r for r in dispositions["cases"] if r["source"] != "nsealr"}
    assert len(public_cases) == sum(r["source"] != "nsealr" for r in dispositions["cases"])
    expected_cases, private_case_hashes = set(), set()
    effective = {}
    for overlay in m["overlays"]:
        record_bytes = blob(overlay["record_source"], overlay["manifest_path"])
        assert sha(record_bytes) == overlay["manifest_sha256"]
        assert sha(blob(overlay["record_source"], overlay["patch_path"])) == overlay["patch_sha256"]
        for path, change in json.loads(record_bytes)["files"].items():
            key = overlay["target_source"], path
            assert effective.get(key, sha(blob(*key))) == change["before_sha256"]
            effective[key] = change["after_sha256"]
    for record_row in case_summary["sources"]:
        name = record_row["source"]
        record_bytes = (case_root / (name + "-cases.json")).read_bytes()
        assert sha(record_bytes) == record_row["record_sha256"]
        record = json.loads(record_bytes)
        command = next(r for r in case_commands if r["label"] == name + "-cases")
        raw_log = (case_root / command["log"]).read_bytes()
        assert command["exit_code"] == 0 and sha(raw_log) == command["sha256"]
        assert json.loads(raw_log) == record["cases"]
        checkout = Path(command["cwd"])
        assert git(checkout, "rev-parse", "HEAD").decode().strip() == entries[name]["commit"]
        assert record["source_commit"] == entries[name]["commit"] and record["source_tree"] == entries[name]["tree"]
        bindings = {r["path"]: r["sha256"] for r in record["input_files"]}
        assert set(bindings) == set(trees[name])
        for path, digest in bindings.items():
            assert digest == effective.get((name, path), sha(blob(name, path)))
            assert not (checkout / path).is_symlink() and sha((checkout / path).read_bytes()) == digest
        assert len(record["cases"]) == record_row["case_count"]
        for case in record["cases"]:
            path = case["file"].split("/companion/", 1)[1] if name == "companion" else case["path"]
            case_id = case.get("name", case.get("id"))
            key = name, path, case_id
            if (name, path) not in expected_files:
                private_case_hashes.add(sha(canonical({"path": path, "case_id": case_id})))
            else:
                expected_cases.add(key)
                assert public_cases[key]["effective_source_sha256"] == bindings[path]
    assert expected_cases == set(public_cases)
    assert private_case_hashes == {r["case_identity_sha256"] for r in dispositions["private_excluded_cases"]}
    if args.obligations:
        obligations = read(args.obligations)
        assert obligations["source_commit"] == entries["lab"]["commit"]
        assert dispositions["private_case_obligations_sha256"] == sha(args.obligations.read_bytes())
        indexed = {r["case_identity_sha256"]: r for r in obligations["cases"]}
        assert len(indexed) == len(obligations["cases"]) == len(private_case_hashes)
        assert set(indexed) == private_case_hashes
        for row in dispositions["private_excluded_cases"]:
            assert {k: v for k, v in row.items() if k != "source"} == indexed[row["case_identity_sha256"]]
        for row in obligations["cases"]:
            if row["treatment"] == "replace-product-guardrail":
                assert all(row.get(k) for k in ("negative_control", "positive_control", "target_gate", "after_execution"))
            for binding in row.get("existing_source_bindings", []):
                name = binding["source"]
                assert binding["commit"] == entries[name]["commit"]
                path = binding.get("path")
                if path is None:
                    paths = [p for p in trees[name] if sha(p.encode()) == binding["path_identity_sha256"]]
                    assert len(paths) == 1
                    path = paths[0]
                assert sha(blob(name, path)) == binding["sha256"]
    closure = read(args.records / "closed-evidence.json")
    graph = json.loads(blob("nsealr", m["graph"]["path"]))
    expected = {}
    references = 0
    for task in graph["tasks"]:
        if task["status"] not in {"verified", "integrated"}:
            continue
        for artifact in task["result_artifacts"]:
            references += 1
            expected.setdefault(artifact["path"], set()).add(task["id"])
            assert sha(blob("nsealr", artifact["path"])) == artifact["sha256"]
    assert {a["path"] for a in closure["artifacts"]} == set(expected)
    for row in closure["artifacts"]:
        mode, kind, oid = trees["nsealr"][row["path"]]
        assert kind == "blob" and (row["mode"], row["blob"]) == (mode, oid)
        assert row["original_commit"] == entries["nsealr"]["commit"]
        assert set(row["tasks"]) == expected[row["path"]]
        assert row["current_unchanged_path"] == row["path"]
        assert row["sha256"] == sha(blob("nsealr", row["path"]))
    recovery = []
    for folder in ("recovery-01", "workspace-recovery-02", "hardware-recovery-03"):
        root = args.author_runtime / folder
        summary = read(root / "summary.json")
        commands = read(root / "commands.json")
        assert sha(canonical(commands)) == summary["commands_sha256"]
        for command in commands:
            assert command["exit_code"] == 0
            assert sha((root / command["log"]).read_bytes()) == command["sha256"]
        for row in summary["sources"]:
            name = row["source"]
            assert sha((root / (name + ".bundle")).read_bytes()) == row["bundle_sha256"]
            refs_path = root / (name + "-refs.json")
            refs = read(refs_path)["refs"]
            assert sha(refs_path.read_bytes()) == row["refs_record_sha256"]
            restored = root / (name + "-restored.git")
            git(restored, "fsck", "--full", "--strict")
            assert git(restored, "rev-parse", row["selected_commit"] + "^{tree}").decode().strip() == row["selected_tree"]
            for ref in refs:
                assert git(restored, "rev-parse", "--verify", ref["ref"]).decode().strip() == ref["object"]
            assert root.stat().st_mode & 0o077 == 0
            recovery.append({"source": name, "context": folder, "bundle_sha256": row["bundle_sha256"],
                             "all_captured_refs_verified": len(refs), "restored_fsck": 0})
    # An actual frozen S02 artifact alteration must be rejected, even with an
    # otherwise genuine current graph. Mutation exists only in this in-memory view.
    sys.path.insert(0, str(Path.cwd() / "tools/migration"))
    from rehearse import Source, PreflightError, evidence_closure, inventory
    source = Source(args.source_root, entries["nsealr"])
    try:
        original = source.blob
        path = next(t for t in graph["tasks"] if t["id"] == "S02")["result_artifacts"][-1]["path"]
        source.blob = lambda p: original(p) + (b"\nreviewer-tamper\n" if p == path else b"")
        try:
            evidence_closure(source, m["graph"]["path"])
            raise AssertionError("changed closed S02 artifact accepted")
        except PreflightError as error:
            assert "closed artifact hash mismatch" in str(error)
    finally:
        source.close()
    collision = copy.deepcopy(m)
    pi = next(e for e in collision["sources"] if e["name"] == "raspberry")
    next(r for r in pi["rules"] if r.get("path") == "LICENSE")["destination"] = "LICENSE"
    result = inventory(collision, args.source_root)
    assert result["destination_collisions"] and not result["summary"]["import_allowed"]
    args.output.write_bytes(canonical({"candidate": args.candidate, "manifest_sha256": sha(args.manifest.read_bytes()),
        "source_trees": {name: e["tree"] for name, e in entries.items()}, "public_disposition_rows_verified": len(seen),
        "closed_artifact_references": references, "unique_closed_artifacts": len(expected), "recovery": recovery,
        "framework_case_rows_verified": len(expected_cases), "private_case_opaque_bindings_verified": len(private_case_hashes),
        "overlay_postimages_verified": len(effective),
        "actual_closed_S02_artifact_tamper": "rejected", "actual_map_destination_collision": "blocked",
        "scope": "Independent source/bundle/evidence correspondence and meaningful rejection controls; no import, product test execution or hardware claim."}))


if __name__ == "__main__":
    main()
