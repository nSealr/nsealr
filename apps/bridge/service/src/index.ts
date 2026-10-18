#!/usr/bin/env node
import { readSync, writeSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import {
  MAX_NATIVE_MESSAGE_BYTES,
  NATIVE_MESSAGE_LENGTH_BYTES,
  decodeNativeMessage,
  encodeNativeMessage,
  handleLocalServiceRequestAsync,
  handleLocalServiceRequest,
  type LocalServiceContext,
  type LocalServiceResponse
} from "@nsealr/client";
import { SerialLineStreamPort, type SerialLinePort } from "@nsealr/transport";
import { contextArgsFromCliArgs, loadServiceContextFromFiles } from "./context.js";
import {
  nativeHostInstallApprovalJsonFromArgs,
  nativeHostInstallExecutionJsonFromArgs,
  nativeHostInstallPlanJsonFromArgs,
  nativeHostManifestJsonFromArgs
} from "./manifest.js";

function nativeMessageError(message: string): LocalServiceResponse {
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

export function runServiceOnce(input: Uint8Array, context: LocalServiceContext = {}): Uint8Array {
  try {
    return encodeNativeMessage(handleLocalServiceRequest(decodeNativeMessage(input), context));
  } catch (error) {
    return encodeNativeMessage(nativeMessageError(error instanceof Error ? error.message : String(error)));
  }
}

export async function runServiceOnceAsync(input: Uint8Array, context: LocalServiceContext = {}): Promise<Uint8Array> {
  try {
    return encodeNativeMessage(await handleLocalServiceRequestAsync(decodeNativeMessage(input), context));
  } catch (error) {
    return encodeNativeMessage(nativeMessageError(error instanceof Error ? error.message : String(error)));
  }
}

function messageLength(prefix: Uint8Array): number {
  if (prefix.byteLength !== NATIVE_MESSAGE_LENGTH_BYTES) {
    throw new Error("native message frame missing length prefix");
  }
  return new DataView(prefix.buffer, prefix.byteOffset, prefix.byteLength).getUint32(0, true);
}

function concatFrame(prefix: Uint8Array, payload: Uint8Array): Uint8Array {
  const frame = new Uint8Array(prefix.byteLength + payload.byteLength);
  frame.set(prefix, 0);
  frame.set(payload, prefix.byteLength);
  return frame;
}

function readFrameFromBuffer(input: Uint8Array, offset: number): { frame: Uint8Array; nextOffset: number } {
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

function encodeNativeMessageError(message: string): Uint8Array {
  return encodeNativeMessage(nativeMessageError(message));
}

export function runServiceFrames(input: Uint8Array, context: LocalServiceContext = {}): Uint8Array {
  const outputs: Uint8Array[] = [];
  let offset = 0;

  while (offset < input.byteLength) {
    try {
      const { frame, nextOffset } = readFrameFromBuffer(input, offset);
      outputs.push(runServiceOnce(frame, context));
      offset = nextOffset;
    } catch (error) {
      outputs.push(encodeNativeMessageError(error instanceof Error ? error.message : String(error)));
      break;
    }
  }

  return Buffer.concat(outputs.map((output) => Buffer.from(output)));
}

export async function runServiceFramesAsync(input: Uint8Array, context: LocalServiceContext = {}): Promise<Uint8Array> {
  const outputs: Uint8Array[] = [];
  let offset = 0;

  while (offset < input.byteLength) {
    try {
      const { frame, nextOffset } = readFrameFromBuffer(input, offset);
      outputs.push(await runServiceOnceAsync(frame, context));
      offset = nextOffset;
    } catch (error) {
      outputs.push(encodeNativeMessageError(error instanceof Error ? error.message : String(error)));
      break;
    }
  }

  return Buffer.concat(outputs.map((output) => Buffer.from(output)));
}

function readExactly(fd: number, byteLength: number): Uint8Array | undefined {
  const buffer = Buffer.alloc(byteLength);
  let offset = 0;
  while (offset < byteLength) {
    const bytesRead = readSync(fd, buffer, offset, byteLength - offset, null);
    if (bytesRead === 0) {
      if (offset === 0) return undefined;
      throw new Error("native message length prefix does not match payload");
    }
    offset += bytesRead;
  }
  return buffer;
}

function readNativeFrameFromFd(inputFd: number): Uint8Array | undefined {
  const prefix = readExactly(inputFd, NATIVE_MESSAGE_LENGTH_BYTES);
  if (prefix === undefined) return undefined;
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

export function runServiceStdio(options: {
  context?: LocalServiceContext;
  inputFd?: number;
  outputFd?: number;
} = {}): void {
  const inputFd = options.inputFd ?? 0;
  const outputFd = options.outputFd ?? 1;
  const context = options.context ?? {};

  while (true) {
    try {
      const frame = readNativeFrameFromFd(inputFd);
      if (frame === undefined) return;
      writeSync(outputFd, runServiceOnce(frame, context));
    } catch (error) {
      writeSync(outputFd, encodeNativeMessageError(error instanceof Error ? error.message : String(error)));
      return;
    }
  }
}

export async function runServiceStdioAsync(options: {
  context?: LocalServiceContext;
  inputFd?: number;
  outputFd?: number;
} = {}): Promise<void> {
  const inputFd = options.inputFd ?? 0;
  const outputFd = options.outputFd ?? 1;
  const context = options.context ?? {};

  while (true) {
    try {
      const frame = readNativeFrameFromFd(inputFd);
      if (frame === undefined) return;
      writeSync(outputFd, await runServiceOnceAsync(frame, context));
    } catch (error) {
      writeSync(outputFd, encodeNativeMessageError(error instanceof Error ? error.message : String(error)));
      return;
    }
  }
}

async function openNodeSerialLinePort(path: string): Promise<SerialLinePort> {
  const { SerialPort } = await import("serialport");
  const serialPort = new SerialPort({ path, baudRate: 115_200, autoOpen: false });
  await new Promise<void>((resolve, reject) => {
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

export async function runServiceCli(args: string[]): Promise<void> {
  if (args.length === 0) {
    await runServiceStdioAsync();
    return;
  }
  try {
    const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
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
  } catch (error) {
    writeSync(2, `${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runServiceCli(process.argv.slice(2)).catch((error: unknown) => {
    writeSync(2, `${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  });
}
