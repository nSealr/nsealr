import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { resolveSpecsRoot } from "@nsealr/fixtures";
import { NSEALR_V0_LIMITS } from "@nsealr/protocol";
import { decodeSerialFrame, encodeSerialFrame, SERIAL_FRAME_PREFIX } from "./serial.js";

const specsRoot = resolveSpecsRoot();
const signEventRequest = JSON.parse(readFileSync(resolve(specsRoot, "examples/request-kind-1-basic.json"), "utf8"));
const serialVector = JSON.parse(readFileSync(resolve(specsRoot, "vectors/transports/serial-frame-request-kind-1-basic.json"), "utf8"));

describe("serial framing draft", () => {
  it("round-trips a request frame as one newline-terminated ASCII line", () => {
    const frame = encodeSerialFrame({ type: "request", payload: signEventRequest });

    expect(frame.startsWith(SERIAL_FRAME_PREFIX)).toBe(true);
    expect(frame.endsWith("\n")).toBe(true);
    expect(frame).toBe(serialVector.frame);
    expect(decodeSerialFrame(frame)).toEqual({ type: "request", payload: signEventRequest });
    expect(decodeSerialFrame(serialVector.frame)).toEqual({ type: serialVector.type, payload: serialVector.decoded });
  });

  it("accepts CRLF-terminated frames from serial line readers", () => {
    const frame = encodeSerialFrame({ type: "request", payload: signEventRequest });

    expect(decodeSerialFrame(frame.replace("\n", "\r\n"))).toEqual({ type: "request", payload: signEventRequest });
  });

  it("round-trips UTF-8 payloads without Node runtime helpers", () => {
    const request = {
      ...signEventRequest,
      request_id: "req-serial-utf8-browser-safe",
      params: {
        event_template: {
          ...signEventRequest.params.event_template,
          content: "Line one\nTabbed\tEuro \u20ac Lock \ud83d\udd10"
        }
      }
    };

    expect(decodeSerialFrame(encodeSerialFrame({ type: "request", payload: request }))).toEqual({
      type: "request",
      payload: request
    });
  });

  it("rejects encoded frames that would exceed max_serial_frame_bytes", () => {
    expect(() =>
      encodeSerialFrame({
        type: "request",
        payload: { data: "x".repeat(NSEALR_V0_LIMITS.max_serial_frame_bytes) }
      })
    ).toThrow("serial frame exceeds max_serial_frame_bytes");
  });

  it("rejects frames with unsupported types", () => {
    const frame = encodeSerialFrame({ type: "request", payload: signEventRequest }).replace(":request:", ":pubkey:");

    expect(() => decodeSerialFrame(frame)).toThrow("unsupported serial frame type");
  });

  it("rejects frames with checksum mismatches", () => {
    const frame = encodeSerialFrame({ type: "request", payload: signEventRequest });
    const checksum = frame.match(/:([0-9a-f]{16})\n$/u)?.[1];
    if (!checksum) throw new Error("test frame did not include checksum");
    const badChecksum = checksum === "0".repeat(16) ? "1".repeat(16) : "0".repeat(16);
    const corrupted = frame.replace(checksum, badChecksum);

    expect(() => decodeSerialFrame(corrupted)).toThrow("serial checksum mismatch");
  });

  it("rejects shared invalid serial hardening vectors deterministically", () => {
    const invalidRoot = resolve(specsRoot, "vectors/invalid");
    for (const name of [
      "serial-frame-checksum-mismatch",
      "serial-frame-malformed-payload",
      "serial-frame-oversized",
      "serial-frame-unsupported-type"
    ]) {
      const vector = JSON.parse(readFileSync(resolve(invalidRoot, `${name}.json`), "utf8"));
      expect(() => decodeSerialFrame(vector.frame), name).toThrow(vector.expected_error);
    }
  });
});
