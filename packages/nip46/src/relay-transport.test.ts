import { describe, expect, it } from "vitest";
import { InMemoryRelay, eventMatchesFilter, type RelayEvent } from "./relay-transport.js";

function evt(over: Partial<RelayEvent> = {}): RelayEvent {
  return {
    id: "a".repeat(64),
    pubkey: "b".repeat(64),
    created_at: 1000,
    kind: 24133,
    tags: [["p", "c".repeat(64)]],
    content: "ciphertext",
    sig: "d".repeat(128),
    ...over
  };
}

describe("eventMatchesFilter", () => {
  it("matches on kinds, authors, #p tag and since", () => {
    const event = evt();
    expect(eventMatchesFilter(event, { kinds: [24133], authors: ["b".repeat(64)], "#p": ["c".repeat(64)], since: 1000 })).toBe(true);
    expect(eventMatchesFilter(event, { kinds: [1] })).toBe(false);
    expect(eventMatchesFilter(event, { authors: ["z".repeat(64)] })).toBe(false);
    expect(eventMatchesFilter(event, { "#p": ["z".repeat(64)] })).toBe(false);
    expect(eventMatchesFilter(event, { since: 1001 })).toBe(false);
    expect(eventMatchesFilter(event, {})).toBe(true);
  });
});

describe("InMemoryRelay", () => {
  it("delivers a published event to a matching subscriber", async () => {
    const relay = new InMemoryRelay();
    const received: RelayEvent[] = [];
    await relay.subscribe({ kinds: [24133], "#p": ["c".repeat(64)] }, (event) => received.push(event));
    await relay.publish(evt());
    expect(received).toHaveLength(1);
    expect(received[0].content).toBe("ciphertext");
  });

  it("does not deliver events that fail the filter", async () => {
    const relay = new InMemoryRelay();
    const received: RelayEvent[] = [];
    await relay.subscribe({ kinds: [9999] }, (event) => received.push(event));
    await relay.publish(evt({ kind: 24133 }));
    expect(received).toHaveLength(0);
  });

  it("replays matching historical events on subscribe", async () => {
    const relay = new InMemoryRelay();
    await relay.publish(evt({ id: "1".repeat(64) }));
    const received: RelayEvent[] = [];
    await relay.subscribe({ kinds: [24133] }, (event) => received.push(event));
    expect(received).toHaveLength(1);
    expect(received[0].id).toBe("1".repeat(64));
  });

  it("stops delivering after the subscription is closed", async () => {
    const relay = new InMemoryRelay();
    const received: RelayEvent[] = [];
    const subscription = await relay.subscribe({ kinds: [24133] }, (event) => received.push(event));
    subscription.close();
    await relay.publish(evt());
    expect(received).toHaveLength(0);
  });

  it("rejects publish/subscribe after the relay is closed", async () => {
    const relay = new InMemoryRelay();
    await relay.close();
    await expect(relay.publish(evt())).rejects.toThrow();
    await expect(relay.subscribe({}, () => undefined)).rejects.toThrow();
  });
});
