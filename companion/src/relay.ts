import { finalizeEvent, generateSecretKey, getPublicKey } from 'nostr-tools/pure';
import { v2 as nip44 } from 'nostr-tools/nip44';
import { schnorr } from '@noble/curves/secp256k1.js';
import { hexToBytes } from '@noble/hashes/utils.js';
import { Owner } from './owner.ts';
import type { Result } from './owner.ts';
import { eventId, methods, object, parseJSON, publicKey, text } from './protocol.ts';
import type { Method, SignedEvent } from './protocol.ts';

export function relayURL(input: string): string {
  const url = new URL(input);
  if (url.protocol !== 'wss:' || url.username || url.password || url.hash) throw Error('Use a secure wss:// relay URL.');
  return url.href;
}

function transportEvent(input: unknown, recipient: string): SignedEvent {
  const row = object(input);
  if (Object.keys(row).length !== 7 || row.kind !== 24133 || !Number.isSafeInteger(row.created_at) ||
      Math.abs(Date.now() / 1000 - Number(row.created_at)) > 300 ||
      JSON.stringify(row.tags) !== JSON.stringify([['p', recipient]])) throw Error('Invalid remote signer event.');
  const event = { pubkey: publicKey(row.pubkey), kind: 24133, created_at: Number(row.created_at),
    tags: [['p', recipient]], content: text(row.content, 100000) };
  const id = eventId(event);
  if (row.id !== id || typeof row.sig !== 'string' || !/^[0-9a-f]{128}$/.test(row.sig) ||
      !schnorr.verify(hexToBytes(row.sig), hexToBytes(id), hexToBytes(event.pubkey))) throw Error('Remote signer event verification failed.');
  return { ...event, id, sig: row.sig };
}

type Approval = (origin: string, method: Method | 'connect', detail: string) => Promise<boolean>;

