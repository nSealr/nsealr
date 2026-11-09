import test from 'node:test';
import assert from 'node:assert/strict';
import { finalizeEvent, getEventHash, getPublicKey, verifyEvent } from 'nostr-tools/pure';
import { v2 as nip44 } from 'nostr-tools/nip44';
import { Owner } from '../src/owner.ts';
import { frames } from '../src/frames.ts';
import { createRumor, messageRelays, publishCopies, readMessage, readWrap, relayCommand, sealCopies } from '../src/messaging.ts';
import type { SignedEvent } from '../src/protocol.ts';

const sender = new Uint8Array(32).fill(3), recipient = new Uint8Array(32).fill(4);
const senderPublic = getPublicKey(sender), recipientPublic = getPublicKey(recipient);
const signal = () => new AbortController().signal;
function softwareDevice(secret: Uint8Array) {
  const seen = new Set<string>(); let calls = 0;
  const owner = new Owner(() => {
    const operation = owner.operation;
    if (!operation || seen.has(operation.request.id)) return;
    seen.add(operation.request.id); calls++;
    queueMicrotask(() => {
      const request = operation.request; let result: string;
      if (request.method === 'sign_event') result = JSON.stringify(finalizeEvent(JSON.parse(request.params[0]), secret));
      else if (request.method === 'nip44_encrypt') result = nip44.encrypt(request.params[1], nip44.utils.getConversationKey(secret, request.params[0]));
      else if (request.method === 'nip44_decrypt') result = nip44.decrypt(request.params[1], nip44.utils.getConversationKey(secret, request.params[0]));
      else result = getPublicKey(secret);
      for (const frame of frames(JSON.stringify({ id: request.id, result }))) owner.scan(frame);
    });
  });
  owner.select(getPublicKey(secret)); return { owner, calls: () => calls };
}
let failSelf = true, requireAuth = false;
const posted: SignedEvent[] = [], auths: SignedEvent[] = [];
class Socket {
  static OPEN = 1;
  static current: Socket;
  subscription = '';
  readyState = 0;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  authenticated = false;
  readonly url: string;
  constructor(url: string) { this.url = url; Socket.current = this; queueMicrotask(() => { this.readyState = 1; this.onopen?.(); if (requireAuth) this.emit(['AUTH', 'actual-socket-challenge']); }); }
  emit(row: unknown[]) { queueMicrotask(() => this.onmessage?.({ data: JSON.stringify(row) })); }
  send(message: string) {
    const row = JSON.parse(message);
    if (row[0] === 'REQ') this.subscription = row[1];
    if (row[0] === 'AUTH') {
      auths.push(row[1]); assert.equal(verifyEvent(row[1]), true);
      assert.deepEqual(row[1].tags, [['relay', this.url], ['challenge', 'actual-socket-challenge']]);
      this.authenticated = true; this.emit(['OK', row[1].id, true, '']); return;
    }
    if (requireAuth && !this.authenticated) return;
    if (row[0] === 'EVENT') {
      posted.push(row[1]); const accepted = !(failSelf && row[1].tags.some((tag: string[]) => tag[0] === 'p' && tag[1] === senderPublic));
      this.emit(['OK', row[1].id, accepted, accepted ? '' : 'blocked: unavailable']);
    } else if (row[0] === 'REQ') {
      for (const secret of [sender, recipient]) {
        const event = finalizeEvent({ kind: 10050, created_at: 1710000000, tags: [['relay', 'wss://inbox.example']], content: '' }, secret);
        this.emit(['EVENT', row[1], event]);
      }
      this.emit(['EOSE', row[1]]);
    }
  }
  close() { this.readyState = 3; }
}
globalThis.WebSocket = Socket as unknown as typeof WebSocket;

