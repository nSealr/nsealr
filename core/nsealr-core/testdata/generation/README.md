# Local generation vectors

Public fixtures generated on 2026-11-09 with Node 24.22.0, OpenSSL SHA256,
@scure/bip39 2.0.1, @scure/bip32 2.0.1 and nostr-tools 2.23.3. These are
independent implementations of the Rust hash, mnemonic and NIP06 derivation.
The companion lockfile pins their registry integrity values.

Run `node oracle.mjs /path/to/companion` to reproduce the recorded vectors in
the device boundary tests. Patterns deliberately have no secret entropy.

Dice generation hashes exact ASCII digits 1..6, like SeedSigner's
[string-hash method](https://github.com/SeedSigner/seedsigner/blob/995ce5c65df4bd333f61cd3dd992b39a49138a1d/src/seedsigner/helpers/mnemonic_generation.py).
Twelve words use the first 16 hash bytes; 24 use all 32. nSealr requires 50/100
rolls. This differs from SeedSigner's 99-roll 24-word minimum. Fair independent
rolls are an input assumption; hashing does not certify their entropy.

Photo frame hashing is `SHA256("nsealr/photo-frame\0" || final_byte ||
previous_digest32 || rgb565_frame)`, with exactly 1280000 frame bytes and an
initial zero digest. The photo seed is `SHA256("nsealr/photo-seed\0" ||
image_digest32 || hardware_entropy32)`. Both domain strings end with byte 0.
The board owns capture, distinct-frame checks, explicit acceptance and wiping;
these vectors do not qualify image entropy, hardware randomness or remanence.
