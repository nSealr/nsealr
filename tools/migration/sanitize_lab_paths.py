#!/usr/bin/env python3
"""Prepare the two-file privacy exception in protected storage, not a target repo."""
from __future__ import annotations

import argparse
import ast
import difflib
import io
import json
from pathlib import Path
import sys
import types
import unittest

from admission import Recorder, protected_destination
from rehearse import PreflightError, Source, canonical, decode_json, digest, write_private


PATHS = ("scripts/integration_feature_matrix.py", "tests/test_integration_feature_matrix.py")


def replace_literals(data: bytes, mapping: dict) -> tuple[bytes, int]:
    offsets = [0]
    for line in data.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    edits = []
    for node in ast.walk(ast.parse(data)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in mapping:
            edits.append((offsets[node.lineno - 1] + node.col_offset,
                          offsets[node.end_lineno - 1] + node.end_col_offset,
                          json.dumps(mapping[node.value]).encode()))
    changed = data
    for start, end, value in sorted(edits, reverse=True):
        changed = changed[:start] + value + changed[end:]
    return changed, len(edits)


def run_cases(module_bytes: bytes, test_bytes: bytes) -> tuple[dict, bytes]:
    key = "scripts.integration_feature_matrix"
    prior = sys.modules.get(key)
    module = types.ModuleType(key)
    module.__file__ = str(Path.cwd() / "protected-review/scripts/integration_feature_matrix.py")
    test = types.ModuleType("privacy_feature_matrix_tests")
    test.__file__ = str(Path.cwd() / "protected-review/tests/test_integration_feature_matrix.py")
    try:
        exec(compile(module_bytes, module.__file__, "exec"), module.__dict__)
        sys.modules[key] = module
        exec(compile(test_bytes, test.__file__, "exec"), test.__dict__)
        suite = unittest.defaultTestLoader.loadTestsFromModule(test)
        names = [case.id() for group in suite for case in group]
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        return {"case_ids": names, "run": result.testsRun, "failures": len(result.failures),
                "errors": len(result.errors), "skipped": len(result.skipped), "passed": result.wasSuccessful()}, stream.getvalue().encode()
    finally:
        if prior is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = prior


def prepare(manifest: dict, source_root: Path, output: Path) -> dict:
    recorder = Recorder(protected_destination(output, source_root, manifest))
    entry = next(s for s in manifest["sources"] if s["name"] == "lab")
    source = Source(source_root, entry)
    try:
        original = {path: source.blob(path) for path in PATHS}
        tree = ast.parse(original[PATHS[0]])
        assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == "LAB_DOCS" for t in n.targets))
        literals = [n.value for n in ast.walk(assignment.value) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        if len(literals) != 3 or len(set(literals)) != 3:
            raise PreflightError("unexpected private reference inventory")
        mapping = {old: f"docs/historical-feature-contract-{i:02d}.md" for i, old in enumerate(literals, 1)}
        changed, rows = {}, []
        for path in PATHS:
            changed[path], count = replace_literals(original[path], mapping)
            if count != (3 if path == PATHS[0] else 4):
                raise PreflightError("unexpected private reference occurrence count")
            # Reverse substitution must recover the exact AST; all nonliteral bytes
            # are also preserved by the span-only edit above.
            reverse, reverse_count = replace_literals(changed[path], {v: k for k, v in mapping.items()})
            if (reverse_count != count or ast.dump(ast.parse(reverse)) != ast.dump(ast.parse(original[path]))
                    or any(old.encode() in changed[path] for old in mapping)):
                raise PreflightError("privacy transformation changed logic or retained an excluded path")
            write_private(output / Path(path).name, changed[path])
            rows.append({"source_path": path, "source_blob": source.files[path]["blob"],
                         "before_sha256": digest(original[path]), "after_sha256": digest(changed[path]),
                         "literal_occurrences_replaced": count, "ast_equal_under_inverse_literal_mapping": True})
        patch_bytes = "".join("".join(difflib.unified_diff(original[path].decode().splitlines(True),
                                      changed[path].decode().splitlines(True), fromfile="a/" + path, tofile="b/" + path))
                              for path in PATHS).encode()
        write_private(output / "private-full.patch", patch_bytes)
        before, before_log = run_cases(original[PATHS[0]], original[PATHS[1]])
        after, after_log = run_cases(changed[PATHS[0]], changed[PATHS[1]])
        write_private(output / "before-tests.log", before_log)
        write_private(output / "after-tests.log", after_log)
        if not before["passed"] or not after["passed"] or before["case_ids"] != after["case_ids"]:
            raise PreflightError("privacy exception failed original/sanitized case equivalence")
        result = {"source_repository": entry["repository"], "source_commit": source.commit,
                  "license": "CC0-1.0", "license_sha256": digest(source.blob("LICENSE")), "files": rows,
                  "private_patch_sha256": digest(patch_bytes), "private_patch_published": False,
                  "replacement_paths": list(mapping.values()), "before_cases": before, "after_cases": after,
                  "before_log_sha256": digest(before_log), "after_log_sha256": digest(after_log),
                  "exception": "Only three document address literals are renamed bijectively across two files. Original addresses cease to resolve; no claim of byte equality or unchanged external paths.",
                  "later_adaptation": "The two historical private-prose assertions are explicitly retired during later behavior adaptation; retain useful feature shape/owner/missing-extra checks against accepted current contracts. No placeholder documents or compatibility tree are created.",
                  "source_import_performed": False, "independent_admission_review_required": True}
        write_private(output / "summary.json", canonical(result))
        return result
    finally:
        source.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("manifest", "source-root", "destination"):
        parser.add_argument("--" + option, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(decode_json(args.manifest.read_bytes()), args.source_root.resolve(strict=True), args.destination.absolute())
        print(json.dumps(result, indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
