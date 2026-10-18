#!/usr/bin/env python3
"""A02 source recovery and canonical validation; no consolidation/import operation."""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

from rehearse import PreflightError, Source, canonical, decode_json, digest, git, safe_path, select, validate_manifest, write_private


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Recorder:
    def __init__(self, root: Path):
        if root.exists() or root.is_symlink():
            raise PreflightError("destination must not exist")
        if root.absolute().parent != root.parent.resolve(strict=True):
            raise PreflightError("destination parent must be canonical and already exist")
        self.root = root
        root.mkdir(mode=0o700)
        self.rows = []
        self.environment = {"python": sys.version, "python_executable": sys.executable,
                            "python_sha256": digest(Path(sys.executable).read_bytes()),
                            "platform": platform.platform(), "machine": platform.machine(),
                            "git": subprocess.check_output(["git", "--version"]).decode().strip(),
                            "boundary": "Pinned user-space tools do not make the operating system or hosted runner hermetic."}
        write_private(root / "environment.json", canonical(self.environment))

    def run(self, label: str, command: list[str], cwd: Path, expected: int = 0) -> bytes:
        started = now()
        process = subprocess.run(command, cwd=cwd, capture_output=True)
        filename = f"{len(self.rows):02d}-{label}.log"
        output = process.stdout + process.stderr
        write_private(self.root / filename, output)
        self.rows.append({"label": label, "command": command, "cwd": str(cwd),
                          "started_utc": started, "ended_utc": now(), "exit_code": process.returncode,
                          "log": filename, "sha256": digest(output),
                          "environment_sha256": digest(canonical(self.environment))})
        (self.root / "commands.json").write_bytes(canonical(self.rows))
        os.chmod(self.root / "commands.json", 0o600)
        if process.returncode != expected:
            raise PreflightError(f"{label} failed ({process.returncode}); protected log retained")
        return process.stdout


def protected_destination(output: Path, source_root: Path, manifest: dict) -> Path:
    output = output.absolute()
    for source in manifest["sources"]:
        if output.is_relative_to(source_root / safe_path(source["directory"])):
            raise PreflightError("output must not be inside a canonical source")
    return output


def recover(manifest: dict, source_root: Path, output: Path) -> dict:
    validate_manifest(manifest)
    output = protected_destination(output, source_root, manifest)
    prior_umask = os.umask(0o077)
    try:
        recorder = Recorder(output)
        rows = []
        for entry in manifest["sources"]:
            source = Source(source_root, entry)
            try:
                # Freeze object IDs, not live ref names. Source refs are read only.
                refs = []
                for line in git(source.repo, "for-each-ref", "--format=%(refname) %(objectname)").decode().splitlines():
                    name, oid = line.split()
                    safe_path(name)
                    if not re.fullmatch(r"[0-9a-f]{40}", oid):
                        raise PreflightError("non-SHA1 source ref needs explicit format support")
                    refs.append({"ref": name, "object": oid})
                refs.append({"ref": "refs/a02/selected-source", "object": source.commit})
                capture = output / (source.name + "-capture.git")
                restored = output / (source.name + "-restored.git")
                bundle = output / (source.name + ".bundle")
                recorder.run(source.name + "-capture-init", ["git", "init", "--bare", str(capture)], output)
                recorder.run(source.name + "-capture-fetch", ["git", "-C", str(capture), "fetch", "--no-tags", str(source.repo),
                             *[f"+{r['object']}:{r['ref']}" for r in refs]], output)
                recorder.run(source.name + "-bundle", ["git", "-C", str(capture), "bundle", "create", str(bundle), "--all"], output)
                recorder.run(source.name + "-verify", ["git", "-C", str(capture), "bundle", "verify", str(bundle)], output)
                recorder.run(source.name + "-restore-init", ["git", "init", "--bare", str(restored)], output)
                recorder.run(source.name + "-restore-fetch", ["git", "-C", str(restored), "fetch", str(bundle), "+refs/*:refs/*"], output)
                recorder.run(source.name + "-restore-fsck", ["git", "-C", str(restored), "fsck", "--full", "--strict"], output)
                restored_tree = git(restored, "rev-parse", source.commit + "^{tree}").decode().strip()
                if restored_tree != source.tree:
                    raise PreflightError("restored selected tree mismatch")
                for reference in refs:
                    actual = git(restored, "rev-parse", reference["ref"]).decode().strip()
                    if actual != reference["object"]:
                        raise PreflightError("restored source ref mismatch")
                private_record = {"source": source.name, "refs": refs, "selected_commit": source.commit,
                                  "selected_tree": source.tree, "bundle_sha256": digest(bundle.read_bytes())}
                write_private(output / (source.name + "-refs.json"), canonical(private_record))
                rows.append({"source": source.name, "visibility": entry["visibility"],
                             "selected_commit": source.commit, "selected_tree": source.tree,
                             "preserved_ref_count": len(refs), "refs_record_sha256": digest(canonical(private_record)),
                             "bundle_bytes": bundle.stat().st_size, "bundle_sha256": private_record["bundle_sha256"],
                             "restore_tree_equal": True, "restore_refs_equal": True, "fsck_exit_code": 0})
            finally:
                source.close()
        summary = {"scope": "Protected source-history recovery only; no target assembly or private history publication",
                   "manifest_sha256": digest(canonical(manifest)), "sources": rows,
                   "all_restored": True, "raw_logs_visibility": "private local runtime only",
                   "commands_sha256": digest(canonical(recorder.rows)), "import_allowed": False}
        write_private(output / "summary.json", canonical(summary))
        return summary
    finally:
        os.umask(prior_umask)


