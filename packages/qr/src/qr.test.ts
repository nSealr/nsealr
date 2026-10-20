import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { resolveSpecsRoot } from "@nsealr/fixtures";
import { NSEALR_V0_LIMITS } from "@nsealr/protocol";
import {
  ANIMATED_QR_ENVELOPE_PREFIX,
  decodeAnimatedQrEnvelopeFrames,
  decodeQrEnvelope,
  encodeAnimatedQrEnvelopeFrames,
  encodeQrEnvelope,
  QR_ENVELOPE_PREFIX
} from "./qr.js";

const specsRoot = resolveSpecsRoot();

describe("original QR signer byte grammar", () => {
  it("checks duplicate/Unicode/number/BOM evidence in static and animated ingress", () => {
    const valid = '{"version":2,"request_id":"r","method":"get_public_key"}';
    const hash = (value: string | Uint8Array) => createHash("sha256").update(value).digest("hex");
    for (const raw of [valid.replace(':2,', ':2.0,'), valid.replace(':2,', ':2,"version":2,'), valid.replace('"r"', '"\\ud800"'), '\ufeff' + valid, valid + '{}']) {
      const bytes = Buffer.from(raw), payload = bytes.toString("base64url");
      expect(() => decodeQrEnvelope(`nsealr1:${payload}`)).toThrow();
      const body = `nsealr1a:${hash(bytes)}:1/1:${payload}`;
      expect(() => decodeAnimatedQrEnvelopeFrames([`${body}:${hash(body).slice(0, 16)}`])).toThrow();
    }
    expect(decodeQrEnvelope(`nsealr1:${Buffer.from(valid).toString("base64url")}`)).toEqual(JSON.parse(valid));
  });
});
const signEventRequest = JSON.parse(readFileSync(resolve(specsRoot, "examples/request-kind-1-basic.json"), "utf8"));
const qrVector = JSON.parse(readFileSync(resolve(specsRoot, "vectors/transports/qr-envelope-kind-1-basic.json"), "utf8"));
const animatedQrVector = JSON.parse(readFileSync(resolve(specsRoot, "vectors/transports/qr-animated-response-kind-1-basic.json"), "utf8"));

describe("QR envelope v0", () => {
  it("encodes and decodes an uncompressed base64url JSON envelope", () => {
    const envelope = encodeQrEnvelope(signEventRequest);

    expect(envelope.startsWith(QR_ENVELOPE_PREFIX)).toBe(true);
    expect(envelope).not.toContain("=");
    expect(envelope).toBe(qrVector.envelope);
    expect(decodeQrEnvelope(envelope)).toEqual(signEventRequest);
    expect(decodeQrEnvelope(qrVector.envelope)).toEqual(qrVector.decoded);
  });

  it("round-trips UTF-8 content in browser-safe QR helpers", () => {
    const request = {
      ...signEventRequest,
      request_id: "req-utf8-browser-safe",
      params: {
        event_template: {
          ...signEventRequest.params.event_template,
          content: "Line one\nTabbed\tEuro \u20ac Lock \ud83d\udd10"
        }
      }
    };

    expect(decodeQrEnvelope(encodeQrEnvelope(request))).toEqual(request);
    expect(decodeAnimatedQrEnvelopeFrames(encodeAnimatedQrEnvelopeFrames(request, { chunkSizeChars: 23 }))).toEqual(request);
  });

  it("rejects envelopes without the nsealr1 prefix", () => {
    expect(() => decodeQrEnvelope("nostr:abc")).toThrow("QR envelope requires nsealr1 prefix");
  });

  it("rejects envelopes whose payload is not JSON", () => {
    expect(() => decodeQrEnvelope(`${QR_ENVELOPE_PREFIX}bm90LWpzb24`)).toThrow("QR envelope payload is not valid JSON");
  });

  it("rejects encode-side static payloads that exceed the v0 decoded JSON limit", () => {
    expect(() =>
      encodeQrEnvelope({ payload: "x".repeat(NSEALR_V0_LIMITS.max_static_qr_decoded_json_bytes + 1) })
    ).toThrow("QR decoded JSON exceeds max_static_qr_decoded_json_bytes");
  });

  it("encodes and decodes animated QR frame sets from the shared vector", () => {
    const frames = encodeAnimatedQrEnvelopeFrames(animatedQrVector.decoded, {
      chunkSizeChars: animatedQrVector.chunk_size_chars
    });

    expect(frames).toEqual(animatedQrVector.frames);
    expect(frames.every((frame) => frame.startsWith(ANIMATED_QR_ENVELOPE_PREFIX))).toBe(true);
    expect(decodeAnimatedQrEnvelopeFrames(frames)).toEqual(animatedQrVector.decoded);
    expect(decodeAnimatedQrEnvelopeFrames([...frames].reverse())).toEqual(animatedQrVector.decoded);
  });

  it("rejects malformed animated QR frame sets deterministically", () => {
    expect(() => decodeAnimatedQrEnvelopeFrames([])).toThrow("animated QR requires at least one frame");
    expect(() => decodeAnimatedQrEnvelopeFrames(animatedQrVector.frames.slice(1))).toThrow(
      "animated QR frames must be unique and contiguous"
    );
    expect(() =>
      decodeAnimatedQrEnvelopeFrames([animatedQrVector.frames[0].replace(/.$/u, "0"), ...animatedQrVector.frames.slice(1)])
    ).toThrow("animated QR frame checksum mismatch");
  });

  it("rejects shared invalid QR hardening vectors deterministically", () => {
    const fixtures = JSON.parse(readFileSync(resolve(specsRoot, "vectors/limits/nsealr-v0.json"), "utf8"));
    expect(fixtures.name).toBe("nsealr-v0");
    const invalidRoot = resolve(specsRoot, "vectors/invalid");
    for (const name of ["qr-envelope-invalid-utf8", "qr-envelope-malformed", "qr-envelope-oversized", "qr-envelope-padded"]) {
      const vector = JSON.parse(readFileSync(resolve(invalidRoot, `${name}.json`), "utf8"));
      expect(() => decodeQrEnvelope(vector.envelope), name).toThrow(vector.expected_error);
    }
  });
});
