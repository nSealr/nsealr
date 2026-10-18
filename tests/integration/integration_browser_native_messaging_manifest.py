#!/usr/bin/env python3
"""Verify browser-extension package plans against native-host manifests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

try:
    from tests.integration.browser_integration_support import (
        CommandPlan,
        build_browser_package_plan_command,
        build_native_host_install_approval_command,
        build_native_host_install_execute_command,
        build_native_host_install_plan_command,
        build_native_host_manifest_command,
        run_failure_without_stdout,
        run_json_command,
        run_json_file_command,
    )
    from tests.integration.integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from browser_integration_support import (
        CommandPlan,
        build_browser_package_plan_command,
        build_native_host_install_approval_command,
        build_native_host_install_execute_command,
        build_native_host_install_plan_command,
        build_native_host_manifest_command,
        run_failure_without_stdout,
        run_json_command,
        run_json_file_command,
    )
    from integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[2]
COMPANION = ROOT
SERVICE_HOST_PATH = "/Applications/nSealr/nsealr-service"
CHROMIUM_NATIVE_MANIFEST_PATH = "/Users/example/Library/Application Support/Google/Chrome/NativeMessagingHosts/dev.nsealr.companion.json"
FIREFOX_NATIVE_MANIFEST_PATH = "/Users/example/Library/Application Support/Mozilla/NativeMessagingHosts/dev.nsealr.companion.json"
CHROMIUM_EXTENSION_ID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
FIREFOX_EXTENSION_ID = "extension@nsealr.dev"
NATIVE_HOST_NAME = "dev.nsealr.companion"


def build_package_plan_command(
    *,
    companion: Path,
    target: str,
    extension_id: str | None = None,
) -> CommandPlan:
    return build_browser_package_plan_command(
        companion=companion,
        target=target,
        firefox_extension_id=extension_id,
    )


def assert_secretless_package_plan(package_plan: dict[str, Any], target: str) -> None:
    if package_plan.get("target") != target:
        raise AssertionError("browser package plan target drifted")
    if package_plan.get("native_host_name") != NATIVE_HOST_NAME:
        raise AssertionError("browser package plan native host name drifted")
    for field in (
        "installs_native_host_manifest",
        "writes_extension_storage",
        "stores_production_secrets",
        "dispatches_signers",
    ):
        if package_plan.get(field) is not False:
            raise AssertionError(f"browser package plan must keep {field}=false")
    manifest = package_plan.get("manifest")
    if not isinstance(manifest, dict):
        raise AssertionError("browser package manifest is missing")
    if manifest.get("permissions") != ["nativeMessaging"]:
        raise AssertionError("browser package permissions drifted")
    if "host_permissions" in manifest or "optional_host_permissions" in manifest:
        raise AssertionError("browser package plan must not request host permissions")


def assert_native_host_manifest(manifest: dict[str, Any], browser: str, extension_id: str) -> None:
    if manifest.get("name") != NATIVE_HOST_NAME:
        raise AssertionError("native host name drifted")
    if manifest.get("path") != SERVICE_HOST_PATH:
        raise AssertionError("native host path drifted")
    if manifest.get("type") != "stdio":
        raise AssertionError("native host type drifted")
    if browser == "chromium":
        if manifest.get("allowed_origins") != [f"chrome-extension://{extension_id}/"]:
            raise AssertionError("chromium native host allowed origin drifted")
        if "allowed_extensions" in manifest:
            raise AssertionError("chromium native host must not use Firefox extension allow-list")
    elif browser == "firefox":
        if manifest.get("allowed_extensions") != [extension_id]:
            raise AssertionError("firefox native host extension allow-list drifted")
        if "allowed_origins" in manifest:
            raise AssertionError("firefox native host must not use Chromium origin allow-list")
    else:
        raise AssertionError(f"unsupported browser in test: {browser}")


def assert_firefox_extension_id_linkage(package_plan: dict[str, Any], native_manifest: dict[str, Any]) -> None:
    package_id = package_plan.get("manifest", {}).get("browser_specific_settings", {}).get("gecko", {}).get("id")
    native_ids = native_manifest.get("allowed_extensions")
    if package_id != FIREFOX_EXTENSION_ID or native_ids != [FIREFOX_EXTENSION_ID]:
        raise AssertionError("Firefox extension id drifted between package plan and native manifest")


def assert_native_host_rejection(command: CommandPlan, label: str, expected_error: str) -> None:
    result = run_failure_without_stdout(command, label)
    if expected_error not in result.stderr:
        raise AssertionError(f"{label} rejection message drifted: {result.stderr!r}")


def assert_native_host_install_plan(
    plan: dict[str, Any],
    browser: str,
    manifest_path: str,
    expected_manifest: dict[str, Any],
) -> None:
    if plan.get("format") != "nsealr-native-host-install-plan-v0":
        raise AssertionError("native-host install plan format drifted")
    install_digest = plan.get("install_digest")
    if not isinstance(install_digest, str) or len(install_digest) != 64:
        raise AssertionError("native-host install plan digest drifted")
    if plan.get("browser") != browser:
        raise AssertionError("native-host install plan browser drifted")
    if plan.get("manifest_path") != manifest_path:
        raise AssertionError("native-host install plan path drifted")
    if plan.get("manifest") != expected_manifest:
        raise AssertionError("native-host install plan manifest drifted")
    for field in ("writes_files", "stores_production_secrets"):
        if plan.get(field) is not False:
            raise AssertionError(f"native-host install plan must keep {field}=false")
    if plan.get("requires_user_approval") is not True:
        raise AssertionError("native-host install plan must require user approval")
    if plan.get("would_create_directories") != [{
        "purpose": "native_host_manifest_parent",
        "path": str(Path(manifest_path).parent),
        "access": "ensure_directory",
        "contains_secret_material": False,
    }]:
        raise AssertionError("native-host install plan directory intent drifted")
    if plan.get("would_write_files") != [{
        "purpose": "native_host_manifest",
        "path": manifest_path,
        "access": "write_new",
        "contains_secret_material": False,
    }]:
        raise AssertionError("native-host install plan write intent drifted")


def assert_native_host_install_approval(approval: dict[str, Any], plan: dict[str, Any]) -> None:
    if approval.get("format") != "nsealr-native-host-install-approval-v0":
        raise AssertionError("native-host install approval format drifted")
    if approval.get("install_digest") != plan.get("install_digest"):
        raise AssertionError("native-host install approval digest drifted")
    if approval.get("plan") != plan:
        raise AssertionError("native-host install approval plan drifted")
    if approval.get("approved_at") != 1900000000:
        raise AssertionError("native-host install approval timestamp drifted")
    if approval.get("requires_user_approval") is not True:
        raise AssertionError("native-host install approval must require user approval")
    for field in ("writes_files", "stores_production_secrets"):
        if approval.get(field) is not False:
            raise AssertionError(f"native-host install approval must keep {field}=false")


def assert_native_host_install_execution(
    execution: dict[str, Any],
    approval: dict[str, Any],
    manifest_path: Path,
) -> None:
    if execution.get("format") != "nsealr-native-host-install-execution-v0":
        raise AssertionError("native-host install execution format drifted")
    if execution.get("install_digest") != approval.get("install_digest"):
        raise AssertionError("native-host install execution digest drifted")
    if execution.get("approved_at") != approval.get("approved_at"):
        raise AssertionError("native-host install execution approval timestamp drifted")
    if execution.get("manifest_path") != str(manifest_path):
        raise AssertionError("native-host install execution path drifted")
    if execution.get("directories_ensured") != approval["plan"].get("would_create_directories"):
        raise AssertionError("native-host install execution directory drifted")
    files_written = execution.get("files_written")
    if not isinstance(files_written, list) or len(files_written) != 1:
        raise AssertionError("native-host install execution file report drifted")
    file_report = files_written[0]
    if file_report.get("purpose") != "native_host_manifest" or file_report.get("path") != str(manifest_path):
        raise AssertionError("native-host install execution file report path drifted")
    if file_report.get("access") != "write_new" or file_report.get("contains_secret_material") is not False:
        raise AssertionError("native-host install execution file report safety drifted")
    if not isinstance(file_report.get("bytes"), int) or file_report["bytes"] <= 0:
        raise AssertionError("native-host install execution byte count drifted")
    sha256 = file_report.get("sha256")
    if not isinstance(sha256, str) or len(sha256) != 64:
        raise AssertionError("native-host install execution sha256 drifted")
    if execution.get("requires_user_approval") is not True:
        raise AssertionError("native-host install execution must require user approval")
    if execution.get("writes_files") is not True:
        raise AssertionError("native-host install execution must report writes_files=true")
    if execution.get("stores_production_secrets") is not False:
        raise AssertionError("native-host install execution must remain secretless")
    written_manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    if written_manifest != approval["plan"].get("manifest"):
        raise AssertionError("native-host install execution wrote unexpected manifest")


def main() -> int:
    if not COMPANION.exists():
        raise FileNotFoundError(f"missing product component: {COMPANION}")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)
    with tempfile.TemporaryDirectory(prefix="nsealr-native-host-install-") as temp_dir:
        temp_root = Path(temp_dir)
        duplicate_manifest_path = "/Users/example/Library/Application Support/Google/Chrome/NativeMessagingHosts/other.json"

        assert_native_host_rejection(
            CommandPlan(
                cwd=COMPANION,
                argv=build_native_host_manifest_command(
                    companion=COMPANION,
                    browser="chromium",
                    host_path=SERVICE_HOST_PATH,
                    extension_id=CHROMIUM_EXTENSION_ID,
                    out_path=temp_root / "duplicate-native-host-manifest.json",
                ).argv + ["--browser", "firefox"],
            ),
            "native-host duplicated manifest option",
            "--browser is duplicated",
        )
        assert_native_host_rejection(
            CommandPlan(
                cwd=COMPANION,
                argv=build_native_host_install_plan_command(
                    companion=COMPANION,
                    browser="chromium",
                    host_path=SERVICE_HOST_PATH,
                    manifest_path=CHROMIUM_NATIVE_MANIFEST_PATH,
                    extension_id=CHROMIUM_EXTENSION_ID,
                    out_path=temp_root / "duplicate-native-host-plan.json",
                ).argv + ["--manifest-path", duplicate_manifest_path],
            ),
            "native-host duplicated install-plan option",
            "--manifest-path is duplicated",
        )

        chromium_plan = run_json_command(build_package_plan_command(
            companion=COMPANION,
            target="chromium",
        ))
        chromium_native_manifest_path = temp_root / "chromium-native-host-manifest.json"
        chromium_native_manifest = run_json_file_command(build_native_host_manifest_command(
            companion=COMPANION,
            browser="chromium",
            host_path=SERVICE_HOST_PATH,
            extension_id=CHROMIUM_EXTENSION_ID,
            out_path=chromium_native_manifest_path,
        ), chromium_native_manifest_path)
        assert_secretless_package_plan(chromium_plan, "chromium")
        assert_native_host_manifest(chromium_native_manifest, "chromium", CHROMIUM_EXTENSION_ID)
        chromium_install_plan_path = temp_root / "chromium-install-plan.json"
        chromium_install_plan = run_json_file_command(build_native_host_install_plan_command(
            companion=COMPANION,
            browser="chromium",
            host_path=SERVICE_HOST_PATH,
            manifest_path=CHROMIUM_NATIVE_MANIFEST_PATH,
            extension_id=CHROMIUM_EXTENSION_ID,
            out_path=chromium_install_plan_path,
        ), chromium_install_plan_path)
        assert_native_host_install_plan(
            chromium_install_plan,
            "chromium",
            CHROMIUM_NATIVE_MANIFEST_PATH,
            chromium_native_manifest,
        )
        chromium_install_approval_path = temp_root / "chromium-install-approval.json"
        chromium_install_approval = run_json_file_command(build_native_host_install_approval_command(
            companion=COMPANION,
            plan_path=chromium_install_plan_path,
            install_digest=chromium_install_plan["install_digest"],
            approved_at=1900000000,
            out_path=chromium_install_approval_path,
        ), chromium_install_approval_path)
        assert_native_host_install_approval(chromium_install_approval, chromium_install_plan)
        chromium_temp_manifest_path = Path(temp_dir) / "NativeMessagingHosts" / "dev.nsealr.companion.json"
        chromium_temp_plan_path = temp_root / "chromium-temp-install-plan.json"
        chromium_temp_install_plan = run_json_file_command(build_native_host_install_plan_command(
            companion=COMPANION,
            browser="chromium",
            host_path=SERVICE_HOST_PATH,
            manifest_path=str(chromium_temp_manifest_path),
            extension_id=CHROMIUM_EXTENSION_ID,
            out_path=chromium_temp_plan_path,
        ), chromium_temp_plan_path)
        assert_native_host_install_plan(
            chromium_temp_install_plan,
            "chromium",
            str(chromium_temp_manifest_path),
            chromium_native_manifest,
        )
        chromium_temp_approval_path = temp_root / "chromium-temp-install-approval.json"
        chromium_temp_approval = run_json_file_command(build_native_host_install_approval_command(
            companion=COMPANION,
            plan_path=chromium_temp_plan_path,
            install_digest=chromium_temp_install_plan["install_digest"],
            approved_at=1900000000,
            out_path=chromium_temp_approval_path,
        ), chromium_temp_approval_path)
        assert_native_host_install_approval(chromium_temp_approval, chromium_temp_install_plan)
        execution_path = temp_root / "chromium-temp-install-execution.json"
        execution = run_json_file_command(build_native_host_install_execute_command(
            companion=COMPANION,
            approval_path=chromium_temp_approval_path,
            install_digest=chromium_temp_approval["install_digest"],
            out_path=execution_path,
        ), execution_path)
        assert_native_host_install_execution(execution, chromium_temp_approval, chromium_temp_manifest_path)
        overwrite_attempt = run_failure_without_stdout(build_native_host_install_execute_command(
            companion=COMPANION,
            approval_path=chromium_temp_approval_path,
            install_digest=chromium_temp_approval["install_digest"],
            out_path=execution_path,
        ), "native-host install execution")
        if "exists" not in overwrite_attempt.stderr and "EEXIST" not in overwrite_attempt.stderr:
            raise AssertionError("native-host install execution overwrite rejection drifted")

        firefox_plan = run_json_command(build_package_plan_command(
            companion=COMPANION,
            target="firefox",
            extension_id=FIREFOX_EXTENSION_ID,
        ))
        firefox_native_manifest_path = temp_root / "firefox-native-host-manifest.json"
        firefox_native_manifest = run_json_file_command(build_native_host_manifest_command(
            companion=COMPANION,
            browser="firefox",
            host_path=SERVICE_HOST_PATH,
            extension_id=FIREFOX_EXTENSION_ID,
            out_path=firefox_native_manifest_path,
        ), firefox_native_manifest_path)
        assert_secretless_package_plan(firefox_plan, "firefox")
        assert_native_host_manifest(firefox_native_manifest, "firefox", FIREFOX_EXTENSION_ID)
        assert_firefox_extension_id_linkage(firefox_plan, firefox_native_manifest)
        firefox_install_plan_path = temp_root / "firefox-install-plan.json"
        firefox_install_plan = run_json_file_command(build_native_host_install_plan_command(
            companion=COMPANION,
            browser="firefox",
            host_path=SERVICE_HOST_PATH,
            manifest_path=FIREFOX_NATIVE_MANIFEST_PATH,
            extension_id=FIREFOX_EXTENSION_ID,
            out_path=firefox_install_plan_path,
        ), firefox_install_plan_path)
        assert_native_host_install_plan(
            firefox_install_plan,
            "firefox",
            FIREFOX_NATIVE_MANIFEST_PATH,
            firefox_native_manifest,
        )

        install_attempt = CommandPlan(
            cwd=COMPANION,
            argv=build_native_host_manifest_command(
                companion=COMPANION,
                browser="chromium",
                host_path=SERVICE_HOST_PATH,
                extension_id=CHROMIUM_EXTENSION_ID,
                out_path=temp_root / "unexpected-install-option.json",
            ).argv + ["--install"],
        )
        install_result = run_failure_without_stdout(install_attempt, "native-messaging")
        if "unknown option" not in install_result.stderr and "unsupported" not in install_result.stderr:
            raise AssertionError("native-host install-option rejection message drifted")

    print("nSealr integrated browser native-messaging manifest verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
