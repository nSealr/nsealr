#!/usr/bin/env python3
"""Independent data/mapping checks and hostile controls in two owned copies."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
BASE = "b1c90139a651895284b2624da7d12903cf16bc9d"
SOURCE = "03216fba02d229bcdb5c81d0573bbe26c6f35abc"
VECTOR = "docs/restart/implementation/S03/vectors.json"
CONFIG = "ci/core-test-projections.json"

def committed(commit, path):
    return subprocess.check_output(["git", "show", commit + ":" + path], cwd=ROOT)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def snapshot(path):
    assert all(p.is_file() and not p.is_symlink() for p in path.iterdir())
    return {p.name: p.read_bytes() for p in path.iterdir()}

def main():
    module = importlib.util.spec_from_file_location("s03_read_only_contracts", ROOT / "scripts/verify_contracts.py")
    verifier = importlib.util.module_from_spec(module)
    module.loader.exec_module(verifier)
    config = committed(BASE, CONFIG)
    vectors = committed(SOURCE, VECTOR)
    rows = json.loads(config)
    assert len(rows) == 170 and len({r["output"] for r in rows}) == 170
    controls = []
    def inputs(checkout):
        verifier.validate(checkout / "protocols/contracts/v1", ROOT)
        assert (checkout / CONFIG).read_bytes() == config, "stale/tampered projection mapping"
        assert (checkout / VECTOR).read_bytes() == vectors, "stale/tampered independent vectors"
    def outputs(output, expected):
        assert snapshot(output) == expected, "missing/extra/hidden/tampered projected output"
    def reject(name, call):
        try:
            call()
        except (AssertionError, ValueError, OSError, KeyError, TypeError):
            controls.append(dict(case=name, outcome="REJECT"))
        else:
            raise AssertionError("negative accepted: " + name)
    def change(path, data, call, name):
        previous = path.read_bytes()
        path.write_bytes(data)
        try:
            reject(name, call)
        finally:
            path.write_bytes(previous)
    def missing(path, call, name):
        previous = path.read_bytes()
        path.unlink()
        try:
            reject(name, call)
        finally:
            path.write_bytes(previous)
    runtime = ROOT / "tools/migration/.runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="s03-projection-controls-", dir=runtime) as temporary:
        parent = Path(temporary)
        results = []
        for name in ("first-checkout", "different/deeper-checkout"):
            checkout = parent / name
            (checkout / "ci").mkdir(parents=True)
            shutil.copytree(ROOT / "protocols/contracts/v1", checkout / "protocols/contracts/v1")
            (checkout / VECTOR).parent.mkdir(parents=True)
            (checkout / VECTOR).write_bytes(vectors)
            (checkout / CONFIG).write_bytes(config)
            script = checkout / "ci/project_core_fixtures.py"
            script.write_bytes(committed(BASE, "ci/project_core_fixtures.py"))
            baseline_output = checkout / "baseline-output"
            subprocess.run(["python3", str(script), str(baseline_output)], check=True)
            baseline = snapshot(baseline_output)
            assert len(baseline) == 173
            expected = {}
            for row in rows:
                value = json.loads((checkout / "protocols/contracts/v1" / row["artifact_path"]).read_bytes())
                for part in row["pointer"]:
                    value = value[int(part)] if isinstance(value, list) else value[part]
                data = value if row["encoding"] == "string" else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                expected[row["output"]] = data.encode("utf-8")
                assert baseline[row["output"]] == expected[row["output"]]
            # Three Rust helper files remain exact outputs of the immutable b1
            # data-only projector, independently of all new S03 implementation.
            expected.update({n: d for n, d in baseline.items() if n not in expected})
            expected["s03-vectors.json"] = vectors
            script.write_bytes((ROOT / "ci/project_core_fixtures.py").read_bytes())
            output = checkout / "combined-output"
            inputs(checkout)
            subprocess.run(["python3", str(script), str(output)], check=True)
            outputs(output, expected)
            results.append({n: sha(d) for n, d in snapshot(output).items()})
            if name != "first-checkout":
                continue
            artifact = checkout / "protocols/contracts/v1"
            artifact_file = artifact / json.loads((artifact / "manifest.json").read_bytes())["files"][0]["path"]
            missing(artifact_file, lambda: inputs(checkout), "missing_contract_source")
            change(artifact_file, artifact_file.read_bytes()+b" ", lambda: inputs(checkout), "tampered_contract_source")
            change(artifact / "manifest.json", (artifact / "manifest.json").read_bytes()+b"\n", lambda: inputs(checkout), "stale_or_modified_manifest")
            hidden = artifact / "vectors/.unadmitted-hidden"
            hidden.write_bytes(b"hidden")
            try:
                reject("extra_hidden_contract_source", lambda: inputs(checkout))
            finally:
                hidden.unlink()
            for label, mutation in (
                ("missing_mapping", lambda v: v.pop()),
                ("extra_mapping", lambda v: v.append(dict(v[0], output="extra.txt"))),
                ("changed_pointer", lambda v: v[0].update(pointer=["unadmitted"])),
                ("changed_output_mapping", lambda v: v[0].update(output="stale.txt")),
            ):
                changed = json.loads(config)
                mutation(changed)
                change(checkout / CONFIG, json.dumps(changed).encode(), lambda: inputs(checkout), label)
            missing(checkout / VECTOR, lambda: inputs(checkout), "missing_independent_vector_source")
            change(checkout / VECTOR, vectors+b"\n", lambda: inputs(checkout), "stale_independent_vector_source")
            field = output / rows[0]["output"]
            missing(field, lambda: outputs(output, expected), "missing_generated_output")
            change(field, field.read_bytes()+b"changed", lambda: outputs(output, expected), "tampered_generated_output")
            helper = output / "review-fixtures.rs"
            change(helper, helper.read_bytes()+b"// stale", lambda: outputs(output, expected), "stale_generated_helper")
            hidden = output / ".unadmitted-output"
            hidden.write_bytes(b"hidden")
            try:
                reject("extra_hidden_generated_output", lambda: outputs(output, expected))
            finally:
                hidden.unlink()
            inputs(checkout)
            outputs(output, expected)
        assert results[0] == results[1]
    assert VECTOR in (ROOT / "crates/nsealr-core/build.rs").read_text()
    result = dict(status="PASS", legacy_rows=170, legacy_helper_files=3, independent_vector_outputs=1,
                  byte_identical_across_two_checkout_paths=True, outputs=results[0],
                  original_source_vector_sha256=sha(vectors), config_sha256=sha(config),
                  negative_controls=controls, negative_count=len(controls),
                  scope="Data-only output equivalence and input/output provenance checks; no Rust/parser/signer/renderer computes expected data.")
    (HERE / "projection-checks.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(dict(status="PASS", outputs=len(results[0]), negative_controls=len(controls))))

if __name__ == "__main__":
    main()
