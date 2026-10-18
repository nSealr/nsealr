# Maintained crypto selection and fresh evidence

S02-04/05/06, 2026-10-18. Product candidate:
`b64afa7a8e3dd9e0e155eea55bf402715ddf32ad`. This is a portable implementation and
integration-candidate decision, not permission to use a real identity or a device
qualification. Research runners/sources were reconciled against `source-inputs.json`
and executed afresh; October 13 results are not counted as new acceptance.

## Decision

The product replaces custom SHA256 with **sha2 0.11.0**, defaults off and
`zeroize` enabled, and custom owned-buffer wiping with **zeroize 1.9.1**, defaults
off. Source inspection confirms enabled Drop for the SHA core and block buffer.
The public adapter exposes no state serialization, Debug or Clone. Registry
checksums, exact added package licenses/manifests and target features are in
`evidence/dependencies.json` and `evidence/integration/cargo-tree-core.log`.
Existing unrelated lock versions were retained. Full `cargo deny check` passes.

Select **k256 0.14.0**, defaults off, `schnorr,ecdh`, as the maintained candidate
for the next engine integration. It passes the needed raw APIs/vectors and
exercised no-allocator final links without a C ABI boundary; its observed probe
sections are smaller than the alternative below. This is an engineering preference
subject to the exact target's integer timing, memory and performance evidence.
No new unused signing API is added to the product, whose protocol remains disabled.

Retain **secp256k1 0.33.1 / secp256k1-sys 0.14.1**, defaults off, `lowmemory`, as
the maintained C alternative. The required explicit ABI fix and memory/FFI
qualification make it less convenient for the first portable integration, not
cryptographically disqualified. The isolated probe also pins sha2 0.11.0 and hmac
0.13.0. CC0-1.0 applies to libsecp and its bindings; it is research-only here and
is not silently added to the product's dependency policy. k256/sha2/hmac/zeroize
are Apache-2.0 OR MIT; vendored product dependencies retain original notices.

Do not infer whole-backend temporary erasure from a zeroizing key object. Inspected
k256 `SigningKey` and elliptic-curve `SharedSecret` wipe on Drop, but `sign_raw`
uses nonce derivation arrays and `NonZeroScalar` temporaries without a universal
drop-wipe guarantee (`NonZeroScalar` provides `Zeroize`, not Drop). The C binding
also exposes Copy secret/shared-secret types and explicitly non-secure erase
helpers. Before real-key admission, K01 and each custody implementation must
inventory backend scratch, minimize copies, choose reviewed mitigation/upstream
changes where required, and measure relevant target memory behavior. A wrapper
cannot erase temporaries it never owns. This finding is not masked by the vector
pass or by Rust ownership and is not a physical-erasure claim.

## Independent protocol oracles

For each provider the fresh host run passes **19 BIP340 verification cases**
(9 valid, 10 invalid), **8 exact signature cases**, and **43 NIP44 conversation
cases** (35 valid, 8 invalid). Expected values come from pinned upstream fixtures,
not from the implementation under test. The two-provider comparison is additional
evidence, not the oracle itself. See `evidence/crypto/vectors.log`, `fixtures.log`
and `runs.json` for exact commands, versions, working directories and log hashes.

The raw 32-byte BIP340 message path is exercised against the official vector.
The negative test demonstrates that the high-level k256 `Signer` produces a
different signature by hashing the event digest again; that result fails raw
verification. The NIP44 negative test passes libsecp's default hashed ECDH output
through HKDF extract and proves it differs from the independent conversation key.
Both correct wrappers use the unhashed shared x-coordinate followed by HKDF
extract with `nip44-v2`. This is not full NIP44 encryption/decryption qualification.

