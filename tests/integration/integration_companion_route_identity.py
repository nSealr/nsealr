#!/usr/bin/env python3
"""Verify companion dispatch binds signer responses to the selected route key."""

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
SPECS = ROOT / "protocols/contracts/v1"


@dataclass(frozen=True)
class CommandPlan:
    cwd: Path
    argv: list[str]


def build_route_identity_command(*, companion: Path, script_path: Path, specs: Path) -> CommandPlan:
    return CommandPlan(cwd=companion, argv=["node", str(script_path), str(specs)])


def write_route_identity_script(path: Path) -> None:
    path.write_text(textwrap.dedent("""\
        import assert from "node:assert/strict";
        import { readFileSync } from "node:fs";
        import { createHash } from "node:crypto";
        import { join } from "node:path";
        import { clientIdForIdentity, handleLocalServiceRequest } from "@nsealr/client";

        const specs = process.argv[2];
        if (typeof specs !== "string") throw new Error("missing specs path");
        const readJson = (relativePath) => JSON.parse(readFileSync(join(specs, relativePath), "utf8"));

        const request = readJson("examples/request-kind-1-basic.json");
        const response = readJson("examples/response-kind-1-basic.json");
        const esp32Account = readJson("vectors/accounts/esp32-usb-device-slot-0.json");
        const esp32Route = readJson("vectors/route-selections/esp32-usb-sign-event-slot-0.json").request;
        const wrongRoutePublicKey = "d".repeat(64);
        const client = {
          surface: "browser_extension",
          origin: "https://example.com",
          app_name: "nSealr lab"
        };
        const grant = {
          client_id: clientIdForIdentity(client),
          origin: client.origin,
          surface: client.surface,
          allowed_operations: ["dispatch_signer_request"],
          approved_at: 1900000000,
          expires_at: 2000000000
        };
        // Synthetic recording adapter inputs; no physical/provider qualification.
        const compatibility = (route, exactRequest) => {
          const common = readJson("vectors/profile-capabilities/cases-v1.json");
          const implementation = readJson(common.implementation_examples[route.profile]);
          const adapter = structuredClone(implementation);
          const { conformance_only: _, ...body } = structuredClone(implementation);
          const reported = { ...body, format: "nsealr.capabilities.v1", form: "full" };
          for (const source of [adapter, reported]) for (const method of source.methods) Object.assign(method, { configuration: "configured", availability: "available", reason: null });
          return { implementation, adapter, reported, limits: structuredClone(common.limits_manifest), adapter_limits: structuredClone(common.limits_manifest), connection_id: "conformance.integration.usb", generation: 1,
            review_plan: { request_sha256: createHash("sha256").update(JSON.stringify(exactRequest)).digest("hex"), implementation_id: implementation.implementation_id, connection_id: "conformance.integration.usb", generation: 1, context_id: "conformance.no-authority", geometry_id: "conformance.recording.synthetic", pages: 7 } };
        };
        const context = (account, signerResponse) => ({
          accounts: [account],
          grants: [grant],
          now: 1900000001, monotonicNow: () => 0, signerCompatibility: compatibility,
          signerDispatcher: () => signerResponse
        });
        const dispatch = (requestId, routeRequest, signerRequest, account, signerResponse) => handleLocalServiceRequest({
          version: 1,
          request_id: requestId,
          operation: "dispatch_signer_request",
          params: {
            client,
            route_request: routeRequest,
            request: signerRequest
          }
        }, context(account, signerResponse));

        const matchingSignEvent = dispatch(
          "lab-route-identity-sign-event-ok",
          esp32Route,
          request,
          esp32Account,
          response
        );
        assert.equal(matchingSignEvent.ok, true);

        const wrongRouteAccount = { ...esp32Account, public_key: wrongRoutePublicKey };
        const wrongSignEvent = dispatch(
          "lab-route-identity-sign-event-wrong",
          esp32Route,
          request,
          wrongRouteAccount,
          response
        );
        assert.equal(wrongSignEvent.ok, false);
        assert.equal(wrongSignEvent.error?.code, "invalid_signer_response");
        assert.equal(
          wrongSignEvent.error?.message,
          "signer response public key does not match selected route"
        );

        const publicKeyRequest = {
          version: 2,
          request_id: "lab-route-identity-get-public-key",
          method: "get_public_key"
        };
        const publicKeyRoute = { ...esp32Route, method: "get_public_key" };
        const publicKeyResponse = {
          version: 2,
          request_id: publicKeyRequest.request_id,
          ok: true,
          result: { public_key: response.result.event.pubkey }
        };

        const matchingPublicKey = dispatch(
          "lab-route-identity-get-public-key-ok",
          publicKeyRoute,
          publicKeyRequest,
          esp32Account,
          publicKeyResponse
        );
        assert.equal(matchingPublicKey.ok, true);

        const wrongPublicKey = dispatch(
          "lab-route-identity-get-public-key-wrong",
          publicKeyRoute,
          publicKeyRequest,
          wrongRouteAccount,
          publicKeyResponse
        );
        assert.equal(wrongPublicKey.ok, false);
        assert.equal(wrongPublicKey.error?.code, "invalid_signer_response");
        assert.equal(
          wrongPublicKey.error?.message,
          "signer response public key does not match selected route"
        );

        console.log("nSealr companion selected-route response identity integration passed");
        """), encoding="utf-8")


def main() -> int:
    for repo in (COMPANION, SPECS):
        if not repo.exists():
            raise FileNotFoundError(f"missing product component: {repo}")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)

    script_cache_dir = COMPANION / "packages" / "client" / ".tmp" / "nsealr-lab"
    script_cache_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="route-identity-", dir=script_cache_dir) as script_dir:
        route_identity_script = Path(script_dir) / "route-identity.mjs"
        write_route_identity_script(route_identity_script)
        command = build_route_identity_command(companion=COMPANION, script_path=route_identity_script, specs=SPECS)
        run_command(command.argv, command.cwd)

    for directory in (script_cache_dir, script_cache_dir.parent):
        try:
            directory.rmdir()
        except OSError:
            pass

    print("nSealr integrated companion route identity smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
