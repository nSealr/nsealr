import { chacha20 } from "@noble/ciphers/chacha.js";
import { equalBytes } from "@noble/ciphers/utils.js";
import { secp256k1 } from "@noble/curves/secp256k1.js";
import { expand, extract } from "@noble/hashes/hkdf.js";
import { hmac } from "@noble/hashes/hmac.js";
import { sha256 } from "@noble/hashes/sha2.js";
import { concatBytes, hexToBytes, randomBytes, utf8ToBytes } from "@noble/hashes/utils.js";

// NIP-44 v2 authenticated encryption (ChaCha20 + HMAC-SHA256, HKDF key schedule).
// Crypto primitives are @noble; this module only composes the NIP-44 v2 scheme.
// Correctness is pinned by the official vectors + a differential test vs nostr-tools.

const SALT = utf8ToBytes("nip44-v2");
const MIN_PLAINTEXT_SIZE = 1;
const MAX_PLAINTEXT_SIZE = 65535;
const VERSION = 2;

const utf8Decoder = new TextDecoder();

// --- standard base64 (with padding), validating, cross-platform ---
const B64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
const B64_LOOKUP: Int16Array = (() => {
  const table = new Int16Array(256).fill(-1);
  for (let i = 0; i < B64_ALPHABET.length; i += 1) {
    table[B64_ALPHABET.charCodeAt(i)] = i;
  }
  return table;
})();

function bytesToBase64(bytes: Uint8Array): string {
  let out = "";
  let i = 0;
  for (; i + 2 < bytes.length; i += 3) {
    const n = (bytes[i] << 16) | (bytes[i + 1] << 8) | bytes[i + 2];
    out += B64_ALPHABET[(n >> 18) & 63] + B64_ALPHABET[(n >> 12) & 63] + B64_ALPHABET[(n >> 6) & 63] + B64_ALPHABET[n & 63];
  }
  const rem = bytes.length - i;
  if (rem === 1) {
    const n = bytes[i] << 16;
    out += B64_ALPHABET[(n >> 18) & 63] + B64_ALPHABET[(n >> 12) & 63] + "==";
  } else if (rem === 2) {
    const n = (bytes[i] << 16) | (bytes[i + 1] << 8);
    out += B64_ALPHABET[(n >> 18) & 63] + B64_ALPHABET[(n >> 12) & 63] + B64_ALPHABET[(n >> 6) & 63] + "=";
  }
  return out;
}

function decodeBase64Char(code: number): number {
  return code < 256 ? B64_LOOKUP[code] : -1;
}

function base64ToBytes(value: string): Uint8Array {
  const length = value.length;
  if (length === 0 || length % 4 !== 0) {
    throw new Error("invalid base64 length");
  }
  let padding = 0;
  if (value[length - 1] === "=") {
    padding = value[length - 2] === "=" ? 2 : 1;
  }
  const out = new Uint8Array((length / 4) * 3 - padding);
  let o = 0;
  for (let i = 0; i < length; i += 4) {
    const isLastGroup = i + 4 === length;
    const isPad2 = value[i + 2] === "=";
    const isPad3 = value[i + 3] === "=";
    // '=' is only legal as contiguous padding at the very end of the string.
    if ((isPad2 || isPad3) && !isLastGroup) throw new Error("invalid base64 padding");
    if (isPad2 && !isPad3) throw new Error("invalid base64 padding");
    const c0 = decodeBase64Char(value.charCodeAt(i));
    const c1 = decodeBase64Char(value.charCodeAt(i + 1));
    const c2 = isPad2 ? 0 : decodeBase64Char(value.charCodeAt(i + 2));
    const c3 = isPad3 ? 0 : decodeBase64Char(value.charCodeAt(i + 3));
    if (c0 < 0 || c1 < 0 || c2 < 0 || c3 < 0) {
      throw new Error("invalid base64 character");
    }
    const n = (c0 << 18) | (c1 << 12) | (c2 << 6) | c3;
    out[o] = (n >> 16) & 0xff;
    o += 1;
    if (!isPad2) {
      out[o] = (n >> 8) & 0xff;
      o += 1;
    }
    if (!isPad3) {
      out[o] = n & 0xff;
      o += 1;
    }
  }
  return out;
}

