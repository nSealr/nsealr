import { randomUUID, createHash } from "node:crypto";
import { createConnection } from "node:net";
import { parseLocalGrantStore } from "@nsealr/client";
import { SerialLineStreamPort } from "@nsealr/transport";
import { loadServiceContextFromFiles, readContextJsonFile } from "./context.js";
import { parseServiceRouteDriverStore } from "./drivers.js";
import { PublicS3Budget } from "./public-s3-budget.js";
const IMPLEMENTATION = "nsealr.s3.public.scalar3.e7f04215.v1";
const KEY = "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9";
async function openStream(path) {
    return new Promise((resolve, reject) => {
        const stream = createConnection(path);
        const failed = (error) => { stream.destroy(); reject(error); };
        stream.once("error", failed);
        stream.once("connect", () => { stream.off("error", failed); resolve(stream); });
    });
}
export async function loadPublicS3Context(options) {
    if (options.now !== undefined || !options.grantStorePath || !options.accountStorePath ||
        !options.routeDriverStorePath || !options.storageApprovalPath)
        throw new Error("public S3 requires all approved context files and real grant time");
    let port;
    const context = loadServiceContextFromFiles({ ...options,
        openSerialLinePort: () => { throw new Error("public S3 has no serial/device fallback"); },
        openPublicS3Stream: () => { if (!port)
            throw new Error("public S3 stream unavailable"); return port; }
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
    let state = "open";
    let generation = 0, closing = false, used = false;
    let closePromise;
    let budget;
    const id = "public-s3-" + randomUUID();
    const fail = () => { if (state !== "failed")
        ++generation; state = "failed"; };
    stream.on("error", fail);
    stream.on("close", () => { if (!closing)
        fail(); });
    port = {
        async writeLine(line) {
            if (state !== "open")
                throw new Error("public S3 stream not open");
            try {
                await raw.writeLine(line);
            }
            catch (error) {
                fail();
                throw error;
            }
        },
        async readLine() {
            try {
                const line = await raw.readLine();
                if (line === null)
                    fail();
                return line;
            }
            catch (error) {
                fail();
                throw error;
            }
        },
        close() {
            if (!closePromise) {
                closing = true;
                closePromise = raw.close().then(() => { if (state !== "failed")
                    state = "settled"; });
            }
            return closePromise;
        }
    };
    const fixture = {
        source: "e7f04215fc97808acdafdbf9420f6ef6d0102c5b",
        image_sha256: "7943dbcf4a1e389718b1959086487b6b13cdb50bb0f577ced9d4539c6d1fd7da",
        connection() {
            if (digest() !== config || stream.destroyed && !closing)
                fail();
            return { connection_id: id, generation, config_digest: config, state };
        },
        begin() {
            if (!budget)
                throw new Error("public S3 operation clock is not armed");
            if (used || state !== "open")
                throw new Error("public S3 fixture requires a fresh connection");
            used = true;
            budget.check();
        },
        check() { if (!budget)
            throw new Error("public S3 budget missing"); budget.check(); },
        phase(phase) { if (!budget)
            throw new Error("public S3 budget missing"); budget.phase(phase); },
        remainingMs() { if (!budget)
            throw new Error("public S3 budget missing"); return budget.remainingMs(); }
    };
    context.publicS3Fixture = fixture;
    context.currentGrants = () => parseLocalGrantStore(readContextJsonFile(options.grantStorePath, "current grants")).grants;
    return {
        context,
        connectionId: id,
        arm() { if (budget)
            throw new Error("public S3 operation already armed"); budget = new PublicS3Budget(); },
        check() { fixture.check(); if (fixture.connection().state === "failed")
            throw new Error("public S3 lease changed"); },
        async close() {
            const operation = Promise.resolve(port.close());
            let timer;
            try {
                await Promise.race([operation, new Promise((_, reject) => {
                        timer = setTimeout(() => { fail(); reject(new Error("public S3 close did not settle")); }, 4000);
                    })]);
            }
            finally {
                if (timer)
                    clearTimeout(timer);
            }
        }
    };
}
