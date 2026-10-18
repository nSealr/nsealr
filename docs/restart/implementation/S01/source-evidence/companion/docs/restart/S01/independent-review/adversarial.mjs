// Independent review experiment. Public scalars 1..4 are test material only.
// Wire envelopes and signed results use nostr-tools, not Bridge's wire helpers.
import assert from 'node:assert/strict';
import { PassThrough, Writable } from 'node:stream';
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import { finalizeEvent, getPublicKey, verifyEvent } from 'nostr-tools/pure';
import { nip44 } from 'nostr-tools';
import { Nip46SessionManager } from '../../../../packages/nip46/dist/session-manager.js';
import { parseStrictJson } from '../../../../packages/protocol/dist/encoding.js';
import { evaluateNip46RelayResponseStep } from '../../../../packages/nip46/dist/nip46.js';
import { SerialLineStreamPort } from '../../../../packages/transport/dist/transport.js';
import { NostrToolsRelay } from '../../../../packages/nip46/dist/relay-pool-adapter.js';

const scalar = n => Uint8Array.from({length: 32}, (_, i) => i === 31 ? n : 0);
const client = scalar(1), remote = scalar(2), user = scalar(3), attacker = scalar(4);
const cp = getPublicKey(client), rp = getPublicKey(remote), up = getPublicKey(user);
assert.equal(cp, '79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798');
assert.notEqual(rp, up);
const template = {created_at: 1700000000, kind: 1, tags: [['t', 'independent']], content: 'review'};
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const flush = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return {promise, resolve, reject}; };
const observed = promise => promise.then(value => ({ok: true, value}), error => ({ok: false, error}));
function wire(raw, author = remote, tags = [['p', cp]]) {
  const content = nip44.v2.encrypt(raw, nip44.v2.utils.getConversationKey(author, cp));
  return finalizeEvent({kind: 24133, created_at: 1700000000, tags, content}, author);
}
function harness(options = {}) {
  const subscriptions = [], messages = [];
  const h = {subscriptions, messages, onPublish: undefined};
  h.deliverRaw = (raw, index = subscriptions.length - 1, author = remote, tags) => subscriptions[index].handler(wire(raw, author, tags));
  h.deliver = (message, index, author) => h.deliverRaw(JSON.stringify(message), index, author);
  h.reply = message => h.deliver({id: message.id, result: message.method === 'connect' ? 'ack' : message.method === 'get_public_key' ? up : JSON.stringify(finalizeEvent(JSON.parse(message.params[0]), user))});
  h.transport = {
    async subscribe(filter, handler) { const sub = {filter, handler, closes: 0}; subscriptions.push(sub); return {close() { ++sub.closes; }}; },
    async publish(event) {
      assert.equal(verifyEvent(event), true);
      assert.equal(event.pubkey, cp);
      const message = JSON.parse(nip44.v2.decrypt(event.content, nip44.v2.utils.getConversationKey(remote, cp)));
      messages.push(message);
      return h.onPublish ? h.onPublish(message) : h.reply(message);
    },
    async close() {}
  };
  h.session = new Nip46SessionManager({clientSecretKey: client, remoteSignerPubkey: rp, expectedUserPubkey: up, transport: h.transport, requestTimeoutMs: 70, randomId: () => 'same', ...options});
  return h;
}
const results = [];
async function check(name, run) {
  const start = performance.now();
  try { await run(); results.push({name, outcome: 'pass', milliseconds: Math.round(performance.now() - start)}); console.log(`PASS ${name}`); }
  catch (error) { results.push({name, outcome: 'fail', error: String(error)}); console.error(`FAIL ${name}`, error); }
}

