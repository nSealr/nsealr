#!/usr/bin/env python3
"""Verify file-backed companion service context stays storage-approval gated."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

try:
    from tests.integration.integration_support import build_pnpm_workspace, env_for_command, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from integration_support import build_pnpm_workspace, env_for_command, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[2]
COMPANION = ROOT
SPECS = ROOT / "protocols/contracts/v1"


def service_command(*args: str) -> list[str]:
    return [
        "pnpm",
        "--silent",
        "--filter",
        "@nsealr/service",
        "service",
        "--",
        *args,
    ]


def companion_command(*args: str) -> list[str]:
    return ["pnpm", "nsealr", *args]


def run_service_failure(*args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        service_command(*args),
        cwd=COMPANION,
        check=False,
        capture_output=True,
        input="",
        text=True,
    )
    if result.returncode == 0:
        raise AssertionError("service context command unexpectedly succeeded")
    if result.stdout:
        raise AssertionError("service context command wrote stdout after validation failure")
    return result


def run_companion_failure(*args: str) -> subprocess.CompletedProcess[str]:
    command = companion_command(*args)
    result = subprocess.run(
        command,
        cwd=COMPANION,
        check=False,
        capture_output=True,
        input="",
        text=True,
        env=env_for_command(command),
    )
    if result.returncode == 0:
        raise AssertionError("companion CLI command unexpectedly succeeded")
    return result


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf8"))


def service_account_store(*, account: object) -> dict[str, object]:
    return {
        "format": "nsealr-service-account-store-v0",
        "updated_at": 1900000000,
        "accounts": [account],
        "contains_secret_material": False,
    }


def service_route_driver_store(*, serial_line: dict[str, object]) -> dict[str, object]:
    return {
        "format": "nsealr-service-route-driver-store-v0",
        "updated_at": 1900000000,
        "contains_secret_material": False,
        "routes": [{
            "account_id": "acct-esp32-usb-slot-0",
            "route_type": "esp32_usb_nip46",
            "transport": "usb",
            "driver": "serial_line",
            "serial_line": {
                "path": "/dev/cu.usbmodem-test",
                **serial_line,
            },
        }],
    }


def approve_route_driver_storage(
    *,
    account_store: Path,
    route_driver_store: Path,
    review_path: Path,
    approval_path: Path,
    approved_at: int,
) -> None:
    run_command([
        "pnpm",
        "nsealr",
        "local",
        "review-storage",
        "--account-store",
        str(account_store),
        "--route-driver-store",
        str(route_driver_store),
        "--out",
        str(review_path),
    ], COMPANION)
    review = read_json(review_path)
    if not isinstance(review, dict) or not isinstance(review.get("storage_digest"), str):
        raise AssertionError("storage review did not include a digest")
    run_command([
        "pnpm",
        "nsealr",
        "local",
        "approve-storage",
        "--review",
        str(review_path),
        "--reviewed-storage-digest",
        review["storage_digest"],
        "--approved-at",
        str(approved_at),
        "--out",
        str(approval_path),
    ], COMPANION)


def main() -> int:
    for repo in (COMPANION, SPECS):
        if not repo.exists():
            raise FileNotFoundError(f"missing product component: {repo}")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)

    with tempfile.TemporaryDirectory(prefix="nsealr-service-context-") as temp_dir:
        temp = Path(temp_dir)
        grant_store = temp / "local-grants.json"
        account_store = temp / "accounts.json"
        oversized_ignored_lines_driver_store = temp / "oversized-ignored-lines-drivers.json"
        oversized_timeout_driver_store = temp / "oversized-timeout-drivers.json"
        review_path = temp / "storage-review.json"
        approval_path = temp / "storage-approval.json"
        driver_review_path = temp / "route-driver-storage-review.json"
        driver_approval_path = temp / "route-driver-storage-approval.json"
        grant_store.write_text(json.dumps({
            "format": "nsealr-local-grant-store-v0",
            "updated_at": 1900000000,
            "grants": [],
            "contains_secret_material": False,
        }, indent=2) + "\n", encoding="utf8")
        esp32_account = read_json(SPECS / "vectors/accounts/esp32-usb-device-slot-0.json")
        account_store.write_text(json.dumps(service_account_store(account=esp32_account), indent=2) + "\n", encoding="utf8")
        oversized_ignored_lines_driver_store.write_text(json.dumps(service_route_driver_store(
            serial_line={"max_ignored_lines": 129}
        ), indent=2) + "\n", encoding="utf8")
        oversized_timeout_driver_store.write_text(json.dumps(service_route_driver_store(
            serial_line={"response_timeout_ms": 120001}
        ), indent=2) + "\n", encoding="utf8")

        duplicate_review_cases = [
            ("--grant-store", grant_store, temp / "duplicate-grants.json"),
            ("--grant-store-output", temp / "grants-next.json", temp / "grants-other.json"),
            ("--account-store", account_store, temp / "duplicate-accounts.json"),
            ("--route-driver-store", oversized_ignored_lines_driver_store, oversized_timeout_driver_store),
        ]
        for option, first_path, second_path in duplicate_review_cases:
            duplicate_review_path = temp / f"duplicate-{option.removeprefix('--')}-review.json"
            duplicate = run_companion_failure(
                "local",
                "review-storage",
                option,
                str(first_path),
                option,
                str(second_path),
                "--out",
                str(duplicate_review_path),
            )
            if f"{option} is duplicated" not in duplicate.stderr:
                raise AssertionError(f"review-storage duplicate {option} error drifted")
            for unexpected in ("at Option.parseArg", "apps/bridge/cli/src/index.ts", "DEP0205"):
                if unexpected in duplicate.stderr:
                    raise AssertionError(f"review-storage duplicate {option} leaked CLI diagnostic noise")
            if duplicate_review_path.exists():
                raise AssertionError(f"review-storage duplicate {option} wrote review output")

        missing = run_service_failure("--grant-store", str(grant_store))
        if "storage-approval" not in missing.stderr:
            raise AssertionError("service context missing-approval error drifted")

        run_command([
            "pnpm",
            "nsealr",
            "local",
            "review-storage",
            "--grant-store",
            str(grant_store),
            "--out",
            str(review_path),
        ], COMPANION)
        review = json.loads(review_path.read_text(encoding="utf8"))
        run_command([
            "pnpm",
            "nsealr",
            "local",
            "approve-storage",
            "--review",
            str(review_path),
            "--reviewed-storage-digest",
            review["storage_digest"],
            "--approved-at",
            "1900000001",
            "--out",
            str(approval_path),
        ], COMPANION)

        success = run_command(
            service_command(
                "--grant-store",
                str(grant_store),
                "--storage-approval",
                str(approval_path),
            ),
            COMPANION,
            capture_output=True,
            input="",
        )
        if success.stdout or success.stderr:
            raise AssertionError("storage-approved service context smoke should be quiet without stdin")

        wrong_approval = run_service_failure(
            "--account-store",
            str(temp / "missing-accounts.json"),
            "--storage-approval",
            str(approval_path),
        )
        if "does not cover" not in wrong_approval.stderr:
            raise AssertionError("service context wrong-approval error drifted")

        approve_route_driver_storage(
            account_store=account_store,
            route_driver_store=oversized_ignored_lines_driver_store,
            review_path=driver_review_path,
            approval_path=driver_approval_path,
            approved_at=1900000001,
        )
        oversized_ignored_lines = run_service_failure(
            "--account-store",
            str(account_store),
            "--route-driver-store",
            str(oversized_ignored_lines_driver_store),
            "--storage-approval",
            str(driver_approval_path),
        )
        if "max_ignored_lines exceeds max" not in oversized_ignored_lines.stderr:
            raise AssertionError("service context oversized max_ignored_lines error drifted")

        approve_route_driver_storage(
            account_store=account_store,
            route_driver_store=oversized_timeout_driver_store,
            review_path=driver_review_path,
            approval_path=driver_approval_path,
            approved_at=1900000002,
        )
        oversized_timeout = run_service_failure(
            "--account-store",
            str(account_store),
            "--route-driver-store",
            str(oversized_timeout_driver_store),
            "--storage-approval",
            str(driver_approval_path),
        )
        if "response_timeout_ms exceeds max" not in oversized_timeout.stderr:
            raise AssertionError("service context oversized response_timeout_ms error drifted")

    print("nSealr companion service context storage-approval integration passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
