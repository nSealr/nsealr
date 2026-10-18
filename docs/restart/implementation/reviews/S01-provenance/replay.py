#!/usr/bin/env python3
"""Distinct reviewer replay; mutable inputs exist only under this directory/.work."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SOURCE = "7a32eed82f542e818fad1c48d6815a38930eac32"
ORIGINAL = "30ae87dd31c3c292b22f4758d4fad9fea63a7b37"
ORIGINAL_PATH = "docs/restart/implementation/reviews/S01-integration/probe.py"
ORIGINAL_SHA = "39bce90e92a473930768d7b92aa76b70c8163ad495ea8fbdd1e9976e65ab4caf"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "tools/baseline"))
from bootstrap import Recorder, apply_lab_overlay, fetch, sha256, write_json


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == SOURCE
    work = HERE / ".work"
    work.mkdir(exist_ok=False)
    original = subprocess.check_output(["git", "show", f"{ORIGINAL}:{ORIGINAL_PATH}"], cwd=ROOT)
    assert hashlib.sha256(original).hexdigest() == ORIGINAL_SHA
    original_path = work / "original-probe.py"
    original_path.write_bytes(original)
    probe = load("original_distinct_review_probe", original_path)
    probe.HERE, probe.ROOT, probe.WORK = HERE, ROOT, work / "current"
    probe.CANDIDATE = SOURCE
    probe.PINS["firmware"] = SOURCE
    original_run = probe.run

    def corrected_run(argv, cwd):
        result = original_run(argv, cwd)
        if argv[:2] == ["git", "apply"] and len(argv) == 3 and argv[-1].endswith("/lab-metadata-v1.patch"):
            patch = str(ROOT / "tools/baseline/overlays/lab-provenance-followup.patch")
            original_run(["git", "apply", "--check", patch], cwd)
            original_run(["git", "apply", patch], cwd)
        return result

    probe.run = corrected_run
    assert probe.main() == 0
    recorder = Recorder(HERE / "commands", dict(os.environ))
    recorder.run("bootstrap-boundaries", [sys.executable, "-m", "unittest", "-v", "test_bootstrap.py"], ROOT / "tools/baseline")
    recorder.env["PYTHONPATH"] = str(probe.WORK / "lab")
    recorder.run("direct-fixture-boundaries", [sys.executable, "tests/test_fixture_snapshots.py", "-v"], probe.WORK / "lab")

    historical = work / "historical"
    historical.mkdir()
    lab_commit = probe.PINS["lab"]
    old_specs = "8bb8cca71355bcf8d81a093bcee9f3fe6915b121"
    old_core = "9194e292aa8a3176874cc9bf5814cefc26b6fe1a"
    fetch(recorder, "lab", "/home/tux/nsealr/lab", lab_commit, historical)
    fetch(recorder, "specs", "/home/tux/nsealr/specs", old_specs, historical)
    (historical / "evidence").mkdir()
    for filename, label in (("lab-provenance", "overlay"), ("lab-provenance-followup", "provenance-followup-overlay")):
        apply_lab_overlay(recorder, historical, lab_commit, ROOT / f"tools/baseline/overlays/{filename}.json", label)
    probe.archive(ROOT, old_core, historical / "firmware", ("tests/fixtures/specs",))
    checker = load("independent_historical_checker", historical / "lab/scripts/check_fixture_snapshots.py")
    snapshot = historical / "firmware/tests/fixtures/specs"
    metadata_path = snapshot / "SOURCE.json"
    saved_metadata = metadata_path.read_bytes()
    cases = []

    def case(name, reject=False):
        try:
            detail = checker.compare_fixture_snapshots(org=historical, repositories=("firmware",), required_snapshot_globs={})
            rejected = False
        except checker.FixtureSnapshotError as error:
            detail, rejected = str(error), True
        row = dict(case=name, expected_reject=reject, observed_reject=rejected, passed=reject == rejected, detail=detail)
        cases.append(row)
        print(json.dumps(row), flush=True)

    case("historical_clean_with_empty_required_globs")
    metadata_path.unlink()
    case("historical_missing_SOURCE", True)
    vector = snapshot / "vectors/nip46-relay-steps/sign-event-response-step.json"
    saved_vector = vector.read_bytes()
    vector.unlink()
    case("historical_missing_SOURCE_and_real_vector", True)
    vector.write_bytes(saved_vector)
    metadata = json.loads(saved_metadata)
    hidden = next(key for key in metadata["files"] if Path(key).name == ".gitkeep")
    hidden_path = snapshot / hidden
    saved_hidden = hidden_path.read_bytes()
    hidden_path.write_bytes(b"independent reviewer hidden byte mutation\n")
    metadata["files"][hidden] = sha256(hidden_path)
    metadata_path.write_text(json.dumps(metadata))
    case("historical_forged_hidden_digest", True)
    hidden_path.write_bytes(saved_hidden)
    metadata_path.write_bytes(saved_metadata)
    case("historical_restored")
    metadata_path.write_bytes((ROOT / "tests/fixtures/specs/SOURCE.json").read_bytes())
    case("current_manifest_cannot_relabel_historical_specs", True)
    metadata_path.write_bytes(saved_metadata)
    v1 = json.loads((ROOT / "docs/restart/implementation/S01/lab-metadata-v1.json").read_text())
    absent_v1 = all(sha256(historical / "lab" / name) == hashes["before_sha256"] for name, hashes in v1["files"].items())
    assert absent_v1 and all(case["passed"] for case in cases)
    for tree in (probe.WORK / "lab", historical / "lab"):
        manifest = json.loads((ROOT / "tools/baseline/overlays/lab-provenance-followup.json").read_text())
        assert sha256(tree / "LICENSE") == manifest["license_sha256"]
        assert all(sha256(tree / name) == hashes["after_sha256"] for name, hashes in manifest["files"].items())
    write_json(HERE / "historical-result.json", dict(source=SOURCE, core=old_core, specs=old_specs, lab=lab_commit,
               v1_overlay_not_applied=absent_v1, cases=cases, passed=True))
    write_json(HERE / "environment.json", dict(python=sys.version, executable=sys.executable,
               executable_sha256=sha256(Path(sys.executable)), original_probe_sha256=ORIGINAL_SHA,
               candidate=SOURCE, mutations="owned review .work only", runtime="existing pinned R00 Python; no new installation claim"))


if __name__ == "__main__":
    main()
