#!/usr/bin/env python3
"""Read-only A02 adoption-scope identity, append and frozen-path checks.

This does not materialize the adoption or accept the separate final rehearsal.
No source body, bundle or private object is copied into the review directory.
"""
import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

SCOPE = "c44598f1c516aa16336a5b1fa6f8d52424f5f80c"
SCOPE_BASE = "6c732f9dd89eeb33214bcebd7321b3ab50904a8e"
AUTHOR = "f9a09ba2e9b0212f7dafa53b086c5f1c366d9288"
PRODUCT = "daf8ba03a9eb820f99b0f1bf5c4f553a7961e008"
TREE = "db0687a5ec15228e944360e00e391a4fff863f5d"
CORE = "f2ef70f522af4977e15f81554a8c6eadcdbe8097"
BASE = Path("/home/tux/nsealr/.restart-tools/goal")
PRODUCT_REPO = BASE / "a02/tools/migration/.runtime/rehearsal-01/repository"
RECOVERY = BASE / "a02/tools/migration/.runtime/rehearsal-04/candidate-recovery"
MANIFEST = "docs/restart/implementation/A02/final-review-package.json"
PAYLOAD = "docs/restart/implementation/resume-2026-10-20/a02-adoption-payload.json"
SPEC = "docs/restart/implementation/resume-2026-10-20/a02-adoption-scope.md"
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def sha(body):
    return hashlib.sha256(body).hexdigest()


def read(repo, commit, path):
    return git(repo, "show", commit + ":" + path)


def tree(repo, commit):
    result = {}
    for entry in git(repo, "ls-tree", "-rz", commit).split(b"\0"):
        if entry:
            header, path = entry.split(b"\t", 1)
            mode, kind, oid = header.decode().split()
            result[path.decode()] = (mode, kind, oid)
    return result


def blobs(repo, oids):
    ids = sorted(set(oids))
    output = git_batch(repo, ids)
    data = {}
    cursor = 0
    for oid in ids:
        end = output.index(b"\n", cursor)
        got, kind, size = output[cursor:end].decode().split()
        assert got == oid and kind == "blob"
        start = end + 1
        cursor = start + int(size)
        data[oid] = output[start:cursor]
        assert output[cursor:cursor + 1] == b"\n"
        cursor += 1
    assert cursor == len(output)
    return data


def git_batch(repo, ids):
    return subprocess.check_output(["git", "-C", str(repo), "cat-file", "--batch"],
                                   input=("\n".join(ids) + "\n").encode())


