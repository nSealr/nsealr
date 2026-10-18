import { closeSync, mkdtempSync, openSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { loadSpecsFixtures, resolveSpecsRoot } from "@nsealr/fixtures";
import {
  NATIVE_MESSAGE_LENGTH_BYTES,
  clientIdForIdentity,
  decodeNativeMessage,
  encodeNativeMessage,
  type LocalClientGrant,
  type LocalClientIdentity
} from "@nsealr/client";
import {
  runServiceFrames,
  runServiceFramesAsync,
  runServiceOnce,
  runServiceOnceAsync,
  runServiceStdio,
  runServiceStdioAsync
} from "./index.js";

const specsRoot = resolveSpecsRoot();
const fixtures = loadSpecsFixtures(specsRoot);
const routeVector = fixtures.routeSelections.find((selection) => selection.name === "esp32-usb-sign-event-slot-0");
if (!routeVector) throw new Error("route selection fixture is missing");
const request = JSON.parse(readFileSync(resolve(specsRoot, "examples/request-kind-1-basic.json"), "utf8"));
const response = JSON.parse(readFileSync(resolve(specsRoot, "examples/response-kind-1-basic.json"), "utf8"));
const client: LocalClientIdentity = {
  surface: "native_host_test",
  origin: "app:nsealr-service-test",
  app_name: "nSealr service test"
};
const grant: LocalClientGrant = {
  client_id: clientIdForIdentity(client),
  origin: client.origin,
  surface: client.surface,
  allowed_operations: ["validate_signer_request"],
  approved_at: 1_900_000_000,
  expires_at: 2_000_000_000
};
const dispatchGrant: LocalClientGrant = {
  ...grant,
  allowed_operations: ["dispatch_signer_request"]
};

function decodeFrames(frames: Uint8Array): unknown[] {
  const messages: unknown[] = [];
  let offset = 0;
  while (offset < frames.byteLength) {
    const prefix = frames.slice(offset, offset + NATIVE_MESSAGE_LENGTH_BYTES);
    const length = new DataView(prefix.buffer, prefix.byteOffset, prefix.byteLength).getUint32(0, true);
    const frameEnd = offset + NATIVE_MESSAGE_LENGTH_BYTES + length;
    messages.push(decodeNativeMessage(frames.slice(offset, frameEnd)));
    offset = frameEnd;
  }
  return messages;
}

describe("local companion service app", () => {
  it("handles one native-messaging service request", () => {
    const output = runServiceOnce(encodeNativeMessage({
      version: 1,
      request_id: "svc-status-1",
      operation: "service_status"
    }));

    expect(decodeNativeMessage(output)).toMatchObject({
      version: 1,
      request_id: "svc-status-1",
      ok: true,
      result: {
        service: {
          protocol: "nsealr-local-service-v0",
          stores_production_secrets: false
        }
      }
    });
  });

  it("passes injected in-memory authorization context to the local service", () => {
    const output = runServiceOnce(encodeNativeMessage({
      version: 1,
      request_id: "svc-validate-1",
      operation: "validate_signer_request",
      params: { client, request }
    }), {
      grants: [grant],
      now: 1_900_000_000
    });

    expect(decodeNativeMessage(output)).toMatchObject({
      version: 1,
      request_id: "svc-validate-1",
      ok: true,
      result: {
        validation: { valid: true }
      }
    });
  });

  it("returns signer-route unavailable for authorized dispatch without a driver", () => {
    const output = runServiceOnce(encodeNativeMessage({
      version: 1,
      request_id: "svc-dispatch-unavailable",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request
      }
    }), {
      accounts: fixtures.accounts,
      grants: [dispatchGrant],
      now: 1_900_000_000
    });

    expect(decodeNativeMessage(output)).toMatchObject({
      version: 1,
      request_id: "svc-dispatch-unavailable",
      ok: false,
      error: {
        code: "signer_route_unavailable",
        message: "signer dispatch is not configured",
        retryable: false
      }
    });
  });

  it("awaits async dispatch through the native-message service helper", async () => {
    const output = await runServiceOnceAsync(encodeNativeMessage({
      version: 1,
      request_id: "svc-dispatch-async",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request
      }
    }), {
      accounts: fixtures.accounts,
      grants: [dispatchGrant],
      now: 1_900_000_000,
      signerDispatcher: async () => response
    });

    expect(decodeNativeMessage(output)).toMatchObject({
      version: 1,
      request_id: "svc-dispatch-async",
      ok: true,
      result: {
        signer_response: expect.objectContaining({ request_id: request.request_id })
      }
    });
  });

  it("returns deterministic native-message errors for malformed frames", () => {
    const output = runServiceOnce(new Uint8Array([1, 0, 0, 0]));

    expect(decodeNativeMessage(output)).toMatchObject({
      version: 1,
      request_id: "invalid-service-request",
      ok: false,
      error: {
        code: "invalid_native_message",
        message: expect.stringMatching(/length prefix/u),
        retryable: false
      }
    });
  });

  it("handles multiple native-messaging frames in one service stream", () => {
    const input = Buffer.concat([
      Buffer.from(encodeNativeMessage({
        version: 1,
        request_id: "svc-stream-status",
        operation: "service_status"
      })),
      Buffer.from(encodeNativeMessage({
        version: 1,
        request_id: "svc-stream-validate",
        operation: "validate_signer_request",
        params: { client, request }
      }))
    ]);

    expect(decodeFrames(runServiceFrames(input, {
      grants: [grant],
      now: 1_900_000_000
    }))).toEqual([
      expect.objectContaining({
        request_id: "svc-stream-status",
        ok: true
      }),
      expect.objectContaining({
        request_id: "svc-stream-validate",
        ok: true,
        result: { validation: { valid: true } }
      })
    ]);
  });

  it("handles async multiple native-messaging frames in one service stream", async () => {
    const input = Buffer.concat([
      Buffer.from(encodeNativeMessage({
        version: 1,
        request_id: "svc-async-stream-status",
        operation: "service_status"
      })),
      Buffer.from(encodeNativeMessage({
        version: 1,
        request_id: "svc-async-stream-validate",
        operation: "validate_signer_request",
        params: { client, request }
      }))
    ]);

    expect(decodeFrames(await runServiceFramesAsync(input, {
      grants: [grant],
      now: 1_900_000_000
    }))).toEqual([
      expect.objectContaining({
        request_id: "svc-async-stream-status",
        ok: true
      }),
      expect.objectContaining({
        request_id: "svc-async-stream-validate",
        ok: true,
        result: { validation: { valid: true } }
      })
    ]);
  });

  it("returns one deterministic error frame for a truncated service stream", () => {
    expect(decodeFrames(runServiceFrames(new Uint8Array([1, 0])))).toEqual([
      expect.objectContaining({
        request_id: "invalid-service-request",
        ok: false,
        error: expect.objectContaining({
          code: "invalid_native_message",
          message: expect.stringMatching(/length prefix/u)
        })
      })
    ]);
  });

  it("runs the native-messaging stdio loop over file descriptors", () => {
    const dir = mkdtempSync(join(tmpdir(), "nsealr-service-"));
    const inputPath = join(dir, "input.bin");
    const outputPath = join(dir, "output.bin");
    writeFileSync(inputPath, Buffer.concat([
      Buffer.from(encodeNativeMessage({
        version: 1,
        request_id: "svc-fd-status",
        operation: "service_status"
      })),
      Buffer.from(encodeNativeMessage({
        version: 1,
        request_id: "svc-fd-validate",
        operation: "validate_signer_request",
        params: { client, request }
      }))
    ]));
    const inputFd = openSync(inputPath, "r");
    const outputFd = openSync(outputPath, "w");
    try {
      runServiceStdio({
        inputFd,
        outputFd,
        context: {
          grants: [grant],
          now: 1_900_000_000
        }
      });
    } finally {
      closeSync(inputFd);
      closeSync(outputFd);
    }

    const output = readFileSync(outputPath);
    rmSync(dir, { recursive: true, force: true });

    expect(decodeFrames(output)).toEqual([
      expect.objectContaining({
        request_id: "svc-fd-status",
        ok: true
      }),
      expect.objectContaining({
        request_id: "svc-fd-validate",
        ok: true,
        result: { validation: { valid: true } }
      })
    ]);
  });

  it("runs the async native-messaging stdio loop over file descriptors", async () => {
    const dir = mkdtempSync(join(tmpdir(), "nsealr-service-async-"));
    const inputPath = join(dir, "input.bin");
    const outputPath = join(dir, "output.bin");
    writeFileSync(inputPath, Buffer.concat([
      Buffer.from(encodeNativeMessage({
        version: 1,
        request_id: "svc-async-fd-status",
        operation: "service_status"
      })),
      Buffer.from(encodeNativeMessage({
        version: 1,
        request_id: "svc-async-fd-validate",
        operation: "validate_signer_request",
        params: { client, request }
      }))
    ]));
    const inputFd = openSync(inputPath, "r");
    const outputFd = openSync(outputPath, "w");
    try {
      await runServiceStdioAsync({
        inputFd,
        outputFd,
        context: {
          grants: [grant],
          now: 1_900_000_000
        }
      });
    } finally {
      closeSync(inputFd);
      closeSync(outputFd);
    }

    const output = readFileSync(outputPath);
    rmSync(dir, { recursive: true, force: true });

    expect(decodeFrames(output)).toEqual([
      expect.objectContaining({
        request_id: "svc-async-fd-status",
        ok: true
      }),
      expect.objectContaining({
        request_id: "svc-async-fd-validate",
        ok: true,
        result: { validation: { valid: true } }
      })
    ]);
  });
});