def canonical_plan(manifest: dict, source_root: Path, output: Path, python: Path) -> dict:
    validate_manifest(manifest)
    entry = next(e for e in manifest["sources"] if e["name"] == manifest["graph"]["source"])
    source = Source(source_root, entry)
    try:
        if git(source.repo, "rev-parse", "HEAD").decode().strip() != source.commit:
            raise PreflightError("canonical checkout must match pinned graph commit")
        if git(source.repo, "status", "--porcelain"):
            raise PreflightError("canonical checkout must be clean for direct validator execution")
        graph_path = manifest["graph"]["path"]
        graph = decode_json(source.blob(graph_path))
        bound = {graph_path, "scripts/validate_restart_plan.py", "scripts/test_validate_restart_plan.py"}
        for task in graph["tasks"]:
            if task.get("status") in {"verified", "integrated"}:
                bound.update(a["path"] for a in task["result_artifacts"])
        def correspondence():
            for path in sorted(bound):
                if (source.repo / safe_path(path)).read_bytes() != source.blob(path):
                    raise PreflightError(f"canonical validator input differs from Git: {path}")
        correspondence()
        recorder = Recorder(protected_destination(output, source_root, manifest))
        recorder.run("canonical-plan", [str(python), "-I", "-B", "scripts/validate_restart_plan.py"], source.repo)
        recorder.run("canonical-plan-controls", [str(python), "-I", "-B", "-m", "unittest", "discover", "-s", "scripts", "-p", "test_validate_restart_plan.py", "-v"], source.repo)
        correspondence()
        if git(source.repo, "rev-parse", "HEAD").decode().strip() != source.commit or git(source.repo, "status", "--porcelain"):
            raise PreflightError("canonical checkout changed during validator execution")
        summary = {"source_commit": source.commit, "source_tree": source.tree, "bound_file_count": len(bound),
                   "validator_path": "scripts/validate_restart_plan.py",
                   "validator_sha256": digest(source.blob("scripts/validate_restart_plan.py")),
                   "validator_exit_code": 0, "negative_controls_exit_code": 0,
                   "before_after_source_correspondence": True, "commands_sha256": digest(canonical(recorder.rows)),
                   "scope": "Full existing canonical validator and controls; structural proof only, not substantive review."}
        write_private(output / "summary.json", canonical(summary))
        return summary
    finally:
        source.close()


