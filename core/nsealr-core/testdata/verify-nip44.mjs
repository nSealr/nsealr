// External oracle for deterministic, public-only Rust fixtures.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const [fixtureFile, nodeModules] = process.argv.slice(2);
assert(fixtureFile && nodeModules, "usage: verify-nip44.mjs FIXTURES NODE_MODULES");
const require = createRequire(path.join(path.resolve(nodeModules), "package.json"));
const nip44 = require("nostr-tools/nip44");
const { getPublicKey } = require("nostr-tools/pure");
const packageInfo = JSON.parse(readFileSync(path.join(nodeModules, "nostr-tools/package.json"), "utf8"));
assert.equal(packageInfo.version, "2.23.3");
const rows = readFileSync(fixtureFile, "utf8").trim().split("\n").map(JSON.parse);
assert.equal(rows.length, 64);
for (const [index, row] of rows.entries()) {
  assert.equal(row.case, index);
  const alice = new Uint8Array(32);
  const bob = new Uint8Array(32);
  alice[31] = index + 1;
  bob[31] = index + 65;
  assert.equal(getPublicKey(alice), row.alice);
  assert.equal(getPublicKey(bob), row.bob);
  const aliceKey = nip44.getConversationKey(alice, row.bob);
  const bobKey = nip44.getConversationKey(bob, row.alice);
  assert.deepEqual(aliceKey, bobKey);
  assert.equal(nip44.encrypt(row.plaintext, aliceKey, Buffer.from(row.nonce, "hex")), row.payload);
  assert.equal(nip44.decrypt(row.payload, bobKey), row.plaintext);
}
console.log(JSON.stringify({ passed: true, cases: rows.length, oracle: "nostr-tools@2.23.3", physical_evidence: false }));
