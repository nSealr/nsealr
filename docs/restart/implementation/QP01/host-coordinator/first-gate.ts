// Admitted finite engineering gate. O alone owns W; C uses the existing owner.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Readable, Writable } from "node:stream";
import { clientIdForIdentity, handleLocalServiceRequestAsync, type LocalServiceContext,
  type SignerCompatibilitySnapshot } from "@nsealr/client";
import { parseAccountDescriptor } from "@nsealr/policy";
import { parseImplementationProfile, parseLimitsManifest, type FullCapabilities, CapabilityError } from "@nsealr/protocol";
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

function validatePhase(row: any, pid: number, contract: any, presented: boolean, unused: boolean) {
  assert(presented && !unused, "worker_phase_requires_presented_P_not_unused");
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
  if (row.outcome === "unused") {
    assert.equal(row.worker_pid, null, "unused_has_no_worker");
    assert.equal(phase, undefined, "unused_has_no_phase");
    assert.equal(row.G_bytes, 0, "unused_has_no_G");
    assert.equal(row.image_bytes_sent, 0, "unused_has_no_image");
    assert.equal(row.input_bytes_received, 0, "unused_has_no_input");
  }
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
    assert(row.stdout_observed <= 512, "decoded_stdout_overflow");
    assert.equal(row.stdout_observed, row.stdout_retained, "decoded_stdout_observed_retained_mismatch");
    assert.equal(row.stdout_retained, row.result_bytes, "decoded_stdout_retained_result_mismatch");
    assert(row.stderr_observed <= 512, "decoded_stderr_overflow");
    assert.equal(row.stderr_observed, row.stderr_retained, "decoded_stderr_observed_retained_mismatch");
    assert.equal(row.final_worker_eligible, true); assert.equal(row.cancel_observed, false);
    assert.equal(row.G_bytes, 1); assert.equal(row.image_bytes_sent, 172800); assert.equal(row.input_bytes_received, 172800);
    assert.equal(row.timing.invalidated_ns, null); assert.notEqual(row.timing.begin_ns, null);
    assert(BigInt(row.timing.final_admission_ns) < BigInt(row.timing.begin_ns) + 8000000000n);
  } else { assert.equal(output.length, 0); assert.equal(row.final_worker_eligible, false); }
}

async function prepareOwner(root: string, contract: any, syntheticArgv?: string[], onSettled?: (observation: any) => void) {
  const python = process.env.NSEALR_QP01_PYTHON, binary = process.env.NSEALR_QP01_QR_WORKER;
  assert(python && binary);
  assert.equal(hash(readFileSync(binary)), contract.identities.worker_elf_sha256);
  const argv = syntheticArgv ?? ["-B", resolve(root, "apps/pi/app/nsealr_vault/qr_worker.py"),
    "--worker", binary, "--sha256", contract.identities.worker_elf_sha256];
  const child = spawn(python, argv, { cwd: root, env: process.env, stdio: ["pipe", "pipe", "pipe", "pipe", "pipe", "pipe"] });
  const started = process.hrtime.bigint();
  const command = child.stdio[3] as Writable, readyStream = child.stdio[4] as Readable, statusStream = child.stdio[5] as Readable;
  let output = Buffer.alloc(0), diagnostic = Buffer.alloc(0), readyBytes = Buffer.alloc(0), status = Buffer.alloc(0);
  let statusEOF = false, readyEOF = false, readyAccepted = false, outEOF = false, errEOF = false, collected = false;
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
    if (readyBytes.equals(Buffer.from("R")) && !fault && !collected) { readyAccepted = true; readyYes(); }
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
          validatePhase(row, child.pid, contract, presented && commands.some((entry) => entry.opcode === "P"), unused); phase = row;
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
    const observation = { pid: child.pid, ...end, ready_hex: readyBytes.toString("hex"),
      readyEOF, readyAccepted, statusEOF, outEOF, errEOF, status_bytes: seenBytes, commands, phase, terminal,
      output_bytes: output.length, output_sha256: output.length ? hash(output) : null,
      diagnostic_base64: diagnostic.toString("base64"), elapsed_ns: String(process.hrtime.bigint() - started),
      protocol_error: fault ? String(fault) : null, synthetic_no_W_helper: !!syntheticArgv,
      complete_status_records: lines, unconsumed_status_bytes: status.length };
    console.log(JSON.stringify({ owner_settlement: observation }));
    onSettled?.(observation);
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
    rawControl: (bytes: string) => { control(bytes); },
    controlEOF: () => command.end(),
    phase: () => phase,
    acknowledge: () => { assert(phase && !ack && !cancelled); ack = true; control("G"); },
    disposeUnused: async () => { assert(!presented); if (!unused) { unused = true; control("Q"); child.stdin!.end(); } return settle(); },
    present: async (image: Buffer, live: () => boolean, phaseHook?: (acknowledge: () => void) => void) => {
      assert(!presented && !unused && !cancelled); presented = true;
      onPhase = () => {
        const acknowledge = () => { assert(!ack); if (!cancelled && live()) { ack = true; control("G"); } else cancel(); };
        if (phaseHook) phaseHook(acknowledge); else acknowledge();
      };
      control("P");
      // Bounded write requests; no image is offered before P or after invalidation.
      for (let at = 0; at < image.length && !cancelled; at += 4096) {
        if (!child.stdin!.write(image.subarray(at, at + 4096)))
          await new Promise<void>((yes) => { child.stdin!.once("drain", yes); child.stdin!.once("close", yes); });
      }
      if (!child.stdin!.destroyed) child.stdin!.end();
      const result = await settle();
      if (result.terminal.outcome === "decoded") { assert(ack); assert.equal(result.terminal.input_sha256, hash(image)); }
      return result;
    }
  };
}

