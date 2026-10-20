import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import * as protocol from "@nsealr/protocol";
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


// Independent framing/checksum inputs use Node Buffer/crypto, not QR encoders.
const hashQrInput = (value: string | Uint8Array) => createHash("sha256").update(value).digest("hex");
const animatedRawFrame = (digest: string, indexTotal: string, chunk: string): string => {
  const body = `${ANIMATED_QR_ENVELOPE_PREFIX}${digest}:${indexTotal}:${chunk}`;
  return `${body}:${hashQrInput(body).slice(0, 16)}`;
};
const independentAnimatedFrames = (raw: string | Uint8Array, firstSingleChars = 0): string[] => {
  const bytes = typeof raw === "string" ? Buffer.from(raw) : Buffer.from(raw);
  const payload = bytes.toString("base64url");
  const chunks = firstSingleChars > 0
    ? [...payload.slice(0, firstSingleChars), payload.slice(firstSingleChars)]
    : payload.match(/.{1,256}/gu)!;
  return chunks.map((chunk, index) => animatedRawFrame(hashQrInput(bytes), `${index + 1}/${chunks.length}`, chunk));
};
const stringJsonBytes = (bytes: number): string => JSON.stringify("a".repeat(bytes - 2));
const staticByteLimit = NSEALR_V0_LIMITS.max_static_qr_decoded_json_bytes;
const animatedByteLimit = NSEALR_V0_LIMITS.max_animated_qr_decoded_json_bytes;
const encodedAnimatedLimit = Math.ceil(animatedByteLimit * 4 / 3);
// Fixed digest/checksum widths and existing max64 index/total: no new capacity.
const animatedFrameOverhead = ANIMATED_QR_ENVELOPE_PREFIX.length + 64 + 16 + 4
  + 2 * String(NSEALR_V0_LIMITS.max_animated_qr_frame_count).length;
const wholeAnimatedFrameLimit = animatedFrameOverhead + NSEALR_V0_LIMITS.max_animated_qr_frame_payload_chars;

