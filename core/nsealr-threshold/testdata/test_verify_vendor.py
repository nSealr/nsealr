"""Adverse admission tests; fixture writes stay in the workspace temporary area."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).with_name("verify-vendor.py")
UPSTREAM = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
PACKAGES = ("frost-core", "frost-rerandomized", "frost-secp256k1-tr", "chacha20", "thiserror")


class VendorAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if UPSTREAM is None:
            raise RuntimeError("pass the pinned clean FROST checkout as the first argument")
        parent = Path(os.environ.get("TMPDIR", ROOT / ".tmp"))
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent, prefix="threshold-admission-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name)
        cls.clean = cls.base / "clean"
        for name in PACKAGES:
            shutil.copytree(ROOT / "vendor" / name, cls.clean / "vendor" / name)
        for name in ("Cargo.lock", ".cargo/config.toml", "core/nsealr-threshold/Cargo.toml"):
            target = cls.clean / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        subprocess.run(["git", "init", "-q", str(cls.clean)], check=True)
        subprocess.run(["git", "-C", str(cls.clean), "add", "-f", "--", "vendor"], check=True)

    def setUp(self):
        self.root = self.base / self._testMethodName
        shutil.copytree(self.clean, self.root)

    def verify(self, succeeds, optimized=False, upstream=None):
        before = {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (self.root / "vendor").rglob("*") if p.is_file() and not p.is_symlink()}
        command = [sys.executable] + (["-O"] if optimized else [])
        result = subprocess.run(command + [str(SCRIPT), str(upstream or UPSTREAM), "--repo", str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, succeeds, result.stdout + result.stderr)
        after = {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (self.root / "vendor").rglob("*") if p.is_file() and not p.is_symlink()}
        self.assertEqual(before, after, "verification must never rewrite admitted files/checksums")

    def test_exact_sources_normal_and_optimized(self):
        self.verify(True)
        self.verify(True, optimized=True)

    def test_source_plus_matching_checksum_cannot_pass(self):
        for package, name in [("frost-core", "src/round2.rs"), ("frost-rerandomized", "src/lib.rs"),
                              ("frost-secp256k1-tr", "src/lib.rs"), ("chacha20", "src/lib.rs")]:
            with self.subTest(package=package):
                file = self.root / "vendor" / package / name
                file.write_bytes(file.read_bytes() + b"\n// harmless unreviewed source\n")
                checksum = self.root / "vendor" / package / ".cargo-checksum.json"
                data = json.loads(checksum.read_text())
                data["files"][name] = hashlib.sha256(file.read_bytes()).hexdigest()
                checksum.write_text(json.dumps(data))
                self.verify(False)
                self.verify(False, optimized=True)
                shutil.rmtree(self.root / "vendor" / package)
                shutil.copytree(self.clean / "vendor" / package, self.root / "vendor" / package)

    def test_file_set_and_checksum_entry_changes(self):
        for change in ("extra", "missing", "missing-entry", "extra-entry", "symlink"):
            with self.subTest(change=change):
                package = self.root / "vendor/frost-core"
                file = package / "src/round2.rs"
                checksum = package / ".cargo-checksum.json"
                if change == "extra":
                    (package / "src/unreviewed.rs").write_text("// harmless extra source\n")
                elif change == "missing":
                    file.unlink()
                elif change in ("missing-entry", "extra-entry"):
                    data = json.loads(checksum.read_text())
                    if change == "missing-entry": del data["files"]["src/round2.rs"]
                    else: data["files"]["extra.rs"] = "0" * 64
                    checksum.write_text(json.dumps(data))
                else:
                    file.unlink(); file.symlink_to(self.clean / "vendor/frost-core/src/round2.rs")
                self.verify(False)
                shutil.rmtree(package)
                shutil.copytree(self.clean / "vendor/frost-core", package)

    def test_checksums_cannot_reference_a_file_missing_from_git(self):
        subprocess.run(["git", "-C", str(self.root), "rm", "--cached", "--",
                        "vendor/thiserror/build/probe.rs"], check=True, capture_output=True)
        self.verify(False)

    def test_cargo_lock_and_dependency_identity(self):
        for name, old, new in [
            ("Cargo.lock", "65c35e4b699c7e15ccbe7ee35c005e4fc0a278d22238a2857e6ce2dadeda1b06", "0" * 64),
            (".cargo/config.toml", '[source.crates-io]\nreplace-with = "vendored-sources"', '[source.crates-io]'),
            (".cargo/config.toml", "0966bd1529aa062ad3b621af99e277f976b1c0f0", "0" * 40),
            ("core/nsealr-threshold/Cargo.toml", 'features = ["rng", "zeroize"]', 'features = ["rng"]'),
        ]:
            with self.subTest(name=name):
                file = self.root / name
                original = file.read_text()
                self.assertIn(old, original)
                file.write_text(original.replace(old, new))
                self.verify(False)
                file.write_text(original)

    def test_dirty_upstream_reference_is_rejected(self):
        clone = self.base / "dirty-reference"
        subprocess.run(["git", "clone", "-q", "--shared", str(UPSTREAM), str(clone)], check=True)
        file = clone / "frost-core/src/round2.rs"
        file.write_bytes(file.read_bytes() + b"\n// dirty reference\n")
        self.verify(False, upstream=clone)

    def test_wrong_upstream_commit_is_rejected(self):
        clone = self.base / "wrong-reference"
        subprocess.run(["git", "clone", "-q", "--shared", str(UPSTREAM), str(clone)], check=True)
        subprocess.run(["git", "-C", str(clone), "-c", "user.name=Admission Test",
                        "-c", "user.email=admission@example.invalid", "commit", "-q",
                        "--allow-empty", "-m", "Independent wrong-reference fixture"], check=True)
        self.verify(False, upstream=clone)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
