# S02 portable secret boundary and crypto selection

Specification candidate, 2026-10-18. Parent: S02, all five acceptance clauses in
`../../work-items.json`. Input: nSealr/nsealr
`768e8a35ae541f53f5da9c7bea7bf5c577fb474d`; reconciled file hashes are in
`source-inputs.json`. Implementer: secret_execution (Astra xhigh). Independent
specification/final reviewer is assigned by the coordinator. No implementation
starts before specification acceptance. The parent graph is the sole status ledger.

Root independently accepted specification commit
`d9f8c2d4ecdf2efe8c5cd4e87fa4f6f31ca4f3b2` before implementation. Two source-derived
clarifications were accepted during implementation: migrate the constructor in
`apps/desktop-simulator/src/replay.rs` and the test fixture setup in
`crates/nsealr-core/src/review/qr_flow.rs`; reject invalid BIP39 checksums at both
owned insertion paths with `InvalidSeedChecksum`. Deliberately malformed backup
fixtures use crate-private test construction. The existing button/approval model
is preserved for S03 revalidation; local backup functions are not a physical
authorization guarantee. The coordinator owns the independent review record.

## Purpose and limits

Prevent ordinary formatting, implicit copies and direct public field access from
exposing portable-core session secrets. Establish maintained hashing/wiping and a
reproducible algorithm selection foundation for later S03/K01 device integration.
The trusted image remains one address space: opaque types do not resist a hostile
caller able to read memory. Backup is intentionally secret revealing and must have
an explicit local output boundary. This does not implement signing, change the
product catalog, qualify physical erasure, or close any device/release gate.

The current sources contradict the required boundary. `nip19::SecretKey` aliases
a Copy/Debug byte array; `WordIndexes`, `SessionSeedWordIndexes`,
`SessionKeySource`, `StatelessSessionKeyring`, `SessionSourceBackupPayload` and
its flow result expose secret-bearing Debug and/or Clone. Source scalar/index
fields and payload text fields are public. Constructors clone a source out of a
temporary eight-slot keyring, import duplicates a pending source, and backup IO
both emits and returns the secret. `hash.rs` implements custom SHA-256. Move
comments incorrectly call static inaccessibility stronger than physical wiping.
No production entropy provider or crypto signer exists in this checkout.

## Requirements and observable contract

| ID | Requirement and failure behavior | Independent check |
| --- | --- | --- |
| S02-01 | All identified owned secret types have fixed redacted Debug, no Clone/Copy, private secret fields, and no generic public raw-byte dereference. Nonsecret kind/label/count metadata remains inspectable. | Save baseline public-fixture Debug exposure; post-change assert full Debug output; external compile-fail probes for Clone, Copy and field/raw access, plus a valid public API control. |
| S02-02 | Decode/import creates one bounded owned secret; keyring insertion consumes ownership and source extraction moves it. Invalid scalar/seed/label/capacity returns typed error and drops temporary owned input. Rejection, cancellation and errors drop pending input. Legacy eight-slot capacity remains until P01/K01 identity integration. | Existing decode/error/import vectors plus consumed-value compile failure; explicit clear checks on live owned storage. No reads through destroyed Rust objects to claim Drop erasure. |
| S02-03 | Backup payload is non-cloneable, redacted, drop-wiped, with explicit borrowed reveal methods for the local output adapter. The raw builder becomes internal; normal flow returns a payload only after approval. IO borrows it during emission and must not also retain it in the returned result. | Reject/early-approve/error cases produce no payload/output; approved fixture has exact nsec/SeedQR content; format nested result; IO return contains no second payload. This does not repair the full S03 authorization model. |
| S02-04 | Use pinned maintained zeroization for owned scalar, indexes, payload and identified decoding/hash scratch. Replace custom SHA256 with a narrow maintained adapter preserving digest and incremental behavior; no Debug/Clone hasher state. | Independent SHA256 known answers and all affected existing vectors; wipe live storage; feature/dependency audit. Account for caller buffers separately. |
| S02-05 | Qualify maintained algorithm candidates with exact versions/features and independent BIP340/NIP44 expected values; raw event digest must not be rehashed and NIP44 uses unhashed shared-x before HKDF extract. | Re-execute all pinned official vectors in historical probe, including wrong-prehash/hashed-ECDH negatives. Fetch/cache NIP44 JSON by pinned hash, respecting absent redistribution license. |
| S02-06 | Select default candidate based on source review, vectors, no_std and exercised final-link results. Preserve the C backend ABI failure and exact correction. Probe actual new core hashing/wiping linkage too. | Run historical ARM M33/RISC-V probes afresh with logs/ELF hashes/nm; add core final-link probe on RISC-V. First compile target is `riscv32imafc-unknown-none-elf`; ISA/link success is not identification or qualification of an ESP32 assembly. |
| S02-07 | Define fallible entropy ownership/provider contract, no hidden deterministic or weak runtime fallback, and device source-to-binary/invocation/failure proof. Existing caller-byte helpers are clearly deterministic import/conversion, never entropy qualification. | Source audit for provider consumers/FFI; document exact required device procedures. A bounded test provider may prove error propagation but cannot establish entropy quality. |