test('private send creates the same unsigned rumor for recipient and self, with independently decryptable signed layers', async () => {
  const { owner, calls } = softwareDevice(sender);
  const rumor = createRumor(senderPublic, recipientPublic, 'Private café message');
  const boxes = new Map([[senderPublic, ['wss://inbox.example/']], [recipientPublic, ['wss://inbox.example/']]]);
  const copies = await sealCopies(owner, rumor, boxes, signal()); assert.equal(copies.length, 2); assert.equal(calls(), 4);
  assert.notEqual(copies[0].event.pubkey, copies[1].event.pubkey);
  for (const [index, secret] of [recipient, sender].entries()) {
    const wrap = copies[index].event; assert.equal(verifyEvent(wrap), true);
    const seal = JSON.parse(nip44.decrypt(wrap.content, nip44.utils.getConversationKey(secret, wrap.pubkey)));
    assert.equal(verifyEvent(seal), true); assert.equal(seal.pubkey, senderPublic); assert.deepEqual(seal.tags, []);
    const inner = JSON.parse(nip44.decrypt(seal.content, nip44.utils.getConversationKey(secret, seal.pubkey)));
    assert.equal(inner.sig, undefined); assert.equal(getEventHash(inner), inner.id); assert.deepEqual(inner, rumor);
    const reader = softwareDevice(secret); assert.deepEqual(await readMessage(reader.owner, wrap, signal()), rumor); assert.equal(reader.calls(), 2);
  }
  assert.throws(() => createRumor(senderPublic, recipientPublic, 'x'.repeat(4096)), /limit/);
});
test('selected-message receive rejects wrong outer recipient and a seal that impersonates the inner author', async () => {
  const { owner } = softwareDevice(recipient), attacker = new Uint8Array(32).fill(5), wrapper = new Uint8Array(32).fill(6);
  const rumor = createRumor(senderPublic, recipientPublic, 'Forged author');
  const seal = finalizeEvent({ kind: 13, created_at: 1710000000, tags: [], content: nip44.encrypt(JSON.stringify(rumor), nip44.utils.getConversationKey(attacker, recipientPublic)) }, attacker);
  const wrap = finalizeEvent({ kind: 1059, created_at: 1710000000, tags: [['p', recipientPublic]], content: nip44.encrypt(JSON.stringify(seal), nip44.utils.getConversationKey(wrapper, recipientPublic)) }, wrapper);
  assert.throws(() => readWrap(wrap, senderPublic), /addressed/);
  await assert.rejects(readMessage(owner, wrap, signal()), /different identity/);
});
test('copy publication exposes partial failure and retry reuses only the unaccepted encrypted event', async () => {
  posted.length = 0; failSelf = true; requireAuth = false;
  const { owner } = softwareDevice(sender), rumor = createRumor(senderPublic, recipientPublic, 'Retry this copy');
  const copies = await sealCopies(owner, rumor, new Map([[senderPublic, ['wss://inbox.example/']], [recipientPublic, ['wss://inbox.example/']]]), signal());
  await publishCopies(owner, copies, signal(), () => {});
  assert.equal(copies[0].accepted.length, 1); assert.equal(copies[1].accepted.length, 0); assert.equal(Object.keys(copies[1].errors).length, 1);
  const pendingID = copies[1].event.id; failSelf = false;
  await publishCopies(owner, copies, signal(), () => {}); assert.equal(posted.length, 3); assert.equal(posted[2].id, pendingID); assert.equal(copies[1].accepted.length, 1);
});
test('message relay discovery verifies signed preferences and authenticates the actual selected socket through the owner', async () => {
  auths.length = 0; requireAuth = true;
  const { owner } = softwareDevice(sender);
  const boxes = await messageRelays(owner, [senderPublic, recipientPublic], ['wss://discovery.example'], signal());
  assert.deepEqual(boxes.get(recipientPublic), ['wss://inbox.example/']); assert.equal(auths.length, 1); assert.equal(auths[0].pubkey, senderPublic);
  const aborted = new AbortController(); aborted.abort();
  assert.throws(() => relayCommand(owner, 'wss://inbox.example', {}, false, aborted.signal), /cancelled/);
  const waiting = new Owner(); waiting.select(senderPublic);
  const query = relayCommand(waiting, 'wss://inbox.example', {}, false, signal());
  await new Promise(resolve => setTimeout(resolve, 0)); assert.equal(waiting.operation?.request.method, 'sign_event');
  Socket.current.emit(['EOSE', Socket.current.subscription]);
  assert.deepEqual(await query, []); assert.equal(waiting.operation, null);
  requireAuth = false;
});
