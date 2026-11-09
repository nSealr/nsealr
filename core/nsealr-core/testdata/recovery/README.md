# Public recovery vectors

Observed 2026-11-09. These seeds and passphrases are public fixtures. Never use
them for an identity with value or privacy requirements.

| File | Independent source and extraction |
| --- | --- |
| `bip39-english.json` | All 24 English entries of [Trezor vectors.json](https://github.com/trezor/python-mnemonic/blob/b57a5ad77a981e743f4167ab2f7927a55c1e82a8/vectors.json), unchanged. All use `TREZOR`; compare the published 64-byte seed. Other languages are outside this English mnemonic importer. |
| `bip32-published.json` | All 17 nodes in [BIP32 vectors 1–4](https://github.com/bitcoin/bips/blob/a34f044bb8d5cd684d7a742d2f6483c14b719046/bip-0032.mediawiki). Decode published Base58Check xprv/xpub values, validate their checksums, extract scalar, chain code and compressed point; no derivation computes expected values. Includes both leading-zero vectors. Extended-key text parsing is not an exposed API. |
| `seedqr-published.json` | All nine [SeedQR vectors](https://github.com/SeedSigner/seedsigner/blob/995ce5c65df4bd333f61cd3dd992b39a49138a1d/docs/seed_qr/README.md): copy mnemonic/digits, evaluate published Python byte literals, render those exact bytes as hex. Includes NUL, LF, CR, CRLF and high-bit bytes. |
| `unicode18-nfkd.txt` | All 20,171 rows/five columns of [Unicode 18 NormalizationTest.txt](https://www.unicode.org/Public/18.0.0/ucd/NormalizationTest.txt), comments/part labels removed. Every column must normalize to column five. Original SHA-256 `25a50d816764b04abfb4a646d3eb2b2a803284c3873d9a06757b94fe4513dde3`. License is adjacent. |
| `nip06-scure.json` | `generate-oracle.mjs` uses independent JavaScript @scure BIP39/BIP32 and @noble secp256k1, with the adjacent npm integrity lock. Two [published NIP06 mnemonics](https://github.com/nostr-protocol/nips/blob/b587c619c2ea662d40b40976aeccf6ac8d6ba9eb/06.md), each at accounts 0/1/2147483647 with six passphrases: empty, `TREZOR`, composed/decomposed café, leading/trailing significant space. The generator asserts both published empty-passphrase account-zero private keys before emitting 36 rows. |

To reproduce the JavaScript oracle, install `@scure/bip32@2.4.0` and
`@scure/bip39@2.4.0` with scripts disabled in an isolated workspace directory,
compare the resulting npm lock's versions/integrities, and run
`node core/nsealr-core/testdata/recovery/generate-oracle.mjs <npm-prefix>`.
No implementation-under-test output is used as an expected value.

The additional exhaustive Unicode test compares every Unicode scalar and several
multi-character reorderings with the library's allocating iterator. This checks
our buffer/ordering glue; the official corpus supplies independent expected
normalization output. It does not qualify display or input on a physical device.
