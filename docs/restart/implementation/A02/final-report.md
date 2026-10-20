# A02 final rehearsal candidate — 20 October 2026

The isolated candidate is `daf8ba03a9eb820f99b0f1bf5c4f553a7961e008`,
tree `db0687a5ec15228e944360e00e391a4fff863f5d`. This report binds the completed local implementation package for distinct final
review. Local acceptance, exact replay and actual recovery are complete for this
candidate; independent review and coordinator adoption/main CI remain pending.
The [package validation](execution/final-package-validation-04/result.json) checks
current case-source hashes, report links, retained license bytes, notice paths,
failure explanations and public evidence privacy. The [acceptance receipt](acceptance-receipt.json)
records the five author assessments without closing the task.
The [model-transition handoff](MODEL-TRANSITION-HANDOFF.md) is a historical
checkpoint superseded by this exact package. A02 has
not been adopted or closed; canonical main remains
`f2ef70f522af4977e15f81554a8c6eadcdbe8097`. Source freeze remains in force.

The explicit 20 October user resumption supersedes the historical
[pause checkpoint](PAUSE-HANDOFF.md). It does not change source inputs,
privacy requirements or the scope of the accepted [brief](brief.md).
No source repository was archived, no package was published, and no canonical
main or task graph was mutated by this delivery.

## Exact source and recovery

The [final source map](final-source-map.json) accounts for all 4,456 admitted
public/selected-private file rows, their original repository/commit/path/blob/
mode/hash, initial copied blob, final path/blob/mode/hash, rights basis and
numbered declared changes. It distinguishes 3,268 unchanged selected files,
198 transformed selected files, four selected historical overlay files removed
after execution, 498 deduplicated counterparts, 24 duplicates of deliberately
retired contracts, 30 other retirements and 434 exclusions. These are file
dispositions, not test counts. Excluded private sources are represented by counts
only; their names, bodies and histories are not imported.

The [initial import map](execution/initial-import-map.json) binds all 3,470
selected file copies at import commit
`86569e073da4faec0811d67137bbb0fd4f74c7c6`, tree
`59008a6e0fdb4475d03bbe4f1761f8514f552e84`. Existing public core ancestry was
fetched alone into empty Git; the complete original core tree, including the
later-removed snapshots, was retained initially. Two selected CC0 helper files
used only the exact separately reviewed seven-literal privacy correction.
This is explicitly recorded as an exception to byte equality.

The [39 ordered patches](../../../../tools/migration/patches/series.json)
declare every later file preimage, postimage and mode, patch hash, commit and
tree. The [final tree inventory](final-tree.json) accounts for all 3,612 tracked
files and every migration addition. The report generator replays the complete
file-state declarations from the initial tree and rejects undeclared differences.
It does not infer equivalence from filenames or pass totals.

The [new assembly and actual restoration](execution/rehearsal-04/result.json)
reproduced all 39 commits and final tree exactly in an absent destination.
Both stores contain exactly 7,943 reachable allowed objects and 330 commits:
the public core ancestry, one selected import and 39 transformations.
They have only `refs/heads/rehearsal`, with no other refs, remotes, push URLs,
alternates, grafts, shallow history, object symlinks or hardlinks.
`git fsck --full --strict` passed. The 6,596,041-byte bundle has SHA-256
`e4e28dc2fdee6aff9fc318eaa3e0ab254aa5aa3f18ddc44a82d492603cda5f03`;
every restored object and the tree matched. The earlier 36-patch restoration
and the un-restored pause bundle remain dated historical observations.

The [source reference report](source-references.json) preserves exact public
main/tag observations from immediately before and after the new import. Tags
remain original source references; evidence tags are not product releases, and
no source tag is invented or moved to a synthetic migration commit. All nine
public mains matched the admitted pins. Source repositories are still retained.

All twelve original source recoveries were previously verified/restored under
the admission gate. The additional
[private workspace recovery](execution/workspace-recovery-05-summary.json)
now captures and restores all seven observed refs, including the unchanged main
and distinct later pause branch. Its bundle SHA-256 is
`62bf7e973bcf973b80ca81f832c7a043b259a58b80f844c1b4e97c5353f04c98`.
Raw refs, logs and bundles remain protected. This is dated recovery, not archival
approval; any refs created afterward require another refresh before archive.

## Current paths, notices and rights