export async function runFirstGate({ prepareNative, basic, root }: {
  prepareNative(hold?: boolean, env?: NodeJS.ProcessEnv, syntheticArgv?: string[]): Promise<Native>; basic: any; root: string;
}) {
  const contract = JSON.parse(readFileSync(new URL("control-contract.json", import.meta.url), "utf8"));
  if (process.argv.includes("--owner-correction-parser")) { parserRelationControls(contract); return; }
  const deadlineFocus = process.argv.includes("--owner-deadline-control");
  if (process.argv.includes("--owner-malformed-controls")) { await malformedHelpers(root, contract); return; }
  const image = readFileSync(resolve(root, contract.independent_oracle.image_path));
  const expected = readFileSync(resolve(root, contract.independent_oracle.decoded_frame_path));
  assert.equal(image.length, 172800); assert.equal(hash(image), contract.independent_oracle.image_sha256);
  assert.equal(expected.length, 259); assert.equal(hash(expected), contract.independent_oracle.decoded_frame_sha256);
  assert.equal(basic.response.result.event.sig, contract.independent_oracle.expected_signature);
  const preparePair = async (env = process.env, syntheticArgv?: string[]) => {
    const owner = await prepareOwner(root, contract);
    try { return { owner, native: await prepareNative(false, env, syntheticArgv) }; }
    catch (error) {
      const result = await owner.disposeUnused();
      assert.equal(result.terminal.worker_pid, null); assert.equal(result.terminal.outcome, "unused");
      assert(owner.isCollected()); throw error;
    }
  };
  if (!deadlineFocus) {
    // FIRST actual initialization/disposal. No P/RGB/W/native request.
    {
      const { owner, native } = await preparePair();
      const [result] = await Promise.all([owner.disposeUnused(), native.dispose()]);
      assert.equal(result.terminal.outcome, "unused"); assert.equal(result.terminal.worker_pid, null);
      assert.equal(native.inputBytes(), 0); assert(owner.isCollected() && native.isCollected());
      console.log(JSON.stringify({ case: "FG0_startup_unused", pass: true, W_spawned: 0, C_input_bytes: 0 }));
    }
    await assert.rejects(preparePair({ ...process.env, NSEALR_QP01_LIBRARY_SHA256: "0".repeat(64) }), /SHA256 mismatch/);
    console.log(JSON.stringify({ case: "FG0_C_library_ready_failure", pass: true, W_spawned: 0, C_input_bytes: 0 }));
    await assert.rejects(preparePair(process.env, ["-c", "import os; os.write(4,b'RX'); os.close(4); os.read(0,1)"]), /invalid readiness token/);
    console.log(JSON.stringify({ case: "FG0_C_handshake_failure", pass: true, W_spawned: 0, C_input_bytes: 0, synthetic_C_helper: true }));
    await assert.rejects(async () => {
      const { owner, native } = await preparePair();
      try { assert.fail("controlled pre-presentation assertion"); }
      finally { await Promise.all([owner.disposeUnused(), native.dispose()]); assert(owner.isCollected() && native.isCollected()); }
    }, /controlled pre-presentation assertion/);
    console.log(JSON.stringify({ case: "FG0_pre_presentation_assertion", pass: true, W_spawned: 0, C_input_bytes: 0 }));
  }
  // The frozen early smoke stays in its original source/receipt; the stable
  // sequence below includes normal first, then only the admitted fault groups.
  type Mode = "normal" | "timeout-preG" | "timeout-late" | "cancel-preG" | "cancel-late" |
    "generation" | "Cdeath" | "control-eof" | "preadmission" | "elapsed-before-timer";
  async function exchangeCase(mode: Mode, id: string) {
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
    let secondGuard = false, privateDecoded = 0, phaseEntered = false;
    let elapsedGuard: Record<string, unknown> | undefined;
    let settlePort!: () => void, reached!: () => void, release!: () => void;
    let portSettled = new Promise<void>((yes) => { settlePort = yes; });
    const held = new Promise<void>((yes) => { reached = yes; });
    const released = new Promise<void>((yes) => { release = yes; });
    let abort: (() => void) | undefined, signal: AbortSignal | undefined;
    const causes: { cause: string; node_ns: string; C_input_bytes: number; W_pid: number | null }[] = [];
    const localCancel = (cause: string) => {
      invalidated = true;
      causes.push({ cause, node_ns: String(process.hrtime.bigint()), C_input_bytes: native.inputBytes(),
        W_pid: owner.phase()?.worker_pid ?? null });
      owner.cancel(); void native.dispose();
    };
    const dispatcher = createManualQrRouteDispatcher({ account_id: account.account_id, route_type: "raspberry_qr_vault",
      openPort: async (control) => {
        opens++; signal = control.abort_signal;
        abort = () => localCancel("actual_abort_signal");
        signal.addEventListener("abort", abort, { once: true });
        return {
          present: async (frame) => {
            control.before_present(); assert.equal(frame, expected.toString("ascii"));
            console.log(JSON.stringify({ case: id, first_before_present: true, node_ns: String(process.hrtime.bigint()) }));
            try {
              const result = await owner.present(image, () => !invalidated && !native.isCollected(), (acknowledge) => {
                phaseEntered = true;
                if (mode === "timeout-preG") reached();
                else if (mode === "cancel-preG") { localCancel("private_cancel_preG"); reached(); }
                else if (mode === "Cdeath") {
                  causes.push({ cause: "injected_C_SIGKILL_not5000ms", node_ns: String(process.hrtime.bigint()),
                    C_input_bytes: native.inputBytes(), W_pid: owner.phase().worker_pid });
                  assert(native.killOwned()); reached();
                } else if (mode === "control-eof") { owner.controlEOF(); reached(); }
                else { acknowledge(); if (mode === "generation") snapshot.generation++; }
              });
              if (result.terminal.outcome !== "decoded") throw new Error(`O refused: ${result.terminal.outcome}`);
              const decoded = result.output; privateDecoded = decoded.length;
              assert(decoded.equals(Buffer.from(frame)));
              if (mode === "timeout-late") { reached(); await released; }
              if (mode === "cancel-late") localCancel("private_cancel_after_W_settlement");
              assert(!invalidated && !native.isCollected());
              if (mode === "elapsed-before-timer") {
                assert(owner.isCollected() && result.terminal.worker_wait.exit_code === 0);
                const holdBegin = performance.now();
                assert(holdBegin - operationStart < 100, "deadline already elapsed before the intended synchronous hold");
                assert.equal(control.abort_signal.aborted, false);
                // Actual elapsed time, not a substituted clock or intercepted timer.
                // Node cannot run a timer callback during this synchronous interval.
                while (performance.now() - holdBegin < 110) { /* finite real-time hold */ }
                const holdEnd = performance.now();
                assert.equal(control.abort_signal.aborted, false);
                try { control.before_present(); }
                catch (error) {
                  assert(error instanceof CapabilityError);
                  assert.equal(error.reason, "runtime_unavailable");
                  assert.equal(error.message, "local deadline expired or clock rolled back/unavailable");
                  assert.equal(control.abort_signal.aborted, false);
                  elapsedGuard = { type: error.name, reason: error.reason, message: error.message,
                    signal_aborted: control.abort_signal.aborted, hold_begin_ms: holdBegin, hold_end_ms: holdEnd,
                    actual_hold_ms: holdEnd - holdBegin, operation_elapsed_ms: holdEnd - operationStart,
                    W_O_collected: owner.isCollected(), private_decoded_bytes: decoded.length, C_input_bytes: native.inputBytes() };
                  console.log(JSON.stringify({ case: id, synchronous_deadline_guard: elapsedGuard }));
                  throw error; // Preserve the real guard error through the existing async cleanup.
                }
                assert.fail("same before_present did not reject the real elapsed deadline");
              }
              // SAME actual guard while Bridge.presenting remains true; never an
              // asynchronous continuation after present() returned.
              control.before_present();
              pending = native.send(decoded.toString("ascii"));
              secondGuard = true; void pending.catch(() => {});
            } catch (error) {
              invalidated = true; owner.cancel(); await native.dispose();
              throw error;
            }
          },
          scan: async () => { scans++; assert(pending); return pending; },
          close: async () => {
            try {
              await native.dispose();
              await owner.settle(); // Real O/W status/EOF, never C close alone.
              // This Node-only hold proves reservation through aggregate close;
              // it never stops O or defers its actual W/IO cleanup.
              if (mode === "timeout-preG") await released;
              closes++;
            } finally { if (abort) signal!.removeEventListener("abort", abort); settlePort(); }
          }
        };
      }
    });
    const context: LocalServiceContext = { accounts: [account], now: 1, // Synthetic fixture wall metadata; actual service default performance.now governs deadlines.
      grants: [{ client_id: clientIdForIdentity(identity), origin: identity.origin, surface: identity.surface,
        allowed_operations: ["dispatch_signer_request"] }], signerCompatibility: () => snapshot, signerDispatcher: dispatcher };
    const envelope = { version: 1 as const, request_id: "qp01.local.fixture", operation: "dispatch_signer_request" as const,
      params: { client: identity, route_request: { account_id: account.account_id, method: "sign_event" }, request } };
    if (mode === "preadmission") {
      const method = snapshot.adapter.methods.find((entry) => entry.id === "sign_event"); assert(method);
      Object.assign(method, { availability: "unavailable", reason: "provider_missing" });
    }
    const run = () => handleLocalServiceRequestAsync(envelope, context);
    ({ owner, native } = await preparePair());
    void native.ended.then(() => { if (!owner.isCollected()) localCancel("C_actual_close"); });
    const started = process.hrtime.bigint();
    const operationStart = performance.now();
    let result: any, ownerResult: Awaited<ReturnType<typeof owner.settle>> | undefined;
    try {
      const operation = run();
      if (mode === "preadmission") {
        result = await operation; assert.equal(result.ok, false); assert.equal(opens, 0);
        ownerResult = await owner.disposeUnused(); await native.dispose();
        assert.equal(ownerResult.terminal.worker_pid, null); assert.equal(native.inputBytes(), 0);
        assert(owner.isCollected() && native.isCollected());
        console.log(JSON.stringify({ case: id, pass: true, actual_client: result, opens, W_spawned: 0, C_input_bytes: 0 }));
        return;
      }
      if (mode.startsWith("timeout")) {
        await Promise.race([held, operation.then(() => { throw new Error("operation ended before held phase"); })]);
        assert.equal((await run() as any).error.code, "runtime_unavailable");
        assert.equal((await handleLocalServiceRequestAsync(envelope, { ...context }) as any).error.code, "signer_transport_failed");
        result = await operation;
        assert.equal(result.error.code, "signer_transport_timeout");
        assert.equal((await run() as any).error.code, "runtime_unavailable");
        assert.equal((await handleLocalServiceRequestAsync(envelope, { ...context }) as any).error.code, "signer_transport_failed");
        assert.equal(closes, 0);
        release();
      } else result = await operation;
      await portSettled;
      ownerResult = await owner.settle();
      console.log(JSON.stringify({ case: id, actual_client: result, operation_ns: String(process.hrtime.bigint() - started),
        causes, phaseEntered, secondGuard, privateDecoded, elapsedGuard, C_input_bytes: native.inputBytes(), opens, scans, closes }));
      if (mode === "normal") {
        assert.equal(result.ok, true, JSON.stringify(result)); assert.deepEqual(result.result.signer_response, basic.response);
        assert.equal(native.inputBytes(), 259); assert.equal(Buffer.byteLength(await pending!), 611);
        assert.deepEqual({ opens, scans, closes }, { opens: 1, scans: 1, closes: 1 });
      } else {
        assert.equal(result.ok, false, JSON.stringify(result)); assert.equal(native.inputBytes(), 0); assert.equal(secondGuard, false);
        if (mode === "generation" || mode === "timeout-late" || mode === "cancel-late" || mode === "elapsed-before-timer") {
          assert.equal(privateDecoded, 259); assert.equal(ownerResult.terminal.outcome, "decoded");
        } else { assert.equal(ownerResult.terminal.result_bytes, 0); assert.equal(ownerResult.terminal.G_bytes, 0); }
        if (mode === "elapsed-before-timer") {
          assert(elapsedGuard); assert.equal(elapsedGuard.C_input_bytes, 0);
          assert(["runtime_unavailable", "signer_transport_timeout"].includes(result.error.code));
        }
        if (mode === "Cdeath") assert.equal((await native.ended).signal, "SIGKILL");
        if (mode === "cancel-preG") assert.equal(ownerResult.terminal.cancel_observed, true);
        if (mode === "control-eof") assert.equal(ownerResult.terminal.outcome, "control_lost");
      }
      assert(owner.isCollected() && native.isCollected());
      await new Promise<void>((yes) => setImmediate(yes));
      if (mode.startsWith("timeout")) {
        // Same dispatcher/context after actual aggregate settlement; no factory
        // recreation to erase busy/quarantine. Fresh C/O/W, same original image.
        ({ owner, native } = await preparePair());
        mode = "normal"; invalidated = false; pending = undefined;
        portSettled = new Promise<void>((yes) => { settlePort = yes; });
        void native.ended.then(() => { if (!owner.isCollected()) localCancel("C_actual_close"); });
        const fresh = await run(); assert.equal(fresh.ok, true, JSON.stringify(fresh));
        await portSettled; assert(owner.isCollected() && native.isCollected());
        assert.deepEqual(fresh.result.signer_response, basic.response);
        console.log(JSON.stringify({ case: id, fresh_same_factory_after_actual_collection: true, C_input_bytes: native.inputBytes() }));
      }
    } finally {
      release(); if (!owner.isCollected()) owner.cancel();
      await native.dispose();
      if (opens) await portSettled; else await owner.settle();
      if (pending) await pending.catch(() => {});
    }
    console.log(JSON.stringify({ case: id, pass: true, all_collected: true }));
  }
  if (deadlineFocus) {
    await exchangeCase("elapsed-before-timer", "FG2_elapsed_deadline_before_timer_callback");
    return;
  }
  await exchangeCase("preadmission", "FG0_actual_pre_admission_refusal");
  await exchangeCase("normal", "FG1_normal259");
  await exchangeCase("timeout-preG", "FG2_timeout_preG");
  await exchangeCase("timeout-late", "FG2_timeout_late");
  await exchangeCase("elapsed-before-timer", "FG2_elapsed_deadline_before_timer_callback");
  await exchangeCase("cancel-preG", "FG3_cancel_preG");
  await exchangeCase("cancel-late", "FG3_cancel_late");
  await exchangeCase("generation", "FG4_generation");
  await exchangeCase("Cdeath", "FG5_C_SIGKILL_preG");
  await exchangeCase("control-eof", "FG6_control_EOF_preG");
  for (const [id, opcode] of [["FG3_cancel_preP", "X"], ["FG6_invalid_opcode", "Z"],
    ["FG6_duplicate_P", "PP"], ["FG6_premature_G", "G"]] as const) {
    const { owner, native } = await preparePair();
    try {
      owner.rawControl(opcode);
      const result = await owner.settle(); await native.dispose();
      assert.equal(result.terminal.worker_pid, null); assert.equal(result.terminal.result_bytes, 0);
      assert.equal(native.inputBytes(), 0); assert(native.isCollected() && owner.isCollected());
      assert.equal(result.terminal.outcome, opcode === "X" ? "cancelled" : "control_malformed");
      console.log(JSON.stringify({ case: id, pass: true, W_spawned: 0, C_input_bytes: 0 }));
    } finally { if (!owner.isCollected()) owner.cancel(); await Promise.all([owner.settle(), native.dispose()]); }
  }
  {
    const { owner, native } = await preparePair();
    await native.dispose(); assert(native.isCollected());
    owner.cancel(); const result = await owner.settle();
    assert.equal(result.terminal.worker_pid, null); assert.equal(native.inputBytes(), 0);
    console.log(JSON.stringify({ case: "FG5_C_early_exit_before_P", pass: true, W_spawned: 0, C_input_bytes: 0 }));
  }
  await malformedHelpers(root, contract);
  parserRelationControls(contract);
  console.log(JSON.stringify({ scope: "FG0_through_FG7_host_author_only", groups: 8, pass: true,
    no_component_or_physical_qualification: true }));
}

