import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { schnorr, secp256k1 } from "@noble/curves/secp256k1.js";
import { bytesToHex, hexToBytes } from "@noble/hashes/utils.js";
import * as ntNip44 from "nostr-tools/nip44";
import { getConversationKey, encrypt, decrypt } from "./nip44.js";

// Official NIP-44 v2 test vectors (nostr-protocol/nips, paulmillr/nip44 reference).
// Vendored verbatim at test-fixtures/nip44-official-vectors.json for reproducibility.
const vectors = JSON.parse(
  readFileSync(fileURLToPath(new URL("./test-fixtures/nip44-official-vectors.json", import.meta.url)), "utf-8")
).v2;

describe("nip44 v2 — official vectors", () => {
  it("derives every conversation key", () => {
    for (const v of vectors.valid.get_conversation_key) {
      expect(bytesToHex(getConversationKey(v.sec1, v.pub2))).toBe(v.conversation_key);
    }
  });

  it("encrypts to the exact payload (fixed nonce) and decrypts back", () => {
    for (const v of vectors.valid.encrypt_decrypt) {
      const ck = hexToBytes(v.conversation_key);
      expect(encrypt(v.plaintext, ck, hexToBytes(v.nonce))).toBe(v.payload);
      expect(decrypt(v.payload, ck)).toBe(v.plaintext);
    }
  });

  it("rejects every invalid-decrypt vector", () => {
    for (const v of vectors.invalid.decrypt) {
      const ck = hexToBytes(v.conversation_key);
      expect(() => decrypt(v.payload, ck)).toThrow();
    }
  });

  it("rejects malformed base64 payloads (strict decoder)", () => {
    const v = vectors.valid.encrypt_decrypt[0];
    const ck = hexToBytes(v.conversation_key);
    const mid = Math.floor(v.payload.length / 2);
    // '=' injected mid-string (padding outside the final group)
    expect(() => decrypt(`${v.payload.slice(0, mid)}=${v.payload.slice(mid + 1)}`, ck)).toThrow();
    // non-ASCII character (charCode > 255) must be rejected, not silently treated as 0
    expect(() => decrypt(`${v.payload.slice(0, mid)}Ā${v.payload.slice(mid + 1)}`, ck)).toThrow();
  });
});

describe("nip44 v2 — differential vs nostr-tools", () => {
  it("matches nostr-tools for conversation keys and cross round-trips", () => {
    const lengths = [1, 32, 33, 100, 1000, 65535];
    for (const length of lengths) {
      const skA = secp256k1.utils.randomSecretKey();
      const skB = secp256k1.utils.randomSecretKey();
      const pubA = bytesToHex(schnorr.getPublicKey(skA));
      const pubB = bytesToHex(schnorr.getPublicKey(skB));

      const ckOurs = getConversationKey(bytesToHex(skA), pubB);
      const ckTheirs = ntNip44.getConversationKey(skA, pubB);
      expect(bytesToHex(ckOurs)).toBe(bytesToHex(ckTheirs));

      const plaintext = "x".repeat(length);
      // our decrypt of their ciphertext, and theirs of ours, plus reverse direction (B->A)
      expect(decrypt(ntNip44.encrypt(plaintext, ckTheirs), ckOurs)).toBe(plaintext);
      expect(ntNip44.decrypt(encrypt(plaintext, ckOurs), ckTheirs)).toBe(plaintext);
      const ckReverse = getConversationKey(bytesToHex(skB), pubA);
      expect(bytesToHex(ckReverse)).toBe(bytesToHex(ckOurs));
    }
  });
});
