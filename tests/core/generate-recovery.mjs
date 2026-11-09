// Independent expected answers. Uses the committed recovery oracle npm lock;
// imports no product code and never reads implementation outputs.
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const root = resolve(process.argv[2], 'node_modules');
const load = path => import(pathToFileURL(resolve(root, path)));
const { entropyToMnemonic, mnemonicToSeedSync } = await load('@scure/bip39/index.js');
const { wordlist } = await load('@scure/bip39/wordlists/english.js');
const { HDKey } = await load('@scure/bip32/index.js');
const { schnorr } = await load('@noble/curves/secp256k1.js');
const hex = bytes => Buffer.from(bytes).toString('hex');
const cases = [];
for (const size of [16, 20, 24, 28, 32]) {
  const mnemonic = entropyToMnemonic(new Uint8Array(size).fill(size), wordlist);
  for (const passphrase of ['', 'café']) {
    const node = HDKey.fromMasterSeed(mnemonicToSeedSync(mnemonic, passphrase)).derive("m/44'/1237'/0'/0/0");
    cases.push({ mnemonic, passphrase, account: 0, private_key: hex(node.privateKey), public_key: hex(schnorr.getPublicKey(node.privateKey)) });
  }
}
process.stdout.write(JSON.stringify({ source: '@scure/bip39 + @scure/bip32 + @noble/curves; committed recovery oracle lock', cases }, null, 2) + '\n');
