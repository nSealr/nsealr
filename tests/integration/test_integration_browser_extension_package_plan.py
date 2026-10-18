from __future__ import annotations

import unittest
from pathlib import Path

from tests.integration.integration_browser_extension_package_plan import (
    CONTENT_SCRIPT_MATCH,
    FIREFOX_EXTENSION_ID,
    NATIVE_HOST_NAME,
    PACKAGE_PLAN_FORMAT,
    PACKAGE_PLAN_REVIEW_FORMAT,
    assert_package_plan,
    assert_package_plan_review,
    build_package_plan_command,
    package_plan_digest,
)


class IntegrationBrowserExtensionPackagePlanTests(unittest.TestCase):
    def test_package_plan_command_uses_private_browser_extension_script(self) -> None:
        command = build_package_plan_command(
            companion=Path("/repos/companion"),
            target="chromium",
            content_script_match=CONTENT_SCRIPT_MATCH,
        )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:6], [
            "pnpm",
            "--silent",
            "--filter",
            "@nsealr/browser-extension",
            "package-plan",
            "--",
        ])
        self.assertIn("--target", command.argv)
        self.assertIn("chromium", command.argv)
        self.assertIn("--content-script-match", command.argv)
        self.assertIn(CONTENT_SCRIPT_MATCH, command.argv)

    def test_package_plan_command_has_no_output_or_install_option(self) -> None:
        command = build_package_plan_command(
            companion=Path("/repos/companion"),
            target="chromium",
        )

        self.assertNotIn("--out", command.argv)
        self.assertNotIn("--output", command.argv)
        self.assertNotIn("--write", command.argv)
        self.assertNotIn("--install", command.argv)
        self.assertNotIn("native-host", command.argv)

    def test_package_plan_command_can_request_firefox_id(self) -> None:
        command = build_package_plan_command(
            companion=Path("/repos/companion"),
            target="firefox",
            firefox_extension_id="extension@nsealr.dev",
        )

        self.assertIn("--target", command.argv)
        self.assertIn("firefox", command.argv)
        self.assertIn("--firefox-extension-id", command.argv)
        self.assertIn("extension@nsealr.dev", command.argv)

    def test_package_plan_command_can_request_extension_storage_origin_profile(self) -> None:
        command = build_package_plan_command(
            companion=Path("/repos/companion"),
            target="chromium",
            content_script_match=CONTENT_SCRIPT_MATCH,
            origin_permission_mode="extension-storage",
        )

        self.assertIn("--origin-permission-mode", command.argv)
        self.assertIn("extension-storage", command.argv)

    def test_package_plan_command_can_request_review_envelope(self) -> None:
        command = build_package_plan_command(
            companion=Path("/repos/companion"),
            target="chromium",
            content_script_match=CONTENT_SCRIPT_MATCH,
            review=True,
        )

        self.assertIn("--review", command.argv)

    def test_package_plan_assertion_requires_page_script_resource(self) -> None:
        plan = {
            "format": PACKAGE_PLAN_FORMAT,
            "target": "chromium",
            "popup_mode": "pending_requests",
            "native_host_name": NATIVE_HOST_NAME,
            "installs_native_host_manifest": False,
            "writes_extension_storage": False,
            "uses_extension_storage": False,
            "uses_active_tab_permission": False,
            "stores_production_secrets": False,
            "dispatches_signers": False,
            "manifest": {
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
            },
            "entrypoints": [
                {
                    "role": "background_service_worker",
                    "source": "apps/bridge/browser-extension/src/nsealr-background-entrypoint.ts",
                    "output": "nsealr-background-entrypoint.js",
                },
                {
                    "role": "content_script",
                    "source": "apps/bridge/browser-extension/src/nsealr-content-script-entrypoint.ts",
                    "output": "nsealr-content-script-entrypoint.js",
                },
                {
                    "role": "page_script",
                    "source": "apps/bridge/browser-extension/src/nsealr-page-script-entrypoint.ts",
                    "output": "nsealr-page-script-entrypoint.js",
                },
                {
                    "role": "action_popup",
                    "source": "apps/bridge/browser-extension/src/nsealr-popup-entrypoint.ts",
                    "output": "nsealr-popup-entrypoint.js",
                },
            ],
        }

        assert_package_plan(plan)
        plan["uses_extension_storage"] = True
        with self.assertRaisesRegex(AssertionError, "extension-storage profile"):
            assert_package_plan(plan)
        plan["uses_extension_storage"] = False
        plan["manifest"]["web_accessible_resources"] = []
        with self.assertRaisesRegex(AssertionError, "page-script resource"):
            assert_package_plan(plan)

    def test_package_plan_assertion_allows_extension_storage_profile(self) -> None:
        plan = {
            "format": PACKAGE_PLAN_FORMAT,
            "target": "chromium",
            "popup_mode": "origin_permission_approval",
            "native_host_name": NATIVE_HOST_NAME,
            "installs_native_host_manifest": False,
            "writes_extension_storage": False,
            "uses_extension_storage": True,
            "uses_active_tab_permission": True,
            "stores_production_secrets": False,
            "dispatches_signers": False,
            "manifest": {
                "permissions": ["nativeMessaging", "activeTab", "storage"],
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
            },
            "entrypoints": [
                {
                    "role": "background_service_worker",
                    "source": "apps/bridge/browser-extension/src/nsealr-background-entrypoint.ts",
                    "output": "nsealr-background-entrypoint.js",
                },
                {
                    "role": "content_script",
                    "source": "apps/bridge/browser-extension/src/nsealr-content-script-entrypoint.ts",
                    "output": "nsealr-content-script-entrypoint.js",
                },
                {
                    "role": "page_script",
                    "source": "apps/bridge/browser-extension/src/nsealr-page-script-entrypoint.ts",
                    "output": "nsealr-page-script-entrypoint.js",
                },
                {
                    "role": "action_popup",
                    "source": "apps/bridge/browser-extension/src/nsealr-popup-entrypoint.ts",
                    "output": "nsealr-popup-entrypoint.js",
                },
            ],
        }

        assert_package_plan(plan, origin_permission_mode="extension-storage")
        plan["uses_active_tab_permission"] = False
        with self.assertRaisesRegex(AssertionError, "activeTab profile"):
            assert_package_plan(plan, origin_permission_mode="extension-storage")

    def test_package_plan_review_assertion_checks_digest_and_secretless_flags(self) -> None:
        package_plan = {
            "format": PACKAGE_PLAN_FORMAT,
            "target": "chromium",
            "popup_mode": "pending_requests",
            "native_host_name": NATIVE_HOST_NAME,
            "installs_native_host_manifest": False,
            "writes_extension_storage": False,
            "uses_extension_storage": False,
            "uses_active_tab_permission": False,
            "stores_production_secrets": False,
            "dispatches_signers": False,
            "manifest": {
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
            },
            "entrypoints": [
                {
                    "role": "background_service_worker",
                    "source": "apps/bridge/browser-extension/src/nsealr-background-entrypoint.ts",
                    "output": "nsealr-background-entrypoint.js",
                },
                {
                    "role": "content_script",
                    "source": "apps/bridge/browser-extension/src/nsealr-content-script-entrypoint.ts",
                    "output": "nsealr-content-script-entrypoint.js",
                },
                {
                    "role": "page_script",
                    "source": "apps/bridge/browser-extension/src/nsealr-page-script-entrypoint.ts",
                    "output": "nsealr-page-script-entrypoint.js",
                },
                {
                    "role": "action_popup",
                    "source": "apps/bridge/browser-extension/src/nsealr-popup-entrypoint.ts",
                    "output": "nsealr-popup-entrypoint.js",
                },
            ],
        }
        review = {
            "format": PACKAGE_PLAN_REVIEW_FORMAT,
            "package_plan_digest": package_plan_digest(package_plan),
            "requires_user_review": True,
            "installs_native_host_manifest": False,
            "writes_extension_storage": False,
            "stores_production_secrets": False,
            "dispatches_signers": False,
            "package_plan": package_plan,
        }

        assert_package_plan_review(review)
        review["writes_extension_storage"] = True
        with self.assertRaisesRegex(AssertionError, "writes_extension_storage"):
            assert_package_plan_review(review)

    def test_package_plan_assertion_allows_firefox_without_content_scripts(self) -> None:
        plan = {
            "format": PACKAGE_PLAN_FORMAT,
            "target": "firefox",
            "popup_mode": "pending_requests",
            "native_host_name": NATIVE_HOST_NAME,
            "installs_native_host_manifest": False,
            "writes_extension_storage": False,
            "uses_extension_storage": False,
            "uses_active_tab_permission": False,
            "stores_production_secrets": False,
            "dispatches_signers": False,
            "manifest": {
                "manifest_version": 3,
                "name": "nSealr",
                "description": "nSealr browser bridge for external Nostr signers",
                "version": "0.1.0",
                "permissions": ["nativeMessaging"],
                "background": {
                    "service_worker": "nsealr-background-entrypoint.js",
                    "type": "module",
                },
                "action": {
                    "default_title": "nSealr",
                    "default_popup": "nsealr-popup.html",
                },
                "browser_specific_settings": {
                    "gecko": {
                        "id": FIREFOX_EXTENSION_ID,
                    },
                },
            },
            "entrypoints": [
                {
                    "role": "background_service_worker",
                    "source": "apps/bridge/browser-extension/src/nsealr-background-entrypoint.ts",
                    "output": "nsealr-background-entrypoint.js",
                },
                {
                    "role": "content_script",
                    "source": "apps/bridge/browser-extension/src/nsealr-content-script-entrypoint.ts",
                    "output": "nsealr-content-script-entrypoint.js",
                },
                {
                    "role": "page_script",
                    "source": "apps/bridge/browser-extension/src/nsealr-page-script-entrypoint.ts",
                    "output": "nsealr-page-script-entrypoint.js",
                },
                {
                    "role": "action_popup",
                    "source": "apps/bridge/browser-extension/src/nsealr-popup-entrypoint.ts",
                    "output": "nsealr-popup-entrypoint.js",
                },
            ],
        }

        assert_package_plan(
            plan,
            target="firefox",
            content_script_match=None,
            firefox_extension_id=FIREFOX_EXTENSION_ID,
        )
        plan["manifest"]["browser_specific_settings"]["gecko"]["id"] = "other@nsealr.dev"
        with self.assertRaisesRegex(AssertionError, "firefox package plan settings"):
            assert_package_plan(
                plan,
                target="firefox",
                content_script_match=None,
                firefox_extension_id=FIREFOX_EXTENSION_ID,
            )


if __name__ == "__main__":
    unittest.main()
