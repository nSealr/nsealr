// Native Rust signer and independent browser verifier exchange real wire frames.
import assert from 'node:assert/strict';
import { mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';
import { Collector, frames } from '../companion/src/frames.ts';
import { request, response } from '../companion/src/protocol.ts';

const require = createRequire(new URL('../companion/package.json', import.meta.url));
const { v2: nip44 } = require('nostr-tools/nip44');

const root = resolve(import.meta.dirname, '..');
const output = resolve(root, '.cache/integration');
mkdirSync(output, { recursive: true });
function run(command, args, options = {}) {
  const result = spawnSync(command, args, { cwd: root, encoding: 'utf8', ...options });
  if (result.error) throw result.error;
  return result;
}
function checked(command, args) {
  const result = run(command, args, { stdio: 'inherit' });
  assert.equal(result.status, 0, `${command} failed`);
}
checked('cargo', ['build', '-p', 'nsealr-device', '--release', '--locked', '--offline']);
const target = resolve(process.env.CARGO_TARGET_DIR || resolve(root, 'target'));
const native = resolve(output, 'optical');
checked(process.env.CC || 'cc', ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
  '-Icore/nsealr-device/include', 'tests/integration/optical.c',
  resolve(target, 'release/libnsealr_device.a'), '-lpthread', '-ldl', '-lm', '-o', native]);

const key = 'f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9';
function exchange(pending, ordered = frames(JSON.stringify(pending))) {
  const result = run(native, [], { input: ordered.join('\n') + '\n' });
  assert.equal(result.status, 0, result.stderr);
  const collector = new Collector();
  let complete;
  const returned = result.stdout.trim().split('\n');
  for (const frame of returned.reverse()) complete = collector.add(frame) ?? complete;
  assert.ok(complete);
  assert.equal(frames(complete).sort().join('\n'), returned.sort().join('\n'));
  return response(complete, pending, key);
}
assert.equal(exchange(request('get_public_key', [], key)), key);
const template = { kind: 1, created_at: 1710000000,
  tags: [['t', 'nsealr'], ['p', key]],
  content: 'Exact content: "quoted"\nCaffè, 日本語, 🔑. '.repeat(24) };
const pending = request('sign_event', [template], key);
const outgoing = frames(JSON.stringify(pending));
assert.ok(outgoing.length > 1);
const reordered = [...outgoing].reverse();
reordered.splice(1, 0, reordered[0]);
const signed = exchange(pending, reordered);
assert.equal(signed.content, template.content);
assert.deepEqual(signed.tags, template.tags);

const secret = new Uint8Array(32); secret[31] = 3;
const conversation = nip44.utils.getConversationKey(secret, key);
const plaintext = 'Private text: café, 日本語, 🔑.';
const encrypted = exchange(request('nip44_encrypt', [key, plaintext], key));
assert.equal(nip44.decrypt(encrypted, conversation), plaintext);
const ciphertext = nip44.encrypt(plaintext, conversation, new Uint8Array(32).fill(0x43));
assert.equal(exchange(request('nip44_decrypt', [key, ciphertext], key)), plaintext);
conversation.fill(0); secret.fill(0);

const corrupted = [...outgoing];
const last = corrupted[0].at(-1);
corrupted[0] = corrupted[0].slice(0, -1) + (last === 'A' ? 'B' : 'A');
assert.equal(run(native, [], { input: corrupted.join('\n') + '\n' }).status, 2);
console.log('PASS native Rust ↔ companion: identity, multipart QR, Unicode event, independent signature/NIP44 verification, damaged frame rejection.');
