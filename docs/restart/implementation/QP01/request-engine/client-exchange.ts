// Finite public-fixture engineering test. No default route or device readiness.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Readable, Writable } from "node:stream";
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

// One child is initialized before the actual client call. No frame is accepted
// by this preparation function; only controlled present() may send one later.
async function prepareNative(hold = false, env = process.env, syntheticArgv?: string[]) {
  const python = env.NSEALR_QP01_PYTHON;
  assert(python && env.NSEALR_QP01_LIBRARY && env.NSEALR_QP01_LIBRARY_SHA256);
  const argv = syntheticArgv ?? ["-B", resolve(root, "docs/restart/implementation/QP01/request-engine/exchange.py"),
    "--ready-fd", "4", ...(hold ? ["--settlement-fd", "3"] : [])];
  const child = spawn(python, argv, { cwd: root, env, stdio: ["pipe", "pipe", "pipe", "pipe", "pipe"] });
  const spawnedAt = process.hrtime.bigint();
  const safety = setTimeout(() => child.kill("SIGKILL"), 5000);
  children++;
  const stdout: Buffer[] = [], stderr: Buffer[] = [];
  let out = 0, err = 0, overflow = false, notified = false, sent = false, reaped = false, disposing = false;
  let readyBytes = Buffer.alloc(0), readyAt: bigint | undefined, sentAt: bigint | undefined;
  let closedAt: bigint | undefined, spawnError: Error | undefined;
  let held: ((release: () => void) => void) | undefined;
  let releaseHeld: (() => void) | undefined;
  let readyYes!: () => void, readyNo!: (error: Error) => void;
  const ready = new Promise<void>((yes, no) => { readyYes = yes; readyNo = no; });
  // Observe rejection from startup/stream events even before the await below.
  void ready.catch(() => {});
  const readiness = child.stdio[4] as Readable, settlement = child.stdio[3] as Writable;
  child.stdout!.on("data", (chunk: Buffer) => { out += chunk.length;
    if (!sent || out > 947) { overflow = true; child.kill("SIGKILL"); }
    else stdout.push(chunk); });
  child.stderr!.on("data", (chunk: Buffer) => { err += chunk.length;
    if (err <= 262144) {
      stderr.push(chunk);
      if (held && !notified && chunk.includes(10)) { notified = true;
        let released = false;
        releaseHeld = () => { if (!released) { released = true; settlement.end("R"); } };
        held(releaseHeld);
        if (disposing) releaseHeld();
      }
    } else { overflow = true; child.kill("SIGKILL"); } });
  readiness.on("data", (chunk: Buffer) => {
    if (readyBytes.length + chunk.length > 1 || chunk.toString("ascii") !== "R") {
      readyNo(new Error("invalid readiness token")); child.kill("SIGKILL");
    } else readyBytes = Buffer.concat([readyBytes, chunk]);
  });
  readiness.on("end", () => {
    if (readyBytes.equals(Buffer.from("R")) && !reaped && !overflow && err === 0) {
      readyAt = process.hrtime.bigint(); readyYes();
    } else readyNo(new Error("missing exact library-ready token/EOF"));
  });
  readiness.on("error", readyNo);
  child.stdin!.on("error", () => { /* Actual child/stream close decides failure. */ });
  settlement.on("error", () => { /* Actual child/stream close decides failure. */ });
  const ended = new Promise<{ code: number | null; signal: NodeJS.Signals | null }>((yes) => {
    child.once("error", (error) => { spawnError = error; readyNo(error); });
    child.once("close", (code, signal) => {
      reaped = true; collected++; closedAt = process.hrtime.bigint(); clearTimeout(safety);
      readyNo(new Error("child closed before readiness"));
      console.log(JSON.stringify({ child_settlement: { pid: child.pid, code, signal,
        synthetic_handshake_control: !!syntheticArgv, sent, readiness_hex: readyBytes.toString("hex"),
        stdout_bytes: out, stderr_bytes: err, overflow,
        initialization_ns: readyAt === undefined ? null : String(readyAt - spawnedAt),
        request_to_close_ns: sentAt === undefined ? null : String(closedAt - sentAt) } }));
      yes({ code, signal });
    });
  });
  const dispose = async () => {
    disposing = true;
    releaseHeld?.();
    if (!sent && !child.stdin!.destroyed) child.stdin!.end(); // No-request EOF, never a warmup.
    await ended; // The original absolute safety timer remains active until actual close.
  };
  try {
    await ready;
    assert(!reaped && child.exitCode === null && child.signalCode === null && !overflow);
  } catch (error) {
    await dispose();
    throw new Error(`child readiness failed: ${error}: ${Buffer.concat(stderr)}`);
  }
  return {
    dispose, isCollected: () => reaped,
    async send(frame: string, onHeld?: (release: () => void) => void): Promise<string> {
      assert(!sent && !reaped && readyAt !== undefined && !overflow);
      assert(Buffer.byteLength(frame) <= 947);
      sent = true; sentAt = process.hrtime.bigint(); held = onHeld;
      child.stdin!.end(frame);
      const { code, signal } = await ended; // Stream/process settlement precedes port.close.
      assert(code === 0 && signal === null && !overflow && !spawnError,
        `fixture child failed: ${code}/${signal}: ${Buffer.concat(stderr)}`);
      const response = Buffer.concat(stdout).toString("ascii");
      const trace = JSON.parse(Buffer.concat(stderr).toString("utf8"));
      assert.equal(trace.sha256, env.NSEALR_QP01_LIBRARY_SHA256);
      assert.equal(trace.input_sha256, createHash("sha256").update(frame).digest("hex"));
      assert.equal(trace.output_sha256, createHash("sha256").update(response).digest("hex"));
      assert(trace.synthetic_complete_review.length > 1);
      reports.push(trace);
      console.log(JSON.stringify({ native_observation: trace }));
      return response;
    }
  };
}

