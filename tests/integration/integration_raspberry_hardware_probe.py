#!/usr/bin/env python3
"""Run the Raspberry SeedSigner-compatible hardware probe integration smoke."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    from tests.integration.integration_support import run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from integration_support import run_command


ROOT = Path(__file__).resolve().parents[2]
RASPBERRY = ROOT / "apps/pi"


@dataclass(frozen=True)
class CommandPlan:
    cwd: Path
    argv: list[str]


def build_hardware_probe_command(*, raspberry: Path, out_path: Path) -> CommandPlan:
    return CommandPlan(
        cwd=raspberry,
        argv=[
            str(raspberry / ".venv/bin/python"),
            "-m",
            "nsealr_vault",
            "hardware-probe",
            "--out",
            str(out_path),
        ],
    )


def assert_safe_probe_report(path: Path) -> None:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != "nsealr-raspberry-seedsigner-compatibility-probe-v0":
        raise AssertionError(f"{path}: unexpected hardware-probe format")
    for flag in ("production_signing_enabled", "persistent_secret_present", "tropic01_used"):
        if report.get(flag) is not False:
            raise AssertionError(f"{path}: {flag} must be false")
    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        raise AssertionError(f"{path}: checks must be a non-empty list")
    for check in checks:
        if not isinstance(check, dict) or check.get("status") not in {"pass", "fail", "blocked"}:
            raise AssertionError(f"{path}: every check must have pass/fail/blocked status")


def main() -> int:
    if not RASPBERRY.exists():
        raise FileNotFoundError(f"missing product component: {RASPBERRY}")

    run_command(["make", "setup"], RASPBERRY)
    with tempfile.TemporaryDirectory(prefix="nsealr-raspberry-probe-") as temp_dir:
        probe_path = Path(temp_dir) / "hardware-probe.json"
        command = build_hardware_probe_command(raspberry=RASPBERRY, out_path=probe_path)
        run_command(command.argv, command.cwd)
        assert_safe_probe_report(probe_path)

    print("nSealr integrated Raspberry hardware-probe smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
