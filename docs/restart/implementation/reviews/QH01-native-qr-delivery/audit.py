"""One-shot frozen delivery correspondence audit; no product or CI execution."""
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

BASE = "0985af3a3e2aab335eaaeac09a3b3f1fd0bd1ebf"
HEAD = "dfc2aeb444109eda10fe1ddfba2b977ab97b2b44"
PREFIX = "docs/restart/implementation/QH01/native-qr-delivery/"
EXPECTED_TREE = "a477c08387e937771d047fe96f2885c6d7c7c186"

def git(*args):
    return subprocess.check_output(["git", *args])

def digest(data):
    return hashlib.sha256(data).hexdigest()

def load(path, commit=HEAD):
    return json.loads(git("show", f"{commit}:{path}"))

cache = {}
def blob(oid):
    if oid not in cache:
        cache[oid] = git("cat-file", "blob", oid)
    return cache[oid]

def tree(commit, prefix=""):
    rows = {}
    for row in git("ls-tree", "-rz", commit, *(["--", prefix] if prefix else [])).split(b"\0"):
        if row:
            meta, path = row.split(b"\t", 1)
            mode, kind, oid = meta.decode().split()
            assert kind == "blob"
            rows[path.decode()] = (mode, oid)
    return rows

def entry(row, path, entries):
    mode, oid = entries[path]
    data = blob(oid)
    assert row["mode"] == mode and row["blob"] == oid, path
    assert row["bytes"] == len(data) and row["sha256"] == digest(data), path

assert git("rev-parse", HEAD + "^{tree}").decode().strip() == EXPECTED_TREE
assert subprocess.run(["git", "merge-base", "--is-ancestor", BASE, HEAD]).returncode == 0
before, after = tree(BASE), tree(HEAD)
changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
existing = changed & before.keys()
assert existing == {"docs/restart/README.md", "docs/restart/implementation/handoff.md", "plan/work-items.json"}
assert len(changed) == 118 and len(changed - before.keys()) == 115
inventory = load(PREFIX + "copy-inventory.json")
assert inventory["base_commit"] == BASE and inventory["exact_copy_count"] == 102
assert [g["count"] for g in inventory["source_groups"]] == [11, 81, 10]
destinations = set()
for group in inventory["source_groups"]:
    original = tree(group["commit"], group["prefix"])
    rows = [r for r in inventory["copies"] if r["source_commit"] == group["commit"]]
    assert len(rows) == len(original) == group["count"]
    assert {r["source_path"] for r in rows} == original.keys()
    for row in rows:
        src, dst = row["source_path"], row["destination_path"]
        assert src == dst and dst not in destinations and dst not in before
        assert original[src] == after[dst]
        entry(row, dst, after)
        destinations.add(dst)
assert len(destinations) == 102
assert changed == existing | destinations | {p for p in after if p.startswith(PREFIX)}
manifest = load(PREFIX + "artifact-manifest.json")
assert manifest["integration_base"] == BASE and manifest["member_count"] == 117
assert {r["path"] for r in manifest["members"]} == changed - {PREFIX + "artifact-manifest.json"}
for row in manifest["members"]:
    entry(row, row["path"], after)
    assert row["change"] == ("M" if row["path"] in before else "A")
assert digest(git("show", HEAD + ":" + PREFIX + "artifact-manifest.json")) == "5f87e26bb79c0c832c14e0d94d16df074b4f72e806d93c5012049c059ba3ca0e"
inner = load("docs/restart/implementation/QH01/native-qr-probe/artifact-manifest.json")
assert inner["members"] == len(inner["files"]) == 80
for row in inner["files"]:
    entry(row, row["path"], after)
correspondence = load(PREFIX + "source-correspondence.json")
assert correspondence["original_source_base"] == "d41a37e25cd0a86d3a47294f8d0ba24913128a21"
assert correspondence["delivery_base"] == BASE and len(correspondence["bindings"]) == 5
source_bindings = load("docs/restart/implementation/QH01/native-qr-probe/source-bindings.json")
assert {r["path"] for r in correspondence["bindings"]} == {r["path"] for r in source_bindings["bindings"]}
for row in correspondence["bindings"]:
    path = row["path"]
    assert tree(row["source"], path)[path] == before[path] == after[path]
    entry(row, path, after)