type Mutation = "account-key" | "request-id" | "template" | "event-id" | "signature";
async function setup(vector = basic, mutation?: Mutation, changed?: string, holdChild = false) {
  let worker: Awaited<ReturnType<typeof prepareNative>>;
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
          pending = worker.send(input, holdChild ? entered : undefined); holdChild = false;
          void pending.catch(() => {}); // Keep failure observed if the client returns early.
        },
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
        close: async () => { try { if (pending) await pending; closes++; } finally { settled(); } }
      };
    }
  });
  const context: LocalServiceContext = { accounts: [account], now: 1, monotonicNow: () => ticks,
    grants: [{ client_id: clientIdForIdentity(identity), origin: identity.origin, surface: identity.surface,
      allowed_operations: ["dispatch_signer_request"] }], signerCompatibility: () => snapshot, signerDispatcher: dispatcher };
  const envelope = { version: 1 as const, request_id: "qp01.local.fixture", operation: "dispatch_signer_request" as const,
    params: { client: identity, route_request: { account_id: account.account_id, method: "sign_event" }, request } };
  // Setup assertions/fixture parsing above own no child. Preparation receives no request.
  worker = await prepareNative(holdChild);
  return { run: () => handleLocalServiceRequestAsync(envelope, context),
    separate: () => handleLocalServiceRequestAsync(envelope, { ...context }), held, settled: settledPromise,
    counts: () => ({ opens, scans, closes }),
    refuseBeforeRun: () => {
      const method = snapshot.adapter.methods.find((entry) => entry.id === "sign_event");
      assert(method); Object.assign(method, { availability: "unavailable", reason: "provider_missing" });
    },
    prepareFresh: async () => { assert(worker.isCollected()); worker = await prepareNative(); pending = undefined; },
    dispose: async () => { await worker.dispose(); if (pending) await pending.catch(() => {});
      await new Promise<void>((yes) => setImmediate(yes)); }
  };
}

