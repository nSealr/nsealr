import { spawn } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { type Readable, type Writable } from "node:stream";
import { verifySignedEventResponse } from "@nsealr/core";
import { decodeSerialFrame, encodeSerialFrame } from "@nsealr/framing";
import { NSEALR_V0_LIMITS, utf8ByteLength, validateRequest, validateResponse } from "@nsealr/protocol";

export type SignerTransport = {
  readonly name: string;
  exchange(request: unknown): Promise<unknown>;
};

export type SerialLinePort = {
  writeLine(line: string): Promise<void>;
  readLine(): Promise<string | null>;
  close?(): Promise<void> | void;
};

export type SerialLinePortOpener = (path: string) => Promise<SerialLinePort> | SerialLinePort;

// The port owns these streams. Observe the documented implementation hook because
// emitClose:false permits destruction to finish without any public completion event.
function observeDestruction(stream: Readable | Writable, completed: () => void): () => void {
  const original = stream._destroy;
  const descriptor = Object.getOwnPropertyDescriptor(stream, "_destroy");
  const restore = (): void => {
    if (stream._destroy !== observed) return;
    if (descriptor) Object.defineProperty(stream, "_destroy", descriptor);
    else Reflect.deleteProperty(stream, "_destroy");
  };
  function observed(this: Readable | Writable, error: Error | null, callback: (error?: Error | null) => void): void {
    let settled = false;
    const done = (failure?: Error | null): void => {
      if (settled) return;
      settled = true;
      restore();
      // Node queues a possible error event after this callback. One check-phase
      // turn keeps our handler until that nextTick work has run, even in ESM.
      try { callback(failure); } finally { setImmediate(completed); }
    };
    try { original.call(this, error, done); }
    catch (failure) { done(failure instanceof Error ? failure : new Error(String(failure))); }
  }
  try {
    Object.defineProperty(stream, "_destroy", descriptor && "value" in descriptor
      ? { ...descriptor, value: observed }
      : { value: observed, configurable: true, writable: true, enumerable: descriptor?.enumerable ?? false });
  } catch (cause) {
    throw new Error("serial line port requires replaceable stream destruction hooks", { cause });
  }
  return restore;
}

export class SerialLineStreamPort implements SerialLinePort {
  private readonly input: Readable;
  private readonly output: Writable;
  private buffer = "";
  private bufferedBytes = 0;
  private ended = false;
  private inputError: Error | null = null;
  private reading = false;
  private wakeReader: (() => void) | undefined;
  private cancelWrite: ((error: Error) => void) | undefined;
  private restoreInputDestroy: (() => void) | undefined;
  private restoreOutputDestroy: (() => void) | undefined;
  private readonly maxBufferedBytes: number;
  private readonly maxBufferedLines: number;
  private readonly encoding: BufferEncoding;

  constructor(options: { input: Readable; output: Writable; encoding?: BufferEncoding; maxBufferedBytes?: number; maxBufferedLines?: number }) {
    this.maxBufferedBytes = this.limit(options.maxBufferedBytes ?? NSEALR_V0_LIMITS.max_serial_frame_bytes, 1_048_576, "maxBufferedBytes");
    this.maxBufferedLines = this.limit(options.maxBufferedLines ?? 64, 4096, "maxBufferedLines");
    this.encoding = options.encoding ?? "utf8";
    this.input = options.input;
    this.output = options.output;
    if (this.input.destroyed || this.output.destroyed) throw new Error("serial line port stream already closed");
    try {
      this.restoreInputDestroy = observeDestruction(this.input, this.onInputClose);
      if (this.output !== (this.input as unknown)) this.restoreOutputDestroy = observeDestruction(this.output, this.onOutputClose);
      this.input.setEncoding(this.encoding);
      this.input.on("data", this.onData);
      this.input.on("end", this.onEnd);
      this.input.on("error", this.onError);
      this.input.on("close", this.onInputClose);
      if (this.output !== (this.input as unknown)) {
        this.output.on("error", this.onError);
        this.output.on("close", this.onOutputClose);
      }
    } catch (error) {
      this.detachInput();
      this.detachOutput();
      throw error;
    }
  }

