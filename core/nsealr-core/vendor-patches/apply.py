#!/usr/bin/env python3
"""Apply or verify the exact bounded recovery vendor changes; no downloads."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

patches = Path(__file__).resolve().parent
root = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else patches.parents[2]
manifest = json.loads((patches / "patches.json").read_text())
admitted = {}
for crate, record in manifest.items():
    package = root / "vendor" / crate
    checksum = package / ".cargo-checksum.json"
    if package.is_symlink() or checksum.is_symlink():
        raise SystemExit(f"Unexpected source link: {crate}")
    expected = record["upstream_files"]
    actual = {p.relative_to(package).as_posix(): p for p in package.rglob("*") if p.is_file() or p.is_symlink()}
    if set(actual) != set(expected) | {".cargo-checksum.json"}:
        raise SystemExit(f"Unexpected source file set: {crate}")
    contents = json.loads(checksum.read_text())
    if contents["package"] != record["crate_archive_sha256"] or set(contents["files"]) != set(expected):
        raise SystemExit(f"Unexpected crate archive identity or checksum file set: {crate}")
    states = set()
    for name, original in expected.items():
        if actual[name].is_symlink():
            raise SystemExit(f"Unexpected source link: {crate}/{name}")
        digest = hashlib.sha256(actual[name].read_bytes()).hexdigest()
        hashes = record["files"].get(name)
        if hashes is None:
            if digest != original or contents["files"][name] != original:
                raise SystemExit(f"Unexpected unchanged source: {crate}/{name}")
            continue
        if digest == hashes["original_sha256"]:
            states.add("original")
        elif digest == hashes["patched_sha256"]:
            states.add("patched")
        else:
            raise SystemExit(f"Unexpected source: {crate}/{name}")
        if contents["files"][name] not in hashes.values():
            raise SystemExit(f"Unexpected patched checksum: {crate}/{name}")
    if states not in ({"original"}, {"patched"}):
        raise SystemExit(f"Mixed original/patched state: {crate}")
    admitted[crate] = (states, contents)

# Check every crate before changing any file. A declared patch can update only
# its named entries; it must never bless an unrelated vendor modification.
for crate, record in manifest.items():
    package = root / "vendor" / crate
    states, contents = admitted[crate]
    if states == {"original"}:
        with (patches / f"{crate}.patch").open("rb") as patch:
            subprocess.run(["patch", "-p1", "--batch", "--fuzz=0"], cwd=root, stdin=patch, check=True)
    for name, hashes in record["files"].items():
        if hashlib.sha256((package / name).read_bytes()).hexdigest() != hashes["patched_sha256"]:
            raise SystemExit(f"Patch verification failed: {crate}/{name}")
        contents["files"][name] = hashes["patched_sha256"]
    (package / ".cargo-checksum.json").write_text(json.dumps(contents, separators=(",", ":")))
    print(f"Verified recovery patch: {crate} {record['version']}")
