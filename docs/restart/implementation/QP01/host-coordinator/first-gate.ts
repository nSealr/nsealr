// Admitted finite engineering gate. O alone owns W; C uses the existing owner.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Readable, Writable } from "node:stream";
import { clientIdForIdentity, handleLocalServiceRequestAsync, type LocalServiceContext,
  type SignerCompatibilitySnapshot } from "@nsealr/client";
import { parseAccountDescriptor } from "@nsealr/policy";
import { parseImplementationProfile, parseLimitsManifest, type FullCapabilities } from "@nsealr/protocol";
import { createManualQrRouteDispatcher } from "../../../../../apps/bridge/service/src/manual-qr.js";

type Native = { dispose(): Promise<void>; isCollected(): boolean; inputBytes(): number;
  ended: Promise<{ code: number | null; signal: NodeJS.Signals | null }>; pid: number | undefined;
  send(frame: string): Promise<string>; killOwned(): boolean };
const hash = (data: Buffer | string) => createHash("sha256").update(data).digest("hex");
const equalKeys = (value: any, keys: string[]) => {
  assert(value && typeof value === "object" && !Array.isArray(value));
  assert.deepEqual(Object.keys(value), keys);
};
const integer = (n: unknown, min = 0, max = Number.MAX_SAFE_INTEGER) => {
  assert(typeof n === "number" && Number.isSafeInteger(n) && n >= min && n <= max);
};
const digest = (s: unknown) => assert(typeof s === "string" && /^[a-f0-9]{64}$/.test(s));
const decimal = (s: unknown) => {
  assert(typeof s === "string" && /^(0|[1-9][0-9]{0,19})$/.test(s));
  assert(BigInt(s) <= 18446744073709551615n);
};

function validatePhase(row: any, pid: number, contract: any) {
  equalKeys(row, contract.worker_ready_record.fixed_key_order);
  assert.equal(row.v, 1); assert.equal(row.kind, "worker_ready");
  assert.equal(row.owner_pid, pid); integer(row.worker_pid, 2);
  assert.equal(row.ppid, pid); assert.equal(row.sid, row.worker_pid); assert.equal(row.pgid, row.worker_pid);
  assert.equal(row.exe_sha256, contract.identities.worker_elf_sha256);
  assert.deepEqual(row.limits, contract.worker_ready_record.limits);
  assert.equal(row.G_bytes, 0); assert.equal(row.image_bytes_sent, 0);
  assert(Array.isArray(row.fds)); assert.equal(row.fds.length, 3);
  row.fds.forEach((fd: any, i: number) => {
    equalKeys(fd, ["fd", "target", "dev", "ino"]); assert.equal(fd.fd, i);
    decimal(fd.dev); decimal(fd.ino);
    assert.equal(fd.target, `pipe:[${fd.ino}]`); assert(fd.target.length <= 27);
  });
}

