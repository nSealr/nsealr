import { describe, expect, it } from "vitest";
import { schnorr } from "@noble/curves/secp256k1.js";
import { bytesToHex } from "@noble/hashes/utils.js";
import { computeEventId, verifySchnorrSignature } from "@nsealr/core";
import { buildNip46RequestEvent, decryptNip46Event } from "./session-protocol.js";

describe("nip46 session protocol", () => {
  const clientSk = schnorr.utils.randomSecretKey();
  const remoteSk = schnorr.utils.randomSecretKey();
  const clientPub = bytesToHex(schnorr.getPublicKey(clientSk));
  const remotePub = bytesToHex(schnorr.getPublicKey(remoteSk));

  it("builds a signed, encrypted kind-24133 request the remote can decrypt", () => {
    const message = JSON.stringify({ id: "req-1", method: "sign_event", params: ["{}"] });
    const event = buildNip46RequestEvent(clientSk, remotePub, message, 1700000000);
    expect(event.kind).toBe(24133);
    expect(event.pubkey).toBe(clientPub);
    expect(event.tags).toEqual([["p", remotePub]]);
    expect(event.created_at).toBe(1700000000);
    expect(event.id).toBe(computeEventId(event));
    expect(verifySchnorrSignature(event.pubkey, event.id, event.sig)).toBe(true);
    expect(decryptNip46Event(remoteSk, event)).toBe(message);
  });

  it("round-trips a response back to the client", () => {
    const response = JSON.stringify({ id: "req-1", result: "ack" });
    const event = buildNip46RequestEvent(remoteSk, clientPub, response, 1700000001);
    expect(event.pubkey).toBe(remotePub);
    expect(decryptNip46Event(clientSk, event)).toBe(response);
  });

  it("rejects a tampered event id", () => {
    const event = buildNip46RequestEvent(clientSk, remotePub, "hello", 1700000000);
    expect(() => decryptNip46Event(remoteSk, { ...event, id: "0".repeat(64) })).toThrow();
  });

  it("rejects a tampered signature", () => {
    const event = buildNip46RequestEvent(clientSk, remotePub, "hello", 1700000000);
    expect(() => decryptNip46Event(remoteSk, { ...event, sig: "0".repeat(128) })).toThrow();
  });

  it("rejects a non-24133 event", () => {
    const event = buildNip46RequestEvent(clientSk, remotePub, "hello", 1700000000);
    expect(() => decryptNip46Event(remoteSk, { ...event, kind: 1 })).toThrow();
  });

  it("rejects tampered content (event id no longer matches)", () => {
    const event = buildNip46RequestEvent(clientSk, remotePub, "hello", 1700000000);
    expect(() => decryptNip46Event(remoteSk, { ...event, content: `${event.content}x` })).toThrow();
  });

  it("rejects an event addressed to a different recipient", () => {
    const event = buildNip46RequestEvent(clientSk, remotePub, "hello", 1700000000);
    const otherSk = schnorr.utils.randomSecretKey();
    expect(() => decryptNip46Event(otherSk, event)).toThrow(/not addressed/);
  });
});
