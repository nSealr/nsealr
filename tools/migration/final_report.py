#!/usr/bin/env python3
"""Verify and export the exact A02 final source map; never export runtime objects."""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import json
from pathlib import Path
import subprocess

from assemble import read_git, tree
from rehearse import canonical, digest, git


def main(author: Path, replay_name: str) -> None:
    author = author.resolve()
    runtime = author / "tools/migration/.runtime"
    target = runtime / "rehearsal-01/repository"
    report = author / "docs/restart/implementation/A02"
    patches = author / "tools/migration/patches"
    head = read_git(target, "rev-parse", "HEAD").decode().strip()
    if read_git(target, "status", "--porcelain"):
        raise ValueError("final target is dirty")
    replay = json.loads((runtime / replay_name / "result.json").read_bytes())
    if replay["second_assembly"]["target_head"] != head:
        raise ValueError("restored replay is not this final candidate")

    # Private original document references are read only for an exclusion check.
    original = ast.parse(git(Path("/home/tux/nsealr/lab"), "show",
        "3303ab17a28ed32419576627d5abb93db3999635:scripts/integration_feature_matrix.py"))
    assignment = next(n for n in original.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "LAB_DOCS" for t in n.targets))
    words = [n.value for n in ast.walk(assignment.value)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    forbidden = [s.encode() for value in words for s in (value, Path(value).name)]

    def write(relative: str, value: dict | list) -> None:
        data = canonical(value)
        if any(s in data for s in forbidden):
            raise ValueError("private document reference in proposed public output")
        destination = report / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

    def copy(source: Path, relative: str) -> None:
        data = source.read_bytes()
        if any(s in data for s in forbidden):
            raise ValueError("private document reference in proposed public output")
        destination = report / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

    imported = json.loads((runtime / "rehearsal-01/import-map.json").read_bytes())
    admitted = json.loads((report / "admission-evidence/file-dispositions.json").read_bytes())
    manifest = json.loads((report / "admission-inputs.json").read_bytes())
    series = json.loads((patches / "series.json").read_bytes())
    initial_tree = tree(target, imported["initial_commit"])
    current_tree = tree(target, head)

    # Hash every initial blob in one batch, then replay the declared file states.
    blob_ids = sorted({value["blob"] for value in initial_tree.values()})
    process = subprocess.run(["git", "-C", str(target), "cat-file", "--batch"],
        input=("\n".join(blob_ids) + "\n").encode(), capture_output=True, check=True)
    data = process.stdout
    offset = 0
    hashes = {}
    for oid in blob_ids:
        end = data.index(b"\n", offset)
        actual, kind, size = data[offset:end].decode().split()
        size = int(size)
        if actual != oid or kind != "blob":
            raise ValueError("unexpected batch object")
        begin = end + 1
        hashes[oid] = digest(data[begin:begin + size])
        offset = begin + size + 1
    state = {path: dict(mode=value["mode"], sha256=hashes[value["blob"]])
             for path, value in initial_tree.items()}
    changes = defaultdict(list)
    preceding = imported["initial_commit"]
    for number, item in enumerate(series, 1):
        record = json.loads((patches / item["record"]).read_bytes())
        patch_sha = digest((patches / item["patch"]).read_bytes())
        if record["source_commit"] != preceding or patch_sha != item["sha256"] or patch_sha != record["patch_sha256"]:
            raise ValueError("broken patch chain")
        for row in record["changes"]:
            path = row["path"]
            expected = None if row["before_sha256"] is None else dict(
                mode=row["before_mode"], sha256=row["before_sha256"])
            if state.get(path) != expected:
                raise ValueError("declared preimage disagrees with complete tree")
            changes[path].append(dict(number=number, record=item["record"],
                commit=record["target_commit"], before_sha256=row["before_sha256"],
                after_sha256=row["after_sha256"]))
            if row["after_sha256"] is None:
                del state[path]
            else:
                state[path] = dict(mode=row["after_mode"], sha256=row["after_sha256"])
        preceding = record["target_commit"]
    observed = {path: dict(mode=value["mode"], sha256=digest((target / path).read_bytes()))
                for path, value in current_tree.items()}
    if preceding != head or state != observed:
        raise ValueError("final tracked tree contains undeclared difference")

    selected = {(r["source"], r["path"]): r for r in imported["files"]}
    originals = defaultdict(list)
    source_rows = []
    by_source_path = {(r["source"], r["path"]): r for r in admitted["files"]}
    for row in admitted["files"]:
        source, old_path = row["source"], row["path"]
        entry = selected.get((source, old_path))
        initial_path = entry["initial_target_path"] if entry else old_path if source == "nsealr" else None
        final_path = row["destination"]
        if row["action"] == "deduplicate" and row.get("canonical"):
            canonical_row = by_source_path[(row["canonical"]["source"], row["canonical"]["path"])]
            final_path = canonical_row["destination"]
        if final_path not in current_tree:
            final_path = None
        if entry and final_path is None and not changes.get(initial_path):
            raise ValueError("selected source disappeared without a declaration")
        if final_path:
            final = dict(path=final_path, blob=current_tree[final_path]["blob"], **observed[final_path])
            originals[final_path].append(dict(source=source, path=old_path,
                relationship="deduplicated counterpart" if row["action"] == "deduplicate" else "selected origin"))
            disposition = ("deduplicated into authoritative artifact" if row["action"] == "deduplicate"
                else "original bytes and mode retained" if final["sha256"] == row["sha256"] and final["mode"] == row["mode"]
                else "selected source transformed by declared patches")
        else:
            final = None
            disposition = ("selected source removed by declared patch; original recoverable"
                if entry else "duplicate of retired contract; no active counterpart"
                if row["action"] == "deduplicate" else row["action"])
        source_rows.append(dict(source=source, source_commit=row["commit"],
            source_path=old_path, source_blob=row["blob"], source_mode=row["mode"],
            source_sha256=row["sha256"], admission_action=row["action"],
            admission_rule=row["rule"], reason=row["reason"],
            rights_basis=row.get("rights_basis", "No new content import; preserve source ownership and existing notices."),
            initial_target_path=initial_path, initial_copy=entry["copy"] if entry else None,
            initial_blob=initial_tree[initial_path]["blob"] if initial_path in initial_tree else None,
            final=final, final_disposition=disposition,
            declarations=sorted({x["number"] for p in (initial_path, final_path) if p for x in changes.get(p, [])})))

    final_files = [dict(path=path, **current_tree[path], sha256=observed[path]["sha256"],
        initial_blob=initial_tree.get(path, {}).get("blob"),
        origins=originals.get(path, []), declarations=changes.get(path, []),
        provenance="initial admitted source" if path in initial_tree else "declared migration addition")
        for path in sorted(current_tree)]
    frozen = json.loads((report / "admission-evidence/closed-evidence.json").read_bytes())
    for row in frozen["artifacts"]:
        if current_tree.get(row["path"]) != dict(mode=row["mode"], blob=row["blob"]) or observed[row["path"]]["sha256"] != row["sha256"]:
            raise ValueError("closed evidence changed")
    graph = (target / "plan/work-items.json").read_bytes()
    original_graph = read_git(target, "show", manifest["sources"][0]["commit"] + ":docs/restart/work-items.json")
    # The graph move was byte exact. The sole later operational-policy field is
    # declared separately; no task, closed acceptance or other graph byte changes.
    policy = json.loads(graph)["execution_model_policy"]
    policy_source = "7c9b9a9d6e1874c7a5b09cee1daaec48fc08085e"
    expected_policy = json.loads(read_git(author, "show", policy_source + ":docs/restart/work-items.json"))["execution_model_policy"]
    expected_policy["integration"] = ("Declared operational-policy-only A02 transformation under the latest maintainer authority. "
        "Source main f2 remains frozen; task records, historical O01 evidence and the unmerged pause task reconciliation are unchanged. "
        "Candidate policy awaits distinct review and normal adoption.")
    addition = canonical({"execution_model_policy": policy}).removeprefix(b"{\n").removesuffix(b"\n}\n")
    expected_graph = original_graph.removesuffix(b"\n}\n") + b",\n" + addition + b"\n}\n"
    if (digest(original_graph) != frozen["graph_sha256"] or graph != expected_graph
            or policy != expected_policy or "docs/restart/work-items.json" in current_tree):
        raise ValueError("graph exceeds exact move plus declared current operational policy")
    graph_verification = dict(original_move_byte_exact=True, all_47_task_records_unchanged=True,
        sole_later_difference="execution_model_policy", policy_source_commit=policy_source,
        historical_graph_sha256=digest(original_graph), current_graph_sha256=digest(graph),
        historical_closed_acceptance_and_model_evidence_unchanged=True)
    current_contracts = json.loads((target / "plan/evidence-index.json").read_bytes())["current_contracts"]
    for row in current_contracts:
        if observed[row["current_path"]]["sha256"] != row["initial_relocated_sha256"]:
            raise ValueError("current contract exceeds declared link relocation")

    refs = json.loads((runtime / replay_name / "initial-import/public-refs-after/summary.json").read_bytes())
    write("final-source-map.json", dict(schema_version=1, target_commit=head,
        target_tree=read_git(target, "rev-parse", "HEAD^{tree}").decode().strip(),
        initial_commit=imported["initial_commit"], initial_tree=imported["initial_tree"],
        admission_package=imported["admitted_package"], coordinator_decision=imported["coordinator_decision"],
        original_admitted_map_sha256=digest((report / "admission-evidence/file-dispositions.json").read_bytes()),
        patch_series_sha256=digest((patches / "series.json").read_bytes()),
        complete_initial_plus_declared_tree_equal=True, selected_source_count=len(selected),
        public_and_selected_private_file_dispositions=source_rows,
        excluded_private_counts_only=admitted["private_excluded_counts"],
        excluded_private_paths_or_bodies_published=False,
        counts=dict(Counter(r["final_disposition"] for r in source_rows)),
        rights_review="Prior exact admission and narrow privacy reviews remain binding; final independent review is pending. No blanket relicensing.",
        current_contracts=current_contracts,
        closed_tasks=[r["id"] for r in frozen["tasks"]],
        immutable_artifact_references=sum(r["artifact_references"] for r in frozen["tasks"]),
        immutable_unique_files=len(frozen["artifacts"]),
        immutable_bytes_modes_blobs_and_task_records_verified=True,
        graph_verification=graph_verification))
    write("final-tree.json", dict(target_commit=head, tracked_file_count=len(final_files), files=final_files))
    write("source-references.json", dict(target_commit=head, public_sources=refs["public_sources"],
        observed_utc=refs["observed_utc"], target_ref_policy="Only refs/heads/rehearsal; source evidence tags remain source references and are not rewritten or relabeled as release tags.",
        private_sources=[dict(name=r["name"], selected_commit=r["commit"], selected_tree=r["tree"],
            disposition="selected licensed files only" if r["name"] == "lab" else "protected recovery only; no content/history import",
            private_refs="Protected dated all-ref recovery records; names and objects not exported here.")
            for r in manifest["sources"] if r["visibility"] == "private"]))

    # Only these explicit records are exportable; no recursion through repositories.
    for name in ["resume-navigation-execution-01", "resume-navigation-execution-02", "source-replay-execution-03", "model-policy-execution-01", "source-replay-execution-04", "final-report-execution-02", "final-package-validation-01", "final-package-validation-02", "final-package-validation-03", "final-package-validation-04", "final-package-validation-05"]:
        for source in sorted((runtime / name).iterdir()):
            if source.is_file() and source.suffix in {".json", ".log", ".sh"}:
                copy(source, f"execution/{name}/{source.name}")
    copy(runtime / "workspace-recovery-05/summary.json", "execution/workspace-recovery-05-summary.json")
    copy(runtime / "rehearsal-01/import-map.json", "execution/initial-import-map.json")

    failures = []
    for source in sorted((report / "execution").rglob("commands.json")):
        rows = json.loads(source.read_bytes())
        if not isinstance(rows, list):
            continue
        for row in rows:
            if row.get("exit_code", 0):
                log = source.parent / row["log"]
                failures.append(dict(commands=source.relative_to(report).as_posix(),
                    label=row["label"], exit_code=row["exit_code"],
                    log=log.relative_to(report).as_posix(), log_sha256=digest(log.read_bytes()),
                    disposition="Preserved failed observation; see failure-removal-ledger.md for cause, correction and final acceptance."))
    write("failure-observations.json", dict(scope="Every nonzero exit in exported A02 execution command records; inherited before-state failures remain in their original source evidence.", observations=failures))
    print(json.dumps(dict(target=head, source_rows=len(source_rows), final_files=len(final_files),
        frozen_files=len(frozen["artifacts"]), failures=len(failures),
        all_tracked_changes_declared=True)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author-repo", type=Path, required=True)
    parser.add_argument("--replay", required=True)
    args = parser.parse_args()
    main(args.author_repo, args.replay)
