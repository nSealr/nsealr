import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import {
  clientIdForIdentity, handleLocalServiceRequestAsync,
  type LocalServiceContext, type SignerCompatibilitySnapshot
} from "@nsealr/client";
import { parseAccountDescriptor } from "@nsealr/policy";
import { compactReportedCapabilities, parseImplementationProfile, parseLimitsManifest, type FullCapabilities } from "@nsealr/protocol";
import * as qr from "@nsealr/qr";
import { resolveSpecsRoot } from "@nsealr/fixtures";
import {
  createManualQrRouteDispatcher, type ManualQrPort, type ManualQrPortControl
} from "./manual-qr.js";

const specs = resolveSpecsRoot();
const load = (path: string) => JSON.parse(readFileSync(resolve(specs, path), "utf8"));
const manifestCases = load("vectors/profile-capabilities/cases-v1.json");
// Independent pre-existing public signed response; no host signing key/operation.
const signedRequest = load("examples/request-kind-1-basic.json");
const signedResponse = load("examples/response-kind-1-basic.json");
const publicRequest = load("examples/request-get-public-key.json");
const publicResponse = load("examples/response-get-public-key.json");
const rawQr = (value: unknown) => `nsealr1:${Buffer.from(JSON.stringify(value)).toString("base64url")}`;
const client = { surface: "cli" as const, origin: "app:qh01-manual-fixture", app_name: "QH01 public software fixture" };
function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function setup(method: "get_public_key" | "sign_event" = "get_public_key") {
  const request = structuredClone(method === "sign_event" ? signedRequest : publicRequest);
  const response = structuredClone(method === "sign_event" ? signedResponse : publicResponse);
  const implementation = parseImplementationProfile(load(manifestCases.implementation_examples.pi_qr));
  const adapter = structuredClone(implementation);
  const { conformance_only: _, ...data } = structuredClone(implementation);
  const reported: FullCapabilities = { ...data, format: "nsealr.capabilities.v1", form: "full" };
  for (const source of [adapter, reported]) for (const entry of source.methods) {
    Object.assign(entry, { configuration: "configured", availability: "available", reason: null });
  }
  const limits = parseLimitsManifest(structuredClone(manifestCases.limits_manifest));
  const snapshot: SignerCompatibilitySnapshot = {
    implementation, adapter, reported, limits, adapter_limits: structuredClone(limits),
    connection_id: "qh01.synthetic.connection", generation: 1,
    review_plan: { request_sha256: createHash("sha256").update(JSON.stringify(request)).digest("hex"),
      implementation_id: implementation.implementation_id, connection_id: "qh01.synthetic.connection", generation: 1,
      context_id: "qh01.synthetic.no-consent", geometry_id: "qh01.unqualified.fixture", pages: 7 }
  };
  const account = parseAccountDescriptor(load("vectors/accounts/raspberry-qr-nip06-account-0.json"));
  // Routing metadata for this independently signed fixture, not NIP06/custody proof.
  account.public_key = publicResponse.result.public_key;
  let now = 0, opens = 0, scans = 0, closes = 0;
  let controls!: ManualQrPortControl;
  let openHook: ((control: ManualQrPortControl) => ManualQrPort | Promise<ManualQrPort>) | undefined;
  let closeHook: (() => void | Promise<void>) | undefined;
  let scanned: string | null = rawQr(response);
  const presented: string[] = [];
  const port = (control: ManualQrPortControl): ManualQrPort => ({
    present: (envelope) => { control.before_present(); presented.push(envelope); },
    scan: async () => { scans++; return scanned; },
    close: async () => { closes++; await closeHook?.(); }
  });
  const dispatcher = createManualQrRouteDispatcher({
    account_id: account.account_id, route_type: "raspberry_qr_vault",
    openPort: async (control) => { opens++; controls = control; return openHook ? await openHook(control) : port(control); }
  });
  const context: LocalServiceContext = {
    accounts: [account], now: 1, monotonicNow: () => now,
    grants: [{ client_id: clientIdForIdentity(client), origin: client.origin, surface: client.surface,
      allowed_operations: ["dispatch_signer_request"] }],
    signerCompatibility: () => snapshot, signerDispatcher: dispatcher
  };
  const envelope = { version: 1 as const, request_id: "qh01.local.fixture", operation: "dispatch_signer_request" as const,
    params: { client, route_request: { account_id: account.account_id, method }, request } };
  return { context, envelope, account, snapshot, request, response, presented, port,
    get counts() { return { opens, scans, closes }; }, get controls() { return controls; },
    set now(value: number) { now = value; }, set scanned(value: string | null) { scanned = value; },
    set openHook(value: typeof openHook) { openHook = value; }, set closeHook(value: typeof closeHook) { closeHook = value; } };
}
const run = (state: ReturnType<typeof setup>) => handleLocalServiceRequestAsync(state.envelope, state.context);
const errorResponse = (state: ReturnType<typeof setup>, padding = 200) => ({ version: 2,
  request_id: state.request.request_id, ok: false,
  error: { code: "user_rejected", message: "x".repeat(padding), retryable: false } });

