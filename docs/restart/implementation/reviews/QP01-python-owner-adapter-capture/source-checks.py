"""Read-only Git/JSON/AST checks for exact 77b68113 delivery review only."""
import ast
import collections
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[5]
CANDIDATE = "77b681135a92283305bb7ae48de6f75f463a1ffb"
BASE = "8f0c4bc54f72ea62e201fdf19be9380f4b20c877"
PREP = "c1d21a81dd16a342dcb53cee972a3b6c532679fe"
AUTHOR = "28a84f37190a4d36637acbe7614940f4218621dc"
REVIEW = "3c9afc1c08c078704026694e2ff463eabb3ab8ac"
PREP_REVIEW = "7031d05e13b0f0d417c7c907c094a69edcb493e0"
Q01 = "71329dd8a0a8dbe7840a953863eead59f18b128f"
ADOPTION = "457bd387168ed8861f67edae0eeac4481dc80d5a"
DC = "dc0b7c81a12bf83d70b6ce9ecd65b49ce55fc082"
CHECKER = "docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py"
PREFIX = "docs/restart/implementation/QP01/python-owner-adapter/"


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def blob(ref, path):
    return git("show", ref + ":" + path)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tree(ref):
    entries = {}
    for row in git("ls-tree", "-rz", "--full-tree", ref).split(b"\0"):
        if row:
            meta, path = row.split(b"\t", 1)
            mode, kind, oid = meta.decode().split()
            entries[path.decode()] = (mode, kind, oid)
    assert entries
    return entries


def changed(a, b):
    return {p for p in a.keys() | b.keys() if a.get(p) != b.get(p)}