| Source owner/path | Candidate owner/path | Treatment |
| --- | --- | --- |
| nsealr core `crates/nsealr-core` | Same path in nSealr/nsealr | Existing engine; separate embedded workspace |
| nsealr `apps/desktop-simulator` | Same path, explicit host workspace | Own lock, toolchain and output directory; signing remains disabled |
| companion `packages`, `apps`, supporting scripts/docs | `packages`, `apps/bridge`, `tools/bridge`, `docs/bridge` | Internal packages private; only packed `@nsealr/sdk` is a publication candidate |
| raspberry application/tests/docs | `apps/pi` | Independent reference implementation and actual adapter source retained |
| specs protocols/schemas/vectors/examples | `protocols/contracts/v1` | Sole authoritative artifact; verifier, generator and independent tests retained |
| selected lab helpers/tests | `tests/integration` | Only individually admitted CC0 files; privacy correction and exact S01 overlays recorded |
| `docs/restart/work-items.json` | `plan/work-items.json` | Byte-exact initial move plus declared current operational policy; one task-state file |
| reviewed P01 source contracts | `docs/product` | Separate current copies, with declared link relocation only |
| hardware, board-sdk, website, .github | Separate owners | No product source import or new product build prerequisite |

The graph still has all 47 tasks and all seven originally closed task records,
with every original graph byte preserved apart from appending the declared
`execution_model_policy` field. That current field and the live AGENTS/execution
guide follow the latest explicit maintainer policy: Sol `xhigh` for coordinator
and all agents, with Astra `xhigh` only for a concrete exceptional complexity
reason. Hardware/security category alone is insufficient. Closed O01 criteria,
model assignments and evidence remain historical and byte exact. The unmerged
pause task reconciliation is not imported.
All 1,511 frozen artifact references, representing 1,508 unique files, retain
their original paths, blobs, modes and bytes. Historical links retain their
historical meaning; the current contracts and live navigation use their declared
current paths. `plan/evidence-index.json` is an equivalence/navigation index,
not another state authority. Current requirement copies introduce no new
requirements or acceptance claims.

Bridge's MIT notice is retained at `LICENSES/companion-MIT.txt` and in the
packed SDK; Pi's MIT notice is at `apps/pi/LICENSE`; contracts' CC0 notice is at
`protocols/contracts/v1/LICENSE`; selected lab tooling's CC0 notice is at
`LICENSES/lab-tooling-CC0.txt`. Existing public vendor, official crypto-vector
and other nested notices remain in place. The original per-file rights review,
narrow privacy review and admission decision remain the basis of selection.
Neither hashes nor the root MIT notice provide blanket relicensing. Private
workspace and legacy hardware have no selected content, and no original private
manual or full private history is added.

The [draft notices](draft-source-notices.md) are ready for later coordinator
application, subject to reviewed adoption and verified destination links.
They are not published notices or archival claims.

## Acceptance binding

The [complete cold run](execution/cold-product-03/evidence/suites/result.json)
executed one uninterrupted `make -k ci` at
`2bb10013c9fcaab04c544abcff3f480243200da1`, with every command passing and its runner verifying no source change during
execution. The final candidate differs in exactly four files. Patch 38 corrects
`docs/reproducible-build.md`; patch 39 changes only live `AGENTS.md`,
`docs/restart/execution.md` and the top-level operational model policy in
`plan/work-items.json`. All 47 task records remain unchanged. Executable source,
tests, fixtures, locks, toolchains and recipes are byte-identical to the
full-tested source. The [policy/equivalence checks](execution/model-policy-execution-01/commands.json)
record the exact four paths and another passing `make docs test`.
The [exact delta and affected checks](execution/resume-navigation-execution-01/commands.json)
and [successful guide check](execution/resume-navigation-execution-02/result.json)
record `make docs test`, current-owner/feature/command checks and shell syntax.
This is explicit evidence reuse by source equivalence, not a claim that the full
suite ran again on a later commit.

| Canonical A02 acceptance | Actual evidence and limit |
| --- | --- |
| Isolated import preserving provenance and old commits/tags/paths | Complete initial/final maps, all 39 exact replayed commits, original public ancestry, selected-only import, original tag observations and restored allowed-object audit above |
| Separate host/embedded toolchains and workspaces | Root core workspace and standalone simulator workspace each pin Rust 1.95.0, own locks and build outputs; full run executes both plus real `riscv32imafc-unknown-none-elf` core build |
| Compare imported trees, execute equivalent acceptance and eliminate fixture duplication | Exact initial tree plus declared final tree; full product suite; all retained named cases and explicit dispositions; one checked authoritative contract artifact, independent Python/Pi oracles and deterministic expected-data projection |
| Prepare redirects and external Nostr interoperability plan | Draft notices plus [source-bound interoperability handoff](interoperability-handoff.md); no live client/device session or publication claim |
| Validate existing components without custom-board/empty-SDK dependency | Cold product bootstrap fetches only the exact product, builds/tests in isolation with no sibling hardware/SDK/private checkout; separate hardware regression passes independently; no ESP32/P4 app or implemented SDK is invented |

