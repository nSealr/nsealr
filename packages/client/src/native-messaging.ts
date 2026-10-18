import { utf8ByteLength } from "@nsealr/protocol";

export const NATIVE_MESSAGE_LENGTH_BYTES = 4;
export const MAX_NATIVE_MESSAGE_BYTES = 16 * 1024;

export type NativeMessageFrameExchange = (frame: Uint8Array) => Promise<Uint8Array> | Uint8Array;

const decoder = new TextDecoder("utf-8", { fatal: true });
const encoder = new TextEncoder();

export function encodeNativeMessage(message: unknown, maxBytes = MAX_NATIVE_MESSAGE_BYTES): Uint8Array {
  const body = encoder.encode(JSON.stringify(message));
  if (body.byteLength > maxBytes) {
    throw new Error("native message exceeds max bytes");
  }
  const frame = new Uint8Array(NATIVE_MESSAGE_LENGTH_BYTES + body.byteLength);
  const view = new DataView(frame.buffer);
  view.setUint32(0, body.byteLength, true);
  frame.set(body, NATIVE_MESSAGE_LENGTH_BYTES);
  return frame;
}

export function decodeNativeMessage(frame: Uint8Array, maxBytes = MAX_NATIVE_MESSAGE_BYTES): unknown {
  if (frame.byteLength < NATIVE_MESSAGE_LENGTH_BYTES) {
    throw new Error("native message frame missing length prefix");
  }
  const view = new DataView(frame.buffer, frame.byteOffset, frame.byteLength);
  const length = view.getUint32(0, true);
  if (length > maxBytes) {
    throw new Error("native message exceeds max bytes");
  }
  if (frame.byteLength !== NATIVE_MESSAGE_LENGTH_BYTES + length) {
    throw new Error("native message length prefix does not match payload");
  }
  const body = decoder.decode(frame.slice(NATIVE_MESSAGE_LENGTH_BYTES));
  if (utf8ByteLength(body) !== length) {
    throw new Error("native message length is not a UTF-8 byte length");
  }
  return JSON.parse(body);
}
