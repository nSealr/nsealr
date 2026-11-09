import { schnorr } from '@noble/curves/secp256k1.js';
import { sha256 } from '@noble/hashes/sha2.js';
import { bytesToHex, hexToBytes } from '@noble/hashes/utils.js';
import { object, parseJSON, publicKey, response, text } from './protocol.ts';
import type { Request, SignedEvent } from './protocol.ts';

export type Group = { group: string; pubkey: string; members: string[] };
type Peer = { type: 'nsealr_peer'; phase: string; group: string; session: string; sender: string; recipient: string; content: string; sig: string };
type Phase = 'joins' | 'setup1' | 'setup2' | 'groups' | 'commitment' | 'share' | 'result' | 'complete';
const digest = (value: unknown) => sha256(new TextEncoder().encode(JSON.stringify(value)));
const hex = (value: unknown) => { if (typeof value !== 'string' || !/^[a-f0-9]{64}$/.test(value)) throw Error('Invalid ceremony identifier.'); return value; };
const exact = (row: Record<string, unknown>, keys: string[]) => { if (Object.keys(row).length !== keys.length || keys.some(key => !Object.hasOwn(row, key))) throw Error('Unexpected ceremony fields.'); };
function members(value: unknown, count: number): string[] {
  if (!Array.isArray(value) || value.length !== count) throw Error('Wrong participant count.');
  const keys = value.map(publicKey);
  if (keys.some((key, index) => index > 0 && keys[index - 1] >= key)) throw Error('Participant keys must be unique and sorted.');
  return keys;
}
export function groupRecord(raw: string): Group & { participant: number } {
  const row = object(parseJSON(raw)); exact(row, ['type', 'group', 'pubkey', 'members', 'participant']);
  if (row.type !== 'nsealr_group' || !Number.isInteger(row.participant) || Number(row.participant) < 1 || Number(row.participant) > 3) throw Error('Scan a public group record from a participant device.');
  return { group: hex(row.group), pubkey: publicKey(row.pubkey), members: members(row.members, 3), participant: Number(row.participant) };
}
export function setupFingerprint(session: string, keys: string[]): string {
  return bytesToHex(digest(['nSealr 2-of-3 setup', session, keys]));
}
function peerRecord(raw: string): Peer {
  const row = object(parseJSON(raw)); exact(row, ['type', 'phase', 'group', 'session', 'sender', 'recipient', 'content', 'sig']);
  if (row.type !== 'nsealr_peer' || typeof row.phase !== 'string' || !['setup1', 'setup2', 'commitment', 'share'].includes(row.phase)) throw Error('Unsupported ceremony packet.');
  const peer = { type: 'nsealr_peer' as const, phase: row.phase, group: hex(row.group), session: hex(row.session), sender: publicKey(row.sender), recipient: publicKey(row.recipient), content: text(row.content), sig: text(row.sig, 128) };
  if (!/^[a-f0-9]{128}$/.test(peer.sig) || !schnorr.verify(hexToBytes(peer.sig), digest(['nSealr threshold peer', peer.phase, peer.group, peer.session, peer.sender, peer.recipient, peer.content]), hexToBytes(peer.sender))) throw Error('The participant packet signature is invalid.');
  return peer;
}

