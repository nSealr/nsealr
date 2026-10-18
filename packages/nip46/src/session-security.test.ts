import { afterEach, describe, expect, it, vi } from "vitest";
import { finalizeEvent, getPublicKey } from "nostr-tools/pure";
import { useWebSocketImplementation } from "nostr-tools/pool";
import { evaluateNip46RelayResponseStep } from "./nip46.js";
import { Nip46SessionManager } from "./session-manager.js";
import { buildNip46RequestEvent, decryptNip46Event } from "./session-protocol.js";
import { NostrToolsRelay } from "./relay-pool-adapter.js";
import type { RelayEvent, RelayEventHandler, RelayTransport } from "./relay-transport.js";

// Public fixture scalars, never production material. The expected public keys
// and signed event oracle come from nostr-tools, independently of the manager.
const key = (n: number): Uint8Array => Uint8Array.from({ length: 32 }, (_, i) => i === 31 ? n : 0);
const client = key(1), remote = key(2), user = key(3), foreign = key(4);
const remotePubkey = getPublicKey(remote), userPubkey = getPublicKey(user);
const template = { created_at: 1700000000, kind: 1, tags: [] as string[][], content: "S01 public fixture" };
type Message = { id: string; method: string; params: string[] };
const sessions: Nip46SessionManager[] = [];
afterEach(async () => { await Promise.all(sessions.splice(0).map(s => s.close())); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); });

function harness(reply?: (message: Message, deliver: (text: string, author?: Uint8Array) => void) => void,
  options: Partial<ConstructorParameters<typeof Nip46SessionManager>[0]> = {}) {
  let handler: RelayEventHandler = () => undefined;
  const messages: Message[] = [];
  const subscriptions: Array<{ closed: boolean }> = [];
  const deliver = (text: string, author = remote) => handler(buildNip46RequestEvent(author, getPublicKey(client), text, 1700000000));
  const transport: RelayTransport = {
    async subscribe(_filter, onEvent) { handler = onEvent; const sub = { closed: false }; subscriptions.push(sub); return { close: () => { sub.closed = true; } }; },
    async publish(event) {
      const message = JSON.parse(decryptNip46Event(remote, event)) as Message;
      messages.push(message);
      if (reply) reply(message, deliver);
      else deliver(JSON.stringify({ id: message.id, result: message.method === "get_public_key" ? userPubkey : message.method === "sign_event" ? JSON.stringify(finalizeEvent(JSON.parse(message.params[0]), user)) : "ack" }));
    },
    async close() {}
  };
  const session = new Nip46SessionManager({ clientSecretKey: client, remoteSignerPubkey: remotePubkey, transport, requestTimeoutMs: 200, ...options });
  sessions.push(session);
  return { session, transport, messages, subscriptions, deliver };
}

function ordinaryReply(message: Message, deliver: (text: string, author?: Uint8Array) => void) {
  deliver(JSON.stringify({ id: message.id, result: message.method === "get_public_key" ? userPubkey : message.method === "sign_event" ? JSON.stringify(finalizeEvent(JSON.parse(message.params[0]), user)) : "ack" }));
}

