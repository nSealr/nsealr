from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_fixture_snapshots import (
    DEFAULT_REQUIRED_SNAPSHOT_GLOBS,
    FixtureSnapshotError,
    compare_fixture_snapshots,
)


class FixtureSnapshotTests(unittest.TestCase):
    def test_companion_requires_feature_matrix_snapshots(self) -> None:
        self.assertIn("vectors/features/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["companion"])

    def test_companion_requires_route_selection_snapshots(self) -> None:
        self.assertIn("vectors/route-selections/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["companion"])

    def test_companion_requires_policy_change_snapshots(self) -> None:
        self.assertIn("vectors/policy-changes/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["companion"])
        self.assertIn(
            "schemas/policy-change-review-v0.schema.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["companion"],
        )

    def test_companion_requires_access_surface_snapshots(self) -> None:
        self.assertIn("vectors/access-surfaces/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["companion"])

    def test_companion_requires_nip46_connection_uri_snapshots(self) -> None:
        self.assertIn("vectors/nip46-connection-uris/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["companion"])

    def test_companion_requires_nip46_session_snapshots(self) -> None:
        self.assertIn("vectors/nip46-sessions/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["companion"])

    def test_esp32_nip46_invalid_snapshot_scope_excludes_session_lifecycle(self) -> None:
        self.assertIn("vectors/invalid/nip46-sign-event-*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"])
        self.assertNotIn("vectors/invalid/nip46*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"])

    def test_raspberry_requires_seedqr_snapshots(self) -> None:
        self.assertIn("vectors/seedqr/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["raspberry"])

    def test_raspberry_requires_nip19_nsec_snapshots(self) -> None:
        self.assertIn("vectors/nip19/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["raspberry"])

    def test_raspberry_requires_session_import_review_snapshots(self) -> None:
        self.assertIn("vectors/session-import-reviews/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["raspberry"])

    def test_raspberry_requires_session_source_backup_snapshots(self) -> None:
        self.assertIn("vectors/session-source-backups/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["raspberry"])

    def test_raspberry_requires_identity_route_snapshots(self) -> None:
        self.assertIn(
            "vectors/accounts/raspberry-qr-nip06-account-0.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["raspberry"],
        )
        self.assertIn("vectors/policies/manual-only-qr-vault.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["raspberry"])
        self.assertIn(
            "vectors/route-selections/raspberry-qr-sign-event-account-0.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["raspberry"],
        )

    def test_esp32_requires_nip19_nsec_snapshots(self) -> None:
        self.assertIn("vectors/nip19/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"])

    def test_esp32_requires_seedqr_snapshots(self) -> None:
        self.assertIn("vectors/seedqr/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"])

    def test_esp32_requires_session_import_review_snapshots(self) -> None:
        self.assertIn("vectors/session-import-reviews/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"])

    def test_esp32_requires_session_source_backup_snapshots(self) -> None:
        self.assertIn("vectors/session-source-backups/*.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"])

    def test_esp32_requires_identity_route_snapshots(self) -> None:
        self.assertIn("vectors/accounts/esp32-qr-nip06-account-0.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"])
        self.assertIn("vectors/accounts/esp32-usb-device-slot-0.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"])
        self.assertIn("vectors/policies/manual-only-qr-vault.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"])
        self.assertIn(
            "vectors/policies/manual-only-persistent-device.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"],
        )
        self.assertIn("vectors/policies/scoped-automation-daily-use.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"])
        self.assertIn(
            "vectors/policy-changes/esp32-usb-enable-kind-1-automation.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"],
        )
        self.assertIn(
            "vectors/route-selections/esp32-qr-sign-event-account-0.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"],
        )
        self.assertIn(
            "vectors/route-selections/esp32-usb-sign-event-slot-0.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["firmware"],
        )

    def test_hardware_requires_custom_wallet_route_snapshots(self) -> None:
        self.assertIn(
            "vectors/accounts/custom-hardware-wallet-slot-0.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["hardware"],
        )
        self.assertIn(
            "vectors/grants/custom-hardware-wallet-kind-1-session.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["hardware"],
        )
        self.assertIn(
            "vectors/policies/manual-only-persistent-device.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["hardware"],
        )
        self.assertIn(
            "vectors/policy-changes/custom-hardware-wallet-enable-kind-1-automation.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["hardware"],
        )
        self.assertIn(
            "vectors/policies/scoped-automation-daily-use.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["hardware"],
        )
        self.assertIn(
            "vectors/route-selections/custom-hardware-wallet-sign-event-slot-0.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["hardware"],
        )

    def test_smartcard_requires_identity_route_snapshots(self) -> None:
        self.assertIn("vectors/accounts/smartcard-slot-0.json", DEFAULT_REQUIRED_SNAPSHOT_GLOBS["smartcard"])
        self.assertIn(
            "vectors/policies/manual-only-displayless-smartcard.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["smartcard"],
        )
        self.assertIn(
            "vectors/route-selections/smartcard-sign-event-slot-0.json",
            DEFAULT_REQUIRED_SNAPSHOT_GLOBS["smartcard"],
        )

    def test_matching_snapshot_files_pass(self) -> None:
        with TemporaryDirectory() as tmp:
            org = Path(tmp)
            (org / "specs" / "vectors" / "devices").mkdir(parents=True)
            (org / "companion" / "tests" / "fixtures" / "specs" / "vectors" / "devices").mkdir(parents=True)
            (org / "specs" / "vectors" / "devices" / "status.json").write_text(
                '{"status":"ok"}\n',
                encoding="utf-8",
            )
            (org / "companion" / "tests" / "fixtures" / "specs" / "vectors" / "devices" / "status.json").write_text(
                '{"status":"ok"}\n',
                encoding="utf-8",
            )

            compare_fixture_snapshots(org=org, repositories=("companion",))

    def test_mismatched_snapshot_reports_repo_and_path(self) -> None:
        with TemporaryDirectory() as tmp:
            org = Path(tmp)
            (org / "specs" / "vectors" / "devices").mkdir(parents=True)
            (org / "companion" / "tests" / "fixtures" / "specs" / "vectors" / "devices").mkdir(parents=True)
            (org / "specs" / "vectors" / "devices" / "status.json").write_text(
                '{"status":"new"}\n',
                encoding="utf-8",
            )
            (org / "companion" / "tests" / "fixtures" / "specs" / "vectors" / "devices" / "status.json").write_text(
                '{"status":"old"}\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                FixtureSnapshotError,
                r"companion: vectors/devices/status\.json differs from specs",
            ):
                compare_fixture_snapshots(org=org, repositories=("companion",))

    def test_snapshot_without_live_specs_file_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            org = Path(tmp)
            (org / "specs").mkdir()
            (org / "raspberry" / "tests" / "fixtures" / "specs" / "vectors" / "review").mkdir(parents=True)
            (org / "raspberry" / "tests" / "fixtures" / "specs" / "vectors" / "review" / "stale.json").write_text(
                "{}\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                FixtureSnapshotError,
                r"raspberry: vectors/review/stale\.json is missing from specs",
            ):
                compare_fixture_snapshots(org=org, repositories=("raspberry",))

    def test_required_snapshot_glob_reports_missing_live_specs_file(self) -> None:
        with TemporaryDirectory() as tmp:
            org = Path(tmp)
            (org / "specs" / "vectors" / "review-transcripts").mkdir(parents=True)
            snapshot_root = org / "companion" / "tests" / "fixtures" / "specs" / "vectors" / "review-transcripts"
            snapshot_root.mkdir(parents=True)
            (org / "specs" / "vectors" / "review-transcripts" / "existing.json").write_text(
                '{"name":"existing"}\n',
                encoding="utf-8",
            )
            (org / "specs" / "vectors" / "review-transcripts" / "new.json").write_text(
                '{"name":"new"}\n',
                encoding="utf-8",
            )
            (snapshot_root / "existing.json").write_text(
                '{"name":"existing"}\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                FixtureSnapshotError,
                r"companion: vectors/review-transcripts/new\.json required snapshot is missing",
            ):
                compare_fixture_snapshots(
                    org=org,
                    repositories=("companion",),
                    required_snapshot_globs={"companion": ("vectors/review-transcripts/*.json",)},
                )


class ProvenanceSnapshotTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        import json
        import subprocess
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.org = Path(self.temporary.name)
        self.specs = self.org / "specs"
        self.snapshot = self.org / "firmware/tests/fixtures/specs"
        self.metadata_path = self.snapshot / "SOURCE.json"
        self.vector = "vectors/nip46-relay-steps/sign-event-response-step.json"
        self.hidden = "vectors/hidden/.gitkeep"
        for root in (self.specs, self.snapshot):
            for relative, content in ((self.vector, b'{"valid":true}\n'), (self.hidden, b"")):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        self.git("init", "-q")
        self.git("add", "vectors")
        self.git("-c", "user.name=Fixture test", "-c", "user.email=test@invalid.example",
                 "commit", "-qm", "Independent committed bytes")
        self.metadata = {
            "repository": "https://github.com/nSealr/specs", "commit": self.git("rev-parse", "HEAD").decode().strip(),
            "files": {relative: hashlib.sha256((self.specs / relative).read_bytes()).hexdigest()
                      for relative in (self.vector, self.hidden)},
        }
        self.write_metadata()

    def git(self, *args):
        import subprocess
        return subprocess.check_output(["git", *args], cwd=self.specs, stderr=subprocess.STDOUT)

    def write_metadata(self):
        import json
        self.metadata_path.write_text(json.dumps(self.metadata))

    def check(self):
        return compare_fixture_snapshots(org=self.org, repositories=("firmware",), required_snapshot_globs={})

    def forge(self, relative):
        import hashlib
        path = self.snapshot / relative
        if path.exists():
            self.metadata["files"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            self.metadata["files"].pop(relative, None)
        self.write_metadata()

    def test_complete_snapshot_counts_hidden_vector(self):
        self.assertEqual(self.check(), 2)

    def test_missing_manifest_rejects_before_iteration(self):
        self.metadata_path.unlink()
        with self.assertRaisesRegex(FixtureSnapshotError, "SOURCE.json"):
            self.check()

    def test_missing_manifest_and_v1_vector_rejects(self):
        self.metadata_path.unlink()
        (self.snapshot / self.vector).unlink()
        with self.assertRaisesRegex(FixtureSnapshotError, "SOURCE.json"):
            self.check()

    def test_missing_vectors_with_retained_or_forged_inventory_reject(self):
        for relative in (self.vector, self.hidden):
            path = self.snapshot / relative
            original = path.read_bytes()
            path.unlink()
            with self.subTest(relative=relative, forged=False), self.assertRaises(FixtureSnapshotError):
                self.check()
            self.forge(relative)
            with self.subTest(relative=relative, forged=True), self.assertRaises(FixtureSnapshotError):
                self.check()
            path.write_bytes(original)
            self.forge(relative)
        self.assertEqual(self.check(), 2)

    def test_extra_normal_and_hidden_vectors_reject_even_with_forged_inventory(self):
        for relative in ("vectors/extra.json", "vectors/.extra"):
            path = self.snapshot / relative
            path.write_bytes(b"{}")
            self.forge(relative)
            with self.subTest(relative=relative), self.assertRaises(FixtureSnapshotError):
                self.check()
            path.unlink()
            self.forge(relative)

    def test_tampered_normal_and_hidden_vectors_reject_forged_digest(self):
        for relative in (self.vector, self.hidden):
            path = self.snapshot / relative
            original = path.read_bytes()
            path.write_bytes(b"forged")
            self.forge(relative)
            with self.subTest(relative=relative), self.assertRaisesRegex(FixtureSnapshotError, "differs from specs"):
                self.check()
            path.write_bytes(original)
            self.forge(relative)

    def test_dirty_upstream_and_snapshot_with_forged_digest_reject(self):
        for relative in (self.vector, self.hidden):
            source, snapshot = self.specs / relative, self.snapshot / relative
            original = source.read_bytes()
            source.write_bytes(b"forged")
            snapshot.write_bytes(b"forged")
            self.forge(relative)
            with self.subTest(relative=relative), self.assertRaisesRegex(FixtureSnapshotError, "claimed commit"):
                self.check()
            source.write_bytes(original)
            snapshot.write_bytes(original)
            self.forge(relative)

    def test_wrong_provenance_or_hash_rejects(self):
        import copy
        valid = copy.deepcopy(self.metadata)
        for key, value in (("commit", "0" * 40), ("repository", "https://example.invalid/specs"),
                           ("files", {}), ("files", {**valid["files"], self.hidden: "0" * 64})):
            self.metadata = {**valid, key: value}
            self.write_metadata()
            with self.subTest(key=key, value=value), self.assertRaises(FixtureSnapshotError):
                self.check()

    def test_malformed_or_nonobject_manifest_rejects(self):
        for text in ("{", "[]", "null"):
            self.metadata_path.write_text(text)
            with self.subTest(text=text), self.assertRaises(FixtureSnapshotError):
                self.check()

    def test_source_worktree_inventory_drift_rejects(self):
        path = self.specs / self.hidden
        path.unlink()
        with self.assertRaises(FixtureSnapshotError):
            self.check()
        path.write_bytes(b"")
        extra = self.specs / "vectors/.extra"
        extra.write_bytes(b"")
        with self.assertRaises(FixtureSnapshotError):
            self.check()

    def test_nonregular_source_snapshot_and_manifest_reject(self):
        for root in (self.specs, self.snapshot):
            path = root / self.hidden
            path.unlink()
            path.symlink_to(root / self.vector)
            with self.subTest(root=root), self.assertRaises(FixtureSnapshotError):
                self.check()
            path.unlink()
            path.write_bytes(b"")
        data = self.metadata_path.read_bytes()
        other = self.snapshot / "metadata"
        other.write_bytes(data)
        self.metadata_path.unlink()
        self.metadata_path.symlink_to(other)
        with self.assertRaises(FixtureSnapshotError):
            self.check()

    def test_committed_nonregular_vector_rejects(self):
        path = self.specs / self.hidden
        path.unlink()
        path.symlink_to(self.specs / self.vector)
        self.git("add", "vectors")
        self.git("-c", "user.name=Fixture test", "-c", "user.email=test@invalid.example",
                 "commit", "-qm", "Unsupported symlink")
        self.metadata["commit"] = self.git("rev-parse", "HEAD").decode().strip()
        self.write_metadata()
        with self.assertRaisesRegex(FixtureSnapshotError, "nonregular committed"):
            self.check()

    def test_partial_consumer_manifest_is_validated_when_present(self):
        destination = self.org / "companion/tests/fixtures/specs"
        destination.parent.mkdir(parents=True)
        self.snapshot.rename(destination)
        (destination / "SOURCE.json").unlink()
        self.assertEqual(compare_fixture_snapshots(org=self.org, repositories=("companion",), required_snapshot_globs={}), 2)
        (destination / "SOURCE.json").symlink_to(destination / "missing")
        with self.assertRaises(FixtureSnapshotError):
            compare_fixture_snapshots(org=self.org, repositories=("companion",), required_snapshot_globs={})
        (destination / "SOURCE.json").unlink()
        (destination / "SOURCE.json").write_text("{}")
        with self.assertRaises(FixtureSnapshotError):
            compare_fixture_snapshots(org=self.org, repositories=("companion",), required_snapshot_globs={})


if __name__ == "__main__":
    unittest.main()