Source authority: [BIP340](https://github.com/bitcoin/bips/blob/927b6de9915c9262615a6399de51b200f81e5aa4/bip-0340.mediawiki),
[NIP44](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/44.md),
[k256 0.14.0](https://docs.rs/k256/0.14.0/k256/),
[libsecp binding](https://docs.rs/secp256k1/0.33.1/secp256k1/).
Targeted inspected registry source hashes are in `evidence/source-review.json`.
BIP340 fixture SHA256 is
`34c9d1d9c3a88d524bc80778540dc43f8306ec249a7485293063c376db851c2d`.
NIP44 fixture commit `671a1f04bcfacaf125b0db68adc45bc9ce0e763b`, SHA256
`269ed0f69e4c192512cc779e78c555090cebc7c785b609e338a62afc3ce25040`, is fetched/hash
checked locally. Its standalone JSON has no explicit redistribution license;
neither it nor generated constants are included in this delivery.

## Compile and final-link evidence

Rust 1.95.0, LLVM 22.1.2, Clang 19.1.7, host x86_64 Linux; precise tool outputs
are saved. Both candidates compile `no_std` rlibs for
`thumbv8m.main-none-eabihf` and `riscv32imafc-unknown-none-elf`. Exercised final
links invoke signing, verification and conversation-key derivation, have no
allocator and pass `nm -u` with no unresolved symbols plus readelf/size inspection.

| Provider / target | .text bytes | .rodata bytes | .bss bytes |
| --- | ---: | ---: | ---: |
| k256 / ARM M33 | 42,486 | 1,160 | 97 |
| k256 / RISC-V | 57,392 | 1,160 | 97 |
| libsecp lowmemory / ARM M33 | 51,284 | 4,724 | 400 |
| libsecp lowmemory / RISC-V, corrected ABI | 65,502 | 4,756 | 400 |

The uncorrected C/RISC-V final link exits **101** with `different floating-point
ABI`. The successful rlib compile had not detected it. The preserved failing log
is `evidence/crypto/link-libsecp-riscv32imafc-unknown-none-elf.log`; the corrected
run explicitly sets `CC_riscv32imafc_unknown_none_elf=clang` and
`CFLAGS_riscv32imafc_unknown_none_elf='-mabi=ilp32f -march=rv32imafc'`.
`link-runs.json` records both commands, environment overrides, logs and ELF hashes;
`link-verdict.json` requires the intended failure reason and every corrected pass.

The **actual new core**, separately linked on RISC-V with hashing, scalar intake,
keyring clear/drop exercised, reports .text 15,056, .rodata 328, .bss 32 and zero
undefined symbols. See `evidence/integration/commands.json` and `core-*.log`.
These link-only files lack startup, board memory maps and entropy; never flash
them. Local generated ELF files are hash-bound but not published as firmware.
Section counts are probe-specific and are not total application flash or peak
stack/RAM. No processor execution, speed, side-channel or physical test occurred.

RISC-V is the first compile/link contract used here. It does not select an exact
commercial assembly or qualify Xtensa, Pi Linux, P4 peripherals or an ARM board.
Every actual implementation/release still owns its full binary, ABI, memory,
timing, custody and entropy gates. See `entropy-contract.md` for the provider
provenance/failure contract; this probe deliberately takes explicit public fixture
auxiliary bytes and has no qualified runtime entropy provider.

## Reproduce

From repository root, with pinned toolchain/targets and documented Clang available:

```sh
python3 docs/restart/implementation/S02/probes/collect.py
NSEALR_SPIKE_EVIDENCE_ROOT="$PWD/docs/restart/implementation/S02/evidence/crypto" python3 research/2026-10-13/crypto/run_spike.py
NSEALR_SPIKE_EVIDENCE_ROOT="$PWD/docs/restart/implementation/S02/evidence/crypto" python3 research/2026-10-13/crypto/link_probe.py
```

These commands overwrite local result logs; preserve the committed record before
capturing a new run. Product builds use the vendored locked graph. The separate
historical research workspace resolves its locked registry graph from an isolated
working directory and fetches the pinned non-redistributed NIP44 fixture.