def public_refs(manifest: dict, source_root: Path, output: Path) -> dict:
    validate_manifest(manifest)
    recorder = Recorder(protected_destination(output, source_root, manifest))
    rows = []
    for entry in manifest["sources"]:
        if entry["visibility"] != "public":
            continue
        source = Source(source_root, entry)
        try:
            url = "https://github.com/" + entry["repository"] + ".git"
            raw = recorder.run(source.name + "-public-refs", ["git", "ls-remote", "--heads", "--tags", url], source_root)
            remote = dict((name, oid) for oid, name in (line.split() for line in raw.decode().splitlines()))
            main = remote.get("refs/heads/main")
            if not main:
                raise PreflightError("public main reference unavailable")
            result = subprocess.run(["git", "-C", str(source.repo), "merge-base", "--is-ancestor", source.commit, main], capture_output=True)
            if result.returncode:
                raise PreflightError(f"selected public source not established in remote main: {source.name}")
            local_tags = source.identity()["local_tags"]
            matched = []
            for tag in local_tags:
                if tag["ref"].startswith("refs/tags/evidence/"):
                    if remote.get(tag["ref"]) != tag["object"]:
                        raise PreflightError(f"reviewed evidence tag mismatch: {source.name}")
                    matched.append(tag)
            rows.append({"source": source.name, "repository": entry["repository"], "selected_commit": source.commit,
                         "remote_main": main, "selected_in_remote_main_history": True,
                         "reviewed_evidence_tags": matched, "remote_refs_sha256": digest(raw)})
        finally:
            source.close()
    summary = {"observed_utc": now(), "public_sources": rows, "commands_sha256": digest(canonical(recorder.rows)),
               "scope": "Read-only public ref reconciliation; evidence tags identify preserved reviews, not product releases."}
    write_private(output / "summary.json", canonical(summary))
    return summary


def overlay_chain(manifest: dict, source_root: Path) -> dict:
    """Check declared patch provenance and hash continuity without assembling files."""
    validate_manifest(manifest)
    sources = {}
    try:
        for entry in manifest["sources"]:
            sources[entry["name"]] = Source(source_root, entry)
        if manifest.get("corrected_s01_inputs"):
            for path, expected in manifest["corrected_s01_inputs"].items():
                if digest(sources["nsealr"].blob(path)) != expected:
                    raise PreflightError("corrected S01 input hash mismatch")
        current, rows = {}, []
        seen_patches = {}
        for overlay in manifest.get("overlays", []):
            owner = sources[overlay["record_source"]]
            target = sources[overlay["target_source"]]
            record_bytes = owner.blob(overlay["manifest_path"])
            patch_bytes = owner.blob(overlay["patch_path"])
            if digest(record_bytes) != overlay["manifest_sha256"] or digest(patch_bytes) != overlay["patch_sha256"]:
                raise PreflightError("overlay source artifact hash mismatch")
            record = decode_json(record_bytes)
            if (record["repository"] != target.entry["repository"] or record["commit"] != target.commit
                    or record["patch_sha256"] != overlay["patch_sha256"]):
                raise PreflightError("overlay source identity mismatch")
            after = record.get("apply_after")
            if after and seen_patches.get(after["patch"]) != after["sha256"]:
                raise PreflightError("overlay prerequisite missing or reordered")
            files = []
            for path, change in record["files"].items():
                safe_path(path)
                if select(path, target.entry)["action"] not in {"retain", "transform"}:
                    raise PreflightError("overlay path is not explicitly selected")
                key = (target.name, path)
                preimage = current.get(key, digest(target.blob(path)))
                if change["before_sha256"] != preimage:
                    raise PreflightError("overlay preimage chain mismatch")
                if not re.fullmatch(r"[0-9a-f]{64}", change["after_sha256"]):
                    raise PreflightError("invalid overlay postimage hash")
                current[key] = change["after_sha256"]
                files.append({"path": path, **change})
            seen_patches[overlay["patch_path"]] = overlay["patch_sha256"]
            rows.append({**overlay, "record_commit": owner.commit, "target_commit": target.commit, "files": files})
        return {"manifest_sha256": digest(canonical(manifest)), "overlays": rows,
                "effective_postimages": [{"source": name, "path": path, "sha256": sha}
                                         for (name, path), sha in sorted(current.items())],
                "scope": "Source manifests and patch digests verified; hash chain only. Actual application and resulting bytes require admitted import verification.",
                "import_allowed": False}
    finally:
        for source in sources.values():
            source.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("recover", "canonical-plan", "public-refs", "overlay-chain"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    args = parser.parse_args()
    try:
        manifest = decode_json(args.manifest.read_bytes())
        root = args.source_root.resolve(strict=True)
        if args.command == "recover":
            result = recover(manifest, root, args.destination.absolute())
        elif args.command == "canonical-plan":
            result = canonical_plan(manifest, root, args.destination.absolute(), args.python)
        elif args.command == "public-refs":
            result = public_refs(manifest, root, args.destination.absolute())
        else:
            result = overlay_chain(manifest, root)
            recorder = Recorder(protected_destination(args.destination.absolute(), root, manifest))
            write_private(recorder.root / "summary.json", canonical(result))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, KeyError, TypeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
