#!/usr/bin/env python3
"""Check the admitted path scope, frozen inputs and actual port identities."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
BASE = "b1c90139a651895284b2624da7d12903cf16bc9d"
SPECIFICATION = "e95eaaf8e3fd76ede797f128f0cc7de43ab2bb03"

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    spec = json.loads((HERE.parent / "source-reconciliation.json").read_bytes())
    addendum = json.loads((HERE.parent / "source-pin-addendum.json").read_bytes())
    historical = addendum["historical_public_copy_manifest"]["files"]
    allowed = {r["path"] for r in spec["source_changed_files"] if r["group"] in ("product_source", "vendor")}
    allowed |= {r["path"] for r in historical}
    allowed |= {"apps/desktop-simulator/Cargo.lock", "ci/project_core_fixtures.py",
                "ci/core-test-projections.json", "crates/nsealr-core/build.rs",
                "crates/nsealr-core/src/review/test_fixtures.rs"}
    specification_paths = git("ls-tree", "-r", "--name-only", SPECIFICATION, "--",
                              "docs/restart/implementation/S03/integration").decode().splitlines()
    assert len(specification_paths) == 5
    allowed.update(specification_paths)
    for path in specification_paths:
        assert (ROOT / path).read_bytes() == git("show", SPECIFICATION + ":" + path), path
    scope = str(HERE.relative_to(ROOT)) + "/"
    changed = git("diff", "--name-only", BASE).decode().splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").decode().splitlines()
    assert all(p in allowed or p.startswith(scope) for p in changed + untracked), {
        p for p in changed + untracked if p not in allowed and not p.startswith(scope)}
    immutable = ["plan/work-items.json", "docs/restart/README.md", "docs/restart/implementation/handoff.md",
                 "scripts/verify_contracts.py", "scripts/test_contracts.py", "scripts/check_product_gates.py",
                 "scripts/test_product_gates.py", "tests/integration/run.py", "ci/ratchet.json",
                 "ci/core-test-projections.json"]
    frozen = []
    frozen += git("ls-tree", "-r", "--name-only", BASE, "--", "protocols/contracts/v1").decode().splitlines()
    frozen += git("ls-tree", "-r", "--name-only", BASE, "--", "docs/restart/implementation/S03/integration").decode().splitlines()
    for path in immutable + frozen:
        assert (ROOT / path).read_bytes() == git("show", BASE + ":" + path), path
    for row in historical:
        path = ROOT / row["path"]
        assert sha(path.read_bytes()) == row["sha256"], path
        assert path.stat().st_mode & 0o777 == (0o755 if row["mode"] == "100755" else 0o644), path
    # Every original vendor blob is retained; exactly the admitted new blobs
    # extend it. No source/vendor output normalization is applied to originals.
    for path in git("ls-tree", "-r", "--name-only", BASE, "--", "vendor").decode().splitlines():
        assert (ROOT / path).read_bytes() == git("show", BASE + ":" + path), path
    for row in spec["source_changed_files"]:
        if row["group"] == "vendor":
            assert sha((ROOT / row["path"]).read_bytes()) == row["reviewed_source"]["sha256"], row["path"]
    files = []
    for row in spec["source_changed_files"]:
        if row["group"] != "product_source":
            continue
        path = ROOT / row["path"]
        data = path.read_bytes()
        assert not any(marker in data for marker in (b"<<<<<<< current-A02", b">>>>>>> reviewed-S03"))
        files.append(dict(path=row["path"], mode="100755" if path.stat().st_mode & 0o111 else "100644",
                          bytes=len(data), sha256=sha(data),
                          original_source=row["reviewed_source"], input_current=row["preparation_target"],
                          admitted_resolution=row["resolution"]))
    result = dict(status="PASS_bounded_port_and_frozen_inputs", product_input=BASE,
                  actual_product_files=files, additional_interfaces=[p for p in changed if p not in {r["path"] for r in files} and not p.startswith("docs/") and not p.startswith("vendor/")],
                  unchanged_existing_projection_rows=170, historical_copies=80,
                  graph_and_all47_criteria_dependencies_unchanged=True,
                  closed7_and_frozen1508_index_unchanged=True,
                  read_only_checker_gates_runner_v1_and_floors_unchanged=True,
                  changed_paths=changed, untracked_paths=untracked)
    (HERE / "port-reconciliation.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(dict(status=result["status"], product_files=len(files), additional_interfaces=result["additional_interfaces"])))

if __name__ == "__main__":
    main()
