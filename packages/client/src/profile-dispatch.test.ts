import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { resolveSpecsRoot } from "@nsealr/fixtures";
import { encodeSerialFrame } from "@nsealr/framing";
import { encodeQrEnvelope } from "@nsealr/qr";
import { parseAccountDescriptor, selectAccountRoute } from "@nsealr/policy";
import { parseImplementationProfile, parseLimitsManifest, type FullCapabilities } from "@nsealr/protocol";
import {
  assessSignerCompatibility, clientIdForIdentity, createRouteDispatcher,
  handleLocalServiceRequestAsync, type LocalServiceContext,
  type SignerCompatibilitySnapshot, type SignerDispatchRequest
} from "./service.js";

const root = resolveSpecsRoot();
const load = (path: string) => JSON.parse(readFileSync(resolve(root, path), "utf8"));
const cases = load("vectors/profile-capabilities/cases-v1.json");
const request = load("examples/request-kind-1-basic.json"), response = load("examples/response-kind-1-basic.json");
const client = { surface: "cli" as const, origin: "app:t01-conformance", app_name: "T01 recording adapter" };
function snapshot(profile = "esp32_no_se"): SignerCompatibilitySnapshot {
  const implementation = parseImplementationProfile(load(cases.implementation_examples[profile]));
  const adapter = structuredClone(implementation);
  const { conformance_only: _, ...data } = structuredClone(implementation);
  const reported: FullCapabilities = { ...data, format: "nsealr.capabilities.v1", form: "full" };
  for (const source of [adapter, reported]) for (const method of source.methods) {
    Object.assign(method, { configuration: "configured", availability: "available", reason: null });
  }
  const limits = parseLimitsManifest(structuredClone(cases.limits_manifest));
  return { implementation, adapter, reported, limits, adapter_limits: structuredClone(limits), connection_id: "conformance.connection.1", generation: 1 };
}
function setup(profile = "esp32_no_se") {
  const account = parseAccountDescriptor(load(profile === "pi_qr" ? "vectors/accounts/raspberry-qr-nip06-account-0.json" : "vectors/accounts/esp32-usb-device-slot-0.json"));
  // This is synthetic routing metadata for the same fixed independent signed
  // event, not proof of NIP06 derivation/recovery or attached Pi custody.
  if (profile === "pi_qr") account.public_key = response.result.event.pubkey;
  let live = snapshot(profile), now = 0;
  const writes: string[] = [];
  let beforeWrite: ((dispatch: SignerDispatchRequest) => void | Promise<void>) | undefined;
  let captured: SignerDispatchRequest | undefined;
  const context: LocalServiceContext = {
    accounts: [account],
    grants: [{ client_id: clientIdForIdentity(client), origin: client.origin, surface: client.surface, allowed_operations: ["dispatch_signer_request"] }],
    now: 1, monotonicNow: () => now, signerCompatibility: () => live,
    signerDispatcher: createRouteDispatcher([{ account_id: account.account_id, dispatch: async (dispatch) => {
      captured = dispatch;
      await beforeWrite?.(dispatch);
      dispatch.before_write?.();
      writes.push(profile === "pi_qr" ? encodeQrEnvelope(dispatch.request) : encodeSerialFrame({ type: "request", payload: dispatch.request }));
      return structuredClone(response);
    } }])
  };
  const envelope = {
    version: 1 as const, request_id: "local.t01", operation: "dispatch_signer_request" as const,
    params: { client, route_request: { account_id: account.account_id, method: "sign_event" }, request: structuredClone(request) }
  };
  return { account, context, envelope, writes, get live() { return live; }, set live(value) { live = value; }, set now(value: number) { now = value; }, set beforeWrite(value: typeof beforeWrite) { beforeWrite = value; }, get captured() { return captured; } };
}

