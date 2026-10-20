#!/usr/bin/env python3
"""Read-only delivery composition checks; no original plan acceptance rerun."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
CANDIDATE = "1db465e0371814f47ea17d297d5cb8d848e1680e"
BASE = "503719d5c607bdbcd1da30a89b0c3c6f5983c01b"
OLD_BASE = "b1c90139a651895284b2624da7d12903cf16bc9d"
ORIGINAL = "268d2c52456f107cf369b54316c29ef35be10751"
REVIEW = "36912cbab6dbf46a96c51f9f6078ca8d5178a17e"
PREFIX = "docs/restart/implementation/P02/delivery/"

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def body(commit, path):
    return git("show", commit + ":" + path)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def load(path):
    return json.loads(body(CANDIDATE, path))

def identity(commit, path):
    mode, kind, blob = git("ls-tree", commit, "--", path).decode().split("\t")[0].split()
    assert kind == "blob"
    raw = body(commit, path)
    return dict(mode=mode, blob=blob, bytes=len(raw), sha256=sha(raw))

assert git("rev-parse", "HEAD").decode().strip() == CANDIDATE
assert git("rev-parse", CANDIDATE + "^{tree}").decode().strip() == "56d7ea635539264d9c973a7c771249c76d15c1ab"
assert subprocess.run(["git", "merge-base", "--is-ancestor", BASE, CANDIDATE], cwd=ROOT).returncode == 0
delta = [r.split("\t") for r in git("diff", "--name-status", BASE, CANDIDATE).decode().splitlines()]
assert len(delta) == 48 and all(status == "A" for status, _ in delta)
original = [r.split("\t") for r in git("diff", "--name-status", OLD_BASE, ORIGINAL).decode().splitlines()]
assert len(original) == 32 and all(status == "A" for status, _ in original)
inventories = []
for _, path in original:
    current = identity(CANDIDATE, path)
    assert current == identity(ORIGINAL, path), path
    inventories.append(dict(path=path, source_commit=ORIGINAL, source_path=path, **current))

reconciliation = load(PREFIX + "reconciliation.json")
assert reconciliation["actual_base"] == BASE and reconciliation["original_base"] == OLD_BASE
actual_base_delta = git("diff", "--name-status", OLD_BASE, BASE).decode().splitlines()
assert actual_base_delta == reconciliation["base_delta_paths"]
base_rows = [row.split("\t") for row in actual_base_delta]
assert len(base_rows) == 129
assert {p for s, p in base_rows if s == "M"} == {
    "plan/work-items.json", "docs/restart/README.md", "docs/restart/implementation/handoff.md"}
assert len([1 for s, p in base_rows if s == "A" and p.startswith("docs/restart/implementation/A02/closure/")]) == 126
assert set(s for s, _ in base_rows) == {"A", "M"}

copies = reconciliation["review_copies"]
assert len(copies) == 9 and len({r["destination"] for r in copies}) == 9
original_review_paths = git("ls-tree", "-r", "--name-only", REVIEW, "--",
                            "docs/restart/implementation/reviews/P02-current-layout-final").decode().splitlines()
assert set(original_review_paths) == {r["source_path"] for r in copies}
for row in copies:
    assert row["source_commit"] == REVIEW
    source = identity(REVIEW, row["source_path"])
    assert source == identity(CANDIDATE, row["destination"]), row["destination"]
    assert all(row[k] == v for k, v in source.items()), row["destination"]
    inventories.append(dict(path=row["destination"], source_commit=REVIEW, source_path=row["source_path"], **source))
review_root = PREFIX + "evidence/root-review/"
review = load(review_root + "review.json")
assert review["candidate"] == ORIGINAL and review["reviewer"] == "/root"
assert review["author"] == "/root/b01_final_review" and review["distinct_agent"] is True
assert review["verdict"] == "PASS_documentary_current_layout_only"
assert sha(body(CANDIDATE, review_root + "review.json")) == reconciliation["review_sha256"]
assert len(review["artifacts"]) == 8
for item in review["artifacts"]:
    raw = body(CANDIDATE, review_root + item["path"])
    assert sha(raw) == item["sha256"] and len(raw) == item["bytes"]
assert {Path(r["destination"]).name for r in copies} == {a["path"] for a in review["artifacts"]} | {"review.json"}

expected = {p for _, p in original} | {r["destination"] for r in copies} | {
    PREFIX + p for p in ["README.md", "reconciliation.json", "commands.json", "affected-docs.log",
                        "current-plan.log", "frozen-evidence.log", "whitespace.json"]}
assert {p for _, p in delta} == expected
assert all(p.startswith("docs/restart/implementation/P02/") or p in {
    "docs/product/compatibility-plan.md", "docs/product/research-protocols.md"} for p in expected)

mapping = load("docs/restart/implementation/P02/integration/source-map.json")
contexts = reconciliation["context_reconciliation"]
assert len(contexts) == len(mapping["current_context"]) == 11
assert {r["path"] for r in contexts} == {r["current_path"] for r in mapping["current_context"]}
for row in contexts:
    old, current = body(OLD_BASE, row["path"]), body(BASE, row["path"])
    assert row["old_input_sha256"] == sha(old) and row["actual_base_sha256"] == sha(current)
    assert row["unchanged"] == (old == current)
assert [r["path"] for r in contexts if not r["unchanged"]] == ["plan/work-items.json"]
for row in mapping["current_context"]:
    assert row["current_commit"] == OLD_BASE and row["sha256"] == sha(body(OLD_BASE, row["current_path"]))

old_graph = json.loads(body(OLD_BASE, "plan/work-items.json"))
graph = json.loads(body(BASE, "plan/work-items.json"))
assert body(BASE, "plan/work-items.json") == body(CANDIDATE, "plan/work-items.json")
old_tasks, tasks = ({t["id"]: t for t in g["tasks"]} for g in (old_graph, graph))
assert len(tasks) == 47 and tasks.keys() == old_tasks.keys()
assert all(tasks[k]["acceptance"] == old_tasks[k]["acceptance"] and
           tasks[k]["depends_on"] == old_tasks[k]["depends_on"] for k in tasks)
assert all(tasks[k] == old_tasks[k] for k in tasks if k != "A02")
assert len(tasks["P02"]["acceptance"]) == 5 and tasks["P02"]["review_verdict"] is None
for key in ("resources", "release_paths"):
    assert graph[key] == old_graph[key]
assert len(graph["resources"]) == 16 and len(graph["release_paths"]) == 5
assert body(OLD_BASE, "plan/evidence-index.json") == body(BASE, "plan/evidence-index.json") == body(CANDIDATE, "plan/evidence-index.json")

for row in load(PREFIX + "commands.json"):
    assert row["exit_code"] == 0 and sha(body(CANDIDATE, PREFIX + row["log"])) == row["sha256"]
links = []
for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body(CANDIDATE, PREFIX + "README.md").decode()):
    if urlsplit(target).scheme:
        continue
    resolved = (ROOT / PREFIX / unquote(target.split("#")[0])).resolve()
    assert resolved.is_relative_to(ROOT) and resolved.is_file(), target
    links.append(dict(target=target, resolved=str(resolved.relative_to(ROOT))))

whitespace = load(PREFIX + "whitespace.json")
full = subprocess.run(["git", "diff", "--check", BASE, CANDIDATE], cwd=ROOT, capture_output=True)
nonlog = subprocess.run(["git", "diff", "--check", BASE, CANDIDATE, "--", ".", ":(exclude)*.log"], cwd=ROOT, capture_output=True)
assert full.returncode == whitespace["whole_staged_exit_code"] == 2
assert full.stdout.decode() == whitespace["whole_staged_diagnostic"]
assert nonlog.returncode == whitespace["nonlog_staged_exit_code"] == 0 and not nonlog.stdout
assert sha(body(CANDIDATE, PREFIX + "current-plan.log")) == whitespace["raw_log_sha256"]

result = dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), candidate=CANDIDATE,
              actual_base=BASE, candidate_additions=48, existing_edits=0, exact_original_copies=32,
              exact_root_review_copies=9, paired_root_manifest_members=8, delivery_records=7,
              base_delta=dict(paths=129, a02_additions=126, metadata_edits=3),
              contexts=11, contexts_changed=["plan/work-items.json"],
              all47_criteria_dependencies_preserved=True, other46_tasks_unchanged=True,
              resources=16, independent_release_paths=5, frozen_index_unchanged=True,
              source_and_target_copy_bindings=inventories, delivery_links=links,
              whitespace=dict(full_exit=2, nonlog_exit=0, preserved_raw_validator_log=True),
              status="PASS_delivery_composition_checks_only",
              limits="No self-approval of original plan content; no source/runtime/hardware/CI/task-closure acceptance.")
(OUT / "probe-result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k not in ("source_and_target_copy_bindings", "delivery_links")}, sort_keys=True))
