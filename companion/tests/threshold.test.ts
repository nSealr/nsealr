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
const secrets = [3, 4, 5, 6].map(value => { const key = new Uint8Array(32); key[31] = value; return key; });
const keys = secrets.slice(0, 3).map(getPublicKey).sort();
const replacement = getPublicKey(secrets[3]);
const secretFor = (key: string) => secrets.find(secret => getPublicKey(secret) === key)!;
const groupSecret = new Uint8Array(32); groupSecret[31] = 7;
const groupKey = getPublicKey(groupSecret);
const descriptor = '020302' + groupKey + keys.map((key, i) => (i + 1).toString(16).padStart(64, '0') + '02' + key).join('');
const group = { group: '66'.repeat(32), pubkey: groupKey, descriptor, members: keys.map((key, i) => ({ id: i + 1, key })) };
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
  assert.throws(() => c.ingest(record(2, keys[0])), /descriptor|different group/);
  c.ingest(record(2)); c.ingest(record(3)); assert.equal(c.phase, 'complete'); assert.deepEqual(c.group, group);
  assert.throws(() => groupRecord(JSON.stringify({ ...JSON.parse(record(1)), private_share: 'never accepted' })), /fields/);
});

test('threshold signing requires both authenticated phases before the exact original result and rejects stale or changed events', () => {
  const pending = request('sign_event', [{ kind: 1, created_at: 1710000000, tags: [], content: 'Exact group note' }], group.pubkey);
  assert.throws(() => new Ceremony({ group, selected: [keys[0], keys[0]], request: pending }), /unique/);
  assert.throws(() => new Ceremony({ group, selected: [keys[0], group.pubkey].sort(), request: pending }), /group/);
  const c = new Ceremony({ group, selected: keys.slice(0, 2), request: pending });
  const payload = JSON.parse(c.current!.raw); assert.equal(payload.id, pending.id); assert.equal(payload.event, pending.params[0]);
  const event = finalizeEvent(JSON.parse(pending.params[0]), groupSecret);
  const result = JSON.stringify({ id: pending.id, result: JSON.stringify(event) });
  assert.throws(() => c.ingest(result), /fields/);
  collect(c); deliver(c); assert.equal(c.phase, 'share'); collect(c); deliver(c); assert.equal(c.phase, 'result');
  assert.throws(() => c.ingest(JSON.stringify({ id: 'different-request', result: JSON.stringify(event) })), /different request/);
  const changed = finalizeEvent({ ...JSON.parse(pending.params[0]), content: 'Changed' }, groupSecret);
  assert.throws(() => c.ingest(JSON.stringify({ id: pending.id, result: JSON.stringify(changed) })), /changed/);
  c.ingest(result); assert.equal(c.phase, 'complete'); assert.equal(c.result!.id, event.id); assert.equal(c.resultWire, result);
  const cancelled = new Ceremony({ group, selected: keys.slice(0, 2), request: pending }); cancelled.cancel(); assert.throws(() => cancelled.ingest(result), /ended/);
  const expired = new Ceremony({ group, selected: keys.slice(0, 2), request: pending }), clock = Date.now;
  try { Date.now = () => expired.deadline; assert.throws(() => expired.ingest(result), /ended/); }
  finally { Date.now = clock; }
});

test('lost-share repair binds stable member IDs, fresh replacement, exact roles, all barriers and unchanged public identity', () => {
  const c = new Ceremony({ group, lost: 1 }), helpers = keys.slice(1);
  assert.throws(() => new Ceremony({ group, lost: 4 }), /lost member/);
  assert.throws(() => c.ingest(JSON.stringify({ type: 'nsealr_join', key: keys[0] })), /fresh/);
  c.ingest(JSON.stringify({ type: 'nsealr_join', key: replacement }));
  assert.equal(c.fingerprint, createHash('sha256').update(JSON.stringify(['nSealr 2-of-3 repair', c.session, group.group, 1, replacement])).digest('hex'));
  assert.deepEqual(JSON.parse(c.current!.raw), { type: 'nsealr_repair', session: c.session, group: group.group, descriptor, members: group.members, participant: 1, replacement });
  const updated = { ...group, group: '88'.repeat(32), members: group.members.map(member => member.id === 1 ? { id: 1, key: replacement } : member) };
  const record = (participant: number, changes = {}) => JSON.stringify({ type: 'nsealr_group', ...updated, participant, ...changes });
  // The new key's lexical position must never renumber the surviving members.
  assert.notDeepEqual(updated.members.map(member => member.key), [...updated.members.map(member => member.key)].sort());
  assert.equal(c.memberNumber(replacement), 1); assert.equal(c.memberNumber(helpers[0]), 2);
  assert.throws(() => c.ingest(packet(c, replacement, helpers[0])), /roles/);
  assert.throws(() => c.ingest(packet(c, keys[0], helpers[0])), /participant/);
  assert.throws(() => c.ingest(packet(c, helpers[0], helpers[1], { group: group.group })), /session/);
  for (const [sender, recipient] of [[helpers[0], helpers[1]], [helpers[1], helpers[0]]]) c.ingest(packet(c, sender, recipient));
  assert.throws(() => c.ingest(record(1)), /Finish routing/); deliver(c); assert.equal(c.phase, 'repair_sigma');
  assert.throws(() => c.ingest(packet(c, helpers[0], helpers[1])), /roles/);
  for (const helper of helpers) c.ingest(packet(c, helper, replacement));
  deliver(c); assert.equal(c.phase, 'repair_ready');
  assert.throws(() => c.ingest(record(1)), /fields/);
  assert.throws(() => c.ingest(packet(c, helpers[0], replacement)), /roles/);
  for (const helper of helpers) c.ingest(packet(c, replacement, helper));
  c.delivered(); assert.equal(c.phase, 'repair_ready'); c.delivered(); assert.equal(c.phase, 'groups');
  assert.throws(() => c.ingest(record(1, { group: group.group })), /new roster/);
  assert.throws(() => c.ingest(record(1, { descriptor: descriptor.slice(0, -2) + '00' })), /preserve/);
  assert.throws(() => c.ingest(record(1, { members: group.members })), /roster/);
  c.ingest(record(1)); c.ingest(record(1)); assert.equal(c.count, 1);
  assert.throws(() => c.ingest(record(2, { group: '99'.repeat(32) })), /different group/);
  c.ingest(record(2)); assert.equal(c.phase, 'groups'); c.ingest(record(3)); assert.equal(c.phase, 'complete'); assert.deepEqual(c.group, updated);
  assert.throws(() => groupRecord(record(1, { members: keys })), /object/i);
  assert.throws(() => groupRecord(record(1, { members: updated.members.map(member => ({ ...member, id: 1 })) })), /numbers/);
  assert.throws(() => groupRecord(record(1, { members: updated.members.map(member => ({ ...member, key: replacement })) })), /unique/);
});
