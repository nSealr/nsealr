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
            (org / "firmware" / "tests" / "fixtures" / "specs" / "vectors" / "devices").mkdir(parents=True)
            (org / "specs" / "vectors" / "devices" / "status.json").write_text(
                '{"status":"ok"}\n',
                encoding="utf-8",
            )
            (org / "firmware" / "tests" / "fixtures" / "specs" / "vectors" / "devices" / "status.json").write_text(
                '{"status":"ok"}\n',
                encoding="utf-8",
            )

            compare_fixture_snapshots(org=org, repositories=("firmware",))

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


if __name__ == "__main__":
    unittest.main()
