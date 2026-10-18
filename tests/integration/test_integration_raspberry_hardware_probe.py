from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.integration_raspberry_hardware_probe import (
    assert_safe_probe_report,
    build_hardware_probe_command,
)


class RaspberryHardwareProbeIntegrationTests(unittest.TestCase):
    def test_hardware_probe_command_uses_raspberry_cli(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-raspberry-probe-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_hardware_probe_command(
                raspberry=Path("/repos/raspberry"),
                out_path=temp / "hardware-probe.json",
            )

        self.assertEqual(command.cwd, Path("/repos/raspberry"))
        self.assertEqual(command.argv[:3], ["/repos/raspberry/.venv/bin/python", "-m", "nsealr_vault"])
        self.assertIn("hardware-probe", command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(temp / "hardware-probe.json"), command.argv)

    def test_safe_probe_report_rejects_production_claims(self) -> None:
        report = {
            "format": "nsealr-raspberry-seedsigner-compatibility-probe-v0",
            "ready_for_hardware_acceptance": False,
            "production_signing_enabled": True,
            "persistent_secret_present": False,
            "tropic01_used": False,
            "checks": [],
        }

        with tempfile.TemporaryDirectory(prefix="nsealr-raspberry-probe-report-") as temp_dir:
            path = Path(temp_dir) / "hardware-probe.json"
            path.write_text(json.dumps(report), encoding="utf-8")

            with self.assertRaisesRegex(AssertionError, "production_signing_enabled"):
                assert_safe_probe_report(path)

    def test_safe_probe_report_accepts_blocked_development_probe(self) -> None:
        report = {
            "format": "nsealr-raspberry-seedsigner-compatibility-probe-v0",
            "ready_for_hardware_acceptance": False,
            "production_signing_enabled": False,
            "persistent_secret_present": False,
            "tropic01_used": False,
            "checks": [{"id": "board_model", "status": "blocked"}],
        }

        with tempfile.TemporaryDirectory(prefix="nsealr-raspberry-probe-report-") as temp_dir:
            path = Path(temp_dir) / "hardware-probe.json"
            path.write_text(json.dumps(report), encoding="utf-8")

            assert_safe_probe_report(path)


if __name__ == "__main__":
    unittest.main()