describe("S01 authenticated session boundary", () => {
  it("discovers the user separately from transport before activation", async () => {
    const { session, messages } = harness();
    await session.connect();
    expect(messages.map(m => m.method)).toEqual(["connect", "get_public_key"]);
    expect((session as unknown as { userPubkey?: string }).userPubkey).toBe(userPubkey);
    expect((await session.signEvent(template)).pubkey).toBe(userPubkey);
    expect(userPubkey).not.toBe(remotePubkey);
  });

  it("rejects a changed user key with a valid event signature", async () => {
    let selected = user;
    const { session } = harness((message, deliver) => {
      if (message.method !== "sign_event") return ordinaryReply(message, deliver);
      deliver(JSON.stringify({ id: message.id, result: JSON.stringify(finalizeEvent(JSON.parse(message.params[0]), selected)) }));
    });
    await session.connect();
    expect((await session.signEvent(template)).pubkey).toBe(userPubkey);
    selected = foreign;
    await expect(session.signEvent(template)).rejects.toThrow(/user|identity|pubkey/i);
  });

  it("ignores foreign signed transport authors delivered past adapter filters", async () => {
    const { session } = harness((message, deliver) => {
      if (message.method !== "sign_event") return ordinaryReply(message, deliver);
      deliver(JSON.stringify({ id: message.id, result: JSON.stringify(finalizeEvent(JSON.parse(message.params[0]), user)) }), foreign);
      deliver(JSON.stringify({ id: message.id, error: "expected author control" }));
    });
    await session.connect();
    await expect(session.signEvent(template)).rejects.toThrow("expected author control");
  });

  it.each(["duplicate", "escaped duplicate", "trailing"])("rejects %s wire JSON without consuming the request", async (variant) => {
    const { session } = harness((message, deliver) => {
      if (message.method !== "sign_event") return ordinaryReply(message, deliver);
      const result = JSON.stringify(JSON.stringify(finalizeEvent(JSON.parse(message.params[0]), user)));
      const extra = variant === "escaped duplicate" ? '"\\u0069d"' : '"id"';
      deliver(variant === "trailing" ? JSON.stringify({ id: message.id, result: JSON.parse(result) }) + "{}" : `{${extra}:"ignored","id":${JSON.stringify(message.id)},"result":${result}}`);
      deliver(JSON.stringify({ id: message.id, error: "strict parse control" }));
    });
    await session.connect();
    await expect(session.signEvent(template)).rejects.toThrow("strict parse control");
  });

  it("rejects nested signed-event duplicate members", async () => {
    const { session } = harness((message, deliver) => {
      if (message.method !== "sign_event") return ordinaryReply(message, deliver);
      const event = JSON.stringify(finalizeEvent(JSON.parse(message.params[0]), user));
      deliver(JSON.stringify({ id: message.id, result: '{"pubkey":"ignored",' + event.slice(1) }));
    });
    await session.connect();
    await expect(session.signEvent(template)).rejects.toThrow(/duplicate|JSON/i);
  });

  it("cannot reactivate after close races a response", async () => {
    const { session, transport } = harness();
    const original = transport.publish;
    transport.publish = async event => { await original(event); await session.close(); };
    await expect(session.connect()).rejects.toThrow(/clos/i);
    expect(session.phase).toBe("session_closed");
  });

  it("does not reuse IDs when the caller RNG repeats", async () => {
    const { session, messages } = harness(undefined, { randomId: () => "repeat" });
    await session.connect();
    await session.signEvent(template);
    await session.signEvent(template);
    expect(new Set(messages.map(m => m.id)).size).toBe(messages.length);
  });
});

describe("S01 default adapter control", () => {
  it("locked SimplePool filters foreign authors even if the relay sends them", async () => {
    let socket: FakeSocket | undefined;
    const sent: string[] = [];
    class FakeSocket {
      readyState = 1;
      onopen?: () => void;
      onclose?: (event: { message: string }) => void;
      onmessage?: (event: { data: string }) => void;
      constructor() { socket = this; queueMicrotask(() => this.onopen?.()); }
      send(data: string) { sent.push(data); }
      close() { this.readyState = 3; this.onclose?.({ message: "closed" }); }
    }
    useWebSocketImplementation(FakeSocket);
    const adapter = new NostrToolsRelay(["wss://s01.invalid"]);
    const received: RelayEvent[] = [];
    const sub = await adapter.subscribe({ kinds: [24133], authors: [remotePubkey] }, e => received.push(e));
    try {
      await vi.waitFor(() => expect(sent.some(s => JSON.parse(s)[0] === "REQ")).toBe(true));
      const id = JSON.parse(sent.find(s => JSON.parse(s)[0] === "REQ")!)[1];
      const bad = buildNip46RequestEvent(foreign, getPublicKey(client), '{"id":"probe","result":"ack"}', 1700000000);
      const good = buildNip46RequestEvent(remote, getPublicKey(client), '{"id":"probe","result":"ack"}', 1700000000);
      socket!.onmessage!({ data: JSON.stringify(["EVENT", id, bad]) });
      socket!.onmessage!({ data: JSON.stringify(["EVENT", id, good]) });
      expect(received.map(e => e.pubkey)).toEqual([remotePubkey]);
    } finally { sub.close(); await adapter.close(); useWebSocketImplementation(WebSocket); }
  });
});


describe("S01 distinct metadata identities and envelope", () => {
  it("permits a signed user result distinct from transport author", () => {
    const result = JSON.stringify(finalizeEvent(structuredClone(template), user));
    const step = { direction: "remote_signer_to_client", event: buildNip46RequestEvent(remote, getPublicKey(client), "opaque", 1700000000), decrypted_message: { id: "metadata", result }, expected_user_pubkey: userPubkey };
    expect(evaluateNip46RelayResponseStep(step)).toMatchObject({ format: "nsealr-nip46-relay-response-step-v1", result_pubkey: userPubkey, result_pubkey_bound_to_expected_user: true });
  });
  it("rejects signed ambiguous recipient tags", () => {
    const original = buildNip46RequestEvent(remote, getPublicKey(client), "hello", 1700000000);
    const event = finalizeEvent({ ...original, tags: [...original.tags, ["p", getPublicKey(foreign)]] }, remote);
    expect(() => decryptNip46Event(client, event)).toThrow(/recipient|address/i);
  });
});

