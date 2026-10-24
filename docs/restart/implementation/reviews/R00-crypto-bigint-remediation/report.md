# crypto-bigint remediation source and proof review

PASS_SECURITY_PATCH_SOURCE_AND_FOCUSED_PROOF_ONLY; findings[]. Exact final
candidate `4f132f5bba19f28ee491d05189eea1ad919ba7b4`, tree
`41e55fec64d2abc04a76e9d9d03826dc47388af5`. Product bytes remain exact executed
`7badfdc93fcb1654e97943204b7b854113c21120` / product commitad4ac14c, against
failed source5e17. This final review reuses the separately frozen2f106d1e static
reading; its then-pending status is preserved, rather than relabelled.

The official RustSec source declares0.7.6 patched for RUSTSEC-2026-0387. Captured
official sparse records, archives, VCS/tag/original manifests and Cargo checksums
agree: crypto-bigint archive6bb08299… has224 exact vendor bodies; ctutils38d28fb6…
has23. The223 old bigint bodies equal the0.7.5 archive. Both MIT/Apache notices
are intact. Fourteen successful primary fetch records match their actual bytes;
the assigned-ID404 remains preserved. These are primary-source/transport/checksum
bindings, not a claim of publisher signatures or universal supply-chain safety.

The minimum closure is crypto-bigint0.7.5→0.7.6 plus ctutils0.4.4→0.4.5. The latter
is required by the published normalized/.orig/tag/sparse^0.4.5 dependency, despite
PR/changelog0.4.4 prose. No override hides that discrepancy. Exactly77 product
paths change:64 bigint,11 ctutils and two active locks. Root44 and desktop47
retain every other package record; worker12 and all1879 other vendor files are
exact. No application, policy, manifest, toolchain, threshold or gate is changed.
MSRV1.87 fits the unchanged pinned1.95; runtime features and other requirements
stay exact. Upstream development-lock churn is vendor source, not product closure.

The source inspection addresses borrow masks/barriers and zero counts, UintRef
equality/selection, division, Montgomery carry/reduction, CtOption inversion,
safegcd overflow and square-root replacement. Existing k256 scalar reduction still
uses the compatible zero-in/mask-borrow-out interface, and typed integer/encoding/
Montgomery APIs used by unchanged downstream crates remain. The public sqrt APIs
remain while internals and boundary tests change. No local replacement crypto or
deleted functionality is used to pass gates. Source/tests support this published
remediation and bounded compatibility; generated constant-time behavior on every
compiler/target, side-channel absence and exploitation were not established.

The70-path final tail contains task proof only. Independently checked111 manifest
members plus self,2222 exact executed/final input bindings, all23 command exit/log/
environment bindings and eight actual tool-file hashes. The manifest is
`2c4c2ae44b69690d429cc94f117d3c87b2477f9545b4e959c267751447445dfe`;
result hash is `855cfbf618eec1eeb2016bc61cfdde3ffda847d5a1d03989f8f85318f8b2ba70`.
No author receipt was recreated or re-executed by this reviewer.

The actual default/all-feature workspace logs show257/258 core tests,10+4
integration cases,3 fixture units and15 core doctests. Desktop21 vectors plus
its build-root case pass. Newly emitted source-bound S03 eight events/three
imports and K01 thirteen vectors/three identities pass the existing independent
oracles, including1313 mutation and27 preflight rejections. Driver ordering and
fresh observed-directory creation bind those outputs to the actual7bad run;
the oracle's own warning that data comparison alone is not execution provenance
is respected by the command/source/environment bindings, not erased.

Official unchanged ctutils library source passes157 units via rustc against the
already product-built cmov/subtle libraries; proptest/development ecosystem and
whole upstream bigint tests were not fetched or credited. RISC-V32 no-default
release is compilation only. Root/host clippy keep warning/dead-code denial.
Coverage100/100/77.69 satisfies unchanged100/100/76.70 floors. The fresh release C
ABI artifact's compiler JSON/path/650608bytes/SHA431a0e29… match the actual retained
ELF and explicit environment of the14 existing EngineAdapterTests. This proves
neither new ELF reproducibility nor ARM/device execution or route admission.

Fresh `make cargo-deny` uses the unchanged standard recipe: four controls, three
official-data fetches and three offline checks with `--deny index-failure`, all
successful, with no index-failure warnings hidden. This proof is the actual
2026-10-24T04:28:57.220799+00:00 command and raw logs. Its temporary database was
deleted by the existing tool. Its DB identity/content is not retained, pinned or
asserted equal to the earlier discovery snapshot. The primary discovery sources
and later fresh-audit observations have separate roles.

Original full5e17 remains FAILED/exit2 for0387; its functional17 passes do not
make it green. The count100/77 inventory error and shell continuation remain
verifier failures, not product failures or attributed PASS. The reviewer also
retains a harmless wrong commands.json lookup, corrected to checks/commands.json
without candidate/runtime edits. Vendor/archive/raw whitespace is preserved:
author full whitespace exits2, scoped authored material exits0. A reviewer tool-
metadata writer initially assumed an alias-only schema for two direct binary
rows, then its dependent writer lacked fields; those errors are retained in the
validation. All eight actual tool files were subsequently checked, with no
candidate/runtime edit or PASS credited to either incomplete writer.

The same review adds only the requested assembly facet at root integration
`72c54c716cfa222a2c67c3295ae77e2e0abb481e`, tree
`e6f2b0b11605ab1036bb85db5a7818e4d493f8ef`. All189 author product/proof postimages
are mode/blob-exact4f. Root's last commit changes only graph and its existing
source-correspondence record. The ten changed live R00 hashes (two locks/eight
ctutils files) match actual source, all47 formal/global sets and other45 task
records stay exact, and original failed5e exit2/no-acceptance remains explicit.
Current23 focused successes are distinguished from still-required new complete/
protected/main gates. This does not re-review the other historical lifecycle
reviews/imports already present in that root branch.

Reviewer performed read-only Git/archive/JSON/source/proof inspection only: zero
independent builds/tests/signatures/audits/fetches/hosted operations. No replay
was necessary to resolve a remaining question. Beyond the scoped ten bindings
above, root still owns final assembly, one complete stable gate, protected PR/merge and
actual-main/source qualification. No task, physical/provider/custody/default route,
device or release qualification is closed by this verdict.
