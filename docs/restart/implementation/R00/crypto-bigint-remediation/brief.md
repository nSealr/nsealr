# RUSTSEC-2026-0387 minimum dependency remediation

Base is root's clean failed stable source
`5e17f9a957137c7d856f12bc08f5f795d3f858d8`. Its one `make -k ci` exited2:
cargo-deny rejected crypto-bigint0.7.5 for RUSTSEC-2026-0387; the17 integration
steps passed. Preserve that source and original log, not a new exploit claim.
The root and standalone desktop locks select0.7.5; the separate QR-worker graph
does not include this crate. This task changes no product implementation or gate.

The [official advisory](https://github.com/RustSec/advisory-db/blob/8a5b8090ef20c9c1b425f3373f28b0b23cc5c7a0/crates/crypto-bigint/RUSTSEC-2026-0387.md)
declares0.7.6 patched. Its published archive SHA256
`6bb08299a6046833a879ace115697f12fd2bd6c8d3e93c909ffc9e0738e7cae0`
matches the authenticated official sparse registry record and archive VCS/tag
`c34044b8a1479ef32bec0a9030cf2f07b06506d9`. It is not yanked in this captured
record. The existing vendor is byte-exact to the authenticated0.7.5 archive.

The [release PR](https://github.com/RustCrypto/crypto-bigint/pull/1365) says
ctutils0.4.4, but the actual published Cargo.toml, Cargo.toml.orig, pinned upstream
tag manifest and sparse record all require **ctutils ^0.4.5**. Root explicitly
admitted that necessary minimum transitive patch. The ctutils0.4.5 archive SHA256
`38d28fb6aa7dd680b3ffd1a3e64e115c177bdba63c0ae7f9cd48129ff05c4fa0`
matches its official sparse record; VCS/tag is
`88d6e90d4cfd2fc3333d00e13c99241507d2138f`. Its runtime dependencies and features
are unchanged from0.4.4. Both new crates require Rust1.87, below pinned1.95.
Do not override the dependency requirement or infer compatibility from the PR
description alone. Sources, fetch failures and this discrepancy remain evidence.

Writable product scope is exactly Cargo.lock, apps/desktop-simulator/Cargo.lock,
vendor/crypto-bigint and vendor/ctutils. Use official Cargo vendor metadata and
narrow offline updates after authenticated acquisition. Every other package
record and vendor subtree must remain exact; worker lock, manifests/config,
toolchain, audit rules, application source, thresholds and task graph stay exact.
Unexpected closure or source incompatibility stops the edit for explanation.

Inspect the complete authenticated upstream diffs and selected downstream APIs
before claiming compatibility. The change includes timing and arithmetic fixes,
not just a version field. Keep upstream tests/dev lock bytes as vendor source;
they do not authorize additional product dependencies or arbitrary downloads.
Freeze the actual changed source and finite expectations before build/sign/test
and notify root. Functional tests are not all-target constant-time proof.

After that freeze, use unchanged R00 tools and task-local Cargo/target/tmp paths:
default/all-feature Rust workspace tests; explicit no-default no_std RISC-V build;
standalone desktop vectors; fresh observed S03/K01 outputs checked with existing
independent oracles; relevant clippy and existing coverage floors; release C ABI
artifact binding plus existing EngineAdapterTests using public fixtures; and the
unchanged audit gate across all three current graphs with fresh official data.
No full make-ci, hosted CI, production keys, new corpus or actor composition run.
Root owns the one later complete stable/protected integration after distinct B01
review of this coherent candidate. Reuse unaffected source-bound evidence only.

Preserve original RED, all significant command/source failures, raw outputs,
source/environment/ELF bindings and limits. The result can remove these affected
versions and demonstrate bounded functional compatibility. It cannot establish
absence of side channels on every compiler/CPU, physical qualification, a default
route, provider custody, task completion or release acceptance.