## Owned files, consumers and delivery

Writable implementation: `crates/nsealr-core/src/{nip19.rs,bip39/mod.rs,seedqr.rs,
hash.rs,text.rs,session/}`, new small secret/entropy modules if the accepted design
needs them, associated public-interface tests, and affected
`apps/desktop-simulator/src/replay/{sources,session_reviews}.rs` consumers. Dependency
pins are in core `Cargo.toml`, workspace `Cargo.lock` and regenerated `vendor/`.
Evidence/probes live here in S02. Historical research source is read-only input;
new evidence must not overwrite its 2026-10-13 record. No canonical graph,
bootstrap, unrelated protocol/authorization or shared-plan edits.

Ordered coherent deliveries: (1) owned secret APIs, redaction, maintained wiping
and hashing with consumer migration; (2) fresh crypto/source/link evaluation and
entropy contract, followed by full affected CI and independent exact-candidate
review. Neither delivery alone closes the parent. Unresolved acceptance stays
open explicitly; evidence may be a later commit referencing the product candidate.

## Owners, copies, memory and log boundaries

| Material | Lifetime / required owners and remaining copies |
| --- | --- |
| Import text / camera / caller entropy | Borrowed local input exists before the core; caller owns and must clear capture, decoder, input and display buffers. Core cannot erase `&str`/`&[u8]` storage or Python/OS copies. Never accepted through Bridge as user identity material. |
| Scalar and mnemonic indexes | Fixed arrays, no allocator; opaque owned decode result, then moved source/keyring. Borrow internally only for encoding/fingerprint. Wipe current owned storage on clear/drop. Eliminate general clone and temporary-keyring copy. |
| Decode and checksum scratch | Bech32 words/bytes, mnemonic word/index/checksum buffers, SeedQR checksum, fingerprint concatenation, hash state: scoped wipe guards or maintained zeroizing hash state. Document any unavoidable borrowed-output buffers at the API. |
| Backup | Deliberate transformed copies (mnemonic/digits/entropy hex/nsec) bounded by existing capacities, wipe on drop. Local adapter may explicitly borrow reveal text. Display/QR framebuffer and optical exposure are device responsibilities; transcript/error/Debug contain no payload. |
| Selected account / review metadata | Public kind/index/label, public key and fingerprints are not secret storage. Labels are user-controlled and may themselves contain sensitive input; redacted Debug for containers avoids relying on label hygiene. Fingerprints leak stable correlation by design; no identity authentication claim. |
| Hash / crypto probe | SHA256 may absorb secret fingerprint/checksum input, so its state is secret-bearing. Probe keys are published fixtures; research array APIs are not product custody interfaces. Future signing/ECDH scratch is a device integration obligation. |

No heap allocation is introduced in core. Fixed arrays are inline, but their
actual address and moves depend on the compiler/caller. Each target must place
the owning session, stack and scratch in qualified internal RAM, exclude external
RAM/DMA/log/crash-dump/swap paths as applicable and inspect the final map/runtime
configuration. This core cannot enforce linker placement. Drop does not execute
on power loss/abort; moves, registers and compiler temporaries can retain copies.
Zeroization narrows exposure and does not prove physical erasure or side-channel
resistance. Do not introduce unsafe post-drop observation tests.

## Maintained dependencies and source authority

Proposed product pins: `zeroize = 1.9.1`, no defaults; `sha2 = 0.11.0`, no
defaults, `zeroize` feature. Verify vendored source and dependency feature graph.
`zeroize` supplies volatile writes/compiler fences but explicitly excludes copies,
registers, memory protection and physical guarantees. Existing generic `FixedStr`
is public text; secret payload wrappers own and wipe it instead of making every
review string secret. Avoid adding `secrecy` solely to wrap a fixed 32-byte array.

