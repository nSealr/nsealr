// The caller authenticates/selects the remote transport key. This manager binds
// that peer and its separately resolved user identity for one in-memory session.
import { schnorr } from "@noble/curves/secp256k1.js";
import { bytesToHex, hexToBytes } from "@noble/hashes/utils.js";
import { verifySignedEventResponse, type EventTemplate, type SignedEvent } from "@nsealr/core";
import { NSEALR_V0_LIMITS, parseStrictJson, validateRequest, validateResponse } from "@nsealr/protocol";
import { requireResponseMessage, type Nip46ResponseMessage } from "./nip46.js";
import { buildNip46RequestEvent, decryptNip46Event } from "./session-protocol.js";
import type { RelayEvent, RelaySubscription, RelayTransport } from "./relay-transport.js";

export type SessionPhase = "idle" | "session_active" | "session_closed";
export type Nip46SessionManagerOptions = {
  clientSecretKey: string | Uint8Array;
  remoteSignerPubkey: string;
  expectedUserPubkey?: string;
  transport: RelayTransport;
  requestTimeoutMs?: number;
  maxPendingRequests?: number;
  now?: () => number;
  // Optional test suffix; cannot replace the mandatory random session namespace.
  randomId?: () => string;
};
type PendingRequest = {
  resolve: (message: Nip46ResponseMessage) => void;
  reject: (error: Error) => void;
  timer: ReturnType<typeof setTimeout>;
  published: boolean;
  message?: Nip46ResponseMessage;
};
function asError(value: unknown): Error { return value instanceof Error ? value : new Error(String(value)); }
function boundedInteger(value: number, max: number, label: string): number {
  if (!Number.isSafeInteger(value) || value < 1 || value > max) throw new Error(`${label} must be an integer in 1..${max}`);
  return value;
}
function publicKey(value: unknown, label: string): string {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/u.test(value)) throw new Error(`${label} must be a lowercase x-only pubkey`);
  try { schnorr.utils.lift_x(BigInt(`0x${value}`)); }
  catch { throw new Error(`${label} is not a valid secp256k1 pubkey`); }
  return value;
}

export class Nip46SessionManager {
  readonly clientPubkey: string;
  private phaseValue: SessionPhase = "idle";
  private readonly secretKey: Uint8Array;
  private readonly remoteSignerPubkey: string;
  private readonly expectedUserPubkey?: string;
  private userPubkeyValue: string | undefined;
  private readonly transport: RelayTransport;
  private readonly requestTimeoutMs: number;
  private readonly maxPendingRequests: number;
  private readonly now: () => number;
  private readonly randomId?: () => string;
  private readonly namespace = globalThis.crypto.randomUUID();
  private counter = 0;
  private epoch = 0;
  private subscribing = false;
  private publishing = 0;
  private readonly pending = new Map<string, PendingRequest>();
  private subscription: RelaySubscription | undefined;
  private connectFailure: ((error: Error) => void) | undefined;
  private closing: Promise<void> | undefined;

  constructor(options: Nip46SessionManagerOptions) {
    this.remoteSignerPubkey = publicKey(options.remoteSignerPubkey, "remote signer transport");
    this.expectedUserPubkey = options.expectedUserPubkey === undefined ? undefined : publicKey(options.expectedUserPubkey, "expected user");
    this.requestTimeoutMs = boundedInteger(options.requestTimeoutMs ?? 30000, 300000, "requestTimeoutMs");
    this.maxPendingRequests = boundedInteger(options.maxPendingRequests ?? 32, 256, "maxPendingRequests");
    this.secretKey = typeof options.clientSecretKey === "string" ? hexToBytes(options.clientSecretKey) : options.clientSecretKey.slice();
    this.clientPubkey = bytesToHex(schnorr.getPublicKey(this.secretKey));
    this.transport = options.transport;
    this.now = options.now ?? (() => Math.floor(Date.now() / 1000));
    this.randomId = options.randomId;
  }
  get phase(): SessionPhase { return this.phaseValue; }
  get userPubkey(): string | undefined { return this.userPubkeyValue; }