  private limit(value: number, max: number, name: string): number {
    if (!Number.isSafeInteger(value) || value < 1 || value > max) throw new Error(`${name} must be an integer in 1..${max}`);
    return value;
  }

  private readonly onData = (chunk: string | Buffer): void => {
    if (this.inputError || this.ended) return;
    const text = typeof chunk === "string" ? chunk : chunk.toString(this.encoding);
    // Check before concatenating so even one oversized delivery is not retained.
    if (text.length > this.maxBufferedBytes || this.bufferedBytes + utf8ByteLength(text) > this.maxBufferedBytes) {
      this.fail(new Error("serial line port buffer exceeded maxBufferedBytes"));
      return;
    }
    let lines = 0;
    for (const char of this.buffer) if (char === "\n") ++lines;
    for (const char of text) if (char === "\n") ++lines;
    const last = text.length ? text.at(-1) : this.buffer.at(-1);
    if (last !== undefined && last !== "\n") ++lines;
    if (lines > this.maxBufferedLines) {
      this.fail(new Error("serial line port buffer exceeded maxBufferedLines"));
      return;
    }
    this.buffer += text;
    this.bufferedBytes += utf8ByteLength(text);
    if (this.buffer.includes("\n")) this.input.pause();
    this.notifyReader();
  };
  private readonly onEnd = (): void => { this.ended = true; this.notifyReader(); };
  private readonly onError = (error: Error): void => this.fail(error instanceof Error ? error : new Error(String(error)));
  private readonly onInputClose = (): void => {
    if (!this.inputError) {
      if (this.input.errored) this.fail(this.input.errored);
      else if (!this.ended || this.cancelWrite) this.fail(new Error("serial line port input closed prematurely"));
    }
    this.detachInput();
  };
  private readonly onOutputClose = (): void => {
    if (!this.inputError) this.fail(this.output.errored ?? new Error("serial line port output closed"));
    this.detachOutput();
  };

  writeLine(line: string): Promise<void> {
    if (this.inputError) return Promise.reject(this.inputError);
    if (this.cancelWrite) return Promise.reject(new Error("serial line port write already pending"));
    const outputLine = line.endsWith("\n") ? line : `${line}\n`;
    if (outputLine.length > NSEALR_V0_LIMITS.max_serial_frame_bytes || utf8ByteLength(outputLine) > NSEALR_V0_LIMITS.max_serial_frame_bytes) {
      return Promise.reject(new Error("serial line port output exceeded max_serial_frame_bytes"));
    }
    return new Promise<void>((resolve, reject) => {
      let settled = false, callbackDone = false, drained = false, returned = false;
      const finish = (error?: Error): void => {
        if (settled || (!error && !(returned && callbackDone && drained))) return;
        settled = true;
        this.cancelWrite = undefined;
        this.output.off("drain", onDrain);
        if (error) reject(error); else resolve();
      };
      const onDrain = (): void => { drained = true; finish(); };
      this.cancelWrite = error => finish(error);
      this.output.on("drain", onDrain);
      try {
        const accepted = this.output.write(outputLine, "utf8", error => {
          if (error) this.fail(error);
          else { callbackDone = true; finish(); }
        });
        drained ||= accepted;
        returned = true;
        finish();
      } catch (error) { this.fail(error instanceof Error ? error : new Error(String(error))); }
    });
  }

