import { schnorr } from '@noble/curves/secp256k1.js';
import { sha256 } from '@noble/hashes/sha2.js';
import { bytesToHex, hexToBytes } from '@noble/hashes/utils.js';
import { object, parseJSON, publicKey, response, text } from './protocol.ts';
import type { Request, SignedEvent } from './protocol.ts';

export type Member = { id: number; key: string };
export type Group = { group: string; pubkey: string; descriptor: string; members: Member[] };
type Peer = { type: 'nsealr_peer'; phase: string; group: string; session: string; sender: string; recipient: string; content: string; sig: string };
type Phase = 'joins' | 'setup1' | 'setup2' | 'groups' | 'commitment' | 'share' | 'result' | 'repair_delta' | 'repair_sigma' | 'repair_ready' | 'complete';
type Start = { group: Group; selected: string[]; request: Request } | { group: Group; lost: number };
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
  const row = object(parseJSON(raw)); exact(row, ['type', 'group', 'pubkey', 'descriptor', 'members', 'participant']);
  if (row.type !== 'nsealr_group' || !Number.isInteger(row.participant) || Number(row.participant) < 1 || Number(row.participant) > 3) throw Error('Scan a public group record from a participant device.');
  if (!Array.isArray(row.members) || row.members.length !== 3) throw Error('Wrong participant count.');
  const roster = row.members.map((value, index) => {
    const member = object(value); exact(member, ['id', 'key']);
    if (member.id !== index + 1) throw Error('Member numbers must remain in order, from 1 to 3.');
    return { id: index + 1, key: publicKey(member.key) };
  });
  if (new Set(roster.map(member => member.key)).size !== 3) throw Error('Participant keys must be unique.');
  const pubkey = publicKey(row.pubkey);
  // Two signers, three members, then the compressed public key and public shares.
  if (typeof row.descriptor !== 'string' || !/^02030[23][a-f0-9]{454}$/.test(row.descriptor) || row.descriptor.slice(6, 70) !== pubkey) throw Error('Invalid public group descriptor.');
  return { group: hex(row.group), pubkey, descriptor: row.descriptor, members: roster, participant: Number(row.participant) };
}
export function setupFingerprint(session: string, keys: string[]): string {
  return bytesToHex(digest(['nSealr 2-of-3 setup', session, keys]));
}
function peerRecord(raw: string): Peer {
  const row = object(parseJSON(raw)); exact(row, ['type', 'phase', 'group', 'session', 'sender', 'recipient', 'content', 'sig']);
  if (row.type !== 'nsealr_peer' || typeof row.phase !== 'string' || !['setup1', 'setup2', 'commitment', 'share', 'repair_delta', 'repair_sigma', 'repair_ready'].includes(row.phase)) throw Error('Unsupported ceremony packet.');
  const peer = { type: 'nsealr_peer' as const, phase: row.phase, group: hex(row.group), session: hex(row.session), sender: publicKey(row.sender), recipient: publicKey(row.recipient), content: text(row.content), sig: text(row.sig, 128) };
  if (!/^[a-f0-9]{128}$/.test(peer.sig) || !schnorr.verify(hexToBytes(peer.sig), digest(['nSealr threshold peer', peer.phase, peer.group, peer.session, peer.sender, peer.recipient, peer.content]), hexToBytes(peer.sender))) throw Error('The participant packet signature is invalid.');
  return peer;
}

