import test from 'node:test';
import assert from 'node:assert/strict';
import { finalizeEvent, getPublicKey } from 'nostr-tools/pure';
import { v2 as nip44 } from 'nostr-tools/nip44';
import { RemoteSigner, relayURL } from '../src/relay.ts';
import { Owner } from '../src/owner.ts';
import { frames } from '../src/frames.ts';

const deviceKey = new Uint8Array(32).fill(1), clientKey = new Uint8Array(32).fill(2);
const devicePublic = getPublicKey(deviceKey), clientPublic = getPublicKey(clientKey);
class Socket {
  static OPEN = 1;
  static current: Socket;
  readyState = 0;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  output: unknown[][] = [];
  autoAck = true;
  constructor(_url: string) { Socket.current = this; queueMicrotask(() => { this.readyState = 1; this.onopen?.(); }); }
  send(message: string) {
    const packet = JSON.parse(message); this.output.push(packet);
    if (packet[0] === 'EVENT' && this.autoAck) queueMicrotask(() => this.receive(['OK', packet[1].id, true, '']));
  }
  receive(packet: unknown[]) { this.onmessage?.({ data: JSON.stringify(packet) }); }
  close() { if (this.readyState === 3) return; this.readyState = 3; queueMicrotask(() => this.onclose?.()); }
}
globalThis.WebSocket = Socket as unknown as typeof WebSocket;
async function until(check: () => boolean) { for (let i = 0; i < 100; i++) { if (check()) return; await new Promise(resolve => setTimeout(resolve, 2)); } assert.fail('Condition did not become true.'); }
async function setup(allow = true, autoAck = true) {
  const owner = new Owner(); owner.select(devicePublic); const prompts: string[] = [];
  const remote = new RemoteSigner('wss://relay.example/', owner, async (origin, method) => { prompts.push(`${origin}:${method}`); return allow; }, () => {});
  await remote.open(); const socket = Socket.current; socket.autoAck = autoAck;
  const conversation = nip44.utils.getConversationKey(clientKey, remote.transportKey);
  function send(id: string, method: string, params: string[]) {
    socket.receive(['EVENT', 'nsealr', finalizeEvent({ kind: 24133, created_at: Math.floor(Date.now() / 1000), tags: [['p', remote.transportKey]], content: nip44.encrypt(JSON.stringify({ id, method, params }), conversation) }, clientKey)]);
  }
  function replies() { return socket.output.filter(row => row[0] === 'EVENT').map(row => JSON.parse(nip44.decrypt((row[1] as any).content, conversation))); }
  const secret = new URL(remote.bunker).searchParams.get('secret')!;
  send('connect-rpc', 'connect', [remote.transportKey, secret]); await until(() => replies().length === 1);
  return { owner, remote, socket, send, replies, prompts, conversation };
}

test('NIP46 pairs once with a transport identity separate from the user and refuses declined pairing', async () => {
  const session = await setup(true, false); assert.notEqual(session.remote.transportKey, devicePublic); assert.equal(session.remote.client, clientPublic); assert.equal(session.replies()[0].result, 'ack');
  session.send('before-pairing-relay-ack', 'get_public_key', []);
  await new Promise(resolve => setTimeout(resolve, 10)); assert.equal(session.owner.operation, null);
  session.socket.autoAck = true;
  session.socket.receive(['OK', (session.socket.output.find(row => row[0] === 'EVENT')![1] as any).id, true, '']);
  await until(() => session.owner.operation?.request.method === 'get_public_key');
  session.remote.close();
  const denied = await setup(false); assert.match(denied.replies()[0].error, /rejected/); assert.equal(denied.remote.client, null); denied.remote.close();
});
test('NIP46 maps arbitrary RPC IDs to fresh optical IDs and returns only the verified original event', async () => {
  const session = await setup();
  const note = { created_at: 1710000000, kind: 1, tags: [], content: 'Remote note' };
  session.send('remote request with spaces', 'sign_event', [JSON.stringify(note)]);
  await until(() => !!session.owner.operation); const operation = session.owner.operation!;
  assert.notEqual(operation.request.id, 'remote request with spaces'); assert.equal(JSON.parse(operation.request.params[0]).pubkey, devicePublic);
  const signed = finalizeEvent(note, deviceKey);
  for (const frame of frames(JSON.stringify({ id: operation.request.id, result: JSON.stringify(signed) }))) session.owner.scan(frame);
  await until(() => session.replies().length === 2);
  assert.equal(session.replies()[1].id, 'remote request with spaces'); assert.equal(JSON.parse(session.replies()[1].result).id, signed.id);
  session.remote.close();
});
test('NIP46 queues at most four concurrent requests; replay and cancellation never create extra device operations', async () => {
  const session = await setup(); session.send('one', 'get_public_key', []); await until(() => !!session.owner.operation);
  const optical = session.owner.operation!.request.id;
  session.send('one', 'get_public_key', []); session.send('two', 'get_public_key', []); session.send('three', 'get_public_key', []); session.send('four', 'get_public_key', []); session.send('overflow', 'get_public_key', []);
  await until(() => session.replies().length === 2);
  assert.equal(session.owner.operation!.request.id, optical); assert.match(session.replies()[1].error, /queue is full/);
  session.owner.cancel(); await until(() => session.replies().length === 6);
  assert.ok(session.replies().slice(2).every(row => /cancelled/.test(row.error)));
  session.send('unsupported', 'nip04_encrypt', [clientPublic, 'text']); await until(() => session.replies().length === 7);
  assert.match(session.replies()[6].error, /Unsupported/); assert.equal(session.owner.operation, null); session.remote.close();
});
test('NIP46 remote close cancels its pending operation, revokes permissions and cannot reopen', async () => {
  const session = await setup(); session.send('key', 'get_public_key', []); await until(() => !!session.owner.operation);
  session.remote.close(); await until(() => session.owner.operation === null); assert.equal(session.owner.grants.size, 0);
  await assert.rejects(session.remote.open(), /closed/);
});
test('NIP46 accepts a client pairing URI only for its declared secure relay', async () => {
  assert.throws(() => relayURL('ws://relay.example')); assert.throws(() => relayURL('wss://user:secret@relay.example'));
  const owner = new Owner(); owner.select(devicePublic);
  const remote = new RemoteSigner('wss://relay.example', owner, async () => true, () => {});
  await remote.open(); const socket = Socket.current;
  await assert.rejects(remote.acceptClient(`nostrconnect://${clientPublic}?relay=wss%3A%2F%2Fwrong.example&secret=hello`));
  await remote.acceptClient(`nostrconnect://${clientPublic}?relay=wss%3A%2F%2Frelay.example%2F&secret=hello`);
  assert.equal(remote.client, clientPublic);
  const output = socket.output.find(row => row[0] === 'EVENT')!;
  assert.equal(JSON.parse(nip44.decrypt((output[1] as any).content, nip44.utils.getConversationKey(clientKey, remote.transportKey))).result, 'hello');
  remote.close();
});