  async readLine(): Promise<string | null> {
    if (this.inputError) throw this.inputError;
    if (this.reading) throw new Error("serial line port read already pending");
    this.reading = true;
    try {
      while (true) {
        if (this.inputError) throw this.inputError;
        const newline = this.buffer.indexOf("\n");
        if (newline !== -1 || (this.ended && this.buffer.length)) {
          const length = newline === -1 ? this.buffer.length : newline + 1;
          const line = this.buffer.slice(0, length);
          this.buffer = this.buffer.slice(length);
          this.bufferedBytes -= utf8ByteLength(line);
          if (!this.ended && !this.buffer.includes("\n")) this.input.resume();
          return line;
        }
        if (this.ended) return null;
        await new Promise<void>(resolve => { this.wakeReader = resolve; });
      }
    } finally { this.reading = false; }
  }

  close(): void { this.fail(new Error("serial line port closed")); }

  private fail(error: Error): void {
    if (this.inputError) return;
    this.inputError = error;
    this.buffer = "";
    this.bufferedBytes = 0;
    this.ended = true;
    this.input.pause();
    this.input.off("data", this.onData);
    this.input.off("end", this.onEnd);
    this.cancelWrite?.(error);
    this.notifyReader();
    // Destruction completion (or its close event) removes our remaining handlers.
    // .closed alone is insufficient: Node may still have an error event queued.
    this.input.destroy();
    if (this.output !== (this.input as unknown)) this.output.destroy();
  }
  private detachInput(): void {
    this.restoreInputDestroy?.();
    this.restoreInputDestroy = undefined;
    this.input.off("data", this.onData);
    this.input.off("end", this.onEnd);
    this.input.off("error", this.onError);
    this.input.off("close", this.onInputClose);
  }
  private detachOutput(): void {
    if (this.output === (this.input as unknown)) return;
    this.restoreOutputDestroy?.();
    this.restoreOutputDestroy = undefined;
    this.output.off("error", this.onError);
    this.output.off("close", this.onOutputClose);
  }
  private notifyReader(): void {
    const wake = this.wakeReader;
    this.wakeReader = undefined;
    wake?.();
  }
}

export function readJsonFile(path: string): unknown {
  return JSON.parse(readFileSync(path, "utf8"));
}

