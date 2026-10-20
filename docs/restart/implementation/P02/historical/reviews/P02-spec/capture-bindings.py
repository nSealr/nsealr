#!/usr/bin/env python3
"""Capture exact P02 specification/source correspondence, not product qualification."""
import datetime
import hashlib
import json
import platform
import subprocess
from pathlib import Path

CANDIDATE = "79f238e3273bf2279f203b7566488609707db65d"
BASE = "f2ef70f522af4977e15f81554a8c6eadcdbe8097"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def command(*args):
    return subprocess.check_output(args, cwd=ROOT)


def git(*args):
    return command("git", *args).decode().strip()


def blob(commit, path):
    data = command("git", "show", f"{commit}:{path}")
    return {"path": path, "commit": commit,
            "blob": git("rev-parse", f"{commit}:{path}"),
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def source_json(commit, path):
    return json.loads(command("git", "show", f"{commit}:{path}"))


notes = source_json(CANDIDATE, "docs/restart/implementation/P02/input-notes.json")
plan = source_json(CANDIDATE, "docs/restart/implementation/P02/acceptance-plan.json")
graph = source_json(BASE, "docs/restart/work-items.json")
tasks = {item["id"]: item for item in graph["tasks"]}
expected_paths = [f"docs/restart/implementation/P02/{name}" for name in
                  ("acceptance-plan.json", "brief.md", "input-notes.json")]
changed = git("diff", "--name-only", BASE, CANDIDATE).splitlines()
assert changed == expected_paths, changed
assert git("rev-parse", CANDIDATE + "^") == BASE
assert notes["input_commit"] == BASE
assert notes["input_tree"] == git("rev-parse", BASE + "^{tree}")
bindings = [blob(item["commit"], item["path"]) for item in notes["source_bindings"]]
assert bindings == notes["source_bindings"]
assert all(item["commit"] == BASE for item in bindings)
assert notes["task_criteria"] == tasks["P02"]["acceptance"]
assert [item["text"] for item in plan["criteria"]] == tasks["P02"]["acceptance"]
assert [item["index"] for item in plan["criteria"]] == list(range(5))
assert tasks["P01"]["status"] == "integrated"
assert tasks["P02"]["status"] == "ready"
assert tasks["P02"]["depends_on"] == ["P01"]
owners = ["C01", "C02", "T01", "QH01", "Q01", "Q02", "Q03", "B01", "B02", "B03"]
assert all(owner in tasks for owner in owners)
command("git", "diff", "--check", BASE, CANDIDATE)
remote = git("ls-remote", "origin", "refs/heads/main", "refs/heads/restart/p02-compatibility")
issue = json.loads(command("gh", "issue", "view", "24", "--repo", "nSealr/nsealr",
                          "--json", "title,body,state,url"))
record = {
    "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "candidate": CANDIDATE, "candidate_tree": git("rev-parse", CANDIDATE + "^{tree}"),
    "base": BASE, "base_tree": notes["input_tree"], "candidate_parent_equals_base": True,
    "candidate_files": [blob(CANDIDATE, path) for path in changed],
    "source_bindings_recomputed_equal": bindings,
    "unchanged_criteria": tasks["P02"]["acceptance"],
    "indices": [item["index"] for item in plan["criteria"]],
    "task_state": {key: {field: tasks[key][field] for field in ("status", "depends_on")}
                   for key in ("P01", "P02")},
    "owning_tasks_inspected": {key: tasks[key]["title"] for key in owners},
    "graph_and_all_other_tracked_source_unchanged": True,
    "diff_check_exit": 0,
    "remote_refs_snapshot": remote.splitlines(),
    "assignment_snapshot": issue,
    "environment": {"platform": platform.platform(), "python": platform.python_version(),
                    "git": git("--version"),
                    "gh": command("gh", "--version").decode().splitlines()[0]},
    "commands": ["git show <commit>:<path>", "git rev-parse <commit>:<path>",
                 "git diff --name-only f2ef70f522af4977e15f81554a8c6eadcdbe8097 79f238e3273bf2279f203b7566488609707db65d",
                 "git diff --check f2ef70f522af4977e15f81554a8c6eadcdbe8097 79f238e3273bf2279f203b7566488609707db65d",
                 "git ls-remote origin refs/heads/main refs/heads/restart/p02-compatibility",
                 "gh issue view 24 --repo nSealr/nsealr --json title,body,state,url"],
    "result": "PASS exact source/scope/criteria correspondence; no runtime or research execution"
}
(HERE / "input-verification.json").write_text(json.dumps(record, indent=2) + "\n")
print(f"PASS: {len(bindings)} exact source bindings, {len(changed)} scoped files, 5 unchanged criteria")
