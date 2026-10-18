#!/usr/bin/env python3
"""Verify the companion browser-extension package-plan CLI across repositories."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Any

try:
    from scripts.browser_integration_support import (
        CommandPlan,
        build_browser_package_plan_command,
        run_failure_without_stdout,
        run_json_command,
    )
    from scripts.integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from browser_integration_support import (
        CommandPlan,
        build_browser_package_plan_command,
        run_failure_without_stdout,
        run_json_command,
    )
    from integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[1]
ORG = ROOT.parent
COMPANION = ORG / "companion"
PACKAGE_PLAN_FORMAT = "nsealr-browser-extension-package-plan-v0"
PACKAGE_PLAN_DIGEST_FORMAT = "nsealr-browser-extension-package-plan-digest-v0"
PACKAGE_PLAN_REVIEW_FORMAT = "nsealr-browser-extension-package-plan-review-v0"
CONTENT_SCRIPT_MATCH = "https://example.com/*"
FIREFOX_EXTENSION_ID = "extension@nsealr.dev"
NATIVE_HOST_NAME = "dev.nsealr.companion"


def _sha256_json(payload: dict[str, Any]) -> str:
    return sha256(json.dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()


def package_plan_digest(plan: dict[str, Any]) -> str:
    return _sha256_json({
        "format": PACKAGE_PLAN_DIGEST_FORMAT,
        "plan": plan,
    })


def build_package_plan_command(
    *,
    companion: Path,
    target: str,
    content_script_match: str | None = None,
    firefox_extension_id: str | None = None,
    origin_permission_mode: str | None = None,
    review: bool = False,
) -> CommandPlan:
    return build_browser_package_plan_command(
        companion=companion,
        target=target,
        content_script_match=content_script_match,
        firefox_extension_id=firefox_extension_id,
        origin_permission_mode=origin_permission_mode,
        review=review,
    )


def assert_package_plan(
    plan: dict[str, Any],
    *,
    target: str = "chromium",
    content_script_match: str | None = CONTENT_SCRIPT_MATCH,
    firefox_extension_id: str | None = None,
    origin_permission_mode: str = "embedded",
) -> None:
    if plan.get("format") != PACKAGE_PLAN_FORMAT:
        raise AssertionError("browser package plan format drifted")
    if plan.get("target") != target:
        raise AssertionError("browser package plan target drifted")
    if plan.get("native_host_name") != NATIVE_HOST_NAME:
        raise AssertionError("browser package plan native-host name drifted")
    for field in (
        "installs_native_host_manifest",
        "writes_extension_storage",
        "stores_production_secrets",
        "dispatches_signers",
    ):
        if plan.get(field) is not False:
            raise AssertionError(f"browser package plan must keep {field}=false")
    expected_extension_storage = origin_permission_mode == "extension-storage"
    if plan.get("uses_extension_storage") is not expected_extension_storage:
        raise AssertionError("browser package plan extension-storage profile drifted")
    if plan.get("uses_active_tab_permission") is not expected_extension_storage:
        raise AssertionError("browser package plan activeTab profile drifted")
    expected_popup_mode = (
        "origin_permission_approval"
        if expected_extension_storage
        else "pending_requests"
    )
    if plan.get("popup_mode") != expected_popup_mode:
        raise AssertionError("browser package plan popup mode drifted")

    manifest = plan.get("manifest")
    if not isinstance(manifest, dict):
        raise AssertionError("browser package plan manifest is missing")
    expected_permissions = (
        ["nativeMessaging", "activeTab", "storage"]
        if expected_extension_storage
        else ["nativeMessaging"]
    )
    if manifest.get("permissions") != expected_permissions:
        raise AssertionError("browser package plan permissions drifted")
    for forbidden in ("host_permissions", "optional_host_permissions"):
        if forbidden in manifest:
            raise AssertionError(f"browser package plan must not include {forbidden}")
    if not expected_extension_storage and "storage" in manifest.get("permissions", []):
        raise AssertionError("browser package plan must not include storage permission")
    if target == "chromium":
        if "browser_specific_settings" in manifest:
            raise AssertionError("chromium package plan must not include Firefox settings")
    elif target == "firefox":
        if manifest.get("browser_specific_settings") != {
            "gecko": {
                "id": firefox_extension_id,
            },
        }:
            raise AssertionError("firefox package plan settings drifted")
    else:
        raise AssertionError("browser package plan target is unsupported")
    if manifest.get("background", {}).get("service_worker") != "nsealr-background-entrypoint.js":
        raise AssertionError("browser package plan background entrypoint drifted")
    if manifest.get("action", {}).get("default_popup") != "nsealr-popup.html":
        raise AssertionError("browser package plan popup html drifted")

    if content_script_match is None:
        if "content_scripts" in manifest:
            raise AssertionError("browser package plan must not include content scripts")
        if "web_accessible_resources" in manifest:
            raise AssertionError("browser package plan must not include page-script resources")
    else:
        if manifest.get("content_scripts") != [{
            "matches": [content_script_match],
            "js": ["nsealr-content-script-entrypoint.js"],
            "run_at": "document_start",
            "all_frames": False,
            "match_about_blank": False,
        }]:
            raise AssertionError("browser package plan content-script manifest drifted")
        if manifest.get("web_accessible_resources") != [{
            "resources": ["nsealr-page-script-entrypoint.js"],
            "matches": [content_script_match],
        }]:
            raise AssertionError("browser package plan page-script resource drifted")

    entrypoints = plan.get("entrypoints")
    expected_entrypoints = [
        {
            "role": "background_service_worker",
            "source": "apps/browser-extension/src/nsealr-background-entrypoint.ts",
            "output": "nsealr-background-entrypoint.js",
        },
        {
            "role": "content_script",
            "source": "apps/browser-extension/src/nsealr-content-script-entrypoint.ts",
            "output": "nsealr-content-script-entrypoint.js",
        },
        {
            "role": "page_script",
            "source": "apps/browser-extension/src/nsealr-page-script-entrypoint.ts",
            "output": "nsealr-page-script-entrypoint.js",
        },
        {
            "role": "action_popup",
            "source": "apps/browser-extension/src/nsealr-popup-entrypoint.ts",
            "output": "nsealr-popup-entrypoint.js",
        },
    ]
    if entrypoints != expected_entrypoints:
        raise AssertionError("browser package plan entrypoints drifted")


def assert_package_plan_review(
    review: dict[str, Any],
    *,
    origin_permission_mode: str = "embedded",
) -> None:
    if review.get("format") != PACKAGE_PLAN_REVIEW_FORMAT:
        raise AssertionError("browser package-plan review format drifted")
    reviewed_package_plan_digest = review.get("package_plan_digest")
    if (
        not isinstance(reviewed_package_plan_digest, str) or
        not re.fullmatch(r"[0-9a-f]{64}", reviewed_package_plan_digest)
    ):
        raise AssertionError("browser package-plan review digest drifted")
    if review.get("requires_user_review") is not True:
        raise AssertionError("browser package-plan review must require user review")
    for field in (
        "installs_native_host_manifest",
        "writes_extension_storage",
        "stores_production_secrets",
        "dispatches_signers",
    ):
        if review.get(field) is not False:
            raise AssertionError(f"browser package-plan review must keep {field}=false")
    package_plan = review.get("package_plan")
    if not isinstance(package_plan, dict):
        raise AssertionError("browser package-plan review must include package_plan")
    assert_package_plan(package_plan, origin_permission_mode=origin_permission_mode)
    if package_plan_digest(package_plan) != reviewed_package_plan_digest:
        raise AssertionError("browser package-plan review digest does not match package_plan")


def main() -> int:
    if not COMPANION.exists():
        raise FileNotFoundError(f"missing sibling repository: {COMPANION}")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)
    command = build_package_plan_command(
        companion=COMPANION,
        target="chromium",
        content_script_match=CONTENT_SCRIPT_MATCH,
    )
    assert_package_plan(run_json_command(command))

    review_command = build_package_plan_command(
        companion=COMPANION,
        target="chromium",
        content_script_match=CONTENT_SCRIPT_MATCH,
        review=True,
    )
    assert_package_plan_review(run_json_command(review_command))

    extension_storage_command = build_package_plan_command(
        companion=COMPANION,
        target="chromium",
        content_script_match=CONTENT_SCRIPT_MATCH,
        origin_permission_mode="extension-storage",
    )
    assert_package_plan(
        run_json_command(extension_storage_command),
        origin_permission_mode="extension-storage",
    )
    extension_storage_review = build_package_plan_command(
        companion=COMPANION,
        target="chromium",
        content_script_match=CONTENT_SCRIPT_MATCH,
        origin_permission_mode="extension-storage",
        review=True,
    )
    assert_package_plan_review(
        run_json_command(extension_storage_review),
        origin_permission_mode="extension-storage",
    )

    firefox_command = build_package_plan_command(
        companion=COMPANION,
        target="firefox",
        firefox_extension_id=FIREFOX_EXTENSION_ID,
    )
    assert_package_plan(
        run_json_command(firefox_command),
        target="firefox",
        content_script_match=None,
        firefox_extension_id=FIREFOX_EXTENSION_ID,
    )

    broad_match = build_package_plan_command(
        companion=COMPANION,
        target="chromium",
        content_script_match="<all_urls>",
    )
    broad_match_result = run_failure_without_stdout(broad_match, "browser package-plan")
    if "content script match" not in broad_match_result.stderr:
        raise AssertionError("browser package-plan broad-match rejection message drifted")

    extension_storage_without_origin = build_package_plan_command(
        companion=COMPANION,
        target="chromium",
        origin_permission_mode="extension-storage",
    )
    extension_storage_result = run_failure_without_stdout(extension_storage_without_origin, "browser package-plan")
    if "content-script match" not in extension_storage_result.stderr:
        raise AssertionError("browser package-plan extension-storage rejection message drifted")

    write_attempt = CommandPlan(
        cwd=COMPANION,
        argv=command.argv + ["--write", "package-plan.json"],
    )
    write_result = run_failure_without_stdout(write_attempt, "browser package-plan")
    if "unsupported" not in write_result.stderr:
        raise AssertionError("browser package-plan write-option rejection message drifted")

    print("nSealr cross-repo browser-extension package-plan CLI verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
