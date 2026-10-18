#!/usr/bin/env python3
"""Independent source correspondence for a documentary P02 candidate; no code execution."""
import base64
import concurrent.futures
import datetime
import hashlib
import io
import json
import platform
import re
import subprocess
import tarfile
import urllib.request
from pathlib import Path

import yaml

CANDIDATE = "50d32a08e3e5fd245b4c8c8179c3619874b66076"
BASE = "f2ef70f522af4977e15f81554a8c6eadcdbe8097"
PREP = "79f238e3273bf2279f203b7566488609707db65d"
PREP_REVIEW = "b02ae0b4767ec41f42b1ea4202a192be6eca8189"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
RESEARCH = Path("/home/tux/nsealr/.restart-tools/goal/p02-research")
PREFIX = "docs/restart/implementation/P02/"
REPOS = {"hzrd149/nostrudel": RESEARCH / "nostrudel",
         "coracle-social/coracle": RESEARCH / "coracle",
         "nSealr/companion": Path("/home/tux/nsealr/companion"),
         "nSealr/nsealr": ROOT}


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read()


register = json.loads(git(ROOT, "show", CANDIDATE + ":" + PREFIX + "source-register.json"))
result = json.loads(git(ROOT, "show", CANDIDATE + ":" + PREFIX + "result.json"))
graph = json.loads(git(ROOT, "show", BASE + ":docs/restart/work-items.json"))
tasks = {item["id"]: item for item in graph["tasks"]}
paths = git(ROOT, "diff", "--name-only", BASE, CANDIDATE).decode().splitlines()
assert len(paths) == 12 and all(path.startswith((PREFIX, "docs/restart/implementation/reviews/P02-spec/")) for path in paths)
candidate_files = []
for path in paths:
    body = git(ROOT, "show", CANDIDATE + ":" + path)
    candidate_files.append({"path": path, "bytes": len(body), "sha256": sha(body),
                            "blob": git(ROOT, "rev-parse", CANDIDATE + ":" + path).decode().strip()})
for name in ("brief.md", "input-notes.json", "acceptance-plan.json"):
    assert git(ROOT, "show", CANDIDATE + ":" + PREFIX + name) == git(ROOT, "show", PREP + ":" + PREFIX + name)
review_paths = git(ROOT, "diff", "--name-only", PREP, PREP_REVIEW).decode().splitlines()
assert len(review_paths) == 4
for path in review_paths:
    assert git(ROOT, "show", CANDIDATE + ":" + path) == git(ROOT, "show", PREP_REVIEW + ":" + path)
for artifact in result["artifacts"]:
    assert sha(git(ROOT, "show", CANDIDATE + ":" + artifact["path"])) == artifact["sha256"]
assert [item["acceptance"] for item in result["criteria"]] == tasks["P02"]["acceptance"]
assert [item["index"] for item in result["criteria"]] == list(range(5))
source_records = []
for item in register["source_files"]:
    if "repository" not in item:
        continue
    repo = REPOS[item["repository"]]
    data = git(repo, "show", item["commit"] + ":" + item["path"])
    tree_line = git(repo, "ls-tree", item["commit"], "--", item["path"]).decode().split()
    assert tree_line[0] == item["mode"] and tree_line[2] == item["blob"]
    assert len(data) == item["bytes"] and sha(data) == item["sha256"]
    source_records.append(item)
locks = {}
for item in register["clients"]:
    repo = REPOS[item["repository"]]
    assert git(repo, "rev-parse", "HEAD").decode().strip() == item["commit"]
    assert git(repo, "rev-parse", "HEAD^{tree}").decode().strip() == item["tree"]
    assert not git(repo, "status", "--porcelain").strip()
    body = git(repo, "show", item["commit"] + ":pnpm-lock.yaml")
    assert sha(body) == item["lockfile_sha256"]
    locks[item["name"]] = yaml.safe_load(body)
    package = json.loads(git(repo, "show", item["commit"] + ":package.json"))
    assert package["version"] == item["package_version"]
    assert package["packageManager"] == item["package_manager"]
    for name, dependency in item["selected_dependencies"].items():
        locked = locks[item["name"]]["importers"]["."]["dependencies"][name]
        assert (locked["specifier"], locked["version"]) == (dependency["specifier"], dependency["resolved"])


