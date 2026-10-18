import { execFileSync } from "node:child_process";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { schnorr } from "@noble/curves/secp256k1.js";
import { bytesToHex, hexToBytes } from "@noble/hashes/utils.js";
import { computeEventId, verifySchnorrSignature } from "@nsealr/core";
import { NostrToolsRelay } from "./relay-pool-adapter.js";
import { Nip46SessionManager } from "./session-manager.js";
import { buildNip46RequestEvent, decryptNip46Event } from "./session-protocol.js";

// Live end-to-end over a REAL Nostr relay in Docker. Gated by NSEALR_LIVE_E2E so
// it never runs in the base `make ci` (which must stay fast and Docker-free).
// Run with: NSEALR_LIVE_E2E=1 pnpm exec vitest run packages/nip46/src/session-live.e2e.test.ts

const RELAY_PORT = 8088;
const RELAY_URL = `ws://localhost:${RELAY_PORT}`;
const IMAGE = "scsibug/nostr-rs-relay";

function signEventTemplate(template: { created_at: number; kind: number; tags: string[][]; content: string }, userSecretKey: Uint8Array) {
  const pubkey = bytesToHex(schnorr.getPublicKey(userSecretKey));
  const full = { pubkey, ...template };
  const id = computeEventId(full);
  return { ...full, id, sig: bytesToHex(schnorr.sign(hexToBytes(id), userSecretKey)) };
}

async function waitForRelay(url: string, timeoutMs: number): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const reachable = await new Promise<boolean>((resolve) => {
      const ws = new WebSocket(url);
      const timer = setTimeout(() => {
        ws.close();
        resolve(false);
      }, 1000);
      ws.onopen = () => {
        clearTimeout(timer);
        ws.close();
        resolve(true);
      };
      ws.onerror = () => {
        clearTimeout(timer);
        resolve(false);
      };
    });
    if (reachable) return;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("relay did not become ready");
}

describe.skipIf(!process.env.NSEALR_LIVE_E2E)("NIP-46 live e2e over a Docker relay", () => {
  let containerId = "";

  beforeAll(async () => {
    execFileSync("docker", ["pull", IMAGE], { stdio: "ignore" });
    containerId = execFileSync("docker", ["run", "-d", "-p", `${RELAY_PORT}:8080`, IMAGE]).toString().trim();
    await waitForRelay(RELAY_URL, 30000);
  }, 180000);

  afterAll(() => {
    if (containerId) execFileSync("docker", ["rm", "-f", containerId], { stdio: "ignore" });
  });

  it("connects and signs end-to-end through a real relay", async () => {
    const clientSk = schnorr.utils.randomSecretKey();
    const remoteSk = schnorr.utils.randomSecretKey();
    const userSk = schnorr.utils.randomSecretKey();
    const remotePub = bytesToHex(schnorr.getPublicKey(remoteSk));

    // Remote signer counterparty on its own relay connection.
    const remoteRelay = new NostrToolsRelay([RELAY_URL]);
    const remoteSubscription = await remoteRelay.subscribe({ kinds: [24133], "#p": [remotePub] }, (event) => {
      void (async () => {
        try {
          const message = JSON.parse(decryptNip46Event(remoteSk, event)) as { id: string; method: string; params: string[] };
          const result = message.method === "sign_event"
            ? JSON.stringify(signEventTemplate(JSON.parse(message.params[0]), userSk))
            : message.method === "get_public_key" ? bytesToHex(schnorr.getPublicKey(userSk)) : "ack";
          const response = JSON.stringify({ id: message.id, result });
          await remoteRelay.publish(buildNip46RequestEvent(remoteSk, event.pubkey, response, Math.floor(Date.now() / 1000)));
        } catch {
          // ignore: the relay may be closing during teardown after the assertions ran
        }
      })();
    });

    const clientRelay = new NostrToolsRelay([RELAY_URL]);
    const session = new Nip46SessionManager({
      clientSecretKey: clientSk,
      remoteSignerPubkey: remotePub,
      transport: clientRelay,
      requestTimeoutMs: 15000
    });

    await session.connect();
    expect(session.phase).toBe("session_active");

    const signed = await session.signEvent({ created_at: Math.floor(Date.now() / 1000), kind: 1, tags: [], content: "live relay hello" });
    expect(signed.content).toBe("live relay hello");
    expect(signed.pubkey).toBe(bytesToHex(schnorr.getPublicKey(userSk)));
    expect(verifySchnorrSignature(signed.pubkey, signed.id, signed.sig)).toBe(true);

    await session.close();
    remoteSubscription.close();
    await remoteRelay.close();
  }, 40000);
});
