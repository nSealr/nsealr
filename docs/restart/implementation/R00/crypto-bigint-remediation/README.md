# crypto-bigint 0.7.6 minimum security patch

This candidate removes the versions affected by RUSTSEC-2026-0387 from the two
active cryptographic Cargo graphs. It updates crypto-bigint0.7.5→0.7.6 and the
necessary ctutils0.4.4→0.4.5, with **77 product paths**: two locks and the two
vendor subtrees. Root44/desktop47 package counts remain unchanged, with the other
42/45 package records exact. The12-package QR-worker graph, every other product
file, all1879 other vendor files, policies, thresholds and task graph are exact.
Distinct B01 review and root's later complete/protected integration remain pending.

The [precommitted brief](brief.md) and [expectations](expectations.json) identify
the admitted scope. The [official RustSec advisory](https://github.com/RustSec/advisory-db/blob/8a5b8090ef20c9c1b425f3373f28b0b23cc5c7a0/crates/crypto-bigint/RUSTSEC-2026-0387.md)
(CC-BY-4.0) declares>=0.7.6 patched. Both official archives match authenticated
sparse registry checksums and pinned VCS/tag manifests; [Cargo-generated vendor
metadata](resolution/vendor-authentication.json) validates224 bigint and23 ctutils
files byte-for-byte. The archived crates retain their Apache-2.0/MIT license bodies.
The [release PR](https://github.com/RustCrypto/crypto-bigint/pull/1365) and changelog
say ctutils0.4.4; published normalized/original/tag manifests and sparse metadata
instead require^0.4.5. That discrepancy is preserved, not overridden. MSRV1.87 fits
unchanged Rust1.95. [Patch inspection](source-review.md) accounts for arithmetic,
timing, API and upstream-development-lock changes; the latter do not expand either
product closure.

Actual source was frozen before compilation/signing/tests at
`7badfdc93fcb1654e97943204b7b854113c21120`, with product bytes fromad4ac14c.
[Source freeze](source-freeze.json), [2222 input bindings](checks/source-inputs.json),
[commands](checks/commands.json), [tools](checks/tools.json) and [correspondence](source-correspondence.json)
bind the proof-only tail to those bytes. All23 focused command receipts exited0:

- Workspace core257 default/258 all-feature units,10+4 integration cases,
  fixture-crate3 units and15 core doctests per configuration; desktop21 vectors
  plus its build-root case. Root/host clippy kept warnings/dead-code denied.
- Existing S03 and K01 oracles verified newly emitted outputs: S03 eight events
  and three imports; K01 thirteen vectors, three identities,1313 mutation
  rejections and27 preflight rejections. Expected public fixtures stayed exact.
- Official unmodified ctutils0.4.5 library source passed157 unit tests, compiled
  against the already product-built cmov/subtle libraries. No proptest ecosystem
  was installed. Core no-default RISC-V32 release compilation passed.
- Coverage retained core100%, fixture100%, host77.69%, against100/100/76.70 floors.
- A fresh release C ABI library from the changed closure passed the14 existing
  EngineAdapterTests, including basic/tagged signatures, explicit auxiliary data,
  failed callbacks, consumption/reservation and cleanup checks. Its compiler JSON,
  ELF headers and SHA431a0e29861116d21a4eb0395e44a4cd3f41c9b6d5cc3b2c2dad5aeaf274336d
  identify this host artifact; no reproducibility claim follows.
- The unchanged `make cargo-deny` passed its four controls and all three graphs,
  retaining advisory/yanked/license/bans/source policies and fail-closed missing
  index handling. It fetched fresh official data then checked offline. The recipe
  deletes its temporary cache: this receipt is time/log-bound, not a claim that its
  DB equals the separately pinned discovery snapshot.

Root's original full5e17 `make -k ci` remains RED/exit2 for the new advisory; its
17 integration steps passed. The original log hash and advisory excerpt remain
under`sources/`. [The inventory-reader error](freeze-reader-error.json) preserves
an assertion that accidentally counted23 documentation paths with77 product paths
and the shell continuation that committed afterward. Explicit allowed-path checks
corrected that verification before any new runtime. No PASS is attributed to the
failed reader. Subsequent dependent commands fail closed. Read-only source-location
errors, official raw archives/diffs and log whitespace are also retained.

This is bounded source authentication and functional compatibility. It is not an
all-target constant-time proof, an exploit assessment, ARM/Pi execution, physical
qualification, provider/key-custody qualification, default-route promotion or task
closure. No full product/hosted CI was run by this author. Root owns current graph
hash reconciliation, one complete stable gate and protected PR/resulting-main gates
after distinct review. Existing historical reports retain their original sources.
