#!/usr/bin/env python3
"""Emit reviewable A02 source/case records; no target import or task-policy engine."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from rehearse import Source, canonical, decode_json, digest, git, select


def treatment(source, path, name, action):
    if action == "retire":
        return "retire-smartcard", "Retired active smartcard implementation; preserve archive/source. New negative gates reject removed public commands, exports and routes."
    if source == "lab":
        if path == "tests/test_fixture_snapshots.py":
            if "smartcard_requires" in name:
                return "retire-smartcard", "Retired card consumer has no active fixture-coverage obligation; reject undeclared consumers instead."
            if "hardware_requires" in name:
                return "external-regression", "Preserve hardware consumer coverage separately against the pinned external owner; not a product build prerequisite."
            return "replace-artifact-provenance", "Replace duplicate-snapshot mechanics with one authoritative artifact. Preserve this named missing/extra/tamper/hidden/nonregular/hash/consumer-scope obligation; explicit partial consumers require declared coverage."
        if path == "tests/test_integration_feature_matrix.py":
            if ".test_lab_docs_" in name:
                return "retire-private-prose", "Retire historical private-prose text requirement; replace with live artifact/owner-contract presence and stale-reference rejection. Privacy-only address renaming is a separate earlier stage."
            return "adapt-owner-contract", "Preserve this shape/missing-extra/owner check against accepted current owners/profiles, excluding retired smartcards; do not invent supported hardware."
        if path == "tests/test_integration_hardware_validation.py":
            return "external-regression", "Preserve existing assertions in the separate external-hardware regression lane."
        return "retain", "Preserve all assertions, including corrected S01 metadata cases; adapt only declared consumer paths/commands."
    if source == "specs":
        if ".test_smartcard_apdu_" in name:
            return "retire-smartcard", "APDU-only oracle retired with active smartcard protocol; source history remains."
        if "smartcard" in name:
            return "replace-retired-route-rejection", "Replace card-specific supported-route semantics with rejection of the retired route before authority, policy or IO."
        if any(token in name for token in ("feature_matrix", "route_refusal", "identity_policy_schemas", "identity_policy_vectors", "policy_route_mismatch")):
            return "adapt-active-contract", "Retain useful validation and all active cases; remove only separately inventoried smartcard members. Preserve route/policy mismatch using retained fixtures and preserve shared-feature/QR parity checks."
        if "checkout_structure" in name:
            return "adapt-structure", "Preserve renamed-checkout, wrong-license and missing-directory negatives for the new authoritative artifact path; retire obsolete standalone-repository file-list requirements."
    if source == "companion":
        if "smartcard" in name.lower() or ("external review acknowledgement" in name.lower() and path.startswith("packages/client/")):
            return "replace-retired-route-rejection", "Retired successful card/ack dispatch is removed. Require unsupported route/command/field rejection before dispatch; retain ordinary active-route safety, identity and response checks."
        if path in {"packages/fixtures/src/fixtures.test.ts", "packages/policy/src/policy.test.ts"} and any(t in name.lower() for t in ("descriptor", "policy decision", "route", "feature matrix")):
            return "adapt-active-contract", "Preserve all active fixture assertions and negative policy/authority checks; explicitly remove card-only positive members and use a retained route for general mismatch checks."
        if "shared route-refusal contract" in name:
            return "adapt-active-contract", "Preserve every retained route refusal, remove the one card member, and add retired-route rejection."
    return "retain", "Preserve case assertions and independent expected results; only declared fixture-root/layout adaptations."


def emit(manifest_path: Path, inventory_path: Path, cases_root: Path, source_root: Path, output: Path):
    manifest = decode_json(manifest_path.read_bytes())
    inventory = decode_json(inventory_path.read_bytes())
    if decode_json((inventory_path.parent / "runtime.json").read_bytes())["inventory_sha256"] != digest(inventory_path.read_bytes()):
        raise ValueError("frozen inventory digest mismatch")
    if inventory["manifest_sha256"] != digest(canonical(manifest)):
        raise ValueError("inventory does not bind current admission manifest")
    output.mkdir(exist_ok=False)
    entries = {s["name"]: s for s in manifest["sources"]}
    file_map = {(r["source"], r["path"]): r for r in inventory["files"]}
    public_files, private_omitted = [], Counter()
    for row in inventory["files"]:
        source = entries[row["source"]]
        if source["visibility"] == "private" and row["action"] == "exclude":
            private_omitted[row["source"]] += 1
            continue
        record = {k: row[k] for k in ("source", "commit", "path", "mode", "blob", "sha256", "action", "rule", "reason", "destination")}
        if row["action"] in {"retain", "transform"}:
            if row["source"] == "nsealr":
                record["rights_basis"] = "Existing public ancestry; retain every original notice and third-party license unchanged. No blanket MIT relicensing."
            else:
                record["rights_basis"] = "Selected source root " + ("MIT" if row["source"] in {"companion", "raspberry"} else "CC0-1.0") + "; no competing nested notice found in selected paths."
                record["license"] = source["root_license"]
            record["privacy"] = ("Selected CC0 tooling only; private history excluded" if source["visibility"] == "private" else "Existing public source")
            record["initial_copy"] = "Exact original Git blob before separately declared overlays/adaptation"
            if row["source"] == "lab" and row["path"] in manifest["privacy_preimport_exceptions"]["paths"]:
                record["privacy"] = "Two-file pre-import exception: public first commit must use reviewed sanitized postimage; original path literals/full patch remain private."
                record["initial_copy"] = "Explicit exception bound by privacy-evidence/summary.json; original blob is never committed publicly"
        if "canonical" in row:
            record["canonical"] = row["canonical"]
        public_files.append(record)
    (output / "file-dispositions.json").write_bytes(canonical({"manifest_sha256": inventory["manifest_sha256"],
        "source_inventory_sha256": digest(inventory_path.read_bytes()), "files": public_files,
        "private_excluded_counts": dict(private_omitted), "private_path_names_published": False,
        "rights_review": "Author assessment for distinct admission review; hashes/license markers alone are not a rights or privacy review.",
        "original_tree_file_count": len(inventory["files"]), "import_executed": False}))
    closure = inventory["closed_evidence"]
    closure["source_identity"] = {"repository": "nSealr/nsealr", "commit": entries["nsealr"]["commit"], "tree": entries["nsealr"]["tree"]}
    closure["migration"] = "All frozen artifact bytes/paths remain unchanged. Current graph moves once to plan/work-items.json. Current P01 contracts get separately attributed editable paths; no second live graph."
    for artifact in closure["artifacts"]:
        artifact["original_commit"] = entries["nsealr"]["commit"]
        artifact["current_unchanged_path"] = artifact["path"]
        artifact["source_url"] = "https://github.com/nSealr/nsealr/blob/" + entries["nsealr"]["commit"] + "/" + artifact["path"]
    (output / "closed-evidence.json").write_bytes(canonical(closure))
    cases, omitted, opaque_exclusions = [], Counter(), []
    collection_records = {r["source"]: r for r in decode_json((cases_root / "summary.json").read_bytes())["sources"]}
    for name in ("companion", "specs", "raspberry", "lab"):
        record = decode_json((cases_root / (name + "-cases.json")).read_bytes())
        if digest(canonical(record)) != collection_records[name]["record_sha256"]:
            raise ValueError("case collection record digest mismatch")
        if record["source_commit"] != entries[name]["commit"] or record["source_tree"] != entries[name]["tree"]:
            raise ValueError("case source identity drift")
        bindings = {r["path"]: r["sha256"] for r in record["input_files"]}
        for case in record["cases"]:
            path = case["file"].split("/companion/", 1)[1] if name == "companion" else case["path"]
            case_name = case.get("name", case.get("id"))
            row = file_map[(name, path)]
            if entries[name]["visibility"] == "private" and row["action"] == "exclude":
                omitted[name] += 1
                opaque_exclusions.append({"source": name, "case_identity_sha256": digest(canonical({"path": path, "case_id": case_name})),
                                          "treatment": "exclude-private-repository-maintenance",
                                          "reason": "Private taxonomy, repository Makefile/drift or sibling-orchestration maintenance; not a selected product consumer. Original case/source preserved in protected collection and Git recovery."})
                continue
            decision, obligation = treatment(name, path, case_name, row["action"])
            cases.append({"source": name, "commit": record["source_commit"], "path": path,
                          "effective_source_sha256": bindings[path], "case_id": case_name,
                          "target_file": row["destination"], "treatment": decision, "obligation": obligation,
                          "after_execution": "required; not executed before import"})
    core = Source(source_root, entries["nsealr"])
    try:
        rust_path = "docs/restart/implementation/S01/followup-evidence/fresh/evidence/affected/00-core-ci.log"
        text = core.blob(rust_path).decode()
        group, rust = None, {}
        for line in text.splitlines():
            running = re.search(r"Running (.+?) \(.*?/deps/([a-z_]+)-[0-9a-f]+\)", line)
            if running:
                group = running[2]
            elif "Doc-tests " in line:
                group = "doctest:" + line.strip().split()[-1]
            match = re.fullmatch(r"test (.+?) \.\.\. ok", line)
            if match and group:
                rust[(group, match[1])] = {"source": "nsealr", "commit": entries["nsealr"]["commit"],
                     "group": group, "case_id": match[1], "evidence_log": rust_path,
                     "evidence_log_sha256": digest(core.blob(rust_path)), "treatment": "retain",
                     "obligation": "Preserve all Rust assertions/doctests; split workspaces without weakening coverage or independent vector/category completeness.",
                     "after_execution": "required; not executed before import"}
        cases.extend(rust.values())
        before = []
        old_base = "docs/restart/implementation/S01/evidence"
        fresh_base = "docs/restart/implementation/S01/followup-evidence/fresh"
        old_commands = decode_json(core.blob(old_base + "/suites/commands.json"))
        fresh_commands = decode_json(core.blob(fresh_base + "/evidence/affected/commands.json"))
        for base in (old_base, fresh_base):
            pins = decode_json(core.blob(base + "/source-commits.json"))
            if any(pin != entries[name]["commit"] for name, pin in pins.items() if name != "nsealr"):
                raise ValueError("before-suite selected source pin mismatch")
        old_environment = decode_json(core.blob(old_base + "/environment.json"))
        fresh_environment = decode_json(core.blob(fresh_base + "/environment.json"))
        def normalized_environment(env, suffix):
            return {k: v.replace("/.work/" + suffix, "/.work/ENV") for k, v in env.items()}
        if normalized_environment(old_environment, "runtime") != normalized_environment(fresh_environment, "current-default"):
            raise ValueError("before environments differ beyond declared runtime root")
        binaries = []
        for position, executable in ((1, "python3"), (2, "node")):
            old_binary = Path(old_environment["PATH"].split(":")[position]) / executable
            new_binary = Path(fresh_environment["PATH"].split(":")[position]) / executable
            before_sha, after_sha = digest(old_binary.read_bytes()), digest(new_binary.read_bytes())
            if before_sha != after_sha:
                raise ValueError("reused runtime binary mismatch")
            binaries.append({"tool": executable, "sha256": before_sha, "old_path": str(old_binary), "current_path": str(new_binary)})
        chosen = [(old_base + "/suites", row) for row in old_commands if row["label"] not in {"firmware-ci", "lab-ci", "full-integration"}]
        chosen += [(fresh_base + "/evidence/affected", row) for row in fresh_commands]
        for base, command in chosen:
            path = base + "/" + command["log"]
            if digest(core.blob(path)) != command["sha256"] or command["exit_code"] != 0:
                raise ValueError("before gate log failed/hash drift")
            before.append({**command, "source_log": path, "reuse": "Before-state only; complete after-migration acceptance must execute",
                           "current_core_commit": entries["nsealr"]["commit"]})
        comparison = git(core.repo, "diff", "--name-only", "7a32eed82f542e818fad1c48d6815a38930eac32", core.commit).decode().splitlines()
        if any(not path.startswith(("docs/restart/", "tools/cad/")) for path in comparison):
            raise ValueError("unexpected core delta invalidates before-gate correspondence")
        (output / "before-gates.json").write_bytes(canonical({"source_commit": core.commit, "gates": before,
            "core_source_comparison": {"tested": "7a32eed82f542e818fad1c48d6815a38930eac32", "current": core.commit,
                "changed_paths": comparison, "only_restart_docs_and_cad_tool_additions": True,
                "disposition": "Rust/core/bootstrap/workflow/gate source unchanged. Current full graph validator/controls executed independently against f2; added CAD owner keeps separate E01 proof."},
            "environment_records": [{"path": p, "sha256": digest(core.blob(p))} for p in
                [old_base + "/environment.json", old_base + "/runtime-reuse.json", fresh_base + "/environment.json", fresh_base + "/evidence/environment-manifest.json"]],
            "source_pin_records": [{"path": p, "sha256": digest(core.blob(p))} for p in [old_base + "/source-commits.json", fresh_base + "/source-commits.json"]],
            "case_collection": "Actual Vitest/unittest discovery from exact source plus corrected overlay bytes, verified before/after; runtime-only collector count is not assertion execution.",
            "environment_correspondence": {"all_variables_equal_after_runtime_root_substitution": True, "actual_binary_equality": binaries},
            "historical_failures": "Preserved in immutable R00/S01 artifacts, including original provenance bypass and metadata discovery failures. Corrected final before-state gates pass; no old failure was deleted or waived.",
            "boundary": "Same pinned user-space versions/locks and declared local host. No OS hermeticity or physical/live-client qualification claim."}))
    finally:
        core.close()
    (output / "case-dispositions.json").write_bytes(canonical({"cases": sorted(cases, key=lambda r:(r["source"], r.get("path",r.get("group","")), r["case_id"])),
        "counts": dict(Counter(r["treatment"] for r in cases)), "private_excluded_case_counts": dict(omitted),
        "private_excluded_cases": opaque_exclusions,
        "private_full_collection_sha256": digest((cases_root / "lab-cases.json").read_bytes()),
        "selection_reconciliation": "Collection manifest preceded two checker selections/privacy metadata. Same exact source commits/trees and overlay postimages; selection changes are reflected here without repeating unchanged collection.",
        "after_migration_acceptance": "All retained/replacement/external cases require actual execution. No implementation or conformance claim is made by this ledger."}))
    return {"public_file_records": len(public_files), "private_excluded_paths": sum(private_omitted.values()),
            "public_case_records": len(cases), "closed_artifact_references": sum(t["artifact_references"] for t in closure["tasks"]),
            "unique_closed_artifacts": len(closure["artifacts"]), "import_allowed": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("manifest", "inventory", "cases", "source-root", "output"):
        parser.add_argument("--" + argument, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(emit(args.manifest, args.inventory, args.cases, args.source_root, args.output), indent=2))