await check('foreign author cannot ack, select identity, or cancel a signing request; same-key valid control succeeds', async () => {
  const h = harness();
  h.onPublish = message => {
    h.deliver({id: message.id, error: 'foreign correlated failure'}, undefined, attacker);
    h.deliver({id: message.id, result: getPublicKey(attacker)}, undefined, attacker);
    h.reply(message);
  };
  try { await h.session.connect(); const signed = await h.session.signEvent(structuredClone(template)); assert.equal(signed.pubkey, up); assert.equal(verifyEvent(signed), true); }
  finally { await h.session.close(); }
});

await check('default adapter filters a malicious actual loopback WebSocket relay ignoring author/recipient/kind filters', async () => {
  // Minimal actual HTTP-upgrade/WebSocket peer: no mocked SimplePool or socket.
  // It deliberately sends nonmatching events under the requested subscription.
  const server = createServer(); const sockets = new Set(); const delivered = [];
  const control = wire('{"id":"loopback","result":"ack"}');
  const badRecipient = wire('wrong recipient', remote, [['p', getPublicKey(attacker)]]);
  const badKind = finalizeEvent({...control, kind: 1}, remote);
  const invalidSignature = {...wire('invalid signature'), sig: '0'.repeat(128)};
  const send = (socket, value) => {
    const payload = Buffer.from(JSON.stringify(value));
    const header = payload.length < 126 ? Buffer.from([0x81, payload.length]) : Buffer.from([0x81, 126, payload.length >> 8, payload.length & 255]);
    socket.write(Buffer.concat([header, payload]));
  };
  server.on('upgrade', (request, socket) => {
    sockets.add(socket); socket.on('close', () => sockets.delete(socket));
    const accept = createHash('sha1').update(request.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    socket.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${accept}\r\n\r\n`);
    let buffered = Buffer.alloc(0);
    socket.on('data', chunk => {
      buffered = Buffer.concat([buffered, chunk]);
      while (buffered.length >= 2) {
        const opcode = buffered[0] & 15, masked = (buffered[1] & 128) !== 0;
        let length = buffered[1] & 127, offset = 2;
        if (length === 126) { if (buffered.length < 4) return; length = buffered.readUInt16BE(2); offset = 4; }
        assert.notEqual(length, 127, 'small fixture frames only');
        if (buffered.length < offset + (masked ? 4 : 0) + length) return;
        const mask = masked ? buffered.subarray(offset, offset + 4) : undefined;
        offset += masked ? 4 : 0;
        const payload = Buffer.from(buffered.subarray(offset, offset + length)); buffered = buffered.subarray(offset + length);
        if (mask) for (let i = 0; i < payload.length; ++i) payload[i] ^= mask[i % 4];
        if (opcode === 8) { socket.end(); continue; }
        if (opcode !== 1) continue;
        const message = JSON.parse(payload.toString());
        if (message[0] === 'REQ') {
          const sub = message[1];
          for (const event of [wire('foreign', attacker), badRecipient, badKind, invalidSignature, control]) send(socket, ['EVENT', sub, event]);
          send(socket, ['EOSE', sub]);
        }
      }
    });
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const adapter = new NostrToolsRelay([`ws://127.0.0.1:${server.address().port}`]);
  let sub;
  try {
    const ready = deferred();
    sub = await adapter.subscribe({kinds: [24133], authors: [rp], '#p': [cp]}, event => { delivered.push(event); if (event.id === control.id) ready.resolve(); });
    await Promise.race([ready.promise, sleep(1000).then(() => { throw new Error('loopback response deadline'); })]);
    await flush(); assert.deepEqual(delivered.map(x => x.id), [control.id]);
    console.log('  actual loopback relay: five delivered wire events, one accepted callback');
  } finally {
    sub?.close(); await adapter.close(); for (const socket of sockets) socket.destroy();
    await new Promise(resolve => server.close(resolve));
  }
});

await check('ambiguous outer recipients and duplicate/trailing plaintext do not consume the valid correlation slot', async () => {
  const h = harness();
  h.onPublish = message => {
    const failure = JSON.stringify({id: message.id, error: 'injected'});
    h.deliverRaw(failure, undefined, remote, [['p', cp], ['p', cp]]);
    h.deliverRaw(`{"id":"${message.id}","\\u0069d":"${message.id}","error":"injected"}`);
    h.deliverRaw(failure + '{}');
    h.deliverRaw(failure.padEnd(1025, ' '));
    h.reply(message);
  };
  try { await h.session.connect(); assert.equal((await h.session.signEvent(structuredClone(template))).pubkey, up); }
  finally { await h.session.close(); }
});

await check('correct transport cannot substitute user, canonical content, nested duplicate, id, or signature', async () => {
  const h = harness(); await h.session.connect();
  try {
    for (const mode of ['user', 'content', 'duplicate', 'id', 'signature']) {
      h.onPublish = message => {
        const t = JSON.parse(message.params[0]);
        if (mode === 'content') t.content += ' changed';
        const signed = finalizeEvent(t, mode === 'user' ? attacker : user);
        if (mode === 'id') signed.id = '0'.repeat(64);
        if (mode === 'signature') signed.sig = '0'.repeat(128);
        let result = JSON.stringify(signed);
        if (mode === 'duplicate') result = result.slice(0, -1) + `,"\\u0070ubkey":"${up}"}`;
        h.deliver({id: message.id, result});
      };
      const result = await observed(h.session.signEvent(structuredClone(template)));
      assert.equal(result.ok, false, mode);
    }
    h.onPublish = undefined;
    const callerTemplate = structuredClone(template);
    const signing = h.session.signEvent(callerTemplate);
    callerTemplate.tags[0][1] = 'mutated'; callerTemplate.content = 'mutated';
    const signed = await signing;
    assert.equal(signed.content, template.content); assert.deepEqual(signed.tags, template.tags);
  } finally { await h.session.close(); }
});

await check('invalid discovered curve point fails closed and retry selects a valid distinct user', async () => {
  const h = harness({expectedUserPubkey: undefined});
  h.onPublish = message => message.method === 'get_public_key' ? h.deliver({id: message.id, result: 'f'.repeat(64)}) : h.reply(message);
  try {
    assert.equal((await observed(h.session.connect())).ok, false);
    assert.equal(h.session.phase, 'idle'); assert.equal(h.session.userPubkey, undefined);
    assert.equal(h.subscriptions[0].closes, 1);
    h.onPublish = undefined; await h.session.connect(); assert.equal(h.session.userPubkey, up);
    assert.equal(new Set(h.messages.map(x => x.id)).size, h.messages.length);
  } finally { await h.session.close(); }
});

await check('timeout/reconnect survives old publication rejection and old-handler injection of the new request id', async () => {
  const h = harness({maxPendingRequests: 2});
  const firstPublish = deferred();
  h.onPublish = message => { h.reply(message); return firstPublish.promise; };
  try {
    const first = observed(h.session.connect());
    await sleep(90); assert.equal((await first).ok, false); assert.equal(h.subscriptions[0].closes, 1);
    h.onPublish = message => {
      // The old callback sees the *current* ID. Epoch filtering, not ID uniqueness,
      // must prevent this valid, same-author injected failure from consuming it.
      h.deliver({id: message.id, error: 'old subscription callback'}, 0);
      h.deliver({id: h.messages[0].id, result: 'ack'});
      firstPublish.reject(new Error('late failed old publish'));
      h.reply(message);
    };
    await h.session.connect(); assert.equal(h.session.phase, 'session_active');
    assert.equal((await h.session.signEvent(structuredClone(template))).pubkey, up);
    assert.equal(new Set(h.messages.map(x => x.id)).size, h.messages.length);
    assert.equal(h.session.publishing, 0); assert.equal(h.session.pending.size, 0);
  } finally { await h.session.close(); }
});

await check('100 retries cannot accumulate more than two unsettled publications after logical timeouts', async () => {
  const h = harness({maxPendingRequests: 2}); await h.session.connect();
  const holds = [];
  h.onPublish = () => { const hold = deferred(); holds.push(hold); return hold.promise; };
  try {
    const a = observed(h.session.signEvent(structuredClone(template))), b = observed(h.session.signEvent(structuredClone(template)));
    await sleep(90); assert.equal((await a).ok, false); assert.equal((await b).ok, false);
    for (let i = 0; i < 100; ++i) assert.match((await observed(h.session.signEvent(structuredClone(template)))).error.message, /publish limit/);
    assert.equal(holds.length, 2); assert.equal(h.session.publishing, 2); assert.equal(h.session.pending.size, 0);
    holds[0].resolve(); holds[1].reject(new Error('late rejection')); await flush();
    assert.equal(h.session.publishing, 0); h.onPublish = undefined;
    assert.equal((await h.session.signEvent(structuredClone(template))).pubkey, up);
  } finally { holds.forEach(x => x.resolve()); await h.session.close(); }
});

await check('100 retries cannot accumulate subscription acquisitions; late handle closes once and cannot activate', async () => {
  const h = harness(); const acquisition = deferred(); let calls = 0, closes = 0;
  h.transport.subscribe = () => { ++calls; return acquisition.promise; };
  const first = observed(h.session.connect()); await sleep(90); assert.equal((await first).ok, false);
  for (let i = 0; i < 100; ++i) assert.match((await observed(h.session.connect())).error.message, /acquisition still pending/);
  assert.equal(calls, 1); await h.session.close(); acquisition.resolve({close() { ++closes; }}); await flush();
  assert.equal(closes, 1); assert.equal(h.session.phase, 'session_closed'); assert.equal(h.session.userPubkey, undefined);
});

await check('response/publication/close ordering matrix never returns a signature before publication or after cancellation', async () => {
  for (const order of ['response,publish', 'publish,response', 'response,close,publish', 'publish,close,response', 'close,response,publish', 'close,publish,response']) {
    const h = harness(); await h.session.connect(); const hold = deferred(); let message;
    h.onPublish = m => { message = m; return hold.promise; };
    let outcome; const result = observed(h.session.signEvent(structuredClone(template))).then(x => { outcome = x; return x; });
    await flush();
    for (const action of order.split(',')) {
      if (action === 'response') h.reply(message);
      if (action === 'publish') hold.resolve();
      if (action === 'close') await h.session.close();
      await flush();
      if (action === order.split(',')[0] && action !== 'close') assert.equal(outcome, undefined, order);
    }
    assert.equal((await result).ok, !order.includes('close'), order);
    await h.session.close(); assert.equal(h.session.pending.size, 0); assert.equal(h.session.publishing, 0);
  }
});

await check('strict JSON rejects escaped duplicate aliases at every container depth while accepting distinct keys', async () => {
  for (let depth = 0; depth < 32; ++depth) {
    const wrap = inner => '['.repeat(depth) + inner + ']'.repeat(depth);
    assert.throws(() => parseStrictJson(wrap('{"x":0,"\\u0078":1}'), 1024), /duplicate/);
    assert.deepEqual(parseStrictJson(wrap('{"x":0,"y":1}'), 1024), JSON.parse(wrap('{"x":0,"y":1}')));
  }
  assert.throws(() => parseStrictJson('['.repeat(33) + '0' + ']'.repeat(33), 1024), /nesting/);
  const exact = JSON.stringify('€'.repeat(340) + 'aa'); assert.equal(Buffer.byteLength(exact), 1024);
  assert.equal(typeof parseStrictJson(exact, 1024), 'string');
  assert.throws(() => parseStrictJson(exact + ' ', 1024), /byte/);
  for (const value of ['{"a":"escaped \\" },{ not tokens","b":0}', '{"__proto__":0,"\\u005f_proto__":1}']) {
    if (value.includes('__proto__')) assert.throws(() => parseStrictJson(value, 1024), /duplicate/);
    else assert.deepEqual(parseStrictJson(value, 1024), JSON.parse(value));
  }
});

await check('all decoded chunk partitions obey aggregate byte/line model, discard overflow, and remove listeners', async () => {
  const text = 'a\n€\r\ntail'; const codepoints = [...text]; let partitions = 0;
  for (const maxBytes of [10, 11, 12]) for (let split = 0; split <= codepoints.length; ++split) {
    ++partitions;
    const input = new PassThrough(), output = new PassThrough();
    const port = new SerialLineStreamPort({input, output, maxBufferedBytes: maxBytes, maxBufferedLines: 3});
    // Bypass pause deliberately: an adapter delivering decoded chunks anyway
    // must encounter the cap, not silently retain an unbounded private queue.
    input.emit('data', codepoints.slice(0, split).join(''));
    input.emit('data', codepoints.slice(split).join(''));
    if (maxBytes < Buffer.byteLength(text)) {
      assert.equal(port.bufferedBytes, 0); assert.equal(port.buffer, '');
      assert.equal((await observed(port.readLine())).ok, false);
    } else {
      assert.equal(port.bufferedBytes, Buffer.byteLength(text)); assert.equal(input.isPaused(), true);
      input.emit('end');
      assert.equal(await port.readLine(), 'a\n'); assert.equal(await port.readLine(), '€\r\n');
      assert.equal(await port.readLine(), 'tail'); assert.equal(await port.readLine(), null);
    }
    port.close(); await flush();
    for (const stream of [input, output]) for (const event of ['data', 'error', 'close']) assert.equal(stream.listenerCount(event), 0);
  }
  console.log(`  modeled chunk partitions: ${partitions}`);
});

await check('stream callback failure preserves first error across buffered data, pending read/write, and hostile redelivery', async () => {
  const input = new PassThrough(); let complete;
  const output = new Writable({highWaterMark: 1, write(_chunk, _encoding, callback) { complete = callback; }});
  const port = new SerialLineStreamPort({input, output, maxBufferedBytes: 4});
  const reading = observed(port.readLine()), writing = observed(port.writeLine('x'));
  const failure = new Error('independent output failure'); complete(failure);
  assert.equal((await reading).error, failure); assert.equal((await writing).error, failure);
  input.emit('data', 'x\n'.repeat(10000)); port.close();
  assert.equal((await observed(port.readLine())).error, failure); assert.equal((await observed(port.writeLine('x'))).error, failure);
  assert.equal(port.bufferedBytes, 0); await flush(); assert.equal(output.listenerCount('drain'), 0);
});

await check('v1 metadata separates keys and expected-user binding without claiming session authority', async () => {
  const fixture = JSON.parse(readFileSync(new URL('../../../../tests/fixtures/specs/vectors/nip46-relay-steps/get-public-key-response-step.json', import.meta.url), 'utf8'));
  fixture.decrypted_message.result = up;
  delete fixture.expected_user_pubkey;
  const unbound = evaluateNip46RelayResponseStep(fixture);
  assert.equal(unbound.format, 'nsealr-nip46-relay-response-step-v1'); assert.equal(unbound.result_pubkey, up);
  assert.equal(unbound.result_pubkey_bound_to_expected_user, false);
  fixture.expected_user_pubkey = up;
  const bound = evaluateNip46RelayResponseStep(fixture); assert.equal(bound.result_pubkey_bound_to_expected_user, true);
  for (const field of ['acknowledges_connect', 'dispatches_signer', 'creates_grants', 'persists_session_state']) assert.equal(bound[field], false);
  fixture.expected_user_pubkey = getPublicKey(attacker); assert.throws(() => evaluateNip46RelayResponseStep(fixture), /expected user/);
});

console.log(JSON.stringify({candidate: 'd385ddb0c775a1e863e9db0ee9ae38fee5f19057', results}, null, 2));
if (results.some(x => x.outcome !== 'pass')) process.exitCode = 1;