async function malformedHelpers(root: string, contract: any) {
  // These finite stdlib helpers cannot spawn W. They exercise the live channel
  // parser only; no fake frame/native response or worker-success claim.
  const modes = ["ready-extra", "ready-missing", "status-missing", "status-truncated", "status-overflow",
    "wrong-owner", "wrong-worker", "contradictory-IO", "duplicate-key", "duplicate-terminal", "phase-after-terminal"];
  for (const mode of modes) {
    const script = String.raw`import os,json,time
mode=${JSON.stringify(mode)}
os.write(4,b'RX' if mode=='ready-extra' else b'' if mode=='ready-missing' else b'R');os.close(4)
command=os.read(3,1)
assert command==(b'X' if mode.startswith('ready-') else b'Q')
n=time.monotonic_ns()
r={'v':1,'kind':'terminal','owner_pid':os.getpid(),'outcome':'unused','ownership':'settled','worker_pid':None,'worker_wait':None,'worker_io':{'stdin_closed':None,'stdout_eof':None,'stderr_eof':None,'owned_fds_closed':True},'session_policy_verified':False,'input_bytes_received':0,'input_sha256':None,'G_bytes':0,'image_bytes_sent':0,'stdout_observed':0,'stdout_retained':0,'stderr_observed':0,'stderr_retained':0,'worker_stderr_base64':'','result_bytes':0,'result_sha256':None,'final_worker_eligible':False,'cancel_observed':False,'timing':{'begin_ns':None,'invalidated_ns':str(n),'cleanup_deadline_ns':str(n+4000000000),'settled_ns':str(n),'final_admission_ns':str(n)}}
if mode=='wrong-owner':r['owner_pid']+=1
if mode=='wrong-worker':r['worker_pid']=99
if mode=='contradictory-IO':r['worker_io']['owned_fds_closed']=False
wire=(json.dumps(r,separators=(',',':'))+'\n').encode()
if mode=='status-missing':wire=b''
if mode=='status-truncated':wire=wire[:-1]
if mode=='status-overflow':wire=b'x'*4097
if mode=='duplicate-key':wire=wire.replace(b'{',b'{"v":1,',1)
if mode=='duplicate-terminal':wire+=wire
if mode=='phase-after-terminal':wire+=b'{"kind":"worker_ready"}\n'
if mode.startswith('ready-'):wire=b''
try:os.write(5,wire)
except BrokenPipeError:pass
`;
    const exportDir = process.env.NSEALR_QP01_HELPER_EXPORT;
    if (exportDir) {
      const path = resolve(exportDir, `${mode}.py`);
      writeFileSync(path, script, { flag: "wx" });
      console.log(JSON.stringify({ helper_export: mode, path, sha256: hash(script), intended_command: mode.startsWith("ready-") ? "X" : "Q" }));
      continue;
    }
    let observation: any;
    await assert.rejects(async () => {
      const owner = await prepareOwner(root, contract, ["-B", "-c", script], (value) => { observation = value; });
      owner.rawControl("Q"); await owner.settle();
    });
    // A helper crash/readiness failure cannot satisfy a later malformed-status
    // case. Require its real successful execution and the intended wire defect.
    assert(observation); assert.equal(observation.code, 0); assert.equal(observation.signal, null);
    assert.equal(observation.diagnostic_base64, ""); assert.equal(observation.output_bytes, 0);
    assert(observation.readyEOF && observation.statusEOF && observation.outEOF && observation.errEOF);
    if (mode.startsWith("ready-")) {
      assert.equal(observation.ready_hex, mode === "ready-extra" ? "5258" : "");
      assert.equal(observation.status_bytes, 0); assert(observation.protocol_error);
    } else {
      assert.equal(observation.ready_hex, "52"); assert.equal(observation.readyAccepted, true);
      if (mode === "status-missing") { assert.equal(observation.status_bytes, 0); assert.equal(observation.terminal, undefined); }
      if (mode === "status-truncated") { assert(observation.status_bytes > 0); assert(observation.unconsumed_status_bytes > 0); assert.equal(observation.terminal, undefined); }
      if (mode === "status-overflow") { assert.equal(observation.status_bytes, 4097); assert.match(observation.protocol_error, /status capacity/); }
      if (mode === "wrong-owner") assert.notEqual(observation.terminal.owner_pid, observation.pid);
      if (mode === "wrong-worker") { assert.equal(observation.terminal.worker_pid, 99); assert.equal(observation.terminal.worker_wait, null); }
      if (mode === "contradictory-IO") assert.equal(observation.terminal.worker_io.owned_fds_closed, false);
      if (mode === "duplicate-key") { assert(observation.protocol_error); assert.equal(observation.terminal, undefined); assert.equal(observation.complete_status_records, 1); }
      if (mode === "duplicate-terminal" || mode === "phase-after-terminal") {
        assert(observation.protocol_error); assert.equal(observation.terminal.kind, "terminal"); assert.equal(observation.complete_status_records, 2);
      }
    }
    console.log(JSON.stringify({ case: `FG7_${mode}`, pass: true, helper_only: true, W_spawned: 0 }));
  }
}


