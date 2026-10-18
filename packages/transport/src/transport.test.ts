import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { PassThrough } from "node:stream";
import { once } from "node:events";
import { describe, expect, it } from "vitest";
import { resolveSpecsRoot } from "@nsealr/fixtures";
import { decodeSerialFrame, encodeSerialFrame } from "@nsealr/framing";
import { validateResponse } from "@nsealr/protocol";
import {
  JsonFileTransport,
  JsonLineStdioTransport,
  SerialFrameTransport,
  SerialLineStreamPort,
  SerialLineTransport,
  exchangeSerialLineRequest,
  readJsonFile,
  writeJsonFile
} from "./transport.js";

const specsRoot = resolveSpecsRoot();
const key = JSON.parse(readFileSync(resolve(specsRoot, "vectors/keys/test-key-1.json"), "utf8")) as {
  secret_key: string;
};
const signEventRequest = JSON.parse(readFileSync(resolve(specsRoot, "examples/request-kind-1-basic.json"), "utf8"));
const signingDisabledResponse = JSON.parse(
  readFileSync(resolve(specsRoot, "examples/response-sign-event-disabled-esp32-s3-scaffold.json"), "utf8")
);
const capabilitiesRequest = JSON.parse(readFileSync(resolve(specsRoot, "examples/request-get-capabilities.json"), "utf8"));
const capabilitiesResponse = JSON.parse(
  readFileSync(resolve(specsRoot, "examples/response-get-capabilities-esp32-s3-scaffold.json"), "utf8")
);
const publicKeyVector = JSON.parse(
  readFileSync(resolve(specsRoot, "vectors/devices/esp32-s3-get-public-key-dev.json"), "utf8")
);
const basicEventVector = JSON.parse(readFileSync(resolve(specsRoot, "vectors/events/kind-1-basic.json"), "utf8"));

