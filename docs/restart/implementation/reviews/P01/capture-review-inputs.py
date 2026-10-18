#!/usr/bin/env python3
"""Capture immutable review inputs; this is evidence collection, not a prose test."""
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import subprocess
import urllib.request

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[4]
CANDIDATE = "df4cff34b4733aaac04db9b176db7c4edfc256d8"
INITIAL = "2d68108d50517c93e08b29cb6d7b6d6cf35f62cf"
INPUT = "768e8a35ae541f53f5da9c7bea7bf5c577fb474d"
PIN = "37db639582d857e12468dcccd99b2c7f1d657da9"
FILES = [
    "docs/restart/product-contract.md",
    "docs/restart/implementation/P01/brief.md",
    "docs/restart/implementation/P01/requirements.md",
    "docs/restart/implementation/P01/event-review-contract.md",
    "docs/restart/implementation/P01/threat-models.md",
    "docs/restart/client-qualification.md",
]
CONTEXT = [
    "AGENTS.md", "docs/restart/work-items.json", "docs/restart/execution.md",
    "docs/restart/development.md", "docs/restart/repositories.md",
    "docs/restart/implementation/README.md", "docs/restart/implementation/handoff.md",
]
COMMANDS = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(*args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True)
    COMMANDS.append({"argv": list(args), "exit_code": result.returncode,
                     "stdout_sha256": sha(result.stdout),
                     "stderr": result.stderr.decode(errors="replace")})
    result.check_returncode()
    return result.stdout


def bind(commit, paths):
    rows = []
    for path in paths:
        body = run("git", "show", f"{commit}:{path}")
        rows.append({"path": path, "bytes": len(body), "sha256": sha(body),
                     "git_blob": run("git", "rev-parse", f"{commit}:{path}").decode().strip()})
    return rows


def source(number):
    url = f"https://raw.githubusercontent.com/nostr-protocol/nips/{PIN}/{number:02d}.md"
    with urllib.request.urlopen(url, timeout=45) as response:
        body = response.read()
        return {"nip": number, "url": url, "status": response.status,
                "bytes": len(body), "sha256": sha(body)}


def main():
    report = {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reviewer": "/root/independent_security_review",
        "input_commit": INPUT, "initial_review_candidate": INITIAL,
        "reviewed_candidate": CANDIDATE,
        "initial_authored_files": bind(INITIAL, FILES),
        "final_authored_files": bind(CANDIDATE, FILES),
        "context_files": bind(CANDIDATE, CONTEXT),
        "semantic_delta": run("git", "diff", "--stat", INITIAL, CANDIDATE,
                              "--", *FILES).decode(),
    }
    graph = json.loads(run("git", "show", f"{CANDIDATE}:docs/restart/work-items.json"))
    report["observed_task_record"] = next(x for x in graph["tasks"] if x["id"] == "P01")
    report["github_pr"] = json.loads(run("gh", "pr", "view", "13", "--json",
        "headRefOid,baseRefName,state,isDraft,statusCheckRollup,url"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        report["pinned_primary_sources"] = list(executor.map(source,
            [1, 2, 7, 9, 10, 17, 18, 19, 25, 42, 44, 46, 49, 59, 65]))
    report["collection_commands"] = COMMANDS
    report["note"] = (
        "Digests bind inputs and observation times; neither successful retrieval nor CI "
        "establishes semantic acceptance. See review.json for independent analysis. "
        "An earlier read-only gh invocation requested unsupported baseRefOid and exited 1; "
        "the corrected invocation above uses baseRefName. No product tests were needed "
        "for this specification-only review, and no tests asserting prose existence were run.")
    (OUT / "input-bindings.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"candidate": CANDIDATE, "authored_files": len(FILES),
                      "primary_sources": len(report["pinned_primary_sources"]),
                      "input_bindings_sha256": sha((OUT / "input-bindings.json").read_bytes())}))


if __name__ == "__main__":
    main()
