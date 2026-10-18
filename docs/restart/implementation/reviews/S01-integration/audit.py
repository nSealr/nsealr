#!/usr/bin/env python3
"""Read-only hash/source correspondence audit of the exact integration candidate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
AUTHOR = ROOT / "docs/restart/implementation/S01"
ORG = Path("/home/tux/nsealr")
CANDIDATE = "ae01a32e8e0aab335115bbd17caad27f29122709"
BASE = "9194e292aa8a3176874cc9bf5814cefc26b6fe1a"
FIXTURE = "41f5d2d193e4a00227737e1f8d71ce57e39ea889"
SPECS = "45f8b6ff1123f3f55be4ce457fd1008e91043cc2"
COMPANION = "678796900e462f5504e47fe934e2e5f23d85824f"


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def filehash(path):
    return digest(path.read_bytes())


def paths(repo, commit, prefix):
    return git(repo, "ls-tree", "-r", "--name-only", commit, prefix).decode().splitlines()


def tree(repo, commit):
    return dict(line.split("\t")[::-1] for line in git(repo, "ls-tree", commit).decode().splitlines())


def changed(repo, old, new, prefix=None):
    args = ["diff", "--no-renames", "--name-only", old, new]
    if prefix:
        args += ["--", prefix]
    return git(repo, *args).decode().splitlines()


def main():
    results = {}
    artifacts = json.loads((AUTHOR / "artifacts.json").read_text())
    for record in artifacts:
        assert filehash(ROOT / record["path"]) == record["sha256"], record["path"]
    results["author_artifact_hashes"] = len(artifacts)
    command_count = 0
    for path in (AUTHOR / "evidence").rglob("commands.json"):
        for command in json.loads(path.read_text()):
            assert filehash(path.parent / command["log"]) == command["sha256"], command["label"]
            command_count += 1
    results["command_record_log_hashes"] = command_count
    metadata = json.loads((ROOT / "tests/fixtures/specs/SOURCE.json").read_text())
    assert metadata["commit"] == SPECS
    assert metadata["repository"] == "https://github.com/nSealr/specs"
    upstream = paths(ORG / "specs", SPECS, "vectors")
    snapshot = paths(ROOT, CANDIDATE, "tests/fixtures/specs/vectors")
    snapshot = [p.removeprefix("tests/fixtures/specs/") for p in snapshot]
    assert set(upstream) == set(snapshot) == set(metadata["files"])
    for name in upstream:
        source = git(ORG / "specs", "show", f"{SPECS}:{name}")
        target = git(ROOT, "show", f"{CANDIDATE}:tests/fixtures/specs/{name}")
        assert source == target
        assert digest(target) == metadata["files"][name]
    results["exact_complete_vector_bytes_and_inventory"] = len(upstream)
    results["tracked_dotfiles_verified_independently"] = [p for p in upstream if Path(p).name.startswith(".")]
    migration = json.loads((AUTHOR / "fixture-migration.json").read_text())
    actual_changes = changed(ORG / "specs", migration["old_specs_commit"], SPECS, "vectors")
    assert set(actual_changes) == {p["path"] for p in migration["changes"]}
    core_changes = changed(ROOT, BASE, CANDIDATE, "tests/fixtures/specs/vectors")
    assert {p.removeprefix("tests/fixtures/specs/") for p in core_changes} == set(actual_changes)
    for record in migration["changes"]:
        for side, commit in (("before", migration["old_specs_commit"]), ("after", SPECS)):
            expected = record[side + "_sha256"]
            available = record["path"] in paths(ORG / "specs", commit, record["path"])
            assert available == (expected is not None)
            if available:
                assert digest(git(ORG / "specs", "show", f"{commit}:{record['path']}")) == expected
    results["raw_migration_paths_verified"] = len(actual_changes)
    final_tree, base_tree, fixture_tree = tree(ROOT, CANDIDATE), tree(ROOT, BASE), tree(ROOT, FIXTURE)
    unchanged = {k: v for k, v in base_tree.items() if k not in ("tests", "docs")}
    assert all(final_tree[k] == v for k, v in unchanged.items())
    assert {k: v for k, v in final_tree.items() if k != "docs"} == {k: v for k, v in fixture_tree.items() if k != "docs"}
    results["unchanged_native_dependency_ci_top_level_objects"] = len(unchanged)
    results["final_equals_tested_non_docs_top_level_objects"] = len(final_tree) - 1
    companion_delivery = "beb8d25da73661e4ede21bf62deb0cdb84406c5f"
    assert git(ORG / "companion", "rev-parse", COMPANION + "^{tree}") == git(ORG / "companion", "rev-parse", companion_delivery + "^{tree}")
    companion_diff = changed(ORG / "companion", "9e023ccef300ddeb738c377fe68b130a94123477", COMPANION)
    assert all(p.startswith("docs/restart/S01/") for p in companion_diff)
    specs_diff = changed(ORG / "specs", "b0022f3dd8b1c2b1bb553c0e5f84e81fb312396a", SPECS)
    assert all(p.startswith("docs/") for p in specs_diff)
    results["companion_reviewed_product_correspondence"] = {"identical_delivery_tree": True, "post_product_docs_paths": len(companion_diff)}
    results["specs_reviewed_product_correspondence"] = {"post_product_docs_paths": len(specs_diff)}
    for basename, directory in (("lab-provenance", ROOT / "tools/baseline/overlays"), ("lab-metadata-v1", AUTHOR)):
        manifest = json.loads((directory / (basename + ".json")).read_text())
        assert filehash(directory / (basename + ".patch")) == manifest["patch_sha256"]
        for path, hashes in manifest["files"].items():
            assert digest(git(ORG / "lab", "show", f"{manifest['commit']}:{path}")) == hashes["before_sha256"]
            assert filehash(HERE / ".work/probe/lab" / path) == hashes["after_sha256"]
    for suffix in ("patch", "json"):
        name = f"tools/baseline/overlays/lab-provenance.{suffix}"
        assert git(ROOT, "show", BASE + ":" + name) == (ROOT / name).read_bytes()
    results["ordered_overlay_patch_and_file_hashes"] = "pass; original R00 overlay byte-identical"
    assert digest(git(ORG / "specs", "show", SPECS + ":LICENSE")) == migration["license_sha256"]
    assert digest(git(ORG / "lab", "show", "3303ab17a28ed32419576627d5abb93db3999635:LICENSE")) == migration["license_sha256"]
    results["cc0_license_hash"] = migration["license_sha256"]
    brief_review = json.loads((AUTHOR / "integration-spec-review.json").read_text())
    # Discover the explicitly named hash field without depending on JSON key order.
    assert filehash(AUTHOR / "integration-brief.md") in brief_review.values()
    results["accepted_brief_hash"] = filehash(AUTHOR / "integration-brief.md")
    suite_records = json.loads((AUTHOR / "evidence/suites/commands.json").read_text())
    assert len(suite_records) == 9 and all(r["exit_code"] == 0 for r in suite_records)
    assert all(r["argv"] == ["make", "-k", "ci"] for r in suite_records[:8])
    assert suite_records[-1]["argv"] == ["make", "integration"]
    for previous, current in zip(suite_records, suite_records[1:]):
        assert previous["ended"] <= current["started"]
    integration = (AUTHOR / "evidence/suites/08-full-integration.log").read_text()
    recipe = git(ORG / "lab", "show", "3303ab17a28ed32419576627d5abb93db3999635:Makefile").decode().split("integration-pnpm:\n", 1)[1].split("\n\n", 1)[0]
    expected_steps = [line.strip().replace("$(VENV_PYTHON)", ".venv/bin/python") for line in recipe.splitlines()]
    observed_steps = [line for line in integration.splitlines() if line.startswith(".venv/bin/python scripts/")]
    assert expected_steps == observed_steps and len(observed_steps) == 20
    required_names = ("with-credentials", "with-fragment", "wrong-scheme")
    for name in required_names:
        assert integration.count("NIP-46 v1 auth-negative executed: relay-step-response-auth-url-" + name + "\n") == 1
    assert "snapshot check passed (546 files)" in integration
    assert "nSealr cross-repo smartcard companion simulator smoke test passed" in integration
    results["recorded_gate_completeness"] = {"independent_ci_commands": 8, "ordered_integration_steps": 20, "auth_negative_invocations": 3, "fixture_comparisons": 546}
    results["candidate"] = CANDIDATE
    results["pass"] = True
    (HERE / "audit-result.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
