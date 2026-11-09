// Independent oracle: no Rust code or event ID/signature helper is imported.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const prefix = resolve(process.argv[2]);
const { schnorr, secp256k1 } = await import(pathToFileURL(resolve(prefix, 'node_modules/@noble/curves/secp256k1.js')));
const rows = JSON.parse(readFileSync(process.argv[3], 'utf8'));
const sha = (data) => createHash('sha256').update(data).digest();
const bytes = (hex) => Uint8Array.from(Buffer.from(hex, 'hex'));
const framedHash = (...parts) => sha(Buffer.concat(parts.flatMap(p => {
  p = Buffer.from(p); const n = Buffer.alloc(8); n.writeBigUInt64BE(BigInt(p.length)); return [n, p];
})));
const parities = new Set();
for (const row of rows) {
  const e = row.event;
  const canonical = JSON.stringify([0, e.pubkey, e.created_at, e.kind, e.tags, e.content]);
  const id = sha(Buffer.from(canonical, 'utf8'));
  assert.equal(id.toString('hex'), e.id, `${row.label} canonical NIP01 ID`);
  assert.equal(schnorr.verify(bytes(e.sig), id, bytes(e.pubkey)), true, row.label);
  const changed = Uint8Array.from(id); changed[31] ^= 1;
  assert.equal(schnorr.verify(bytes(e.sig), changed, bytes(e.pubkey)), false);
  const badSignature = bytes(e.sig); badSignature[63] ^= 1;
  assert.equal(schnorr.verify(badSignature, id, bytes(e.pubkey)), false);
  const descriptor = Buffer.from(row.group_descriptor, 'hex');
  assert.equal(descriptor[0], row.threshold);
  assert.equal(descriptor.length, 35 + descriptor[1] * 65);
  assert.equal(descriptor.subarray(3, 35).toString('hex'), e.pubkey);
  assert.equal(framedHash(row.scheme, descriptor).toString('hex'), row.group);
  if (row.source_secret_fixture) {
    const secret = bytes(row.source_secret_fixture);
    assert.equal(Buffer.from(schnorr.getPublicKey(secret)).toString('hex'), e.pubkey, 'existing identity preserved');
    const compressed = secp256k1.getPublicKey(secret, true);
    assert.equal(descriptor.subarray(2, 35).toString('hex'), Buffer.from(compressed).toString('hex'));
    parities.add(compressed[0]);
  }
  console.log(`${row.label}: independent canonical-ID, BIP340, mutation checks, group descriptor OK`);
}
assert.equal(rows.length, 8);
assert.equal(parities.size, 2, 'both source-key Y parities covered');
console.log(`PASS ${rows.length} complete Nostr events; source compressed-key parities=${[...parities].sort().join(',')}`);
