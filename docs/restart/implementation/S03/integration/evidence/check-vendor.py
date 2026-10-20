#!/usr/bin/env python3
"""Compare retained exact source and Cargo's independent two-lock union output."""
import hashlib
import json
from pathlib import Path
import tomllib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def files(root):
    return {str(p.relative_to(root)): sha(p) for p in root.rglob("*") if p.is_file()}

def main():
    vendor = ROOT / "vendor"
    output = ROOT / "tools/migration/.runtime/s03-vendor-union"
    before, after = files(vendor), files(output)
    changed = sorted(k for k in before.keys() & after.keys() if before[k] != after[k])
    missing = sorted(before.keys() - after.keys())
    assert not after.keys() - before.keys()
    assert all(k.endswith("/.cargo-checksum.json") for k in changed)
    packages = []
    comparisons = []
    for directory in sorted(p for p in vendor.iterdir() if p.is_dir()):
        package = tomllib.loads((directory / "Cargo.toml").read_text())["package"]
        source = json.loads((directory / ".cargo-checksum.json").read_bytes())
        generated = json.loads((output / directory.name / ".cargo-checksum.json").read_bytes())
        assert source["package"] == generated["package"]
        for path, digest in source["files"].items():
            assert sha(directory / path) == digest, (directory, path)
        for path, digest in generated["files"].items():
            # Re-vendoring an existing directory source can list its INPUT
            # checksum file. It hashes the admitted input, not its own output.
            if path == ".cargo-checksum.json":
                assert digest == sha(directory / path)
            else:
                assert source["files"][path] == digest, (directory, path)
        removed = sorted(source["files"].keys() - generated["files"].keys())
        assert set(removed) == {p.removeprefix(directory.name + "/") for p in missing
                                if p.startswith(directory.name + "/")}
        notices = [str(p.relative_to(vendor)) for p in directory.rglob("*")
                   if p.is_file() and any(s in p.name.upper() for s in ("LICENSE", "COPYING", "NOTICE"))]
        assert notices, directory
        packages.append(dict(directory=directory.name, name=package["name"], version=package["version"],
                             license=package.get("license"), checksum=source["package"], notices=notices))
        comparisons.append(dict(directory=directory.name, omitted_packaging_metadata=removed,
                                added_input_checksum_entry=".cargo-checksum.json" in generated["files"],
                                package_identity_and_retained_source_hashes_identical=True))
    result = dict(status="PASS_exact_dependency_identities_and_retained_source_bytes",
                  registry_packages=len(packages), local_packages=2, total_union_identities=len(packages)+2,
                  retained_source_files=before, license_notices=packages,
                  all_original_cargo_checksums_verified=True,
                  independent_cargo_vendor_output=dict(source_command="commands/vendor-union/command.json",
                      files=after, omitted_source_metadata=missing, rewritten_checksum_files=changed,
                      comparisons=comparisons),
                  disposition="Retain all admitted source/checksum/license bytes. Independent re-vendor output is not overlaid onto source.",
                  initial_probe_failures=[
                      "Whole-directory byte equality rejected documented re-vendor packaging/checksum differences; actual mismatch set retained here.",
                      "First comparison refinement raised KeyError for generated input checksum entries. Explicitly validated those against original input bytes instead."])
    (HERE / "vendor-union-check.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(dict(packages=len(packages), source_files=len(before), output_files=len(after),
                          omitted_metadata=len(missing), status=result["status"])))

if __name__ == "__main__":
    main()