function parserRelationControls(contract: any) {
  // Pure validator controls only. All PID/pipe fields below are fabricated
  // values, never process ownership evidence; no child/native call is made.
  const pid = 10001, worker = 10002;
  const output = Buffer.from(contract.independent_oracle.decoded_frame_ascii, "ascii");
  const phase = { v: 1, kind: "worker_ready", owner_pid: pid, worker_pid: worker, ppid: pid,
    sid: worker, pgid: worker, exe_sha256: contract.identities.worker_elf_sha256,
    limits: structuredClone(contract.worker_ready_record.limits), G_bytes: 0, image_bytes_sent: 0,
    fds: [0, 1, 2].map((fd) => ({ fd, target: `pipe:[${100 + fd}]`, dev: "1", ino: String(100 + fd) })) };
  const decoded = { v: 1, kind: "terminal", owner_pid: pid, outcome: "decoded", ownership: "settled",
    worker_pid: worker, worker_wait: { raw_status: 0, exit_code: 0, collector_pid: pid },
    worker_io: { stdin_closed: true, stdout_eof: true, stderr_eof: true, owned_fds_closed: true },
    session_policy_verified: true, input_bytes_received: 172800, input_sha256: contract.independent_oracle.image_sha256,
    G_bytes: 1, image_bytes_sent: 172800, stdout_observed: output.length, stdout_retained: output.length,
    stderr_observed: 0, stderr_retained: 0, worker_stderr_base64: "", result_bytes: output.length,
    result_sha256: hash(output), final_worker_eligible: true, cancel_observed: false,
    timing: { begin_ns: "1", invalidated_ns: null, cleanup_deadline_ns: null, settled_ns: "2", final_admission_ns: "3" } };
  const unused = { ...decoded, outcome: "unused", worker_pid: null, worker_wait: null,
    worker_io: { stdin_closed: null, stdout_eof: null, stderr_eof: null, owned_fds_closed: true },
    session_policy_verified: false, input_bytes_received: 0, input_sha256: null, G_bytes: 0, image_bytes_sent: 0,
    stdout_observed: 0, stdout_retained: 0, result_bytes: 0, result_sha256: null, final_worker_eligible: false,
    timing: { begin_ns: null, invalidated_ns: "1", cleanup_deadline_ns: "4000000001", settled_ns: "2", final_admission_ns: "3" } };
  // Baselines satisfy all old/new checks before the single-relation mutations.
  validatePhase(phase, pid, contract, true, false);
  validateTerminal(decoded, pid, phase, contract, output);
  validateTerminal(unused, pid, undefined, contract, Buffer.alloc(0));
  const cases: [string, string, () => void][] = [
    ["phase-before-P", "worker_phase_requires_presented_P_not_unused", () => validatePhase(phase, pid, contract, false, false)],
    ["phase-after-Q", "worker_phase_requires_presented_P_not_unused", () => validatePhase(phase, pid, contract, true, true)],
    ["unused-with-phase", "unused_has_no_phase", () => validateTerminal(unused, pid, phase, contract, Buffer.alloc(0))],
    ["unused-with-worker", "unused_has_no_worker", () => validateTerminal({ ...unused, worker_pid: worker,
      worker_wait: decoded.worker_wait, worker_io: decoded.worker_io }, pid, undefined, contract, Buffer.alloc(0))],
    ["decoded-stdout-count-mismatch", "decoded_stdout_observed_retained_mismatch", () => validateTerminal(
      { ...decoded, stdout_observed: output.length + 1 }, pid, phase, contract, output)],
    ["decoded-stdout-overflow", "decoded_stdout_overflow", () => validateTerminal(
      { ...decoded, stdout_observed: 513, stdout_retained: 512 }, pid, phase, contract, output)],
    ["decoded-stdout-retained-result-mismatch", "decoded_stdout_retained_result_mismatch", () => validateTerminal(
      { ...decoded, stdout_observed: output.length - 1, stdout_retained: output.length - 1 }, pid, phase, contract, output)],
    ["decoded-stderr-overflow", "decoded_stderr_overflow", () => validateTerminal(
      { ...decoded, stderr_observed: 513, stderr_retained: 512, worker_stderr_base64: Buffer.alloc(512).toString("base64") }, pid, phase, contract, output)],
    ["decoded-stderr-truncation", "decoded_stderr_observed_retained_mismatch", () => validateTerminal(
      { ...decoded, stderr_observed: 10, stderr_retained: 9, worker_stderr_base64: Buffer.alloc(9).toString("base64") }, pid, phase, contract, output)]
  ];
  for (const [id, message, exercise] of cases) {
    assert.throws(exercise, (error) => error instanceof assert.AssertionError && error.message.includes(message));
    console.log(JSON.stringify({ case: `FG7_relation_${id}`, pass: true, pure_synthetic_parser_only: true,
      expected_relation: message, kernel_processes_spawned: 0, C_input_bytes: 0 }));
  }
}
