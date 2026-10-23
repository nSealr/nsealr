// Finite public-fixture engineering test. No default route or device readiness.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { clientIdForIdentity, handleLocalServiceRequestAsync, type LocalServiceContext,
  type SignerCompatibilitySnapshot } from "@nsealr/client";
import { parseAccountDescriptor } from "@nsealr/policy";
import { parseImplementationProfile, parseLimitsManifest, type FullCapabilities } from "@nsealr/protocol";
import { createManualQrRouteDispatcher } from "../../../../../apps/bridge/service/src/manual-qr.js";

const root = resolve(fileURLToPath(new URL("../../../../../", import.meta.url)));
const load = (path: string) => JSON.parse(readFileSync(resolve(root, "protocols/contracts/v1", path), "utf8"));
const basic = load("vectors/events/kind-1-basic.json"), tagged = load("vectors/events/kind-1-tags.json");
const amended = JSON.parse(readFileSync(new URL("expectations.json", import.meta.url), "utf8"));
for (const [vector, id] of [[basic, "basic"], [tagged, "tagged"]] as const) {
  const expected = amended.independent_positive_expectations.find((row: any) => row.id === id);
  assert.equal(vector.signature, expected.legacy_verification_reference.signature);
  vector.response.result.event.sig = expected.expected_signature;
  assert.deepEqual(vector.response.result.event, expected.expected_complete_event);
}
const identity = { surface: "cli" as const, origin: "app:qp01-public-fixture", app_name: "QP01 synthetic engineering fixture" };
const qr = (value: unknown) => `nsealr1:${Buffer.from(JSON.stringify(value)).toString("base64url")}`;
const decode = (value: string) => JSON.parse(Buffer.from(value.slice(8), "base64url").toString("utf8"));
let children = 0, collected = 0;
const reports: unknown[] = [];

async function native(frame: string, held?: (release: () => void) => void): Promise<string> {
  assert(Buffer.byteLength(frame) <= 947);
  const python = process.env.NSEALR_QP01_PYTHON;
  assert(python && process.env.NSEALR_QP01_LIBRARY && process.env.NSEALR_QP01_LIBRARY_SHA256);
  const argv = ["-B", resolve(root, "docs/restart/implementation/QP01/request-engine/exchange.py")];
  if (held) argv.push("--settlement-fd", "3");
  const child = spawn(python, argv, { cwd: root, env: process.env, stdio: ["pipe", "pipe", "pipe", "pipe"] });
  const safety = setTimeout(() => child.kill("SIGKILL"), 5000);
  children++;
  const stdout: Buffer[] = [], stderr: Buffer[] = [];
  let out = 0, err = 0, overflow = false, notified = false;
  child.stdout.on("data", (chunk: Buffer) => { out += chunk.length;
    if (out <= 947) stdout.push(chunk); else { overflow = true; child.kill("SIGKILL"); } });
  child.stderr.on("data", (chunk: Buffer) => { err += chunk.length;
    if (err <= 262144) {
      stderr.push(chunk);
      if (held && !notified && chunk.includes(10)) { notified = true;
        held(() => (child.stdio[3] as import("node:stream").Writable).end("R")); }
    } else { overflow = true; child.kill("SIGKILL"); } });
  child.stdin.on("error", () => { /* Actual exit/close below decides failure. */ });
  const ended = new Promise<void>((yes, no) => {
    child.once("error", no);
    child.once("close", (code, signal) => { collected++; clearTimeout(safety);
      if (code === 0 && signal === null && !overflow) yes();
      else no(new Error(`fixture child failed: ${code}/${signal}: ${Buffer.concat(stderr)}`)); });
  });
  child.stdin.end(frame);
  await ended; // Native/callback/process/stream settlement before port.close.
  const response = Buffer.concat(stdout).toString("ascii");
  const trace = JSON.parse(Buffer.concat(stderr).toString("utf8"));
  assert.equal(trace.sha256, process.env.NSEALR_QP01_LIBRARY_SHA256);
  assert.equal(trace.input_sha256, createHash("sha256").update(frame).digest("hex"));
  assert.equal(trace.output_sha256, createHash("sha256").update(response).digest("hex"));
  assert(trace.synthetic_complete_review.length > 1);
  reports.push(trace);
  console.log(JSON.stringify({ native_observation: trace }));
  return response;
}