  // This profile supports direct ack only. Token discovery, auth challenges and
  // relay switching require separate reviewed caller flows.
  connect(): Promise<void> {
    if (this.phaseValue !== "idle") return Promise.reject(new Error(`cannot connect from phase ${this.phaseValue}`));
    if (this.connectFailure) return Promise.reject(new Error("NIP-46 connect already in progress"));
    if (this.subscribing) return Promise.reject(new Error("NIP-46 subscription acquisition still pending"));
    const epoch = ++this.epoch;
    return new Promise<void>((resolve, reject) => {
      let finished = false;
      // Subscription acquisition is also bounded; each subsequent request owns
      // its own deadline, including when publish never settles.
      const subscribeTimer = setTimeout(() => finish(new Error("NIP-46 subscribe timed out")), this.requestTimeoutMs);
      subscribeTimer.unref?.();
      const finish = (error?: Error): void => {
        if (finished) return;
        finished = true;
        clearTimeout(subscribeTimer);
        this.connectFailure = undefined;
        if (error) {
          ++this.epoch;
          this.userPubkeyValue = undefined;
          this.closeSubscription();
          this.rejectPending(error);
          reject(error);
        } else resolve();
      };
      this.connectFailure = finish;
      const run = async (): Promise<void> => {
        let subscription: RelaySubscription;
        this.subscribing = true;
        try {
          subscription = await this.transport.subscribe(
            { kinds: [24133], "#p": [this.clientPubkey], authors: [this.remoteSignerPubkey] },
            event => { if (this.epoch === epoch && this.phaseValue !== "session_closed") this.handleEvent(event); }
          );
        } finally { this.subscribing = false; }
        clearTimeout(subscribeTimer);
        if (finished || this.phaseValue === "session_closed" || this.epoch !== epoch) { subscription.close(); return; }
        this.subscription = subscription;
        const ack = await this.sendRequest("connect", [this.remoteSignerPubkey]);
        if (ack.error !== undefined) throw new Error(`NIP-46 connect rejected: ${ack.error}`);
        if (ack.result !== "ack") throw new Error('NIP-46 connect expected "ack"');
        const discovery = await this.sendRequest("get_public_key", []);
        if (discovery.error !== undefined) throw new Error(`NIP-46 get_public_key rejected: ${discovery.error}`);
        const user = publicKey(discovery.result, "resolved user");
        if (this.expectedUserPubkey !== undefined && user !== this.expectedUserPubkey) throw new Error("NIP-46 resolved user identity does not match expected user pubkey");
        if (finished || this.phaseValue !== "idle" || this.epoch !== epoch) throw new Error("NIP-46 session closed during connect");
        this.userPubkeyValue = user;
        this.phaseValue = "session_active";
        finish();
      };
      void run().catch(error => finish(asError(error)));
    });
  }

  async signEvent(template: EventTemplate): Promise<SignedEvent> {
    if (this.phaseValue !== "session_active") throw new Error(`cannot sign_event from phase ${this.phaseValue}`);
    const id = this.nextId();
    const request = { version: 1 as const, request_id: id, method: "sign_event" as const, params: { event_template: template } };
    const validation = validateRequest(request);
    if (!validation.ok) throw new Error(`NIP-46 sign_event request invalid: ${validation.error}`);
    const snapshot = JSON.parse(JSON.stringify(template)) as EventTemplate;
    const selectedUser = this.userPubkeyValue;
    const response = await this.sendRequest("sign_event", [JSON.stringify(snapshot)], id);
    if (this.phaseValue !== "session_active") throw new Error("NIP-46 session closed");
    if (response.error !== undefined) throw new Error(`NIP-46 sign_event rejected: ${response.error}`);
    if (response.result === undefined) throw new Error("NIP-46 sign_event response has no result");
    const event = parseStrictJson(response.result, NSEALR_V0_LIMITS.max_nip46_decrypted_message_json_bytes) as SignedEvent;
    const result = { version: 1, request_id: id, ok: true, result: { event } };
    const shape = validateResponse(result);
    if (!shape.ok) throw new Error(`NIP-46 signed event invalid: ${shape.error}`);
    if (event.pubkey !== selectedUser) throw new Error("NIP-46 signed event user identity does not match session pubkey");
    const verification = verifySignedEventResponse({ ...request, params: { event_template: snapshot } }, result);
    if (!verification.ok) throw new Error(`NIP-46 signed event failed verification: ${verification.error}`);
    return event;
  }