def check_package(item):
    # Independently fetch official immutable version tarballs; never extract or execute them.
    data = fetch(item["tarball"])
    sri = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()
    locked = locks[item["client"]]["packages"][item["package"] + "@" + item["version"]]
    assert sri == item["integrity"] == locked["resolution"]["integrity"]
    assert len(data) == item["tarball_bytes"] and sha(data) == item["tarball_sha256"]
    captured_meta = RESEARCH / (item["package"].replace("@", "").replace("/", "-") + "-registry.json")
    assert sha(captured_meta.read_bytes()) == item["metadata_sha256"]
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        package_body = tar.extractfile("package/package.json").read()
        assert sha(package_body) == item["package_json_sha256"]
        package = json.loads(package_body)
        assert (package["name"], package["version"]) == (item["package"], item["version"])
        files = []
        for source in register["source_files"]:
            if source.get("package") == item["package"]:
                body = tar.extractfile(source["path"]).read()
                assert len(body) == source["bytes"] and sha(body) == source["sha256"]
                local = RESEARCH / "dependencies" / item["package"].replace("@", "").replace("/", "-") / source["path"]
                assert local.read_bytes() == body
                files.append({"id": source["id"], "path": source["path"], "sha256": sha(body)})
        return {"package": item["package"], "version": item["version"], "url": item["tarball"],
                "sha256": sha(data), "sri": sri, "locked_sri_equal": True, "files": files}


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    packages = list(pool.map(check_package, register["published_packages"]))
browser_records = []
for name, item in zip(("chrome", "firefox"), register["browser_candidates"]):
    body = (RESEARCH / (name + "-versions.json")).read_bytes()
    assert sha(body) == item["metadata_sha256"]
    doc = json.loads(body)
    if name == "chrome":
        assert doc["channels"]["Stable"]["version"] == item["version"]
        assert doc["channels"]["Stable"]["revision"] == item["revision"]
    else:
        assert doc["LATEST_FIREFOX_VERSION"] == item["version"]
    browser_records.append({"metadata_url": item["metadata_url"], "sha256": sha(body),
                            "version": item["version"], "captured_body_reused": True,
                            "executable_tested": False})
mdn = register["official_browser_compatibility"]
assert sha(fetch(mdn["url"])) == mdn["sha256"]
plan = git(ROOT, "show", CANDIDATE + ":" + PREFIX + "compatibility-plan.md").decode()
rows = [line for line in plan.splitlines() if re.match(r"\| P02-[A-Z]\d\d ", line)]
assert [re.match(r"\| (P02-[A-Z]\d\d)", line)[1] for line in rows] == result["scenarios"]
owners = sorted(set(re.findall(r"\b(?:QP?\d\d|QH\d\d|[A-Z]\d\dS?)\b", " ".join(line.split("|")[-2] for line in rows))))
assert set(owners) <= set(tasks), set(owners) - set(tasks)
subprocess.run(["git", "diff", "--check", BASE, CANDIDATE], cwd=ROOT, check=True)
record = {"candidate": CANDIDATE, "candidate_tree": git(ROOT, "rev-parse", CANDIDATE + "^{tree}").decode().strip(),
          "input": BASE, "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "command": "python3 docs/restart/implementation/reviews/P02-final/verify-bindings.py", "exit_code": 0,
          "environment": {"python": platform.python_version(), "pyyaml": yaml.__version__, "platform": platform.platform(),
                          "git": git(ROOT, "--version").decode().strip()},
          "candidate_files": candidate_files, "immutable_preparation_files": 3, "unchanged_review_files": review_paths,
          "result_artifact_hashes_equal": True, "criteria_equal": True, "all_other_tracked_source_unchanged": True,
          "git_source_bindings": source_records, "fresh_npm_tarball_checks": packages,
          "official_browser_capture_checks": browser_records, "fresh_mdn_body_equal": mdn,
          "scenario_owner_ids": owners,
          "remote_refs_snapshot": git(ROOT, "ls-remote", "origin", "refs/heads/main", "refs/heads/restart/p02-compatibility").decode().splitlines(),
          "result": "PASS source correspondence; substantive source and planning assessment is in review.md",
          "limits": ["No package installation, lifecycle script, client build, browser, relay, device or human session executed.",
                     "The two version API bodies are timestamped author captures, not repeated mutable API observations."]}
(HERE / "binding-verification.json").write_text(json.dumps(record, indent=2) + "\n")
print("PASS: 12 scoped files; 18 Git bindings; seven fresh lock-SRI tarballs and 12 registered bodies; exact prior copies/criteria; real scenario owner IDs")
