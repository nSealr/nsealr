#!/usr/bin/env python3
"""Authenticate pinned threshold vendor bytes and all vendor Git/checksum closure."""
from pathlib import Path, PurePosixPath
import argparse
import difflib
import hashlib
import json
import subprocess
import tomllib

PIN = "0966bd1529aa062ad3b621af99e277f976b1c0f0"
URL = "https://github.com/ZcashFoundation/frost"
CRATE = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *arguments):
    return subprocess.check_output(["git", "-C", str(root), *arguments])


def file_map(directory):
    result = {}
    require(not directory.is_symlink(), f"source directory is a symlink: {directory}")
    for path in directory.rglob("*"):
        require(not path.is_symlink(), f"source symlink: {path}")
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = path
    return result


def verify(repo, upstream):
    manifest = json.loads((CRATE / "patches/vendor-admission.json").read_text())
    require(set(manifest["packages"]) == {"frost-core", "frost-rerandomized", "frost-secp256k1-tr", "chacha20"},
            "unexpected authenticated threshold package set")
    require(manifest["frost_commit"] == PIN and manifest["frost_git"] == URL,
            "unexpected FROST manifest identity")
    require(git(upstream, "rev-parse", "HEAD").decode().strip() == PIN,
            "upstream HEAD differs from the pinned FROST commit")
    require(not git(upstream, "status", "--porcelain").strip(), "upstream reference is dirty")
    require(Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve() == repo,
            "repository path must be a Git root")

    with (repo / "Cargo.lock").open("rb") as source:
        lock = tomllib.load(source)["package"]
    with (repo / ".cargo/config.toml").open("rb") as source:
        config = tomllib.load(source)["source"]
    require(config.get("crates-io") == {"replace-with": "vendored-sources"},
            "unexpected crates.io Cargo source replacement")
    source_key = f"git+{URL}?rev={PIN}"
    expected_source = {"git": URL, "rev": PIN, "replace-with": "vendored-sources"}
    require(config.get(source_key) == expected_source, "unexpected FROST Cargo source replacement")
    require(config.get("vendored-sources") == {"directory": "vendor"},
            "unexpected vendor directory")
    with (repo / "core/nsealr-threshold/Cargo.toml").open("rb") as source:
        dependencies = tomllib.load(source)["dependencies"]
    require(dependencies["frost-secp256k1-tr"] ==
            {"git": URL, "rev": PIN, "default-features": False},
            "threshold manifest differs from the pinned FROST dependency")
    require(dependencies["chacha20"] == {"version": "=0.10.2", "default-features": False,
            "features": ["rng", "zeroize"]}, "unexpected ChaCha20 dependency")

    for package, record in manifest["packages"].items():
        matches = [entry for entry in lock if entry["name"] == package]
        require(len(matches) == 1, f"unexpected lockfile entries: {package}")
        entry = matches[0]
        require(entry["version"] == record["version"], f"unexpected lockfile version: {package}")
        if package.startswith("frost-"):
            require(entry["source"] == f"{source_key}#{PIN}", f"unexpected lockfile source: {package}")
            original_cargo = git(upstream, "show", f"{PIN}:{package}/Cargo.toml")
            require(sha256(original_cargo) == record["upstream_cargo_sha256"],
                    f"unexpected upstream Cargo.toml: {package}")
            for name, original_path in record["upstream_git_paths"].items():
                original = git(upstream, "show", f"{PIN}:{original_path}")
                require(sha256(original) == record["upstream_files"][name],
                        f"upstream manifest mismatch: {package}/{name}")
        else:
            require(entry["source"] == "registry+https://github.com/rust-lang/crates.io-index" and
                    entry["checksum"] == record["package_checksum"],
                    f"unexpected registry archive identity: {package}")
        directory = repo / "vendor" / package
        actual = file_map(directory)
        expected = dict(record["upstream_files"])
        for name, patch in record["patched_files"].items():
            require(expected[name] == patch["original_sha256"], f"patch original mismatch: {package}/{name}")
            expected[name] = patch["patched_sha256"]
        require(set(actual) == set(expected) | {".cargo-checksum.json"},
                f"unexpected authenticated file set: {package}")
        checksum = json.loads(actual[".cargo-checksum.json"].read_text())
        require(checksum == {"files": expected, "package": record["package_checksum"]},
                f"unauthenticated checksum manifest: {package}")
        for name, digest in expected.items():
            require(sha256(actual[name].read_bytes()) == digest, f"unauthenticated source: {package}/{name}")

    patch_bytes = (CRATE / "patches/frost-core-zeroize.patch").read_bytes()
    require(sha256(patch_bytes) == manifest["frost_patch_sha256"], "unexpected FROST patch bytes")
    originals = json.loads((CRATE / "patches/frost-core-original-hashes.json").read_text())
    declared = manifest["packages"]["frost-core"]["patched_files"]
    require(originals == {name: record["original_sha256"] for name, record in declared.items()},
            "unexpected FROST changed-file map")
    patch = []
    for name in originals:
        original = git(upstream, "show", f"{PIN}:frost-core/{name}").decode()
        changed = (repo / "vendor/frost-core" / name).read_text()
        patch.extend(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                     fromfile="a/" + name, tofile="b/" + name))
    require("".join(patch).encode() == patch_bytes, "FROST cleanup diff differs from the declared patch")

    # Closure covers every vendored package, including files ignored by Git patterns.
    tracked = {name.decode() for name in git(repo, "ls-files", "-z", "--", "vendor").split(b"\0") if name}
    admitted = set()
    files = 0
    packages = 0
    for directory in sorted((repo / "vendor").iterdir()):
        require(directory.is_dir() and not directory.is_symlink(), f"unexpected vendor entry: {directory}")
        actual = file_map(directory)
        require(".cargo-checksum.json" in actual, f"missing vendor checksum: {directory.name}")
        checksum = json.loads(actual[".cargo-checksum.json"].read_text())
        expected = checksum["files"]
        require(set(actual) == set(expected) | {".cargo-checksum.json"},
                f"vendor file/checksum set mismatch: {directory.name}")
        for name, digest in expected.items():
            path = PurePosixPath(name)
            require(not path.is_absolute() and ".." not in path.parts, f"invalid vendor path: {name}")
            require(sha256(actual[name].read_bytes()) == digest, f"vendor checksum mismatch: {directory.name}/{name}")
        admitted.update(f"vendor/{directory.name}/{name}" for name in actual)
        files += len(expected)
        packages += 1
    require(tracked == admitted,
            f"vendor Git/checksum closure mismatch; untracked={sorted(admitted - tracked)}; missing={sorted(tracked - admitted)}")
    print(f"PASS pinned FROST and ChaCha20 complete source maps; exact cleanup patch; "
          f"{packages} vendor packages/{files} checksummed files have Git closure")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path, help="clean FROST checkout at the pinned commit")
    parser.add_argument("--repo", type=Path, default=CRATE.parents[1], help="repository to verify")
    args = parser.parse_args()
    try:
        verify(args.repo.resolve(), args.upstream.resolve())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"FAIL {error}") from error


if __name__ == "__main__":
    main()
