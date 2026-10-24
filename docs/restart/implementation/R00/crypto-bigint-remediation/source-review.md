# Authenticated patch and selected API review

This is a source inspection before new compilation or tests, not a timing audit.
Both complete published archive diffs were inspected: crypto-bigint has 63 changed
files (including one new internal square-root module), ctutils has 10 (including
new primitives and their unit tests). `sources/archive-comparison.json` pins the
bigint file changes. Cargo-generated metadata separately authenticates all 224
new bigint files and all 23 ctutils files against the sparse-checksummed archives.

The bigint changes include guarded primitive borrowing/addition/zero counts;
constant-time equality in UintRef; branchless bit-length rounding; boxed inversion
using CtOption selection; Montgomery repeated-square full reduction; safe-GCD
iteration arithmetic widened to u64 with an explicit limit; mixed-precision zero
GCD handling; correct Jacobi-symbol fallback; exact-division zero/remainder tests;
Karatsuba carry propagation; replacement of fixed/boxed square-root internals;
and corrected modular-subtraction carry assignment. Mixed-width add/sub/select
now require the destination to be at least as wide as the source. Existing public
square-root interfaces remain; the removed helpers and GCD tuple outputs are
internal. Encoding adds Zeroize, while the DER test obtains its alloc guard.
Associated upstream boundary/property tests, benchmarks and documentation were
read; these source tests are not represented as already executed.

ctutils adds the primitives that bigint now imports for both 32- and 64-bit
words, barriers around borrow/comparison representations, fixed-stage fallback
zero counts, and explicit RISC-V32 wide-add handling. Its old public Choice and
selection interfaces remain. The complete 0.4.4→0.4.5 diff and new unit tests were
read. Functional tests cannot prove generated code is constant-time on all targets.

The selected downstream code was inspected in unchanged k256, elliptic-curve,
primefield and primeorder: U256/U512, Limb/Word, array encodings, modular retrieval,
fixed Montgomery forms/parameters, inversion, reduction and comparison/selection
traits remain available. No local caller adaptation is indicated by source review;
actual compatibility is reserved for the predeclared checks after source freeze.

The normalized/original/tag manifests and sparse records require ctutils ^0.4.5,
contradicting the release PR/changelog's 0.4.4 text. The actual minimum closure is
bigint0.7.6 plus ctutils0.4.5. Bigint raises MSRV1.85→1.87 and package resolver2→3;
ctutils already required1.87. Pinned Rust1.95 and the root workspace resolver are
unchanged. Runtime features and all other runtime dependency requirements remain
unchanged. Upstream's development lock changes128→112 packages, with75 removed,
59 added and one same-version dependency update; the complete parsed comparison
is `sources/upstream-dev-lock-comparison.json`. Those upstream dev inputs remain
archive/vendor source only and are not the product dependency graph.

The isolated standard Cargo resolution pins the two new crates plus the existing
four required transitive versions. Cargo vendor creates official file/package
checksums. Only these two vendor directories are transferred. Narrow offline
updates keep44 root and47 desktop packages: only the two admitted package records
change. The independent12-package QR worker graph remains exact. No new external
product package, manifest, toolchain, policy, gate or product code change is allowed.

The precommitted Python difflib text is a human comparison: files without terminal
LF can meet the next header. It is not an executable patch; original archive bytes
and path/hash inventories are authoritative. No upstream bytes were normalized.