def binding(repo, commit, path):
    body = read(repo, commit, path)
    mode, kind, oid = tree(repo, commit)[path]
    return {"commit": commit, "path": path, "mode": mode, "kind": kind,
            "blob": oid, "bytes": len(body), "sha256": sha(body)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope-commit", default=SCOPE)
    parser.add_argument("--author-commit", default=AUTHOR)
    parser.add_argument("--reuse-original-audit", type=Path)
    args = parser.parse_args()
    scope, author = args.scope_commit, args.author_commit
    payload = json.loads(read(REPO, scope, PAYLOAD))
    package_body = read(REPO, author, MANIFEST)
    package = json.loads(package_body)
    assert payload["author_commit"] == author and payload["product_commit"] == PRODUCT
    assert payload["product_tree"] == TREE and payload["package_sha256"] == sha(package_body)
    assert package["product_commit"] == PRODUCT and package["product_tree"] == TREE
    assert git(PRODUCT_REPO, "rev-parse", PRODUCT + "^{tree}").decode().strip() == TREE
    delta = git(REPO, "diff", "--name-status", SCOPE_BASE, scope).decode().splitlines()
    assert sorted(delta) == sorted(["A\t" + PAYLOAD, "A\t" + SPEC])
    subprocess.run(["git", "-C", str(REPO), "diff", "--check", SCOPE_BASE, scope], check=True)
    source_tree, product_tree = tree(REPO, author), tree(PRODUCT_REPO, PRODUCT)
    rows = payload["rows"]
    paths = [row["path"] for row in rows]
    assert len(paths) == len(set(paths)) == payload["total_files"] == 983
    namespace = ("docs/restart/implementation/A02/", "tools/migration/")
    actual_public = {p for p in source_tree if p.startswith(namespace)}
    assert actual_public == set(paths)
    assert {row["path"] for row in package["files"]} | {MANIFEST} == set(paths)
    assert len(package["files"]) == 982
    author_blobs = blobs(REPO, [row["blob"] for row in rows])
    counts = collections.Counter()
    for row in rows:
        path = PurePosixPath(row["path"])
        assert not path.is_absolute() and str(path) == row["path"]
        assert not {"..", ".runtime", ".git", "__pycache__", "node_modules"}.intersection(path.parts)
        assert not row["path"].endswith((".bundle", ".pdf", ".zip", ".tar", ".gz", ".pyc"))
        assert row["source_commit"] == author
        assert source_tree[row["path"]] == (row["mode"], "blob", row["blob"])
        assert row["mode"] in {"100644", "100755"}
        body = author_blobs[row["blob"]]
        assert len(body) == row["bytes"] and sha(body) == row["sha256"]
        prior = product_tree.get(row["path"])
        if prior:
            assert prior == source_tree[row["path"]]
            assert row["before"] == {k: row[k] for k in ("mode", "blob", "sha256", "bytes")}
            assert row["disposition"] == "unchanged"
        else:
            assert row["before"] is None and row["disposition"] == "add_reviewed_A02_output"
            for parent in path.parents:
                if str(parent) in product_tree:
                    raise AssertionError("file/symlink parent collision: " + str(parent))
        counts[row["disposition"]] += 1
    assert dict(counts) == {"add_reviewed_A02_output": 910, "unchanged": 73}
    assert payload["counts"] == dict(counts, replace_reviewed_A02_output=0)
    by_path = {row["path"]: row for row in rows}
    for row in package["files"]:
        assert all(row[key] == by_path[row["path"]][key] for key in ("mode", "sha256"))

    affected_update = None
    if author != AUTHOR:
        allowed = {"docs/restart/implementation/A02/final-report.md",
                   "docs/restart/implementation/A02/execution/progress.json", MANIFEST}
        changed = git(REPO, "diff", "--name-status", AUTHOR, author).decode().splitlines()
        assert set(changed) == {"M\t" + path for path in allowed}
        prior = json.loads(read(REPO, SCOPE, PAYLOAD))
        prior_rows = {row["path"]: row for row in prior["rows"]}
        assert set(prior_rows) == set(paths) and prior["counts"] == payload["counts"]
        changed_rows = set()
        for row in rows:
            old_row = dict(prior_rows[row["path"]])
            old_row["source_commit"] = author
            if old_row != row:
                changed_rows.add(row["path"])
            assert old_row["before"] == row["before"]
        assert changed_rows == allowed
        progress = json.loads(author_blobs[by_path["docs/restart/implementation/A02/execution/progress.json"]["blob"]])
        assert len(progress["artifacts"]) == 755
        for row in progress["artifacts"]:
            assert by_path[row["path"]]["sha256"] == row["sha256"]
        intermediate = git(REPO, "rev-parse", "c9958ec").decode().strip()
        bad_index = json.loads(read(REPO, intermediate, "docs/restart/implementation/A02/execution/progress.json"))
        stale = next(row for row in bad_index["artifacts"] if row["path"] == "docs/restart/implementation/A02/final-report.md")
        actual = sha(read(REPO, intermediate, stale["path"]))
        assert stale["sha256"] != actual
        affected_update = {"original_scope": SCOPE, "original_author": AUTHOR,
                           "new_author_changed_paths": sorted(allowed),
                           "payload_source_commit_updated_everywhere": True,
                           "payload_content_rows_changed": sorted(changed_rows),
                           "all_755_current_artifact_hashes_verified": True,
                           "intermediate_stale_index": {"commit": intermediate,
                                                        "declared_report_hash": stale["sha256"],
                                                        "actual_report_hash": actual,
                                                        "preserved_in_history": True}}

    closed = json.loads(read(REPO, author, "docs/restart/implementation/A02/admission-evidence/closed-evidence.json"))
    frozen = closed["artifacts"]
    assert len(frozen) == len({r["path"] for r in frozen}) == 1508
    original_tree = tree(REPO, CORE)
    frozen_blobs = blobs(REPO, [row["blob"] for row in frozen])
    for row in frozen:
        path = row["path"]
        expected = (row["mode"], "blob", row["blob"])
        assert original_tree[path] == product_tree[path] == expected
        assert sha(frozen_blobs[row["blob"]]) == row["sha256"]
    frozen_paths = {row["path"] for row in frozen}
    metadata = {"docs/restart/README.md", "docs/restart/implementation/handoff.md", "plan/work-items.json"}
    assert not frozen_paths.intersection(paths)
    assert not frozen_paths.intersection(metadata)
    assert not any(path.startswith(("docs/restart/implementation/A02/coordinator-adoption/",
                                   "docs/restart/implementation/reviews/A02-final/")) for path in frozen_paths)
    source_graph = json.loads(read(REPO, CORE, "docs/restart/work-items.json"))
    graph = json.loads(read(PRODUCT_REPO, PRODUCT, "plan/work-items.json"))
    old_tasks = {row["id"]: row for row in source_graph["tasks"]}
    tasks = {row["id"]: row for row in graph["tasks"]}
    assert len(old_tasks) == len(tasks) == 47 and set(old_tasks) == set(tasks)
    for name in tasks:
        for field in ("acceptance", "depends_on"):
            assert old_tasks[name][field] == tasks[name][field]
    closed_ids = [row["id"] for row in closed["tasks"]]
    assert len(closed_ids) == 7
    assert all(old_tasks[name] == tasks[name] for name in closed_ids)
    assert source_graph["resources"] == graph["resources"] and len(graph["resources"]) == 16
    assert source_graph["release_paths"] == graph["release_paths"] and len(graph["release_paths"]) == 5
    assert "docs/restart/work-items.json" not in product_tree

    recovery_record = json.loads(read(REPO, author, "docs/restart/implementation/A02/execution/rehearsal-04/result.json"))
    initial = json.loads(read(REPO, author, "docs/restart/implementation/A02/execution/initial-import-map.json"))
    bundle = RECOVERY / "candidate.bundle"
    reused = None
    if args.reuse_original_audit:
        prior_body = args.reuse_original_audit.read_bytes()
        reused = json.loads(prior_body)
        assert reused["scope_candidate"] == SCOPE and reused["author_commit"] == AUTHOR
        assert reused["product_commit"] == PRODUCT and reused["product_tree"] == TREE
        assert affected_update is not None
        bundle_result = dict(reused["bundle"])
        assert package["recovery"]["bundle_sha256"] == bundle_result["sha256"]
        bundle_result["reused_original_observation_without_bundle_or_object_reaudit"] = True
    else:
        bundle_body = bundle.read_bytes()
        assert sha(bundle_body) == package["recovery"]["bundle_sha256"] == "e4e28dc2fdee6aff9fc318eaa3e0ab254aa5aa3f18ddc44a82d492603cda5f03"
        bundle_refs = git(PRODUCT_REPO, "bundle", "list-heads", str(bundle)).decode().strip()
        assert bundle_refs == PRODUCT + " refs/heads/rehearsal"
        subprocess.run(["git", "-C", str(PRODUCT_REPO), "bundle", "verify", str(bundle)],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    extra_commits = git(PRODUCT_REPO, "rev-list", "--reverse", CORE + ".." + PRODUCT).decode().splitlines()
    assert extra_commits == [initial["initial_commit"]] + recovery_record["second_assembly"]["commits"]
    assert len(extra_commits) == 40 and package["patch_count"] == 39
    expected_parent = CORE
    for commit in extra_commits:
        assert git(PRODUCT_REPO, "rev-list", "--parents", "-n", "1", commit).decode().strip() == commit + " " + expected_parent
        expected_parent = commit
    audits = []
    for root in (() if reused else (PRODUCT_REPO, RECOVERY / "restored")):
        reachable = {line.split()[0] for line in git(root, "rev-list", "--objects", PRODUCT).decode().splitlines()}
        present = set(git(root, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)").decode().splitlines())
        assert present == reachable and len(present) == 7943
        assert git(root, "rev-list", "--count", PRODUCT).decode().strip() == "330"
        assert not git(root, "remote").strip()
        assert git(root, "for-each-ref", "--format=%(objectname) %(refname)").decode().strip() == bundle_refs
        assert not (root / ".git/objects/info/alternates").exists()
        object_files = [p for p in (root / ".git/objects").rglob("*") if p.is_file()]
        assert all(p.stat().st_nlink == 1 for p in object_files)
        audits.append({"repository_role": "source" if root == PRODUCT_REPO else "restored",
                       "objects": len(present), "commits": 330,
                       "all_present_objects_reachable": True, "only_selected_ref_no_remote_or_alternates": True,
                       "object_files_have_no_hardlinks": True})
    if not reused:
        bundle_result = {"sha256": sha(bundle_body), "bytes": len(bundle_body), "refs": bundle_refs,
                         "verify_exit_code": 0, "complete_public_core_ancestry_then_declared_initial_import_and_39_transformations": True,
                         "source_and_existing_restore_object_audits": audits}
    receipt = {"schema_version": 1, "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "python": sys.version.split()[0], "scope_candidate": scope,
               "scope_base": SCOPE_BASE,
               "scope_bindings": [binding(REPO, scope, SPEC), binding(REPO, scope, PAYLOAD)],
               "author_commit": author, "product_commit": PRODUCT, "product_tree": TREE,
               "manifest_binding": binding(REPO, author, MANIFEST),
               "scope_delta": delta, "candidate_diff_check_exit_code": 0,
               "payload": {"files": 983, "manifest_members": 982, "unchanged": 73, "additions": 910,
                           "replacements": 0, "all_source_mode_blob_bytes_sha256_verified": True,
                           "all_preimages_verified": True, "namespaces": list(namespace),
                           "total_bytes": sum(row["bytes"] for row in rows),
                           "no_runtime_archive_manual_or_escaping_member_paths": True},
               "frozen_evidence": {"files_verified": 1508, "mode_blob_sha256_unchanged": True,
                                   "payload_intersections": [], "permitted_metadata_intersections": [],
                                   "coordinator_and_final_review_prefix_intersections": []},
               "graph": {"tasks": 47, "all_criteria_and_dependencies_unchanged": True,
                         "closed_records_all_fields_unchanged": closed_ids,
                         "unchanged_resources": 16, "unchanged_releases": 5, "sole_graph": "plan/work-items.json"},
               "bundle": bundle_result,
               "affected_binding_update": affected_update,
               "original_audit_reuse": ({"path": str(args.reuse_original_audit),
                                          "sha256": sha(prior_body)} if reused else None),
               "limits": ["Scope preparation only; separate final rehearsal review result was not consumed or presumed passing",
                          "No materialization/import/checkout/ref or product mutation; no product CI or functional tests",
                          "Path/body identity and known frozen-path checks do not replace full rights/privacy/rehearsal review",
                          "No actual PR, protected merge, main CI, closure or release acceptance"],
               "result": "PASS_scope_identity_payload_and_frozen_path_checks_only"}
    (HERE / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"result": receipt["result"], "files": 983, "additions": 910,
                      "unchanged": 73, "replacements": 0, "frozen_files": 1508,
                      "objects_per_isolated_repository": 7943}))


if __name__ == "__main__":
    main()
