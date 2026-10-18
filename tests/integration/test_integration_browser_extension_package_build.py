from __future__ import annotations

import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from scripts.integration_browser_extension_package_build import (
    CONTENT_SCRIPT_MATCH,
    EXPECTED_FILES,
    EXTENSION_ID,
    FIREFOX_EXTENSION_ID,
    LOCAL_PAIRING_DIGEST,
    NATIVE_HOST_NAME,
    PACKAGE_BUILD_FORMAT,
    ROUTE_ACCOUNT_ID,
    ROUTE_TYPE,
    assert_package_build,
)
from scripts.browser_integration_support import build_browser_package_build_command
from scripts.browser_integration_support import build_browser_route_config_approval_command
from scripts.browser_integration_support import build_browser_route_config_review_command


def _sha256_text(source: str) -> str:
    return sha256(source.encode("utf-8")).hexdigest()


def _sha256_json(payload: dict) -> str:
    return sha256(json.dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()


PACKAGE_PLAN_REVIEW = Path("/tmp/package-plan-review.json")
REVIEWED_PACKAGE_PLAN_DIGEST = "a" * 64


class IntegrationBrowserExtensionPackageBuildTests(unittest.TestCase):
    def test_package_build_command_uses_private_browser_extension_script(self) -> None:
        command = build_browser_package_build_command(
            companion=Path("/repos/companion"),
            target="chromium",
            out_dir=Path("/tmp/nsealr-extension"),
            package_plan_review=PACKAGE_PLAN_REVIEW,
            route_account_id=ROUTE_ACCOUNT_ID,
            route_config_approval=Path("/tmp/route-config-approval.json"),
            route_type=ROUTE_TYPE,
            content_script_match=CONTENT_SCRIPT_MATCH,
            extension_id=EXTENSION_ID,
            origin_permission_store=Path("/tmp/origin-permission-store.json"),
            local_pairing_digest=LOCAL_PAIRING_DIGEST,
        )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:6], [
            "pnpm",
            "--silent",
            "--filter",
            "@nsealr/browser-extension",
            "package-build",
            "--",
        ])
        self.assertIn("--target", command.argv)
        self.assertIn("chromium", command.argv)
        self.assertIn("--out-dir", command.argv)
        self.assertIn("/tmp/nsealr-extension", command.argv)
        self.assertIn("--package-plan-review", command.argv)
        self.assertIn(str(PACKAGE_PLAN_REVIEW), command.argv)
        self.assertIn("--route-account-id", command.argv)
        self.assertIn(ROUTE_ACCOUNT_ID, command.argv)
        self.assertIn("--route-config-approval", command.argv)
        self.assertIn("/tmp/route-config-approval.json", command.argv)
        self.assertIn("--route-type", command.argv)
        self.assertIn(ROUTE_TYPE, command.argv)
        self.assertIn("--content-script-match", command.argv)
        self.assertIn(CONTENT_SCRIPT_MATCH, command.argv)
        self.assertIn("--extension-id", command.argv)
        self.assertIn(EXTENSION_ID, command.argv)
        self.assertIn("--origin-permission-store", command.argv)
        self.assertIn("/tmp/origin-permission-store.json", command.argv)
        self.assertIn("--local-pairing-digest", command.argv)
        self.assertIn(LOCAL_PAIRING_DIGEST, command.argv)

    def test_package_build_command_has_no_install_option(self) -> None:
        command = build_browser_package_build_command(
            companion=Path("/repos/companion"),
            target="chromium",
            out_dir=Path("/tmp/nsealr-extension"),
            package_plan_review=PACKAGE_PLAN_REVIEW,
            route_account_id=ROUTE_ACCOUNT_ID,
            route_config_approval=Path("/tmp/route-config-approval.json"),
            route_type=ROUTE_TYPE,
        )

        self.assertNotIn("--install", command.argv)
        self.assertNotIn("--write-storage", command.argv)
        self.assertNotIn("native-host", command.argv)
        self.assertIn("--route-type", command.argv)
        self.assertIn(ROUTE_TYPE, command.argv)

    def test_package_build_command_can_request_firefox_id(self) -> None:
        command = build_browser_package_build_command(
            companion=Path("/repos/companion"),
            target="firefox",
            out_dir=Path("/tmp/nsealr-firefox-extension"),
            package_plan_review=PACKAGE_PLAN_REVIEW,
            route_account_id=ROUTE_ACCOUNT_ID,
            route_config_approval=Path("/tmp/route-config-approval.json"),
            route_type=ROUTE_TYPE,
            firefox_extension_id=FIREFOX_EXTENSION_ID,
        )

        self.assertIn("--target", command.argv)
        self.assertIn("firefox", command.argv)
        self.assertIn("--firefox-extension-id", command.argv)
        self.assertIn(FIREFOX_EXTENSION_ID, command.argv)
        self.assertIn("--route-type", command.argv)
        self.assertIn(ROUTE_TYPE, command.argv)

    def test_route_config_review_and_approval_commands_are_secretless(self) -> None:
        review = build_browser_route_config_review_command(
            companion=Path("/repos/companion"),
            route_account_id=ROUTE_ACCOUNT_ID,
            route_type=ROUTE_TYPE,
        )
        self.assertEqual(review.cwd, Path("/repos/companion"))
        self.assertEqual(review.argv[:6], [
            "pnpm",
            "--silent",
            "--filter",
            "@nsealr/browser-extension",
            "route-config-review",
            "--",
        ])
        self.assertIn("--route-account-id", review.argv)
        self.assertIn(ROUTE_ACCOUNT_ID, review.argv)
        self.assertIn("--route-type", review.argv)
        self.assertIn(ROUTE_TYPE, review.argv)
        self.assertNotIn("--out", review.argv)
        self.assertNotIn("--write-storage", review.argv)

        approval = build_browser_route_config_approval_command(
            companion=Path("/repos/companion"),
            review_path=Path("/tmp/route-review.json"),
            route_config_digest="0" * 64,
            approved_at=1_900_000_000,
        )
        self.assertEqual(approval.cwd, Path("/repos/companion"))
        self.assertEqual(approval.argv[:6], [
            "pnpm",
            "--silent",
            "--filter",
            "@nsealr/browser-extension",
            "route-config-approve",
            "--",
        ])
        self.assertIn("--review", approval.argv)
        self.assertIn("/tmp/route-review.json", approval.argv)
        self.assertIn("--reviewed-route-config-digest", approval.argv)
        self.assertIn("0" * 64, approval.argv)
        self.assertIn("--approved-at", approval.argv)
        self.assertIn("1900000000", approval.argv)
        self.assertNotIn("--write-storage", approval.argv)

    def test_package_build_assertion_requires_secretless_artifact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-package-build-test-") as root:
            out_dir = Path(root) / "extension"
            out_dir.mkdir()
            manifest = {
                "permissions": ["nativeMessaging"],
                "background": {
                    "service_worker": "nsealr-background-entrypoint.js",
                },
                "action": {
                    "default_popup": "nsealr-popup.html",
                },
                "content_scripts": [{
                    "matches": [CONTENT_SCRIPT_MATCH],
                    "js": ["nsealr-content-script-entrypoint.js"],
                    "run_at": "document_start",
                    "all_frames": False,
                    "match_about_blank": False,
                }],
                "web_accessible_resources": [{
                    "resources": ["nsealr-page-script-entrypoint.js"],
                    "matches": [CONTENT_SCRIPT_MATCH],
                }],
            }
            (out_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            for name in EXPECTED_FILES[1:]:
                if name == "nsealr-popup.html":
                    (out_dir / name).write_text(
                        '<main id="nsealr-popup-root"></main><script src="nsealr-popup-entrypoint.js"></script>\n',
                        encoding="utf-8",
                    )
                else:
                    (out_dir / name).write_text(
                        f"/* {ROUTE_ACCOUNT_ID} {LOCAL_PAIRING_DIGEST} {EXTENSION_ID} {NATIVE_HOST_NAME} */\n",
                        encoding="utf-8",
                    )
            files = []
            for name in EXPECTED_FILES:
                source = (out_dir / name).read_text(encoding="utf-8")
                files.append({
                    "path": name,
                    "bytes": len(source.encode("utf-8")),
                    "sha256": _sha256_text(source),
                })

            result = {
                "format": PACKAGE_BUILD_FORMAT,
                "target": "chromium",
                "out_dir": str(out_dir),
                "package_plan_digest": REVIEWED_PACKAGE_PLAN_DIGEST,
                "route_config_digest": "b" * 64,
                "route_account_id": ROUTE_ACCOUNT_ID,
                "route_type": ROUTE_TYPE,
                "native_host_name": NATIVE_HOST_NAME,
                "popup_mode": "pending_requests",
                "manifest_permissions": ["nativeMessaging"],
                "origin_permission_mode": "embedded",
                "extension_id": EXTENSION_ID,
                "local_pairing_digest": LOCAL_PAIRING_DIGEST,
                "content_script_origins": ["https://example.com"],
                "package_digest": _sha256_json({
                    "format": "nsealr-browser-extension-package-digest-v0",
                    "target": "chromium",
                    "files": files,
                }),
                "files": files,
                "installs_native_host_manifest": False,
                "writes_extension_storage": False,
                "stores_production_secrets": False,
                "dispatches_signers": False,
                "uses_active_tab_permission": False,
                "embeds_origin_permission_store": True,
                "uses_extension_origin_permission_storage": False,
            }

            assert_package_build(result, out_dir)
            manifest["permissions"] = ["nativeMessaging", "activeTab", "storage"]
            (out_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (out_dir / "nsealr-background-entrypoint.js").write_text(
                f"/* {ROUTE_ACCOUNT_ID} {LOCAL_PAIRING_DIGEST} {NATIVE_HOST_NAME} */\n",
                encoding="utf-8",
            )
            (out_dir / "nsealr-popup-entrypoint.js").write_text(
                f"/* {ROUTE_ACCOUNT_ID} {LOCAL_PAIRING_DIGEST} */\n",
                encoding="utf-8",
            )
            files = []
            for name in EXPECTED_FILES:
                source = (out_dir / name).read_text(encoding="utf-8")
                files.append({
                    "path": name,
                    "bytes": len(source.encode("utf-8")),
                    "sha256": _sha256_text(source),
                })
            result["files"] = files
            result["package_digest"] = _sha256_json({
                "format": "nsealr-browser-extension-package-digest-v0",
                "target": "chromium",
                "files": files,
            })
            result["popup_mode"] = "origin_permission_approval"
            result["manifest_permissions"] = ["nativeMessaging", "activeTab", "storage"]
            result["origin_permission_mode"] = "extension_storage"
            del result["extension_id"]
            result["uses_active_tab_permission"] = True
            result["embeds_origin_permission_store"] = False
            result["uses_extension_origin_permission_storage"] = True
            self.assertIsNone(assert_package_build(result, out_dir, origin_permission_mode="extension-storage"))
            result["uses_extension_origin_permission_storage"] = False
            with self.assertRaisesRegex(AssertionError, "extension-storage"):
                assert_package_build(result, out_dir, origin_permission_mode="extension-storage")
            result["popup_mode"] = "pending_requests"
            result["manifest_permissions"] = ["nativeMessaging"]
            result["origin_permission_mode"] = "embedded"
            result["extension_id"] = EXTENSION_ID
            result["uses_active_tab_permission"] = False
            result["embeds_origin_permission_store"] = True
            result["uses_extension_origin_permission_storage"] = False
            result["writes_extension_storage"] = True
            with self.assertRaisesRegex(AssertionError, "writes_extension_storage"):
                assert_package_build(result, out_dir)

    def test_package_build_assertion_allows_firefox_without_content_script(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-firefox-package-build-test-") as root:
            out_dir = Path(root) / "firefox-extension"
            out_dir.mkdir()
            manifest = {
                "permissions": ["nativeMessaging"],
                "background": {
                    "service_worker": "nsealr-background-entrypoint.js",
                },
                "action": {
                    "default_popup": "nsealr-popup.html",
                },
                "browser_specific_settings": {
                    "gecko": {
                        "id": FIREFOX_EXTENSION_ID,
                    },
                },
            }
            (out_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            for name in EXPECTED_FILES[1:]:
                if name == "nsealr-popup.html":
                    (out_dir / name).write_text(
                        '<main id="nsealr-popup-root"></main><script src="nsealr-popup-entrypoint.js"></script>\n',
                        encoding="utf-8",
                    )
                else:
                    (out_dir / name).write_text(f"/* {ROUTE_ACCOUNT_ID} {NATIVE_HOST_NAME} */\n", encoding="utf-8")
            files = []
            for name in EXPECTED_FILES:
                source = (out_dir / name).read_text(encoding="utf-8")
                files.append({
                    "path": name,
                    "bytes": len(source.encode("utf-8")),
                    "sha256": _sha256_text(source),
                })

            result = {
                "format": PACKAGE_BUILD_FORMAT,
                "target": "firefox",
                "out_dir": str(out_dir),
                "package_plan_digest": REVIEWED_PACKAGE_PLAN_DIGEST,
                "route_config_digest": "c" * 64,
                "route_account_id": ROUTE_ACCOUNT_ID,
                "route_type": ROUTE_TYPE,
                "native_host_name": NATIVE_HOST_NAME,
                "popup_mode": "pending_requests",
                "manifest_permissions": ["nativeMessaging"],
                "origin_permission_mode": "none",
                "content_script_origins": [],
                "package_digest": _sha256_json({
                    "format": "nsealr-browser-extension-package-digest-v0",
                    "target": "firefox",
                    "files": files,
                }),
                "files": files,
                "installs_native_host_manifest": False,
                "writes_extension_storage": False,
                "stores_production_secrets": False,
                "dispatches_signers": False,
                "uses_active_tab_permission": False,
                "embeds_origin_permission_store": False,
                "uses_extension_origin_permission_storage": False,
            }

            self.assertIsNone(assert_package_build(
                result,
                out_dir,
                target="firefox",
                origin_permission_mode="none",
            ))


if __name__ == "__main__":
    unittest.main()
