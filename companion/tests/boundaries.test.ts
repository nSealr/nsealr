import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { finalizeEvent, getPublicKey } from 'nostr-tools/pure';
import { v2 as nip44 } from 'nostr-tools/nip44';
import { Collector, frames } from '../src/frames.ts';
import { Owner } from '../src/owner.ts';
import { canonical, eventId, identity, npub, parseJSON, request, response, signedEvent, template } from '../src/protocol.ts';

// Public deterministic test key. It is never used by the app or extension.
const key = new Uint8Array(32); key[31] = 1;
const pubkey = getPublicKey(key);
const note = { pubkey, created_at: 1710000000, kind: 1, tags: [['t', 'nostr']], content: 'Hello, café.\nExact text.' };
const sign = () => JSON.parse(JSON.stringify(finalizeEvent(structuredClone(note), key)));
const reply = (owner: Owner, result: unknown) => frames(JSON.stringify({ id: owner.operation!.request.id, result: typeof result === 'string' ? result : JSON.stringify(result) }));
function deliver(owner: Owner, chunks: string[]) { for (const chunk of chunks) owner.scan(chunk); }

test('public identity parses the published NIP19 example and round trips without secret formats', () => {
  assert.equal(identity('npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6'), '3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d');
  assert.equal(identity(npub(pubkey)), pubkey);
  assert.throws(() => identity('nsec1secret')); assert.throws(() => identity('f'.repeat(64)));
});
test('strict JSON refuses duplicates, trailing data, lone surrogates and excessive nesting', () => {
  for (const value of ['{"id":"a","id":"b"}', '{"x":1}null', '"\\ud800"', '"\\udfff"', '[1,]', '1e999', '['.repeat(18) + '0' + ']'.repeat(18)]) assert.throws(() => parseJSON(value));
  assert.equal((parseJSON('{"__proto__":"text","s":"🎵"}') as any).__proto__, 'text');
});
test('NIP07 templates gain the selected identity and reject a conflicting supplied key or ID', () => {
  const { pubkey: _, ...withoutKey } = note;
  const operation = request('sign_event', [withoutKey], pubkey);
  assert.deepEqual(JSON.parse(operation.params[0]), note);
  assert.throws(() => request('sign_event', [{ ...note, pubkey: '2'.repeat(64) }], pubkey));
  assert.throws(() => request('sign_event', [{ ...note, id: '0'.repeat(64) }], pubkey));
  assert.throws(() => request('sign_event', [note], null));
});
test('event ID and BIP340 result match an independently signed exact event', () => {
  const expected = createHash('sha256').update(JSON.stringify([0, pubkey, 1710000000, 1, [['t', 'nostr']], 'Hello, café.\nExact text.'])).digest('hex');
  assert.equal(eventId(note), expected);
  const event = sign(); assert.deepEqual(signedEvent(event, note), event);
  assert.throws(() => signedEvent({ ...event, sig: '0'.repeat(128) }, note));
  assert.throws(() => signedEvent(event, { ...note, content: 'Changed' }));
  assert.throws(() => signedEvent({ ...event, tags: [...event.tags, ['p', pubkey]] }, note));
});
test('message, content, numeric and aggregate event bounds fail before QR display', () => {
  for (const altered of [{ content: 'a'.repeat(8193) }, { created_at: 2 ** 54 }, { kind: 65536 }, { tags: Array.from({ length: 257 }, () => ['t']) }, { tags: [Array(9).fill('x')] }, { content: '\ud800' }]) assert.throws(() => template({ ...note, ...altered }, pubkey));
  assert.throws(() => request('sign_event', [{ ...note, tags: Array.from({ length: 256 }, () => ['t', 'x'.repeat(256)]) }], pubkey));
});
test('QR collection handles reordered and repeated frames at the exact message maximum', () => {
  const source = 'x'.repeat(32768), encoded = frames(source); assert.equal(encoded.length, 86);
  const collector = new Collector(); assert.equal(collector.add(encoded[85]), null); assert.equal(collector.add(encoded[85]), null);
  let result: string | null = null; for (const frame of encoded.slice(0, 85).reverse()) result = collector.add(frame);
  assert.equal(result, source); assert.equal(collector.progress.total, 0);
  assert.throws(() => frames(source + 'x')); assert.throws(() => frames(''));
});
test('QR collection rejects mixed messages, count changes, conflicting bytes and invalid UTF8', () => {
  const a = frames('x'.repeat(500)), b = frames('y'.repeat(500)), collector = new Collector(); collector.add(a[0]);
  assert.throws(() => collector.add(b[1])); assert.throws(() => collector.add(a[0].replace(':0:2:', ':0:3:')));
  const pieces = a[0].split(':'); pieces[4] = Buffer.alloc(384, 65).toString('base64url'); assert.throws(() => collector.add(pieces.join(':')));
  const invalid = Buffer.from([255]), id = createHash('sha256').update(invalid).digest('hex');
  assert.throws(() => new Collector().add(`ns:${id}:0:1:${invalid.toString('base64url')}`));
});
test('QR collection rejects tampered hashes, noncanonical indices/base64 and false final lengths', () => {
  const one = frames('hello')[0];
  for (const broken of [one.replace(':0:1:', ':00:1:'), one + '=', one.replace(/:[^:]+$/, ':a'), one.replace(/^ns:[^:]+/, `ns:${'0'.repeat(64)}`), one.replace(':0:1:', ':0:2:')]) assert.throws(() => new Collector().add(broken));
});
test('owner rejects ungranted origins and grants never bypass the device exchange', async () => {
  const owner = new Owner(); owner.select(pubkey);
  await assert.rejects(owner.start('https://a.example', 'sign_event', [note]), /permission/);
  owner.grant('https://a.example', 'sign_event');
  const result = owner.start('https://a.example', 'sign_event', [note]); assert.ok(owner.operation);
  await assert.rejects(owner.start('https://b.example', 'sign_event', [note]));
  const event = sign(); deliver(owner, reply(owner, event)); assert.deepEqual(await result, event); assert.equal(owner.operation, null);
});
test('cancel destroys collection and prevents stale result acceptance on the next request', async () => {
  const owner = new Owner(); owner.select(pubkey);
  const first = owner.start('local', 'sign_event', [note], true); const rejected = assert.rejects(first, /cancelled/);
  const old = reply(owner, sign()); owner.cancel(); await rejected; assert.equal(owner.collector.progress.received, 0);
  const next = owner.start('local', 'sign_event', [note], true); const nextRejected = assert.rejects(next, /different request/);
  assert.throws(() => deliver(owner, old)); await nextRejected; assert.equal(owner.operation, null);
  const damaged = owner.start('local', 'sign_event', [note], true);
  const damagedRejected = assert.rejects(damaged, /Mixed QR/);
  const valid = reply(owner, sign());
  owner.scan(valid[0]);
  assert.throws(() => owner.scan(frames('x'.repeat(500))[1]));
  await damagedRejected;
  assert.equal(owner.operation, null); assert.equal(owner.collector.progress.received, 0);
});
test('identity change and permission revocation cancel pending work and reset grants', async () => {
  const owner = new Owner(); owner.select(pubkey); owner.grant('https://a.example', 'sign_event');
  const promise = owner.start('https://a.example', 'sign_event', [note]); const rejected = assert.rejects(promise, /revoked/);
  owner.revoke('https://a.example'); await rejected;
  owner.grant('https://a.example', 'get_public_key'); owner.select(pubkey); assert.equal(owner.grants.size, 0);
});
test('device rejection is final; signatures with changed data cannot escape the owner', async () => {
  const owner = new Owner(); owner.select(pubkey);
  let result = owner.start('local', 'sign_event', [note], true); let rejected = assert.rejects(result, /Device: Rejected/);
  assert.throws(() => deliver(owner, frames(JSON.stringify({ id: owner.operation!.request.id, error: 'Rejected' })))); await rejected;
  result = owner.start('local', 'sign_event', [note], true); rejected = assert.rejects(result, /changed event/);
  assert.throws(() => deliver(owner, reply(owner, finalizeEvent({ ...note, content: 'Changed' }, key)))); await rejected;
});
test('identity response must match a selected npub; ambiguous response envelopes fail', () => {
  const pending = request('get_public_key', [], pubkey);
  assert.equal(response(JSON.stringify({ id: pending.id, result: pubkey }), pending, pubkey), pubkey);
  assert.throws(() => response(JSON.stringify({ id: pending.id, result: pubkey, error: 'denied' }), pending, pubkey));
  assert.throws(() => response(JSON.stringify({ id: pending.id, result: getPublicKey(new Uint8Array(32).fill(2)) }), pending, pubkey));
});
test('NIP44 operations carry exact peer/text and require their own device response', async () => {
  const owner = new Owner(); owner.select(pubkey); owner.grant('https://client.example', 'nip44_encrypt');
  const pending = owner.start('https://client.example', 'nip44_encrypt', [pubkey, 'A private message']);
  assert.deepEqual(owner.operation!.request.params, [pubkey, 'A private message']);
  const cipher = nip44.encrypt('A private message', nip44.utils.getConversationKey(key, pubkey), new Uint8Array(32).fill(3));
  deliver(owner, reply(owner, cipher)); assert.equal(await pending, cipher);
  await assert.rejects(owner.start('https://client.example', 'nip44_decrypt', [pubkey, cipher]), /permission/);
});
test('timeouts and disconnect reject outstanding work exactly once', async () => {
  const owner = new Owner(undefined, 5); const pending = owner.start('local', 'get_public_key', [], true);
  await assert.rejects(pending, /expired/); assert.equal(owner.operation, null);
  owner.select(pubkey); owner.grant('https://a.example', 'sign_event');
  const next = owner.start('https://a.example', 'sign_event', [note]); const rejected = assert.rejects(next, /disconnected/);
  owner.disconnect(); await rejected; assert.equal(owner.key, null); assert.equal(owner.grants.size, 0);
});