export function writeJsonFile(path: string, value: unknown): void {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function assertValidRequest(value: unknown, label = "transport request"): void {
  const validation = validateRequest(value);
  if (!validation.ok) {
    throw new Error(`${label} invalid: ${validation.error}`);
  }
}

function assertValidResponse(value: unknown, label = "transport response"): void {
  const validation = validateResponse(value);
  if (!validation.ok) {
    throw new Error(`${label} invalid: ${validation.error}`);
  }
}

function requestIdOf(value: unknown): string {
  return (value as { request_id: string }).request_id;
}

function assertResponseMatchesRequest(request: unknown, response: unknown, label = "transport response"): void {
  if (requestIdOf(response) !== requestIdOf(request)) {
    throw new Error(`${label} request_id does not match request`);
  }
}

function assertResponseVerifiedAgainstRequest(request: unknown, response: unknown, label = "transport response"): void {
  assertResponseMatchesRequest(request, response, label);
  if ((request as { method?: unknown }).method !== "sign_event" || (response as { ok?: unknown }).ok !== true) {
    return;
  }
  const verification = verifySignedEventResponse(request, response);
  if (!verification.ok) {
    throw new Error(`${label} ${verification.error}`);
  }
}

function serialErrorPayloadMessage(payload: unknown): string {
  if (typeof payload === "string") return payload;
  if (
    typeof payload === "object" &&
    payload !== null &&
    !Array.isArray(payload) &&
    typeof (payload as { error?: unknown }).error === "string"
  ) {
    return (payload as { error: string }).error;
  }
  return JSON.stringify(payload);
}

function truncateUtf8(value: string, maxBytes: number): string {
  let result = "";
  for (const char of value) {
    if (utf8ByteLength(result + char) > maxBytes) {
      return result;
    }
    result += char;
  }
  return result;
}

export class JsonFileTransport implements SignerTransport {
  readonly name = "json-file";
  readonly requestPath: string;
  readonly responsePath: string;

  constructor(options: { requestPath: string; responsePath: string }) {
    this.requestPath = options.requestPath;
    this.responsePath = options.responsePath;
  }

  async writeRequest(request: unknown): Promise<void> {
    assertValidRequest(request);
    writeJsonFile(this.requestPath, request);
  }

  async readResponse(): Promise<unknown> {
    const response = readJsonFile(this.responsePath);
    assertValidResponse(response);
    return response;
  }

  async exchange(request: unknown): Promise<unknown> {
    await this.writeRequest(request);
    const response = await this.readResponse();
    assertResponseVerifiedAgainstRequest(request, response);
    return response;
  }
}

export class JsonLineStdioTransport implements SignerTransport {
  readonly name = "json-line-stdio";
  private readonly command: string;
  private readonly args: string[];
  private readonly cwd?: string;
  private readonly env?: NodeJS.ProcessEnv;
  private readonly maxOutputLineBytes: number;
  private readonly maxStderrBytes: number;
  private readonly responseTimeoutMs: number;

  constructor(options: {
    command: string;
    args?: string[];
    cwd?: string;
    env?: NodeJS.ProcessEnv;
    maxOutputLineBytes?: number;
    maxStderrBytes?: number;
    responseTimeoutMs?: number;
  }) {
    this.command = options.command;
    this.args = options.args ?? [];
    this.cwd = options.cwd;
    this.env = options.env;
    this.maxOutputLineBytes = options.maxOutputLineBytes ?? NSEALR_V0_LIMITS.max_serial_frame_bytes;
    this.maxStderrBytes = options.maxStderrBytes ?? NSEALR_V0_LIMITS.max_serial_frame_bytes;
    this.responseTimeoutMs = options.responseTimeoutMs ?? 30_000;
  }

  async exchange(request: unknown): Promise<unknown> {
    assertValidRequest(request);
    return new Promise((resolve, reject) => {
      const child = spawn(this.command, this.args, {
        cwd: this.cwd,
        env: this.env,
        stdio: ["pipe", "pipe", "pipe"]
      });
      let stdout = "";
      let stderr = "";
      let settled = false;
      const responseTimer = setTimeout(() => {
        fail(new Error(`stdio signer timed out before response after ${this.responseTimeoutMs}ms`));
      }, this.responseTimeoutMs);

      const fail = (error: Error): void => {
        if (settled) return;
        settled = true;
        clearTimeout(responseTimer);
        if (child.exitCode === null && child.signalCode === null && !child.killed) {
          child.kill();
        }
        reject(error);
      };

      const succeed = (response: unknown): void => {
        if (settled) return;
        settled = true;
        clearTimeout(responseTimer);
        resolve(response);
      };

      if (!child.stdin || !child.stdout || !child.stderr) {
        fail(new Error("stdio transport requires piped stdin, stdout, and stderr"));
        return;
      }

      child.stdout.setEncoding("utf8");
      child.stderr.setEncoding("utf8");
      child.stderr.on("data", (chunk: string) => {
        stderr += chunk;
        if (utf8ByteLength(stderr) > this.maxStderrBytes) {
          stderr = `${truncateUtf8(stderr, this.maxStderrBytes)}...<stderr truncated>`;
        }
      });
      child.stdout.on("data", (chunk: string) => {
        stdout += chunk;
        if (utf8ByteLength(stdout) > this.maxOutputLineBytes) {
          fail(new Error("stdio signer stdout exceeded max_output_line_bytes before newline response"));
          return;
        }
        const newlineIndex = stdout.indexOf("\n");
        if (newlineIndex === -1) return;
        const line = stdout.slice(0, newlineIndex);
        try {
          const response = JSON.parse(line);
          assertValidResponse(response);
          assertResponseVerifiedAgainstRequest(request, response);
          succeed(response);
        } catch (error) {
          fail(error instanceof Error ? error : new Error(String(error)));
        }
      });
      child.on("error", fail);
      child.on("close", (code) => {
        if (settled) return;
        fail(new Error(`stdio signer exited before responding with code ${code}; stderr: ${stderr.trim()}`));
      });
      child.stdin.end(`${JSON.stringify(request)}\n`, "utf8");
    });
  }
}

export class SerialFrameTransport implements SignerTransport {
  readonly name = "serial-frame";
  private readonly exchangeFrame: (line: string) => Promise<string>;

  constructor(options: { exchangeFrame: (line: string) => Promise<string> }) {
    this.exchangeFrame = options.exchangeFrame;
  }

  async exchange(request: unknown): Promise<unknown> {
    assertValidRequest(request, "serial frame request");
    const requestLine = encodeSerialFrame({ type: "request", payload: request });
    const responseLine = await this.exchangeFrame(requestLine);
    const responseFrame = decodeSerialFrame(responseLine);
    if (responseFrame.type === "error") {
      throw new Error(`serial frame transport error: ${serialErrorPayloadMessage(responseFrame.payload)}`);
    }
    if (responseFrame.type !== "response") {
      throw new Error(`serial frame transport expected response frame, got ${responseFrame.type}`);
    }
    assertValidResponse(responseFrame.payload, "serial frame response");
    assertResponseVerifiedAgainstRequest(request, responseFrame.payload, "serial frame response");
    return responseFrame.payload;
  }
}

export class SerialLineTransport implements SignerTransport {
  readonly name = "serial-line";
  private readonly port: SerialLinePort;
  private readonly maxIgnoredLines: number;
  private readonly responseTimeoutMs: number;

  constructor(options: { port: SerialLinePort; maxIgnoredLines?: number; responseTimeoutMs?: number }) {
    this.port = options.port;
    this.maxIgnoredLines = options.maxIgnoredLines ?? 32;
    this.responseTimeoutMs = options.responseTimeoutMs ?? 30_000;
  }

  async exchange(request: unknown): Promise<unknown> {
    const transport = new SerialFrameTransport({
      exchangeFrame: async (line) => {
        await this.writeLineWithTimeout(line);
        for (let ignored = 0; ignored <= this.maxIgnoredLines; ignored += 1) {
          const responseLine = await this.readLineWithTimeout();
          if (responseLine === null) {
            throw new Error("serial line transport reached end of input before response");
          }
          if (responseLine.startsWith("nsealr1f:")) {
            return responseLine;
          }
        }
        throw new Error("serial line transport did not receive a protocol frame");
      }
    });
    return transport.exchange(request);
  }

  private async writeLineWithTimeout(line: string): Promise<void> {
    await this.withTimeout(
      this.port.writeLine(line),
      `serial line transport timed out before write completed after ${this.responseTimeoutMs}ms`
    );
  }

  private async readLineWithTimeout(): Promise<string | null> {
    return this.withTimeout(
      this.port.readLine(),
      `serial line transport timed out before response after ${this.responseTimeoutMs}ms`
    );
  }

  private async withTimeout<T>(operation: Promise<T>, timeoutMessage: string): Promise<T> {
    let timeout: ReturnType<typeof setTimeout> | undefined;
    try {
      return await Promise.race([
        operation,
        new Promise<never>((_resolve, reject) => {
          timeout = setTimeout(() => {
            reject(new Error(timeoutMessage));
          }, this.responseTimeoutMs);
        })
      ]);
    } finally {
      if (timeout !== undefined) {
        clearTimeout(timeout);
      }
    }
  }
}

export async function exchangeSerialLineRequest(options: {
  path: string;
  request: unknown;
  openPort: SerialLinePortOpener;
  maxIgnoredLines?: number;
  responseTimeoutMs?: number;
}): Promise<unknown> {
  assertValidRequest(options.request, "serial line request");
  const port = await options.openPort(options.path);
  try {
    const transport = new SerialLineTransport({
      port,
      maxIgnoredLines: options.maxIgnoredLines,
      responseTimeoutMs: options.responseTimeoutMs
    });
    return await transport.exchange(options.request);
  } finally {
    await port.close?.();
  }
}