async function usingState<T>(state: Awaited<ReturnType<typeof setup>>, run: () => Promise<T>): Promise<T> {
  try { return await run(); } finally { await state.dispose(); }
}

if (process.argv.includes("--readiness-controls")) {
  // Separate no-signing controls, not extra cases in the original14-child campaign.
  const unused = await prepareNative(); await unused.dispose(); assert(unused.isCollected());
  const refused = await setup();
  await usingState(refused, async () => {
    refused.refuseBeforeRun(); assert.equal((await refused.run()).ok, false);
    assert.deepEqual(refused.counts(), { opens: 0, scans: 0, closes: 0 });
  });
  const assertion = await setup();
  await assert.rejects(usingState(assertion, async () => { assert.fail("controlled assertion before presentation"); }),
    /controlled assertion before presentation/);
  await assert.rejects(prepareNative(false, { ...process.env, NSEALR_QP01_LIBRARY_SHA256: "0".repeat(64) }),
    /SHA256 mismatch/);
  await assert.rejects(prepareNative(false, process.env, ["-c",
    "import os; os.write(4,b'RX'); os.close(4); os.read(0,1)"]), /invalid readiness token/);
  assert.equal(reports.length, 0); assert.equal(children, 5); assert.equal(collected, 5);
  console.log(JSON.stringify({ readiness_controls: 5, request_bytes_sent: 0, native_reports: 0, children, collected }));
} else {
  for (const vector of [basic, tagged]) {
    const state = await setup(vector);
    await usingState(state, async () => {
      const result = await state.run();
      assert.equal(result.ok, true, JSON.stringify(result));
      assert.deepEqual((result as any).result.signer_response, vector.response);
      assert.deepEqual(state.counts(), { opens: 1, scans: 1, closes: 1 });
    });
  }
  for (const mutation of ["account-key", "request-id", "template", "event-id", "signature"] as const) {
    const state = await setup(basic, mutation);
    await usingState(state, async () => {
      const result = await state.run();
      assert.equal(result.ok, false);
      assert.equal((result as any).error.code, "invalid_signer_response", JSON.stringify(result));
      assert.deepEqual(state.counts(), { opens: 1, scans: 1, closes: 1 });
    });
  }
  for (const change of ["account", "generation", "availability", "limits", "deadline"]) {
    const state = await setup(basic, undefined, change);
    await usingState(state, async () => {
      const result = await state.run();
      assert.equal(result.ok, false, change);
      assert.deepEqual(state.counts(), { opens: 1, scans: 1, closes: 1 });
    });
  }
  {
    const state = await setup(basic, undefined, undefined, true);
    await usingState(state, async () => {
      const operation = state.run();
      const release = await Promise.race([state.held, operation.then(() => {
        throw new Error("client operation ended before controlled held-child entry");
      })]);
      try {
        const timedOut = await operation;
        assert.equal((timedOut as any).error.code, "signer_transport_timeout");
        assert.equal((await state.run() as any).error.code, "runtime_unavailable");
        assert.equal((await state.separate() as any).error.code, "signer_transport_failed");
        assert.equal(state.counts().closes, 0);
      } finally {
        release(); await state.settled;
        // close() returning precedes dispatcher/pending-finally actual settlement.
        await new Promise<void>((yes) => setImmediate(yes));
      }
      await state.prepareFresh();
      const fresh = await state.run();
      assert.equal(fresh.ok, true, JSON.stringify(fresh));
      assert.deepEqual(state.counts(), { opens: 2, scans: 2, closes: 2 });
    });
  }
  assert.equal(children, 14); assert.equal(children, collected);
  console.log(JSON.stringify({ scope: "actual client + public-fixture host adapter only", positive: 2,
    valid_shape_verifier_negatives: 5, post_native_currentness_negatives: 5,
    actual_unsettled_child_timeout_no_early_reuse_then_fresh: true, children, collected, reports }, null, 2));
}