describe("actual local service to recording adapter compatibility", () => {
  it("R-01: dispatches exact USB semantics through the service and verifies the independent signed response", async () => {
    const state = setup();
    const result = await handleLocalServiceRequestAsync(state.envelope, state.context);
    expect(result).toMatchObject({ ok: true, result: { signer_response: response } });
    expect(state.writes).toEqual([encodeSerialFrame({ type: "request", payload: request })]);
    expect(state.captured!.effective_limits!.method.content_utf8_bytes).toBe(512);
  });

  it("R-02: equivalent QR operation uses volatile custody and its own lower finite deadline", async () => {
    const state = setup("pi_qr");
    state.live.adapter_limits.methods.find((method) => method.method_id === "sign_event")!.deadline_ms = 50;
    const result = await handleLocalServiceRequestAsync(state.envelope, state.context);
    expect(result).toMatchObject({ ok: true });
    expect(state.writes).toEqual([encodeQrEnvelope(request)]);
    expect(state.captured!.route_selection.custody).toBe("volatile_session");
    expect(state.captured!.effective_limits!.method.deadline_ms).toBe(50);
  });

  it("R-03: each requested semantic mismatch rejects with zero operation writes and no fallback", async () => {
    const mutations = {
      account_id: "unknown", profile: "pi_qr", implementation_id: "unknown",
      contract: "nsealr.signing.v0", method_revision: 2, operation_id: "unknown.catalog",
      algorithm_id: "nip44.v2", custody: "volatile_session", transport: "qr",
      codec_id: "unknown.codec", limits_id: "unknown.limits"
    };
    for (const [key, value] of Object.entries(mutations)) {
      const state = setup(); Object.assign(state.envelope.params.route_request, { [key]: value });
      expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(false);
      expect(state.writes).toHaveLength(0);
    }
  });

  it("R-04: reported availability/huge remote limits cannot raise local method or frame caps", async () => {
    const state = setup();
    state.live.limits.methods.find((method) => method.method_id === "sign_event")!.content_utf8_bytes = Number.MAX_SAFE_INTEGER;
    state.live.adapter_limits.methods.find((method) => method.method_id === "sign_event")!.content_utf8_bytes = 8;
    expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(false);
    expect(state.writes).toHaveLength(0);
    const unknown = setup(); unknown.live.reported.implementation_id = "unknown";
    expect((await handleLocalServiceRequestAsync(unknown.envelope, unknown.context)).ok).toBe(false);
    expect(unknown.writes).toHaveLength(0);
  });

  it("A-05/R-05: changed account, capability/provider, connection or limits between selection and write invalidate the operation", async () => {
    for (const mutate of [
      (state: ReturnType<typeof setup>) => { state.context.accounts![0].public_key = "79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"; },
      (state: ReturnType<typeof setup>) => { Object.assign(state.live.adapter.methods[2], { availability: "unavailable", reason: "provider_missing" }); },
      (state: ReturnType<typeof setup>) => { state.live.generation++; },
      (state: ReturnType<typeof setup>) => { state.live.connection_id = "different.connection"; },
      (state: ReturnType<typeof setup>) => { state.live.limits.methods[2].deadline_ms--; }
    ]) {
      const state = setup(); state.beforeWrite = () => mutate(state);
      expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(false);
      expect(state.writes).toHaveLength(0);
      expect(() => state.captured?.before_write?.()).toThrow(/no longer active/);
    }
  });

  it("A-04/R-06: expected-user/request/canonical-ID/signature verification remains mandatory", async () => {
    for (const key of ["request_id", "pubkey", "id", "sig"]) {
      const state = setup();
      state.context.signerDispatcher = (dispatch) => {
        dispatch.before_write?.();
        const changed = structuredClone(response);
        if (key === "request_id") changed.request_id = "different.request";
        else changed.result.event[key] = "0".repeat(key === "sig" ? 128 : 64);
        return changed;
      };
      expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(false);
    }
  });

  it("L-01/L-02: missing local observations fail closed; exact input bounds do not truncate", async () => {
    const missing = setup(); delete missing.context.signerCompatibility;
    expect((await handleLocalServiceRequestAsync(missing.envelope, missing.context)).ok).toBe(false);
    expect(missing.writes).toHaveLength(0);
    for (const delta of [-1, 0, 1]) {
      const state = setup();
      const length = Buffer.byteLength(request.params.event_template.content, "utf8");
      state.live.adapter_limits.methods.find((method) => method.method_id === "sign_event")!.content_utf8_bytes = length + delta;
      const result = await handleLocalServiceRequestAsync(state.envelope, state.context);
      expect(result.ok).toBe(delta >= 0);
      expect(state.envelope.params.request).toEqual(request);
      expect(state.writes.length).toBe(delta >= 0 ? 1 : 0);
    }
  });

  it("L-04/L-06: exact expiry, rollback and missing clocks refuse writes and release pending state", async () => {
    for (const time of [99, 100, 101]) {
      const state = setup(); state.beforeWrite = () => { state.now = time; };
      expect(await handleLocalServiceRequestAsync(state.envelope, state.context)).toMatchObject({ ok: time < 100 });
      expect(state.writes.length).toBe(time < 100 ? 1 : 0);
    }
    for (const bad of [undefined, Number.MAX_SAFE_INTEGER, -1]) {
      const state = setup(); state.context.monotonicNow = () => bad;
      expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(false);
      expect(state.writes).toHaveLength(0);
    }
    const rollback = setup(); let reads = 0;
    rollback.context.monotonicNow = () => ++reads === 1 ? 10 : 9;
    expect((await handleLocalServiceRequestAsync(rollback.envelope, rollback.context)).ok).toBe(false);
    expect(rollback.writes).toHaveLength(0);
    rollback.context.monotonicNow = () => 0;
    expect((await handleLocalServiceRequestAsync(rollback.envelope, rollback.context)).ok).toBe(true);
  });

  it("L-04: bounded pending operations reject a flood and recover after completion", async () => {
    const state = setup(); let resume!: () => void;
    state.beforeWrite = () => new Promise<void>((resolve) => { resume = resolve; });
    const pending = handleLocalServiceRequestAsync(state.envelope, state.context);
    const second = await handleLocalServiceRequestAsync(state.envelope, state.context);
    expect(second).toMatchObject({ ok: false, error: { code: "runtime_unavailable" } });
    expect(state.writes).toHaveLength(0);
    resume(); expect((await pending).ok).toBe(true);
    state.beforeWrite = undefined;
    expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(true);
  });

  it("P-04/P-05/P-06/P-07: custody, required component and manual-only constraints stay profile-specific", () => {
    const state = setup(), route = selectAccountRoute([state.account], { account_id: state.account.account_id, method: "sign_event" });
    const wrong = structuredClone(state.account); wrong.signer_route.custody = "volatile_session";
    expect(() => parseAccountDescriptor(wrong)).toThrow(/custody_mismatch/);
    wrong.signer_route.custody = "mcu_wrapped_persistent"; wrong.signer_route.policy_support = "scoped_automation";
    expect(() => parseAccountDescriptor(wrong)).toThrow(/manual/);
    const custom = snapshot("custom_board");
    const account = parseAccountDescriptor(load("vectors/accounts/custom-hardware-wallet-slot-0.json"));
    expect(() => assessSignerCompatibility(selectAccountRoute([account], {account_id: account.account_id, method: "sign_event"}), request, custom)).toThrow(/SE configuration/);
    const sameObject = structuredClone(state.live); sameObject.adapter = sameObject.implementation;
    expect(() => assessSignerCompatibility(route, request, sameObject)).toThrow(/unavailable/);
  });
});
