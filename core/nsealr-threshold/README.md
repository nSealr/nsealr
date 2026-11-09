# nsealr-threshold

A no_std + alloc cryptographic/session foundation for the ESP32-P4 Nostr
threshold product. It is not the finished group ceremony, backup interface,
optical protocol, or device review implementation.

The selected primitive is ZF `frost-secp256k1-tr` 3.0.0 at
`0966bd1529aa062ad3b621af99e277f976b1c0f0`, with the local cleanup patch described
in `patches/README.md`. Signing uses ordinary upstream `sign`/`aggregate` with
no additional Taproot tweak. DKG's returned, already tweaked group key is the
identity. Existing-key dealer splitting preserves the imported key's exact
compressed point and Nostr x-only identity. A dealer's full key existed and may
still exist elsewhere. DKG makes a new identity.

## Acceptance of this foundation

- Dealer 2-of-3 and 3-of-5, bounded consuming DKG, and fresh share backup/restore
  produce valid standard Nostr signatures, independently verified outside Rust.
- Every signer receives a complete core `EventTemplate`; the core computes its
  full 32-byte ID using the selected actual group key. No hash-only signing API.
- Full group descriptor, selected participant set, session and event ID are bound
  into a common immutable `RoundIntent`. A local owner epoch and deadline bind
  the physical review capability. Full peer commitments bind the second round.
- One volatile nonce owner emits a commitment once and is taken before any
  signing attempt. Errors, cancellation, lock, group selection, expired clocks,
  changed intent, commitment substitution and replay cannot reuse that owner.
- A qualified fallible 32-byte seed precedes upstream infallible RNG operations.
  ChaCha20Rng clears its state/output buffer on drop. The signer rejects an
  immediately repeated seed and uses a distinct owner-epoch ChaCha stream for
  nonconsecutive repeats during that owner's lifetime. Source uniqueness after
  reset still needs qualified hardware entropy; software cannot prove it.
- Backup `NST1` is at most 460 bytes: magic, participant ID, long-term share,
  full public descriptor and scheme-bound SHA-256 checksum. It contains no
  transient nonce or round. Restore requires independently confirmed expected
  group and participant IDs and verifies the secret share's public point.

## Trusted adapter contract

`ReviewAuthority::review` must apply semantic admission, display the complete
unchanged event and actual group descriptor, confirm all selected participants,
and obtain fresh physical consent before calling `ReviewIntent::approve`.
`check_live` must compare that same authority/context on every call and reject
cancel, policy/group changes, lock, reset, timeout or revoked physical authority.
`admit_round` must authenticate every participant's commitment and admit the
complete immutable transcript. A host grant, QR checksum or matching digest
cannot supply this authority. Time is trusted monotonic milliseconds.

Use exactly one `Signer` owner through its firmware lifetime, including lock and
reload. Do not clone memory, restore snapshots, or serialize its private state.
After emitting a public share the adapter may retain a bounded public response
for retransmission; it must not call `sign` again to retry.

Dealer delivery and DKG require an authenticated, consistent broadcast view.
DKG round-two `Delivery` contains a secret polynomial share and additionally
requires confidential participant-to-participant delivery. The wrapper binds
ceremony, threshold, participants, sender and recipient and consumes each owner
on transition or failure. It does not establish secure channels or participant
identities. Do not put DKG secret deliveries in ordinary companion traffic.

Secret backup export is a separate local physical-consent interface; clear its
camera/display copies and independently confirm recovery. Its checksum is for
transcription damage, not peer authentication or encryption.

## Bounds and remaining product work

Groups contain 2..=5 participants, threshold 2..=group size; one pending round and
at most five selected signers. The initial maximum round lifetime is five minutes.
Core event parsing limits still apply. The adapter must bound optical decoders
before constructing upstream packages; no wire parser is provided here.

The firmware must supply and qualify its bounded allocator before linking the
new alloc-dependent crate. OOM aborts; there is no allocation-error fallback or
secret-state resume. Host allocator measurements and RISC-V library builds are
recorded separately from pending P4 stack/heap high-water and timing tests.
The [allocator contract](allocator-contract.md) requires global coverage of
caller containers and documents the wipe-before-free adapter and raw heap proof.

The integration still needs complete physical group/event/round review, peer
authentication, bounded optical encodings, practical local secret recovery,
interrupt/reset/power-loss behavior, an independent real peer, and distinct
security review. No device, audit, cross-version Bifrost interoperability,
community endorsement, threshold ECDH/NIP-44 or complete-product claim is made.

## Reproduce

From the repository root, with Rust 1.95.0, Python 3 and the bare-metal Rust
target installed, run:

```sh
cargo test --locked --offline -p nsealr-threshold
cargo test --locked --offline --release -p nsealr-threshold --test allocation -- --nocapture --test-threads=1
cargo build --locked --offline --release -p nsealr-threshold --target riscv32imafc-unknown-none-elf
cargo run --locked --offline -p nsealr-threshold --example public_vectors > public-vectors.json
```

Install the exact oracle lock in an isolated workspace npm prefix (copy
`testdata/oracle-package*.json` to `package*.json`, then `npm ci --ignore-scripts`).
Run `node core/nsealr-threshold/testdata/verify-nostr.mjs PREFIX public-vectors.json`.
All example keys and approvals are public deterministic test
fixtures and must never be wired into production.