context = load(PREFIX + "checks/metadata-01/context.json")
assert context["source_head"] == BASE and len(context["input_hashes"]) == 20
for row in context["input_hashes"]:
    assert digest(blob(after[row["path"]][1])) == row["sha256"], row["path"]
env = git("show", HEAD + ":" + context["environment_path"])
assert digest(env) == context["environment_sha256"]
assert digest(json.dumps(json.loads(env), sort_keys=True).encode()) == context["explicit_environment_sha256"]
assert digest(Path(context["python_executable"]).read_bytes()) == context["python_sha256"]
commands = load(PREFIX + "checks/metadata-01/commands.json")
assert [r["label"] for r in commands] == ["docs", "plan", "frozen-evidence", "contract-source"]
assert all(r["exit_code"] == 0 for r in commands)
for row in commands:
    assert digest(git("show", HEAD + ":" + PREFIX + "checks/metadata-01/" + row["log"])) == row["sha256"]
old, new = load("plan/work-items.json", BASE), load("plan/work-items.json")
assert {k:v for k,v in old.items() if k not in {"tasks", "revision", "as_of"}} == {k:v for k,v in new.items() if k not in {"tasks", "revision", "as_of"}}
old_tasks, new_tasks = ({t["id"]:t for t in graph["tasks"]} for graph in [old, new])
assert old_tasks.keys() == new_tasks.keys() and len(new_tasks) == 47
for task_id in old_tasks:
    if task_id != "QH01":
        assert old_tasks[task_id] == new_tasks[task_id], task_id
qh_before, qh_after = old_tasks["QH01"], new_tasks["QH01"]
assert len(new_tasks["QP01"]["result_artifacts"]) == 84
assert {k:v for k,v in qh_before.items() if k not in {"current_checkpoint", "result_artifacts"}} == {k:v for k,v in qh_after.items() if k not in {"current_checkpoint", "result_artifacts"}}
assert len(qh_before["result_artifacts"]) == 158 and len(qh_after["result_artifacts"]) == 265
assert qh_after["result_artifacts"][:158] == qh_before["result_artifacts"]
for row in qh_after["result_artifacts"]:
    assert digest(blob(after[row["path"]][1])) == row["sha256"], row["path"]
assert qh_after["current_checkpoint"]["ingress_adoption"] == qh_before["current_checkpoint"]["current_adoption"]
for task_id in ["QH01", "QP01", "Q02"]:
    assert new_tasks[task_id]["status"] == "planned"
    assert new_tasks[task_id]["reviewer"] is None and new_tasks[task_id]["review_verdict"] is None
result = load(PREFIX + "result.json")
assert len(result["acceptance_assessments"]) == 14 and all(r["state"] == "incomplete" for r in result["acceptance_assessments"])
for path in changed:
    if path.endswith(".json"):
        json.loads(blob(after[path][1]))
print(json.dumps({
    "candidate": HEAD, "tree": EXPECTED_TREE, "base": BASE,
    "changed_paths": 118, "new_paths": 115, "existing_paths": sorted(existing),
    "exact_public_copies_mode_blob_size_sha256": 102, "copy_groups": [11,81,10],
    "outer_manifest_members_verified": 117, "inner_manifest_members_verified": 80,
    "original_Pi_input_bindings_equal_current_base": 5,
    "stable_gate_input_hashes": 20, "four_original_metadata_logs_hashes_and_exits": True,
    "original_environment_and_current_pinned_python_hashes_match": True,
    "other46_full_task_records_exact": True, "all47_acceptance_dependencies_resources_releases_states_exact": True,
    "old_QH158_artifact_prefix_exact": True, "QH265_artifact_hashes_match": True,
    "old_QP_preparation_and84_artifacts_exact": True,
    "task_status_counts_unchanged": dict(Counter(t["status"] for t in new["tasks"])),
    "all5QH_3QP_6Q02_criteria_incomplete": True,
    "scope": "Frozen source/metadata correspondence only; existing component reviews and actual runs reused, not rerun. No native/physical/task qualification. Protected PR and actual-main gates remain required."
}, indent=2))
