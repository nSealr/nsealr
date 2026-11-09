// Public deterministic fixtures only. Never use these values for an identity.
// Usage: node oracle.mjs /path/to/companion (with its locked dependencies installed).
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
const require = createRequire(resolve(process.argv[2], 'package.json'));
const { entropyToMnemonic, mnemonicToSeedSync } = require('@scure/bip39');
const { wordlist } = require('@scure/bip39/wordlists/english.js');
const { HDKey } = require('@scure/bip32');
const { getPublicKey } = require('nostr-tools/pure');
const hash = (...parts) => createHash('sha256').update(Buffer.concat(parts.map(p => typeof p === 'string' ? Buffer.from(p) : p))).digest();
function identity(words, entropy) {
  const mnemonic = entropyToMnemonic(entropy.subarray(0, words === 12 ? 16 : 32), wordlist);
  const key = HDKey.fromMasterSeed(mnemonicToSeedSync(mnemonic)).derive("m/44'/1237'/0'/0/0").privateKey;
  return { words, entropy: entropy.toString('hex'), mnemonic, public_key: getPublicKey(key) };
}
const dice = [[12, '123456'.repeat(8) + '12'], [24, '654321'.repeat(16) + '6543']]
  .map(([words, rolls]) => ({ rolls, ...identity(words, hash(rolls)) }));
const digest = Buffer.from(Array.from({ length: 32 }, (_, i) => i + 1));
const hardware = Buffer.from(Array.from({ length: 32 }, (_, i) => 255 - i));
const mixed = hash('nsealr/photo-seed\0', digest, hardware);
const frame = Buffer.alloc(1280000, 0x5a);
const first = hash('nsealr/photo-frame\0', Buffer.from([0]), Buffer.alloc(32), frame);
const final = hash('nsealr/photo-frame\0', Buffer.from([1]), first, frame);
console.log(JSON.stringify({ dice, photo: [12, 24].map(words => identity(words, mixed)),
  frame: { first: first.toString('hex'), final: final.toString('hex') } }, null, 2));
