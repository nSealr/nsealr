# Portable Rust baseline

Ported and checked on 2026-11-09 from nSealr integration commit
`0563d692a3ab9c53903c586cac261c14b1702dd0` into the independent repository based
on `50b9f29`. This is a preserved software baseline, not finished product or
hardware acceptance. The release scope is defined in [product.md](product.md).

## What moved

| Source at the pinned commit | New location |
| --- | --- |
| `crates/nsealr-core` | `core/nsealr-core` |
| `crates/nsealr-threshold` | `core/nsealr-threshold` |
| `crates/nsealr-allocator` | `core/nsealr-allocator` |
| `vendor` | `vendor`, byte-for-byte unchanged |
| `protocols/contracts/v1` | Only 83 referenced fixture inputs in `tests/core/contracts` |
| `ci/core-test-projections.json` | `tests/core/projections.json`, unchanged |
| `ci/project_core_fixtures.py` | `tests/core/project_fixtures.py`, paths adjusted |
| `docs/restart/implementation/S03/vectors.json` | `tests/core/authorization-vectors.json` |
| `docs/restart/implementation/K01/independent-inputs.json` | `tests/core/independent-inputs.json` |
| `docs/restart/implementation/K01/evidence/semantic-matrix.json` | `tests/core/semantic-matrix.json` |
| `docs/restart/implementation/K01/evidence/metadata-boundaries.json` | `tests/core/metadata-boundaries.json` |
| `packages/core/src/test-fixtures/nip44-official-vectors.json` | `tests/core/nip44-official-vectors.json` |

The copied JSON files are unchanged expected inputs/answers, not execution logs.
Their historical source labels describe provenance, not the new release scope.
The data projector only selects fields and formats Rust test literals. It never
calls the production parser, review renderer, canonicalizer or signer. Generated
values are included under `cfg(test)`. Python 3 is still a build prerequisite.

The Pi fixture engine and all old applications, historical evidence trees and
process documents were omitted. No retained crate calls that engine. Its unused
local lockfile entry was removed; all third-party dependency pins are unchanged.

Changes to retained crates are limited to fixture/build/verifier paths, comments
and documentation. Two trivial libtest/HashMap harness assertions were removed;
behavioral, adversarial and compile-fail checks were retained. Production Rust
logic, public APIs, fixed bounds, cryptographic operations and failure handling
are unchanged.

## Dependencies and independent answers

Rust is pinned to 1.95.0. Cargo uses the checked-in vendor tree offline, including
the existing recovery and FROST cleanup patches. Vendor Git tree:
`51d2609d75c13032ed1380c84932dd578c60ed4e`.
All 83 packages, 2,939 checksummed files and 83 checksum manifests were retained,
including upstream license files. The project MIT license is unchanged.

FROST remains [ZcashFoundation/frost at 0966bd15](https://github.com/ZcashFoundation/frost/tree/0966bd1529aa062ad3b621af99e277f976b1c0f0).
The exact local patches and authenticated original/patched file maps remain in
`core/nsealr-threshold/patches` and `core/nsealr-core/vendor-patches`. Upstream
audit coverage does not cover these local changes or this product.

Recovery inputs retain published BIP39, BIP32, SeedQR, Unicode and independently
generated NIP06 answers with pins/licenses in
[the recovery corpus](../core/nsealr-core/testdata/recovery/README.md).
NIP44 uses the retained official reference vectors; public-message and private-
message inputs retain their independent oracle scripts and source annotations.
Threshold verification uses the retained exact npm lock for Noble curves 2.4.0,
Node's SHA-256 and independent NIP01 serialization, without importing Rust code.

## Checks on this tree

Environment: Apple Silicon macOS; Rust 1.95.0, Python 3.12.15, Node 24.22.0.
Dependencies were resolved offline. The independent npm oracle was installed
with `npm ci --ignore-scripts --offline` using its committed package and lock.

| Command or check | Observed result |
| --- | --- |
| `cargo test --workspace --offline --locked` | 349 executable tests and 16 compile-fail doc tests passed |
| `cargo test --workspace --all-features --release --offline --locked` | Same 365 checks passed with optimization |
| `cargo clippy --workspace --all-targets --all-features --offline --locked -- -D warnings` | Passed |
| `cargo build --workspace --lib --release --offline --locked --target riscv32imafc-unknown-none-elf` | All three libraries built with their default `no_std` configuration |
| `core/nsealr-threshold/testdata/verify-vendor.py PINNED_FROST_CHECKOUT` | Pinned source maps, exact cleanup patch and complete vendor Git/checksum closure passed |
| `core/nsealr-threshold/testdata/test_verify_vendor.py PINNED_FROST_CHECKOUT` | 7 adverse admission tests passed |
| `core/nsealr-core/vendor-patches/test_apply.py` | 8 recovery patch admission tests passed |
| `cargo run --offline --locked -p nsealr-threshold --example public_vectors`, then `verify-nostr.mjs PREFIX OUTPUT` | 8 complete events passed independent ID/signature/mutation/group checks; both source-key parities covered |

The threshold verifier scripts are under `core/nsealr-threshold/testdata` and
require Python 3.11+ and a clean FROST checkout at the pin above. Cargo itself
needs no checkout.
The default and optimized runs include whole-Layout zero-at-free capture under
the bounded host allocator, cancellation/replay/entropy/approval failures, DKG,
restored shares, recovery vectors and malformed input boundaries.

The first compile found missing historical fixture includes. Those inputs were
relocated without changing their bytes or expected answers before the successful
checks above. No device was accessed, flashed or measured during this port.

## Size and remaining coupling

These are physical Rust line counts, including comments, blank lines, inline
tests and the word list; they are navigation/ownership counts, not runtime size.

| Area | Files | Rust files | Rust lines | Total bytes |
| --- | ---: | ---: | ---: | ---: |
| Owned core | 93 | 66 | 31,855 | 2,792,112 |
| Owned threshold | 18 | 6 | 2,115 | 138,865 |
| Owned allocator | 4 | 2 | 349 | 16,001 |
| Relocated test corpus/projector | 90 | 0 | 0 | 303,868 |
| Vendored upstream dependencies | 3,022 | 2,093 | 722,626 | 27,581,905 |

Core still exposes old serial/scaffold flows, policy changes, multiple profile
types, and supported semantic kinds beyond the selected v1 workflows. Their
tests exercise real boundaries and were preserved, not promoted to product
requirements. The existing review engine still requires complete traversal;
the new summary/optional-detail policy is not implemented by this relocation.
An adapter must admit only the selected product workflows and provide trusted
display, input, clock and entropy; a host transcript is not approval authority.

Threshold is a crypto/session foundation, not a complete ceremony or optical
wire protocol. Authenticated peers, confidential DKG delivery, backup/recovery
UI, a qualified global allocator and actual device integration remain necessary.
Threshold signing does not provide threshold ECDH or NIP44 private messaging.
Do not use public fixture keys or fixture authority implementations in firmware.

Host tests and a RISC-V library build establish no camera/display/erase/radio,
physical entropy, stack/heap/timing or USB-disconnected result. None of those
gates, independent product security review or finished workflow acceptance is
claimed here.