function validateTerminal(row: any, pid: number, phase: any, contract: any, output: Buffer) {
  equalKeys(row, contract.terminal_record.fixed_key_order);
  assert.equal(row.v, 1); assert.equal(row.kind, "terminal"); assert.equal(row.owner_pid, pid);
  assert(contract.terminal_record.outcome_enum.includes(row.outcome));
  assert(contract.terminal_record.ownership_enum.includes(row.ownership));
  assert.equal(row.ownership, "settled", "unknown cleanup retains live O and quarantines this port");
  for (const name of ["session_policy_verified", "final_worker_eligible", "cancel_observed"])
    assert.equal(typeof row[name], "boolean");
  equalKeys(row.worker_io, ["stdin_closed", "stdout_eof", "stderr_eof", "owned_fds_closed"]);
  assert.equal(row.worker_io.owned_fds_closed, true);
  if (row.worker_pid === null) {
    assert.equal(phase, undefined); assert.equal(row.worker_wait, null);
    for (const key of ["stdin_closed", "stdout_eof", "stderr_eof"]) assert.equal(row.worker_io[key], null);
    assert.equal(row.session_policy_verified, false);
    for (const key of ["G_bytes", "image_bytes_sent", "stdout_observed", "stderr_observed"]) assert.equal(row[key], 0);
  } else {
    integer(row.worker_pid, 2);
    if (phase) assert.equal(row.worker_pid, phase.worker_pid);
    assert.equal(row.session_policy_verified, !!phase);
    equalKeys(row.worker_wait, ["raw_status", "exit_code", "collector_pid"]);
    integer(row.worker_wait.raw_status, 0, 65535); integer(row.worker_wait.exit_code, -127, 255);
    assert.equal(row.worker_wait.collector_pid, pid);
    const raw = row.worker_wait.raw_status, low = raw & 127;
    assert.notEqual(low, 127); assert.notEqual(raw, 65535);
    assert.equal(row.worker_wait.exit_code, low === 0 ? (raw >> 8) & 255 : -low);
    for (const key of ["stdin_closed", "stdout_eof", "stderr_eof"]) assert.equal(row.worker_io[key], true);
  }
  for (const key of ["stdout_observed", "stderr_observed"]) integer(row[key]);
  integer(row.input_bytes_received, 0, 172801); integer(row.G_bytes, 0, 1);
  integer(row.image_bytes_sent, 0, 172800);
  for (const key of ["stdout_retained", "stderr_retained", "result_bytes"]) integer(row[key], 0, 512);
  assert(row.stdout_retained <= row.stdout_observed); assert(row.stderr_retained <= row.stderr_observed);
  if (row.input_sha256 !== null) { digest(row.input_sha256); assert.equal(row.input_bytes_received, 172800); }
  assert.equal(typeof row.worker_stderr_base64, "string");
  const stderr = Buffer.from(row.worker_stderr_base64, "base64");
  assert.equal(stderr.toString("base64"), row.worker_stderr_base64); assert.equal(stderr.length, row.stderr_retained);
  assert.equal(row.result_bytes, output.length);
  assert.equal(row.result_sha256, output.length ? hash(output) : null);
  equalKeys(row.timing, ["begin_ns", "invalidated_ns", "cleanup_deadline_ns", "settled_ns", "final_admission_ns"]);
  for (const value of Object.values(row.timing)) if (value !== null) decimal(value);
  assert.notEqual(row.timing.settled_ns, null); assert.notEqual(row.timing.final_admission_ns, null);
  assert(BigInt(row.timing.settled_ns) <= BigInt(row.timing.final_admission_ns));
  if (row.timing.invalidated_ns !== null)
    assert.equal(BigInt(row.timing.cleanup_deadline_ns), BigInt(row.timing.invalidated_ns) + 4000000000n);
  else assert.equal(row.timing.cleanup_deadline_ns, null);
  if (row.outcome === "decoded") {
    assert(phase); assert.equal(row.worker_wait.exit_code, 0);
    assert.equal(row.final_worker_eligible, true); assert.equal(row.cancel_observed, false);
    assert.equal(row.G_bytes, 1); assert.equal(row.image_bytes_sent, 172800); assert.equal(row.input_bytes_received, 172800);
    assert.equal(row.timing.invalidated_ns, null); assert.notEqual(row.timing.begin_ns, null);
    assert(BigInt(row.timing.final_admission_ns) < BigInt(row.timing.begin_ns) + 8000000000n);
  } else { assert.equal(output.length, 0); assert.equal(row.final_worker_eligible, false); }
}

