#!/usr/bin/env python3
"""Verify the browser-safe SDK facade against the live companion checkout."""

from __future__ import annotations

import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path

try:
    from tests.integration.integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[2]
COMPANION = ROOT


@dataclass(frozen=True)
class CommandPlan:
    cwd: Path
    argv: list[str]


def build_browser_runtime_imports_command(*, companion: Path) -> CommandPlan:
    return CommandPlan(cwd=companion, argv=["pnpm", "browser-runtime-imports:check"])


def build_sdk_browser_command(*, companion: Path, script_path: Path) -> CommandPlan:
    return CommandPlan(cwd=companion, argv=["node", str(script_path)])


def write_sdk_browser_script(path: Path) -> None:
    path.write_text(textwrap.dedent("""\
        import assert from "node:assert/strict";
        import * as sdkBrowser from "@nsealr/sdk/browser";

        const request = {
          version: 2,
          request_id: "lab-sdk-browser-qr",
          method: "get_public_key"
        };

        assert.equal(sdkBrowser.client.NATIVE_HOST_NAME, sdkBrowser.browserProvider.NATIVE_HOST_NAME);
        assert.equal(sdkBrowser.protocol.validateRequest(request).ok, true);
        assert.equal(sdkBrowser.qr.encodeQrEnvelope(request).startsWith("nsealr1:"), true);
        assert.deepEqual(sdkBrowser.qr.decodeQrEnvelope(sdkBrowser.qr.encodeQrEnvelope(request)), request);
        assert.equal(sdkBrowser.core.computeEventId({
          pubkey: "0".repeat(64),
          created_at: 1,
          kind: 1,
          tags: [],
          content: "lab sdk browser"
        }).length, 64);

        for (const forbidden of ["fixtures", "framing", "nip46", "smartcard", "transport"]) {
          assert.equal(forbidden in sdkBrowser, false, `${forbidden} must stay out of @nsealr/sdk/browser`);
        }

        console.log("nSealr browser-safe SDK facade integration passed");
        """), encoding="utf-8")


def main() -> int:
    if not COMPANION.exists():
        raise FileNotFoundError(f"missing product component: {COMPANION}")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)
    command = build_browser_runtime_imports_command(companion=COMPANION)
    run_command(command.argv, command.cwd)

    script_cache_dir = COMPANION / "packages" / "sdk" / ".tmp" / "nsealr-lab"
    script_cache_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="sdk-browser-", dir=script_cache_dir) as script_dir:
        script_path = Path(script_dir) / "sdk-browser.mjs"
        write_sdk_browser_script(script_path)
        command = build_sdk_browser_command(companion=COMPANION, script_path=script_path)
        run_command(command.argv, command.cwd)

    for directory in (script_cache_dir, script_cache_dir.parent):
        try:
            directory.rmdir()
        except OSError:
            pass

    run_command(["pnpm", "pack-smoke"], COMPANION)
    print("nSealr integrated browser-safe SDK facade and isolated packed SDK verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