// The coordinator routes authenticated opaque packets. Only devices decrypt shares.
export class Ceremony {
  readonly session = bytesToHex(crypto.getRandomValues(new Uint8Array(32)));
  readonly deadline: number;
  readonly mode: 'setup' | 'sign' | 'repair';
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
  private source: Group | null;
  readonly lost: number | null;
  private replacement = '';
  constructor(start?: Start) {
    this.mode = !start ? 'setup' : 'lost' in start ? 'repair' : 'sign'; this.phase = this.mode === 'sign' ? 'commitment' : 'joins';
    this.source = start ? structuredClone(start.group) : null;
    this.group = this.mode === 'sign' ? this.source : null;
    this.request = start && 'request' in start ? start.request : null;
    this.lost = start && 'lost' in start ? start.lost : null;
    this.deadline = Date.now() + (this.mode === 'sign' ? 5 : 10) * 60_000;
    if (start && 'selected' in start) {
      this.members = members(start.selected, 2);
      if (this.members.some(key => !start.group.members.some(member => member.key === key)) || start.request.method !== 'sign_event' || JSON.parse(start.request.params[0]).pubkey !== start.group.pubkey) throw Error('The selected signing group does not match this exact event.');
    }
    if (this.mode === 'repair' && (!Number.isInteger(this.lost) || this.lost! < 1 || this.lost! > 3)) throw Error('Choose the lost member, from 1 to 3.');
  }
  get expected(): number { return this.mode === 'repair' ? 2 : this.members.length * (this.members.length - 1); }
  get count(): number { return this.phase === 'joins' ? this.members.length : this.phase === 'groups' ? this.records.size : this.packets.size; }
  get fingerprint(): string {
    if (this.mode === 'repair') return bytesToHex(digest(['nSealr 2-of-3 repair', this.session, this.source!.group, this.lost, this.replacement]));
    return this.mode === 'setup' ? setupFingerprint(this.session, this.members) : this.group!.group;
  }
  memberNumber(key: string): number { return this.mode === 'sign' ? this.source!.members.find(member => member.key === key)!.id : this.members.indexOf(key) + 1; }
  get current(): { raw: string; recipient: string | null } | null {
    if (this.delivering) {
      const packet = this.ordered()[this.delivery]; return { raw: packet.raw, recipient: packet.peer.recipient };
    }
    if (this.phase === 'setup1') return { raw: JSON.stringify({ type: 'nsealr_setup', session: this.session, members: this.members }), recipient: null };
    if (this.phase === 'commitment') return { raw: JSON.stringify({ type: 'nsealr_sign', id: this.request!.id, session: this.session, members: this.members, event: this.request!.params[0] }), recipient: null };
    if (this.phase === 'repair_delta') return { raw: JSON.stringify({ type: 'nsealr_repair', session: this.session, group: this.source!.group, descriptor: this.source!.descriptor, members: this.source!.members, participant: this.lost, replacement: this.replacement }), recipient: null };
    return null;
  }
  get deliveryNumber(): number { return this.delivery + 1; }
  private ordered() { return [...this.packets.values()].sort((a, b) => a.peer.recipient.localeCompare(b.peer.recipient) || a.peer.sender.localeCompare(b.peer.sender)); }
  private check() { if (Date.now() >= this.deadline || this.phase === 'complete') throw Error(this.mode === 'repair' ? 'This repair has ended. Compare the devices’ public group records before starting again.' : 'This ceremony has ended. Start a fresh ceremony on every participating device.'); }
  ingest(raw: string) {
    this.check(); text(raw);
    if (this.delivering) throw Error('Finish routing this phase before collecting the next outputs.');
    if (this.phase === 'joins') {
      const row = object(parseJSON(raw)); exact(row, ['type', 'key']);
      if (row.type !== 'nsealr_join') throw Error('Scan a public threshold join code from the device.');
      const key = publicKey(row.key); if (this.members.includes(key)) return;
      if (this.mode === 'repair') {
        if (this.source!.members.some(member => member.key === key)) throw Error('The replacement must use a fresh transport key.');
        this.replacement = key; this.members = this.source!.members.map(member => member.id === this.lost ? key : member.key);
        this.phase = 'repair_delta'; return;
      }
      this.members.push(key); this.members.sort(); if (this.members.length === 3) this.phase = 'setup1'; return;
    }
    if (this.phase === 'groups') {
      const record = groupRecord(raw);
      if (JSON.stringify(record.members.map(member => member.key)) !== JSON.stringify(this.members)) throw Error('The group roster changed.');
      if (this.mode === 'repair' && (record.pubkey !== this.source!.pubkey || record.descriptor !== this.source!.descriptor || record.group === this.source!.group)) throw Error('Repair must preserve the identity and descriptor with a new roster fingerprint.');
      if (this.group && (this.group.group !== record.group || this.group.pubkey !== record.pubkey || this.group.descriptor !== record.descriptor)) throw Error('Participant devices returned different group identities.');
      this.group = { group: record.group, pubkey: record.pubkey, descriptor: record.descriptor, members: record.members };
      this.records.add(record.participant); if (this.records.size === 3) this.phase = 'complete'; return;
    }
    if (this.phase === 'result') {
      const result = response(raw, this.request!, this.group!.pubkey);
      if (typeof result === 'string') throw Error('The device did not return a signed event.');
      this.result = result; this.resultWire = raw; this.phase = 'complete'; return;
    }
    const peer = peerRecord(raw);
    if (peer.phase !== this.phase || peer.session !== this.session || peer.group !== this.fingerprint || peer.sender === peer.recipient || !this.members.includes(peer.sender) || !this.members.includes(peer.recipient)) throw Error('Packet phase, session or participant does not match this ceremony.');
    if (this.mode === 'repair') {
      const senderIsReplacement = peer.sender === this.replacement, recipientIsReplacement = peer.recipient === this.replacement;
      if ((this.phase === 'repair_delta' && (senderIsReplacement || recipientIsReplacement)) ||
          (this.phase === 'repair_sigma' && (senderIsReplacement || !recipientIsReplacement)) ||
          (this.phase === 'repair_ready' && (!senderIsReplacement || recipientIsReplacement))) throw Error('The repair packet does not follow the helper and replacement roles.');
    }
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
      this.phase = ({ setup1: 'setup2', setup2: 'groups', commitment: 'share', share: 'result', repair_delta: 'repair_sigma', repair_sigma: 'repair_ready', repair_ready: 'groups' } as Record<string, Phase>)[this.phase];
    }
  }
  cancel() { this.packets.clear(); this.records.clear(); this.members = []; this.result = null; this.resultWire = ''; this.phase = 'complete'; }
}
