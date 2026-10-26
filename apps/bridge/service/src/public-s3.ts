import { randomUUID, createHash } from "node:crypto";
import { createConnection, type Socket } from "node:net";
import { parseLocalGrantStore, type PublicS3Fixture } from "@nsealr/client";
import { SerialLineStreamPort, type SerialLinePort } from "@nsealr/transport";
import { loadServiceContextFromFiles, readContextJsonFile, type ServiceContextFileOptions } from "./context.js";
import { parseServiceRouteDriverStore } from "./drivers.js";
import { PublicS3Budget } from "./public-s3-budget.js";

const IMPLEMENTATION = "nsealr.s3.public.scalar3.e7f04215.v1";
const KEY = "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9";
async function openStream(path: string): Promise<Socket> {
  return new Promise((resolve, reject) => {
    const stream = createConnection(path);
    const header = Buffer.from("nsealr-public-usb-open-v1\n", "ascii");
    let received = 0;
    const timer = setTimeout(() => failed(new Error("public USB relay open handshake expired")), 5000);
    const cleanup = () => { clearTimeout(timer); stream.off("data", data); stream.off("end", ended); stream.off("error", failed); };
    const failed = (error: Error) => { cleanup(); stream.destroy(); reject(error); };
    const ended = () => failed(new Error("public USB relay ended before open handshake"));
    const data = (chunk: Buffer) => {
      if (chunk.length > 8192 + header.length) { failed(new Error("public relay setup buffer exceeded")); return; }
      const take = Math.min(chunk.length, header.length - received);
      if (!chunk.subarray(0,take).equals(header.subarray(received,received+take))) {
        failed(new Error("public USB relay open handshake differs")); return;
      }
      received += take;
      if (received === header.length) {
        cleanup(); stream.pause();
        if (chunk.length > take) stream.unshift(chunk.subarray(take));
        resolve(stream);
      }
    };
    stream.once("error", failed);
    stream.once("end", ended);
    stream.on("data", data);
  });
}
export async function loadPublicS3Context(options: ServiceContextFileOptions) {
  if (options.now !== undefined || !options.grantStorePath || !options.accountStorePath ||
      !options.routeDriverStorePath || !options.storageApprovalPath)
    throw new Error("public S3 requires all approved context files and real grant time");
  let port: SerialLinePort | undefined;
  const context = loadServiceContextFromFiles({ ...options,
    openSerialLinePort: () => { throw new Error("public S3 has no serial/device fallback"); },
    openPublicS3Stream: () => { if (!port) throw new Error("public S3 stream unavailable"); return port; }
  });
  const drivers = parseServiceRouteDriverStore(readContextJsonFile(options.routeDriverStorePath, "route drivers"));
  if (drivers.routes.length !== 1 || drivers.routes[0].driver !== "public_s3_stream")
    throw new Error("public S3 requires exactly one local lab stream");
  const route = drivers.routes[0];
  if (context.accounts?.length !== 1 || context.accounts[0].account_id !== route.account_id ||
      context.accounts[0].implementation_id !== IMPLEMENTATION || context.accounts[0].public_key !== KEY ||
      context.accounts[0].limits_id !== "nsealr.limits.s3.public.e7.v1" ||
      context.accounts[0].signer_route.custody !== "volatile_session")
    throw new Error("public S3 account/identity/implementation differs");
  const files = [options.accountStorePath, options.routeDriverStorePath, options.storageApprovalPath, options.grantStorePath];
  const digest = () => createHash("sha256").update(JSON.stringify(files.map(path => readContextJsonFile(path, "public context")))).digest("hex");
  const config = digest();
  const stream = await openStream(route.stream_path);
  const raw = new SerialLineStreamPort({ input: stream, output: stream, maxBufferedBytes: 8192, maxBufferedLines: 9 });
  let state: "open" | "settled" | "failed" = "open";
  let generation = 0, closing = false, used = false;
  let closePromise: Promise<void> | undefined;
  let budget: PublicS3Budget | undefined;
  const id = "public-s3-" + randomUUID();
  const fail = () => { if (state !== "failed") ++generation; state = "failed"; };
  const checkStream = () => {
    if (stream.readableEnded || stream.errored || (stream.destroyed && !closing)) fail();
  };
  const requireOpen = () => {
    checkStream();
    if (state !== "open") throw new Error("public S3 stream not open");
  };
  // Readable EOF revokes this narrower lease even with a complete line buffered.
  stream.on("end", fail);
  stream.on("error", fail);
  stream.on("close", () => { if (!closing) fail(); });
  checkStream();
  stream.resume();
  port = {
    async writeLine(line) {
      requireOpen();
      try { await raw.writeLine(line); requireOpen(); } catch (error) { fail(); throw error; }
    },
    async readLine() {
      requireOpen();
      try { const line = await raw.readLine(); if (line === null) fail(); requireOpen(); return line; }
      catch (error) { fail(); throw error; }
    },
    close() {
      if (!closePromise) {
        checkStream();
        closing = true;
        closePromise = raw.close().then(() => { checkStream(); if (state !== "failed") state = "settled"; });
      }
      return closePromise;
    }
  };
  const fixture: PublicS3Fixture = {
    source: "e7f04215fc97808acdafdbf9420f6ef6d0102c5b",
    image_sha256: "7943dbcf4a1e389718b1959086487b6b13cdb50bb0f577ced9d4539c6d1fd7da",
    connection() {
      checkStream();
      if (digest() !== config) fail();
      return { connection_id: id, generation, config_digest: config, state };
    },
    begin() {
      if (!budget) throw new Error("public S3 operation clock is not armed");
      checkStream();
      if (used || state !== "open") throw new Error("public S3 fixture requires a fresh connection");
      used = true; budget.check();
    },
    check() { if (!budget) throw new Error("public S3 budget missing"); budget.check(); },
    phase(phase) { if (!budget) throw new Error("public S3 budget missing"); budget.phase(phase); },
    remainingMs() { if (!budget) throw new Error("public S3 budget missing"); return budget.remainingMs(); }
  };
  context.publicS3Fixture = fixture;
  context.currentGrants = () => parseLocalGrantStore(readContextJsonFile(options.grantStorePath!, "current grants")).grants;
  return {
    context,
    connectionId: id,
    arm() { if (budget) throw new Error("public S3 operation already armed"); budget = new PublicS3Budget(); },
    check() { fixture.check(); if (fixture.connection().state === "failed") throw new Error("public S3 lease changed"); },
    async close() {
      const operation = Promise.resolve(port!.close!());
      let timer: ReturnType<typeof setTimeout> | undefined;
      try {
        await Promise.race([operation, new Promise<never>((_, reject) => {
          timer = setTimeout(() => { fail(); reject(new Error("public S3 close did not settle")); }, 4000);
        })]);
      } finally { if (timer) clearTimeout(timer); }
    }
  };
}
