import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex } from "@noble/hashes/utils.js";
import {
  assertBase64UrlPayload,
  decodeBase64Url,
  encodeBase64Url,
  jsonToUtf8Bytes,
  parseStrictJson,
  NSEALR_V0_LIMITS,
  utf8ByteLength
} from "@nsealr/protocol";

export const SERIAL_FRAME_PREFIX = "nsealr1f:";

export type SerialFrameType = "request" | "response" | "error";

export type SerialFrame = {
  type: SerialFrameType;
  payload: unknown;
};

const TEXT_ENCODER = new TextEncoder();
const TEXT_DECODER = new TextDecoder("utf-8", { fatal: true });

function isSerialFrameType(value: string): value is SerialFrameType {
  return value === "request" || value === "response" || value === "error";
}

function assertBase64Url(value: string): void {
  assertBase64UrlPayload(value, {
    padded: "serial frame payload must be unpadded base64url",
    invalid: "serial frame payload must be base64url"
  });
}

function checksum(type: SerialFrameType, payload: string): string {
  return bytesToHex(sha256(TEXT_ENCODER.encode(`${type}:${payload}`))).slice(0, 16);
}

function stripLineEnding(line: string): string {
  if (line.endsWith("\r\n")) {
    return line.slice(0, -2);
  }
  if (line.endsWith("\n") || line.endsWith("\r")) {
    return line.slice(0, -1);
  }
  return line;
}

export function encodeSerialFrame(frame: SerialFrame): string {
  const payload = encodeBase64Url(jsonToUtf8Bytes(frame.payload, "serial frame payload must be JSON-serializable"));
  const frameChecksum = checksum(frame.type, payload);
  const line = `${SERIAL_FRAME_PREFIX}${frame.type}:${payload}:${frameChecksum}\n`;
  if (utf8ByteLength(line) > NSEALR_V0_LIMITS.max_serial_frame_bytes) {
    throw new Error("serial frame exceeds max_serial_frame_bytes");
  }
  return line;
}

export function decodeSerialFrame(line: string): SerialFrame {
  if (utf8ByteLength(line) > NSEALR_V0_LIMITS.max_serial_frame_bytes) {
    throw new Error("serial frame exceeds max_serial_frame_bytes");
  }
  const normalized = stripLineEnding(line);
  if (!normalized.startsWith(SERIAL_FRAME_PREFIX)) {
    throw new Error(`serial frame must start with ${SERIAL_FRAME_PREFIX}`);
  }
  const parts = normalized.slice(SERIAL_FRAME_PREFIX.length).split(":");
  if (parts.length !== 3) {
    throw new Error("serial frame must contain type, payload, and checksum");
  }
  const [type, payload, frameChecksum] = parts;
  if (!isSerialFrameType(type)) {
    throw new Error("unsupported serial frame type");
  }
  assertBase64Url(payload);
  if (frameChecksum !== checksum(type, payload)) {
    throw new Error("serial checksum mismatch");
  }
  const decoded = decodeBase64Url(payload, "serial frame payload must be base64url");
  let json: string;
  try {
    json = TEXT_DECODER.decode(decoded);
  } catch (error) {
    throw new Error("serial frame payload must be valid UTF-8", { cause: error });
  }
  try {
    return {
      type,
      payload: parseStrictJson(json, NSEALR_V0_LIMITS.max_serial_frame_bytes)
    };
  } catch (error) {
    throw new Error("serial frame payload is not valid JSON", { cause: error });
  }
}
