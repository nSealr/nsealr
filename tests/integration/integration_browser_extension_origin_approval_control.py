#!/usr/bin/env python3
"""Verify browser-extension popup origin-approval control routing across repositories."""

from __future__ import annotations

import tempfile
from pathlib import Path

try:
    from scripts.integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[1]
ORG = ROOT.parent
COMPANION = ORG / "companion"


def _node_script() -> str:
    background = (COMPANION / "apps/browser-extension/src/background.ts").as_uri()
    runtime_message = (COMPANION / "apps/browser-extension/src/runtime-message.ts").as_uri()
    pending_control = (COMPANION / "apps/browser-extension/src/pending-control.ts").as_uri()
    storage = (COMPANION / "apps/browser-extension/src/origin-permission-storage.ts").as_uri()
    return f"""
const {{ createBrowserExtensionBackgroundController }} = await import({background!r});
const {{ handleBrowserExtensionRuntimeMessage }} = await import({runtime_message!r});
const {{ BROWSER_EXTENSION_CONTROL_PROTOCOL }} = await import({pending_control!r});
const {{
  BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY,
  readBrowserExtensionOriginPermissionStoreFromStorage
}} = await import({storage!r});

class FakeOriginPermissionStorage {{
  constructor() {{
    this.stored = {{}};
    this.setCalls = [];
  }}
  get(key) {{
    if (!(key in this.stored)) return {{}};
    return {{ [key]: this.stored[key] }};
  }}
  set(items) {{
    this.setCalls.push(items);
    this.stored[BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY] =
      items[BROWSER_EXTENSION_ORIGIN_PERMISSION_STORAGE_KEY];
  }}
}}

const routeRequest = {{
  account_id: "esp32-usb-slot-0",
  method: "sign_event",
  route_type: "esp32_usb_nip46"
}};
const storageArea = new FakeOriginPermissionStorage();
const nativeMessages = [];
const localPairingDigest = "d".repeat(64);
const controller = createBrowserExtensionBackgroundController({{
  routeRequest,
  originPermissionStorage: storageArea,
  originPermissionApprovalNow: () => 1900000090,
  sendNativeMessage(_hostName, message) {{
    nativeMessages.push(message);
    throw new Error(`approval control must not use native messaging: ${{message.operation}}`);
  }}
}});
const originReview = {{
  format: "nsealr-browser-origin-permission-review-v0",
  origin: "https://example.com",
  app_name: "nSealr Browser Extension",
  extension_id: "extension@nsealr.dev",
  requested_methods: [
    {{
      method: "get_public_key",
      label: "Read public key",
      effect: "The page can read the selected account public key through the browser provider."
    }}
  ],
  local_pairing_digest: localPairingDigest,
  requires_user_approval: true,
  stores_production_secrets: false,
  creates_grants: false,
  injects_provider: false
}};
const controlRequest = {{
  protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
  version: 1,
  request_id: "lab-origin-approval-control",
  method: "approve_origin_permission",
  params: {{
    origin_review: originReview,
    reviewed_local_pairing_digest: localPairingDigest
  }}
}};
const response = await handleBrowserExtensionRuntimeMessage(controlRequest, {{
  id: "extension@nsealr.dev",
  url: "chrome-extension://extension-id/popup.html"
}}, {{
  controller,
  extensionId: "extension@nsealr.dev"
}});
if (response.protocol !== BROWSER_EXTENSION_CONTROL_PROTOCOL || response.ok !== true) {{
  throw new Error("origin-approval control response failed");
}}
if (response.result.approval.origin !== "https://example.com") {{
  throw new Error("origin-approval origin drifted");
}}
if (response.result.approval.local_pairing_digest !== localPairingDigest) {{
  throw new Error("origin-approval pairing digest drifted");
}}
if (response.result.storage_write.writes_extension_storage !== true) {{
  throw new Error("origin-approval storage write metadata drifted");
}}
for (const field of [
  "creates_grants",
  "dispatches_signers",
  "stores_production_secrets",
  "contains_secret_material"
]) {{
  if (response.result[field] !== false) throw new Error(`origin-approval result must keep ${{field}}=false`);
}}
if (nativeMessages.length !== 0) {{
  throw new Error("origin-approval control contacted native messaging");
}}
const stored = await readBrowserExtensionOriginPermissionStoreFromStorage(storageArea);
if (stored.approvals.length !== 1 || stored.approvals[0].origin !== "https://example.com") {{
  throw new Error("origin-approval control did not persist the approved origin");
}}
const denied = await handleBrowserExtensionRuntimeMessage(controlRequest, {{
  id: "extension@nsealr.dev",
  url: "https://example.com/app"
}}, {{
  controller,
  extensionId: "extension@nsealr.dev"
}});
if (denied.ok !== false || denied.error.code !== "invalid_sender") {{
  throw new Error("page-origin approval control sender was not rejected");
}}
if (nativeMessages.length !== 0) {{
  throw new Error("rejected page-origin approval control contacted native messaging");
}}
"""


def main() -> int:
    if not COMPANION.exists():
        raise FileNotFoundError(f"missing sibling repository: {COMPANION}")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)
    with tempfile.TemporaryDirectory(prefix="nsealr-browser-origin-approval-control-") as root:
        script_path = Path(root) / "verify-origin-approval-control.mjs"
        script_path.write_text(_node_script(), encoding="utf-8")
        run_command([
            "pnpm",
            "exec",
            "node",
            "--disable-warning=DEP0205",
            "--import",
            "tsx/esm",
            str(script_path),
        ], COMPANION)

    print("nSealr cross-repo browser-extension origin-approval control verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