// Only this disposable relay key lives on the computer. Identity operations use Owner.
export class RemoteSigner {
  private secret = generateSecretKey();
  readonly transportKey = getPublicKey(this.secret);
  private token: string = crypto.randomUUID();
  private socket: WebSocket | null = null;
  private peer: string | null = null;
  private seen = new Set<string>();
  private closed = false;
  private busy = false;
  private operations = Promise.resolve();
  private queued = 0;
  private opening: Promise<void> | null = null;
  private acknowledgements = new Map<string, { resolve: () => void; reject: (error: Error) => void; timer: ReturnType<typeof setTimeout> }>();
  readonly relay: string;
  private owner: Owner;
  private approve: Approval;
  private status: (message: string) => void;
  constructor(relay: string, owner: Owner, approve: Approval, status: (message: string) => void) {
    this.relay = relayURL(relay); this.owner = owner; this.approve = approve; this.status = status;
  }
  get bunker() { return `bunker://${this.transportKey}?relay=${encodeURIComponent(this.relay)}&secret=${this.token}`; }
  get client() { return this.peer; }
  async open() {
    if (this.closed) throw Error('Remote signer session is closed.');
    if (this.opening) return this.opening;
    this.opening = new Promise<void>((resolve, reject) => {
      const socket = new WebSocket(this.relay); this.socket = socket;
      const timeout = setTimeout(() => { reject(Error('Relay connection timed out.')); this.close(); }, 15000);
      socket.onopen = () => {
        clearTimeout(timeout);
        socket.send(JSON.stringify(['REQ', 'nsealr', { kinds: [24133], '#p': [this.transportKey], since: Math.floor(Date.now() / 1000) - 5 }]));
        this.status('Relay connected. Pair your client.'); resolve();
      };
      socket.onerror = () => { clearTimeout(timeout); reject(Error('Relay connection failed.')); this.status('Relay connection failed.'); };
      socket.onclose = () => { clearTimeout(timeout); reject(Error('Relay disconnected.')); this.close(); };
      socket.onmessage = event => { void this.receive(event.data).catch(error => this.status(error.message)); };
    });
    return this.opening;
  }
  private async publish(event: SignedEvent): Promise<void> {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) throw Error('Relay is disconnected.');
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.acknowledgements.delete(event.id); reject(Error('Relay did not accept the response.')); }, 15000);
      this.acknowledgements.set(event.id, { resolve, reject, timer });
      this.socket!.send(JSON.stringify(['EVENT', event]));
    });
  }
  private async reply(peer: string, id: string, result?: string, error?: string) {
    if (this.closed) return;
    const key = nip44.utils.getConversationKey(this.secret, peer);
    try {
      const content = nip44.encrypt(JSON.stringify(error === undefined ? { id, result } : { id, error }), key);
      const event = finalizeEvent({ kind: 24133, created_at: Math.floor(Date.now() / 1000), tags: [['p', peer]], content }, this.secret);
      await this.publish(event);
    } finally { key.fill(0); }
  }
  private async receive(raw: unknown) {
    if (this.closed || typeof raw !== 'string' || raw.length > 150000) return;
    const packet = parseJSON(raw, 150000);
    if (!Array.isArray(packet)) return;
    if (packet[0] === 'OK' && typeof packet[1] === 'string') {
      const pending = this.acknowledgements.get(packet[1]);
      if (pending) {
        this.acknowledgements.delete(packet[1]); clearTimeout(pending.timer);
        if (packet[2] === true) pending.resolve(); else pending.reject(Error('Relay rejected the response.'));
      }
      return;
    }
    if (packet[0] === 'AUTH') { this.status('This relay requires authentication. Choose a relay that accepts the session key.'); return; }
    if (packet[0] === 'CLOSED' || packet[0] === 'NOTICE') { this.status('The relay rejected or closed this subscription.'); return; }
    if (packet[0] !== 'EVENT' || packet[1] !== 'nsealr') return;
    const event = transportEvent(packet[2], this.transportKey);
    if (this.peer && event.pubkey !== this.peer) return;
    const conversation = nip44.utils.getConversationKey(this.secret, event.pubkey);
    let message: Record<string, unknown>;
    try { message = object(parseJSON(nip44.decrypt(event.content, conversation))); }
    finally { conversation.fill(0); }
    const id = text(message.id, 128);
    if (!id || typeof message.method !== 'string' || !Array.isArray(message.params) || message.params.length > 4 ||
        message.params.some(value => typeof value !== 'string') || Object.keys(message).length !== 3) throw Error('Invalid NIP-46 request.');
    const params = message.params as string[], method = message.method;
    if (!this.peer && (method !== 'connect' || params[0] !== this.transportKey || !this.token || params[1] !== this.token)) return;
    const seenKey = `${event.pubkey}:${id}`;
    if (this.seen.has(seenKey)) return;
    if (this.seen.size >= 512) { this.close(); throw Error('Start a new remote session to continue.'); }
    this.seen.add(seenKey);
    const origin = `NIP-46 ${event.pubkey}`;
    const generation = this.owner.generation;
    let releaseQueue = () => {};
    let queued = false;
    if (method === 'connect' || (event.pubkey === this.peer && methods.includes(method as Method))) {
      if (this.queued >= 4) { await this.reply(event.pubkey, id, undefined, 'The device request queue is full.'); return; }
      const previous = this.operations;
      this.operations = new Promise<void>(resolve => { releaseQueue = resolve; });
      this.queued++; queued = true; await previous;
    }
    let acquired = false;
    try {
      if (this.closed) return;
      if (generation !== this.owner.generation) throw Error('Queued request cancelled with the previous operation.');
      if (event.pubkey === this.peer && method === 'ping' && !params.length) { await this.reply(event.pubkey, id, 'pong'); return; }
      if (event.pubkey === this.peer && method === 'switch_relays' && !params.length) { await this.reply(event.pubkey, id, 'null'); return; }
      if (event.pubkey === this.peer && method === 'logout' && !params.length) { await this.reply(event.pubkey, id, 'ack'); this.close(); return; }
      if (this.busy) throw Error('Another device request is already open.');
      if (method === 'connect') {
        if (this.peer || params[0] !== this.transportKey || !this.token || params[1] !== this.token) throw Error('Invalid or already used pairing token.');
        this.busy = true; acquired = true;
        if (!await this.approve(origin, 'connect', 'Pair this client for this session. Every identity operation still needs your device.')) throw Error('Pairing rejected.');
        if (this.closed) return;
        this.peer = event.pubkey; this.token = '';
        await this.reply(event.pubkey, id, 'ack'); this.status('Client paired. Keep this companion open.'); return;
      }
      if (event.pubkey !== this.peer) throw Error('Pair this client first.');
      if (!methods.includes(method as Method)) throw Error('Unsupported signer method.');
      this.busy = true; acquired = true;
      if (!this.owner.grants.get(origin)?.has(method as Method)) {
        if (!await this.approve(origin, method as Method, 'Allow this method for this connection. The device asks you for every operation.')) { this.owner.revoke(origin); throw Error('Permission rejected.'); }
        if (this.closed) return;
        this.owner.grant(origin, method as Method);
      }
      const result: Result = await this.owner.start(origin, method as Method, params);
      await this.reply(event.pubkey, id, typeof result === 'string' ? result : JSON.stringify(result));
    } catch (error) {
      await this.reply(event.pubkey, id, undefined, error instanceof Error ? error.message : 'Request failed.');
    } finally { if (acquired) this.busy = false; if (queued) { this.queued--; releaseQueue(); } }
  }
  async acceptClient(uri: string) {
    const parsed = new URL(uri);
    if (parsed.protocol !== 'nostrconnect:') throw Error('Use a nostrconnect:// pairing link.');
    const peer = publicKey(parsed.hostname), secret = text(parsed.searchParams.get('secret'), 128);
    if (!secret || parsed.searchParams.getAll('relay').map(relayURL).indexOf(this.relay) < 0) throw Error('Pairing link must include this relay and a secret.');
    if (this.peer || this.closed || this.busy) throw Error('This session is already paired, busy or closed.');
    this.busy = true;
    let releaseQueue = () => {};
    this.operations = new Promise<void>(resolve => { releaseQueue = resolve; });
    try {
      if (!await this.approve(`NIP-46 ${peer}`, 'connect', 'Pair this client for this session. Client names and URLs do not establish identity.')) throw Error('Pairing rejected.');
      if (this.closed) throw Error('Remote session closed.');
      await this.open(); this.peer = peer; this.token = '';
      await this.reply(peer, crypto.randomUUID(), secret); this.status('Client paired. Keep this companion open.');
    } finally { this.busy = false; releaseQueue(); }
  }
  close() {
    if (this.closed) return;
    this.closed = true; this.socket?.close(); this.secret.fill(0); this.token = '';
    for (const pending of this.acknowledgements.values()) { clearTimeout(pending.timer); pending.reject(Error('Remote session closed.')); }
    this.acknowledgements.clear(); this.seen.clear();
    if (this.peer) this.owner.revoke(`NIP-46 ${this.peer}`);
    this.status('Remote session disconnected.');
  }
}

export async function publishNote(event: SignedEvent, relay: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(relayURL(relay));
    const finish = (error?: Error) => { clearTimeout(timer); socket.close(); error ? reject(error) : resolve(); };
    const timer = setTimeout(() => finish(Error('The relay did not acknowledge this event.')), 15000);
    socket.onopen = () => socket.send(JSON.stringify(['EVENT', event]));
    socket.onerror = () => finish(Error('Relay connection failed.'));
    socket.onmessage = packet => {
      try {
        const row = parseJSON(packet.data);
        if (Array.isArray(row) && row[0] === 'OK' && row[1] === event.id) finish(row[2] === true ? undefined : Error('The relay rejected this event.'));
      } catch { finish(Error('Invalid relay response.')); }
    };
  });
}
