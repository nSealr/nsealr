#!/usr/bin/env python3
"""Verify browser-extension popup origin-review control routing across repositories."""

from __future__ import annotations

import tempfile
from pathlib import Path

try:
    from tests.integration.integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[2]
COMPANION = ROOT


def _node_script() -> str:
    background = (COMPANION / "apps/bridge/browser-extension/src/background.ts").as_uri()
    runtime_message = (COMPANION / "apps/bridge/browser-extension/src/runtime-message.ts").as_uri()
    pending_control = (COMPANION / "apps/bridge/browser-extension/src/pending-control.ts").as_uri()
    client = (COMPANION / "packages/client/src/index.ts").as_uri()
    return f"""
const {{ createBrowserExtensionBackgroundController }} = await import({background!r});
const {{ handleBrowserExtensionRuntimeMessage }} = await import({runtime_message!r});
const {{ BROWSER_EXTENSION_CONTROL_PROTOCOL }} = await import({pending_control!r});
const {{ handleLocalServiceRequest }} = await import({client!r});

const routeRequest = {{
  account_id: "esp32-usb-slot-0",
  method: "sign_event",
  route_type: "esp32_usb_nip46"
}};
const nativeMessages = [];
const controller = createBrowserExtensionBackgroundController({{
  routeRequest,
  nextServiceRequestId: () => "lab-origin-review-service",
  sendNativeMessage(_hostName, message) {{
    nativeMessages.push(message);
    if (message.operation === "request_pairing") return handleLocalServiceRequest(message);
    throw new Error(`unexpected native operation ${{message.operation}}`);
  }}
}});
const controlRequest = {{
  protocol: BROWSER_EXTENSION_CONTROL_PROTOCOL,
  version: 1,
  request_id: "lab-origin-review-control",
  method: "request_origin_permission_review",
  params: {{
    sender: {{
      extension_id: "extension@nsealr.dev",
      page_url: "https://example.com/app"
    }}
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
  throw new Error("origin-review control response failed");
}}
if (response.result.origin_review.origin !== "https://example.com") {{
  throw new Error("origin-review origin drifted");
}}
if (response.result.origin_review.extension_id !== "extension@nsealr.dev") {{
  throw new Error("origin-review extension id drifted");
}}
const methods = response.result.origin_review.requested_methods.map((method) => method.method);
if (JSON.stringify(methods) !== JSON.stringify(["get_public_key", "sign_event"])) {{
  throw new Error("origin-review method projection drifted");
}}
for (const field of [
  "stores_production_secrets",
  "contains_secret_material",
  "creates_grants",
  "injects_provider"
]) {{
  if (response.result[field] !== false) throw new Error(`origin-review result must keep ${{field}}=false`);
}}
if (nativeMessages.length !== 1 || nativeMessages[0].operation !== "request_pairing") {{
  throw new Error("origin-review control did not route through request_pairing");
}}
const denied = await handleBrowserExtensionRuntimeMessage(controlRequest, {{
  id: "extension@nsealr.dev",
  url: "https://example.com/app"
}}, {{
  controller,
  extensionId: "extension@nsealr.dev"
}});
if (denied.ok !== false || denied.error.code !== "invalid_sender") {{
  throw new Error("page-origin control sender was not rejected");
}}
if (nativeMessages.length !== 1) {{
  throw new Error("rejected page-origin control sender contacted native messaging");
}}
"""


def main() -> int:
    if not COMPANION.exists():
        raise FileNotFoundError(f"missing product component: {COMPANION}")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)
    with tempfile.TemporaryDirectory(prefix="nsealr-browser-origin-review-control-") as root:
        script_path = Path(root) / "verify-origin-review-control.mjs"
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

    print("nSealr integrated browser-extension origin-review control verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
