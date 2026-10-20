#!/usr/bin/env python3
"""Collect cases from an existing verified S01 runtime, without creating a target."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from admission import Recorder, overlay_chain, protected_destination
from rehearse import PreflightError, Source, canonical, decode_json, digest, git, write_private


PYTHON_COLLECTOR = """
import inspect,json,pathlib,unittest
suite=unittest.TestLoader().discover('tests')
rows=[]
def walk(node):
    if isinstance(node,unittest.TestSuite):
        for child in node: walk(child)
    else:
        if type(node).__name__=='_FailedTest': raise RuntimeError('test collection import failure: '+node.id())
        rows.append({'id':node.id(),'path':str(pathlib.Path(inspect.getfile(type(node))).resolve().relative_to(pathlib.Path.cwd())),
                     'skip_declared':bool(getattr(type(node),'__unittest_skip__',False) or getattr(getattr(node,node._testMethodName),'__unittest_skip__',False))})
walk(suite)
print(json.dumps(rows,sort_keys=True))
"""


def collect(manifest: dict, source_root: Path, runtime: Path, output: Path, env: dict | None = None) -> dict:
    recorder = Recorder(protected_destination(output, source_root, manifest))
    overlays = overlay_chain(manifest, source_root)
    effective = {(r["source"], r["path"]): r["sha256"] for r in overlays["effective_postimages"]}
    rows = []
    for name in ("companion", "specs", "raspberry", "lab"):
        entry = next(s for s in manifest["sources"] if s["name"] == name)
        source = Source(source_root, entry)
        checkout = runtime / entry["directory"]
        try:
            if git(checkout, "rev-parse", "HEAD").decode().strip() != source.commit:
                raise PreflightError(f"runtime source pin mismatch: {name}")
            bindings = []
            def correspondence():
                current = []
                for path, info in source.files.items():
                    actual = checkout / path
                    if info["kind"] != "blob" or actual.is_symlink():
                        raise PreflightError("nonregular runtime input")
                    expected = effective.get((name, path), digest(source.blob(path)))
                    if digest(actual.read_bytes()) != expected:
                        raise PreflightError(f"runtime input differs from exact source/overlay: {name}")
                    current.append({"path": path, "sha256": expected})
                return current
            bindings = correspondence()
            if name == "companion":
                command = [str(runtime / ".tools/node/bin/node"), "node_modules/vitest/vitest.mjs", "list",
                           "--json", "--configLoader", "runner", "--no-cache", "--maxWorkers=4", "--includeTaskLocation"]
            else:
                python = runtime / (".tools/python/bin/python3" if name == "specs" else entry["directory"] + "/.venv/bin/python")
                command = [str(python), "-B", "-c", PYTHON_COLLECTOR]
            raw = recorder.run(name + "-cases", command, checkout, env=env)
            cases = decode_json(raw)
            if not isinstance(cases, list) or not cases:
                raise PreflightError("empty or malformed runtime case collection")
            if correspondence() != bindings:
                raise PreflightError("runtime inputs changed during collection")
            record = {"source": name, "source_commit": source.commit, "source_tree": source.tree,
                      "case_count": len(cases), "cases": cases, "input_files": bindings,
                      "input_bindings_sha256": digest(canonical(bindings)),
                      "scope": "Framework collection only, no assertion execution claimed; exact source plus declared overlay bytes verified before and after."}
            write_private(output / (name + "-cases.json"), canonical(record))
            rows.append({"source": name, "case_count": len(cases), "record_sha256": digest(canonical(record)),
                         "source_correspondence": True})
        finally:
            source.close()
    result = {"sources": rows, "manifest_sha256": digest(canonical(manifest)),
              "commands_sha256": digest(canonical(recorder.rows)), "import_allowed": False,
              "visibility": "Raw private-source paths/cases remain in protected local runtime; publish only selected authorized rows."}
    write_private(output / "summary.json", canonical(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("manifest", "source-root", "runtime", "destination"):
        parser.add_argument("--" + option, type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True,
                        help="Exact published S01 environment record matching the reused runtime")
    args = parser.parse_args()
    try:
        print(json.dumps(collect(decode_json(args.manifest.read_bytes()), args.source_root.resolve(strict=True),
                                 args.runtime.resolve(strict=True), args.destination.absolute(),
                                 decode_json(args.environment.read_bytes())), indent=2))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