describe("service manual QR port through the existing client lifecycle", () => {
  it.each(["get_public_key", "sign_event"] as const)("exchanges public%s with exact account/request/key and independent response verification", async (method) => {
    const state = setup(method);
    expect(await run(state)).toMatchObject({ ok: true, result: { signer_response: state.response } });
    expect(state.presented).toEqual([rawQr(state.request)]);
    expect(state.counts).toEqual({ opens: 1, scans: 1, closes: 1 });
    expect(state.controls).toMatchObject({ account_id: state.account.account_id, route_type: "raspberry_qr_vault",
      request_id: state.request.request_id, expected_public_key: state.account.public_key });
    expect(() => state.controls.before_present()).toThrow();
  });

  it("refuses another configured account instead of falling back to this port", async () => {
    const state = setup(); const other = structuredClone(state.account); other.account_id = "different-qr-account";
    state.context.accounts!.push(other); state.envelope.params.route_request.account_id = other.account_id;
    expect(await run(state)).toMatchObject({ ok: false, error: { code: "signer_route_unavailable" } });
    expect(state.counts.opens).toBe(0);
  });

  it.each(["before_write", "effective_limits", "abort_signal"] as const)("refuses a dispatch without the existing lifecycle%s binding", async (missing) => {
    const state = setup(); const actual = state.context.signerDispatcher!;
    state.context.signerDispatcher = (dispatch) => {
      const incomplete = { ...dispatch }; delete incomplete[missing]; return actual(incomplete);
    };
    expect(await run(state)).toMatchObject({ ok: false, error: { code: "signer_route_unavailable" } });
    expect(state.counts.opens).toBe(0);
  });

  it.each(["request-id", "public-key", "template", "canonical-id", "signature"])("rejects independent response fault:%s", async (fault) => {
    const state = setup(fault === "public-key" ? "get_public_key" : "sign_event");
    if (fault === "request-id") state.response.request_id = "a-previous-request";
    else if (fault === "public-key") state.response.result.public_key = "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9";
    else if (fault === "template") state.response.result.event.content += "changed";
    else if (fault === "canonical-id") state.response.result.event.id = "0".repeat(64);
    else state.response.result.event.sig = "0".repeat(128);
    state.scanned = rawQr(state.response);
    expect(await run(state)).toMatchObject({ ok: false, error: { code: "invalid_signer_response" } });
    expect(state.counts).toEqual({ opens: 1, scans: 1, closes: 1 });
  });

  it.each(["account", "generation", "availability", "limits", "deadline"])("revalidates after opening immediately before actual presentation:%s", async (change) => {
    const state = setup();
    state.openHook = (control) => {
      if (change === "account") state.account.public_key = "0".repeat(64);
      else if (change === "generation") state.snapshot.generation++;
      else if (change === "availability") Object.assign(state.snapshot.adapter.methods[1], { availability: "unavailable", reason: "provider_missing" });
      else if (change === "limits") state.snapshot.adapter_limits.methods[1].response_json_bytes--;
      else state.now = 100;
      return state.port(control);
    };
    expect((await run(state)).ok).toBe(false); expect(state.presented).toEqual([]);
    expect(state.counts).toEqual({ opens: 1, scans: 0, closes: 1 });
  });

  it.each([99, 100, 101])("honors actual client's exact monotonic boundary%d before presentation", async (now) => {
    const state = setup(); state.openHook = (control) => { state.now = now; return state.port(control); };
    expect((await run(state)).ok).toBe(now < 100);
    expect(state.presented.length).toBe(now < 100 ? 1 : 0);
  });

  it.each(["frame", "decoded", "response", "reassembly", "work"])("rejects actual scanned%s overflow before QR conversion", async (dimension) => {
    const state = setup(); const raw = rawQr(errorResponse(state)); state.scanned = raw;
    const method = state.snapshot.adapter_limits.methods[1];
    const transport = state.snapshot.adapter_limits.transports.find((entry) => entry.transport_id === "qr")!;
    if (dimension === "frame") transport.frame_bytes = rawQr(state.response).length;
    else if (dimension === "decoded") transport.static_decoded_json_bytes = JSON.stringify(state.response).length;
    else if (dimension === "response") method.response_json_bytes = JSON.stringify(state.response).length;
    else if (dimension === "reassembly") transport.reassembly_bytes = JSON.stringify(state.response).length;
    else method.parse_work = rawQr(state.request).length + raw.length - 1;
    const decode = vi.spyOn(qr, "decodeQrEnvelope");
    try {
      expect(await run(state)).toMatchObject({ ok: false, error: { code: "signer_transport_protocol_error" } });
      expect(decode).not.toHaveBeenCalled(); expect(state.counts).toEqual({ opens: 1, scans: 1, closes: 1 });
    } finally { decode.mockRestore(); }
  });

  it.each([-1, 0, 1])("reserves explicit logical payload buffers before opening:capacity delta%d", async (delta) => {
    const state = setup();
    const needed = JSON.stringify(state.request).length + rawQr(state.request).length + 704 + 947;
    state.snapshot.adapter_limits.methods[1].retained_bytes = needed + delta;
    const result = await run(state);
    expect(result.ok).toBe(delta >= 0); expect(state.counts.opens).toBe(delta < 0 ? 0 : 1);
  });

  it.each(["frame", "decoded", "response", "reassembly", "work"].flatMap((dimension) =>
    [-1, 0, 1].map((delta) => ({ dimension, delta }))))("bounds the actual error response at $dimension capacity delta$delta", async ({ dimension, delta }) => {
    const state = setup(); const peerError = errorResponse(state);
    const jsonBytes = Buffer.byteLength(JSON.stringify(peerError), "utf8");
    const raw = rawQr(peerError); state.scanned = raw;
    const method = state.snapshot.adapter_limits.methods[1];
    const transport = state.snapshot.adapter_limits.transports.find((entry) => entry.transport_id === "qr")!;
    if (dimension === "frame") transport.frame_bytes = raw.length + delta;
    else if (dimension === "decoded") transport.static_decoded_json_bytes = jsonBytes + delta;
    else if (dimension === "response") method.response_json_bytes = jsonBytes + delta;
    else if (dimension === "reassembly") transport.reassembly_bytes = jsonBytes + delta;
    else method.parse_work = rawQr(state.request).length + raw.length + delta;
    const decode = vi.spyOn(qr, "decodeQrEnvelope");
    try {
      const result = await run(state);
      if (delta < 0) {
        expect(result).toMatchObject({ ok: false, error: { code: "signer_transport_protocol_error" } });
        expect(decode).not.toHaveBeenCalled();
      } else {
        expect(result).toMatchObject({ ok: true, result: { signer_response: peerError } });
        expect(decode).toHaveBeenCalledTimes(1);
      }
      // Client's independently planned public-key response fits every row.
      // Thus the actual scanned-response boundary is exercised after opening.
      expect(state.counts).toEqual({ opens: 1, scans: 1, closes: 1 });
    } finally { decode.mockRestore(); }
  });

  it("requires the trusted delayed presenter to revalidate at the actual effect", async () => {
    const state = setup();
    state.openHook = (control) => ({ ...state.port(control), present: async (envelope) => {
      await Promise.resolve(); state.snapshot.generation++;
      control.before_present(); state.presented.push(envelope);
    } });
    expect(await run(state)).toMatchObject({ ok: false, error: { code: "runtime_unavailable" } });
    expect(state.presented).toEqual([]);
    expect(state.counts).toEqual({ opens: 1, scans: 0, closes: 1 });
  });

  it("discards an uncooperative late scan before decoding original bytes", async () => {
    vi.useFakeTimers(); const decode = vi.spyOn(qr, "decodeQrEnvelope");
    try {
      const state = setup(); const entered = deferred<void>(); const finish = deferred<string>();
      state.openHook = (control) => ({ ...state.port(control), scan: async () => {
        entered.resolve(); return await finish.promise;
      } });
      const operation = run(state); await entered.promise;
      await vi.advanceTimersByTimeAsync(100);
      expect(await operation).toMatchObject({ ok: false, error: { code: "signer_transport_timeout" } });
      finish.resolve("not-a-valid-or-current-envelope"); await vi.advanceTimersByTimeAsync(0);
      expect(decode).not.toHaveBeenCalled(); expect(state.counts.closes).toBe(1);
    } finally { decode.mockRestore(); vi.useRealTimers(); }
  });

  it("uses one terminal scan, with no repeated-scan retry or cached approval", async () => {
    const state = setup(); const previous = { ...state.response, request_id: "old-operation" }; let reads = 0;
    state.openHook = (control) => ({ ...state.port(control), scan: async () => {
      reads++; return reads === 1 ? rawQr(previous) : rawQr(state.response);
    } });
    expect(await run(state)).toMatchObject({ ok: false, error: { code: "invalid_signer_response" } });
    expect(reads).toBe(1); expect(state.counts.closes).toBe(1);
  });

  it("preserves duplicate evidence in original scanned bytes instead of reserializing a dictionary", async () => {
    const state = setup();
    const raw = JSON.stringify(state.response).replace('"ok":true', '"ok":true,"\\u006fk":true');
    state.scanned = `nsealr1:${Buffer.from(raw).toString("base64url")}`;
    expect(await run(state)).toMatchObject({ ok: false, error: { code: "signer_transport_protocol_error" } });
    expect(state.counts).toEqual({ opens: 1, scans: 1, closes: 1 });
  });

  it("does not turn operator scan cancellation or peer rejection into consent", async () => {
    const state = setup(); state.scanned = null;
    expect(await run(state)).toMatchObject({ ok: false, error: { code: "signer_transport_failed" } });
    state.scanned = rawQr(errorResponse(state, 1));
    expect(await run(state)).toMatchObject({ ok: true, result: { signer_response: { ok: false } } });
    expect(state.counts).toEqual({ opens: 2, scans: 2, closes: 2 });
  });

  it("refuses unsupported discovery and unadmitted message work before opening", async () => {
    const discovery = setup();
    discovery.snapshot.reported = compactReportedCapabilities(discovery.snapshot.reported as FullCapabilities,
      discovery.snapshot.implementation, 704);
    const request = { version: 2, request_id: "unsupported-manual-discovery", method: "get_capabilities" };
    const envelope = { ...discovery.envelope, params: { ...discovery.envelope.params,
      route_request: { account_id: discovery.account.account_id, method: "get_capabilities" }, request } };
    expect(await handleLocalServiceRequestAsync(envelope, discovery.context)).toMatchObject({ ok: false });
    expect(discovery.counts.opens).toBe(0);
    const message = setup("sign_event"); message.request.params.event_template.kind = 4;
    expect(await run(message)).toMatchObject({ ok: false, error: { code: "workflow_not_admitted" } });
    expect(message.counts.opens).toBe(0);
  });

  it.each(["open", "present", "scan", "close"])("keeps adapter and existing pending reservation through an uncooperative%s promise", async (phase) => {
    vi.useFakeTimers();
    try {
      const state = setup(); const entered = deferred<void>(); const finish = deferred<void>();
      state.openHook = async (control) => {
        if (phase === "open") { entered.resolve(); await finish.promise; }
        const port = state.port(control);
        return {
          present: async (envelope) => { if (phase === "present") { entered.resolve(); await finish.promise; } await port.present(envelope); },
          scan: async () => { if (phase === "scan") { entered.resolve(); await finish.promise; } return await port.scan(); },
          close: async () => { if (phase === "close") { entered.resolve(); await finish.promise; } await port.close(); }
        };
      };
      const operation = run(state); await entered.promise;
      await vi.advanceTimersByTimeAsync(100);
      expect(await operation).toMatchObject({ ok: false, error: { code: "signer_transport_timeout" } });
      expect(state.controls.abort_signal.aborted).toBe(true);
      expect(await run(state)).toMatchObject({ ok: false, error: { code: "runtime_unavailable" } });
      const separateContext = { ...state.context };
      expect(await handleLocalServiceRequestAsync(state.envelope, separateContext)).toMatchObject({ ok: false, error: { code: "signer_transport_failed" } });
      expect(state.counts.opens).toBe(1);
      finish.resolve(); await vi.advanceTimersByTimeAsync(0);
      expect(() => state.controls.before_present()).toThrow();
      state.openHook = undefined;
      expect((await run(state)).ok).toBe(true);
      expect(state.counts.opens).toBe(2);
    } finally { vi.useRealTimers(); }
  });

  it.each([false, true])("quarantines the port when cleanup rejects, preserving a primary failure:%s", async (primaryFailure) => {
    const state = setup(); state.closeHook = async () => { throw new Error("unqualified cleanup failure"); };
    if (primaryFailure) state.scanned = "not-an-operation-QR";
    expect(await run(state)).toMatchObject({ ok: false, error: { code: primaryFailure ? "signer_transport_protocol_error" : "signer_transport_close_failed" } });
    state.closeHook = undefined;
    expect(await run(state)).toMatchObject({ ok: false, error: { code: "signer_transport_failed" } });
    expect(state.counts.opens).toBe(1);
  });

  it("does not infer reusable hardware from an opener rejection with unknown partial effects", async () => {
    const state = setup(); state.openHook = async () => { throw new Error("open failed without quiescence proof"); };
    expect(await run(state)).toMatchObject({ ok: false, error: { code: "signer_transport_open_failed" } });
    state.openHook = undefined;
    expect(await run(state)).toMatchObject({ ok: false, error: { code: "signer_transport_failed" } });
    expect(state.counts.opens).toBe(1);
  });

  it("reserves the factory before currentness callbacks can reenter through another actual client context", async () => {
    const state = setup(); const actualDispatch = state.context.signerDispatcher!;
    const actualProvider = state.context.signerCompatibility!;
    const entered = deferred<void>(), finish = deferred<void>();
    let insideAdapter = false, triggered = false;
    let nested: ReturnType<typeof handleLocalServiceRequestAsync> | undefined;
    state.context.signerDispatcher = (dispatch) => {
      insideAdapter = true;
      try { return actualDispatch(dispatch); }
      finally { insideAdapter = false; }
    };
    state.context.signerCompatibility = (route, request) => {
      // Preflight provider calls are outside the adapter. Reenter only from
      // its currentness callback; a separate context bypasses context-local
      // pending capacity but must never bypass the physical factory owner.
      if (insideAdapter && !triggered) {
        triggered = true;
        nested = handleLocalServiceRequestAsync(state.envelope, { ...state.context });
      }
      return actualProvider(route, request);
    };
    state.openHook = async (control) => { entered.resolve(); await finish.promise; return state.port(control); };
    const outer = run(state);
    try {
      await entered.promise;
      expect(triggered).toBe(true); expect(nested).toBeDefined();
      expect(state.counts.opens).toBe(1);
    } finally {
      finish.resolve();
      await Promise.allSettled([outer, nested]);
    }
    expect(await nested).toMatchObject({ ok: false, error: { code: "signer_transport_failed" } });
    expect((await outer).ok).toBe(true);
    state.openHook = undefined;
    expect((await run(state)).ok).toBe(true);
    expect(state.counts.opens).toBe(2);
  });

  it.each(["currentness", "retention"])("releases the owner after a pre-open%s rejection", async (failure) => {
    const state = setup(); const actualDispatch = state.context.signerDispatcher!;
    const retained = state.snapshot.adapter_limits.methods[1].retained_bytes;
    if (failure === "currentness") state.context.signerDispatcher = (dispatch) => actualDispatch({ ...dispatch,
      before_write: () => { throw new Error("synthetic host currentness failure"); } });
    else state.snapshot.adapter_limits.methods[1].retained_bytes = 1;
    expect((await run(state)).ok).toBe(false); expect(state.counts.opens).toBe(0);
    state.context.signerDispatcher = actualDispatch;
    state.snapshot.adapter_limits.methods[1].retained_bytes = retained;
    expect((await run(state)).ok).toBe(true);
    expect(state.counts).toEqual({ opens: 1, scans: 1, closes: 1 });
  });
});