def main():
    current, base, author = tree(CANDIDATE), tree(BASE), tree(AUTHOR)
    assert git("rev-parse", CANDIDATE + "^{tree}").decode().strip() == "73bfe26ede7139953a7b6f72bb998fab321cfc01"
    author_paths = changed(base, author)
    assert len(author_paths) == 50 and not (author_paths & base.keys())
    micro_prefix = "docs/restart/implementation/reviews/QP01-python-owner-adapter-micro/"
    micro_paths = {p for p in tree(REVIEW) if p.startswith(micro_prefix)}
    assert len(micro_paths) == 19
    metadata_path = "docs/restart/implementation/reviews/QP01-python-owner-adapter-delivery-metadata.json"
    q01_path = "docs/restart/implementation/reviews/Q01-current-documentary-adoption.json"
    adoption_prefix = "docs/restart/implementation/reviews/QP01-cold-capture/adoption/"
    adoption_paths = {p for p in tree(ADOPTION) if p.startswith(adoption_prefix)}
    assert len(adoption_paths) == 8
    copies = []
    for source, paths, role in [(AUTHOR, author_paths, "author50"), (REVIEW, micro_paths, "A02_MICRO19"),
                                (PREP_REVIEW, {metadata_path}, "A02_preparation1"), (Q01, {q01_path}, "A02_Q01_documentary1"),
                                (ADOPTION, adoption_paths, "actual8f_adoption8")]:
        source_tree = tree(source)
        for path in sorted(paths):
            assert current[path] == source_tree[path]
            data = blob(CANDIDATE, path)
            copies.append(dict(path=path, source_commit=source, role=role, mode=current[path][0],
                               blob=current[path][2], bytes=len(data), sha256=sha(data)))
    root_paths = {"docs/restart/README.md", "plan/work-items.json", CHECKER} | {
        PREFIX + "capture-checks/" + p for p in ["README.md", "checker-controls.py", "result.json"]}
    copied = {row["path"] for row in copies}
    assert len(copied) == 79 and changed(base, current) == copied | root_paths
    assert len(changed(base, current)) == 85
    assert {p for p in changed(base, current) if p in base} == {"docs/restart/README.md", "plan/work-items.json", CHECKER}
    assert all(current[p] == base[p] for p in base.keys() - root_paths)

    source = blob(CANDIDATE, CHECKER)
    old = blob(BASE, CHECKER)
    assert sha(source) == "f1292809dcf594aee4b50820aa1e3f1d320a419ca6da55b88b314a5559a147df"
    assert sha(old) == "7d5a1669ee2ff366ef34b710e8e8b3bdf25531d6e72ca3fc35442acc653f354d"
    functions = lambda data: {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(data).body if isinstance(n, ast.FunctionDef)}
    assert functions(source)["verify_first"] == functions(old)["verify_first"]

    original = json.loads(blob(BASE, "plan/work-items.json"))
    graph = json.loads(blob(CANDIDATE, "plan/work-items.json"))
    assert {k: v for k, v in graph.items() if k != "tasks"} == {k: v for k, v in original.items() if k != "tasks"}
    assert len(graph["tasks"]) == len(original["tasks"]) == 47
    base_tasks = {t["id"]: t for t in original["tasks"]}
    tasks = {t["id"]: t for t in graph["tasks"]}
    assert list(tasks) == list(base_tasks)
    changes = {}
    mutable = {"QP01": {"result_artifacts", "current_checkpoint"}, "Q01": {"result_artifacts", "current_checkpoint", "integration"}}
    for name, task in tasks.items():
        fields = {k for k in task.keys() | base_tasks[name].keys() if task.get(k) != base_tasks[name].get(k)}
        assert fields <= mutable.get(name, set())
        if fields:
            changes[name] = sorted(fields)
    assert set(changes) == {"Q01", "QP01"}
    historical_brief = "docs/restart/implementation/QP01/host-coordinator/brief.md"
    inherited_reference_observations = []
    for name in ["Q01", "QP01"]:
        for row in tasks[name]["result_artifacts"]:
            actual = sha(blob(CANDIDATE, row["path"]))
            if row["path"] == historical_brief:
                # The unchanged graph retains the original 7996 preparation binding.
                original_source = "7996b15d34766e0de1b8c395fb7bcc0b02079935"
                assert row in base_tasks[name]["result_artifacts"]
                assert sha(blob(original_source, historical_brief)) == row["sha256"]
                assert current[historical_brief] == base[historical_brief]
                inherited_reference_observations.append(dict(path=historical_brief,
                    graph_sha256=row["sha256"], current_sha256=actual,
                    historical_source=original_source, introduced_by_this_candidate=False))
            else:
                assert actual == row["sha256"]
    old_refs = {r["path"]: r["sha256"] for r in base_tasks["QP01"]["result_artifacts"]}
    new_refs = {r["path"]: r["sha256"] for r in tasks["QP01"]["result_artifacts"]}
    assert all(new_refs[p] == digest for p, digest in old_refs.items() if p != CHECKER)
    assert new_refs[CHECKER] == sha(source)

    q01 = json.loads(blob(CANDIDATE, q01_path))
    qrefs = q01["artifact_source_map"]["refs"]
    assert len(qrefs) == 40 and len(q01["criteria"]) == 3
    origin_counts = collections.Counter()
    for row in qrefs:
        path, origin = row["path"], row["origin"]
        source_path = origin.get("source_path", path)
        assert current[path] == tree(origin["commit"])[source_path]
        assert sha(blob(CANDIDATE, path)) == row["sha256"]
        origin_counts[origin["commit"]] += 1
    assert origin_counts["05a1b4c8e7e0cab9fa4c08e3358cc3ef72d97896"] == 23
    assert origin_counts[BASE] == 3 and sum(origin_counts.values()) == 40
    assert tasks["Q01"]["result_artifacts"][:-1] == base_tasks["Q01"]["result_artifacts"]
    for row in q01["original_four_specification_review_copies"]:
        assert current[row["path"]] == tree(row["origin_commit"])[row["path"]]
        assert sha(blob(CANDIDATE, row["path"])) == row["sha256"]
    for row in q01["source_context_map"]:
        assert sha(blob(row["original_commit"], row["path"])) == row["original_sha256"]
        assert sha(blob(CANDIDATE, row["path"])) == row["actual_main_sha256"]
    assert q01["actual_source"]["commit"] == BASE

    raw_path = Path("/home/tux/nsealr/.restart-tools/goal/qp01-python-owner-adapter-runtime-2026-10-24/full-ci-02/make-ci.log")
    raw = raw_path.read_bytes()
    packed = blob(CANDIDATE, PREFIX + "negative/full-validation/stable/make-ci.log.gz")
    assert gzip.decompress(packed) == raw
    assert sha(raw) == "584e3fc3868bc8c0efafc6e1f155db4dde30f8a5f89bcaa8be9f139d462e7dc5"
    receipt = json.loads(blob(CANDIDATE, PREFIX + "capture-checks/result.json"))
    repeated = json.loads((Path(__file__).parent / "checker-controls-01/result.json").read_text())
    for key in ["positive", "mutations", "checker_sha256", "driver_sha256", "original_log_sha256", "optimized_mode_refused"]:
        assert receipt[key] == repeated[key]
    qualified = json.loads(blob(CANDIDATE, PREFIX + "negative/final-source-correspondence.json"))
    assert qualified["qualified_complete_gate_source"] == DC
    runtime_inputs = []
    for row in qualified["source_bindings"]:
        path = row["path"]
        assert current[path] == tree(DC)[path]
        assert sha(blob(CANDIDATE, path)) == row["sha256"]
        runtime_inputs.append(path)

    result = dict(candidate=CANDIDATE, tree=git("rev-parse", CANDIDATE + "^{tree}").decode().strip(),
                  actual_base=BASE, preparation=PREP, author=AUTHOR, copies=copies,
                  exact_copy_count=len(copies), author_postimages=50, selected_A02_review_postimages=21,
                  exact_adoption_postimages=8, delta_paths=85, added_paths=82, existing_paths_changed=3,
                  all_other_base_paths_exact=len(base)-3, root_authored_paths=sorted(root_paths),
                  graph_changed_fields=changes, tasks=47, all_status_criteria_dependencies_resources_releases_and_globals_exact=True,
                  Q01_original_refs=40, Q01_origin_counts=dict(origin_counts), Q01_current_refs=len(tasks["Q01"]["result_artifacts"]),
                  QP01_current_refs=len(tasks["QP01"]["result_artifacts"]),
                  inherited_reference_observations=inherited_reference_observations,
                  verify_first_AST_identical=True, old_checker_sha256=sha(old), active_checker_sha256=sha(source),
                  raw_original_sha256=sha(raw), raw_bytes=len(raw), gzip_sha256=sha(packed), compressed_original_byte_exact=True,
                  author_and_reviewer_control_results_exact=True, qualified_runtime_input_count=len(runtime_inputs),
                  qualified_runtime_inputs=runtime_inputs, product_builds_or_runs=0, hosted_queries=0)
    (Path(__file__).parent / "source-checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"copies", "qualified_runtime_inputs"}}))


if __name__ == "__main__":
    main()
