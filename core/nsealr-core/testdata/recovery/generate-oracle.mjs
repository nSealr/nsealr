// Test fixtures only. Run with an isolated npm prefix containing the pinned
// packages from oracle-package-lock.json. This script never imports Rust code.
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
const prefix = resolve(process.argv[2]);
const load = (p) => import(pathToFileURL(resolve(prefix, 'node_modules', p)));
const { HDKey } = await load('@scure/bip32/index.js');
const { mnemonicToSeedSync } = await load('@scure/bip39/index.js');
const { schnorr } = await load('@noble/curves/secp256k1.js');
const mnemonics = [
  'leader monkey parrot ring guide accident before fence cannon height naive bean',
  'what bleak badge arrange retreat wolf trade produce cricket blur garlic valid proud rude strong choose busy staff weather area salt hollow arm fade',
];
const rows = [];
for (const mnemonic of mnemonics) {
  for (const passphrase of ['', 'TREZOR', 'caf\u00e9', 'cafe\u0301', ' TREZOR', 'TREZOR ']) {
    const seed = mnemonicToSeedSync(mnemonic, passphrase);
    for (const account of [0, 1, 0x7fffffff]) {
      const path = `m/44'/1237'/${account}'/0/0`;
      const node = HDKey.fromMasterSeed(seed).derive(path);
      rows.push({ mnemonic, passphrase, account, path, private_key: Buffer.from(node.privateKey).toString('hex'), public_key: Buffer.from(schnorr.getPublicKey(node.privateKey)).toString('hex') });
    }
  }
}
// Independently verify this oracle setup against both published NIP06 keys.
if (rows[0].private_key !== '7f7ff03d123792d6ac594bfa67bf6d0c0ab55b6b1fdb6249303fe861f1ccba9a' ||
    rows[18].private_key !== 'c15d739894c81a2fcfd3a2df85a0d2c0dbc47a280d092799f144d73d7ae78add') {
  throw new Error('published NIP06 oracle check failed');
}
process.stdout.write(JSON.stringify(rows, null, 2) + '\n');
