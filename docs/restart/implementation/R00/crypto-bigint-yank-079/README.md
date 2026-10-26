# crypto-bigint 0.7.9 minimum yank remediation

Source candidate: `563d10b3c933a0bdc4605d27710c0ff2610960e1`, based on
PR53 source `220aa0d4e4e0f5f58b02ae66164661aaa48da988`.
Root separately reviewed that source and reported PASS. Packaging does not
change the accepted source.

The [pinned upstream changelog](https://github.com/RustCrypto/crypto-bigint/blob/6a22557430de57c27d4e1758c81b7e26d4a26aba/CHANGELOG.md)
attributes the 0.7.6–0.7.8 yanks to
[PR1373](https://github.com/RustCrypto/crypto-bigint/pull/1373). The prior blanket
NonZero multiplication also admitted Montgomery types for which nonzero factors
can have a zero product. Upstream restricts the implementation to Integer.
This is the upstream reason; it is not a claim that nSealr's selected k256 path
is an exploit demonstration.

0.7.9 is the minimum observed non-yanked successor. Its official sparse record,
API checksum, archive and VCS commit agree. Rust MSRV remains 1.87, below
pinned 1.95. k256 0.14.0, elliptic-curve 0.14.1, ctutils 0.4.5 and every other
product package are unchanged. 0.7.10 adds further primitive/multiplication
changes and is outside this minimum correction.

Only the root/desktop package records and the official crypto-bigint vendor
subtree change. No application, manifest, toolchain, policy, threshold, QR-worker
lock or task graph changes. Official Cargo generated the vendor metadata.
The [consumer lock patches](consumer-locks/contexts.json) are bound to exact
frozen P4/S3 sources, resolved offline and have the same registry package/version/
checksum set as a subset of the audited root graph. No P4/S3 source was edited
and no new target binary was built here.

## Observed checks

All 14 commands in [proof/commands.json](proof/commands.json) passed: workspace
default/all-features tests; no-default no_std RISC-V release build; standalone
desktop vectors; independent S03/K01 observations; relevant clippy; new host
fixture cdylib plus existing EngineAdapterTests; and the unchanged three-graph
audit with newly fetched registry/advisory data.

The same audit on the old graph, whose audit inputs equal PR53, rejected
crypto-bigint 0.7.6 with exit 1. Its raw stdout/stderr are retained. This was a
local negative replay, not hosted CI. No yank-ignore or other rule was changed.

Specific upstream regression functions for mul_mod_special zero/MAX c, boxed
inverse truncation and the new P521 const-prime test were **source inspected,
not separately executed**. They are not included in the 14-command claim.
The real feature graph excludes alloc/BoxedUint. The selected k256 uses fixed
Uint inversion and its own field/scalar backends rather than those special
zero/MAX-c multiplication cases. Product vectors/oracles/ABI checks establish
the selected consumer behavior; they do not replace upstream regression coverage
or prove absence of constant-time problems on every compiler/target. No vendor
dev closure, full vendor suite, full make-ci or hosted CI was run.

## Adoption and retained evidence

[affected-artifacts.json](affected-artifacts.json) identifies exact frozen
artifacts and source-specific evidence that cannot be carried to the new crypto
closure. Original hashes, results and reviews remain historical facts. Apply
consumer changes explicitly, rebuild/rebind the affected Rust artifacts and
repeat the relevant producer/runtime checks on each intended target.

The Pi image remains the frozen 0.7.6 diagnostic image; this correction does not
rewrite it or admit its crypto closure. The unchanged QR worker, Python camera/
supervision code and unrelated IO/camera/vendor proofs remain separate. No Pi
image rebuild or SD operation was performed.

Root owns the distinct final evidence review and protected integration. P4/S3
authors have Root's admission to update their own consumers explicitly. The
remaining device, timing, entropy, custody, client and release gates stay open.
