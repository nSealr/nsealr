#!/usr/bin/env python3
"""Verify the companion browser-extension package-build CLI across repositories."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any

try:
    from scripts.browser_integration_support import (
        build_browser_origin_permission_approval_command,
        build_browser_origin_permission_store_create_command,
        build_browser_origin_permission_store_upsert_command,
        build_browser_package_plan_command,
        build_browser_package_build_command,
        build_browser_package_verify_command,
        build_browser_route_config_approval_command,
        build_browser_route_config_review_command,
        run_failure_without_stdout,
        run_json_command,
    )
    from scripts.integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from browser_integration_support import (
        build_browser_origin_permission_approval_command,
        build_browser_origin_permission_store_create_command,
        build_browser_origin_permission_store_upsert_command,
        build_browser_package_plan_command,
        build_browser_package_build_command,
        build_browser_package_verify_command,
        build_browser_route_config_approval_command,
        build_browser_route_config_review_command,
        run_failure_without_stdout,
        run_json_command,
    )
    from integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[1]
ORG = ROOT.parent
COMPANION = ORG / "companion"
PACKAGE_BUILD_FORMAT = "nsealr-browser-extension-package-build-v0"
PACKAGE_DIGEST_FORMAT = "nsealr-browser-extension-package-digest-v0"
PACKAGE_PLAN_FORMAT = "nsealr-browser-extension-package-plan-v0"
PACKAGE_PLAN_DIGEST_FORMAT = "nsealr-browser-extension-package-plan-digest-v0"
PACKAGE_PLAN_REVIEW_FORMAT = "nsealr-browser-extension-package-plan-review-v0"
ROUTE_CONFIG_REVIEW_FORMAT = "nsealr-browser-extension-route-config-review-v0"
ROUTE_CONFIG_APPROVAL_FORMAT = "nsealr-browser-extension-route-config-approval-v0"
ORIGIN_PERMISSION_STORE_FORMAT = "nsealr-browser-origin-permission-store-v0"
ORIGIN_PERMISSION_APPROVAL_FORMAT = "nsealr-browser-origin-permission-approval-v0"
CONTENT_SCRIPT_MATCH = "https://example.com/*"
CONTENT_SCRIPT_ORIGIN = "https://example.com"
EXTENSION_ID = "abcdefghijklmnopabcdefghijklmnop"
FIREFOX_EXTENSION_ID = "extension@nsealr.dev"
LOCAL_PAIRING_DIGEST = "a" * 64
ROUTE_ACCOUNT_ID = "esp32-usb-slot-0"
ROUTE_TYPE = "esp32_usb_nip46"
NATIVE_HOST_NAME = "dev.nsealr.companion"
EXPECTED_FILES = [
    "manifest.json",
    "nsealr-popup.html",
    "nsealr-background-entrypoint.js",
    "nsealr-content-script-entrypoint.js",
    "nsealr-page-script-entrypoint.js",
    "nsealr-popup-entrypoint.js",
]


def _sha256_text(source: str) -> str:
    return sha256(source.encode("utf-8")).hexdigest()


def _sha256_json(payload: dict[str, Any]) -> str:
    return sha256(json.dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()


def _package_digest(result: dict[str, Any]) -> str:
    target = result.get("target")
    files = result.get("files")
    if not isinstance(target, str) or not isinstance(files, list):
        raise AssertionError("browser package-build result cannot be rehashed")
    return _sha256_json({
        "format": PACKAGE_DIGEST_FORMAT,
        "target": target,
        "files": files,
    })


def _result_with_rehashed_file(result: dict[str, Any], relative_path: str, source: str) -> dict[str, Any]:
    rehashed = json.loads(json.dumps(result))
    files = rehashed.get("files")
    if not isinstance(files, list):
        raise AssertionError("browser package-build result file list drifted")
    for entry in files:
        if isinstance(entry, dict) and entry.get("path") == relative_path:
            entry["bytes"] = len(source.encode("utf-8"))
            entry["sha256"] = _sha256_text(source)
            break
    else:
        raise AssertionError(f"browser package-build result is missing {relative_path}")
    rehashed["package_digest"] = _package_digest(rehashed)
    return rehashed


def package_plan_digest(plan: dict[str, Any]) -> str:
    return _sha256_json({
        "format": PACKAGE_PLAN_DIGEST_FORMAT,
        "plan": plan,
    })


def assert_package_plan_review(review: dict[str, Any]) -> str:
    if review.get("format") != PACKAGE_PLAN_REVIEW_FORMAT:
        raise AssertionError("browser package-plan review format drifted")
    package_plan = review.get("package_plan")
    if not isinstance(package_plan, dict):
        raise AssertionError("browser package-plan review must include package_plan")
    if package_plan.get("format") != PACKAGE_PLAN_FORMAT:
        raise AssertionError("browser package-plan review package_plan format drifted")
    reviewed_digest = review.get("package_plan_digest")
    if not isinstance(reviewed_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", reviewed_digest):
        raise AssertionError("browser package-plan review digest drifted")
    if package_plan_digest(package_plan) != reviewed_digest:
        raise AssertionError("browser package-plan review digest does not match package_plan")
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
    return reviewed_digest


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} must contain one JSON object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _assert_no_node_runtime_references(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    forbidden_patterns = (
        re.compile(r"(?:\bBuffer\s*(?:\.|\[)|new\s+Buffer\b|typeof\s+Buffer|globalThis\.Buffer)"),
        re.compile(r"(?:\bprocess\s*(?:\.|\[)|typeof\s+process|globalThis\.process)"),
        re.compile(r"node:"),
    )
    for pattern in forbidden_patterns:
        if pattern.search(source):
            raise AssertionError(f"{path.name} must not contain Node runtime reference matching {pattern.pattern!r}")


def assert_package_build(
    result: dict[str, Any],
    out_dir: Path,
    *,
    target: str = "chromium",
    origin_permission_mode: str = "embedded",
    expected_package_plan_digest: str | None = None,
    expected_route_config_digest: str | None = None,
) -> None:
    if result.get("format") != PACKAGE_BUILD_FORMAT:
        raise AssertionError("browser package-build format drifted")
    if result.get("target") != target:
        raise AssertionError("browser package-build target drifted")
    if Path(str(result.get("out_dir"))) != out_dir:
        raise AssertionError("browser package-build output directory drifted")
    package_plan_digest = result.get("package_plan_digest")
    if not isinstance(package_plan_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", package_plan_digest):
        raise AssertionError("browser package-build package-plan digest drifted")
    if expected_package_plan_digest is not None and package_plan_digest != expected_package_plan_digest:
        raise AssertionError("browser package-build package-plan digest does not match reviewed plan")
    route_config_digest = result.get("route_config_digest")
    if not isinstance(route_config_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", route_config_digest):
        raise AssertionError("browser package-build route config digest drifted")
    if expected_route_config_digest is not None and route_config_digest != expected_route_config_digest:
        raise AssertionError("browser package-build route config digest does not match reviewed config")
    if result.get("route_account_id") != ROUTE_ACCOUNT_ID:
        raise AssertionError("browser package-build route account id drifted")
    if result.get("route_type") != ROUTE_TYPE:
        raise AssertionError("browser package-build route type drifted")
    if result.get("native_host_name") != NATIVE_HOST_NAME:
        raise AssertionError("browser package-build native-host name drifted")
    expected_origin_mode = (
        "extension_storage"
        if origin_permission_mode == "extension-storage"
        else origin_permission_mode
    )
    expected_popup_mode = (
        "origin_permission_approval"
        if origin_permission_mode == "extension-storage"
        else "pending_requests"
    )
    expected_active_tab = origin_permission_mode == "extension-storage"
    if result.get("popup_mode") != expected_popup_mode:
        raise AssertionError("browser package-build popup mode drifted")
    if result.get("uses_active_tab_permission") is not expected_active_tab:
        raise AssertionError("browser package-build activeTab metadata drifted")
    if result.get("origin_permission_mode") != expected_origin_mode:
        raise AssertionError("browser package-build origin permission mode drifted")
    expected_permissions = (
        ["nativeMessaging", "activeTab", "storage"]
        if origin_permission_mode == "extension-storage"
        else ["nativeMessaging"]
    )
    if result.get("manifest_permissions") != expected_permissions:
        raise AssertionError("browser package-build manifest permission metadata drifted")
    if origin_permission_mode == "none":
        if "extension_id" in result:
            raise AssertionError("browser package-build ungated build must not expose extension id")
        if "local_pairing_digest" in result:
            raise AssertionError("browser package-build ungated build must not expose local pairing digest")
        if result.get("content_script_origins") != []:
            raise AssertionError("browser package-build ungated build must not expose content-script origins")
    elif origin_permission_mode == "embedded":
        if result.get("extension_id") != EXTENSION_ID:
            raise AssertionError("browser package-build embedded extension id drifted")
        if result.get("local_pairing_digest") != LOCAL_PAIRING_DIGEST:
            raise AssertionError("browser package-build local pairing digest drifted")
        if result.get("content_script_origins") != [CONTENT_SCRIPT_ORIGIN]:
            raise AssertionError("browser package-build content-script origins drifted")
    elif origin_permission_mode == "extension-storage":
        if "extension_id" in result:
            raise AssertionError("browser package-build extension-storage mode must not expose static extension id")
        if result.get("local_pairing_digest") != LOCAL_PAIRING_DIGEST:
            raise AssertionError("browser package-build local pairing digest drifted")
        if result.get("content_script_origins") != [CONTENT_SCRIPT_ORIGIN]:
            raise AssertionError("browser package-build content-script origins drifted")
    else:
        raise AssertionError(f"unsupported package-build origin-permission mode: {origin_permission_mode}")
    package_digest = result.get("package_digest")
    if not isinstance(package_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", package_digest):
        raise AssertionError("browser package-build package digest drifted")
    files = result.get("files")
    if not isinstance(files, list) or [item.get("path") if isinstance(item, dict) else None for item in files] != EXPECTED_FILES:
        raise AssertionError("browser package-build file list drifted")
    for field in (
        "installs_native_host_manifest",
        "writes_extension_storage",
        "stores_production_secrets",
        "dispatches_signers",
    ):
        if result.get(field) is not False:
            raise AssertionError(f"browser package-build must keep {field}=false")
    if origin_permission_mode == "embedded":
        if result.get("embeds_origin_permission_store") is not True:
            raise AssertionError("browser package-build must embed reviewed origin-permission store for content scripts")
        if result.get("uses_extension_origin_permission_storage") is not False:
            raise AssertionError("browser package-build embedded mode must not use extension origin-permission storage")
    elif origin_permission_mode == "extension-storage":
        if result.get("embeds_origin_permission_store") is not False:
            raise AssertionError("browser package-build extension-storage mode must not embed origin-permission store")
        if result.get("uses_extension_origin_permission_storage") is not True:
            raise AssertionError("browser package-build extension-storage mode must use extension origin-permission storage")
    elif origin_permission_mode == "none":
        if result.get("embeds_origin_permission_store") is not False:
            raise AssertionError("browser package-build ungated mode must not embed origin-permission store")
        if result.get("uses_extension_origin_permission_storage") is not False:
            raise AssertionError("browser package-build ungated mode must not use extension origin-permission storage")
    else:
        raise AssertionError(f"unsupported package-build origin-permission mode: {origin_permission_mode}")

    for name in EXPECTED_FILES:
        path = out_dir / name
        if not path.is_file():
            raise AssertionError(f"browser package-build did not write {name}")
        source = path.read_text(encoding="utf-8")
        if len(source.encode("utf-8")) <= 0:
            raise AssertionError(f"browser package-build wrote empty {name}")
        file_entry = files[EXPECTED_FILES.index(name)]
        if file_entry.get("bytes") != len(source.encode("utf-8")):
            raise AssertionError(f"browser package-build byte count drifted for {name}")
        if file_entry.get("sha256") != _sha256_text(source):
            raise AssertionError(f"browser package-build sha256 drifted for {name}")
    expected_package_digest = _package_digest(result)
    if package_digest != expected_package_digest:
        raise AssertionError("browser package-build package digest does not match file manifest")

    manifest = _read_json(out_dir / "manifest.json")
    if manifest.get("permissions") != expected_permissions:
        raise AssertionError("browser package-build manifest permissions drifted")
    if manifest.get("action", {}).get("default_popup") != "nsealr-popup.html":
        raise AssertionError("browser package-build popup html drifted")
    for forbidden in ("host_permissions", "optional_host_permissions"):
        if forbidden in manifest:
            raise AssertionError(f"browser package-build manifest must not include {forbidden}")
    if origin_permission_mode == "embedded" and "storage" in manifest:
        raise AssertionError("browser package-build embedded mode must not include storage permission")
    if target == "chromium" and "browser_specific_settings" in manifest:
        raise AssertionError("browser package-build Chromium manifest must not include Firefox settings")
    if target == "firefox":
        if manifest.get("browser_specific_settings") != {"gecko": {"id": FIREFOX_EXTENSION_ID}}:
            raise AssertionError("browser package-build Firefox settings drifted")
    if origin_permission_mode == "none":
        for forbidden in ("content_scripts", "web_accessible_resources"):
            if forbidden in manifest:
                raise AssertionError(f"browser package-build ungated manifest must not include {forbidden}")
    else:
        if manifest.get("content_scripts") != [{
            "matches": [CONTENT_SCRIPT_MATCH],
            "js": ["nsealr-content-script-entrypoint.js"],
            "run_at": "document_start",
            "all_frames": False,
            "match_about_blank": False,
        }]:
            raise AssertionError("browser package-build content-script manifest drifted")
        if manifest.get("web_accessible_resources") != [{
            "resources": ["nsealr-page-script-entrypoint.js"],
            "matches": [CONTENT_SCRIPT_MATCH],
        }]:
            raise AssertionError("browser package-build page-script resource drifted")

    for name in EXPECTED_FILES[1:]:
        if name.endswith(".js"):
            _assert_no_node_runtime_references(out_dir / name)
    background = (out_dir / "nsealr-background-entrypoint.js").read_text(encoding="utf-8")
    if ROUTE_ACCOUNT_ID not in background:
        raise AssertionError("browser package-build did not embed selected route account id")
    if NATIVE_HOST_NAME not in background:
        raise AssertionError("browser package-build did not embed native host name")
    if origin_permission_mode != "none" and LOCAL_PAIRING_DIGEST not in background:
        raise AssertionError("browser package-build did not embed reviewed origin permission digest")
    popup = (out_dir / "nsealr-popup-entrypoint.js").read_text(encoding="utf-8")
    if origin_permission_mode == "embedded" and EXTENSION_ID not in background:
        raise AssertionError("browser package-build embedded mode did not embed reviewed extension id")
    if origin_permission_mode == "extension-storage" and (EXTENSION_ID in background or EXTENSION_ID in popup):
        raise AssertionError("browser package-build extension-storage mode must use runtime extension id")
    popup_html = (out_dir / "nsealr-popup.html").read_text(encoding="utf-8")
    if "nsealr-popup-entrypoint.js" not in popup_html or "nsealr-popup-root" not in popup_html:
        raise AssertionError("browser package-build popup html drifted")


def assert_package_build_package_verifier(
    result: dict[str, Any],
    root: Path,
    name: str,
    package_plan_review: Path,
) -> None:
    build_result_path = root / f"{name}-package-build-result.json"
    _write_json(build_result_path, result)
    verified = run_json_command(build_browser_package_verify_command(
        companion=COMPANION,
        build_result=build_result_path,
        package_plan_review=package_plan_review,
    ))
    if verified != result:
        raise AssertionError("browser package-owned package-build verifier output drifted")


def assert_package_build_package_verifier_rejects_package_plan_review_mismatch(
    result: dict[str, Any],
    root: Path,
    name: str,
    mismatched_package_plan_review: Path,
) -> None:
    build_result_path = root / f"{name}-wrong-package-plan-review-package-build-result.json"
    _write_json(build_result_path, result)
    verify_result = run_failure_without_stdout(
        build_browser_package_verify_command(
            companion=COMPANION,
            build_result=build_result_path,
            package_plan_review=mismatched_package_plan_review,
        ),
        "browser package-verify",
    )
    if "package-plan review digest mismatch" not in verify_result.stderr:
        raise AssertionError("browser package-owned package-plan review mismatch rejection drifted")


def assert_package_build_package_verifier_rejects_manifest_drift(
    result: dict[str, Any],
    root: Path,
    name: str,
    package_plan_review: Path,
) -> None:
    source_dir = Path(str(result.get("out_dir")))
    tampered_dir = root / f"{name}-manifest-drift"
    shutil.copytree(source_dir, tampered_dir)

    manifest_path = tampered_dir / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest["name"] = "nSealr Drifted Browser Extension"
    _write_json(manifest_path, manifest)

    tampered_result = _result_with_rehashed_file(
        result,
        "manifest.json",
        manifest_path.read_text(encoding="utf-8"),
    )
    tampered_result["out_dir"] = str(tampered_dir)
    build_result_path = root / f"{name}-manifest-drift-package-build-result.json"
    _write_json(build_result_path, tampered_result)

    verify_result = run_failure_without_stdout(
        build_browser_package_verify_command(
            companion=COMPANION,
            build_result=build_result_path,
            package_plan_review=package_plan_review,
        ),
        "browser package-verify",
    )
    if "manifest drifted" not in verify_result.stderr:
        raise AssertionError("browser package-owned package-build verifier manifest-drift rejection drifted")


def assert_package_build_package_verifier_rejects_background_route_drift(
    result: dict[str, Any],
    root: Path,
    name: str,
    package_plan_review: Path,
) -> None:
    source_dir = Path(str(result.get("out_dir")))
    tampered_dir = root / f"{name}-background-route-drift"
    shutil.copytree(source_dir, tampered_dir)

    background_path = tampered_dir / "nsealr-background-entrypoint.js"
    background = background_path.read_text(encoding="utf-8")
    if ROUTE_ACCOUNT_ID not in background:
        raise AssertionError("browser package-build background test fixture is missing route account id")
    tampered_background = background.replace(ROUTE_ACCOUNT_ID, "esp32-usb-slot-drifted", 1)
    background_path.write_text(tampered_background, encoding="utf-8")

    tampered_result = _result_with_rehashed_file(
        result,
        "nsealr-background-entrypoint.js",
        tampered_background,
    )
    tampered_result["out_dir"] = str(tampered_dir)
    build_result_path = root / f"{name}-background-route-drift-package-build-result.json"
    _write_json(build_result_path, tampered_result)

    verify_result = run_failure_without_stdout(
        build_browser_package_verify_command(
            companion=COMPANION,
            build_result=build_result_path,
            package_plan_review=package_plan_review,
        ),
        "browser package-verify",
    )
    if "route metadata" not in verify_result.stderr:
        raise AssertionError("browser package-owned package-build verifier background-route rejection drifted")


def assert_package_build_package_verifier_rejects_popup_mode_drift(
    result: dict[str, Any],
    root: Path,
    name: str,
    package_plan_review: Path,
) -> None:
    source_dir = Path(str(result.get("out_dir")))
    tampered_dir = root / f"{name}-popup-mode-drift"
    shutil.copytree(source_dir, tampered_dir)

    popup_path = tampered_dir / "nsealr-popup-entrypoint.js"
    popup = popup_path.read_text(encoding="utf-8")
    if "list_pending_requests" not in popup:
        raise AssertionError("browser package-build popup test fixture is missing pending-request control")
    tampered_popup = popup.replace("list_pending_requests", "list_tampered_requests", 1)
    popup_path.write_text(tampered_popup, encoding="utf-8")

    tampered_result = _result_with_rehashed_file(
        result,
        "nsealr-popup-entrypoint.js",
        tampered_popup,
    )
    tampered_result["out_dir"] = str(tampered_dir)
    build_result_path = root / f"{name}-popup-mode-drift-package-build-result.json"
    _write_json(build_result_path, tampered_result)

    verify_result = run_failure_without_stdout(
        build_browser_package_verify_command(
            companion=COMPANION,
            build_result=build_result_path,
            package_plan_review=package_plan_review,
        ),
        "browser package-verify",
    )
    if "popup mode" not in verify_result.stderr:
        raise AssertionError("browser package-owned package-build verifier popup-mode rejection drifted")


def assert_package_build_package_verifier_rejects_popup_html_drift(
    result: dict[str, Any],
    root: Path,
    name: str,
    package_plan_review: Path,
) -> None:
    source_dir = Path(str(result.get("out_dir")))
    tampered_dir = root / f"{name}-popup-html-drift"
    shutil.copytree(source_dir, tampered_dir)

    popup_html_path = tampered_dir / "nsealr-popup.html"
    popup_html = popup_html_path.read_text(encoding="utf-8")
    popup_script = '<script type="module" src="nsealr-popup-entrypoint.js"></script>'
    if popup_script not in popup_html:
        raise AssertionError("browser package-build popup HTML test fixture is missing entrypoint script")
    tampered_popup_html = popup_html.replace(
        popup_script,
        f'{popup_script}\n  <script type="module" src="unexpected-popup.js"></script>',
        1,
    )
    popup_html_path.write_text(tampered_popup_html, encoding="utf-8")

    tampered_result = _result_with_rehashed_file(
        result,
        "nsealr-popup.html",
        tampered_popup_html,
    )
    tampered_result["out_dir"] = str(tampered_dir)
    build_result_path = root / f"{name}-popup-html-drift-package-build-result.json"
    _write_json(build_result_path, tampered_result)

    verify_result = run_failure_without_stdout(
        build_browser_package_verify_command(
            companion=COMPANION,
            build_result=build_result_path,
            package_plan_review=package_plan_review,
        ),
        "browser package-verify",
    )
    if "popup HTML" not in verify_result.stderr:
        raise AssertionError("browser package-owned package-build verifier popup HTML rejection drifted")


def assert_package_build_package_verifier_rejects_source_tree_out_dir(
    result: dict[str, Any],
    root: Path,
    name: str,
    package_plan_review: Path,
) -> None:
    source_dir = Path(str(result.get("out_dir")))
    unsafe_dir = COMPANION / "apps" / "browser-extension" / "src" / f"generated-extension-verify-{name}"
    if unsafe_dir.exists():
        shutil.rmtree(unsafe_dir)
    try:
        shutil.copytree(source_dir, unsafe_dir)
        tampered_result = json.loads(json.dumps(result))
        tampered_result["out_dir"] = str(unsafe_dir)
        build_result_path = root / f"{name}-source-tree-out-dir-package-build-result.json"
        _write_json(build_result_path, tampered_result)

        verify_result = run_failure_without_stdout(
            build_browser_package_verify_command(
                companion=COMPANION,
                build_result=build_result_path,
                package_plan_review=package_plan_review,
            ),
            "browser package-verify",
        )
        if "outside the companion source tree" not in verify_result.stderr:
            raise AssertionError("browser package-owned package-build verifier source-tree output rejection drifted")
    finally:
        if unsafe_dir.exists():
            shutil.rmtree(unsafe_dir)


def assert_package_build_package_verifier_rejects_origin_approval_popup_drift(
    result: dict[str, Any],
    root: Path,
    name: str,
    package_plan_review: Path,
) -> None:
    source_dir = Path(str(result.get("out_dir")))
    tampered_dir = root / f"{name}-origin-approval-popup-drift"
    shutil.copytree(source_dir, tampered_dir)

    popup_path = tampered_dir / "nsealr-popup-entrypoint.js"
    popup = popup_path.read_text(encoding="utf-8")
    if "request_origin_permission_review" not in popup:
        raise AssertionError("browser package-build origin-approval popup test fixture is missing review control")
    tampered_popup = popup.replace("request_origin_permission_review", "request_tampered_permission_review")
    popup_path.write_text(tampered_popup, encoding="utf-8")

    tampered_result = _result_with_rehashed_file(
        result,
        "nsealr-popup-entrypoint.js",
        tampered_popup,
    )
    tampered_result["out_dir"] = str(tampered_dir)
    build_result_path = root / f"{name}-origin-approval-popup-drift-package-build-result.json"
    _write_json(build_result_path, tampered_result)

    verify_result = run_failure_without_stdout(
        build_browser_package_verify_command(
            companion=COMPANION,
            build_result=build_result_path,
            package_plan_review=package_plan_review,
        ),
        "browser package-verify",
    )
    if "popup mode" not in verify_result.stderr:
        raise AssertionError("browser package-owned package-build verifier origin-approval popup rejection drifted")


def assert_package_build_package_verifier_rejects_content_script_drift(
    result: dict[str, Any],
    root: Path,
    name: str,
    package_plan_review: Path,
) -> None:
    source_dir = Path(str(result.get("out_dir")))
    tampered_dir = root / f"{name}-content-script-drift"
    shutil.copytree(source_dir, tampered_dir)

    content_script_path = tampered_dir / "nsealr-content-script-entrypoint.js"
    content_script = content_script_path.read_text(encoding="utf-8")
    if "installNsealrContentScriptEntrypoint" not in content_script:
        raise AssertionError("browser package-build content-script test fixture is missing entrypoint marker")
    tampered_content_script = content_script.replace(
        "installNsealrContentScriptEntrypoint",
        "installTamperedContentScriptEntrypoint",
    )
    content_script_path.write_text(tampered_content_script, encoding="utf-8")

    tampered_result = _result_with_rehashed_file(
        result,
        "nsealr-content-script-entrypoint.js",
        tampered_content_script,
    )
    tampered_result["out_dir"] = str(tampered_dir)
    build_result_path = root / f"{name}-content-script-drift-package-build-result.json"
    _write_json(build_result_path, tampered_result)

    verify_result = run_failure_without_stdout(
        build_browser_package_verify_command(
            companion=COMPANION,
            build_result=build_result_path,
            package_plan_review=package_plan_review,
        ),
        "browser package-verify",
    )
    if "content-script binding" not in verify_result.stderr:
        raise AssertionError("browser package-owned package-build verifier content-script rejection drifted")


def assert_package_build_package_verifier_rejects_page_script_drift(
    result: dict[str, Any],
    root: Path,
    name: str,
    package_plan_review: Path,
) -> None:
    source_dir = Path(str(result.get("out_dir")))
    tampered_dir = root / f"{name}-page-script-drift"
    shutil.copytree(source_dir, tampered_dir)

    page_script_path = tampered_dir / "nsealr-page-script-entrypoint.js"
    page_script = page_script_path.read_text(encoding="utf-8")
    if "installNsealrPageScriptEntrypoint" not in page_script:
        raise AssertionError("browser package-build page-script test fixture is missing entrypoint marker")
    tampered_page_script = page_script.replace(
        "installNsealrPageScriptEntrypoint",
        "installTamperedPageScriptEntrypoint",
    )
    page_script_path.write_text(tampered_page_script, encoding="utf-8")

    tampered_result = _result_with_rehashed_file(
        result,
        "nsealr-page-script-entrypoint.js",
        tampered_page_script,
    )
    tampered_result["out_dir"] = str(tampered_dir)
    build_result_path = root / f"{name}-page-script-drift-package-build-result.json"
    _write_json(build_result_path, tampered_result)

    verify_result = run_failure_without_stdout(
        build_browser_package_verify_command(
            companion=COMPANION,
            build_result=build_result_path,
            package_plan_review=package_plan_review,
        ),
        "browser package-verify",
    )
    if "page-script binding" not in verify_result.stderr:
        raise AssertionError("browser package-owned package-build verifier page-script rejection drifted")


def assert_route_config_review(review: dict[str, Any]) -> None:
    if review.get("format") != ROUTE_CONFIG_REVIEW_FORMAT:
        raise AssertionError("browser route-config review format drifted")
    route_config_digest = review.get("route_config_digest")
    if not isinstance(route_config_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", route_config_digest):
        raise AssertionError("browser route-config review digest drifted")
    if review.get("route_config") != {
        "format": "nsealr-browser-extension-route-config-v0",
        "account_id": ROUTE_ACCOUNT_ID,
        "route_type": ROUTE_TYPE,
    }:
        raise AssertionError("browser route-config review config drifted")
    if review.get("route_request") != {
        "account_id": ROUTE_ACCOUNT_ID,
        "method": "sign_event",
        "route_type": ROUTE_TYPE,
    }:
        raise AssertionError("browser route-config review request drifted")
    for field in ("writes_extension_storage", "creates_grants", "dispatches_signers", "stores_production_secrets"):
        if review.get(field) is not False:
            raise AssertionError(f"browser route-config review must keep {field}=false")
    if review.get("requires_user_approval") is not True:
        raise AssertionError("browser route-config review must require user approval")


def assert_route_config_approval(approval: dict[str, Any], review: dict[str, Any]) -> None:
    if approval.get("format") != ROUTE_CONFIG_APPROVAL_FORMAT:
        raise AssertionError("browser route-config approval format drifted")
    if approval.get("route_config_digest") != review.get("route_config_digest"):
        raise AssertionError("browser route-config approval digest drifted")
    if approval.get("review") != review:
        raise AssertionError("browser route-config approval review drifted")
    if approval.get("approved_at") != 1900000000:
        raise AssertionError("browser route-config approval timestamp drifted")
    for field in ("writes_extension_storage", "creates_grants", "dispatches_signers", "stores_production_secrets"):
        if approval.get(field) is not False:
            raise AssertionError(f"browser route-config approval must keep {field}=false")
    if approval.get("requires_user_approval") is not True:
        raise AssertionError("browser route-config approval must require user approval")


def _origin_permission_method(method: str) -> dict[str, str]:
    if method == "get_public_key":
        return {
            "method": method,
            "label": "Read public key",
            "effect": "The page can read the selected account public key through the browser provider.",
        }
    if method == "sign_event":
        return {
            "method": method,
            "label": "Request event signatures",
            "effect": "The page can ask for Nostr event signatures; the selected signer route still enforces review, approval, and policy.",
        }
    raise AssertionError(f"unsupported origin-permission method fixture: {method}")


def origin_permission_review() -> dict[str, Any]:
    return {
        "format": "nsealr-browser-origin-permission-review-v0",
        "origin": CONTENT_SCRIPT_ORIGIN,
        "app_name": "nSealr Browser Extension",
        "extension_id": EXTENSION_ID,
        "requested_methods": [
            _origin_permission_method("get_public_key"),
            _origin_permission_method("sign_event"),
        ],
        "local_pairing_digest": LOCAL_PAIRING_DIGEST,
        "requires_user_approval": True,
        "stores_production_secrets": False,
        "creates_grants": False,
        "injects_provider": False,
    }


def assert_origin_permission_approval(approval: dict[str, Any]) -> None:
    if approval.get("format") != ORIGIN_PERMISSION_APPROVAL_FORMAT:
        raise AssertionError("browser origin-permission approval format drifted")
    if approval.get("origin") != CONTENT_SCRIPT_ORIGIN:
        raise AssertionError("browser origin-permission approval origin drifted")
    if approval.get("extension_id") != EXTENSION_ID:
        raise AssertionError("browser origin-permission approval extension id drifted")
    if approval.get("approved_methods") != ["get_public_key", "sign_event"]:
        raise AssertionError("browser origin-permission approval method scope drifted")
    if approval.get("local_pairing_digest") != LOCAL_PAIRING_DIGEST:
        raise AssertionError("browser origin-permission approval digest drifted")
    for field in ("creates_grants", "stores_production_secrets", "contains_secret_material"):
        if approval.get(field) is not False:
            raise AssertionError(f"browser origin-permission approval must keep {field}=false")


def assert_origin_permission_store(store: dict[str, Any], approval: dict[str, Any]) -> None:
    if store.get("format") != ORIGIN_PERMISSION_STORE_FORMAT:
        raise AssertionError("browser origin-permission store format drifted")
    if store.get("approvals") != [approval]:
        raise AssertionError("browser origin-permission store approval drifted")
    for field in (
        "writes_extension_storage",
        "creates_grants",
        "dispatches_signers",
        "stores_production_secrets",
        "contains_secret_material",
    ):
        if store.get(field) is not False:
            raise AssertionError(f"browser origin-permission store must keep {field}=false")


def main() -> int:
    if not COMPANION.exists():
        raise FileNotFoundError(f"missing sibling repository: {COMPANION}")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)
    with tempfile.TemporaryDirectory(prefix="nsealr-browser-package-build-") as root:
        out_dir = Path(root) / "extension"
        route_review = run_json_command(build_browser_route_config_review_command(
            companion=COMPANION,
            route_account_id=ROUTE_ACCOUNT_ID,
            route_type=ROUTE_TYPE,
        ))
        assert_route_config_review(route_review)
        route_review_path = Path(root) / "route-config-review.json"
        route_review_path.write_text(json.dumps(route_review, indent=2) + "\n", encoding="utf-8")
        route_approval = run_json_command(build_browser_route_config_approval_command(
            companion=COMPANION,
            review_path=route_review_path,
            route_config_digest=route_review["route_config_digest"],
            approved_at=1900000000,
        ))
        assert_route_config_approval(route_approval, route_review)
        route_approval_path = Path(root) / "route-config-approval.json"
        route_approval_path.write_text(json.dumps(route_approval, indent=2) + "\n", encoding="utf-8")

        origin_review_path = Path(root) / "origin-permission-review.json"
        _write_json(origin_review_path, origin_permission_review())
        origin_approval = run_json_command(build_browser_origin_permission_approval_command(
            companion=COMPANION,
            review_path=origin_review_path,
            local_pairing_digest=LOCAL_PAIRING_DIGEST,
            approved_at=1900000001,
        ))
        assert_origin_permission_approval(origin_approval)
        origin_approval_path = Path(root) / "origin-permission-approval.json"
        _write_json(origin_approval_path, origin_approval)
        empty_origin_store = run_json_command(build_browser_origin_permission_store_create_command(
            companion=COMPANION,
            updated_at=1900000002,
        ))
        empty_origin_store_path = Path(root) / "origin-permission-store-empty.json"
        _write_json(empty_origin_store_path, empty_origin_store)
        origin_store = run_json_command(build_browser_origin_permission_store_upsert_command(
            companion=COMPANION,
            store_path=empty_origin_store_path,
            approval_path=origin_approval_path,
            updated_at=1900000003,
        ))
        assert_origin_permission_store(origin_store, origin_approval)
        origin_store_path = Path(root) / "origin-permission-store.json"
        _write_json(origin_store_path, origin_store)

        embedded_package_plan_review = run_json_command(build_browser_package_plan_command(
            companion=COMPANION,
            target="chromium",
            content_script_match=CONTENT_SCRIPT_MATCH,
            review=True,
        ))
        embedded_package_plan_digest = assert_package_plan_review(embedded_package_plan_review)
        embedded_package_plan_review_path = Path(root) / "embedded-package-plan-review.json"
        _write_json(embedded_package_plan_review_path, embedded_package_plan_review)
        extension_storage_package_plan_review = run_json_command(build_browser_package_plan_command(
            companion=COMPANION,
            target="chromium",
            content_script_match=CONTENT_SCRIPT_MATCH,
            origin_permission_mode="extension-storage",
            review=True,
        ))
        extension_storage_package_plan_digest = assert_package_plan_review(extension_storage_package_plan_review)
        extension_storage_package_plan_review_path = Path(root) / "extension-storage-package-plan-review.json"
        _write_json(extension_storage_package_plan_review_path, extension_storage_package_plan_review)
        firefox_package_plan_review = run_json_command(build_browser_package_plan_command(
            companion=COMPANION,
            target="firefox",
            firefox_extension_id=FIREFOX_EXTENSION_ID,
            review=True,
        ))
        firefox_package_plan_digest = assert_package_plan_review(firefox_package_plan_review)
        firefox_package_plan_review_path = Path(root) / "firefox-package-plan-review.json"
        _write_json(firefox_package_plan_review_path, firefox_package_plan_review)
        chromium_ungated_package_plan_review = run_json_command(build_browser_package_plan_command(
            companion=COMPANION,
            target="chromium",
            review=True,
        ))
        chromium_ungated_package_plan_digest = assert_package_plan_review(chromium_ungated_package_plan_review)
        chromium_ungated_package_plan_review_path = Path(root) / "chromium-ungated-package-plan-review.json"
        _write_json(chromium_ungated_package_plan_review_path, chromium_ungated_package_plan_review)

        command = build_browser_package_build_command(
            companion=COMPANION,
            target="chromium",
            out_dir=out_dir,
            package_plan_review=embedded_package_plan_review_path,
            route_account_id=ROUTE_ACCOUNT_ID,
            route_config_approval=route_approval_path,
            route_type=ROUTE_TYPE,
            content_script_match=CONTENT_SCRIPT_MATCH,
            extension_id=EXTENSION_ID,
            origin_permission_store=origin_store_path,
            local_pairing_digest=LOCAL_PAIRING_DIGEST,
        )
        embedded_result = run_json_command(command)
        assert_package_build(
            embedded_result,
            out_dir,
            expected_package_plan_digest=embedded_package_plan_digest,
            expected_route_config_digest=route_review["route_config_digest"],
        )
        assert_package_build_package_verifier(
            embedded_result,
            Path(root),
            "embedded",
            embedded_package_plan_review_path,
        )
        assert_package_build_package_verifier_rejects_package_plan_review_mismatch(
            embedded_result,
            Path(root),
            "embedded",
            firefox_package_plan_review_path,
        )
        assert_package_build_package_verifier_rejects_manifest_drift(
            embedded_result,
            Path(root),
            "embedded",
            embedded_package_plan_review_path,
        )
        assert_package_build_package_verifier_rejects_background_route_drift(
            embedded_result,
            Path(root),
            "embedded",
            embedded_package_plan_review_path,
        )
        assert_package_build_package_verifier_rejects_popup_mode_drift(
            embedded_result,
            Path(root),
            "embedded",
            embedded_package_plan_review_path,
        )
        assert_package_build_package_verifier_rejects_popup_html_drift(
            embedded_result,
            Path(root),
            "embedded",
            embedded_package_plan_review_path,
        )
        assert_package_build_package_verifier_rejects_source_tree_out_dir(
            embedded_result,
            Path(root),
            "embedded",
            embedded_package_plan_review_path,
        )
        assert_package_build_package_verifier_rejects_content_script_drift(
            embedded_result,
            Path(root),
            "embedded",
            embedded_package_plan_review_path,
        )
        assert_package_build_package_verifier_rejects_page_script_drift(
            embedded_result,
            Path(root),
            "embedded",
            embedded_package_plan_review_path,
        )

        extension_storage_out_dir = Path(root) / "extension-storage"
        extension_storage_command = build_browser_package_build_command(
            companion=COMPANION,
            target="chromium",
            out_dir=extension_storage_out_dir,
            package_plan_review=extension_storage_package_plan_review_path,
            route_account_id=ROUTE_ACCOUNT_ID,
            route_config_approval=route_approval_path,
            route_type=ROUTE_TYPE,
            content_script_match=CONTENT_SCRIPT_MATCH,
            origin_permission_mode="extension-storage",
            local_pairing_digest=LOCAL_PAIRING_DIGEST,
        )
        extension_storage_result = run_json_command(extension_storage_command)
        assert_package_build(
            extension_storage_result,
            extension_storage_out_dir,
            origin_permission_mode="extension-storage",
            expected_package_plan_digest=extension_storage_package_plan_digest,
            expected_route_config_digest=route_review["route_config_digest"],
        )
        assert_package_build_package_verifier(
            extension_storage_result,
            Path(root),
            "extension-storage",
            extension_storage_package_plan_review_path,
        )
        assert_package_build_package_verifier_rejects_origin_approval_popup_drift(
            extension_storage_result,
            Path(root),
            "extension-storage",
            extension_storage_package_plan_review_path,
        )

        firefox_out_dir = Path(root) / "firefox-extension"
        firefox_command = build_browser_package_build_command(
            companion=COMPANION,
            target="firefox",
            out_dir=firefox_out_dir,
            package_plan_review=firefox_package_plan_review_path,
            route_account_id=ROUTE_ACCOUNT_ID,
            route_config_approval=route_approval_path,
            route_type=ROUTE_TYPE,
            firefox_extension_id=FIREFOX_EXTENSION_ID,
        )
        firefox_result = run_json_command(firefox_command)
        assert_package_build(
            firefox_result,
            firefox_out_dir,
            target="firefox",
            origin_permission_mode="none",
            expected_package_plan_digest=firefox_package_plan_digest,
            expected_route_config_digest=route_review["route_config_digest"],
        )
        assert_package_build_package_verifier(
            firefox_result,
            Path(root),
            "firefox",
            firefox_package_plan_review_path,
        )

        existing_result = run_failure_without_stdout(command, "browser package-build")
        if "already exists" not in existing_result.stderr:
            raise AssertionError("browser package-build existing-output rejection message drifted")

        mismatched_plan_dir = Path(root) / "mismatched-plan"
        mismatched_plan = build_browser_package_build_command(
            companion=COMPANION,
            target="chromium",
            out_dir=mismatched_plan_dir,
            package_plan_review=firefox_package_plan_review_path,
            route_account_id=ROUTE_ACCOUNT_ID,
            route_type=ROUTE_TYPE,
            route_config_approval=route_approval_path,
            content_script_match=CONTENT_SCRIPT_MATCH,
            extension_id=EXTENSION_ID,
            origin_permission_store=origin_store_path,
            local_pairing_digest=LOCAL_PAIRING_DIGEST,
        )
        mismatched_plan_result = run_failure_without_stdout(mismatched_plan, "browser package-build")
        if "package-plan review digest mismatch" not in mismatched_plan_result.stderr:
            raise AssertionError("browser package-build package-plan review rejection message drifted")
        if mismatched_plan_dir.exists():
            raise AssertionError("browser package-build wrote output after package-plan review mismatch")

        invalid_route_dir = Path(root) / "invalid-route"
        invalid_route = build_browser_package_build_command(
            companion=COMPANION,
            target="chromium",
            out_dir=invalid_route_dir,
            package_plan_review=embedded_package_plan_review_path,
            route_account_id="bad account id",
            route_type=ROUTE_TYPE,
            route_config_approval=route_approval_path,
            content_script_match=CONTENT_SCRIPT_MATCH,
            extension_id=EXTENSION_ID,
            origin_permission_store=origin_store_path,
            local_pairing_digest=LOCAL_PAIRING_DIGEST,
        )
        invalid_route_result = run_failure_without_stdout(invalid_route, "browser package-build")
        if "account_id" not in invalid_route_result.stderr:
            raise AssertionError("browser package-build invalid-route rejection message drifted")
        if invalid_route_dir.exists():
            raise AssertionError("browser package-build wrote output after route validation failure")

        invalid_qr_route_dir = Path(root) / "invalid-qr-route"
        invalid_qr_route = build_browser_package_build_command(
            companion=COMPANION,
            target="chromium",
            out_dir=invalid_qr_route_dir,
            package_plan_review=embedded_package_plan_review_path,
            route_account_id="esp32-qr-account-0",
            route_type="esp32_qr_vault",
            route_config_approval=route_approval_path,
            content_script_match=CONTENT_SCRIPT_MATCH,
            extension_id=EXTENSION_ID,
            origin_permission_store=origin_store_path,
            local_pairing_digest=LOCAL_PAIRING_DIGEST,
        )
        invalid_qr_route_result = run_failure_without_stdout(invalid_qr_route, "browser package-build")
        if "browser-dispatchable" not in invalid_qr_route_result.stderr:
            raise AssertionError("browser package-build QR-route rejection message drifted")
        if invalid_qr_route_dir.exists():
            raise AssertionError("browser package-build wrote output after QR route validation failure")

        source_tree_out_dir = COMPANION / "apps" / "browser-extension" / "src" / "generated-extension"
        source_tree_output = build_browser_package_build_command(
            companion=COMPANION,
            target="chromium",
            out_dir=source_tree_out_dir,
            package_plan_review=chromium_ungated_package_plan_review_path,
            route_account_id=ROUTE_ACCOUNT_ID,
            route_type=ROUTE_TYPE,
            route_config_approval=route_approval_path,
        )
        source_tree_output_result = run_failure_without_stdout(source_tree_output, "browser package-build")
        if "outside the companion source tree" not in source_tree_output_result.stderr:
            raise AssertionError("browser package-build source-tree output rejection message drifted")
        if source_tree_out_dir.exists():
            raise AssertionError("browser package-build wrote output inside the companion source tree")

    print("nSealr cross-repo browser-extension package-build verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
