import { describe, expect, it } from "vitest";
import {
  assertBase64UrlPayload,
  decodeBase64Url,
  encodeBase64Url,
  jsonToUtf8Bytes,
  parseStrictJson
} from "./encoding.js";

const textDecoder = new TextDecoder("utf-8", { fatal: true });

describe("shared browser-safe encoding helpers", () => {
  it("round-trips UTF-8 JSON through unpadded base64url", () => {
    const value = { content: "Line one\nTabbed\tEuro \u20ac Lock \ud83d\udd10" };
    const bytes = jsonToUtf8Bytes(value, "not JSON");
    const encoded = encodeBase64Url(bytes);

    expect(encoded).not.toContain("=");
    expect(JSON.parse(textDecoder.decode(decodeBase64Url(encoded, "bad base64url")))).toEqual(value);
  });

  it("rejects padded, malformed, and impossible-length payloads deterministically", () => {
    expect(() => assertBase64UrlPayload("abc=", { padded: "padded", invalid: "invalid" })).toThrow("padded");
    expect(() => assertBase64UrlPayload("abc*", { padded: "padded", invalid: "invalid" })).toThrow("invalid");
    expect(() => decodeBase64Url("a", "invalid length")).toThrow("invalid length");
  });

  it("rejects non-JSON-serializable roots deterministically", () => {
    const cyclic: Record<string, unknown> = {};
    cyclic.self = cyclic;

    expect(() => jsonToUtf8Bytes(undefined, "not JSON")).toThrow("not JSON");
    expect(() => jsonToUtf8Bytes(cyclic, "not JSON")).toThrow("not JSON");
  });
});

describe("bounded strict JSON", () => {
  it("preserves JSON values and escaped syntax without false duplicate reports", () => {
    const text = '{"a":"\\\"a\\\": \\n { }", "b":[{"a":1},{"a":2}], "n":1e2, "__proto__":null}';
    expect(parseStrictJson(text, 1024)).toEqual(JSON.parse(text));
  });
  it.each(['{"a":1,"a":2}', '{"a":1,"\\u0061":2}', '{"a":{"x":1,"x":2}}', '{"__proto__":1,"__proto__":2}'])("rejects duplicate names: %s", text => {
    expect(() => parseStrictJson(text, 1024)).toThrow(/duplicate/);
  });
  it("bounds actual UTF-8 bytes including whitespace", () => {
    expect(parseStrictJson('"€"', 5)).toBe("€");
    expect(() => parseStrictJson('"€"', 4)).toThrow(/byte/);
    expect(() => parseStrictJson('"€" ', 5)).toThrow(/byte/);
  });
  it("accepts depth 32 and rejects 33 without recursive traversal", () => {
    expect(parseStrictJson("[".repeat(32) + "0" + "]".repeat(32), 1024)).toBeDefined();
    expect(() => parseStrictJson("[".repeat(33) + "0" + "]".repeat(33), 1024)).toThrow(/nesting/);
  });
  it.each(['{}{}', '{"a":}', 'undefined', 'NaN', '[1,]'])("rejects invalid/trailing JSON: %s", text => {
    expect(() => parseStrictJson(text, 1024)).toThrow();
  });
});
