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
} from "../../../../../../../packages/client/src/service.js";
import { createServiceRouteDispatcher, parseServiceRouteDriverStore } from "../../../../../../../apps/bridge/service/src/drivers.js";

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

// T01-SERVICE-02: actual encoded incoming frame exceeds the intersected
// frame ceiling while the known positive response fits pre-write planning.
{
  const req = load("examples/request-get-public-key.json");
  const positive = load("examples/response-get-public-key.json");
  const framedBytes = (kind: string, value: unknown) => Buffer.byteLength(`nsealr1f:${kind}:${Buffer.from(JSON.stringify(value)).toString("base64url")}:0000000000000000\n`);
  const knownFrameCeiling = Math.max(framedBytes("request", req), framedBytes("response", positive));
  const live = structuredClone(snapshot);
  live.adapter_limits.transports[0].frame_bytes = knownFrameCeiling;
  const actualResponse = { version: 2, request_id: req.request_id, ok: false,
    error: { code: "user_rejected", message: "x".repeat(180), retryable: false } };
  const actualFrame = encodeSerialFrame({ type: "response", payload: actualResponse });
  let writes = 0;
  const dispatcher = createServiceRouteDispatcher(parseServiceRouteDriverStore({
    format: "nsealr-service-route-driver-store-v0", updated_at: 1, contains_secret_material: false,
    routes: [{ account_id: account.account_id, route_type: account.signer_route.type, transport: "usb", driver: "serial_line",
      serial_line: { path: "/dev/cu.usbmodem-review-recording-only", response_timeout_ms: 100 } }]
  }), { openSerialLinePort: () => ({ writeLine: async () => { writes++; }, readLine: async () => actualFrame, close: () => {} }) });
  const context: LocalServiceContext = { accounts: [account], grants: [validGrant], now: 1,
    monotonicNow: () => 0, signerCompatibility: () => live, signerDispatcher: dispatcher };
  const envelope = { version: 1, request_id: "review.frame", operation: "dispatch_signer_request",
    params: { client, route_request: { account_id: account.account_id, method: "get_public_key" }, request: req } };
  const limits = assessSignerCompatibility(selectAccountRoute([account], envelope.params.route_request), req, live);
  assert.equal(limits.transport.frame_bytes, knownFrameCeiling);
  assert.ok(Buffer.byteLength(actualFrame) > knownFrameCeiling);
  assert.ok(Buffer.byteLength(JSON.stringify(actualResponse)) <= limits.method.response_json_bytes);
  const result = await handleLocalServiceRequestAsync(envelope, context);
  assert.equal(result.ok, false); assert.equal(!result.ok && result.error.code, "signer_transport_protocol_error"); assert.equal(writes, 1);
  console.log(JSON.stringify({ finding: "T01-SERVICE-02", known_positive_encoded_frame_fits: knownFrameCeiling,
    effective_frame_bytes: limits.transport.frame_bytes, actual_response_encoded_bytes: Buffer.byteLength(actualFrame),
    actual_response_json_bytes: Buffer.byteLength(JSON.stringify(actualResponse)), response_json_cap: limits.method.response_json_bytes,
    result, operation_writes: writes, defect: "Corrected: actual response frame above effective cap is rejected" }));
}

// T01-SERVICE-03: a sync adapter returns a rejecting promise, then immediate
// current-state rejection skips the only catch attachment after the try/finally.
{
  const live = structuredClone(snapshot); let rejectLater!: (error: Error) => void;
  let captured!: import("../../../../../../../packages/client/src/service.js").SignerDispatchRequest;
  const failures: string[] = [];
  const observer = (error: unknown) => failures.push(error instanceof Error ? error.message : String(error));
  process.on("unhandledRejection", observer);
  try {
    const context: LocalServiceContext = { accounts: [account], grants: [validGrant], now: 1,
      monotonicNow: () => 0, signerCompatibility: () => live,
      signerDispatcher: (dispatch) => { captured = dispatch; live.generation++;
        return new Promise((_resolve, reject) => { rejectLater = reject; }); }
    };
    const envelope = { version: 1, request_id: "review.sync", operation: "dispatch_signer_request",
      params: { client, route_request: { account_id: account.account_id, method: "sign_event" }, request: structuredClone(request) } };
    const result = handleLocalServiceRequest(envelope, context);
    assert.equal(result.ok, false);
    assert.throws(() => captured.before_write!(), /no longer active/);
    rejectLater(new Error("review.public.adapter.rejection"));
    await new Promise<void>((resolve) => setImmediate(resolve));
    await new Promise<void>((resolve) => setImmediate(resolve));
    assert.deepEqual(failures, []);
    console.log(JSON.stringify({ finding: "T01-SERVICE-03", result, revoked_write_hook: true,
      actual_unhandled_rejections: failures, operation_writes: 0,
      observer_role: "Records otherwise default-fatal Node rejection; no production listener installed" }));
  } finally { process.off("unhandledRejection", observer); }
}
