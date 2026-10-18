import { describe, expect, it, vi } from "vitest";
import { NostrToolsRelay, type RelayPool } from "./relay-pool-adapter.js";
import type { RelayEvent } from "./relay-transport.js";

function event(): RelayEvent {
  return {
    id: "a".repeat(64),
    pubkey: "b".repeat(64),
    created_at: 1700000000,
    kind: 24133,
    tags: [["p", "c".repeat(64)]],
    content: "ciphertext",
    sig: "d".repeat(128)
  };
}

function mockPool(): { pool: RelayPool; captured: { params?: { onevent?: (event: RelayEvent) => void }; closed: boolean }; publish: ReturnType<typeof vi.fn>; close: ReturnType<typeof vi.fn> } {
  const captured: { params?: { onevent?: (event: RelayEvent) => void }; closed: boolean } = { closed: false };
  const publish = vi.fn(() => [Promise.resolve("ok")]);
  const close = vi.fn(() => {
    captured.closed = true;
  });
  const pool = {
    publish,
    subscribeMany: vi.fn((_relays: string[], _filter: unknown, params: { onevent?: (event: RelayEvent) => void }) => {
      captured.params = params;
      return { close: vi.fn() };
    }),
    close
  } as unknown as RelayPool;
  return { pool, captured, publish, close };
}

describe("NostrToolsRelay", () => {
  it("delegates publish to the pool for the configured relays", async () => {
    const { pool, publish } = mockPool();
    const adapter = new NostrToolsRelay(["wss://relay.example.com/"], pool);
    const e = event();
    await adapter.publish(e);
    expect(publish).toHaveBeenCalledWith(["wss://relay.example.com/"], e);
  });

  it("forwards subscribed events to the handler", async () => {
    const { pool, captured } = mockPool();
    const adapter = new NostrToolsRelay(["wss://relay.example.com/"], pool);
    const received: RelayEvent[] = [];
    await adapter.subscribe({ kinds: [24133], "#p": ["c".repeat(64)] }, (e) => received.push(e));
    captured.params?.onevent?.(event());
    expect(received).toHaveLength(1);
    expect(received[0].kind).toBe(24133);
  });

  it("closes the pool and rejects publish/subscribe afterwards", async () => {
    const { pool, close } = mockPool();
    const adapter = new NostrToolsRelay(["wss://relay.example.com/"], pool);
    await adapter.close();
    expect(close).toHaveBeenCalledWith(["wss://relay.example.com/"]);
    await expect(adapter.publish(event())).rejects.toThrow();
    await expect(adapter.subscribe({}, () => undefined)).rejects.toThrow();
  });
});