// --- NIP-44 padding scheme ---
function calcPaddedLen(length: number): number {
  if (!Number.isInteger(length) || length < 1) {
    throw new Error("expected positive integer length");
  }
  if (length <= 32) return 32;
  const nextPower = 1 << (Math.floor(Math.log2(length - 1)) + 1);
  const chunk = nextPower <= 256 ? 32 : nextPower / 8;
  return chunk * (Math.floor((length - 1) / chunk) + 1);
}

function pad(plaintext: string): Uint8Array {
  const unpadded = utf8ToBytes(plaintext);
  const unpaddedLen = unpadded.length;
  if (unpaddedLen < MIN_PLAINTEXT_SIZE || unpaddedLen > MAX_PLAINTEXT_SIZE) {
    throw new Error("invalid plaintext length");
  }
  const prefix = new Uint8Array(2);
  prefix[0] = (unpaddedLen >> 8) & 0xff;
  prefix[1] = unpaddedLen & 0xff;
  const suffix = new Uint8Array(calcPaddedLen(unpaddedLen) - unpaddedLen);
  return concatBytes(prefix, unpadded, suffix);
}

function unpad(padded: Uint8Array): string {
  const unpaddedLen = (padded[0] << 8) | padded[1];
  const unpadded = padded.subarray(2, 2 + unpaddedLen);
  if (
    unpaddedLen < MIN_PLAINTEXT_SIZE ||
    unpaddedLen > MAX_PLAINTEXT_SIZE ||
    unpadded.length !== unpaddedLen ||
    padded.length !== 2 + calcPaddedLen(unpaddedLen)
  ) {
    throw new Error("invalid padding");
  }
  return utf8Decoder.decode(unpadded);
}

// --- key schedule ---
export function getConversationKey(privkey: string | Uint8Array, pubkey: string): Uint8Array {
  const priv = typeof privkey === "string" ? hexToBytes(privkey) : privkey;
  const shared = secp256k1.getSharedSecret(priv, hexToBytes(`02${pubkey}`));
  return extract(sha256, shared.subarray(1, 33), SALT);
}

function getMessageKeys(conversationKey: Uint8Array, nonce: Uint8Array): {
  chachaKey: Uint8Array;
  chachaNonce: Uint8Array;
  hmacKey: Uint8Array;
} {
  if (conversationKey.length !== 32) throw new Error("conversation key must be 32 bytes");
  if (nonce.length !== 32) throw new Error("nonce must be 32 bytes");
  const keys = expand(sha256, conversationKey, nonce, 76);
  return {
    chachaKey: keys.subarray(0, 32),
    chachaNonce: keys.subarray(32, 44),
    hmacKey: keys.subarray(44, 76)
  };
}

function hmacAad(key: Uint8Array, message: Uint8Array, aad: Uint8Array): Uint8Array {
  if (aad.length !== 32) throw new Error("AAD must be 32 bytes");
  return hmac(sha256, key, concatBytes(aad, message));
}

// --- public API ---
export function encrypt(plaintext: string, conversationKey: Uint8Array, nonce: Uint8Array = randomBytes(32)): string {
  const { chachaKey, chachaNonce, hmacKey } = getMessageKeys(conversationKey, nonce);
  const padded = pad(plaintext);
  const ciphertext = chacha20(chachaKey, chachaNonce, padded);
  const mac = hmacAad(hmacKey, ciphertext, nonce);
  return bytesToBase64(concatBytes(new Uint8Array([VERSION]), nonce, ciphertext, mac));
}

export function decrypt(payload: string, conversationKey: Uint8Array): string {
  if (typeof payload !== "string") throw new Error("payload must be a string");
  if (payload.length < 132 || payload.length > 87472) throw new Error("invalid payload length");
  if (payload[0] === "#") throw new Error("unsupported version");
  const data = base64ToBytes(payload);
  const version = data[0];
  if (version !== VERSION) throw new Error(`unknown version ${version}`);
  if (data.length < 99 || data.length > 65603) throw new Error("invalid payload size");
  const nonce = data.subarray(1, 33);
  const ciphertext = data.subarray(33, data.length - 32);
  const mac = data.subarray(data.length - 32);
  const { chachaKey, chachaNonce, hmacKey } = getMessageKeys(conversationKey, nonce);
  if (!equalBytes(hmacAad(hmacKey, ciphertext, nonce), mac)) throw new Error("invalid MAC");
  return unpad(chacha20(chachaKey, chachaNonce, ciphertext));
}