describe("S01 identity, replay and cancellation regressions", () => {
  it.each(["0".repeat(64), "f".repeat(64), "AA".repeat(32), "bad"])("rejects invalid discovered curve key %s", async invalid => {
    const { session, subscriptions, messages } = harness((message, deliver) => {
      deliver(JSON.stringify({ id: message.id, result: message.method === "get_public_key" ? invalid : "ack" }));
    });
    await expect(session.connect()).rejects.toThrow(/pubkey/i);
    expect(session.phase).toBe("idle");
    expect(session.userPubkey).toBeUndefined();
    expect(subscriptions.every(s => s.closed)).toBe(true);
    expect(messages.some(m => m.method === "sign_event")).toBe(false);
  });

  it("validates configured curve keys and the expected initial identity", async () => {
    expect(() => harness(undefined, { expectedUserPubkey: "0".repeat(64) })).toThrow(/pubkey/i);
    expect(() => harness(undefined, { remoteSignerPubkey: "f".repeat(64) })).toThrow(/pubkey/i);
    const { session } = harness(undefined, { expectedUserPubkey: getPublicKey(foreign) });
    await expect(session.connect()).rejects.toThrow(/expected user/i);
    expect(session.userPubkey).toBeUndefined();
  });

  it("also permits a user key equal to the transport key", async () => {
    const { session } = harness((message, deliver) => {
      deliver(JSON.stringify({ id: message.id, result: message.method === "get_public_key" ? remotePubkey : message.method === "sign_event" ? JSON.stringify(finalizeEvent(JSON.parse(message.params[0]), remote)) : "ack" }));
    }, { expectedUserPubkey: remotePubkey });
    await session.connect();
    expect((await session.signEvent(template)).pubkey).toBe(remotePubkey);
  });

  it.each(["connect", "get_public_key", "sign_event"])("foreign signed errors cannot consume %s", async target => {
    const { session } = harness((message, deliver) => {
      if (message.method === target) deliver(JSON.stringify({ id: message.id, error: "foreign error" }), foreign);
      ordinaryReply(message, deliver);
    });
    await session.connect();
    await expect(session.signEvent(template)).resolves.toMatchObject({ pubkey: userPubkey });
  });

  it.each(["connect", "get_public_key"])("rejects unsupported auth challenge during %s and can retry", async target => {
    let challenge = true;
    const { session, messages, subscriptions } = harness((message, deliver) => {
      if (challenge && message.method === target) deliver(JSON.stringify({ id: message.id, result: "auth_url", error: "https://signer.example/auth" }));
      else ordinaryReply(message, deliver);
    }, { randomId: () => "repeat" });
    await expect(session.connect()).rejects.toThrow(/rejected/i);
    expect(session.phase).toBe("idle");
    expect(subscriptions[0].closed).toBe(true);
    challenge = false;
    await session.connect();
    expect(session.userPubkey).toBe(userPubkey);
    expect(new Set(messages.map(m => m.id)).size).toBe(messages.length);
  });

  it("ignores replayed completed and other-manager responses", async () => {
    let previous = "";
    const a = harness((message, deliver) => {
      if (message.method !== "sign_event") return ordinaryReply(message, deliver);
      previous = JSON.stringify({ id: message.id, result: JSON.stringify(finalizeEvent(JSON.parse(message.params[0]), user)) });
      deliver(previous);
    }, { randomId: () => "repeat" });
    await a.session.connect();
    await a.session.signEvent(template);
    const b = harness((message, deliver) => {
      if (message.method !== "sign_event") return ordinaryReply(message, deliver);
      deliver(previous);
      deliver(JSON.stringify({ id: message.id, error: "current response" }));
    }, { randomId: () => "repeat" });
    await b.session.connect();
    await expect(b.session.signEvent(template)).rejects.toThrow("current response");
    expect(new Set([...a.messages, ...b.messages].map(m => m.id)).size).toBe(a.messages.length + b.messages.length);
  });

  it("snapshots the submitted template before asynchronous work", async () => {
    const { session } = harness();
    await session.connect();
    const original = { ...template, tags: [["t", "original"]] };
    const signing = session.signEvent(original);
    original.content = "changed";
    original.tags[0][1] = "changed";
    await expect(signing).resolves.toMatchObject({ content: template.content, tags: [["t", "original"]] });
  });

  it("rejects malformed correlated replies and preserves remote rejection", async () => {
    let malformed = true;
    const { session } = harness((message, deliver) => {
      if (message.method !== "sign_event") return ordinaryReply(message, deliver);
      deliver(JSON.stringify(malformed ? { id: message.id, result: "ok", extra: true } : { id: message.id, error: "user cancelled" }));
    });
    await session.connect();
    await expect(session.signEvent(template)).rejects.toThrow(/unsupported|unknown/i);
    malformed = false;
    await expect(session.signEvent(template)).rejects.toThrow("user cancelled");
  });

  it("times out stalled publish and cancels it without unhandled rejection", async () => {
    vi.useFakeTimers();
    const { session, transport, subscriptions } = harness(undefined, { requestTimeoutMs: 10 });
    let rejectPublish: (e: Error) => void = () => undefined;
    transport.publish = () => new Promise((_resolve, reject) => { rejectPublish = reject; });
    const check = expect(session.connect()).rejects.toThrow(/timed out/);
    await vi.advanceTimersByTimeAsync(11);
    await check;
    expect(session.phase).toBe("idle");
    expect(subscriptions[0].closed).toBe(true);
    rejectPublish(new Error("late publish failure"));
    await Promise.resolve();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("closes a subscription acquired after connect cancellation", async () => {
    const { session, transport } = harness();
    let acquire: (subscription: { close: () => void }) => void = () => undefined;
    transport.subscribe = () => new Promise(resolve => { acquire = resolve; });
    const check = expect(session.connect()).rejects.toThrow(/clos/i);
    await session.close();
    await check;
    const close = vi.fn();
    acquire({ close });
    await Promise.resolve();
    expect(close).toHaveBeenCalledOnce();
    expect(session.phase).toBe("session_closed");
  });

  it("times out subscription acquisition and rejects concurrent connect", async () => {
    vi.useFakeTimers();
    const { session, transport } = harness(undefined, { requestTimeoutMs: 10 });
    transport.subscribe = () => new Promise(() => undefined);
    const check = expect(session.connect()).rejects.toThrow(/subscribe timed out/);
    await expect(session.connect()).rejects.toThrow(/progress/);
    await vi.advanceTimersByTimeAsync(11);
    await check;
    expect(vi.getTimerCount()).toBe(0);
  });

  it("limits pending requests before publish and clears them on close", async () => {
    const { session, messages } = harness((message, deliver) => { if (message.method !== "sign_event") ordinaryReply(message, deliver); }, { maxPendingRequests: 2 });
    await session.connect();
    const first = expect(session.signEvent(template)).rejects.toThrow(/closed/);
    const second = expect(session.signEvent(template)).rejects.toThrow(/closed/);
    await expect(session.signEvent(template)).rejects.toThrow(/pending request limit/);
    expect(messages.filter(m => m.method === "sign_event")).toHaveLength(2);
    await session.close();
    await Promise.all([first, second]);
    expect((session as unknown as { pending: Map<string, unknown> }).pending.size).toBe(0);
    expect(session.userPubkey).toBeUndefined();
    expect(client[31]).toBe(1); // closing clears only the manager-owned copy
  });

  it("stops at counter exhaustion and validates resource options", async () => {
    for (const invalid of [0, -1, 1.5, NaN, Infinity, 300001]) expect(() => harness(undefined, { requestTimeoutMs: invalid })).toThrow();
    for (const invalid of [0, 257, NaN]) expect(() => harness(undefined, { maxPendingRequests: invalid })).toThrow();
    const { session, messages } = harness();
    await session.connect();
    (session as unknown as { counter: number }).counter = 0xffffffff;
    await expect(session.signEvent(template)).rejects.toThrow(/counter exhausted/);
    expect(messages).toHaveLength(2);
  });
});

describe("S01 unsettled adapter operation bounds", () => {
  it("rejects retry while a timed-out subscription acquisition remains unresolved", async () => {
    vi.useFakeTimers();
    const { session, transport } = harness(undefined, { requestTimeoutMs: 10 });
    const subscribe = transport.subscribe;
    let acquire: (value: { close: () => void }) => void = () => undefined;
    transport.subscribe = vi.fn(() => new Promise<{ close: () => void }>(resolve => { acquire = resolve; }));
    const first = expect(session.connect()).rejects.toThrow(/timed out/);
    await vi.advanceTimersByTimeAsync(11);
    await first;
    const retry = session.connect();
    const check = expect(retry).rejects.toThrow(/acquisition.*pending/);
    await vi.advanceTimersByTimeAsync(11);
    await check;
    expect(transport.subscribe).toHaveBeenCalledOnce();
    const close = vi.fn();
    acquire({ close });
    await Promise.resolve();
    expect(close).toHaveBeenCalledOnce();
    transport.subscribe = subscribe;
    await session.connect();
    expect(session.phase).toBe("session_active");
  });

  it("retains an unsettled publication slot across timeout and reclaims it on settlement", async () => {
    vi.useFakeTimers();
    const { session, transport, messages } = harness(undefined, { requestTimeoutMs: 10, maxPendingRequests: 1 });
    await session.connect();
    const publish = transport.publish;
    let finishPublish: () => void = () => undefined;
    transport.publish = () => new Promise<void>(resolve => { finishPublish = resolve; });
    const first = expect(session.signEvent(template)).rejects.toThrow(/timed out/);
    await vi.advanceTimersByTimeAsync(11);
    await first;
    const check = expect(session.signEvent(template)).rejects.toThrow(/publish.*limit/);
    await vi.advanceTimersByTimeAsync(11);
    await check;
    finishPublish();
    await Promise.resolve();
    await Promise.resolve();
    transport.publish = publish;
    await expect(session.signEvent(template)).resolves.toMatchObject({ pubkey: userPubkey });
    expect(messages.map(m => m.method)).toEqual(["connect", "get_public_key", "sign_event"]);
  });

  it("cannot activate from a late publish completion after close", async () => {
    const { session, transport } = harness();
    const publish = transport.publish;
    let finish: () => void = () => undefined;
    transport.publish = async event => { await publish(event); await new Promise<void>(resolve => { finish = resolve; }); };
    const check = expect(session.connect()).rejects.toThrow(/clos/);
    await Promise.resolve();
    await Promise.resolve();
    await session.close();
    finish();
    await check;
    expect(session.phase).toBe("session_closed");
    expect(session.userPubkey).toBeUndefined();
  });
});

describe("S01 signed content and bounded envelope", () => {
  it.each(["template", "id", "signature"])("rejects a response with wrong %s", async alteration => {
    const { session } = harness((message, deliver) => {
      if (message.method !== "sign_event") return ordinaryReply(message, deliver);
      const event = finalizeEvent({ ...JSON.parse(message.params[0]), ...(alteration === "template" ? { content: "different reviewed content" } : {}) }, user);
      if (alteration === "id") event.id = "0".repeat(64);
      if (alteration === "signature") event.sig = "0".repeat(128);
      deliver(JSON.stringify({ id: message.id, result: JSON.stringify(event) }));
    });
    await session.connect();
    await expect(session.signEvent(template)).rejects.toThrow(/verification/);
  });

  it("ignores an invalid outer signature and raw over-limit JSON before a valid response", async () => {
    const { session } = harness((message, deliver) => {
      if (message.method !== "sign_event") return ordinaryReply(message, deliver);
      deliver(JSON.stringify({ id: message.id, error: "oversized" }).padEnd(1025, " "));
      deliver(JSON.stringify({ id: message.id, error: "bounded control" }));
    });
    await session.connect();
    await expect(session.signEvent(template)).rejects.toThrow("bounded control");
    const event = buildNip46RequestEvent(remote, getPublicKey(client), "hello", 1700000000);
    expect(() => decryptNip46Event(client, { ...event, sig: "0".repeat(128) })).toThrow(/signature/);
  });

  it("bounds encrypted content and tag dimensions before crypto", () => {
    const event = buildNip46RequestEvent(remote, getPublicKey(client), "hello", 1700000000);
    expect(() => decryptNip46Event(client, { ...event, content: "x".repeat(2049) })).toThrow(/bounds/);
    expect(() => decryptNip46Event(client, { ...event, tags: Array.from({ length: 17 }, () => ["x"]) })).toThrow(/bounds/);
    expect(() => decryptNip46Event(client, { ...event, tags: [["x", "x".repeat(65)]] })).toThrow(/bounds/);
    expect(() => decryptNip46Event(client, { ...event, tags: [Array(9).fill("x")] })).toThrow(/bounds/);
  });
});
