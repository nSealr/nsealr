#!/usr/bin/env node
import { readSync, writeSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { MAX_NATIVE_MESSAGE_BYTES, NATIVE_MESSAGE_LENGTH_BYTES, decodeNativeMessage, encodeNativeMessage, handleLocalServiceRequestAsync, handleLocalServiceRequest } from "@nsealr/client";
import { SerialLineStreamPort } from "@nsealr/transport";
import { contextArgsFromCliArgs, loadServiceContextFromFiles } from "./context.js";
import { loadPublicS3Context } from "./public-s3.js";
import { nativeHostInstallApprovalJsonFromArgs, nativeHostInstallExecutionJsonFromArgs, nativeHostInstallPlanJsonFromArgs, nativeHostManifestJsonFromArgs } from "./manifest.js";
function nativeMessageError(message) {
    return {
        version: 1,
        request_id: "invalid-service-request",
        ok: false,
        error: {
            code: "invalid_native_message",
            message,
            retryable: false
        }
    };
}
export function runServiceOnce(input, context = {}) {
    try {
        return encodeNativeMessage(handleLocalServiceRequest(decodeNativeMessage(input), context));
    }
    catch (error) {
        return encodeNativeMessage(nativeMessageError(error instanceof Error ? error.message : String(error)));
    }
}
export async function runServiceOnceAsync(input, context = {}) {
    try {
        return encodeNativeMessage(await handleLocalServiceRequestAsync(decodeNativeMessage(input), context));
    }
    catch (error) {
        return encodeNativeMessage(nativeMessageError(error instanceof Error ? error.message : String(error)));
    }
}
function messageLength(prefix) {
    if (prefix.byteLength !== NATIVE_MESSAGE_LENGTH_BYTES) {
        throw new Error("native message frame missing length prefix");
    }
    return new DataView(prefix.buffer, prefix.byteOffset, prefix.byteLength).getUint32(0, true);
}
function concatFrame(prefix, payload) {
    const frame = new Uint8Array(prefix.byteLength + payload.byteLength);
    frame.set(prefix, 0);
    frame.set(payload, prefix.byteLength);
    return frame;
}
function readFrameFromBuffer(input, offset) {
    if (input.byteLength - offset < NATIVE_MESSAGE_LENGTH_BYTES) {
        throw new Error("native message frame missing length prefix");
    }
    const prefix = input.slice(offset, offset + NATIVE_MESSAGE_LENGTH_BYTES);
    const length = messageLength(prefix);
    if (length > MAX_NATIVE_MESSAGE_BYTES) {
        throw new Error("native message exceeds max bytes");
    }
    const frameEnd = offset + NATIVE_MESSAGE_LENGTH_BYTES + length;
    if (frameEnd > input.byteLength) {
        throw new Error("native message length prefix does not match payload");
    }
    return {
        frame: input.slice(offset, frameEnd),
        nextOffset: frameEnd
    };
}
function encodeNativeMessageError(message) {
    return encodeNativeMessage(nativeMessageError(message));
}
export function runServiceFrames(input, context = {}) {
    const outputs = [];
    let offset = 0;
    while (offset < input.byteLength) {
        try {
            const { frame, nextOffset } = readFrameFromBuffer(input, offset);
            outputs.push(runServiceOnce(frame, context));
            offset = nextOffset;
        }
        catch (error) {
            outputs.push(encodeNativeMessageError(error instanceof Error ? error.message : String(error)));
            break;
        }
    }
    return Buffer.concat(outputs.map((output) => Buffer.from(output)));
}
export async function runServiceFramesAsync(input, context = {}) {
    const outputs = [];
    let offset = 0;
    while (offset < input.byteLength) {
        try {
            const { frame, nextOffset } = readFrameFromBuffer(input, offset);
            outputs.push(await runServiceOnceAsync(frame, context));
            offset = nextOffset;
        }
        catch (error) {
            outputs.push(encodeNativeMessageError(error instanceof Error ? error.message : String(error)));
            break;
        }
    }
    return Buffer.concat(outputs.map((output) => Buffer.from(output)));
}
function readExactly(fd, byteLength) {
    const buffer = Buffer.alloc(byteLength);
    let offset = 0;
    while (offset < byteLength) {
        const bytesRead = readSync(fd, buffer, offset, byteLength - offset, null);
        if (bytesRead === 0) {
            if (offset === 0)
                return undefined;
            throw new Error("native message length prefix does not match payload");
        }
        offset += bytesRead;
    }
    return buffer;
}
function readNativeFrameFromFd(inputFd) {
    const prefix = readExactly(inputFd, NATIVE_MESSAGE_LENGTH_BYTES);
    if (prefix === undefined)
        return undefined;
    const length = messageLength(prefix);
    if (length > MAX_NATIVE_MESSAGE_BYTES) {
        throw new Error("native message exceeds max bytes");
    }
    const payload = readExactly(inputFd, length);
    if (payload === undefined) {
        throw new Error("native message length prefix does not match payload");
    }
    return concatFrame(prefix, payload);
}
export function runServiceStdio(options = {}) {
    const inputFd = options.inputFd ?? 0;
    const outputFd = options.outputFd ?? 1;
    const context = options.context ?? {};
    while (true) {
        try {
            const frame = readNativeFrameFromFd(inputFd);
            if (frame === undefined)
                return;
            writeSync(outputFd, runServiceOnce(frame, context));
        }
        catch (error) {
            writeSync(outputFd, encodeNativeMessageError(error instanceof Error ? error.message : String(error)));
            return;
        }
    }
}
export async function runServiceStdioAsync(options = {}) {
    const inputFd = options.inputFd ?? 0;
    const outputFd = options.outputFd ?? 1;
    const context = options.context ?? {};
    while (true) {
        try {
            const frame = readNativeFrameFromFd(inputFd);
            if (frame === undefined)
                return;
            writeSync(outputFd, await runServiceOnceAsync(frame, context));
        }
        catch (error) {
            writeSync(outputFd, encodeNativeMessageError(error instanceof Error ? error.message : String(error)));
            return;
        }
    }
}
async function openNodeSerialLinePort(path) {
    const { SerialPort } = await import("serialport");
    const serialPort = new SerialPort({ path, baudRate: 115_200, autoOpen: false });
    await new Promise((resolve, reject) => {
        serialPort.open((error) => {
            if (error) {
                reject(error);
                return;
            }
            resolve();
        });
    });
    return new SerialLineStreamPort({ input: serialPort, output: serialPort });
}
export async function runServiceCli(args) {
    if (args.length === 0) {
        await runServiceStdioAsync();
        return;
    }
    try {
        const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
        if (normalizedArgs.includes("--public-s3-lab")) {
            if (normalizedArgs.filter(arg => arg === "--public-s3-lab").length !== 1)
                throw new Error("duplicate public S3 opt-in");
            const session = await loadPublicS3Context(contextArgsFromCliArgs(normalizedArgs.filter(arg => arg !== "--public-s3-lab")));
            try {
                writeSync(2, JSON.stringify({ public_s3_stream_open: true, connection_id: session.connectionId }) + "\n");
                const frame = readNativeFrameFromFd(0);
                if (!frame)
                    throw new Error("public S3 requires one client request");
                session.arm();
                const request = decodeNativeMessage(frame);
                const output = await runServiceOnceAsync(frame, session.context);
                await session.close();
                const reply = decodeNativeMessage(output);
                if (reply.ok && reply.result?.signer_response !== undefined) {
                    // Recheck the live approved grant after crypto and actual close.
                    const verified = handleLocalServiceRequest({ version: 1, request_id: "public-s3-final-check",
                        operation: "verify_signer_response", params: { client: request.params?.client,
                            request: request.params?.request, response: reply.result.signer_response } }, { grants: session.context.currentGrants() });
                    if (!verified.ok || !("validation" in verified.result) || !verified.result.validation.valid)
                        throw new Error("public S3 final live grant/response check failed");
                    session.check();
                }
                writeSync(1, output);
            }
            finally {
                await session.close();
            }
            return;
        }
        if (normalizedArgs.includes("--native-host-manifest")) {
            writeSync(1, nativeHostManifestJsonFromArgs(args));
            return;
        }
        if (normalizedArgs.includes("--native-host-install-plan")) {
            writeSync(1, nativeHostInstallPlanJsonFromArgs(args));
            return;
        }
        if (normalizedArgs.includes("--native-host-install-approval")) {
            writeSync(1, nativeHostInstallApprovalJsonFromArgs(args));
            return;
        }
        if (normalizedArgs.includes("--native-host-install-execute")) {
            writeSync(1, await nativeHostInstallExecutionJsonFromArgs(args, {
                async ensureDirectory(path) {
                    await mkdir(path, { recursive: true });
                },
                writeFileNew(path, contents) {
                    return writeFile(path, contents, { encoding: "utf8", flag: "wx" });
                }
            }));
            return;
        }
        await runServiceStdioAsync({
            context: loadServiceContextFromFiles({
                ...contextArgsFromCliArgs(args),
                openSerialLinePort: openNodeSerialLinePort
            })
        });
    }
    catch (error) {
        writeSync(2, `${error instanceof Error ? error.message : String(error)}\n`);
        process.exitCode = 1;
    }
}
if (import.meta.url === `file://${process.argv[1]}`) {
    runServiceCli(process.argv.slice(2)).catch((error) => {
        writeSync(2, `${error instanceof Error ? error.message : String(error)}\n`);
        process.exitCode = 1;
    });
}