// The coordinator routes authenticated opaque packets. Only devices decrypt shares.
export class Ceremony {
  readonly session = bytesToHex(crypto.getRandomValues(new Uint8Array(32)));
  readonly deadline: number;
  readonly mode: 'setup' | 'sign';
  phase: Phase;
  delivering = false;
  members: string[] = [];
  group: Group | null;
  result: SignedEvent | null = null;
  resultWire = '';
  private packets = new Map<string, { raw: string; peer: Peer }>();
  private delivery = 0;
  private records = new Set<number>();
  private request: Request | null;
  constructor(group?: Group, selected?: string[], request?: Request) {
    this.mode = group ? 'sign' : 'setup'; this.phase = group ? 'commitment' : 'joins';
    this.group = group ? { ...group, members: [...group.members] } : null; this.request = request ?? null;
    this.deadline = Date.now() + (group ? 5 : 10) * 60_000;
    if (group) {
      this.members = members(selected, 2);
      if (this.members.some(key => !group.members.includes(key)) || request?.method !== 'sign_event' || JSON.parse(request.params[0]).pubkey !== group.pubkey) throw Error('The selected signing group does not match this exact event.');
    }
  }
  get expected(): number { return this.members.length * (this.members.length - 1); }
  get count(): number { return this.phase === 'joins' ? this.members.length : this.phase === 'groups' ? this.records.size : this.packets.size; }
  get fingerprint(): string { return this.mode === 'setup' ? setupFingerprint(this.session, this.members) : this.group!.group; }
  get current(): { raw: string; recipient: string | null } | null {
    if (this.delivering) {
      const packet = this.ordered()[this.delivery]; return { raw: packet.raw, recipient: packet.peer.recipient };
    }
    if (this.phase === 'setup1') return { raw: JSON.stringify({ type: 'nsealr_setup', session: this.session, members: this.members }), recipient: null };
    if (this.phase === 'commitment') return { raw: JSON.stringify({ type: 'nsealr_sign', id: this.request!.id, session: this.session, members: this.members, event: this.request!.params[0] }), recipient: null };
    return null;
  }
  get deliveryNumber(): number { return this.delivery + 1; }
  private ordered() { return [...this.packets.values()].sort((a, b) => a.peer.recipient.localeCompare(b.peer.recipient) || a.peer.sender.localeCompare(b.peer.sender)); }
  private check() { if (Date.now() >= this.deadline || this.phase === 'complete') throw Error('This ceremony has ended. Start a fresh ceremony on every participating device.'); }
  ingest(raw: string) {
    this.check(); text(raw);
    if (this.delivering) throw Error('Finish routing this phase before collecting the next outputs.');
    if (this.phase === 'joins') {
      const row = object(parseJSON(raw)); exact(row, ['type', 'key']);
      if (row.type !== 'nsealr_join') throw Error('Scan a threshold join code from each of three devices.');
      const key = publicKey(row.key); if (this.members.includes(key)) return;
      this.members.push(key); this.members.sort(); if (this.members.length === 3) this.phase = 'setup1'; return;
    }
    if (this.phase === 'groups') {
      const record = groupRecord(raw);
      if (JSON.stringify(record.members) !== JSON.stringify(this.members)) throw Error('The group roster changed.');
      if (this.group && (this.group.group !== record.group || this.group.pubkey !== record.pubkey)) throw Error('Participant devices returned different group identities.');
      this.group = { group: record.group, pubkey: record.pubkey, members: [...record.members] };
      this.records.add(record.participant); if (this.records.size === 3) this.phase = 'complete'; return;
    }
    if (this.phase === 'result') {
      const result = response(raw, this.request!, this.group!.pubkey);
      if (typeof result === 'string') throw Error('The device did not return a signed event.');
      this.result = result; this.resultWire = raw; this.phase = 'complete'; return;
    }
    const peer = peerRecord(raw);
    if (peer.phase !== this.phase || peer.session !== this.session || peer.group !== this.fingerprint || peer.sender === peer.recipient || !this.members.includes(peer.sender) || !this.members.includes(peer.recipient)) throw Error('Packet phase, session or participant does not match this ceremony.');
    const key = `${peer.sender}:${peer.recipient}`;
    if (this.packets.has(key)) { if (this.packets.get(key)!.raw !== raw) throw Error('Conflicting participant packet.'); return; }
    this.packets.set(key, { raw, peer });
    if (this.packets.size === this.expected) { this.delivering = true; this.delivery = 0; }
  }
  delivered() {
    this.check(); if (!this.delivering) throw Error('There is no packet ready to route.');
    this.delivery++;
    if (this.delivery === this.expected) {
      this.delivering = false; this.delivery = 0; this.packets.clear();
      this.phase = ({ setup1: 'setup2', setup2: 'groups', commitment: 'share', share: 'result' } as Record<string, Phase>)[this.phase];
    }
  }
  cancel() { this.packets.clear(); this.records.clear(); this.members = []; this.result = null; this.resultWire = ''; this.phase = 'complete'; }
}
