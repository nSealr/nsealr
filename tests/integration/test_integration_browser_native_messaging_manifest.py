from __future__ import annotations

import unittest
from pathlib import Path

from scripts.integration_browser_native_messaging_manifest import (
    CHROMIUM_EXTENSION_ID,
    FIREFOX_EXTENSION_ID,
    SERVICE_HOST_PATH,
    build_package_plan_command,
    build_native_host_manifest_command,
)


class IntegrationBrowserNativeMessagingManifestTests(unittest.TestCase):
    def test_browser_package_plan_command_can_bind_firefox_extension_id(self) -> None:
        command = build_package_plan_command(
            companion=Path("/repos/companion"),
            target="firefox",
            extension_id=FIREFOX_EXTENSION_ID,
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
        self.assertIn("firefox", command.argv)
        self.assertIn("--firefox-extension-id", command.argv)
        self.assertIn(FIREFOX_EXTENSION_ID, command.argv)

    def test_native_host_manifest_command_uses_public_companion_cli(self) -> None:
        out_path = Path("/tmp/native-host-manifest.json")
        command = build_native_host_manifest_command(
            companion=Path("/repos/companion"),
            browser="chromium",
            host_path=SERVICE_HOST_PATH,
            extension_id=CHROMIUM_EXTENSION_ID,
            out_path=out_path,
        )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:6], [
            "pnpm",
            "--silent",
            "nsealr",
            "local",
            "native-host",
            "manifest",
        ])
        self.assertIn("--browser", command.argv)
        self.assertIn("chromium", command.argv)
        self.assertIn("--host-path", command.argv)
        self.assertIn(SERVICE_HOST_PATH, command.argv)
        self.assertIn("--extension-id", command.argv)
        self.assertIn(CHROMIUM_EXTENSION_ID, command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(out_path), command.argv)

    def test_native_host_manifest_command_has_no_install_or_write_option(self) -> None:
        command = build_native_host_manifest_command(
            companion=Path("/repos/companion"),
            browser="chromium",
            host_path=SERVICE_HOST_PATH,
            extension_id=CHROMIUM_EXTENSION_ID,
            out_path=Path("/tmp/native-host-manifest.json"),
        )

        self.assertNotIn("--output", command.argv)
        self.assertNotIn("--write", command.argv)
        self.assertNotIn("--install", command.argv)


if __name__ == "__main__":
    unittest.main()