  close(): Promise<void> {
    if (this.closing) return this.closing;
    this.phaseValue = "session_closed";
    ++this.epoch;
    this.connectFailure?.(new Error("NIP-46 session closed"));
    this.closeSubscription();
    this.rejectPending(new Error("NIP-46 session closed"));
    this.userPubkeyValue = undefined;
    this.secretKey.fill(0);
    this.closing = Promise.resolve().then(() => this.transport.close());
    return this.closing;
  }

  private closeSubscription(): void {
    const subscription = this.subscription;
    this.subscription = undefined;
    // Local cancellation must complete even when an adapter's close throws.
    try { subscription?.close(); } catch { /* manager has already invalidated its handler */ }
  }
  private rejectPending(error: Error): void {
    for (const pending of this.pending.values()) { clearTimeout(pending.timer); pending.reject(error); }
    this.pending.clear();
  }
  private nextId(): string {
    if (this.counter >= 0xffffffff) throw new Error("NIP-46 session request counter exhausted");
    const suffix = this.randomId?.();
    if (suffix !== undefined && !/^[A-Za-z0-9_-]{1,40}$/u.test(suffix)) throw new Error("NIP-46 request ID suffix invalid");
    return `${this.namespace}:${++this.counter}${suffix === undefined ? "" : `:${suffix}`}`;
  }
  private sendRequest(method: string, params: string[], id = this.nextId()): Promise<Nip46ResponseMessage> {
    if (this.phaseValue === "session_closed") return Promise.reject(new Error("NIP-46 session is closed"));
    if (this.pending.size >= this.maxPendingRequests) return Promise.reject(new Error("NIP-46 pending request limit exceeded"));
    if (this.publishing >= this.maxPendingRequests) return Promise.reject(new Error("NIP-46 unsettled publish limit exceeded"));
    const message = JSON.stringify({ id, method, params });
    parseStrictJson(message, NSEALR_V0_LIMITS.max_nip46_decrypted_message_json_bytes);
    const event = buildNip46RequestEvent(this.secretKey, this.remoteSignerPubkey, message, this.now());
    const response = new Promise<Nip46ResponseMessage>((resolve, reject) => {
      const timer = setTimeout(() => this.failRequest(id, new Error(`NIP-46 request "${method}" timed out`)), this.requestTimeoutMs);
      timer.unref?.();
      this.pending.set(id, { resolve, reject, timer, published: false });
    });
    // Keep the adapter operation bounded even after logical timeout. A request
    // completes only after both publication and its authenticated response; the
    // timer and close still reject promptly if either operation never settles.
    ++this.publishing;
    void Promise.resolve().then(() => {
      if (this.pending.has(id)) return this.transport.publish(event);
    }).then(() => {
      --this.publishing;
      const pending = this.pending.get(id);
      if (pending) { pending.published = true; this.completeRequest(id); }
    }, error => {
      --this.publishing;
      this.failRequest(id, asError(error));
    });
    return response;
  }
  private completeRequest(id: string): void {
    const pending = this.pending.get(id);
    if (!pending?.published || pending.message === undefined) return;
    this.pending.delete(id);
    clearTimeout(pending.timer);
    pending.resolve(pending.message);
  }
  private failRequest(id: string, error: Error): void {
    const pending = this.pending.get(id);
    if (!pending) return;
    this.pending.delete(id);
    clearTimeout(pending.timer);
    pending.reject(error);
  }
  private handleEvent(event: RelayEvent): void {
    if (event.pubkey !== this.remoteSignerPubkey) return;
    let raw: unknown;
    try { raw = parseStrictJson(decryptNip46Event(this.secretKey, event), NSEALR_V0_LIMITS.max_nip46_decrypted_message_json_bytes); }
    catch { return; }
    const id = typeof raw === "object" && raw !== null ? (raw as { id?: unknown }).id : undefined;
    if (typeof id !== "string") return;
    const pending = this.pending.get(id);
    if (!pending || pending.message !== undefined) return;
    try { pending.message = requireResponseMessage(raw); this.completeRequest(id); }
    catch (error) { this.failRequest(id, asError(error)); }
  }
}
