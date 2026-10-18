#!/usr/bin/env python3
"""Verify browser-extension origin-permission artifact CLIs across repositories."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

try:
    from scripts.browser_integration_support import (
        build_browser_origin_permission_approval_command,
        build_browser_origin_permission_store_create_command,
        build_browser_origin_permission_store_revoke_command,
        build_browser_origin_permission_store_upsert_command,
        run_failure_without_stdout,
        run_json_command,
    )
    from scripts.integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from browser_integration_support import (
        build_browser_origin_permission_approval_command,
        build_browser_origin_permission_store_create_command,
        build_browser_origin_permission_store_revoke_command,
        build_browser_origin_permission_store_upsert_command,
        run_failure_without_stdout,
        run_json_command,
    )
    from integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[1]
ORG = ROOT.parent
COMPANION = ORG / "companion"
ORIGIN_PERMISSION_REVIEW_FORMAT = "nsealr-browser-origin-permission-review-v0"
ORIGIN_PERMISSION_APPROVAL_FORMAT = "nsealr-browser-origin-permission-approval-v0"
ORIGIN_PERMISSION_STORE_FORMAT = "nsealr-browser-origin-permission-store-v0"
ORIGIN = "https://example.com"
APP_NAME = "Example"
EXTENSION_ID = "extension@nsealr.dev"
LOCAL_PAIRING_DIGEST = "a" * 64


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _method(method: str) -> dict[str, str]:
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
    raise AssertionError(f"unsupported method fixture: {method}")


def origin_permission_review() -> dict[str, Any]:
    return {
        "format": ORIGIN_PERMISSION_REVIEW_FORMAT,
        "origin": ORIGIN,
        "app_name": APP_NAME,
        "extension_id": EXTENSION_ID,
        "requested_methods": [_method("get_public_key"), _method("sign_event")],
        "local_pairing_digest": LOCAL_PAIRING_DIGEST,
        "requires_user_approval": True,
        "stores_production_secrets": False,
        "creates_grants": False,
        "injects_provider": False,
    }


def assert_approval(approval: dict[str, Any]) -> None:
    if approval.get("format") != ORIGIN_PERMISSION_APPROVAL_FORMAT:
        raise AssertionError("origin-permission approval format drifted")
    if approval.get("origin") != ORIGIN:
        raise AssertionError("origin-permission approval origin drifted")
    if approval.get("app_name") != APP_NAME:
        raise AssertionError("origin-permission approval app name drifted")
    if approval.get("extension_id") != EXTENSION_ID:
        raise AssertionError("origin-permission approval extension id drifted")
    if approval.get("approved_methods") != ["get_public_key", "sign_event"]:
        raise AssertionError("origin-permission approval method scope drifted")
    if approval.get("local_pairing_digest") != LOCAL_PAIRING_DIGEST:
        raise AssertionError("origin-permission approval pairing digest drifted")
    if approval.get("approved_at") != 1900000000:
        raise AssertionError("origin-permission approval timestamp drifted")
    for field in (
        "creates_grants",
        "stores_production_secrets",
        "contains_secret_material",
    ):
        if approval.get(field) is not False:
            raise AssertionError(f"origin-permission approval must keep {field}=false")
    if approval.get("requires_user_approval") is not True:
        raise AssertionError("origin-permission approval must require user approval")
    if approval.get("authorizes_provider_injection") is not True:
        raise AssertionError("origin-permission approval must authorize provider injection")


def assert_store(store: dict[str, Any], *, updated_at: int, approvals: list[dict[str, Any]]) -> None:
    if store.get("format") != ORIGIN_PERMISSION_STORE_FORMAT:
        raise AssertionError("origin-permission store format drifted")
    if store.get("updated_at") != updated_at:
        raise AssertionError("origin-permission store timestamp drifted")
    if store.get("approvals") != approvals:
        raise AssertionError("origin-permission store approvals drifted")
    for field in (
        "writes_extension_storage",
        "creates_grants",
        "dispatches_signers",
        "stores_production_secrets",
        "contains_secret_material",
    ):
        if store.get(field) is not False:
            raise AssertionError(f"origin-permission store must keep {field}=false")
    if store.get("requires_user_approval") is not True:
        raise AssertionError("origin-permission store must require user approval")


def main() -> int:
    if not COMPANION.exists():
        raise FileNotFoundError(f"missing sibling repository: {COMPANION}")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)
    with tempfile.TemporaryDirectory(prefix="nsealr-browser-origin-permission-") as root:
        root_path = Path(root)
        review_path = root_path / "origin-review.json"
        approval_path = root_path / "origin-approval.json"
        store_path = root_path / "origin-store.json"
        _write_json(review_path, origin_permission_review())

        approval = run_json_command(build_browser_origin_permission_approval_command(
            companion=COMPANION,
            review_path=review_path,
            local_pairing_digest=LOCAL_PAIRING_DIGEST,
            approved_at=1900000000,
        ))
        assert_approval(approval)
        _write_json(approval_path, approval)

        store = run_json_command(build_browser_origin_permission_store_create_command(
            companion=COMPANION,
            updated_at=1900000001,
        ))
        assert_store(store, updated_at=1900000001, approvals=[])
        _write_json(store_path, store)

        updated_store = run_json_command(build_browser_origin_permission_store_upsert_command(
            companion=COMPANION,
            store_path=store_path,
            approval_path=approval_path,
            updated_at=1900000002,
        ))
        assert_store(updated_store, updated_at=1900000002, approvals=[approval])
        _write_json(store_path, updated_store)

        revoked_store = run_json_command(build_browser_origin_permission_store_revoke_command(
            companion=COMPANION,
            store_path=store_path,
            origin=ORIGIN,
            extension_id=EXTENSION_ID,
            local_pairing_digest=LOCAL_PAIRING_DIGEST,
            updated_at=1900000003,
        ))
        assert_store(revoked_store, updated_at=1900000003, approvals=[])

        mismatched_approval = build_browser_origin_permission_approval_command(
            companion=COMPANION,
            review_path=review_path,
            local_pairing_digest="b" * 64,
            approved_at=1900000004,
        )
        mismatch = run_failure_without_stdout(mismatched_approval, "browser origin-permission approval")
        if not re.search(r"digest", mismatch.stderr, re.IGNORECASE):
            raise AssertionError("origin-permission digest-mismatch rejection message drifted")

        backwards_revoke = build_browser_origin_permission_store_revoke_command(
            companion=COMPANION,
            store_path=store_path,
            origin=ORIGIN,
            extension_id=EXTENSION_ID,
            local_pairing_digest=LOCAL_PAIRING_DIGEST,
            updated_at=1900000001,
        )
        backwards = run_failure_without_stdout(backwards_revoke, "browser origin-permission revoke")
        if "backward" not in backwards.stderr:
            raise AssertionError("origin-permission backward-timestamp rejection message drifted")

    print("nSealr cross-repo browser-extension origin-permission CLI verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
