// Existing finite public-fixture C-leaf; no CLI, provider, key or process at import.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import type { spawn } from "node:child_process";
import type { Readable, Writable } from "node:stream";

export interface NativeLeafDependencies {
  root: string;
  spawn: typeof spawn;
  timers: { setTimeout: typeof setTimeout; clearTimeout: typeof clearTimeout };
  onSpawn(): void;
  onCollected(): void;
  reportSettlement(record: Record<string, unknown>): void;
  reportObservation(record: unknown): void;
}

export function createPrepareNative(dependencies: NativeLeafDependencies) {
  const { root, spawn, timers, onSpawn, onCollected, reportSettlement, reportObservation } = dependencies;
  return async function prepareNative(hold = false, env = process.env, syntheticArgv?: string[]) {
    const python = env.NSEALR_QP01_PYTHON;
    assert(python && env.NSEALR_QP01_LIBRARY && env.NSEALR_QP01_LIBRARY_SHA256);
    const argv = syntheticArgv ?? ["-B", resolve(root, "docs/restart/implementation/QP01/request-engine/exchange.py"),
      "--ready-fd", "4", ...(hold ? ["--settlement-fd", "3"] : [])];
    const child = spawn(python, argv, { cwd: root, env, stdio: ["pipe", "pipe", "pipe", "pipe", "pipe"] });
    const spawnedAt = process.hrtime.bigint();
    const safety = timers.setTimeout(() => child.kill("SIGKILL"), 5000);
    onSpawn();
    const stdout: Buffer[] = [], stderr: Buffer[] = [];
    let out = 0, err = 0, overflow = false, notified = false, sent = false, reaped = false, disposing = false;
    let readyBytes = Buffer.alloc(0), readyAt: bigint | undefined, sentAt: bigint | undefined;
    let closedAt: bigint | undefined, spawnError: Error | undefined;
    let sentBytes: number | undefined;
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
        reaped = true; onCollected(); closedAt = process.hrtime.bigint(); timers.clearTimeout(safety);
        readyNo(new Error("child closed before readiness"));
        reportSettlement({ pid: child.pid, code, signal,
          synthetic_handshake_control: !!syntheticArgv, sent, readiness_hex: readyBytes.toString("hex"),
          stdout_bytes: out, stderr_bytes: err, overflow,
          initialization_ns: readyAt === undefined ? null : String(readyAt - spawnedAt),
          request_to_close_ns: sentAt === undefined ? null : String(closedAt - sentAt) });
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
      // Observations for the explicit ownership gate; this remains the sole C owner/timer.
      ended, pid: child.pid, inputBytes: () => sent ? (sentBytes ?? 0) : 0,
      killOwned: () => child.kill("SIGKILL"),
      async send(frame: string, onHeld?: (release: () => void) => void): Promise<string> {
        assert(!sent && !reaped && readyAt !== undefined && !overflow);
        assert(Buffer.byteLength(frame) <= 947);
        sent = true; sentBytes = Buffer.byteLength(frame); sentAt = process.hrtime.bigint(); held = onHeld;
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
        reportObservation(trace);
        return response;
      }
    };
  };
}
