# BIP340 / NIP44 crypto feasibility experiment

Research only. This crate has separate workspace membership (`[workspace]` in its own Cargo.toml), has `publish=false`, uses only public test keys and does not implement a signer application. It has no custody, authorization, board startup, memory map, entropy or peripheral integration. Never flash the link-only probe as firmware.

The experiment compares exact `k256 0.14.0` and `secp256k1 0.33.1` (`secp256k1-sys 0.14.1`) releases. It executes independent vectors on the host, then compiles and links exercised Schnorr signing/verification and secp256k1 ECDH plus NIP44 HKDF extract for ARM M33 and RISC-V targets. It does not implement full NIP44 encryption/decryption.

## Reproduce

Requirements: Python 3, rustup, Clang 19.1.7, GNU `nm`, `size`, `readelf`. The captured run used Rust 1.95.0 / LLVM 22.1.2 on x86_64 Linux. Install the explicit toolchain and target libraries if absent:

```sh
rustup toolchain install 1.95.0 --profile minimal
rustup target add --toolchain 1.95.0 thumbv8m.main-none-eabihf riscv32imafc-unknown-none-elf
python3 run_spike.py
python3 link_probe.py
```

Run from this directory. The runners resolve their own project path and execute Cargo from a temporary directory under `/tmp`, passing the absolute `--manifest-path` and explicitly retaining `target/` here. This avoids inheriting the product repository's `.cargo/config.toml` source replacement; separate workspace membership alone does not isolate [Cargo configuration discovery](https://doc.rust-lang.org/cargo/reference/config.html#hierarchical-structure). The product configuration is unchanged. User-level Cargo configuration and environment variables still apply. The runners record each command, effective working directory and explicit overrides, and write logs/JSON under `evidence/`; `NSEALR_SPIKE_EVIDENCE_ROOT` optionally overrides that output directory. Cargo downloads only locked dependencies. `run_spike.py` first fetches NIP44 vectors from an exact commit and verifies their SHA256, or uses the verified cached copy. After dependencies/fixtures/toolchains are cached the commands need no network. Do not run `cargo test --all-features`: the intentionally freestanding binary requires exactly one crypto provider.

The link experiment intentionally preserves a failing RISC-V C ABI configuration, then checks a corrected configuration. Its exit status is successful only if the expected ABI failure is observed and all corrected links succeed. A newer C toolchain that fixes automatic ABI selection will require updating this expected-failure check, not pretending the old failure still happened. The host test runner exits nonzero on any failed command. Every successful link must also pass `readelf`, `size` and `nm` inspection; nonzero inspection exits or any output from `nm -u` fail the link runner.

For a manual corrected libsecp RISC-V link, start in this directory and run the same isolated-Cargo pattern:

```sh
spike_dir="$PWD"
spike_cargo_cwd="$(mktemp -d /tmp/nsealr-crypto-cargo-XXXXXX)"
(
  cd "$spike_cargo_cwd" || exit 1
  CARGO_TARGET_DIR="$spike_dir/target" \
  CC_riscv32imafc_unknown_none_elf=clang \
  CFLAGS_riscv32imafc_unknown_none_elf='-mabi=ilp32f -march=rv32imafc' \
  cargo +1.95.0 rustc --manifest-path "$spike_dir/Cargo.toml" \
    --locked --release --bin freestanding \
    --no-default-features --features libsecp,link-probe \
    --target riscv32imafc-unknown-none-elf -- -C link-arg=--entry=_start
)
spike_link_status=$?
rmdir "$spike_cargo_cwd"
test "$spike_link_status" -eq 0
```

## Recorded outcome and limits

Both providers pass all 19 BIP340 verification cases (9 valid/10 invalid), all 8 exact signing cases, and all 35 valid/8 invalid NIP44 conversation-key derivation cases. Negative checks catch double-hashing a Nostr event ID via k256's high-level signing API, and using libsecp's default hashed ECDH output rather than NIP44's raw x-coordinate. Raw APIs are deliberately contained in this research wrapper, not proposed as the public application API.

Both providers compile `no_std` rlibs on both targets. Both also link without an allocator after the explicit C ABI fix; `nm -u` reports no unresolved symbols. **An rlib success did not detect the ABI failure.** Runtime standard-library features remain disabled; host build dependencies may use `std`.

| Provider / target | `.text` | `.rodata` | `.bss` |
|---|---:|---:|---:|
| k256 / thumbv8m.main-none-eabihf | 42486 | 1160 | 97 |
| libsecp lowmemory / thumbv8m.main-none-eabihf | 51284 | 4724 | 400 |
| k256 / riscv32imafc-unknown-none-elf | 57392 | 1160 | 97 |
| libsecp lowmemory / riscv32imafc-unknown-none-elf, corrected ABI | 65502 | 4756 | 400 |

These are this experiment's section sizes with size optimization/LTO and selected features. The table excludes additional recorded sections and is not a total flash estimate. The 97-byte output buffer is probe data. No target execution, stack/peak RAM, runtime speed, constant-time behavior, peripheral/DMA effects or physical attack resistance was measured. An ARM ISA build does not qualify an STM32U5 board; this RISC-V build does not qualify a P4 firmware image. Xtensa and Pi Linux targets were not tested. No provider is production-approved by this experiment.

## Sources and licensing

- BIP340 vectors are unchanged from bitcoin/bips commit `927b6de9915c9262615a6399de51b200f81e5aa4`; SHA256 `34c9d1d9c3a88d524bc80778540dc43f8306ec249a7485293063c376db851c2d`. The directory's original [LICENSE](sources/bitcoin/bips/bip-0340/LICENSE) offers BSD-2-Clause, MIT or CC0-1.0. [Upstream file](https://github.com/bitcoin/bips/blob/927b6de9915c9262615a6399de51b200f81e5aa4/bip-0340/test-vectors.csv).
- NIP44 vectors are fetched from paulmillr/nip44 commit `671a1f04bcfacaf125b0db68adc45bc9ce0e763b`; SHA256 `269ed0f69e4c192512cc779e78c555090cebc7c785b609e338a62afc3ce25040`. That repository has no root LICENSE and its README identifies licenses of implementations without explicitly assigning a license to the standalone JSON. This research bundle therefore does not redistribute that JSON or its generated Rust constants; they are fetched/generated locally into ignored paths. [Upstream file](https://github.com/paulmillr/nip44/blob/671a1f04bcfacaf125b0db68adc45bc9ce0e763b/nip44.vectors.json).
- [NIP44 key derivation](https://github.com/nostr-protocol/nips/blob/a79e21d90fce5465b50ef385dd368bba99ec4a0b/44.md#encryption) requires raw-x secp256k1 ECDH and HKDF extract with `nip44-v2` salt.
- Cargo.lock contains registry checksums for all dependencies. k256/sha2/hmac are Apache-2.0 OR MIT; secp256k1 and secp256k1-sys are CC0-1.0. Upstream licenses remain applicable to downloaded dependencies. See the versioned [k256 security notes](https://docs.rs/k256/0.14.0/k256/#security-notes) and [secp256k1 documentation](https://docs.rs/secp256k1/0.33.1/secp256k1/).

`results.json` records the observed result and original artifact hashes; reproducing on a different path/toolchain is not promised to yield byte-identical ELF files. These linked artifacts are not distributed with this bundle.
