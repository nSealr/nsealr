import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { schnorr } from '@noble/curves/secp256k1.js';
import { bytesToHex } from '@noble/hashes/utils.js';
import { finalizeEvent, getPublicKey } from 'nostr-tools/pure';
import { v2 as nip44 } from 'nostr-tools/nip44';
import { Ceremony, groupRecord } from '../src/threshold.ts';
import { request } from '../src/protocol.ts';

// Coordinator tests use public transport keys and opaque encrypted payloads.
// They do not implement or simulate FROST's share arithmetic.
const secrets = [3, 4, 5].map(value => { const key = new Uint8Array(32); key[31] = value; return key; });
const keys = secrets.map(getPublicKey).sort();
const secretFor = (key: string) => secrets.find(secret => getPublicKey(secret) === key)!;
const groupSecret = new Uint8Array(32); groupSecret[31] = 7;
const group = { group: '66'.repeat(32), pubkey: getPublicKey(groupSecret), members: keys };
function packet(c: Ceremony, sender: string, recipient: string, changes: Record<string, string> = {}): string {
  const content = nip44.encrypt('Opaque test packet, not a FROST share', nip44.utils.getConversationKey(secretFor(sender), recipient));
  const row = { type: 'nsealr_peer', phase: c.phase, group: c.fingerprint, session: c.session, sender, recipient, content, ...changes };
  const digest = createHash('sha256').update(JSON.stringify(['nSealr threshold peer', row.phase, row.group, row.session, row.sender, row.recipient, row.content])).digest();
  return JSON.stringify({ ...row, sig: bytesToHex(schnorr.sign(digest, secretFor(sender))) });
}
function collect(c: Ceremony) { for (const sender of c.members) for (const recipient of c.members) if (sender !== recipient) c.ingest(packet(c, sender, recipient)); }
function deliver(c: Ceremony) { while (c.delivering) c.delivered(); }

test('threshold setup enforces signed roster/session packets, all-output barriers and three matching group records', () => {
  const c = new Ceremony();
  for (const key of keys) c.ingest(JSON.stringify({ type: 'nsealr_join', key }));
  const start = c.current!.raw;
  assert.equal(c.fingerprint, createHash('sha256').update(JSON.stringify(['nSealr 2-of-3 setup', c.session, keys])).digest('hex'));
  const first = packet(c, keys[0], keys[1]); c.ingest(first); c.ingest(first); assert.equal(c.count, 1); assert.equal(c.current!.raw, start);
  assert.throws(() => c.delivered(), /no packet/);
  assert.throws(() => c.ingest(packet(c, keys[0], keys[1])), /Conflicting/);
  assert.throws(() => c.ingest(packet(c, keys[1], keys[0], { session: '77'.repeat(32) })), /session/);
  const tampered = JSON.parse(packet(c, keys[1], keys[0])); tampered.content += 'x'; assert.throws(() => c.ingest(JSON.stringify(tampered)), /signature/);
  for (const sender of keys) for (const recipient of keys) if (sender !== recipient && !(sender === keys[0] && recipient === keys[1])) c.ingest(packet(c, sender, recipient));
  assert.equal(c.delivering, true); assert.equal(c.current!.recipient, keys[0]);
  assert.throws(() => c.ingest(packet(c, keys[1], keys[0])), /Finish routing/);
  const forwarded = []; while (c.delivering) { forwarded.push(c.current!.raw); c.delivered(); }
  assert.ok(forwarded.includes(first)); assert.equal(new Set(forwarded).size, 6);
  assert.equal(c.phase, 'setup2'); collect(c); deliver(c); assert.equal(c.phase, 'groups');
  const record = (participant: number, pubkey = group.pubkey) => JSON.stringify({ type: 'nsealr_group', ...group, pubkey, participant });
  c.ingest(record(1)); c.ingest(record(1)); assert.equal(c.count, 1);
  assert.throws(() => c.ingest(record(2, keys[0])), /different group/);
  c.ingest(record(2)); c.ingest(record(3)); assert.equal(c.phase, 'complete'); assert.deepEqual(c.group, group);
  assert.throws(() => groupRecord(JSON.stringify({ ...JSON.parse(record(1)), private_share: 'never accepted' })), /fields/);
});

test('threshold signing requires both authenticated phases before the exact original result and rejects stale or changed events', () => {
  const pending = request('sign_event', [{ kind: 1, created_at: 1710000000, tags: [], content: 'Exact group note' }], group.pubkey);
  assert.throws(() => new Ceremony(group, [keys[0], keys[0]], pending), /unique/);
  assert.throws(() => new Ceremony(group, [keys[0], group.pubkey].sort(), pending), /group/);
  const c = new Ceremony(group, keys.slice(0, 2), pending);
  const payload = JSON.parse(c.current!.raw); assert.equal(payload.id, pending.id); assert.equal(payload.event, pending.params[0]);
  const event = finalizeEvent(JSON.parse(pending.params[0]), groupSecret);
  const result = JSON.stringify({ id: pending.id, result: JSON.stringify(event) });
  assert.throws(() => c.ingest(result), /fields/);
  collect(c); deliver(c); assert.equal(c.phase, 'share'); collect(c); deliver(c); assert.equal(c.phase, 'result');
  assert.throws(() => c.ingest(JSON.stringify({ id: 'different-request', result: JSON.stringify(event) })), /different request/);
  const changed = finalizeEvent({ ...JSON.parse(pending.params[0]), content: 'Changed' }, groupSecret);
  assert.throws(() => c.ingest(JSON.stringify({ id: pending.id, result: JSON.stringify(changed) })), /changed/);
  c.ingest(result); assert.equal(c.phase, 'complete'); assert.equal(c.result!.id, event.id); assert.equal(c.resultWire, result);
  const cancelled = new Ceremony(group, keys.slice(0, 2), pending); cancelled.cancel(); assert.throws(() => cancelled.ingest(result), /ended/);
  const expired = new Ceremony(group, keys.slice(0, 2), pending), clock = Date.now;
  try { Date.now = () => expired.deadline; assert.throws(() => expired.ingest(result), /ended/); }
  finally { Date.now = clock; }
});
