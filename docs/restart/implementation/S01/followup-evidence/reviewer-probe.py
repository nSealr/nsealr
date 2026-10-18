#!/usr/bin/env python3
"""Independent integration provenance/discovery probes; all mutations stay in .work.

Reads exact Git objects from authorized local repositories, not their working trees.
Run with Python 3.12+ from this review directory; no third-party packages needed.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
ORG = Path(os.environ.get("NSEALR_REVIEW_SOURCE_ORG", "/home/tux/nsealr"))
CANDIDATE = "ae01a32e8e0aab335115bbd17caad27f29122709"
PINS = {
    "firmware": CANDIDATE,
    "lab": "3303ab17a28ed32419576627d5abb93db3999635",
    "specs": "45f8b6ff1123f3f55be4ce457fd1008e91043cc2",
    "companion": "678796900e462f5504e47fe934e2e5f23d85824f",
    "raspberry": "d1534d9dcfba8fe4a35cea2ed3529e32a5003dc6",
    "smartcard": "ec5da94a05882122e8a794f55f1af3f96a95c696",
    "hardware": "340697d6713a671e9e01b0dc874ec999ab071601",
}
WORK = HERE / ".work/probe"
RESULTS = []


def run(argv, cwd):
    return subprocess.check_output(argv, cwd=cwd, stderr=subprocess.STDOUT)


def archive(repo, commit, target, paths=()):
    target.mkdir(parents=True)
    raw = run(["git", "archive", commit, *paths], repo)
    with tarfile.open(fileobj=io.BytesIO(raw)) as stream:
        stream.extractall(target, filter="data")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def case(name, fn, reject=False):
    try:
        detail = fn()
        rejected = False
    except (AssertionError, ValueError) as exc:
        detail = f"{type(exc).__name__}: {exc}"
        rejected = True
    row = {"case": name, "expected": "reject" if reject else "accept",
           "observed": "reject" if rejected else "accept", "pass": rejected == reject,
           "detail": detail}
    RESULTS.append(row)
    print(json.dumps(row), flush=True)


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    for name, commit in PINS.items():
        source = ROOT if name == "firmware" else ORG / name
        if name == "specs":
            destination = WORK / name
            destination.mkdir()
            run(["git", "init", "-q"], destination)
            run(["git", "fetch", "-q", "--depth=1", str(source), commit], destination)
            run(["git", "checkout", "-q", "--detach", "FETCH_HEAD"], destination)
        else:
            archive(source, commit, WORK / name,
                    () if name == "lab" else ("tests/fixtures/specs",))
    lab = WORK / "lab"
    specs = WORK / "specs"
    run(["git", "init", "-q"], lab)
    patches = [ROOT / "tools/baseline/overlays/lab-provenance.patch",
               ROOT / "docs/restart/implementation/S01/lab-metadata-v1.patch"]
    for patch in patches:
        run(["git", "apply", "--check", str(patch)], lab)
        run(["git", "apply", str(patch)], lab)
    sys.path.insert(0, str(lab))
    checker = load("review_fixture_checker", lab / "scripts/check_fixture_snapshots.py")
    consumer = load("review_nip46_consumer", lab / "scripts/integration_companion_nip46_cli.py")
    snapshot = WORK / "firmware/tests/fixtures/specs"
    metadata_path = snapshot / "SOURCE.json"
    original_metadata = metadata_path.read_bytes()
    metadata = json.loads(original_metadata)

    def check():
        return {"compared_files": checker.compare_fixture_snapshots(org=WORK)}

    def mutate_snapshot(name, relative, content, update_hash=False, remove_source=False):
        path = snapshot / relative
        original = path.read_bytes() if path.exists() else None
        try:
            if content is None:
                path.unlink()
            else:
                path.write_bytes(content)
            if remove_source:
                metadata_path.unlink()
            elif update_hash:
                changed = copy.deepcopy(metadata)
                if content is None:
                    changed["files"].pop(relative, None)
                else:
                    changed["files"][relative] = hashlib.sha256(content).hexdigest()
                metadata_path.write_text(json.dumps(changed))
            case(name, check, reject=True)
        finally:
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original)
            metadata_path.write_bytes(original_metadata)

    case("clean_default_full_snapshot_checker", check)
    nonhidden = "vectors/nip46-relay-steps/sign-event-response-step.json"
    mutate_snapshot("ordinary_vector_tamper_with_recomputed_manifest", nonhidden, b"{}\n", True)
    mutate_snapshot("missing_real_vector_with_manifest_retained", nonhidden, None)
    mutate_snapshot("extra_real_vector_with_recomputed_manifest", "vectors/reviewer-extra.json", b"{}\n", True)
    hidden = next(p for p in metadata["files"] if Path(p).name == ".gitkeep")
    mutate_snapshot("missing_gitkeep_recomputed_manifest", hidden, None, True)
    mutate_snapshot("gitkeep_tamper_recomputed_manifest", hidden, b"reviewer tamper\n", True)
    try:
        metadata_path.unlink()
        case("missing_SOURCE_json", check, reject=True)
    finally:
        metadata_path.write_bytes(original_metadata)
    mutate_snapshot("missing_SOURCE_and_real_v1_vector", nonhidden, None, remove_source=True)
    for key, value in (("commit", "0" * 40), ("repository", "https://example.invalid/specs")):
        changed = copy.deepcopy(metadata)
        changed[key] = value
        try:
            metadata_path.write_text(json.dumps(changed))
            case("wrong_" + key, check, reject=True)
        finally:
            metadata_path.write_bytes(original_metadata)

    selected = consumer.invalid_auth_challenge_relay_step_vectors(specs)

    def inventory(items):
        consumer.assert_auth_challenge_vector_inventory(specs, items)
        return {"names": [item["name"] for item in items]}

    case("v1_discovery_complete", lambda: inventory(selected))
    case("v1_discovery_empty", lambda: inventory([]), reject=True)
    for index in range(3):
        case(f"v1_omitted_selected_case_{index}",
             lambda index=index: inventory(selected[:index] + selected[index + 1:]), reject=True)
        changed = copy.deepcopy(selected)
        changed[index]["expected_error"] += " reviewer tamper"
        case(f"v1_substituted_selected_content_{index}", lambda changed=changed: inventory(changed), reject=True)
    case("v1_duplicate_selected_case", lambda: inventory(selected + selected[:1]), reject=True)
    case("restored_default_full_snapshot_checker", check)
    result = {"candidate": CANDIDATE, "python": sys.version, "python_executable": sys.executable,
              "pins": PINS, "cases": RESULTS, "pass": all(r["pass"] for r in RESULTS)}
    (HERE / "probe-result.json").write_text(json.dumps(result, indent=2) + "\n")
    return int(not result["pass"])


if __name__ == "__main__":
    raise SystemExit(main())