describe("QR ingress before conversion and retained-work bounds", () => {
  it.each([-1, 0])("accepts static decoded byte limit %+d using independent JSON/base64", (delta) => {
    const raw = stringJsonBytes(staticByteLimit + delta);
    expect(Buffer.byteLength(raw)).toBe(staticByteLimit + delta);
    expect(decodeQrEnvelope(`${QR_ENVELOPE_PREFIX}${Buffer.from(raw).toString("base64url")}`)).toEqual(JSON.parse(raw));
  });

  it("rejects canonical static max+1 bytes before base64 allocation or re-encoding", () => {
    const raw = stringJsonBytes(staticByteLimit + 1);
    const envelope = `${QR_ENVELOPE_PREFIX}${Buffer.from(raw).toString("base64url")}`;
    const decode = vi.spyOn(protocol, "decodeBase64Url");
    const encode = vi.spyOn(protocol, "encodeBase64Url");
    try {
      expect(() => decodeQrEnvelope(envelope)).toThrow("QR decoded JSON exceeds max_static_qr_decoded_json_bytes");
      expect(decode).not.toHaveBeenCalled();
      expect(encode).not.toHaveBeenCalled();
    } finally { decode.mockRestore(); encode.mockRestore(); }
  });

  it("rejects static raw max+1 characters before scanning malformed base64", () => {
    const payload = "A".repeat(Math.ceil(staticByteLimit * 4 / 3)) + "?";
    expect(() => decodeQrEnvelope(`${QR_ENVELOPE_PREFIX}${payload}`)).toThrow("QR decoded JSON exceeds max_static_qr_decoded_json_bytes");
  });

  it.each([-1, 0])("accepts complete64-frame input with a whole frame at limit %+d", (delta) => {
    //63 one-character chunks plus the final255/256-character chunk. All64
    //checksums, aggregate digest, JSON and canonical trailing bits are valid.
    const raw = stringJsonBytes(239 + delta);
    const frames = independentAnimatedFrames(raw, 63);
    expect(frames).toHaveLength(64);
    expect(frames.at(-1)!.length).toBe(wholeAnimatedFrameLimit + delta);
    expect(decodeAnimatedQrEnvelopeFrames([...frames].reverse())).toEqual(JSON.parse(raw));
  });

  it("bounds a whole animated frame before split, lexical scan or checksum work", () => {
    const frames = independentAnimatedFrames(stringJsonBytes(240), 63);
    const oversized = frames.at(-1)!;
    expect(oversized.length).toBe(wholeAnimatedFrameLimit + 1);
    const split = vi.spyOn(String.prototype, "split");
    let failure: unknown;
    try {
      try { decodeAnimatedQrEnvelopeFrames([oversized]); } catch (error) { failure = error; }
      expect(split.mock.contexts.some((context) => String(context) === oversized)).toBe(false);
      expect(failure).toMatchObject({ message: "animated QR frame exceeds bounded frame length" });
    } finally { split.mockRestore(); }
  });

  it.each([-1, 0])("accepts animated decoded byte limit %+d independently framed", (delta) => {
    const raw = stringJsonBytes(animatedByteLimit + delta);
    expect(Buffer.byteLength(raw)).toBe(animatedByteLimit + delta);
    expect(decodeAnimatedQrEnvelopeFrames(independentAnimatedFrames(raw))).toEqual(JSON.parse(raw));
  });

  it("bounds exact cumulative chunks before joined base64 allocation or re-encoding", () => {
    const frames = independentAnimatedFrames(stringJsonBytes(animatedByteLimit + 1));
    //This input deliberately fits the conservative raw-header budget, so a
    //whole-frame or raw-collection guard cannot mask the exact chunk check.
    expect(frames.reduce((sum, frame) => sum + frame.length, 0)).toBeLessThanOrEqual(
      encodedAnimatedLimit + frames.length * animatedFrameOverhead);
    const decode = vi.spyOn(protocol, "decodeBase64Url");
    const encode = vi.spyOn(protocol, "encodeBase64Url");
    try {
      expect(() => decodeAnimatedQrEnvelopeFrames(frames)).toThrow("animated QR decoded JSON exceeds max_animated_qr_decoded_json_bytes");
      expect(decode).not.toHaveBeenCalled();
      expect(encode).not.toHaveBeenCalled();
    } finally { decode.mockRestore(); encode.mockRestore(); }
  });

  it.each([-1, 0, 1])("checks the raw collection budget %+d before checksums/duplicate interpretation", (delta) => {
    const count = NSEALR_V0_LIMITS.max_animated_qr_frame_count;
    const payloadCharacters = encodedAnimatedLimit + delta;
    const chunks = Array.from({ length: count }, (_, index) => "A".repeat(
      index === count - 1 ? payloadCharacters - 85 * (count - 1) : 85));
    //Each frame individually has a valid checksum and bounded chunk. Duplicate
    //indices are the isolated later error at/below the raw collection ceiling.
    const frames = chunks.map((chunk) => animatedRawFrame("0".repeat(64), "64/64", chunk));
    expect(frames.reduce((sum, frame) => sum + frame.length, 0)).toBe(
      encodedAnimatedLimit + count * animatedFrameOverhead + delta);
    expect(frames.every((frame) => frame.length <= wholeAnimatedFrameLimit)).toBe(true);
    const encode = vi.spyOn(TextEncoder.prototype, "encode");
    let failure: unknown;
    try {
      try { decodeAnimatedQrEnvelopeFrames(frames); } catch (error) { failure = error; }
      const checksumCalls = encode.mock.calls.filter(([value]) => value?.startsWith(ANIMATED_QR_ENVELOPE_PREFIX));
      if (delta > 0) {
        expect(checksumCalls).toHaveLength(0);
        expect(failure).toMatchObject({ message: "animated QR decoded JSON exceeds max_animated_qr_decoded_json_bytes" });
      } else {
        expect(checksumCalls).toHaveLength(count);
        expect(failure).toMatchObject({ message: "animated QR frames must be unique and contiguous" });
      }
    } finally { encode.mockRestore(); }
  });

  it.each([63, 64])("retains the existing valid caller frame count at%d", (count) => {
    const raw = stringJsonBytes(48);
    const frames = independentAnimatedFrames(raw, count - 1);
    expect(frames).toHaveLength(count);
    expect(decodeAnimatedQrEnvelopeFrames(frames)).toEqual(JSON.parse(raw));
  });

  it("retains the existing65-frame refusal before any frame parsing/checksum", () => {
    const frames = Array.from({ length: 65 }, (_, index) => animatedRawFrame("0".repeat(64), `${index + 1}/65`, "A"));
    const encode = vi.spyOn(TextEncoder.prototype, "encode");
    try {
      expect(() => decodeAnimatedQrEnvelopeFrames(frames)).toThrow("animated QR frame count exceeds max_animated_qr_frame_count");
      expect(encode.mock.calls.filter(([value]) => value?.startsWith(ANIMATED_QR_ENVELOPE_PREFIX))).toHaveLength(0);
    } finally { encode.mockRestore(); }
  });

  it("keeps malformed static grammar errors independently observable below byte limits", () => {
    for (const [payload, message] of [
      ["bnVsbA=", "unpadded base64url"], ["bnVsb?", "must be base64url"],
      ["A", "must be base64url"], ["bnVsbB", "invalid trailing bits"],
      [Buffer.from([255]).toString("base64url"), "valid UTF-8"],
      [Buffer.from("{").toString("base64url"), "not valid JSON"]
    ]) expect(() => decodeQrEnvelope(`${QR_ENVELOPE_PREFIX}${payload}`), payload).toThrow(message);
  });

  it("keeps animated malformed fields/checksum/digest/UTF8/JSON independent of early bounds", () => {
    const digest = hashQrInput("null");
    for (const [frame, message] of [
      [animatedRawFrame(digest, "1/1", "bnVsbA="), "unpadded base64url"],
      [animatedRawFrame(digest, "1/1", "bnVsb?"), "must be base64url"],
      [animatedRawFrame(digest, "1/1", "A"), "payload must be base64url"],
      [animatedRawFrame(digest, "1/1", "bnVsbB"), "invalid trailing bits"],
      [animatedRawFrame("0".repeat(64), "1/1", "bnVsbA"), "decoded digest mismatch"],
      [independentAnimatedFrames(Buffer.from([255]))[0], "valid UTF-8"],
      [independentAnimatedFrames("{")[0], "not valid JSON"],
      [animatedRawFrame(digest, "01/1", "bnVsbA"), "index must use index/total"],
      [animatedRawFrame(digest, "2/1", "bnVsbA"), "frame index is out of range"]
    ]) expect(() => decodeAnimatedQrEnvelopeFrames([frame]), message).toThrow(message);
    const valid = animatedRawFrame(digest, "1/1", "bnVsbA");
    const corrupt = valid.slice(0, -1) + (valid.endsWith("0") ? "1" : "0");
    expect(() => decodeAnimatedQrEnvelopeFrames([corrupt])).toThrow("frame checksum mismatch");
    const first = animatedRawFrame(digest, "1/2", "bnV");
    const second = animatedRawFrame("0".repeat(64), "2/2", "sbA");
    expect(() => decodeAnimatedQrEnvelopeFrames([first, second])).toThrow("frame set mismatch");
    expect(() => decodeAnimatedQrEnvelopeFrames([first, first])).toThrow("unique and contiguous");
    expect(() => decodeAnimatedQrEnvelopeFrames([first])).toThrow("unique and contiguous");
  });
});
