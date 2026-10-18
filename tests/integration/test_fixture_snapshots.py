"""Retained per-feature consumer scopes; source/tamper controls live at the artifact owner."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
REQUIRED_CONTRACT_SCOPES=json.loads((ROOT/'protocols/contracts/v1/consumers.json').read_bytes())

class FixtureScopeTests(unittest.TestCase):
    def test_companion_requires_feature_matrix_snapshots(self) -> None:
        self.assertIn("vectors/features/*.json", REQUIRED_CONTRACT_SCOPES["bridge"])


    def test_companion_requires_route_selection_snapshots(self) -> None:
        self.assertIn("vectors/route-selections/*.json", REQUIRED_CONTRACT_SCOPES["bridge"])


    def test_companion_requires_policy_change_snapshots(self) -> None:
        self.assertIn("vectors/policy-changes/*.json", REQUIRED_CONTRACT_SCOPES["bridge"])
        self.assertIn(
            "schemas/policy-change-review-v0.schema.json",
            REQUIRED_CONTRACT_SCOPES["bridge"],
        )


    def test_companion_requires_access_surface_snapshots(self) -> None:
        self.assertIn("vectors/access-surfaces/*.json", REQUIRED_CONTRACT_SCOPES["bridge"])


    def test_companion_requires_nip46_connection_uri_snapshots(self) -> None:
        self.assertIn("vectors/nip46-connection-uris/*.json", REQUIRED_CONTRACT_SCOPES["bridge"])


    def test_companion_requires_nip46_session_snapshots(self) -> None:
        self.assertIn("vectors/nip46-sessions/*.json", REQUIRED_CONTRACT_SCOPES["bridge"])


    def test_esp32_nip46_invalid_snapshot_scope_excludes_session_lifecycle(self) -> None:
        self.assertIn("vectors/invalid/nip46-sign-event-*.json", REQUIRED_CONTRACT_SCOPES["engine"])
        self.assertNotIn("vectors/invalid/nip46*.json", REQUIRED_CONTRACT_SCOPES["engine"])


    def test_raspberry_requires_seedqr_snapshots(self) -> None:
        self.assertIn("vectors/seedqr/*.json", REQUIRED_CONTRACT_SCOPES["pi"])


    def test_raspberry_requires_nip19_nsec_snapshots(self) -> None:
        self.assertIn("vectors/nip19/*.json", REQUIRED_CONTRACT_SCOPES["pi"])


    def test_raspberry_requires_session_import_review_snapshots(self) -> None:
        self.assertIn("vectors/session-import-reviews/*.json", REQUIRED_CONTRACT_SCOPES["pi"])


    def test_raspberry_requires_session_source_backup_snapshots(self) -> None:
        self.assertIn("vectors/session-source-backups/*.json", REQUIRED_CONTRACT_SCOPES["pi"])


    def test_raspberry_requires_identity_route_snapshots(self) -> None:
        self.assertIn(
            "vectors/accounts/raspberry-qr-nip06-account-0.json",
            REQUIRED_CONTRACT_SCOPES["pi"],
        )
        self.assertIn("vectors/policies/manual-only-qr-vault.json", REQUIRED_CONTRACT_SCOPES["pi"])
        self.assertIn(
            "vectors/route-selections/raspberry-qr-sign-event-account-0.json",
            REQUIRED_CONTRACT_SCOPES["pi"],
        )


    def test_esp32_requires_nip19_nsec_snapshots(self) -> None:
        self.assertIn("vectors/nip19/*.json", REQUIRED_CONTRACT_SCOPES["engine"])


    def test_esp32_requires_seedqr_snapshots(self) -> None:
        self.assertIn("vectors/seedqr/*.json", REQUIRED_CONTRACT_SCOPES["engine"])


    def test_esp32_requires_session_import_review_snapshots(self) -> None:
        self.assertIn("vectors/session-import-reviews/*.json", REQUIRED_CONTRACT_SCOPES["engine"])


    def test_esp32_requires_session_source_backup_snapshots(self) -> None:
        self.assertIn("vectors/session-source-backups/*.json", REQUIRED_CONTRACT_SCOPES["engine"])


    def test_esp32_requires_identity_route_snapshots(self) -> None:
        self.assertIn("vectors/accounts/esp32-qr-nip06-account-0.json", REQUIRED_CONTRACT_SCOPES["engine"])
        self.assertIn("vectors/accounts/esp32-usb-device-slot-0.json", REQUIRED_CONTRACT_SCOPES["engine"])
        self.assertIn("vectors/policies/manual-only-qr-vault.json", REQUIRED_CONTRACT_SCOPES["engine"])
        self.assertIn(
            "vectors/policies/manual-only-persistent-device.json",
            REQUIRED_CONTRACT_SCOPES["engine"],
        )
        self.assertIn("vectors/policies/scoped-automation-daily-use.json", REQUIRED_CONTRACT_SCOPES["engine"])
        self.assertIn(
            "vectors/policy-changes/esp32-usb-enable-kind-1-automation.json",
            REQUIRED_CONTRACT_SCOPES["engine"],
        )
        self.assertIn(
            "vectors/route-selections/esp32-qr-sign-event-account-0.json",
            REQUIRED_CONTRACT_SCOPES["engine"],
        )
        self.assertIn(
            "vectors/route-selections/esp32-usb-sign-event-slot-0.json",
            REQUIRED_CONTRACT_SCOPES["engine"],
        )


    def test_hardware_requires_custom_wallet_route_snapshots(self) -> None:
        self.assertIn(
            "vectors/accounts/custom-hardware-wallet-slot-0.json",
            REQUIRED_CONTRACT_SCOPES["engine"],
        )
        self.assertIn(
            "vectors/grants/custom-hardware-wallet-kind-1-session.json",
            REQUIRED_CONTRACT_SCOPES["engine"],
        )
        self.assertIn(
            "vectors/policies/manual-only-persistent-device.json",
            REQUIRED_CONTRACT_SCOPES["engine"],
        )
        self.assertIn(
            "vectors/policy-changes/custom-hardware-wallet-enable-kind-1-automation.json",
            REQUIRED_CONTRACT_SCOPES["engine"],
        )
        self.assertIn(
            "vectors/policies/scoped-automation-daily-use.json",
            REQUIRED_CONTRACT_SCOPES["engine"],
        )
        self.assertIn(
            "vectors/route-selections/custom-hardware-wallet-sign-event-slot-0.json",
            REQUIRED_CONTRACT_SCOPES["engine"],
        )


if __name__=="__main__":unittest.main()
