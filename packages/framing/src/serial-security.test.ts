import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { decodeSerialFrame } from "./serial.js";

function frame(json: string): string {
  const payload = Buffer.from(json).toString("base64url");
  const checksum = createHash("sha256").update(`request:${payload}`).digest("hex").slice(0, 16);
  return `nsealr1f:request:${payload}:${checksum}\n`;
}

describe("S01 serial raw JSON boundary", () => {
  it.each(['{"request_id":"a","request_id":"b"}', '{"request_id":"a","\\u0072equest_id":"b"}', '{"params":{"kind":1,"kind":2}}'])("rejects duplicate members: %s", json => {
    expect(() => decodeSerialFrame(frame(json))).toThrow(/JSON|duplicate/i);
  });
  it.each(['{}{}', '{} trailing'])("keeps trailing-data rejection: %s", json => {
    expect(() => decodeSerialFrame(frame(json))).toThrow(/JSON/i);
  });
});
