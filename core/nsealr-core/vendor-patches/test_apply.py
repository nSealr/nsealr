"""Reject source or checksum changes outside the authenticated vendor patches."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PATCHES = Path(__file__).resolve().parent
ROOT = PATCHES.parents[2]


class VendorAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nsealr-vendor-admission-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in json.loads((PATCHES / "patches.json").read_text()):
            shutil.copytree(ROOT / "vendor" / name, self.root / "vendor" / name)
        self.source = self.root / "vendor/hmac/src/lib.rs"
        self.checksum = self.root / "vendor/hmac/.cargo-checksum.json"

    def run_patch(self, succeeds):
        before = self.checksum.read_bytes()
        run = subprocess.run([sys.executable, str(PATCHES / "apply.py"), str(self.root)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode == 0, succeeds, run.stdout + run.stderr)
        if not succeeds:
            self.assertEqual(self.checksum.read_bytes(), before)

    def test_exact_patched_sources_are_idempotent(self):
        self.run_patch(True)
        self.run_patch(True)

    def test_unlisted_source_mutation_is_rejected(self):
        self.source.write_bytes(self.source.read_bytes() + b"\n// changed source\n")
        self.run_patch(False)

    def test_matching_forged_checksum_cannot_admit_changed_source(self):
        self.source.write_bytes(self.source.read_bytes() + b"\n// changed source\n")
        record = json.loads(self.checksum.read_text())
        record["files"]["src/lib.rs"] = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.checksum.write_text(json.dumps(record))
        self.run_patch(False)

    def test_unexpected_file_is_rejected(self):
        (self.source.parent / "extra.rs").write_text("// unreviewed source\n")
        self.run_patch(False)

    def test_missing_checksum_file_entry_is_rejected(self):
        record = json.loads(self.checksum.read_text())
        del record["files"]["src/lib.rs"]
        self.checksum.write_text(json.dumps(record))
        self.run_patch(False)

    def test_source_symlink_is_rejected(self):
        other = self.root / "copy.rs"
        other.write_bytes(self.source.read_bytes())
        self.source.unlink()
        self.source.symlink_to(other)
        self.run_patch(False)

    def test_bad_later_crate_cannot_mutate_earlier_checksums(self):
        source = self.root / "vendor/unicode-normalization/src/lookups.rs"
        source.write_bytes(source.read_bytes() + b"\n// changed source\n")
        self.run_patch(False)

    def test_hkdf_matching_checksum_cannot_admit_unguarded_output(self):
        source = self.root / "vendor/hkdf/src/lib.rs"
        source.write_bytes(source.read_bytes() + b"\n// unreviewed change\n")
        checksum = source.parent.parent / ".cargo-checksum.json"
        record = json.loads(checksum.read_text())
        record["files"]["src/lib.rs"] = hashlib.sha256(source.read_bytes()).hexdigest()
        checksum.write_text(json.dumps(record))
        self.run_patch(False)


if __name__ == "__main__":
    unittest.main()
