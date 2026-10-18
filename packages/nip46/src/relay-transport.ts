// Relay transport boundary for NIP-46 over Nostr relays.
// I/O only — no protocol decisions. Two implementations exist: this in-memory
// fake (deterministic, used by tests + the in-process e2e) and a nostr-tools
// backed adapter for production (see relay-pool-adapter.ts).

export type RelayEvent = {
  id: string;
  pubkey: string;
  created_at: number;
  kind: number;
  tags: string[][];
  content: string;
  sig: string;
};

export type RelayFilter = {
  kinds?: number[];
  authors?: string[];
  "#p"?: string[];
  since?: number;
};

export type RelaySubscription = {
  close: () => void;
};

export type RelayEventHandler = (event: RelayEvent) => void;

export interface RelayTransport {
  publish(event: RelayEvent): Promise<void>;
  subscribe(filter: RelayFilter, onEvent: RelayEventHandler): Promise<RelaySubscription>;
  close(): Promise<void>;
}

export function eventMatchesFilter(event: RelayEvent, filter: RelayFilter): boolean {
  if (filter.kinds !== undefined && !filter.kinds.includes(event.kind)) return false;
  if (filter.authors !== undefined && !filter.authors.includes(event.pubkey)) return false;
  if (filter.since !== undefined && event.created_at < filter.since) return false;
  const pValues = filter["#p"];
  if (pValues !== undefined) {
    const hasMatch = event.tags.some((tag) => tag[0] === "p" && pValues.includes(tag[1]));
    if (!hasMatch) return false;
  }
  return true;
}

type Listener = { filter: RelayFilter; onEvent: RelayEventHandler };

// Deterministic in-process relay: keeps published events and replays matching
// history to new subscribers, then forwards future matching events live.
export class InMemoryRelay implements RelayTransport {
  private readonly events: RelayEvent[] = [];
  private readonly listeners = new Set<Listener>();
  private closed = false;

  async publish(event: RelayEvent): Promise<void> {
    if (this.closed) throw new Error("relay is closed");
    this.events.push(event);
    // Snapshot listeners so a handler subscribing/closing during fan-out cannot
    // perturb this delivery (well-defined dispatch).
    for (const listener of [...this.listeners]) {
      if (this.listeners.has(listener) && eventMatchesFilter(event, listener.filter)) listener.onEvent(event);
    }
  }

  // Historical replay is synchronous (deterministic for tests/e2e): `onEvent`
  // fires for matching past events before this method returns, so callers must
  // not assume the returned subscription handle exists inside an initial-replay
  // callback.
  async subscribe(filter: RelayFilter, onEvent: RelayEventHandler): Promise<RelaySubscription> {
    if (this.closed) throw new Error("relay is closed");
    const listener: Listener = { filter, onEvent };
    this.listeners.add(listener);
    for (const event of this.events) {
      if (eventMatchesFilter(event, filter)) onEvent(event);
    }
    return {
      close: () => {
        this.listeners.delete(listener);
      }
    };
  }

  async close(): Promise<void> {
    this.closed = true;
    this.listeners.clear();
  }
}
