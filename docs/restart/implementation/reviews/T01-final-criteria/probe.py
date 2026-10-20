"""Read-only binding/projection checks supporting a separate semantic reading.

This does not execute 42 scenarios, review Pi/provenance product code, or replace
the existing Rust/Bridge/integration campaigns. The only executed product tool
is the unchanged data-only projector, into a disposable directory.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).parent
EVIDENCE = "docs/restart/implementation/T01/integration/evidence/"
CANDIDATE = "e83c49d97efcbec4fb54c11609c0d2d21e687719"
PRODUCT = "c4a2aa8d6567369caa52d7e0680e7581c2a554c3"
sha = lambda b: hashlib.sha256(b).hexdigest()
git = lambda *args: subprocess.check_output(["git", *args], cwd=ROOT)
load = lambda p: json.loads((ROOT / p).read_bytes())

def binding(path, commit=CANDIDATE):
    entry = git("ls-tree", "-z", commit, "--", path).rstrip(b"\0").split(b"\t")[0]
    mode, kind, blob = entry.decode().split()
    assert kind == "blob"
    data = git("show", commit + ":" + path)
    return dict(commit=commit, path=path, mode=mode, blob=blob, bytes=len(data), sha256=sha(data))

assert git("rev-parse", "HEAD").decode().strip() == CANDIDATE
assert git("rev-parse", CANDIDATE + "^{tree}").decode().strip() == "f1c06800f5950aac8efe60f11c76c315d77f202e"
assert git("rev-parse", PRODUCT + ":protocols/contracts/v1").decode().strip() == "b629e75d18190ded2403ffabe965b595a9bcf6a6"
entry = load("docs/restart/implementation/T01/integration/result.json")
cases = load("protocols/contracts/v1/vectors/profile-capabilities/cases-v1.json")
original = json.loads(git("show", "bb20fe121e9c211a829c870d82ef2060c6858c40:protocols/contracts/v1/vectors/profile-capabilities/cases-v1.json"))
assert cases["cases"] == original["cases"] and len(cases["cases"]) == 42
mapping = load(EVIDENCE + "case-evidence.json")
assert [r["id"] for r in mapping["rows"]] == [r["id"] for r in cases["cases"]]
refs = {r["path"]: r for case in mapping["rows"] for r in case["executed_control_references"]}
for path, row in refs.items():
    assert binding(path)["sha256"] == row["sha256"]

receipts = {r["path"] for r in mapping["execution_receipts"]}
receipts |= {EVIDENCE + "commands/" + name + "/command.json" for name in [
    "wire2-pending-discovery-typecheck-10", "wire2-final-data-projection-01", "wire2-layout-core-unit-06"]}
receipt_rows = []
for path in sorted(receipts):
    receipt = load(path)
    log_bindings = []
    for row in receipt["artifacts"]:
        target = str(Path(path).parent / row["path"])
        actual = binding(target)
        assert actual["bytes"] == row["bytes"] and actual["sha256"] == row["sha256"]
        log_bindings.append(actual)
    receipt_rows.append(dict(receipt=binding(path), source_commit=receipt.get("source_commit"),
                             recorded_dirty_diff=receipt.get("initial_tracked_diff_sha256"),
                             exit=receipt["exit_code"], logs=log_bindings))
for declared in mapping["execution_receipts"]:
    assert binding(declared["path"])["sha256"] == declared["sha256"]

post = load(EVIDENCE + "projection-postimages.json")
assert len(post["rows"]) == 170 and len(post["new_rows"]) == 5
config = load("ci/core-test-projections.json")
assert config == [r["mapping"] for r in post["rows"]] + [r["mapping"] for r in post["new_rows"]]
original_config = json.loads(git("show", "dbad656997ad8cf9024ca1489291f5f1d4d3094a:ci/core-test-projections.json"))
assert len(original_config) == 170 and config[:170] == original_config
assert git("rev-parse", "dbad656997ad8cf9024ca1489291f5f1d4d3094a:ci/project_core_fixtures.py") == git("rev-parse", CANDIDATE + ":ci/project_core_fixtures.py")
preimage_cache = {}
for row in post["rows"]:
    before = row["preimage_binding"]
    key = (before["commit"], before["path"])
    if key not in preimage_cache:
        preimage_cache[key] = git("show", before["commit"] + ":" + before["path"])
    raw = preimage_cache[key]
    assert sha(raw) == before["sha256"]
    value = json.loads(raw)
    for part in row["mapping"]["pointer"]:
        value = value[int(part)] if isinstance(value, list) else value[part]
    projected = value if row["mapping"]["encoding"] == "string" else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    assert sha(projected.encode()) == row["preimage_projected_sha256"]
    if not row["semantic_dependency"]:
        assert row["current_projected_sha256"] == row["preimage_projected_sha256"]
with tempfile.TemporaryDirectory(prefix="t01-criteria-projection-") as directory:
    argv = ["python3", "ci/project_core_fixtures.py", directory]
    process = subprocess.run(argv, cwd=ROOT, capture_output=True)
    assert process.returncode == 0, process.stderr
    (OUT / "projector.stdout.log").write_bytes(process.stdout)
    (OUT / "projector.stderr.log").write_bytes(process.stderr)
    produced = Path(directory)
    for row in post["rows"]:
        data = (produced / row["mapping"]["output"]).read_bytes()
        assert len(data) == row["current_projected_bytes"] and sha(data) == row["current_projected_sha256"]
        assert binding("protocols/contracts/v1/" + row["mapping"]["artifact_path"])["sha256"] == row["current_source_sha256"]
    for row in post["new_rows"]:
        data = (produced / row["mapping"]["output"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"]
    for row in post["existing_three_data_helpers_and_bytecopy"]:
        data = (produced / row["output"]).read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"]
    assert len(list(produced.iterdir())) == 179
    projector_command = dict(argv=argv, exit=process.returncode, output_files=179,
                             temporary_outputs_removed=True, expected_values_generated=False)

includes = defaultdict(list)
for path in (ROOT / "crates").rglob("*.rs"):
    text = path.read_text()
    for match in re.finditer(r'env!\("OUT_DIR"\)\s*,\s*"/([^\"]+)"', text):
        includes[match[1]].append(dict(path=str(path.relative_to(ROOT)), line=text.count("\n", 0, match.start()) + 1))
unreferenced = [r for r in post["rows"] if not includes[r["mapping"]["output"]]]
assert len(unreferenced) == 8 and all(r["semantic_group"] == "legacy_status_negative_only" for r in unreferenced)
projection = dict(original_mappings=170, semantic_dependency_rows=sum(r["semantic_dependency"] for r in post["rows"]),
                  all170_projected_preimages_checked_against_original_Git_bytes=True,
                  independent51_projected_preimages_unchanged=True,
                  actual_projected_values_changed=sum(r["projected_value_changed"] for r in post["rows"]),
                  group_counts=dict(Counter(r["semantic_group"] for r in post["rows"])),
                  direct_Rust_output_references=162,
                  historical_only_outputs=[r["mapping"] for r in unreferenced],
                  historical_role="Retained identities only; reject retired status as a whole. These eight outputs are not eight executed gate checks.",
                  helper_includes={r["output"]: includes[r["output"]] for r in post["existing_three_data_helpers_and_bytecopy"]},
                  projector_command=projector_command)
fixed_text = (ROOT / (EVIDENCE + "artifact-pin-review/fixed-inputs.stdout.log")).read_text()
fixed = json.loads(fixed_text[fixed_text.index("{"):])  # actual format has a one-line preamble
assert len(fixed["bindings"]) == 92 and fixed["six_diagnostic_pairs_exact"]
for row in fixed["bindings"]:
    assert binding(row["path"])["sha256"] == row["sha256"]
metadata = load(EVIDENCE + "metadata-delta-review/source-bindings.json")
metadata_changed = [r["after"]["path"] for r in metadata["component_bindings"]
                    if binding(r["after"]["path"])["blob"] != r["after"]["blob"]]
assert metadata_changed == ["protocols/contracts/v1/schemas/account-v1.schema.json"]
delta = git("diff", "--name-only", "ae34085dd6017eaf2539cf0b570bfb49daace824", PRODUCT,
            "--", ".", ":!docs/restart/implementation/T01/integration/").decode().splitlines()
assert len(delta) == 5
result = dict(candidate=CANDIDATE, product=PRODUCT, criteria_source_verdict="See separate semantic report; this probe is binding/projection evidence only",
              semantic_case_objects_unchanged=42, case_source_bindings=[binding(p) for p in sorted(refs)],
              excluded_semantic_source_reviews=["apps/pi/tests/test_vault_core.py", "scripts/test_contracts.py"],
              delegated_Pi_provenance_note="Hashes bind author references only; no judgment of these author-owned product paths here. Root df1/H01 042 and root pin/literal review remain external.",
              receipts=receipt_rows, projection=projection,
              reused_fixed_input_replay=dict(commit="3653d9008241908d971c50ea455981459f7eb9c7", current92_hashes_match=True,
                                            diagnostic_pairs=6, original_failure_preserved=True, new_replay_executed=False),
              metadata_reuse=dict(review="572df40e9fb27c96e8bd5bc59bc66f5b8dd293df", identical18minus1=17,
                                  affected_account_recovery_schema_review="9bbcfdae907134d4c3218b626ddd44c34221bb67"),
              actual_gate_reuse_delta=delta,
              no_full_CI_test_or_device_campaign_executed=True,
              source_bindings=[binding(p) for p in ["docs/restart/implementation/T01/integration/result.json",
                "docs/restart/implementation/T01/integration/handoff.md", EVIDENCE+"case-evidence.json",
                EVIDENCE+"projection-postimages.json", EVIDENCE+"validation-summary.json",
                EVIDENCE+"resource-accounting.json", EVIDENCE+"admission/t01-pending-discovery-test-review.json",
                EVIDENCE+"metadata-delta-review/review.json", EVIDENCE+"service-component-review/corrections/review.json",
                EVIDENCE+"pi-review/review.json", EVIDENCE+"provenance-review/mode-correction/review.json",
                EVIDENCE+"artifact-pin-review/corrections/review.json", EVIDENCE+"portable-boundary-review/source-review.json",
                "ci/core-test-projections.json", "ci/project_core_fixtures.py", "crates/nsealr-core/build.rs",
                "crates/nsealr-core/src/review/qr.rs", "crates/nsealr-core/src/review/test_fixtures.rs",
                "crates/nsealr-core/src/policy/policy_change_review.rs", "docs/restart/implementation/S03/vectors.json"]])
(OUT / "probe-result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(dict(candidate=CANDIDATE, case_objects=42, bound_case_source_paths=len(refs),
                     receipts=len(receipt_rows), projected_outputs=179, mappings=170,
                     direct_Rust_output_references=162, historical_negative_only=8,
                     independent_fixed_input_current_matches=92, status="PASS_BINDINGS_AND_DATA_PROJECTION_ONLY")))
