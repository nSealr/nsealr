from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import browser_extension_chromium_smoke as smoke


class BrowserExtensionChromiumSmokeTests(unittest.TestCase):
    def test_local_content_script_match_validates_port(self) -> None:
        self.assertEqual(
            smoke.local_content_script_match(49152),
            "http://127.0.0.1:49152/*",
        )
        with self.assertRaisesRegex(ValueError, "port is invalid"):
            smoke.local_content_script_match(0)
        with self.assertRaisesRegex(ValueError, "port is invalid"):
            smoke.local_content_script_match(70000)

    def test_probe_page_checks_nip07_provider_shape(self) -> None:
        html = smoke.probe_page_html()
        self.assertIn("window.nostr", html)
        self.assertIn("getPublicKey", html)
        self.assertIn("signEvent", html)
        self.assertIn(smoke.PROVIDER_INJECTED_TITLE, html)
        self.assertIn(smoke.PROVIDER_DENIED_TITLE, html)
        self.assertIn("origin permission denied", html)

    def test_resolve_chromium_browser_accepts_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            browser = Path(temp_root) / "chromium"
            browser.write_text("#!/bin/sh\n", encoding="utf-8")
            browser.chmod(browser.stat().st_mode | stat.S_IXUSR)
            self.assertEqual(smoke.resolve_chromium_browser(str(browser)), browser)

    def test_resolve_chromium_browser_rejects_non_executable_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            old_value = os.environ.get("NSEALR_CHROMIUM_BROWSER")
            env_browser = Path(temp_root) / "env-chromium"
            env_browser.write_text("#!/bin/sh\n", encoding="utf-8")
            env_browser.chmod(env_browser.stat().st_mode | stat.S_IXUSR)
            os.environ["NSEALR_CHROMIUM_BROWSER"] = str(env_browser)
            try:
                browser = Path(temp_root) / "chromium"
                browser.write_text("#!/bin/sh\n", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "not executable"):
                    smoke.resolve_chromium_browser(str(browser))
            finally:
                if old_value is None:
                    os.environ.pop("NSEALR_CHROMIUM_BROWSER", None)
                else:
                    os.environ["NSEALR_CHROMIUM_BROWSER"] = old_value

    def test_resolve_chromium_browser_uses_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            browser = Path(temp_root) / "chromium"
            browser.write_text("#!/bin/sh\n", encoding="utf-8")
            browser.chmod(browser.stat().st_mode | stat.S_IXUSR)
            old_value = os.environ.get("NSEALR_CHROMIUM_BROWSER")
            os.environ["NSEALR_CHROMIUM_BROWSER"] = str(browser)
            try:
                self.assertEqual(smoke.resolve_chromium_browser(), browser)
            finally:
                if old_value is None:
                    os.environ.pop("NSEALR_CHROMIUM_BROWSER", None)
                else:
                    os.environ["NSEALR_CHROMIUM_BROWSER"] = old_value

    def test_write_json_new_writes_report_and_refuses_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            output = Path(temp_root) / "reports" / "chromium-smoke.json"
            smoke.write_json_new(output, {
                "format": smoke.SMOKE_FORMAT,
                "stores_production_secrets": False,
                "dispatches_signers": False,
            })

            self.assertIn(smoke.SMOKE_FORMAT, output.read_text(encoding="utf-8"))
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                smoke.require_new_json_output_path(output)
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                smoke.write_json_new(output, {"format": smoke.SMOKE_FORMAT})

    def test_build_extension_package_runs_package_verifier_before_browser_load(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            temp = Path(temp_root)
            package_result = {
                "format": "nsealr-browser-extension-package-build-v0",
                "out_dir": str(temp / "extension"),
                "stores_production_secrets": False,
                "dispatches_signers": False,
            }
            with (
                patch.object(smoke, "install_pnpm_workspace") as install_workspace,
                patch.object(smoke, "build_pnpm_workspace") as build_workspace,
                patch.object(smoke, "run_json_command", side_effect=[
                    {
                        "format": "nsealr-browser-extension-package-plan-review-v0",
                        "package_plan_digest": "a" * 64,
                        "package_plan": {
                            "format": "nsealr-browser-extension-package-plan-v0",
                            "target": "chromium",
                        },
                    },
                    {"route_config_digest": "b" * 64},
                    {"route_config_digest": "b" * 64},
                    package_result,
                    package_result,
                ]) as run_json,
            ):
                result = smoke.build_extension_package(temp, "http://127.0.0.1:49152/*")

            self.assertEqual(result, package_result)
            install_workspace.assert_called_once_with(smoke.COMPANION)
            build_workspace.assert_called_once_with(smoke.COMPANION)
            self.assertEqual(run_json.call_count, 5)
            build_command = run_json.call_args_list[-2].args[0]
            self.assertIn("package-build", build_command.argv)
            self.assertIn("--package-plan-review", build_command.argv)
            self.assertNotIn("--package-plan-digest", build_command.argv)
            verifier_command = run_json.call_args_list[-1].args[0]
            self.assertIn("package-verify", verifier_command.argv)
            self.assertIn("--package-plan-review", verifier_command.argv)
            build_result_path = temp / "package-build-result.json"
            package_plan_review_path = temp / "package-plan-review.json"
            self.assertEqual(json.loads(build_result_path.read_text(encoding="utf-8")), package_result)
            self.assertEqual(
                json.loads(package_plan_review_path.read_text(encoding="utf-8")),
                {
                    "format": "nsealr-browser-extension-package-plan-review-v0",
                    "package_plan_digest": "a" * 64,
                    "package_plan": {
                        "format": "nsealr-browser-extension-package-plan-v0",
                        "target": "chromium",
                    },
                },
            )


if __name__ == "__main__":
    unittest.main()
