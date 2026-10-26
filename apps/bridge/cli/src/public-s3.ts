import { spawn } from "node:child_process";
import { randomUUID, createHash } from "node:crypto";
import { writeFile } from "node:fs/promises";
import { linkSync, unlinkSync, lstatSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  createNativeMessagingLocalServiceClient, parseLocalGrantStore,
  handleLocalServiceRequest, type LocalClientIdentity
} from "@nsealr/client";
import { verifySignedEventResponse } from "@nsealr/core";
import { readContextJsonFile } from "../../service/src/context.js";

export const PUBLIC_S3_CLI_CLIENT: LocalClientIdentity = {
  surface: "cli", origin: "cli:nsealr-public-s3", app_name: "nSealr public S3 lab", instance_id: "v01"
};
const KEY = "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9";
export type PublicS3CliFiles = {
  grantStore: string; accountStore: string; routeDriverStore: string; storageApproval: string;
};
export async function dispatchPublicS3(options: PublicS3CliFiles & {
  expectedPublicKey: string; method: "sign_event" | "get_public_key"; out: string;
  ready(signal: AbortSignal): Promise<void>; setupTimeoutMs?: number; operationTimeoutMs?: number;
}): Promise<void> {
  // Capture the immutable expected identity before any application callback.
  const expectedKey = options.expectedPublicKey;
  if (expectedKey !== KEY) throw new Error("public S3 requires independently pinned scalar3 identity");
  try { lstatSync(options.out); throw new Error("public S3 output already exists"); }
  catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; }
  const setupMs = Math.min(options.setupTimeoutMs ?? 120000, 120000);
  const operationMs = Math.min(options.operationTimeoutMs ?? 100000, 100000);
  if (!Number.isSafeInteger(setupMs) || setupMs < 1 || !Number.isSafeInteger(operationMs) || operationMs < 1)
    throw new Error("public S3 timeout unavailable");
  const filePaths = [options.accountStore, options.routeDriverStore, options.storageApproval, options.grantStore];
  const digest = () => createHash("sha256").update(JSON.stringify(filePaths.map(path => readContextJsonFile(path, "public CLI context")))).digest("hex");
  const originalConfig = digest();
  const accounts = readContextJsonFile(options.accountStore, "public accounts") as { accounts?: { account_id: string }[] };
  const accountId = accounts.accounts?.[0]?.account_id;
  if (!accountId || accounts.accounts?.length !== 1) throw new Error("public S3 requires one account");
  const args = [fileURLToPath(new URL("../../service/dist/index.js", import.meta.url)), "--public-s3-lab",
    "--grant-store", options.grantStore, "--account-store", options.accountStore,
    "--route-driver-store", options.routeDriverStore, "--storage-approval", options.storageApproval];
  const child = spawn(process.execPath, args, { stdio: ["pipe", "pipe", "pipe"] });
  let output = Buffer.alloc(0), diagnostic = "", readySeen = false;
  let stdoutEOF = false, stderrEOF = false, stdinFinished = false, exitKnown = false, operationStarted = false;
  let exitCode: number | null = null, exitSignal: string | null = null, failure: Error | undefined;
  let resolveReady!: () => void, rejectReady!: (e: Error) => void;
  const opened = new Promise<void>((resolve, reject) => { resolveReady = resolve; rejectReady = reject; });
  // Attach observation before any early result can reject.
  opened.catch(() => undefined);
  let resolveSettled!: () => void;
  const settled = new Promise<void>(resolve => { resolveSettled = resolve; });
  const fail = (error: Error) => { failure ??= error; rejectReady(error); setupAbort.abort(); };
  child.on("error", error => { fail(error); });
  child.stdout.on("data", (chunk: Buffer) => {
    if (output.length + chunk.length > 16388) { fail(new Error("public service output exceeds IPC bound")); child.kill("SIGTERM"); return; }
    output = Buffer.concat([output, chunk]);
  });
  child.stderr.on("data", (chunk: Buffer) => {
    if (Buffer.byteLength(diagnostic) + chunk.length > 4096) { fail(new Error("public service diagnostics exceed bound")); child.kill("SIGTERM"); return; }
    diagnostic += chunk.toString("utf8");
    if (!readySeen && diagnostic.includes("\n")) {
      try {
        const first = JSON.parse(diagnostic.split("\n")[0]);
        if (first.public_s3_stream_open !== true || typeof first.connection_id !== "string") throw new Error("public stream setup failed");
        readySeen = true; resolveReady();
      } catch { fail(new Error("public stream setup failed: " + diagnostic.slice(0,300))); }
    }
  });
  child.stdout.on("end", () => { stdoutEOF = true; });
  child.stderr.on("end", () => { stderrEOF = true; });
  child.stdin.on("error", error => fail(error));
  child.stdin.on("finish", () => { stdinFinished = true; });
  child.on("exit", (code, signal) => { exitKnown = true; exitCode = code; exitSignal = signal;
    if (!operationStarted || code !== 0 || signal) fail(new Error("public service exited before successful settlement"));
  });
  child.on("close", () => { if (!readySeen) fail(new Error("public service exited before setup")); resolveSettled(); });
  const setupAbort = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const bounded = async <T>(work: Promise<T>, ms: number, label: string): Promise<T> => {
    try { return await Promise.race([work, new Promise<never>((_, reject) => {
      timer = setTimeout(() => reject(new Error(label)), ms);
    })]); } finally { if (timer) clearTimeout(timer); }
  };
  const stop = async () => {
    if (!exitKnown) {
      child.stdin.destroy();
      child.kill("SIGTERM");
      const kill = setTimeout(() => child.kill("SIGKILL"), 4000);
      try { await settled; } finally { clearTimeout(kill); }
    } else await settled;
  };
  try {
    // Setup and operator interaction precede the client operation and its clock.
    await bounded((async () => { await opened; await options.ready(setupAbort.signal); })(), setupMs, "public S3 setup expired");
    if (failure) throw failure;
    const origin = process.hrtime.bigint();
    if (digest() !== originalConfig) throw new Error("public S3 context changed during setup; select again");
    process.stderr.write("Public S3 setup complete; operation clock starts before dispatch/preflight.\n");
    const current = () => {
      if (process.hrtime.bigint() - origin >= BigInt(operationMs) * 1_000_000n) throw new Error("public S3 client absolute deadline expired");
      if (digest() !== originalConfig) throw new Error("public S3 context/grant changed");
    };
    current();
    const request = { version: 2, request_id: "public-s3-" + randomUUID(), method: options.method,
      ...(options.method === "sign_event" ? { params: { event_template: {
        kind: 1, created_at: 1710000000, content: "S3 public physical approval", tags: []
      } } } : {}) };
    let sent = false;
    const client = createNativeMessagingLocalServiceClient({ exchange: async frame => {
      if (sent) throw new Error("public S3 allows one client operation");
      sent = true; current(); child.stdin.end(Buffer.from(frame));
      await settled;
      if (failure) throw failure;
      if (!exitKnown || exitCode !== 0 || exitSignal || !stdoutEOF || !stderrEOF || !stdinFinished)
        throw new Error("public S3 service did not settle successfully: " + diagnostic.slice(-300));
      current();
      return output;
    } });
    operationStarted = true;
    const reply = await bounded(client.dispatchSignerRequest(PUBLIC_S3_CLI_CLIENT, {
      account_id: accountId, method: options.method, implementation_id: "nsealr.s3.public.scalar3.e7f04215.v1",
      custody: "volatile_session", transport: "usb", limits_id: "nsealr.limits.s3.public.e7.v1"
    }, request), operationMs, "public S3 operation expired");
    current();
    if (!reply.ok || !("signer_response" in reply.result)) throw new Error("public S3 dispatch rejected");
    const response = reply.result.signer_response as { result?: { event?: { pubkey?: string }; public_key?: string } };
    if ((options.method === "sign_event" ? response.result?.event?.pubkey : response.result?.public_key) !== expectedKey)
      throw new Error("public S3 response identity differs from original pin");
    if (options.method === "sign_event" && !verifySignedEventResponse(request, response).ok) throw new Error("public S3 response verification failed");
    const grants = parseLocalGrantStore(readContextJsonFile(options.grantStore, "current CLI grants")).grants;
    // Revalidate the live approved grant after child collection and verification.
    const validation = handleLocalServiceRequest({ version: 1, request_id: "public-s3-final-" + randomUUID(),
      operation: "verify_signer_response", params: { client: PUBLIC_S3_CLI_CLIENT, request, response } }, { grants });
    if (!validation.ok || !("validation" in validation.result) || !validation.result.validation.valid)
      throw new Error("public S3 client grant/verification is no longer current");
    current();
    const pending = options.out + "." + randomUUID() + ".pending";
    let linked = false;
    try {
      await writeFile(pending, JSON.stringify({ format: "nsealr.public-s3-roundtrip.v1", request, response,
      expected_public_key: expectedKey, settlement: { exit_code: exitCode, stdout_EOF: stdoutEOF, stderr_EOF: stderrEOF, stdin_finished: stdinFinished },
      limits: "public fixture only; USER/targetCPU/globalC5000 unavailable" }, null, 2) + "\n", { flag: "wx", mode: 0o600 });
      current();
      linkSync(pending, options.out); linked = true;
      current();
    } catch (error) { if (linked) unlinkSync(options.out); throw error; }
    finally { try { unlinkSync(pending); } catch (error) { if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error; } }
  } finally { setupAbort.abort(); await stop(); }
}
