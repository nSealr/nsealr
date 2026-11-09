// Independent NIP-01/BIP340 oracle. No Rust canonicalization/signing code is used.
// Run from repository root after pnpm install --frozen-lockfile --offline.
import { createHash } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { schnorr } from '../../../node_modules/.pnpm/@noble+curves@2.2.0/node_modules/@noble/curves/secp256k1.js';

const secret = new Uint8Array(32); secret[31] = 3; // PUBLIC fixture, never custody.
const pubkey = Buffer.from(schnorr.getPublicKey(secret)).toString('hex');
const signed = (template) => {
  const canonical = JSON.stringify([0, pubkey, template.created_at, template.kind, template.tags, template.content]);
  const digest = createHash('sha256').update(canonical).digest();
  return { ...template, pubkey, id: digest.toString('hex'), sig: Buffer.from(schnorr.sign(digest, secret, new Uint8Array(32))).toString('hex') };
};
const originals = [
  { kind: 0, tags: [], content: '{"name":"Public fixture"}' },
  { kind: 7, tags: [['e', 'ab'.repeat(32)], ['p', pubkey]], content: '+' },
  { kind: 1111, tags: [['I', 'https://example.com/article'], ['K', 'web'], ['i', 'https://example.com/article'], ['k', 'web']], content: 'A public comment.' },
  { kind: 30023, tags: [['d', 'article:日本'], ['title', 'Title']], content: '# Full article\n\n[Visible title](https://example.com/actual-target)\n\nTail 🔑' },
].map((event) => signed({ created_at: 1730000000, ...event }));
const events = originals.map((original) => signed({
  created_at: 1730000001, kind: 16,
  tags: [['e', original.id, 'wss://relay.example'], ['p', pubkey], ['k', String(original.kind)],
    ...(original.kind === 0 ? [['a', `0:${pubkey}:`]] : []),
    ...(original.kind === 30023 ? [['a', `30023:${pubkey}:article:日本`]] : [])],
  content: JSON.stringify(original),
}));
events.push(originals[3]);
events.push(signed({ created_at: 1730000002, kind: 30023, tags: [['d', ''], ['published_at', '9007199254740991'], ['title', ''], ['summary', 'Short summary'], ['image', 'https://example.com/unverified.png'], ['t', 'nostr'], ['t', 'nostr'], ['unknown', 'signed extension']], content: 'Entire body\n\u0000\u202Eend' }));
const protectedOriginals = [1, 30023].flatMap(kind => [false, true].map(suffix => signed({
  created_at: 1730000003, kind, tags: [...(kind === 30023 ? [['d', 'protected']] : []), suffix ? ['-', 'extension'] : ['-']], content: 'Protected fixture content',
})));
events.push(signed({ created_at: 1730000004, kind: 30023, tags: [['d', 'protected'], ['-']], content: 'This is not encrypted.' }));
const output = { oracle: '@noble/curves 2.2.0 schnorr + Node SHA256/JSON.stringify', public_fixture_scalar: 3, originals, protectedOriginals, events };
writeFileSync(new URL('./social-vectors.json', import.meta.url), `${JSON.stringify(output, null, 2)}\n`);
console.log(`Generated ${events.length} full event vectors and ${originals.length} signed originals.`);