The full [command output](execution/cold-product-03/evidence/suites/00-product-ci.log)
contains format/clippy, default/std/doctests, secret boundaries, host vector
replay, device core build, both dependency audits, unchanged coverage floors,
two clean builds and a different checkout path, contracts, complete Bridge
build/type/unit/consumer/security/packaging gates, Pi, helpers, product controls
and all seventeen integration steps. Core coverage is 100.00% against 100.00%;
host coverage is 76.76% against 76.70%. The measured core rlib SHA-256 in this
cold run is `05257ea1ba380e0f296a15447a71a2029ac9350dbb0186bd97f04ae0cbb72fda`;
same-tree host SHA-256 is
`425829d8f3762ace798256c7faaa11f8ff5d03772f7bb74eeb00ccd8ac067afd`.
These are environment/source-bound observations, not universal fixed hashes.
The earlier Rust-stage hash is retained separately as a dated historical
observation in `progress.json`; current runtime values bind this complete run.

[TypeScript correspondence](execution/bridge-named-execution-02/case-correspondence.json)
accounts for all 716 original runnable identities: 691 pass afterward,
25 card cases retire; the unchanged live-relay skip remains separate.
There are 686 same-name cases and five renamed cases; unchanged names do not
mean unchanged assertion bytes. The separate treatment ledger records
668 ordinary adaptations, 16 active-contract adaptations, seven route/ack
assertions and 25 retirements.

[Other named correspondence](execution/case-reconciliation-execution-01/case-correspondence.json)
accounts for all 263 original Rust cases, 90 of 92 contract cases, all 150 Pi
cases, and 115 helper cases including thirteen optional browser/serial unit
cases. Two card-only contract cases and ten card-only helper cases retire.
Two selected private-prose cases retire; twenty-one opaque private guardrail
obligations execute through explicit replacements and four obsolete
taxonomy/editorial obligations retire. Seventeen copied-snapshot helper
mechanisms have current artifact replacements; eighteen consumer-scope cases
remain with an explicit class rename. All 67 current root Python controls and
eight bootstrap controls execute. Seven historical active overlay controls
have individual preservation/replacement mappings; the original S01 overlays
were actually applied before the layout transition.

The [separate hardware regression](execution/external-hardware-execution-01/commands.json)
passed against `340697d6713a671e9e01b0dc874ec999ab071601`, including explicit
product/profile alignment. It is not a product prerequisite or physical proof.

## Failures, limits and integration handoff

The [complete exported nonzero-exit inventory](failure-observations.json) retains
all exported failed observations. The explanatory `failure-removal-ledger.md`
is complete and bound by `acceptance-receipt.json`; independent final review
and coordinator adoption remain pending.
Corrections are separate declared changes, not
rewritten logs or erased assertions. `cargo deny` exits zero with inherited
registry/index warnings; complete yank-status coverage is not claimed.
The OS, system compiler/linker, rustup trust boundary and hosted runner are
not hermetic. Actual main CI has not run on this local candidate.

Live relay, installed Chromium/Firefox sessions, physical approval/signing,
camera/display/GPIO, manufacturing, production-key custody and physical
entropy remain unqualified. The Firefox service-worker manifest limitation
remains C01/P02 work. No passing simulator, package, plan check or AI review
closes a physical release gate.

The coordinator must obtain a distinct review of this exact product candidate
and the author evidence commit before normal adoption. The source freeze
protects this input tuple; never overlay this tree on a newer main wholesale.
S03, P02, S04 and B01 held branches are not implicitly part of the candidate.
The pause branch revision-14 graph is an unmerged reconciliation proposal.
Future adoption must reconcile its necessary task assignments/evidence once,
preserve all existing closures and 47 criteria, and avoid inventing adopted
closure for an unmerged branch. Changed inputs invalidate affected review.

After reviewed adoption, the coordinator owns actual main CI, any separately
scoped later branch integration, verified notices and eventual source archive.
Refresh recovery for any refs advanced after the dated captures. The local
rollback is the exact retained candidate/import bundles and frozen patch series,
replayed into another absent destination. No force push, canonical reset,
registry publication or source deletion is part of this rehearsal.
