# Project recovery dependency patches

These are nSealr changes to the pinned crates, not upstream behavior or audit
coverage. `patches.json` records original crate archive hashes, source Git
identities, authenticated complete upstream file manifests, and every changed
file's original/patched SHA-256. The checked-in
vendor file checksums cover the patched files; the package hash retains the
original archive identity. The exact diffs are adjacent to this file.

- HMAC 0.13.0: the upstream `zeroize` feature enables digest state/buffer cleanup
  but leaves derived-key pads, long-key hash results and inner-hash arrays in the
  optimized core. The project patch clears these arrays after use when that
  feature is enabled. Recovery uses `Hmac<Sha512>`, not `SimpleHmac`.
- PBKDF2 0.13.0: add a project `zeroize` feature forwarding digest/HMAC cleanup,
  hold the evolving U value in `Zeroizing`, and finalize directly into it.
  Algorithm, iteration count and output bytes are unchanged.
- Unicode normalization 0.1.26: add an `alloc` feature around the existing
  allocating iterator APIs and make TinyVec optional. `std` enables `alloc`.
  With both disabled, the unchanged character decomposition, combining-class
  primitives and Unicode 18 tables need no allocator. Generated QuickCheck
  functions are gated with their iterator API; no table data changed. Core tests
  enable `alloc` only to compare our fixed buffer with the upstream iterator.
- HKDF 0.13.0: keep expansion output blocks and discarded extraction outputs in
  `Zeroizing`; enable HMAC and array cleanup. These are unconditional project
  changes to the private vendor copy. HKDF output and algorithm are unchanged.
  NIP44 uses `Hkdf<Sha256>`. Its official message-key and payload vectors exercise
  these paths. The generic SimpleHmac path is not a product dependency.

`python3 core/nsealr-core/vendor-patches/apply.py` verifies patched source,
or applies it to the exact original versions and updates only the named patched
file checksums. Every unchanged file and the complete file set are checked before
any mutation; a matching edited checksum cannot admit altered source. Cargo's
omission of an upstream `.gitignore` is recorded explicitly. An optional
repository path permits verification in an isolated copy. Unknown, additional,
linked or partially patched source is rejected. Preserve this patch step when
refreshing vendor: stock `cargo vendor` does not implement the project's PBKDF2
`zeroize` or Unicode `alloc` feature split. Bootstrap a fresh upstream vendor set
with those two local feature references temporarily omitted, then apply the
patches before restoring them. Do this in an isolated checkout.

Zeroizing current owned storage and enabled RustCrypto state is not proof that
compiler moves, registers, arithmetic scratch or physical RAM have been erased.
No upstream audit is claimed to cover these local changes or nSealr.
