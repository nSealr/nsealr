// Production RelayTransport backed by nostr-tools SimplePool (real WebSocket I/O).
// This is the SINGLE place nostr-tools enters production code; it is confined to
// transport. All cryptography (signing, NIP-44, verification) stays hand-rolled.

import { SimplePool } from "nostr-tools/pool";
import type { RelayEvent, RelayEventHandler, RelayFilter, RelaySubscription, RelayTransport } from "./relay-transport.js";

// The minimal slice of SimplePool the adapter depends on (keeps it unit-testable
// with a lightweight mock pool).
export type RelayPool = Pick<SimplePool, "publish" | "subscribeMany" | "close">;

export class NostrToolsRelay implements RelayTransport {
  private readonly relays: string[];
  private readonly pool: RelayPool;
  private readonly subscriptions = new Set<{ close: () => void }>();
  private closed = false;

  constructor(relays: string[], pool: RelayPool = new SimplePool()) {
    if (relays.length === 0) throw new Error("at least one relay URL is required");
    this.relays = relays;
    this.pool = pool;
  }

  async publish(event: RelayEvent): Promise<void> {
    if (this.closed) throw new Error("relay is closed");
    // SimplePool.publish returns one promise per relay; success on any relay is
    // enough. Attach a catch to every promise so a non-winning relay rejection
    // never surfaces as an unhandled rejection.
    const results = this.pool.publish(this.relays, event);
    for (const result of results) void Promise.resolve(result).catch(() => undefined);
    try {
      await Promise.any(results);
    } catch (error) {
      const detail = error instanceof AggregateError ? error.errors.map((reason) => String(reason)).join("; ") : String(error);
      throw new Error(`failed to publish to all relays: ${detail}`);
    }
  }

  async subscribe(filter: RelayFilter, onEvent: RelayEventHandler): Promise<RelaySubscription> {
    if (this.closed) throw new Error("relay is closed");
    const inner = this.pool.subscribeMany(this.relays, filter, {
      onevent: (event): void => {
        onEvent({
          id: event.id,
          pubkey: event.pubkey,
          created_at: event.created_at,
          kind: event.kind,
          tags: event.tags,
          content: event.content,
          sig: event.sig
        });
      }
    });
    this.subscriptions.add(inner);
    return {
      close: () => {
        inner.close();
        this.subscriptions.delete(inner);
      }
    };
  }

  async close(): Promise<void> {
    this.closed = true;
    for (const inner of this.subscriptions) inner.close();
    this.subscriptions.clear();
    this.pool.close(this.relays);
  }
}
