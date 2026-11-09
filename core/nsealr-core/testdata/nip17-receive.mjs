// Public test keys only. Independent nostr-tools/Node fixture oracle, not firmware.
// Usage: node nip17-receive.mjs NODE_MODULES PINNED_NIPS OUTPUT_JSON
import assert from 'node:assert/strict';
import {createHash, createHmac} from 'node:crypto';
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
import {readFileSync, writeFileSync} from 'node:fs';
const require = createRequire(resolve(process.argv[2], 'package.json'));
const {getPublicKey, nip19, nip44, verifyEvent} = require('nostr-tools');
const {schnorr} = createRequire(require.resolve('nostr-tools'))('@noble/curves/secp256k1.js');
assert.equal(JSON.parse(readFileSync(resolve(process.argv[2], 'nostr-tools/package.json'))).version, '2.23.3');
const keys = [1, 2, 3, 4, 5, 6].map(n => { const b = new Uint8Array(32); b[31] = n; return b; });
const pubs = keys.map(getPublicKey), rows = [];
const id = e => createHash('sha256').update(JSON.stringify([0, e.pubkey, e.created_at, e.kind, e.tags, e.content])).digest('hex');
const clone = e => JSON.parse(JSON.stringify(e));
const sign = (e, key) => {
  const event = {...e, pubkey: getPublicKey(key)};
  event.id = id(event);
  event.sig = Buffer.from(schnorr.sign(Buffer.from(event.id, 'hex'), key, new Uint8Array(32))).toString('hex');
  assert(verifyEvent(clone(event)));
  return event;
};
const json = e => JSON.stringify(e);
const plainBytes = x => Buffer.byteLength(x);
let sequence = 0;
function encrypt(text, key, peer) {
  // Deterministic test-only nonce, domain-separated by monotonically fresh index.
  const nonce = createHmac('sha256', 'nsealr public nip17 receive fixtures').update(String(sequence++)).digest();
  return nip44.v2.encrypt(text, nip44.v2.utils.getConversationKey(key, peer), nonce);
}
function oracle(raw, key) {
  const wrap = JSON.parse(raw); assert(verifyEvent(clone(wrap)));
  const seal = JSON.parse(nip44.v2.decrypt(wrap.content, nip44.v2.utils.getConversationKey(key, wrap.pubkey)));
  assert(verifyEvent(clone(seal))); assert.equal(seal.kind, 13); assert.deepEqual(seal.tags, []);
  const rumor = JSON.parse(nip44.v2.decrypt(seal.content, nip44.v2.utils.getConversationKey(key, seal.pubkey)));
  assert.equal(rumor.pubkey, seal.pubkey); assert.equal(id(rumor), rumor.id); assert.equal(rumor.kind, 14); assert(!('sig' in rumor));
  const local = getPublicKey(key), participants = rumor.tags.filter(t => t[0] === 'p').map(t => t[1]);
  assert(rumor.pubkey === local || participants.includes(local));
  return {sender: rumor.pubkey, recipient: local, rumor_id: rumor.id, gift_wrap_id: wrap.id,
    created_at: rumor.created_at, content: rumor.content, tags: rumor.tags, sender_copy: rumor.pubkey === local};
}
function fixture(name, options = {}) {
  const receiver = options.self ? keys[0] : keys[1], receiverPub = getPublicKey(receiver);
  let rumor = {pubkey: pubs[0], created_at: 1730000000, kind: 14, tags: [['p', pubs[1]]], content: 'Hello'};
  options.rumor?.(rumor); rumor.id = id(rumor); options.rumorAfterId?.(rumor);
  let rumorText = options.rumorRaw?.(json(rumor)) ?? json(rumor);
  if (options.rumorBytes) rumorText = rumorText.padEnd(options.rumorBytes, ' ');
  let inner = encrypt(rumorText, keys[0], receiverPub);
  if (options.innerMac) { const binary = Buffer.from(inner, 'base64'); binary[binary.length - 1] ^= 1; inner = binary.toString('base64'); }
  let sealTemplate = {created_at: 1729900000, kind: 13, tags: [], content: inner}; options.seal?.(sealTemplate);
  let seal = sign(sealTemplate, keys[0]); options.sealAfterSign?.(seal);
  let sealText = options.sealRaw?.(json(seal)) ?? json(seal);
  if (options.sealBytes) sealText = sealText.padEnd(options.sealBytes, ' ');
  let outer = encrypt(sealText, keys[2], receiverPub);
  if (options.outerMac) { const binary = Buffer.from(outer, 'base64'); binary[binary.length - 1] ^= 1; outer = binary.toString('base64'); }
  let wrapTemplate = {created_at: 1729890000, kind: 1059, tags: [['p', receiverPub]], content: outer}; options.wrap?.(wrapTemplate);
  let wrap = sign(wrapTemplate, keys[2]); options.wrapAfterSign?.(wrap);
  let wrapText = options.wrapRaw?.(json(wrap)) ?? json(wrap);
  if (options.wrapBytes) wrapText = wrapText.padEnd(options.wrapBytes, ' ');
  const localKey = options.unrelated ? keys[3] : receiver;
  const accept = options.accept ?? true;
  rows.push({name, accept, local_secret: Buffer.from(localKey).toString('hex'), gift_wrap: wrapText,
    sizes: {rumor: plainBytes(rumorText), seal: plainBytes(sealText), gift_wrap: plainBytes(wrapText)},
    ...(accept ? {expected: oracle(wrapText, localKey)} : {})});
}
for (const n of [0, 1, 31, 32, 128, 512, 1024, 1536, 2048]) fixture(`message-${n}`, {rumor: r => r.content = 'x'.repeat(n)});
fixture('unicode-controls', {rumor: r => {r.content = 'Café 世界😀\u2028\u2029\0\b\f\n\r\t"\\'; r.tags.push(['subject', '私密😀'], ['unknown', '\0\n', 'é']);}});
fixture('group-four', {rumor: r => r.tags = pubs.slice(1, 5).map(p => ['p', p, 'wss://relay.example'])});
fixture('sender-self-copy', {self: true});
fixture('sender-self-group', {self: true, rumor: r => r.tags = pubs.slice(1, 5).map(p => ['p', p])});
fixture('rumor-exact-2560', {rumor: r => r.content = 'x'.repeat(2048), rumorBytes: 2560});
fixture('seal-exact-4096', {sealBytes: 4096});
fixture('outer-exact-8192', {wrapBytes: 8192});
fixture('all-32-tags', {rumor: r => r.tags.push(...Array.from({length: 31}, (_, n) => ['x', String(n)]))});
fixture('all-eight-fields', {rumor: r => r.tags.push(['x', ...Array(7).fill('field')])});
fixture('field-exact-256', {rumor: r => r.tags.push(['subject', 'x'.repeat(256)])});
fixture('escaped-serialized-fields', {rumorRaw: s => s.replace('Hello', '\\u0048ello'), sealRaw: s => s.replace('"kind"', '"\\u006bind"'), wrapRaw: s => s.replace('"kind"', '"\\u006bind"')});
fixture('message-over-2048', {accept: false, rumor: r => r.content = 'x'.repeat(2049)});
fixture('rumor-over-2560', {accept: false, rumorBytes: 2561});
fixture('seal-over-4096', {accept: false, sealBytes: 4097});
fixture('outer-over-8192', {accept: false, wrapBytes: 8193});
fixture('all-33-tags', {accept: false, rumor: r => r.tags.push(...Array.from({length: 32}, (_, n) => ['x', String(n)]))});
fixture('nine-fields', {accept: false, rumor: r => r.tags.push(['x', ...Array(8).fill('field')])});
fixture('field-over-256', {accept: false, rumor: r => r.tags.push(['subject', 'x'.repeat(257)])});
fixture('unrelated-local-key', {accept: false, unrelated: true});
fixture('wrong-routing-recipient', {accept: false, wrap: w => w.tags = [['p', pubs[3]]]});
fixture('two-routing-recipients', {accept: false, wrap: w => w.tags.push(['p', pubs[3]])});
fixture('duplicate-routing-recipient', {accept: false, wrap: w => w.tags.push([...w.tags[0]])});
fixture('missing-routing-recipient', {accept: false, wrap: w => w.tags = []});
fixture('routing-p-without-key', {accept: false, wrap: w => w.tags = [['p']]});
fixture('wrong-rumor-recipient', {accept: false, rumor: r => r.tags = [['p', pubs[3]]]});
fixture('missing-rumor-recipient', {accept: false, rumor: r => r.tags = []});
fixture('sender-copy-without-conversation', {accept: false, self: true, rumor: r => r.tags = []});
fixture('duplicate-rumor-recipient', {accept: false, rumor: r => r.tags.push([...r.tags[0]])});
fixture('invalid-curve-recipient', {accept: false, rumor: r => r.tags = [['p', 'ff'.repeat(32)]]});
fixture('short-rumor-recipient', {accept: false, rumor: r => r.tags = [['p', '00']]});
fixture('extra-p-field', {accept: false, rumor: r => r.tags[0].push('', 'extra')});
fixture('empty-tag', {accept: false, rumor: r => r.tags.push([])});
fixture('empty-tag-name', {accept: false, rumor: r => r.tags.push(['', 'field'])});
fixture('signed-rumor', {accept: false, rumorAfterId: r => r.sig = '00'.repeat(64)});
fixture('forged-rumor-id', {accept: false, rumorAfterId: r => r.id = '00'.repeat(32)});
fixture('impersonated-rumor-author', {accept: false, rumor: r => r.pubkey = pubs[3]});
fixture('wrong-rumor-kind', {accept: false, rumor: r => r.kind = 15});
fixture('wrong-seal-kind', {accept: false, seal: s => s.kind = 14});
fixture('seal-tags-not-empty', {accept: false, seal: s => s.tags = [['p', pubs[1]]]});
fixture('wrong-wrap-kind', {accept: false, wrap: w => w.kind = 21059});
fixture('forged-wrap-id', {accept: false, wrapAfterSign: w => w.id = '00'.repeat(32)});
fixture('forged-wrap-signature', {accept: false, wrapAfterSign: w => w.sig = '00'.repeat(64)});
fixture('forged-seal-id', {accept: false, sealAfterSign: s => s.id = '00'.repeat(32)});
fixture('forged-seal-signature', {accept: false, sealAfterSign: s => s.sig = '00'.repeat(64)});
fixture('tampered-outer-mac', {accept: false, outerMac: true});
fixture('tampered-inner-mac', {accept: false, innerMac: true});
for (const layer of ['rumor', 'seal', 'wrap']) {
  for (const [label, alter] of [
    ['duplicate', s => s.replace('"kind":', '"kind":14,"kind":')],
    ['unknown', s => s.replace('{', '{"unexpected":0,')],
    ['number-fraction', s => s.replace(/"created_at":\d+/, '"created_at":1730000000.0')],
    ['number-exponent', s => s.replace(/"created_at":\d+/, '"created_at":173e7')],
    ['number-leading-zero', s => s.replace(/"created_at":\d+/, '"created_at":01730000000')],
    ['number-negative-zero', s => s.replace(/"created_at":\d+/, '"created_at":-0')],
    ['number-over-js-safe', s => s.replace(/"created_at":\d+/, '"created_at":9007199254740992')],
    ['trailing-data', s => s + '{}'],
    ['unpaired-surrogate', s => s.replace('"content":"', '"content":"\\ud800')],
  ]) fixture(`${layer}-${label}`, {accept: false, [`${layer}Raw`]: alter});
}
// Published NIP17 examples, independent of our generated envelopes.
const markdown = readFileSync(resolve(process.argv[3], '17.md'), 'utf8');
const published = [...markdown.matchAll(/```json\s*([\s\S]*?)```/g)].map(m => JSON.parse(m[1])).filter(e => e.kind === 1059);
assert.equal(published.length, 2);
const publishedSecrets = ['nsec12ywtkplvyq5t6twdqwwygavp5lm4fhuang89c943nf2z92eez43szvn4dt', 'nsec1w8udu59ydjvedgs3yv5qccshcj8k05fh3l60k9x57asjrqdpa00qkmr89m'];
published.forEach((wrap, i) => {
  const secret = nip19.decode(publishedSecrets[i]).data, raw = json(wrap);
  rows.push({name: `published-nip17-${i}`, accept: true, local_secret: Buffer.from(secret).toString('hex'), gift_wrap: raw, expected: oracle(raw, secret)});
});
writeFileSync(process.argv[4], JSON.stringify({public_fixture_only: true, source: 'nostr-tools@2.23.3 + Node crypto SHA256 + pinned NIP17 examples', nips_commit: 'b587c619c2ea662d40b40976aeccf6ac8d6ba9eb', cases: rows}, null, 2) + '\n');
console.log(JSON.stringify({cases: rows.length, accepted: rows.filter(r => r.accept).length, refused: rows.filter(r => !r.accept).length}));