Candidate crypto: `k256 = 0.14.0`, defaults off, `schnorr,ecdh`; alternative
`secp256k1 = 0.33.1` / `secp256k1-sys = 0.14.1`, defaults off, `lowmemory`;
`sha2 = 0.11.0`, `hmac = 0.13.0` in isolated probe. Prefer k256 provisionally for
pure-Rust bounded integration if fresh evidence agrees; do not add unused signing
code to the product. Its security notes and integer timing assumptions remain
target obligations. C backend remains viable only with actual ABI/toolchain and
memory/entropy integration proven. No dependency-free preference justifies custom
cryptography. No full NIP44 AEAD qualification is claimed by conversation vectors.

Protocol authority: BIP340 at bitcoin/bips
`927b6de9915c9262615a6399de51b200f81e5aa4`, including test vectors; NIP44 at
nostr-protocol/nips `37db639582d857e12468dcccd99b2c7f1d657da9`; conversation vectors
at paulmillr/nip44 `671a1f04bcfacaf125b0db68adc45bc9ce0e763b` (SHA256 in historical
fetcher). Versioned upstream sources/documentation, not old research conclusions,
determine API semantics. New results record source hashes and tool versions.

Sources inspected: [zeroize](https://docs.rs/zeroize/1.9.1/zeroize/),
[sha2](https://docs.rs/sha2/0.11.0/sha2/),
[k256](https://docs.rs/k256/0.14.0/k256/),
[BIP340](https://github.com/bitcoin/bips/blob/927b6de9915c9262615a6399de51b200f81e5aa4/bip-0340.mediawiki),
[NIP44](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/44.md).

## Entropy contract and unknowns

Device entropy provider must fill a caller-owned bounded destination completely
or return a typed failure; partial bytes are wiped and no key/signature/nonce is
released after failure. No clock, unseeded PRNG, test fixture, silent retry to a
weaker source, weak-symbol default or dynamically substituted provider qualifies.
The profile may explicitly select a qualified OS CSPRNG or DRBG with documented
seeding, health/failure and reseed behavior. An all-zero rejection is not proof of
entropy; scalar rejection sampling is separate from source qualification and must
have a bounded failure path. A seed conversion helper is not a random generator.

Each V01/V02/V03, Q02/Q03 and B02/B03 gate must pin provider/SDK/OS revision and
configuration; trace call sites through Rust/FFI/C/weak aliases/link order/runtime
dispatch into the final ELF/image; inspect symbol/map/disassembly and feature
closure; instrument actual provider invocation on the identified device; inject
unavailable, partial, stuck and interrupted source cases; prove fail-closed output
and absence of unqualified fallback. Record binary hash and instrumentation limits.
S02 can specify and inspect a portable boundary; no physical provider is available
in this checkout and no measured quality/provenance claim follows from statistics.

Unknowns retained: exact first board and memory/linker configuration, stack/RAM,
timing, actual entropy driver, panic/power-loss remanence, DMA/external RAM, local
backup UI/camera lifecycle and all physical side channels. P01 and device gates
own those decisions. They do not justify leaving portable Debug/Clone defects.

## Evidence commands and stop conditions

First preserve public fixture exposure with an external Cargo probe; expected
baseline succeeds in cloning/field access and reveals bytes through formatting.
Then `cargo test -p nsealr-core`, `cargo test -p desktop-simulator`, compile-fail
public API checks, `cargo test -p nsealr-core --features std`, formatting/clippy,
target build, dependency advisory/license checks and `make ci`. Preserve inherited
failures without weakening coverage, license or reproducibility policies. Rerun
only affected checks after changes.

Fresh crypto: `NSEALR_SPIKE_EVIDENCE_ROOT=<S02 evidence directory> python3
research/2026-10-13/crypto/run_spike.py` and `link_probe.py`; versioned scripts
record commands/explicit environment, logs and hashes. Core link probe must use
actual core dependency/feature lock and call hashing plus owned-secret drop/clear;
inspect no undefined symbols and map/sections. Expected C ABI failure must fail for
the documented floating ABI reason; a different failure is inconclusive.

Stop dependent implementation for unresolved security decisions, missing licensed
dependency/fixture provenance, incompatible source/API semantics or failed oracle.
Record findings and amend the brief for independent review if its contract changes.
