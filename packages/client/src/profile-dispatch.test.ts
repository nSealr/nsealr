import { createHash as independentPlanHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { resolveSpecsRoot } from "@nsealr/fixtures";
import { encodeSerialFrame } from "@nsealr/framing";
import { encodeQrEnvelope } from "@nsealr/qr";
import { parseAccountDescriptor, selectAccountRoute } from "@nsealr/policy";
import { compactReportedCapabilities, parseImplementationProfile, parseLimitsManifest, parseSigningRequest, type FullCapabilities } from "@nsealr/protocol";
import {
  assessSignerCompatibility, clientIdForIdentity, createRouteDispatcher,
  handleLocalServiceRequest, handleLocalServiceRequestAsync, type LocalServiceContext,
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
  return { implementation, adapter, reported, limits, adapter_limits: structuredClone(limits), connection_id: "conformance.connection.1", generation: 1, review_plan: { request_sha256: independentPlanHash("sha256").update(JSON.stringify(request)).digest("hex"), implementation_id: implementation.implementation_id, connection_id: "conformance.connection.1", generation: 1, context_id: "conformance.no-authority", geometry_id: "conformance.recording.synthetic", pages: 7 } };
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

  it("L-01: each actual operation dimension uses independent bytes/counts at below/exact/above boundaries", () => {
    const req = load("examples/request-kind-1-tags.json"), res = load("examples/response-kind-1-tags.json");
    const event = req.params.event_template;
    const jsonBytes = (value: unknown) => Buffer.byteLength(JSON.stringify(value), "utf8");
    const input = jsonBytes(req), output = jsonBytes(res);
    // Fixed wire grammar and independently retained Nostr canonical fixture;
    // no runtime framing/canonical/signing output supplies expected limits.
    const frame = (type: string, value: unknown) => Buffer.byteLength(`nsealr1f:${type}:${Buffer.from(JSON.stringify(value)).toString("base64url")}:0000000000000000\n`);
    const incomingFrame = frame("response", res), outgoingFrame = frame("request", req);
    const dimensions: Array<["method" | "transport", string, number]> = [
      ["method", "request_json_bytes", input], ["method", "response_json_bytes", output],
      ["method", "content_utf8_bytes", Buffer.byteLength(event.content)], ["method", "tag_count", event.tags.length],
      ["method", "tag_fields", Math.max(...event.tags.map((tag: string[]) => tag.length))],
      ["method", "tag_field_utf8_bytes", Math.max(...event.tags.flat().map((field: string) => Buffer.byteLength(field)))],
      ["method", "aggregate_tag_utf8_bytes", event.tags.flat().reduce((sum: number, field: string) => sum + Buffer.byteLength(field), 0)],
      ["method", "canonical_bytes", Buffer.byteLength(load("vectors/events/kind-1-tags.json").canonical_serialization)],
      ["method", "review_pages", 7], ["method", "parse_work", incomingFrame + outgoingFrame],
      ["transport", "frame_bytes", Math.max(incomingFrame, outgoingFrame)], ["transport", "reassembly_bytes", Math.max(input, output)],
      ["transport", "parse_work", incomingFrame + outgoingFrame]
    ];
    for (const [group, field, exact] of dimensions) for (const offset of [-1, 0, 1]) {
      const state = setup();
      state.live.review_plan!.request_sha256 = independentPlanHash("sha256").update(JSON.stringify(req)).digest("hex");
      const row = group === "method" ? state.live.adapter_limits.methods[2] : state.live.adapter_limits.transports[0];
      Object.assign(row, { [field]: exact + offset });
      const route = selectAccountRoute([state.account], { account_id: state.account.account_id, method: "sign_event" });
      if (offset < 0) expect(() => assessSignerCompatibility(route, req, state.live), `${group}.${field}`).toThrow();
      else expect(() => assessSignerCompatibility(route, req, state.live), `${group}.${field}`).not.toThrow();
    }
    const raw = JSON.stringify(request), bytes = Buffer.byteLength(raw);
    expect(parseSigningRequest(" ".repeat(704 - bytes) + raw)).toEqual(request);
    expect(() => parseSigningRequest(" ".repeat(705 - bytes) + raw)).toThrow();
    const multibyte = structuredClone(request); multibyte.params.event_template.content = "é".repeat(256);
    expect(() => parseSigningRequest(JSON.stringify(multibyte))).not.toThrow();
    multibyte.params.event_template.content += "é";
    expect(() => parseSigningRequest(JSON.stringify(multibyte))).toThrow();
  });

  it("L-01/L-05: public-key and exact full/reference discovery responses must fit before any I/O", async () => {
    for (const ceiling of [1, 704]) {
      const state = setup(); const req = load("examples/request-get-public-key.json"), res = load("examples/response-get-public-key.json");
      state.envelope.params.request = req; state.envelope.params.route_request.method = "get_public_key";
      state.live.adapter_limits.methods[1].response_json_bytes = ceiling;
      state.context.signerDispatcher = (dispatch) => { dispatch.before_write!(); state.writes.push("public-key-write"); return res; };
      expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(ceiling !== 1);
      expect(state.writes.length).toBe(ceiling === 1 ? 0 : 1);
    }
    for (const form of ["full", "reference"]) {
      const state = setup(); const req = load("examples/request-get-capabilities.json");
      state.envelope.params.request = req; state.envelope.params.route_request.method = "get_capabilities";
      if (form === "reference") state.live.reported = compactReportedCapabilities(state.live.reported as FullCapabilities, state.live.implementation, 704);
      state.context.signerDispatcher = (dispatch) => { dispatch.before_write!(); state.writes.push("discovery-write"); return { version: 2, request_id: req.request_id, ok: true, result: { capabilities: state.live.reported } }; };
      expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(form === "reference");
      expect(state.writes.length).toBe(form === "reference" ? 1 : 0);
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

  it("L-04/L-06: an unresolved adapter reaches the absolute local deadline and its stale write hook is revoked", async () => {
    vi.useFakeTimers();
    try {
      const state = setup(); let cancelled = false;
      state.context.signerDispatcher = (dispatch) => {
        Object.defineProperty(state, "captured", { value: dispatch });
        dispatch.abort_signal!.addEventListener("abort", () => { cancelled = true; });
        return new Promise(() => undefined);
      };
      const operation = handleLocalServiceRequestAsync(state.envelope, state.context);
      await vi.advanceTimersByTimeAsync(100);
      expect(await operation).toMatchObject({ ok: false, error: { code: "signer_transport_timeout" } });
      expect(cancelled).toBe(true);
      expect(() => state.captured!.before_write!()).toThrow(/no longer active/);
      expect(state.writes).toHaveLength(0);
    } finally { vi.useRealTimers(); }
  });

  it("L-04: a timed-out unsettled adapter keeps its finite slot until actual settlement", async () => {
    vi.useFakeTimers();
    try {
      const state = setup(); const finish: Array<(response: unknown) => void> = []; let calls = 0;
      state.context.signerDispatcher = () => { calls++; return new Promise((resolve) => { finish.push(resolve); }); };
      const pending = handleLocalServiceRequestAsync(state.envelope, state.context);
      await vi.advanceTimersByTimeAsync(100);
      expect(await pending).toMatchObject({ ok: false, error: { code: "signer_transport_timeout" } });
      const retry = handleLocalServiceRequestAsync(state.envelope, state.context);
      expect(calls).toBe(1);
      expect(await retry).toMatchObject({ ok: false, error: { code: "runtime_unavailable" } });
      finish[0](structuredClone(response)); await Promise.resolve(); await Promise.resolve();
      state.context.signerDispatcher = () => structuredClone(response);
      expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(true);
    } finally { vi.useRealTimers(); }
  });

  it("L-04: sync API rejects an async dispatcher while preserving its unsettled slot and revoking writes", async () => {
    const state = setup(); let finish!: (response: unknown) => void; let captured!: SignerDispatchRequest; let calls = 0;
    state.context.signerDispatcher = (dispatch) => { calls++; captured = dispatch; return new Promise((resolve) => { finish = resolve; }); };
    expect(handleLocalServiceRequest(state.envelope, state.context)).toMatchObject({ ok: false, error: { code: "signer_dispatch_failed", message: "async signer dispatcher requires handleLocalServiceRequestAsync" } });
    expect(() => captured.before_write!()).toThrow(/no longer active/);
    expect(handleLocalServiceRequest(state.envelope, state.context)).toMatchObject({ ok: false, error: { code: "runtime_unavailable" } });
    expect(calls).toBe(1);
    finish(structuredClone(response)); await Promise.resolve(); await Promise.resolve();
    state.context.signerDispatcher = () => { throw new Error("settled throw control"); };
    expect(handleLocalServiceRequest(state.envelope, state.context)).toMatchObject({ ok: false, error: { code: "signer_dispatch_failed" } });
    state.context.signerDispatcher = () => structuredClone(response);
    expect(handleLocalServiceRequest(state.envelope, state.context).ok).toBe(true);
    expect(handleLocalServiceRequest(state.envelope, state.context).ok).toBe(true);
  });

  it("observes a late rejection when a synchronous dispatch invalidates its snapshot before returning a promise", async () => {
    const state = setup(); let reject!: (reason: unknown) => void; let captured!: SignerDispatchRequest;
    const unhandled: unknown[] = [];
    const record = (error: unknown) => { unhandled.push(error); };
    process.on("unhandledRejection", record);
    try {
      state.context.signerDispatcher = (dispatch) => {
        captured = dispatch;
        state.live.generation++;
        return new Promise((_resolve, refusal) => { reject = refusal; });
      };
      expect(handleLocalServiceRequest(state.envelope, state.context)).toMatchObject({ ok: false });
      expect(() => captured.before_write!()).toThrow(/no longer active/);
      state.live.generation = 1;
      expect(handleLocalServiceRequest(state.envelope, state.context)).toMatchObject({ ok: false, error: { code: "runtime_unavailable" } });
      reject(new Error("late adapter rejection after snapshot invalidation"));
      await new Promise<void>((resolve) => setImmediate(resolve));
      expect(unhandled).toEqual([]);
      expect(state.writes).toHaveLength(0);
      state.context.signerDispatcher = () => structuredClone(response);
      expect(handleLocalServiceRequest(state.envelope, state.context).ok).toBe(true);
    } finally { process.off("unhandledRejection", record); }
  });

  it("L-01/R-05: complete local review-plan observations bind request, implementation, connection, context and geometry", async () => {
    for (const change of [undefined, { pages: 0 }, { pages: Number.NaN }, { request_sha256: "0".repeat(64) }, { implementation_id: "wrong" }, { connection_id: "wrong" }, { generation: 2 }, { geometry_id: "" }, { context_id: "" }]) {
      const state = setup();
      if (change === undefined) delete state.live.review_plan;
      else Object.assign(state.live.review_plan!, change);
      expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(false);
      expect(state.writes).toHaveLength(0);
    }
    for (const ceiling of [6, 7, 8]) {
      const state = setup(); state.live.adapter_limits.methods[2].review_pages = ceiling;
      expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(ceiling >= 7);
      expect(state.writes.length).toBe(ceiling >= 7 ? 1 : 0);
    }
    for (const change of [{ pages: 8 }, { geometry_id: "changed.geometry" }, { context_id: "changed.context" }]) {
      const state = setup(); state.beforeWrite = () => { Object.assign(state.live.review_plan!, change); };
      expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(false);
      expect(state.writes).toHaveLength(0);
    }
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

  it("P-06/D-05/D-06/D-07: no generic blind-sign or offline message/setup/AUTH fallback is introduced", async () => {
    for (const profile of ["esp32_no_se", "pi_qr"]) for (const kind of [4, 13, 14, 1059, 10050, 22242]) {
      const state = setup(profile); state.envelope.params.request.params.event_template.kind = kind;
      expect(await handleLocalServiceRequestAsync(state.envelope, state.context)).toMatchObject({ ok: false, error: { code: "workflow_not_admitted" } });
      expect(state.writes).toHaveLength(0);
    }
    for (const method of ["nip04_encrypt", "nip04_decrypt", "nip44_encrypt", "nip44_decrypt", "export_conversation_key"]) {
      const state = setup(); Object.assign(state.envelope.params.request, {method});
      state.envelope.params.route_request.method = method;
      expect((await handleLocalServiceRequestAsync(state.envelope, state.context)).ok).toBe(false);
      expect(state.writes).toHaveLength(0);
    }
  });
});
