import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { encodeSerialFrame } from "@nsealr/framing";
import { parseAccountDescriptor, selectAccountRoute } from "@nsealr/policy";
import {
  assessSignerCompatibility, clientIdForIdentity,
  handleLocalServiceRequest, handleLocalServiceRequestAsync,
  type LocalServiceContext, type SignerCompatibilitySnapshot
} from "../../../../../packages/client/src/service.js";
import { createServiceRouteDispatcher, parseServiceRouteDriverStore } from "../../../../../apps/bridge/service/src/drivers.js";

const root = resolve("protocols/contracts/v1");
const load = (name: string) => JSON.parse(readFileSync(resolve(root, name), "utf8"));
const request = load("examples/request-kind-1-basic.json");
const response = load("examples/response-kind-1-basic.json");
const common = load("vectors/profile-capabilities/cases-v1.json");
const implementation = load(common.implementation_examples.esp32_no_se);
const adapter = structuredClone(implementation);
const { conformance_only: _, ...body } = structuredClone(implementation);
const reported = { ...body, format: "nsealr.capabilities.v1", form: "full" };
for (const source of [adapter, reported]) for (const method of source.methods)
  Object.assign(method, { configuration: "configured", availability: "available", reason: null });
const account = parseAccountDescriptor(load("vectors/accounts/esp32-usb-device-slot-0.json"));
const snapshot: SignerCompatibilitySnapshot = {
  implementation, adapter, reported, limits: structuredClone(common.limits_manifest), adapter_limits: structuredClone(common.limits_manifest),
  connection_id: "review.recording.1", generation: 1,
  review_plan: { request_sha256: createHash("sha256").update(JSON.stringify(request)).digest("hex"),
    implementation_id: implementation.implementation_id, connection_id: "review.recording.1", generation: 1,
    context_id: "review.no-authority", geometry_id: "review.recording.synthetic", pages: 7 }
};
const client = { surface: "cli" as const, origin: "app:review.service", app_name: "Public fixture recording test" };
const validGrant = { client_id: clientIdForIdentity(client), origin: client.origin, surface: client.surface,
  allowed_operations: ["dispatch_signer_request" as const] };
const route = selectAccountRoute([account], { account_id: account.account_id, method: "sign_event" });
const effective = assessSignerCompatibility(route, request, snapshot);
assert.equal(route.public_key, response.result.event.pubkey);
for (const scenario of ["unpaired", "revoked", "expired", "wrong-operation", "authorized"] as const) {
  const writes: string[] = []; let opens = 0, closes = 0;
  const grants = scenario === "unpaired" ? [] : [{ ...validGrant,
    ...(scenario === "revoked" ? { revoked: true } : {}),
    ...(scenario === "expired" ? { expires_at: 0 } : {}),
    ...(scenario === "wrong-operation" ? { allowed_operations: ["validate_signer_request" as const] } : {}) }];
  const dispatcher = createServiceRouteDispatcher(parseServiceRouteDriverStore({
    format: "nsealr-service-route-driver-store-v0", updated_at: 1, contains_secret_material: false,
    routes: [{ account_id: account.account_id, route_type: account.signer_route.type, transport: "usb", driver: "serial_line",
      serial_line: { path: "/review/recording-only", response_timeout_ms: 100 } }]
  }), { openSerialLinePort: () => { opens++; return {
    writeLine: async (line) => { writes.push(line); },
    readLine: async () => encodeSerialFrame({ type: "response", payload: response }),
    close: () => { closes++; }
  }; } });
  const context: LocalServiceContext = { accounts: [account], grants, now: 1,
    monotonicNow: () => 0, signerCompatibility: () => snapshot, signerDispatcher: dispatcher };
  const envelope = { version: 1, request_id: "review.service", operation: "dispatch_signer_request",
    params: { client, route_request: { account_id: account.account_id, method: "sign_event" }, request: structuredClone(request) } };
  // A real async driver through the synchronous API would be rejected as async;
  // only unauthorized variants are needed to establish the early permission gate.
  const sync = scenario === "authorized" ? undefined : handleLocalServiceRequest(envelope, context);
  const beforeAsync = { opens, writes: writes.length };
  const asyncResult = await handleLocalServiceRequestAsync(envelope, context);
  assert.equal(asyncResult.ok, true);
  assert.equal(writes.length, 1);
  if (sync) { assert.equal(sync.ok, false); assert.equal(!sync.ok && sync.error.code, "unauthorized_client"); assert.equal(beforeAsync.writes, 0); }
  console.log(JSON.stringify({ scenario, exact_route_and_local_snapshot_valid: true,
    effective_method_deadline: effective.method.deadline_ms, effective_pending: effective.method.pending_requests,
    sync: sync?.ok === false ? sync.error : null, before_async: beforeAsync,
    async_result_ok: asyncResult.ok, port_opens: opens, operation_writes: writes.length, closes,
    fixture_only: true, physical_or_signing_authority_claimed: false }));
}
