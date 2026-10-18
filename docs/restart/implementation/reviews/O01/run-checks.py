#!/usr/bin/env python3
"""Bounded independent O01 review checks; no author-worktree writes."""
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent / "evidence"
CANDIDATE = "b040f03a203c61e54e272c3f8bee028c9ee083cf"
OUT.mkdir(exist_ok=True)
records = []

def utc():
    return datetime.now(timezone.utc).isoformat()

def dump(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")

def run(name, argv, cwd=ROOT, expected=0):
    started = utc()
    p = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    path = OUT / (name + ".log")
    path.write_text(p.stdout.rstrip("\n") + ("\n" if p.stdout else ""))
    records.append({"argv": argv, "cwd": str(cwd), "started_utc": started,
                    "finished_utc": utc(), "exit_code": p.returncode, "expected_exit_code": expected,
                    "log": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "output_transform": "Normalize final newline only; retain all output content."})
    dump("commands.json", records)
    assert p.returncode == expected, (name, p.returncode, p.stdout)
    return p.stdout

assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == CANDIDATE
dump("environment.json", {"utc": utc(), "candidate": CANDIDATE,
     "python_executable": sys.executable, "python_version": sys.version,
     "platform": platform.platform(), "machine": platform.machine(),
     "reviewer": "/root/independent_controls_review",
     "model_assignment": "Parent assigned requested gpt-6-astra / xhigh. No hosted identity introspection claimed.",
     "dirty_state_before_checks": subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT, text=True),
     "scope": "Only this review directory is authored; disposable archive below system temporary directory."})
run("plan", [sys.executable, "scripts/validate_restart_plan.py"])
run("negative-suite", [sys.executable, "-m", "unittest", "discover", "-s", "scripts", "-p", "test_validate_restart_plan.py", "-v"])
run("make-test", ["make", "test"])

# Mutate real closed-task inputs from the exact candidate, preserving a valid control.
archive = subprocess.check_output(["git", "archive", CANDIDATE, "scripts", "docs/restart"], cwd=ROOT)
tamper = []
with tempfile.TemporaryDirectory(prefix="nsealr-o01-review-") as name:
    copy = Path(name)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
        tf.extractall(copy, filter="data")
    cmd = [sys.executable, "scripts/validate_restart_plan.py"]
    run("archive-valid", cmd, copy)
    artifact = copy / "docs/restart/implementation/S02/evidence/crypto/vectors.log"
    original = artifact.read_bytes()
    artifact.write_bytes(original + b"\nO01 independent evidence-tamper sentinel\n")
    output = run("reject-real-s02-artifact", cmd, copy, 1)
    assert "S02: artifact hash mismatch docs/restart/implementation/S02/evidence/crypto/vectors.log" in output
    tamper.append({"mutation": "Append bytes to integrated S02 underlying vectors.log without changing manifest.",
                   "original_sha256": hashlib.sha256(original).hexdigest(),
                   "tampered_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                   "result": "Rejected with exact S02 artifact hash mismatch; no unrelated failure needed."})
    artifact.write_bytes(original)
    plan_path = copy / "docs/restart/work-items.json"
    original_plan = plan_path.read_bytes()
    plan = json.loads(original_plan)
    s02 = next(t for t in plan["tasks"] if t["id"] == "S02")
    original_candidate = s02["candidate_commits"]["nSealr/nsealr"]
    s02["candidate_commits"]["nSealr/nsealr"] = CANDIDATE
    plan_path.write_text(json.dumps(plan))
    output = run("reject-real-s02-candidate", cmd, copy, 1)
    assert "S02: review input/candidate mismatch" in output
    assert "S02: evidence input/candidate mismatch" in output
    tamper.append({"mutation": "Replace integrated S02 candidate with another real repository commit, retaining original review and manifest.",
                   "original_candidate": original_candidate, "tampered_candidate": CANDIDATE,
                   "result": "Rejected by both reviewed candidate and result-manifest correspondence."})
    plan_path.write_bytes(original_plan)
    run("archive-restored-valid", cmd, copy)
dump("tamper-results.json", {"candidate": CANDIDATE, "experiments": tamper,
     "control_before_and_after": "pass", "author_worktrees_mutated": False,
     "limits": "Integrity rejection only; no arbitrary evidence truth, actor identity or physical proof is established."})

run("worktrees", ["git", "worktree", "list", "--porcelain"])
run("main-and-candidate-refs", ["git", "ls-remote", "origin", "refs/heads/main", "refs/heads/restart/goal-progress"])
fields = "number,title,state,isDraft,headRefName,headRefOid,mergeCommit,mergedAt,statusCheckRollup,url"
for number in (9, 10, 11, 12, 13, 14):
    run(f"pr-{number}", ["gh", "pr", "view", str(number), "--repo", "nSealr/nsealr", "--json", fields])
for task, commit in [("R00", "9194e292aa8a3176874cc9bf5814cefc26b6fe1a"),
                     ("S02", "e214fc57e7f853aa8d296f20e64bc167d47114b3"),
                     ("A01", "abfd8277925dc2623568e00fe14f4d682c19ac51")]:
    run(f"main-ci-{task}", ["gh", "run", "list", "--repo", "nSealr/nsealr", "--commit", commit,
        "--json", "databaseId,workflowName,status,conclusion,headSha,event,url"])
for repo in ("companion", "specs"):
    run(repo + "-prs", ["gh", "pr", "list", "--repo", "nSealr/" + repo, "--state", "all", "--limit", "10", "--json", fields])
print("O01 independent structural, real evidence tamper, and live-state capture completed.")
