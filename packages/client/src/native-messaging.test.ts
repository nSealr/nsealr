import { describe, expect, it } from "vitest";
import { decodeNativeMessage, encodeNativeMessage } from "./native-messaging.js";

describe("native messaging codec", () => {
  it("round-trips one length-prefixed JSON message", () => {
    const frame = encodeNativeMessage({ hello: "nsealr" });

    expect(decodeNativeMessage(frame)).toEqual({ hello: "nsealr" });
  });

  it("rejects frames with mismatched length prefixes", () => {
    const frame = encodeNativeMessage({ hello: "nsealr" });
    frame[0] += 1;

    expect(() => decodeNativeMessage(frame)).toThrow(/length prefix/u);
  });

  it("rejects oversized outgoing messages before framing", () => {
    expect(() => encodeNativeMessage({ content: "x".repeat(20) }, 8)).toThrow(/exceeds max bytes/u);
  });
});
