import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.integration_hardware_validation import (
    build_hardware_validation_command,
    validate_esp32_qr_secondary_target_alignment,
)


class HardwareIntegrationTests(unittest.TestCase):
    def test_hardware_validation_command_runs_hardware_audit(self) -> None:
        hardware = Path("/workspace/nSealr/hardware")

        command = build_hardware_validation_command(hardware=hardware)

        self.assertEqual(command.cwd, hardware)
        self.assertEqual(command.argv, ["make", "audit"])

    def test_validates_waveshare_secondary_target_alignment(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            board_profile = root / "firmware/boards/waveshare_esp32_s3_touch_lcd_3_5b_c.json"
            requirements = root / "hardware/pcb/reference-esp32-s3-qr-signer/requirements.json"
            board_profile.parent.mkdir(parents=True)
            requirements.parent.mkdir(parents=True)
            board_profile.write_text(
                json.dumps(
                    {
                        "accepted_skus": ["ESP32-S3-Touch-LCD-3.5B-C"],
                        "display": {
                            "driver": "AXS15231B",
                            "connection": "QSPI",
                        },
                        "camera": {"module": "OV5640"},
                    }
                ),
                encoding="utf-8",
            )
            requirements.write_text(
                json.dumps(
                    {
                        "secondary_devkit_candidate": {
                            "sku": "ESP32-S3-Touch-LCD-3.5B-C",
                            "display_driver": "AXS15231B",
                            "display_bus": "QSPI",
                            "camera_module": "OV5640",
                        }
                    }
                ),
                encoding="utf-8",
            )

            validate_esp32_qr_secondary_target_alignment(board_profile, requirements)

    def test_rejects_waveshare_secondary_target_drift(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            board_profile = root / "firmware/boards/waveshare_esp32_s3_touch_lcd_3_5b_c.json"
            requirements = root / "hardware/pcb/reference-esp32-s3-qr-signer/requirements.json"
            board_profile.parent.mkdir(parents=True)
            requirements.parent.mkdir(parents=True)
            board_profile.write_text(
                json.dumps(
                    {
                        "accepted_skus": ["ESP32-S3-Touch-LCD-3.5-C"],
                        "display": {
                            "driver": "ST7796",
                            "connection": "SPI",
                        },
                        "camera": {"module": "OV5640"},
                    }
                ),
                encoding="utf-8",
            )
            requirements.write_text(
                json.dumps(
                    {
                        "secondary_devkit_candidate": {
                            "sku": "ESP32-S3-Touch-LCD-3.5B-C",
                            "display_driver": "AXS15231B",
                            "display_bus": "QSPI",
                            "camera_module": "OV5640",
                        }
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "ESP32 QR secondary target drift"):
                validate_esp32_qr_secondary_target_alignment(board_profile, requirements)


if __name__ == "__main__":
    unittest.main()