async function prepareOwner(root: string, contract: any) {
  const python = process.env.NSEALR_QP01_PYTHON, binary = process.env.NSEALR_QP01_QR_WORKER;
  assert(python && binary);
  assert.equal(hash(readFileSync(binary)), contract.identities.worker_elf_sha256);
  const argv = ["-B", resolve(root, "apps/pi/app/nsealr_vault/qr_worker.py"),
    "--worker", binary, "--sha256", contract.identities.worker_elf_sha256];
  const child = spawn(python, argv, { cwd: root, env: process.env, stdio: ["pipe", "pipe", "pipe", "pipe", "pipe", "pipe"] });
  const started = process.hrtime.bigint();
  const command = child.stdio[3] as Writable, readyStream = child.stdio[4] as Readable, statusStream = child.stdio[5] as Readable;
  let output = Buffer.alloc(0), diagnostic = Buffer.alloc(0), readyBytes = Buffer.alloc(0), status = Buffer.alloc(0);
  let statusEOF = false, readyEOF = false, outEOF = false, errEOF = false, collected = false;
  let cancelled = false, presented = false, ack = false, unused = false, seenBytes = 0, lines = 0;
  let fault: unknown, phase: any, terminal: any;
  let onPhase: (() => void) | undefined;
  const commands: { opcode: string; node_ns: string }[] = [];
  let readyYes!: () => void, readyNo!: (e: unknown) => void;
  const ready = new Promise<void>((yes, no) => { readyYes = yes; readyNo = no; }); void ready.catch(() => {});
  const control = (opcode: string) => {
    commands.push({ opcode, node_ns: String(process.hrtime.bigint()) }); command.write(opcode);
  };
  const cancel = () => {
    if (!cancelled && !unused && !collected) { cancelled = true; control("X"); }
    if (!child.stdin!.destroyed) child.stdin!.end();
  };
  const fail = (error: unknown) => { fault ??= error; readyNo(error); cancel(); };
  command.on("error", (e) => { if (!collected && !terminal) fail(e); });
  child.stdin!.on("error", (e) => { if (!cancelled && !collected) fail(e); });
  const bounded = (stream: Readable, cap: number, get: () => Buffer, put: (b: Buffer) => void) => {
    stream.on("data", (chunk: Buffer) => {
      const before = get(); const after = Buffer.concat([before, chunk.subarray(0, Math.max(0, cap + 1 - before.length))]);
      put(after); if (after.length > cap) fail(new Error("O channel capacity"));
    }); stream.on("error", fail);
  };
  bounded(child.stdout!, 512, () => output, (b) => { output = b; });
  bounded(child.stderr!, 512, () => diagnostic, (b) => { diagnostic = b; });
  child.stdout!.on("end", () => { outEOF = true; }); child.stderr!.on("end", () => { errEOF = true; });
  readyStream.on("data", (chunk: Buffer) => {
    readyBytes = Buffer.concat([readyBytes, chunk.subarray(0, Math.max(0, 2 - readyBytes.length))]);
    if (!readyBytes.equals(Buffer.from("R"))) fail(new Error("invalid O readiness token"));
  });
  readyStream.on("end", () => {
    readyEOF = true;
    if (readyBytes.equals(Buffer.from("R")) && !fault && !collected) readyYes();
    else fail(new Error("missing O readiness/EOF"));
  }); readyStream.on("error", fail);
  statusStream.on("data", (chunk: Buffer) => {
    try {
      seenBytes += chunk.length; assert(seenBytes <= 4096, "O status capacity");
      assert([...chunk].every((byte) => byte < 128));
      status = Buffer.concat([status, chunk]);
      for (let at; (at = status.indexOf(10)) >= 0;) {
        const raw = status.subarray(0, at + 1).toString("ascii"); status = status.subarray(at + 1);
        assert(++lines <= 2); const row = JSON.parse(raw);
        assert.equal(JSON.stringify(row) + "\n", raw); assert.equal(terminal, undefined);
        if (row.kind === "worker_ready") {
          assert.equal(phase, undefined); assert(child.pid);
          validatePhase(row, child.pid, contract); phase = row;
          console.log(JSON.stringify({ owner_phase: row, node_ns: String(process.hrtime.bigint()) }));
          onPhase?.();
        } else { assert.equal(row.kind, "terminal"); terminal = row; }
      }
    } catch (error) { fail(error); }
  }); statusStream.on("end", () => { statusEOF = true; }); statusStream.on("error", fail);
  const ended = new Promise<{ code: number | null; signal: NodeJS.Signals | null }>((yes) => {
    child.once("error", fail);
    child.once("close", (code, signal) => {
      collected = true; readyNo(new Error("O closed before ready"));
      yes({ code, signal });
    });
  });
  let settlement: Promise<{ output: Buffer; terminal: any; phase: any }> | undefined;
  const settle = () => settlement ??= (async () => {
    const end = await ended;
    console.log(JSON.stringify({ owner_settlement: { pid: child.pid, ...end, ready_hex: readyBytes.toString("hex"),
      readyEOF, statusEOF, outEOF, errEOF, status_bytes: seenBytes, commands, phase, terminal,
      output_bytes: output.length, output_sha256: output.length ? hash(output) : null,
      diagnostic_base64: diagnostic.toString("base64"), elapsed_ns: String(process.hrtime.bigint() - started),
      protocol_error: fault ? String(fault) : null } }));
    assert(!fault, String(fault)); assert(readyEOF && statusEOF && outEOF && errEOF);
    assert.equal(status.length, 0); assert(terminal); assert(child.pid); assert.equal(end.signal, null);
    validateTerminal(terminal, child.pid, phase, contract, output);
    assert.equal(end.code, ["unused", "decoded"].includes(terminal.outcome) ? 0 : 2);
    assert.equal(diagnostic.length, 0);
    return { output, terminal, phase };
  })();
  try { await ready; } catch (error) { cancel(); await settle(); throw error; }
  console.log(JSON.stringify({ owner_ready: { pid: child.pid, argv, binary_sha256: contract.identities.worker_elf_sha256,
    startup_ns: String(process.hrtime.bigint() - started), W_spawned: 0, request_bytes: 0 } }));
  return { cancel, settle, isCollected: () => collected,
    disposeUnused: async () => { assert(!presented); if (!unused) { unused = true; control("Q"); child.stdin!.end(); } return settle(); },
    present: async (image: Buffer, live: () => boolean) => {
      assert(!presented && !unused && !cancelled); presented = true;
      onPhase = () => { if (!cancelled && live()) { ack = true; control("G"); } else cancel(); };
      control("P");
      // Bounded write requests; no image is offered before P or after invalidation.
      for (let at = 0; at < image.length && !cancelled; at += 4096) {
        if (!child.stdin!.write(image.subarray(at, at + 4096)))
          await new Promise<void>((yes) => { child.stdin!.once("drain", yes); child.stdin!.once("close", yes); });
      }
      if (!child.stdin!.destroyed) child.stdin!.end();
      const result = await settle(); assert(ack); assert.equal(result.terminal.outcome, "decoded");
      assert.equal(result.terminal.input_sha256, hash(image));
      return result.output;
    }
  };
}

