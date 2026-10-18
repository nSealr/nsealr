import { schnorr } from "@noble/curves/secp256k1.js";
import { sha256 } from "@noble/hashes/sha2.js";
import {
  bytesToHex as nobleBytesToHex,
  hexToBytes as nobleHexToBytes,
  utf8ToBytes
} from "@noble/hashes/utils.js";

export type EventTemplate = {
  created_at: number;
  kind: number;
  tags: string[][];
  content: string;
};

export type SignedEvent = EventTemplate & {
  id: string;
  pubkey: string;
  sig: string;
};

export type SignEventRequest = {
  version: 1;
  request_id: string;
  method: "sign_event";
  params: {
    event_template: EventTemplate;
  };
};

export type SignEventResponse = {
  version: 1;
  request_id: string;
  ok: true;
  result: {
    event: SignedEvent;
  };
};

export type VerificationResult = {
  ok: boolean;
  error?: string;
};

export function hexToBytes(hex: string): Uint8Array {
  if (!/^[0-9a-f]+$/u.test(hex) || hex.length % 2 !== 0) {
    throw new Error("expected lowercase even-length hex");
  }
  return nobleHexToBytes(hex);
}

export function bytesToHex(bytes: Uint8Array): string {
  return nobleBytesToHex(bytes);
}

export function sha256Utf8Hex(value: string): string {
  return bytesToHex(sha256(utf8ToBytes(value)));
}

export function canonicalEventSerialization(event: Pick<SignedEvent, "pubkey" | "created_at" | "kind" | "tags" | "content">): string {
  return JSON.stringify([0, event.pubkey, event.created_at, event.kind, event.tags, event.content]);
}

export function computeEventId(event: Pick<SignedEvent, "pubkey" | "created_at" | "kind" | "tags" | "content">): string {
  return sha256Utf8Hex(canonicalEventSerialization(event));
}

export function verifySchnorrSignature(pubkey: string, eventId: string, signature: string): boolean {
  if (!/^[0-9a-f]{64}$/u.test(pubkey) || !/^[0-9a-f]{64}$/u.test(eventId) || !/^[0-9a-f]{128}$/u.test(signature)) {
    return false;
  }
  return schnorr.verify(hexToBytes(signature), hexToBytes(eventId), hexToBytes(pubkey));
}

function sameTemplate(event: SignedEvent, template: EventTemplate): boolean {
  return (
    event.created_at === template.created_at &&
    event.kind === template.kind &&
    event.content === template.content &&
    JSON.stringify(event.tags) === JSON.stringify(template.tags)
  );
}

export function verifySignedEventResponse(request: unknown, response: unknown): VerificationResult {
  const req = request as Partial<SignEventRequest>;
  const res = response as Partial<SignEventResponse>;
  if (req.method !== "sign_event" || !req.params?.event_template) {
    return { ok: false, error: "request is not a sign_event request" };
  }
  if (res.ok !== true || !res.result?.event) {
    return { ok: false, error: "response is not a successful event response" };
  }
  if (res.request_id !== req.request_id) {
    return { ok: false, error: "response request_id does not match request" };
  }
  const event = res.result.event;
  if (!sameTemplate(event, req.params.event_template)) {
    return { ok: false, error: "signed event does not match requested template" };
  }
  const computedId = computeEventId(event);
  if (event.id !== computedId) {
    return { ok: false, error: "signed event id does not match NIP-01 canonical serialization" };
  }
  if (!verifySchnorrSignature(event.pubkey, event.id, event.sig)) {
    return { ok: false, error: "signed event signature is invalid" };
  }
  return { ok: true };
}
