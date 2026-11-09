# Public recovery answers

These are public test keys and phrases. They are never production identities.

`nip06-scure.json` retains 36 independent answers from the pinned @scure BIP39/
BIP32 and @noble secp256k1 implementations. Inputs include two published
[NIP06 phrases](https://github.com/nostr-protocol/nips/blob/b587c619c2ea662d40b40976aeccf6ac8d6ba9eb/06.md),
accounts 0, 1 and 2147483647, and empty, ASCII, composed/decomposed Unicode and
significant-space passphrases. The exact npm integrity lock and original
generator are adjacent. No Rust implementation output defines an expected key.

`seedqr-published.json` retains all nine published
[SeedQR vectors](https://github.com/SeedSigner/seedsigner/blob/995ce5c65df4bd333f61cd3dd992b39a49138a1d/docs/seed_qr/README.md).
The mnemonic, decimal digits and compact entropy bytes were copied from those
vectors, including NUL, LF, CR, CRLF and high-bit values.

`tests/core/recovery-all-counts.json` adds 12/15/18/21/24-word recovery cases with
empty and Unicode passphrases. Reproduce it with the same npm lock and
`node tests/core/generate-recovery.mjs NPM_PREFIX`. That generator imports only
the independent libraries and uses no product source or outputs.