type Mutation = "account-key" | "request-id" | "template" | "event-id" | "signature";
function setup(vector = basic, mutation?: Mutation, changed?: string, holdChild = false) {
  const cases = load("vectors/profile-capabilities/cases-v1.json");
  const request = structuredClone(vector.request);
  const implementation = parseImplementationProfile(load(cases.implementation_examples.pi_qr));
  const adapter = structuredClone(implementation);
  const { conformance_only: _, ...data } = structuredClone(implementation);
  const reported: FullCapabilities = { ...data, format: "nsealr.capabilities.v1", form: "full" };
  for (const source of [adapter, reported]) for (const entry of source.methods)
    Object.assign(entry, { configuration: "configured", availability: "available", reason: null });
  const limits = parseLimitsManifest(structuredClone(cases.limits_manifest));
  const snapshot: SignerCompatibilitySnapshot = {
    implementation, adapter, reported, limits, adapter_limits: structuredClone(limits),
    connection_id: "qp01.synthetic.connection", generation: 1,
    review_plan: { request_sha256: createHash("sha256").update(JSON.stringify(request)).digest("hex"),
      implementation_id: implementation.implementation_id, connection_id: "qp01.synthetic.connection", generation: 1,
      context_id: "qp01.synthetic.no-consent", geometry_id: "qp01.unqualified.fixture", pages: 7 }
  };
  const account = parseAccountDescriptor(load("vectors/accounts/raspberry-qr-nip06-account-0.json"));
  account.public_key = mutation === "account-key" ? "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9" : vector.signed_event.pubkey;
  let opens = 0, scans = 0, closes = 0, ticks = 0;
  let entered!: (release: () => void) => void, settled!: () => void;
  const held = new Promise<() => void>((yes) => { entered = yes; });
  const settledPromise = new Promise<void>((yes) => { settled = yes; });
  let pending: Promise<string> | undefined;
  const dispatcher = createManualQrRouteDispatcher({ account_id: account.account_id, route_type: "raspberry_qr_vault",
    openPort: async (control) => { opens++;
      return {
        present: (frame) => { control.before_present(); assert.equal(frame, qr(request));
          const input = mutation === "template" ? qr({ ...tagged.request, request_id: request.request_id }) : frame;
          pending = native(input, holdChild ? entered : undefined); holdChild = false; },
        scan: async () => { scans++; assert(pending); let frame = await pending;
          if (mutation && mutation !== "account-key" && mutation !== "template") {
            const response = decode(frame);
            if (mutation === "request-id") response.request_id = "a-valid-different-id";
            if (mutation === "event-id") response.result.event.id = "0".repeat(64);
            if (mutation === "signature") response.result.event.sig = "0".repeat(128);
            frame = qr(response);
          }
          if (changed === "account") account.public_key = "0".repeat(64);
          if (changed === "generation") snapshot.generation++;
          if (changed === "availability") Object.assign(snapshot.adapter.methods[1], { availability: "unavailable", reason: "provider_missing" });
          if (changed === "limits") snapshot.adapter_limits.methods[1].response_json_bytes--;
          if (changed === "deadline") ticks = 100;
          return frame;
        },
        close: async () => { if (pending) await pending; closes++; settled(); }
      };
    }
  });
  const context: LocalServiceContext = { accounts: [account], now: 1, monotonicNow: () => ticks,
    grants: [{ client_id: clientIdForIdentity(identity), origin: identity.origin, surface: identity.surface,
      allowed_operations: ["dispatch_signer_request"] }], signerCompatibility: () => snapshot, signerDispatcher: dispatcher };
  const envelope = { version: 1 as const, request_id: "qp01.local.fixture", operation: "dispatch_signer_request" as const,
    params: { client: identity, route_request: { account_id: account.account_id, method: "sign_event" }, request } };
  return { run: () => handleLocalServiceRequestAsync(envelope, context),
    separate: () => handleLocalServiceRequestAsync(envelope, { ...context }), held, settled: settledPromise,
    counts: () => ({ opens, scans, closes }) };
}

for (const vector of [basic, tagged]) {
  const state = setup(vector);
  const result = await state.run();
  assert.equal(result.ok, true, JSON.stringify(result));
  assert.deepEqual((result as any).result.signer_response, vector.response);
  assert.deepEqual(state.counts(), { opens: 1, scans: 1, closes: 1 });
}
for (const mutation of ["account-key", "request-id", "template", "event-id", "signature"] as const) {
  const state = setup(basic, mutation), result = await state.run();
  assert.equal(result.ok, false);
  assert.equal((result as any).error.code, "invalid_signer_response", JSON.stringify(result));
  assert.deepEqual(state.counts(), { opens: 1, scans: 1, closes: 1 });
}
for (const change of ["account", "generation", "availability", "limits", "deadline"]) {
  const state = setup(basic, undefined, change), result = await state.run();
  assert.equal(result.ok, false, change);
  assert.deepEqual(state.counts(), { opens: 1, scans: 1, closes: 1 });
}
{
  const state = setup(basic, undefined, undefined, true), operation = state.run();
  const release = await state.held;
  try {
    const timedOut = await operation;
    assert.equal((timedOut as any).error.code, "signer_transport_timeout");
    assert.equal((await state.run() as any).error.code, "runtime_unavailable");
    assert.equal((await state.separate() as any).error.code, "signer_transport_failed");
    assert.equal(state.counts().closes, 0);
  } finally {
    release(); await state.settled;
    // close() returning is followed by dispatcher finally/pending-finally;
    // retain the reservation through that actual promise settlement as well.
    await new Promise<void>((yes) => setImmediate(yes));
  }
  const fresh = await state.run();
  assert.equal(fresh.ok, true, JSON.stringify(fresh));
  assert.deepEqual(state.counts(), { opens: 2, scans: 2, closes: 2 });
}
assert.equal(children, collected);
console.log(JSON.stringify({ scope: "actual client + public-fixture host adapter only", positive: 2,
  valid_shape_verifier_negatives: 5, post_native_currentness_negatives: 5,
  actual_unsettled_child_timeout_no_early_reuse_then_fresh: true, children, collected, reports }, null, 2));
