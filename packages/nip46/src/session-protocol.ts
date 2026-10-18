// NIP-46 session wire protocol: build the client's signed + NIP-44-encrypted
// kind-24133 events and decrypt/verify the counterparty's events.
//
// The client transport keypair signs these kind-24133 events and performs the
// NIP-44 ECDH. It is NOT the user's signing key (which never leaves the device);
// it is an ephemeral transport key held in RAM by the caller and never persisted.

import { schnorr } from "@noble/curves/secp256k1.js";
import { bytesToHex, hexToBytes } from "@noble/hashes/utils.js";
import { computeEventId, nip44, verifySchnorrSignature } from "@nsealr/core";
import { utf8ByteLength } from "@nsealr/protocol";
import type { RelayEvent } from "./relay-transport.js";

const NIP46_EVENT_KIND = 24133;

function toSecretKeyBytes(secretKey: string | Uint8Array): Uint8Array {
  return typeof secretKey === "string" ? hexToBytes(secretKey) : secretKey;
}

// Build a signed, NIP-44-encrypted kind-24133 event addressed to `recipientPubkey`.
export function buildNip46RequestEvent(
  senderSecretKey: string | Uint8Array,
  recipientPubkey: string,
  message: string,
  createdAt: number
): RelayEvent {
  const secretKey = toSecretKeyBytes(senderSecretKey);
  const senderPubkey = bytesToHex(schnorr.getPublicKey(secretKey));
  const conversationKey = nip44.getConversationKey(secretKey, recipientPubkey);
  const content = nip44.encrypt(message, conversationKey);
  const template = {
    pubkey: senderPubkey,
    created_at: createdAt,
    kind: NIP46_EVENT_KIND,
    tags: [["p", recipientPubkey]],
    content
  };
  const id = computeEventId(template);
  const sig = bytesToHex(schnorr.sign(hexToBytes(id), secretKey));
  return { ...template, id, sig };
}

// Verify a kind-24133 event (id + BIP-340 signature) and NIP-44-decrypt its
// content using the recipient's secret key and the event sender's pubkey.
export function decryptNip46Event(recipientSecretKey: string | Uint8Array, event: RelayEvent): string {
  if (event.kind !== NIP46_EVENT_KIND) throw new Error(`NIP-46 event kind must be ${NIP46_EVENT_KIND}`);
  if (!/^[0-9a-f]{64}$/u.test(event.pubkey) || !/^[0-9a-f]{64}$/u.test(event.id) || !/^[0-9a-f]{128}$/u.test(event.sig) ||
    !Array.isArray(event.tags) || event.tags.length > 16 || event.tags.some(tag =>
    !Array.isArray(tag) || tag.length > 8 || tag.some(field => typeof field !== "string" || field.length > 64 || utf8ByteLength(field) > 64)
  ) || typeof event.content !== "string" || event.content.length > 2048 || utf8ByteLength(event.content) > 2048 ||
    !Number.isSafeInteger(event.created_at) || event.created_at < 0) {
    throw new Error("NIP-46 event exceeds envelope bounds or has invalid fields");
  }
  if (computeEventId(event) !== event.id) throw new Error("NIP-46 event id does not match its contents");
  if (!verifySchnorrSignature(event.pubkey, event.id, event.sig)) throw new Error("NIP-46 event signature is invalid");
  const secretKey = toSecretKeyBytes(recipientSecretKey);
  // Defense in depth: the wire layer must not rely solely on relay-side #p
  // filtering — require the event to be addressed to this recipient.
  const recipientPubkey = bytesToHex(schnorr.getPublicKey(secretKey));
  const recipients = event.tags.filter(tag => tag[0] === "p");
  if (recipients.length !== 1 || recipients[0][1] !== recipientPubkey) {
    throw new Error("NIP-46 event is not addressed to this recipient");
  }
  const conversationKey = nip44.getConversationKey(secretKey, event.pubkey);
  return nip44.decrypt(event.content, conversationKey);
}
