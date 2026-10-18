from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.integration.integration_companion_sdk_browser import (
    build_browser_runtime_imports_command,
    build_sdk_browser_command,
    write_sdk_browser_script,
)


class IntegrationCompanionSdkBrowserTests(unittest.TestCase):
    def test_browser_runtime_imports_command_uses_companion_check(self) -> None:
        command = build_browser_runtime_imports_command(companion=Path("/repos/companion"))

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv, ["pnpm", "browser-runtime-imports:check"])

    def test_sdk_browser_command_runs_generated_script(self) -> None:
        command = build_sdk_browser_command(
            companion=Path("/repos/companion"),
            script_path=Path("/tmp/sdk-browser.mjs"),
        )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv, ["node", str(Path("/tmp/sdk-browser.mjs"))])

    def test_generated_script_checks_qr_and_rejects_node_only_facades(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "sdk-browser.mjs"
            write_sdk_browser_script(path)
            source = path.read_text(encoding="utf-8")

        self.assertIn('import * as sdkBrowser from "@nsealr/sdk/browser";', source)
        self.assertIn("sdkBrowser.qr.encodeQrEnvelope", source)
        self.assertIn("sdkBrowser.qr.decodeQrEnvelope", source)
        self.assertIn('"fixtures", "framing", "nip46", "smartcard", "transport"', source)
        self.assertNotIn("@nsealr/dev-signer", source)


if __name__ == "__main__":
    unittest.main()
