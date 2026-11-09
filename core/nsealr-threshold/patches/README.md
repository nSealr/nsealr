# Pinned ZF cleanup patch

Observed 2026-11-09. Upstream:
https://github.com/ZcashFoundation/frost/tree/0966bd1529aa062ad3b621af99e277f976b1c0f0

`frost-core-zeroize.patch` applies to that commit's `frost-core` directory.
`frost-core-original-hashes.json` retains SHA-256 of every original changed
source file. `vendor-admission.json` additionally pins every retained file in all
three FROST packages and the ChaCha20 archive, including original/patched hashes
for the changed files. Local Cargo checksums are checked against these
independent maps; modifying source and its checksum together cannot admit it.
The three FROST packages include upstream root license texts, which cargo vendor
did not include automatically. No existing dependency was upgraded.

FROST source, README, changelog, tests, vectors and license hashes map to immutable
Git blobs through `upstream_git_paths`. Cargo generates each normalized
`Cargo.toml`; the maps retain both its generated hash and the upstream manifest
hash. These three generated files were independently reproduced with Cargo
1.95.0 using `cargo vendor --offline` and an isolated manifest containing:

```toml
[package]
name = "threshold-vendor-normalization"
version = "0.0.0"
edition = "2021"
[workspace]
[dependencies]
frost-secp256k1-tr = { git = "https://github.com/ZcashFoundation/frost", rev = "0966bd1529aa062ad3b621af99e277f976b1c0f0", default-features = false }
chacha20 = { version = "=0.10.2", default-features = false, features = ["rng", "zeroize"] }
```

The empty `src/lib.rs` and manifest belong in a workspace temporary directory.
Run `cargo vendor --manifest-path <directory>/Cargo.toml --offline <output>`.
The normal project manifest cannot bootstrap unpatched registry sources because
the recovery dependencies intentionally require their local patch features.

ChaCha20 0.10.2 comes from
https://static.crates.io/crates/chacha20/chacha20-0.10.2.crate,
SHA-256 `65c35e4b699c7e15ccbe7ee35c005e4fc0a278d22238a2857e6ce2dadeda1b06`.
All 25 regular archive files are retained unchanged. The map records this archive
identity separately from local per-file checksums.

## Admission and tracked source closure

Load the workspace's `scripts/env.sh`, then run these commands from the repository
root. Python 3.11 or later supplies the standard-library TOML reader; the recorded
workspace tests use Python 3.12:

```sh
python3 core/nsealr-threshold/testdata/verify-vendor.py <clean-pinned-frost-checkout>
python3 core/nsealr-threshold/testdata/test_verify_vendor.py <clean-pinned-frost-checkout>
```

The verifier checks the clean pinned reference, complete authenticated maps,
exact cleanup diff, dependency manifests, lockfile identities and Cargo source
replacement. It also checks every vendored package's file/checksum set and Git
tracking. Failures remain enforced under `python3 -O`; verification never
rewrites checksums. Whole-tree closure checks tracking and local checksums for
other dependencies; their upstream provenance is outside this threshold map.

The original tracked tree omitted `vendor/thiserror/build/probe.rs` because its
directory matched a build-output ignore pattern. That exact 844-byte original
file is now explicitly tracked. It was recovered from thiserror 2.0.21's archive
https://static.crates.io/crates/thiserror/thiserror-2.0.21.crate,
archive SHA-256 `09e52cb86a36cede5cb101bf8908837b3e4c6e5e59fe7fd85c23fb56200d189e`;
file SHA-256 `8df55471d6b75623d423b17ebbf493335ee66140d1ddd232c88db3e59f61298c`.
Its existing Cargo checksum agrees. Fresh-checkout offline tests must pass;
another local ignored copy is insufficient.

Acceptance requires unchanged authenticated bytes to pass; changed source plus
matching checksums, file-set changes, missing Git files, dirty reference and
source/lockfile substitutions to fail without mutations; and the committed tree
to pass threshold tests in a fresh checkout without network access.

Inspection found secret-bearing nonce input/serialized share Vec allocations,
dealer polynomial Vec allocations, and temporary DKG polynomial copies freed
without clearing. Some scalar cleanup implementations used ordinary zero
assignment without zeroize's volatile guarantee. This patch adds the selected
scalar's `Zeroize` trait bound, calls real scalar zeroize, guards those byte and
coefficient vectors with `Zeroizing`, avoids secret polynomial reallocation,
and clears temporary scalar serialization buffers. It changes no mathematical
operation, cryptographic transcript, point/scalar encoding, or final signature.
Other FROST ciphersuites have not been qualified against the added scalar bound.

Lost-share repair additionally gives `Delta` and `Sigma` a `Zeroize` implementation
for guarded local custody, and guards RTS random coefficients and scalar sums.
The public APIs, equations and serialized contribution bytes are unchanged.

The host allocator test probes known public fixture key/share patterns before
scalar/byte-vector sized allocations are freed, in debug and optimized builds.
It does not prove removal of every scalar copy, stack/register spill, compiler
copy, camera frame, physical RAM remanence, or uninspected upstream path. The
wrapper does not expose upstream SigningNonces serialization. No memory snapshot
or restored round is safe. Review this patch independently before production;
regenerating vendor must reapply it and update checksums reproducibly.

Upstream NCC audit coverage described in the pinned root README is for older
0.6.0 code and explicitly excludes `frost-secp256k1-tr`. It does not audit this
3.0.0 BIP340 integration or this patch.

ChaCha20 0.10.2, with `rng` and `zeroize`, is used instead of rand_chacha because
its RNG core and output buffer zeroize on drop. Its included changelog records
0.10.2's SSE2/SSE4.1 correction:
https://github.com/RustCrypto/stream-ciphers/pull/580