export async function runFirstGate({ prepareNative, basic, root }: {
  prepareNative(): Promise<Native>; basic: any; root: string;
}) {
  const contract = JSON.parse(readFileSync(new URL("control-contract.json", import.meta.url), "utf8"));
  const image = readFileSync(resolve(root, contract.independent_oracle.image_path));
  const expected = readFileSync(resolve(root, contract.independent_oracle.decoded_frame_path));
  assert.equal(image.length, 172800); assert.equal(hash(image), contract.independent_oracle.image_sha256);
  assert.equal(expected.length, 259); assert.equal(hash(expected), contract.independent_oracle.decoded_frame_sha256);
  assert.equal(basic.response.result.event.sig, contract.independent_oracle.expected_signature);
  const preparePair = async () => {
    const owner = await prepareOwner(root, contract);
    try { return { owner, native: await prepareNative() }; }
    catch (error) { await owner.disposeUnused(); throw error; }
  };
  // FIRST actual initialization/disposal. No P/RGB/W/native request.
  {
    const { owner, native } = await preparePair();
    const [result] = await Promise.all([owner.disposeUnused(), native.dispose()]);
    assert.equal(result.terminal.outcome, "unused"); assert.equal(result.terminal.worker_pid, null);
    assert.equal(native.inputBytes(), 0); assert(owner.isCollected() && native.isCollected());
    console.log(JSON.stringify({ case: "FG0_startup_unused", pass: true, W_spawned: 0, C_input_bytes: 0 }));
  }
  // SECOND actual end-to-end operation, before adding fault instrumentation.
  let owner: Awaited<ReturnType<typeof prepareOwner>>, native: Native;
  const load = (path: string) => JSON.parse(readFileSync(resolve(root, "protocols/contracts/v1", path), "utf8"));
  const cases = load("vectors/profile-capabilities/cases-v1.json");
  const request = structuredClone(basic.request);
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
    review_plan: { request_sha256: hash(JSON.stringify(request)), implementation_id: implementation.implementation_id,
      connection_id: "qp01.synthetic.connection", generation: 1, context_id: "qp01.synthetic.no-consent",
      geometry_id: "qp01.unqualified.fixture", pages: 7 }
  };
  const account = parseAccountDescriptor(load("vectors/accounts/raspberry-qr-nip06-account-0.json"));
  account.public_key = basic.signed_event.pubkey;
  const identity = { surface: "cli" as const, origin: "app:qp01-public-fixture", app_name: "QP01 synthetic engineering fixture" };
  let pending: Promise<string> | undefined, invalidated = false, opens = 0, scans = 0, closes = 0;
  let settlePort!: () => void; const portSettled = new Promise<void>((yes) => { settlePort = yes; });
  let abort: (() => void) | undefined, signal: AbortSignal | undefined;
  const dispatcher = createManualQrRouteDispatcher({ account_id: account.account_id, route_type: "raspberry_qr_vault",
    openPort: async (control) => {
      opens++; signal = control.abort_signal;
      abort = () => { invalidated = true; owner.cancel(); void native.dispose(); };
      signal.addEventListener("abort", abort, { once: true });
      return {
        present: async (frame) => {
          control.before_present(); assert.equal(frame, expected.toString("ascii"));
          console.log(JSON.stringify({ first_before_present: true, node_ns: String(process.hrtime.bigint()) }));
          try {
            const decoded = await owner.present(image, () => !invalidated && !native.isCollected());
            assert(decoded.equals(Buffer.from(frame))); assert(!invalidated && !native.isCollected());
            // SAME guard while Bridge.presenting is still true. No await or external
            // work intervenes between this call and the existing synchronous C write.
            control.before_present();
            pending = native.send(decoded.toString("ascii"));
            void pending.catch(() => {});
            console.log(JSON.stringify({ second_before_present: true, C_input_bytes: native.inputBytes() }));
          } catch (error) { invalidated = true; owner.cancel(); await native.dispose(); throw error; }
        },
        scan: async () => { scans++; assert(pending); return pending; },
        close: async () => {
          try {
            await native.dispose();
            await owner.settle(); // Revalidate actual O/W status, never C close alone.
            closes++;
          } finally { if (abort) signal!.removeEventListener("abort", abort); settlePort(); }
        }
      };
    }
  });
  const context: LocalServiceContext = { accounts: [account], now: 1, monotonicNow: () => 0,
    grants: [{ client_id: clientIdForIdentity(identity), origin: identity.origin, surface: identity.surface,
      allowed_operations: ["dispatch_signer_request"] }], signerCompatibility: () => snapshot, signerDispatcher: dispatcher };
  const envelope = { version: 1 as const, request_id: "qp01.local.fixture", operation: "dispatch_signer_request" as const,
    params: { client: identity, route_request: { account_id: account.account_id, method: "sign_event" }, request } };
  ({ owner, native } = await preparePair());
  void native.ended.then(() => { if (!owner.isCollected()) owner.cancel(); });
  const started = process.hrtime.bigint();
  let result: unknown;
  try {
    result = await handleLocalServiceRequestAsync(envelope, context);
    console.log(JSON.stringify({ actual_client: result, operation_ns: String(process.hrtime.bigint() - started) }));
    assert.equal((result as any).ok, true, JSON.stringify(result));
    assert.deepEqual((result as any).result.signer_response, basic.response);
    assert.equal(native.inputBytes(), 259); assert.equal(Buffer.byteLength(await pending!), 611);
    assert.deepEqual({ opens, scans, closes }, { opens: 1, scans: 1, closes: 1 });
  } finally {
    if (!owner.isCollected()) owner.cancel();
    await native.dispose();
    if (opens) await portSettled; else await owner.settle();
    if (pending) await pending.catch(() => {});
  }
  assert(owner.isCollected() && native.isCollected());
  console.log(JSON.stringify({ case: "FG1_normal259", pass: true, C_input_bytes: 259, response_bytes: 611,
    actual_client: result, all_collected: true, remaining_FG_groups: "NOT_EXECUTED" }));
}
