#!/usr/bin/env python3
"""Inventory pinned Git objects and preflight A02; never import or mutate a source."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


REGULAR_MODES = {"100644", "100755"}
ACTIONS = {"retain", "transform", "deduplicate", "retire", "exclude"}
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class PreflightError(ValueError):
    """A source or manifest does not satisfy the inventory contract."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreflightError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def decode_json(data: bytes) -> object:
    return json.loads(data, object_pairs_hook=unique_object)


def canonical(data: object) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode()


def safe_path(value: str) -> str:
    if (not isinstance(value, str) or not value or "\\" in value
            or any(ord(c) < 32 for c in value)):
        raise PreflightError(f"unsafe repository path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in {".", "..", ".git"} for p in value.split("/")):
        raise PreflightError(f"unsafe repository path: {value!r}")
    if path.as_posix() != value:
        raise PreflightError(f"noncanonical repository path: {value!r}")
    return value


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if result.returncode:
        # Do not print arbitrary Git diagnostics or configured credential URLs.
        raise PreflightError(f"Git read failed ({args[0]}) in {repo.name}")
    return result.stdout


class Source:
    def __init__(self, root: Path, entry: dict):
        self.entry = entry
        self.name = entry["name"]
        self.repo = root / safe_path(entry["directory"])
        if self.repo.is_symlink() or self.repo.resolve() != self.repo:
            raise PreflightError(f"source path contains symlink: {self.name}")
        self.commit = entry["commit"]
        if not isinstance(self.commit, str) or not HEX40.fullmatch(self.commit):
            raise PreflightError(f"exact commit required: {self.name}")
        actual = git(self.repo, "rev-parse", self.commit + "^{commit}").decode().strip()
        if actual != self.commit:
            raise PreflightError(f"commit mismatch: {self.name}")
        self.tree = git(self.repo, "rev-parse", self.commit + "^{tree}").decode().strip()
        if self.tree != entry["tree"]:
            raise PreflightError(f"tree mismatch: {self.name}")
        self.files = {}
        for row in git(self.repo, "ls-tree", "-rz", "--full-tree", self.commit).split(b"\0"):
            if not row:
                continue
            metadata, raw_path = row.split(b"\t", 1)
            mode, kind, oid = metadata.decode().split()
            path = safe_path(raw_path.decode("utf-8"))
            self.files[path] = {"mode": mode, "kind": kind, "blob": oid}
        self._batch = subprocess.Popen(
            ["git", "-C", str(self.repo), "cat-file", "--batch"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._cache: dict[str, bytes] = {}

    def close(self) -> None:
        if self._batch.stdin:
            self._batch.stdin.close()
        if self._batch.stdout:
            self._batch.stdout.close()
        self._batch.wait()

    def blob(self, path: str) -> bytes:
        safe_path(path)
        info = self.files.get(path)
        if not info or info["kind"] != "blob":
            raise PreflightError(f"missing source blob: {self.name}:{path}")
        oid = info["blob"]
        if oid not in self._cache:
            assert self._batch.stdin and self._batch.stdout
            self._batch.stdin.write((oid + "\n").encode())
            self._batch.stdin.flush()
            header = self._batch.stdout.readline().decode().split()
            if len(header) != 3 or header[:2] != [oid, "blob"]:
                raise PreflightError(f"invalid Git blob response: {self.name}:{path}")
            data = self._batch.stdout.read(int(header[2]))
            if len(data) != int(header[2]) or self._batch.stdout.read(1) != b"\n":
                raise PreflightError("truncated Git blob response")
            self._cache[oid] = data
        return self._cache[oid]

    def identity(self) -> dict:
        refs = []
        for line in git(self.repo, "for-each-ref", "--format=%(refname) %(objectname) %(*objectname)", "refs/tags").decode().splitlines():
            parts = line.split()
            refs.append({"ref": parts[0], "object": parts[1], "peeled": parts[2] if len(parts) > 2 else None})
        return {"name": self.name, "repository": self.entry["repository"],
                "visibility": self.entry["visibility"], "commit": self.commit,
                "tree": self.tree, "local_tags": refs,
                "tag_limit": "Local refs only; remote correspondence still requires import admission.",
                "dirty_worktree_observed": bool(git(self.repo, "status", "--porcelain"))}


def select(path: str, entry: dict) -> dict:
    for rule in entry["rules"]:
        if (("path" in rule and path == rule["path"])
                or ("prefix" in rule and path.startswith(rule["prefix"]))
                or ("glob" in rule and fnmatch.fnmatchcase(path, rule["glob"]))):
            return rule
    return entry["default"]


def destination(path: str, rule: dict) -> str | None:
    if rule["action"] in {"deduplicate", "retire", "exclude"}:
        return None
    suffix = path[len(rule.get("prefix", "")):]
    return safe_path(rule["destination"].replace("{path}", path).replace("{suffix}", suffix))


def test_inventory(path: str, data: bytes) -> dict | None:
    if not (path.endswith((".test.ts", ".test.tsx"))
            or (path.endswith(".py") and Path(path).name.startswith("test_"))
            or (path.endswith(".rs") and b"#[test]" in data)):
        return None
    text = data.decode("utf-8")
    if path.endswith(".py"):
        tree = ast.parse(text)
        names = [node.name for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")]
        method = "Python AST test function definitions"
    elif path.endswith(".rs"):
        names = re.findall(r"#\[test\]\s*(?:pub\s+)?fn\s+(\w+)", text)
        method = "Rust literal #[test] function declarations"
    else:
        names = [m[1] for m in re.findall(r"\b(?:it|test)(?:\.\w+)*\s*\(\s*([\"'])(.*?)\1", text)]
        method = "TypeScript literal it/test labels; dynamic/generated cases need framework collection"
    return {"method": method, "static_names": sorted(names),
            "runtime_collection": "pending; static discovery is not complete per-case execution coverage"}


def markdown_links(path: str, data: bytes, files: dict) -> list[dict]:
    if not path.endswith(".md"):
        return []
    text = re.sub(r"(?ms)^```.*?^```[^\n]*", "", data.decode("utf-8"))
    targets = re.findall(r"\[[^\]\n]*\]\((<[^>]*>|[^)\n]*)\)", text)
    targets += re.findall(r"(?m)^\s*\[[^\]]+\]:\s*(\S+)", text)
    output = []
    for raw in targets:
        target = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw.split(' "', 1)[0]
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), unquote(parsed.path)))
        safe = not resolved.startswith(("/", "../")) and resolved != ".."
        is_file = resolved in files
        is_directory = any(p.startswith(resolved.rstrip("/") + "/") for p in files)
        output.append({"target": target, "resolved_path": resolved,
                       "exists_at_inventory_commit": safe and (is_file or is_directory),
                       "target_kind": "file" if is_file else "directory" if is_directory else "missing",
                       "interpretation": "historical link; unresolved origins require explicit source/reference reconciliation"})
    return output


def evidence_closure(source: Source, graph_path: str) -> dict:
    graph = decode_json(source.blob(graph_path))
    if not isinstance(graph, dict) or not isinstance(graph.get("tasks"), list):
        raise PreflightError("invalid task graph")
    tasks, records, errors = [], {}, []
    for task in graph["tasks"]:
        if task.get("status") not in {"verified", "integrated"}:
            continue
        task_id = task["id"]
        refs = {}
        for item in task.get("result_artifacts", []):
            path = safe_path(item["path"])
            if path in refs:
                raise PreflightError(f"duplicate closed artifact: {task_id}:{path}")
            if not HEX64.fullmatch(item.get("sha256", "")):
                raise PreflightError(f"invalid artifact digest: {task_id}:{path}")
            info = source.files.get(path)
            if not info or info["mode"] not in REGULAR_MODES:
                raise PreflightError(f"nonregular/missing closed artifact: {task_id}:{path}")
            data = source.blob(path)
            if digest(data) != item["sha256"]:
                raise PreflightError(f"closed artifact hash mismatch: {task_id}:{path}")
            refs[path] = item["sha256"]
            if path not in records:
                records[path] = {"path": path, **info, "sha256": item["sha256"], "tasks": [],
                                 "relative_links": markdown_links(path, data, source.files)}
            records[path]["tasks"].append(task_id)
        manifest_path = task.get("result_manifest")
        if manifest_path not in refs:
            raise PreflightError(f"result manifest outside hashed closure: {task_id}")
        result = decode_json(source.blob(manifest_path))
        if not isinstance(result, dict):
            raise PreflightError(f"invalid result manifest: {task_id}")
        for key in ("input_commits", "candidate_commits", "acceptance"):
            if result.get(key) != task.get(key):
                raise PreflightError(f"closed result {key} mismatch: {task_id}")
        expected_review = {"assignee": task.get("assignee"), "reviewer": task.get("reviewer"), "verdict": "pass"}
        if (not expected_review["reviewer"] or expected_review["reviewer"] == expected_review["assignee"]
                or result.get("review") != expected_review or task.get("review_verdict") != "pass"):
            raise PreflightError(f"closed result independent review mismatch: {task_id}")
        if (task.get("reviewed_input_commits") != task.get("input_commits")
                or task.get("reviewed_candidate_commits") != task.get("candidate_commits")):
            raise PreflightError(f"closed reviewed commit mismatch: {task_id}")
        outcomes = result.get("acceptance_results", [])
        if sorted(o.get("index", -1) for o in outcomes) != list(range(len(task["acceptance"]))):
            raise PreflightError(f"closed acceptance coverage mismatch: {task_id}")
        for outcome in outcomes:
            paths = outcome.get("evidence_paths", [])
            if (outcome.get("outcome") != "pass" or not paths
                    or any(p not in refs or p == manifest_path for p in paths)):
                raise PreflightError(f"closed acceptance evidence mismatch: {task_id}")
        tasks.append({"id": task_id, "artifact_references": len(refs), "manifest": manifest_path,
                      "input_commits": task["input_commits"], "candidate_commits": task["candidate_commits"],
                      "review": expected_review})
    unresolved = sum(not link["exists_at_inventory_commit"] for r in records.values() for link in r["relative_links"])
    if unresolved:
        errors.append(f"{unresolved} frozen relative links need original-source resolution; do not edit frozen bytes")
    return {"graph_path": graph_path, "graph_sha256": digest(source.blob(graph_path)),
            "source_commit": source.commit, "tasks": tasks,
            "artifacts": [records[p] for p in sorted(records)], "pending_reconciliation": errors}


def validate_manifest(manifest: dict) -> None:
    if manifest.get("format") != 1 or manifest.get("mode") != "preflight-only":
        raise PreflightError("only manifest format 1, preflight-only mode is implemented")
    names = []
    for source in manifest.get("sources", []):
        names.append(source["name"])
        if not re.fullmatch(r"[a-z0-9.][a-z0-9.-]*", source["name"]) or source["name"] in {".", ".."}:
            raise PreflightError("source name must be a safe single identifier")
        if source.get("visibility") not in {"public", "private"}:
            raise PreflightError("source visibility must be explicit")
        if "require_current_main" in source and not isinstance(source["require_current_main"], bool):
            raise PreflightError("current-main requirement must be a boolean")
        if source["visibility"] == "private" and source["default"]["action"] != "exclude":
            raise PreflightError("private sources require default exclusion")
        for rule in [*source["rules"], source["default"]]:
            if rule.get("action") not in ACTIONS or not rule.get("reason") or not rule.get("id"):
                raise PreflightError("every disposition needs action, id and reason")
            if rule["action"] in {"retain", "transform"} and not rule.get("destination"):
                raise PreflightError("selected file rule needs a destination")
    if not names or len(names) != len(set(names)):
        raise PreflightError("source names must be nonempty and unique")


def inventory(manifest: dict, root: Path) -> dict:
    validate_manifest(manifest)
    sources = {}
    try:
        for entry in manifest["sources"]:
            sources[entry["name"]] = Source(root, entry)
        files, tests, destinations, collisions, mismatch = [], [], {}, [], []
        for name, source in sources.items():
            notices = [p for p in source.files if re.fullmatch(r"(?:LICEN[CS]E|COPYING|NOTICE)(?:[.-].*)?", Path(p).name, re.I)]
            license_record = source.entry.get("root_license")
            if license_record and digest(source.blob(license_record["path"])) != license_record["sha256"]:
                raise PreflightError(f"root license mismatch: {name}")
            for path, info in source.files.items():
                rule = select(path, source.entry)
                target = destination(path, rule)
                if target and info["mode"] not in REGULAR_MODES:
                    raise PreflightError(f"nonregular selected source: {name}:{path}")
                row = {"source": name, "commit": source.commit, "path": path, **info,
                       "action": rule["action"], "rule": rule["id"], "reason": rule["reason"],
                       "destination": target, "sha256": None}
                data = None
                if info["kind"] == "blob" and rule["action"] != "exclude":
                    data = source.blob(path)
                    row["sha256"] = digest(data)
                if target:
                    if target in destinations:
                        collisions.append({"target": target, "first": destinations[target], "second": [name, path]})
                    destinations[target] = [name, path]
                    row["license_candidates"] = [
                        p for p in notices if path == p or "/" not in p
                        or path.startswith(posixpath.dirname(p) + "/")]
                    row["rights_review"] = "pending selected-file notice/privacy review; root license is not blanket clearance"
                if rule["action"] == "deduplicate":
                    reference = sources[rule["canonical_source"]]
                    canonical_path = path[len(rule["prefix"]):]
                    expected = reference.files.get(canonical_path)
                    equal = bool(expected and expected["mode"] == info["mode"] and expected["blob"] == info["blob"])
                    row["canonical"] = {"source": reference.name, "path": canonical_path, "equal": equal}
                    if not equal:
                        mismatch.append({"source": name, "path": path, "canonical_path": canonical_path})
                if data is not None and (entry := test_inventory(path, data)):
                    tests.append({"source": name, "path": path, "sha256": row["sha256"], "action": rule["action"], **entry})
                files.append(row)
        graph = manifest["graph"]
        closure = evidence_closure(sources[graph["source"]], graph["path"])
        identities = [s.identity() for s in sources.values()]
        counts = {name: dict(Counter(f["action"] for f in files if f["source"] == name)) for name in sources}
        blockers = ["Source import/assembly is not implemented or enabled by this tooling candidate.",
                    "Final adopted S01 main tuple and successful main CI need coordinator reconciliation.",
                    "Selected-file rights/privacy/notice review and complete runtime case disposition remain pending.",
                    "Remote evidence refs, protected bundle creation/restoration and final closed-evidence closure need admission review."]
        if collisions:
            blockers.append(f"{len(collisions)} destination collisions require explicit disposition")
        if mismatch:
            blockers.append(f"{len(mismatch)} snapshot/source differences require final-tuple reconciliation")
        blockers.extend(closure["pending_reconciliation"])
        return {"format": 1, "mode": "preflight-only", "manifest_sha256": digest(canonical(manifest)),
                "sources": identities, "files": files, "tests": tests, "closed_evidence": closure,
                "destination_collisions": collisions, "snapshot_differences": mismatch,
                "bundle_plan": [{"source": s.name, "visibility": s.entry["visibility"],
                                 "selected_commit": s.commit, "local_refs": i["local_tags"],
                                 "destination": f"bundles/{s.name}.bundle", "executed": False,
                                 "requirement": "Private runtime only; verify all ref objects before creation, hash bundle, restore and verify commit/tree. Never import private history."}
                                for s, i in zip(sources.values(), identities)],
                "summary": {"disposition_counts": counts, "file_count": len(files),
                            "test_file_count": len(tests), "closed_tasks": [t["id"] for t in closure["tasks"]],
                            "closed_artifact_references": sum(t["artifact_references"] for t in closure["tasks"]),
                            "unique_closed_artifacts": len(closure["artifacts"]), "import_allowed": False,
                            "blockers": blockers}}
    finally:
        for source in sources.values():
            source.close()


def write_private(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)


def prepare(manifest_path: Path, root: Path, output: Path) -> dict:
    manifest = decode_json(manifest_path.read_bytes())
    if not isinstance(manifest, dict):
        raise PreflightError("manifest must be an object")
    root = root.resolve(strict=True)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise PreflightError("destination must not exist")
    if output.parent.resolve(strict=True) != output.parent:
        raise PreflightError("destination parent must exist and contain no symlinks")
    for source in manifest["sources"]:
        if output.is_relative_to(root / source["directory"]):
            raise PreflightError("destination must not be inside a source repository")
    report = inventory(manifest, root)
    output.mkdir(mode=0o700)
    write_private(output / "manifest.json", canonical(manifest))
    write_private(output / "inventory.json", canonical(report))
    write_private(output / "runtime.json", canonical({"source_root": str(root), "inventory_sha256": digest(canonical(report))}))
    return report["summary"]


def preflight(output: Path) -> dict:
    runtime = decode_json((output / "runtime.json").read_bytes())
    previous = (output / "inventory.json").read_bytes()
    if digest(previous) != runtime["inventory_sha256"]:
        raise PreflightError("recorded inventory hash mismatch")
    manifest = decode_json((output / "manifest.json").read_bytes())
    report = inventory(manifest, Path(runtime["source_root"]))
    original = decode_json(previous)
    # Mutable tags and checkout dirty state are observations, not imported input.
    for key in ("manifest_sha256", "files", "tests", "closed_evidence"):
        if report[key] != original[key]:
            raise PreflightError(f"preflight changed recorded {key}")
    return report["summary"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare", help="write protected inventory/plans only; no repository or bundle creation")
    prepare_parser.add_argument("--manifest", type=Path, required=True)
    prepare_parser.add_argument("--source-root", type=Path, required=True)
    prepare_parser.add_argument("--destination", type=Path, required=True)
    check = commands.add_parser("preflight", help="recheck frozen inventory; returns 2 while import is blocked")
    check.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.manifest, args.source_root, args.destination) if args.command == "prepare" else preflight(args.destination)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if args.command == "prepare" else 2
    except (OSError, KeyError, TypeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