describe("transport adapters", () => {
  it("moves request and response JSON through files", async () => {
    const tempRoot = mkdtempSync(join(tmpdir(), "nsealr-file-"));
    const requestPath = join(tempRoot, "request.json");
    const responsePath = join(tempRoot, "response.json");
    const transport = new JsonFileTransport({ requestPath, responsePath });
    const expectedResponse = {
      version: 1,
      request_id: signEventRequest.request_id,
      ok: false,
      error: {
        code: "user_rejected",
        message: "Rejected in file handoff test",
        retryable: false
      }
    };

    await transport.writeRequest(signEventRequest);
    writeJsonFile(responsePath, expectedResponse);

    expect(readJsonFile(requestPath)).toEqual(signEventRequest);
    await expect(transport.readResponse()).resolves.toEqual(expectedResponse);
  });

  it("rejects file transport exchange responses for a different request id", async () => {
    const tempRoot = mkdtempSync(join(tmpdir(), "nsealr-file-mismatched-response-"));
    const requestPath = join(tempRoot, "request.json");
    const responsePath = join(tempRoot, "response.json");
    const transport = new JsonFileTransport({ requestPath, responsePath });
    writeJsonFile(responsePath, {
      version: 1,
      request_id: "different-request",
      ok: false,
      error: {
        code: "user_rejected",
        message: "Rejected in file handoff test",
        retryable: false
      }
    });

    await expect(transport.exchange(signEventRequest)).rejects.toThrow("transport response request_id does not match request");
  });

  it("rejects invalid file transport requests before writing them", async () => {
    const tempRoot = mkdtempSync(join(tmpdir(), "nsealr-file-invalid-request-"));
    const requestPath = join(tempRoot, "request.json");
    const responsePath = join(tempRoot, "response.json");
    const transport = new JsonFileTransport({ requestPath, responsePath });

    await expect(transport.writeRequest({ version: 1, request_id: "bad request id", method: "get_capabilities" })).rejects.toThrow(
      "transport request invalid: request_id is invalid"
    );
    expect(() => readFileSync(requestPath, "utf8")).toThrow();
  });

  it("rejects invalid file transport responses before returning them", async () => {
    const tempRoot = mkdtempSync(join(tmpdir(), "nsealr-file-invalid-response-"));
    const requestPath = join(tempRoot, "request.json");
    const responsePath = join(tempRoot, "response.json");
    const transport = new JsonFileTransport({ requestPath, responsePath });

    writeJsonFile(responsePath, { version: 1, request_id: signEventRequest.request_id });

    await expect(transport.readResponse()).rejects.toThrow("transport response invalid: ok must be true or false");
    expect(() => readFileSync(requestPath, "utf8")).toThrow();
  });

  it("exchanges one JSON request and response over stdio JSON lines", async () => {
    const tempRoot = mkdtempSync(join(tmpdir(), "nsealr-stdio-"));
    const signerPath = join(tempRoot, "stdio-signer.mjs");
    writeFileSync(
      signerPath,
      [
        "import { createInterface } from 'node:readline';",
        "const rl = createInterface({ input: process.stdin });",
        "rl.once('line', (line) => {",
        "  const request = JSON.parse(line);",
        "  process.stdout.write(JSON.stringify({",
        "    version: 1,",
        "    request_id: request.request_id,",
        "    ok: false,",
        "    error: { code: 'user_rejected', message: 'Rejected by stdio test signer', retryable: false }",
        "  }) + '\\n');",
        "});"
      ].join("\n"),
      "utf8"
    );

    const transport = new JsonLineStdioTransport({
      command: process.execPath,
      args: [signerPath]
    });

    await expect(transport.exchange(signEventRequest)).resolves.toEqual({
      version: 1,
      request_id: signEventRequest.request_id,
      ok: false,
      error: {
        code: "user_rejected",
        message: "Rejected by stdio test signer",
        retryable: false
      }
    });
  });

  it("rejects stdio transport responses for a different request id", async () => {
    const tempRoot = mkdtempSync(join(tmpdir(), "nsealr-stdio-mismatched-response-"));
    const signerPath = join(tempRoot, "stdio-signer.mjs");
    writeFileSync(
      signerPath,
      [
        "import { createInterface } from 'node:readline';",
        "const rl = createInterface({ input: process.stdin });",
        "rl.once('line', () => {",
        "  process.stdout.write(JSON.stringify({",
        "    version: 1,",
        "    request_id: 'different-request',",
        "    ok: false,",
        "    error: { code: 'user_rejected', message: 'Rejected by stdio test signer', retryable: false }",
        "  }) + '\\n');",
        "});"
      ].join("\n"),
      "utf8"
    );
    const transport = new JsonLineStdioTransport({
      command: process.execPath,
      args: [signerPath]
    });

    await expect(transport.exchange(signEventRequest)).rejects.toThrow("transport response request_id does not match request");
  });

  it("rejects invalid stdio transport requests before spawning a signer", async () => {
    const transport = new JsonLineStdioTransport({
      command: "/definitely/missing/nsealr-stdio-signer"
    });

    await expect(transport.exchange({ version: 1, request_id: "bad request id", method: "get_capabilities" })).rejects.toThrow(
      "transport request invalid: request_id is invalid"
    );
  });

  it("rejects invalid stdio transport responses before returning them", async () => {
    const tempRoot = mkdtempSync(join(tmpdir(), "nsealr-stdio-invalid-response-"));
    const signerPath = join(tempRoot, "stdio-signer.mjs");
    writeFileSync(
      signerPath,
      [
        "import { createInterface } from 'node:readline';",
        "const rl = createInterface({ input: process.stdin });",
        "rl.once('line', () => {",
        "  process.stdout.write(JSON.stringify({ version: 1, request_id: 'req-sign-event-1' }) + '\\n');",
        "});"
      ].join("\n"),
      "utf8"
    );

    const transport = new JsonLineStdioTransport({
      command: process.execPath,
      args: [signerPath]
    });

    await expect(transport.exchange(signEventRequest)).rejects.toThrow("transport response invalid: ok must be true or false");
  });

  it("rejects stdio signer output that exceeds the bounded response line buffer", async () => {
    const tempRoot = mkdtempSync(join(tmpdir(), "nsealr-stdio-oversized-output-"));
    const signerPath = join(tempRoot, "stdio-signer.mjs");
    writeFileSync(signerPath, "process.stdout.write('unterminated');\n", "utf8");
    const transport = new JsonLineStdioTransport({
      command: process.execPath,
      args: [signerPath],
      maxOutputLineBytes: 8
    });

    await expect(transport.exchange(signEventRequest)).rejects.toThrow(/stdout exceeded max_output_line_bytes/u);
  });

  it("caps stdio signer stderr included in exit failures", async () => {
    const tempRoot = mkdtempSync(join(tmpdir(), "nsealr-stdio-oversized-stderr-"));
    const signerPath = join(tempRoot, "stdio-signer.mjs");
    writeFileSync(signerPath, "process.stderr.write('diagnostic output');\nprocess.exit(2);\n", "utf8");
    const transport = new JsonLineStdioTransport({
      command: process.execPath,
      args: [signerPath],
      maxStderrBytes: 8
    });

    await expect(transport.exchange(signEventRequest)).rejects.toThrow(/stderr: diagnost\.\.\.<stderr truncated>/u);
  });

  it("rejects silent stdio signers that do not respond before the timeout", async () => {
    const tempRoot = mkdtempSync(join(tmpdir(), "nsealr-stdio-timeout-"));
    const signerPath = join(tempRoot, "stdio-signer.mjs");
    writeFileSync(signerPath, "setTimeout(() => process.exit(0), 200);\n", "utf8");
    const transport = new JsonLineStdioTransport({
      command: process.execPath,
      args: [signerPath],
      responseTimeoutMs: 10
    });

    await expect(
      Promise.race([
        transport.exchange(signEventRequest),
        new Promise<never>((_resolve, reject) => {
          setTimeout(() => reject(new Error("exchange did not time out")), 50);
        })
      ])
    ).rejects.toThrow(/stdio signer timed out before response/u);
  });

  it("exchanges one request and response over serial frames", async () => {
    const transport = new SerialFrameTransport({
      exchangeFrame: async (line) => {
        expect(decodeSerialFrame(line)).toEqual({ type: "request", payload: capabilitiesRequest });
        return encodeSerialFrame({ type: "response", payload: capabilitiesResponse });
      }
    });

    const response = await transport.exchange(capabilitiesRequest);

    expect(response).toEqual(capabilitiesResponse);
    expect(validateResponse(response).ok).toBe(true);
  });

  it("rejects serial response payloads for a different request id", async () => {
    const transport = new SerialFrameTransport({
      exchangeFrame: async () => encodeSerialFrame({
        type: "response",
        payload: { ...capabilitiesResponse, request_id: "different-request" }
      })
    });

    await expect(transport.exchange(capabilitiesRequest)).rejects.toThrow("serial frame response request_id does not match request");
  });

  it("moves ESP32-S3 scaffold signing-disabled responses over serial frames", async () => {
    const transport = new SerialFrameTransport({
      exchangeFrame: async (line) => {
        expect(decodeSerialFrame(line)).toEqual({ type: "request", payload: signEventRequest });
        return encodeSerialFrame({ type: "response", payload: signingDisabledResponse });
      }
    });

    const response = await transport.exchange(signEventRequest);

    expect(response).toEqual(signingDisabledResponse);
    expect(validateResponse(response).ok).toBe(true);
  });

  it("surfaces serial error frames with deterministic diagnostic text", async () => {
    const transport = new SerialFrameTransport({
      exchangeFrame: async () => encodeSerialFrame({ type: "error", payload: { error: "unsupported_request" } })
    });

    await expect(transport.exchange(capabilitiesRequest)).rejects.toThrow(
      "serial frame transport error: unsupported_request"
    );
  });

  it("rejects successful sign_event serial responses with invalid signatures before returning from transport", async () => {
    const invalidSignedResponse = {
      ...basicEventVector.response,
      result: {
        event: {
          ...basicEventVector.response.result.event,
          sig: "00".repeat(64)
        }
      }
    };
    const transport = new SerialFrameTransport({
      exchangeFrame: async (line) => {
        expect(decodeSerialFrame(line)).toEqual({ type: "request", payload: basicEventVector.request });
        return encodeSerialFrame({ type: "response", payload: invalidSignedResponse });
      }
    });

    await expect(transport.exchange(basicEventVector.request)).rejects.toThrow("signed event signature is invalid");
  });

  it("moves ESP32-S3 scaffold public-key responses over serial frames", async () => {
    const transport = new SerialFrameTransport({
      exchangeFrame: async (line) => {
        expect(decodeSerialFrame(line)).toEqual({ type: "request", payload: publicKeyVector.request });
        return encodeSerialFrame({ type: "response", payload: publicKeyVector.response });
      }
    });

    const response = await transport.exchange(publicKeyVector.request);

    expect(response).toEqual(publicKeyVector.response);
    expect(validateResponse(response).ok).toBe(true);
  });

  it("rejects invalid serial response payloads before returning from transport", async () => {
    const transport = new SerialFrameTransport({
      exchangeFrame: async () => encodeSerialFrame({
        type: "response",
        payload: { version: 1, request_id: capabilitiesRequest.request_id }
      })
    });

    await expect(transport.exchange(capabilitiesRequest)).rejects.toThrow("serial frame response invalid: ok must be true or false");
  });

  it("rejects invalid serial request payloads before writing to transport", async () => {
    let exchangeCalled = false;
    const transport = new SerialFrameTransport({
      exchangeFrame: async () => {
        exchangeCalled = true;
        return encodeSerialFrame({ type: "response", payload: capabilitiesResponse });
      }
    });

    await expect(transport.exchange({ version: 1, request_id: "invalid request id", method: "get_capabilities" })).rejects.toThrow(
      "serial frame request invalid: request_id is invalid"
    );
    expect(exchangeCalled).toBe(false);
  });

  it("exchanges one request over an injected serial line port while ignoring device logs", async () => {
    const writtenLines: string[] = [];
    const incomingLines = [
      "I (123) boot: device log before protocol frame\n",
      encodeSerialFrame({ type: "response", payload: capabilitiesResponse })
    ];
    const transport = new SerialLineTransport({
      port: {
        writeLine: async (line) => {
          writtenLines.push(line);
        },
        readLine: async () => incomingLines.shift() ?? null
      }
    });

    await expect(transport.exchange(capabilitiesRequest)).resolves.toEqual(capabilitiesResponse);
    expect(decodeSerialFrame(writtenLines[0])).toEqual({ type: "request", payload: capabilitiesRequest });
  });

  it("accepts CRLF-terminated serial protocol lines from device ports", async () => {
    const crlfResponseLine = encodeSerialFrame({ type: "response", payload: capabilitiesResponse }).replace("\n", "\r\n");
    const transport = new SerialLineTransport({
      port: {
        writeLine: async () => {},
        readLine: async () => crlfResponseLine
      }
    });

    await expect(transport.exchange(capabilitiesRequest)).resolves.toEqual(capabilitiesResponse);
  });

  it("rejects serial line exchanges that do not receive a response before the timeout", async () => {
    const transport = new SerialLineTransport({
      port: {
        writeLine: async () => {},
        readLine: async () => new Promise<string | null>(() => {})
      },
      responseTimeoutMs: 10
    });

    await expect(
      Promise.race([
        transport.exchange(capabilitiesRequest),
        new Promise<never>((_resolve, reject) => {
          setTimeout(() => reject(new Error("exchange did not time out")), 50);
        })
      ])
    ).rejects.toThrow(/serial line transport timed out before response/u);
  });

  it("rejects serial line exchanges that cannot write before the timeout", async () => {
    const transport = new SerialLineTransport({
      port: {
        writeLine: async () => new Promise<void>(() => {}),
        readLine: async () => null
      },
      responseTimeoutMs: 10
    });

    await expect(
      Promise.race([
        transport.exchange(capabilitiesRequest),
        new Promise<never>((_resolve, reject) => {
          setTimeout(() => reject(new Error("exchange did not time out")), 50);
        })
      ])
    ).rejects.toThrow(/serial line transport timed out before write completed/u);
  });

  it("exchanges over a stream-backed serial line port with chunked device output", async () => {
    const input = new PassThrough();
    const output = new PassThrough();
    const transport = new SerialLineTransport({
      port: new SerialLineStreamPort({ input, output })
    });
    const responseLine = encodeSerialFrame({ type: "response", payload: capabilitiesResponse }).replace("\n", "\r\n");

    const exchange = transport.exchange(capabilitiesRequest);
    const [written] = (await once(output, "data")) as [Buffer];
    expect(decodeSerialFrame(written.toString("utf8"))).toEqual({ type: "request", payload: capabilitiesRequest });

    input.write("I (321) boot: ignored log\r\n");
    input.write(responseLine.slice(0, 12));
    input.write(responseLine.slice(12));

    await expect(exchange).resolves.toEqual(capabilitiesResponse);
  });

  it("rejects stream-backed serial input that exceeds the bounded line buffer", async () => {
    const input = new PassThrough();
    const output = new PassThrough();
    const port = new SerialLineStreamPort({ input, output, maxBufferedBytes: 8 });
    const read = port.readLine();

    input.write("unterminated");

    await expect(
      Promise.race([
        read,
        new Promise<never>((_resolve, reject) => {
          setTimeout(() => reject(new Error("read did not reject")), 25);
        })
      ])
    ).rejects.toThrow(/serial line port buffer exceeded/u);
  });

  it("rejects batched short serial lines whose total exceeds the retained-byte limit", async () => {
    const input = new PassThrough();
    const output = new PassThrough();
    const port = new SerialLineStreamPort({ input, output, maxBufferedBytes: 4 });

    input.write("a\nb\nc\n");

    await expect(port.readLine()).rejects.toThrow(/buffer exceeded/);
    port.close();
  });

  it("can close stream-backed serial line ports after failed exchanges", async () => {
    const input = new PassThrough();
    const output = new PassThrough();
    const port = new SerialLineStreamPort({ input, output });

    port.close();

    expect(input.destroyed).toBe(true);
    expect(output.destroyed).toBe(true);
  });

  it("runs a one-shot serial line exchange through a package-owned opener boundary", async () => {
    const openedPaths: string[] = [];
    const closedPaths: string[] = [];
    const writtenLines: string[] = [];
    const incomingLines = [
      "I (123) boot: ignored device log\n",
      encodeSerialFrame({ type: "response", payload: capabilitiesResponse })
    ];

    await expect(
      exchangeSerialLineRequest({
        path: "/dev/cu.usbmodem-test",
        request: capabilitiesRequest,
        openPort: async (path) => {
          openedPaths.push(path);
          return {
            writeLine: async (line) => {
              writtenLines.push(line);
            },
            readLine: async () => incomingLines.shift() ?? null,
            close: () => {
              closedPaths.push(path);
            }
          };
        }
      })
    ).resolves.toEqual(capabilitiesResponse);

    expect(openedPaths).toEqual(["/dev/cu.usbmodem-test"]);
    expect(closedPaths).toEqual(["/dev/cu.usbmodem-test"]);
    expect(decodeSerialFrame(writtenLines[0])).toEqual({ type: "request", payload: capabilitiesRequest });
  });

  it("rejects invalid one-shot serial line requests before opening a port", async () => {
    let opened = false;

    await expect(
      exchangeSerialLineRequest({
        path: "/dev/cu.usbmodem-test",
        request: { version: 1, request_id: "invalid request id", method: "get_capabilities" },
        openPort: async () => {
          opened = true;
          throw new Error("port should not open");
        }
      })
    ).rejects.toThrow("serial line request invalid: request_id is invalid");

    expect(opened).toBe(false);
  });
});
