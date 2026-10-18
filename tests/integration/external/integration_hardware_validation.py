#!/usr/bin/env python3
"""Run the hardware requirements, BOM, and report validation gate.

The ESP32 `security_profile.json` cross-check was removed in Phase 03 Task 05:
the C++ `esp32_s3_usb_signer` app that owned that profile was retired, and the
Rust `apps/key` device app re-establishes its security posture from scratch in
Phase 05. This gate now runs the hardware `make audit` and validates that the
Waveshare secondary QR-vault board profile stays aligned with the hardware
reference requirements.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HARDWARE = Path(os.environ["NSEALR_HARDWARE_ROOT"]).resolve() if "NSEALR_HARDWARE_ROOT" in os.environ else None
ESP32_WAVESHARE_BOARD_PROFILE = ROOT / "boards/waveshare_esp32_s3_touch_lcd_3_5b_c.json"
HARDWARE_ESP32_QR_REQUIREMENTS = HARDWARE / "pcb/reference-esp32-s3-qr-signer/requirements.json" if HARDWARE else None


@dataclass(frozen=True)
class CommandPlan:
    cwd: Path
    argv: list[str]


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def build_hardware_validation_command(*, hardware: Path) -> CommandPlan:
    return CommandPlan(cwd=hardware, argv=["make", "audit"])


def validate_esp32_qr_secondary_target_alignment(board_profile_path: Path, requirements_path: Path) -> None:
    board_profile = json.loads(board_profile_path.read_text(encoding="utf-8"))
    requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
    target = requirements.get("secondary_devkit_candidate")
    if not isinstance(target, dict):
        raise ValueError(f"{requirements_path}: secondary_devkit_candidate must be an object")

    expected = {
        "sku": target.get("sku"),
        "display_driver": target.get("display_driver"),
        "display_bus": target.get("display_bus"),
        "camera_module": target.get("camera_module"),
    }
    observed = {
        "sku": (board_profile.get("accepted_skus") or [None])[0],
        "display_driver": (board_profile.get("display") or {}).get("driver"),
        "display_bus": (board_profile.get("display") or {}).get("connection"),
        "camera_module": (board_profile.get("camera") or {}).get("module"),
    }
    if observed != expected:
        raise ValueError(
            "ESP32 QR secondary target drift: "
            f"{board_profile_path} has {observed!r}, {requirements_path} requires {expected!r}"
        )


def main() -> int:
    if HARDWARE is None or not HARDWARE.exists():
        raise FileNotFoundError(f"explicit NSEALR_HARDWARE_ROOT is required for external hardware regression: {HARDWARE}")
    if not ESP32_WAVESHARE_BOARD_PROFILE.exists():
        raise FileNotFoundError(f"missing sibling ESP32 Waveshare board profile: {ESP32_WAVESHARE_BOARD_PROFILE}")
    if not HARDWARE_ESP32_QR_REQUIREMENTS.exists():
        raise FileNotFoundError(f"missing sibling ESP32 QR requirements: {HARDWARE_ESP32_QR_REQUIREMENTS}")

    command = build_hardware_validation_command(hardware=HARDWARE)
    run(command.argv, command.cwd)
    validate_esp32_qr_secondary_target_alignment(ESP32_WAVESHARE_BOARD_PROFILE, HARDWARE_ESP32_QR_REQUIREMENTS)
    print("nSealr integrated hardware validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
