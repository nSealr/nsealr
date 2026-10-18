#!/usr/bin/env python3
"""Shared browser/native-messaging integration helpers."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.integration_support import env_for_command, pinned_command, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from integration_support import env_for_command, pinned_command, run_command


@dataclass(frozen=True)
class CommandPlan:
    cwd: Path
    argv: list[str]


def build_browser_package_plan_command(
    *,
    companion: Path,
    target: str,
    content_script_match: str | None = None,
    firefox_extension_id: str | None = None,
    origin_permission_mode: str | None = None,
    review: bool = False,
) -> CommandPlan:
    argv = [
        "pnpm",
        "--silent",
        "--filter",
        "@nsealr/browser-extension",
        "package-plan",
        "--",
        "--target",
        target,
    ]
    if firefox_extension_id is not None:
        argv.extend(["--firefox-extension-id", firefox_extension_id])
    if content_script_match is not None:
        argv.extend(["--content-script-match", content_script_match])
    if origin_permission_mode is not None:
        argv.extend(["--origin-permission-mode", origin_permission_mode])
    if review:
        argv.append("--review")
    return CommandPlan(cwd=companion, argv=argv)


def build_browser_package_build_command(
    *,
    companion: Path,
    target: str,
    out_dir: Path,
    package_plan_review: Path,
    route_account_id: str,
    route_config_approval: Path,
    route_type: str | None = None,
    content_script_match: str | None = None,
    firefox_extension_id: str | None = None,
    extension_id: str | None = None,
    origin_permission_mode: str | None = None,
    origin_permission_store: Path | None = None,
    local_pairing_digest: str | None = None,
) -> CommandPlan:
    argv = [
        "pnpm",
        "--silent",
        "--filter",
        "@nsealr/browser-extension",
        "package-build",
        "--",
        "--target",
        target,
        "--out-dir",
        str(out_dir),
        "--package-plan-review",
        str(package_plan_review),
        "--route-account-id",
        route_account_id,
        "--route-config-approval",
        str(route_config_approval),
    ]
    if route_type is not None:
        argv.extend(["--route-type", route_type])
    if firefox_extension_id is not None:
        argv.extend(["--firefox-extension-id", firefox_extension_id])
    if content_script_match is not None:
        argv.extend(["--content-script-match", content_script_match])
    if extension_id is not None:
        argv.extend(["--extension-id", extension_id])
    if origin_permission_mode is not None:
        argv.extend(["--origin-permission-mode", origin_permission_mode])
    if origin_permission_store is not None:
        argv.extend(["--origin-permission-store", str(origin_permission_store)])
    if local_pairing_digest is not None:
        argv.extend(["--local-pairing-digest", local_pairing_digest])
    return CommandPlan(cwd=companion, argv=argv)


def build_browser_package_verify_command(
    *,
    companion: Path,
    build_result: Path,
    package_plan_review: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "--silent",
            "--filter",
            "@nsealr/browser-extension",
            "package-verify",
            "--",
            "--build-result",
            str(build_result),
            "--package-plan-review",
            str(package_plan_review),
        ],
    )


def build_browser_route_config_review_command(
    *,
    companion: Path,
    route_account_id: str,
    route_type: str | None = None,
) -> CommandPlan:
    argv = [
        "pnpm",
        "--silent",
        "--filter",
        "@nsealr/browser-extension",
        "route-config-review",
        "--",
        "--route-account-id",
        route_account_id,
    ]
    if route_type is not None:
        argv.extend(["--route-type", route_type])
    return CommandPlan(cwd=companion, argv=argv)


def build_browser_route_config_approval_command(
    *,
    companion: Path,
    review_path: Path,
    route_config_digest: str,
    approved_at: int,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "--silent",
            "--filter",
            "@nsealr/browser-extension",
            "route-config-approve",
            "--",
            "--review",
            str(review_path),
            "--reviewed-route-config-digest",
            route_config_digest,
            "--approved-at",
            str(approved_at),
        ],
    )


def build_browser_origin_permission_approval_command(
    *,
    companion: Path,
    review_path: Path,
    local_pairing_digest: str,
    approved_at: int,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "--silent",
            "--filter",
            "@nsealr/browser-extension",
            "origin-permission-approve",
            "--",
            "--review",
            str(review_path),
            "--reviewed-local-pairing-digest",
            local_pairing_digest,
            "--approved-at",
            str(approved_at),
        ],
    )


def build_browser_origin_permission_store_create_command(
    *,
    companion: Path,
    updated_at: int,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "--silent",
            "--filter",
            "@nsealr/browser-extension",
            "origin-permission-store-create",
            "--",
            "--updated-at",
            str(updated_at),
        ],
    )


def build_browser_origin_permission_store_upsert_command(
    *,
    companion: Path,
    store_path: Path,
    approval_path: Path,
    updated_at: int,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "--silent",
            "--filter",
            "@nsealr/browser-extension",
            "origin-permission-store-upsert",
            "--",
            "--store",
            str(store_path),
            "--approval",
            str(approval_path),
            "--updated-at",
            str(updated_at),
        ],
    )


def build_browser_origin_permission_store_revoke_command(
    *,
    companion: Path,
    store_path: Path,
    origin: str,
    extension_id: str,
    local_pairing_digest: str,
    updated_at: int,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "--silent",
            "--filter",
            "@nsealr/browser-extension",
            "origin-permission-store-revoke",
            "--",
            "--store",
            str(store_path),
            "--origin",
            origin,
            "--extension-id",
            extension_id,
            "--local-pairing-digest",
            local_pairing_digest,
            "--updated-at",
            str(updated_at),
        ],
    )


def build_native_host_manifest_command(
    *,
    companion: Path,
    browser: str,
    host_path: str,
    extension_id: str,
    out_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "--silent",
            "nsealr",
            "local",
            "native-host",
            "manifest",
            "--browser",
            browser,
            "--host-path",
            host_path,
            "--extension-id",
            extension_id,
            "--out",
            str(out_path),
        ],
    )


def build_native_host_install_plan_command(
    *,
    companion: Path,
    browser: str,
    host_path: str,
    manifest_path: str,
    extension_id: str,
    out_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "--silent",
            "nsealr",
            "local",
            "native-host",
            "plan-install",
            "--browser",
            browser,
            "--host-path",
            host_path,
            "--manifest-path",
            manifest_path,
            "--extension-id",
            extension_id,
            "--out",
            str(out_path),
        ],
    )


def build_native_host_install_approval_command(
    *,
    companion: Path,
    plan_path: Path,
    install_digest: str,
    approved_at: int,
    out_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "--silent",
            "nsealr",
            "local",
            "native-host",
            "approve-install",
            "--plan",
            str(plan_path),
            "--reviewed-install-digest",
            install_digest,
            "--approved-at",
            str(approved_at),
            "--out",
            str(out_path),
        ],
    )


def build_native_host_install_execute_command(
    *,
    companion: Path,
    approval_path: Path,
    install_digest: str,
    out_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "--silent",
            "nsealr",
            "local",
            "native-host",
            "execute-install",
            "--approval",
            str(approval_path),
            "--reviewed-install-digest",
            install_digest,
            "--out",
            str(out_path),
        ],
    )


def run_json_command(command: CommandPlan) -> dict[str, Any]:
    result = run_command(command.argv, command.cwd, capture_output=True)
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise AssertionError("integration command must emit one JSON object")
    return payload


def run_json_file_command(command: CommandPlan, output_path: Path) -> dict[str, Any]:
    result = run_command(command.argv, command.cwd, capture_output=True)
    if result.stdout:
        raise AssertionError("artifact command must not emit JSON stdout")
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("integration command must write one JSON object")
    return payload


def run_failure_without_stdout(command: CommandPlan, label: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        pinned_command(command.argv),
        cwd=command.cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env_for_command(command.argv),
    )
    if result.returncode == 0:
        raise AssertionError(f"{label} command unexpectedly succeeded: {command.argv}")
    if result.stdout:
        raise AssertionError(f"{label} command wrote JSON stdout after validation failure")
    return result
