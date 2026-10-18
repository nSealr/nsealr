import { describe, expect, it } from "vitest";
import { schnorr } from "@noble/curves/secp256k1.js";
import { bytesToHex, hexToBytes } from "@noble/hashes/utils.js";
import { computeEventId, verifySchnorrSignature } from "@nsealr/core";
import { InMemoryRelay, type RelayEvent, type RelayTransport } from "./relay-transport.js";
import { buildNip46RequestEvent, decryptNip46Event } from "./session-protocol.js";
import { Nip46SessionManager } from "./session-manager.js";

// Signs a bare (unencrypted) nostr event template with the user key — what a
// real remote signer does for sign_event. Test-local; no dependency on dev-signer.
function signEventTemplate(template: { created_at: number; kind: number; tags: string[][]; content: string }, userSecretKey: Uint8Array): RelayEvent {
  const pubkey = bytesToHex(schnorr.getPublicKey(userSecretKey));
  const full = { pubkey, ...template };
  const id = computeEventId(full);
  const sig = bytesToHex(schnorr.sign(hexToBytes(id), userSecretKey));
  return { ...full, id, sig };
}

// Minimal remote-signer counterparty: answers connect with "ack" and sign_event
// with a real user-key signature, over the same relay transport.
function startRemoteSigner(transport: RelayTransport, remoteSecretKey: Uint8Array, userSecretKey: Uint8Array): Promise<unknown> {
  const remotePubkey = bytesToHex(schnorr.getPublicKey(remoteSecretKey));
  return transport.subscribe({ kinds: [24133], "#p": [remotePubkey] }, (event) => {
    void (async () => {
      const message = JSON.parse(decryptNip46Event(remoteSecretKey, event)) as { id: string; method: string; params: string[] };
      let result = "ack";
      if (message.method === "get_public_key") result = bytesToHex(schnorr.getPublicKey(userSecretKey));
      if (message.method === "sign_event") {
        result = JSON.stringify(signEventTemplate(JSON.parse(message.params[0]), userSecretKey));
      }
      const responseEvent = buildNip46RequestEvent(remoteSecretKey, event.pubkey, JSON.stringify({ id: message.id, result }), 1700000000);
      await transport.publish(responseEvent);
    })();
  });
}

describe("Nip46SessionManager", () => {
  it("connects and signs an event end-to-end over the in-memory relay", async () => {
    const transport = new InMemoryRelay();
    const clientSk = schnorr.utils.randomSecretKey();
    const remoteSk = schnorr.utils.randomSecretKey();
    const userSk = schnorr.utils.randomSecretKey();
    await startRemoteSigner(transport, remoteSk, userSk);

    const sm = new Nip46SessionManager({
      clientSecretKey: clientSk,
      remoteSignerPubkey: bytesToHex(schnorr.getPublicKey(remoteSk)),
      transport
    });
    expect(sm.phase).toBe("idle");
    await sm.connect();
    expect(sm.phase).toBe("session_active");

    const template = { created_at: 1700000000, kind: 1, tags: [] as string[][], content: "hello nostr" };
    const signed = await sm.signEvent(template);
    expect(signed.content).toBe("hello nostr");
    expect(signed.pubkey).toBe(bytesToHex(schnorr.getPublicKey(userSk)));
    expect(computeEventId(signed)).toBe(signed.id);
    expect(verifySchnorrSignature(signed.pubkey, signed.id, signed.sig)).toBe(true);

    await sm.close();
    expect(sm.phase).toBe("session_closed");
  });

  it("rejects signing before connect", async () => {
    const sm = new Nip46SessionManager({
      clientSecretKey: schnorr.utils.randomSecretKey(),
      remoteSignerPubkey: bytesToHex(schnorr.getPublicKey(schnorr.utils.randomSecretKey())),
      transport: new InMemoryRelay()
    });
    await expect(sm.signEvent({ created_at: 1, kind: 1, tags: [], content: "x" })).rejects.toThrow();
  });

  it("times out when no response arrives", async () => {
    const sm = new Nip46SessionManager({
      clientSecretKey: schnorr.utils.randomSecretKey(),
      remoteSignerPubkey: bytesToHex(schnorr.getPublicKey(schnorr.utils.randomSecretKey())),
      transport: new InMemoryRelay(),
      requestTimeoutMs: 20
    });
    await expect(sm.connect()).rejects.toThrow(/timed out/);
  });
});
