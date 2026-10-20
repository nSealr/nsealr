# A02 distinct final rehearsal review

**PASS** for exact author `bb033619b5346302833d717eb501bfa4e3653a1b`,
manifest SHA-256 `38b2fb69ef3f1e8a2414d168b005d6f674e2eabebe84d252f2239494cea0917e`,
and isolated product `daf8ba03a9eb820f99b0f1bf5c4f553a7961e008`, tree
`db0687a5ec15228e944360e00e391a4fff863f5d`.
No blocking finding remains. This verdict accepts the admitted local rehearsal;
coordinator adoption, task reconciliation, actual PR/main CI and release work remain separate.

The reviewer `/root/a02_final_review` authored none of the product or author
package. The assignment follows the latest Sol `gpt-6.1-sol` / `xhigh` policy,
with no Astra exception. Reviewer and author use the same GitHub identity; this
is distinct agent review, not an external audit or certification.

Full substantive review and independent execution started on exact author
`f9a09ba2e9b0212f7dafa53b086c5f1c366d9288`, before any tracked review writes.
[The final delta check](delta-result.json) verifies only three changed files above
that anchor: one report paragraph, its derived progress-index digest and the
package manifest/receipt. All 982 package members and 755 indexed artifact hashes
pass on the final author. The other 980 payload members, product and every
historical command/result are unchanged.

## Ordered canonical acceptance

| # | Canonical criterion | Verdict and evidence |
| --- | --- | --- |
| 0 | Import in an isolated repository, preserving provenance and mapping old commits/tags/paths. | **PASS.** [Independent replay/restoration](independent-replay/result.json) reproduced the exact initial import, all 39 declared patches and final commit/tree. Initial selection, all 4,456 source rows and 3,612 final files were checked against Git modes/blobs/bytes and rights records. Exact public core ancestry remains; selected licensed private postimages enter as files, without private histories. Source references retain original public commit/tag identities, observed empty tag sets and path mappings. No source repository settings or identity/stars were changed. |
| 1 | Preserve distinct host/embedded target toolchains and build workspaces where needed. | **PASS.** Root contains only the portable core; the simulator has a standalone host workspace. [Independent metadata](embedded-workspace-metadata.log) and [host metadata](host-workspace-metadata.log) confirm separate workspace roots and output directories. Both pin Rust 1.95.0, own locks and vendoring configuration; the core defaults to no_std. The reviewed complete run builds the actual RISC-V core and executes the host gates separately. |
| 2 | Compare imported trees and run equivalent acceptance; eliminate fixture duplication with one authoritative contract artifact. | **PASS.** Exact initial and final trees, pre/postimages, modes and patch/commit chains passed independent replay. The complete cold `make -k ci` actually passed at `2bb10013`; exactly four later documentation files differ in the final product. Source equivalence and affected `make docs test` are verified. The sole contract artifact rejects missing/extra/hidden/forged/stale content. [Nine real-candidate tamper probes](negative-result.json) refused changes and exact restores passed; both checkout locations resolve the same artifact from `/tmp`. [Case audit](case-audit-result.json), actual assertion inspection and targeted executions substantiate the explicit retirements/replacements. |
| 3 | Prepare redirect notices and external Nostr interoperability plan; do not archive or publish source repositories without applicable authorization. | **PASS.** Draft notices map real candidate destinations and preserve source identity/licenses. The handoff pins the NIPs and named client source selections, identifies NIP-01/BIP340, NIP-07/NIP-46 and encoding/crypto obligations, and requires later identified relay/browser/device sessions with actual one-use device approval. No notice publication, source archival or registry publication occurred. |
| 4 | Validate only the migrated existing components and topology: ESP32 signer/Pi/P4 code has no custom-board dependency. Do not require unimplemented SDK code or empty-scaffold proof; actual standalone SDK/application independence is accepted in B02/B03. | **PASS within the accepted existing-component interpretation.** The complete cold product build contains no sibling board-sdk, hardware or private checkout. Root core, simulator, Bridge and Pi source execute in that isolated layout; the 17-step product recipe excludes the separately passing hardware-340 regression. There is no implemented ESP32/P4 device application or SDK consumer to qualify, and none is invented. B02/B03 retain actual future SDK/application independence. |

## Substantive checks and retained obligations

[The independent audit](probe-result.json) checks all 982 public package files,
4,456 complete public/selected-private disposition rows, 3,612 final files and
all ten applicable root notices. Original core vendor, official crypto-vector,
KiCad and other nested notices remain unchanged. The separately admitted two-file
CC0 privacy exception is explicit: only approved sanitized postimages enter the
initial tree. The public package and all 4,785 candidate blob objects contain no
excluded original manual addresses/basenames. Private selected source commits do
not occur in the object store. No private bundle/postimage or unrelated private
source was copied into this review.

The new owned absent destination reproduced all 39 transformations and actually
restored its candidate bundle. `git fsck --full --strict` passed, all 7,943 objects
are reachable and allowed, and all 330 commits have the accepted ancestry. Both
stores contain only the rehearsal branch, with no remote/push URL, alternate,
shallow/graft history, object hardlink or symlink. The bundle remains in protected
ignored runtime. Prior exact admission review `b9d5d96e` and coordinator admission
`0a8bb620` bind selected rights, protected twelve-source recovery and the corrected
S01 helper/metadata/bootstrap inputs. This review inspected those exact records;
it does not claim a fresh all-ref capture of subsequently advanced branches.

The graph move preserves all 47 task records, seven closed records and 1,511
references / 1,508 unique frozen files byte-for-byte. The only later graph field
is current operational model policy. All 81 inventoried historical links retain
pinned source navigation; five current contracts have one normative owner each
and differ only by declared link relocation. The evidence validator derives its
historical closure from frozen source, rather than a hardcoded seven-task count.
Its executed positive tests admit later separately reviewed closures and current
contract edits with their own graph evidence; the canonical validator governs
those new results. Frozen history need not be rewritten to advance the plan.

The [case audit](case-audit-result.json) reconciles all 716 original runnable
TypeScript identities to 691 passes and 25 explicit card retirements, with the
unchanged live-relay skip separate. The sixteen active-contract changes remove
retired members/old owner names. The seven route/acknowledgement replacements
reject retired card routes before dispatch and reject host acknowledgement bypass
while preserving ordinary active dispatch. They are replacements, not assertions
made equivalent by their names. No non-card cryptographic expected values changed:
the thirteen changed active vector files contain owner, card-feature, policy
selection or refusal-contract changes, recorded in [the structural diff](semantic-fixture-diff.json).
All 263 original Rust names occur in the successful complete run; ninety retained
contract cases, 150 Pi cases, 115 helper cases including thirteen optional helper
unit cases, 67 root controls and eight current bootstrap controls have bound
successful execution. Seventeen old snapshot mechanisms, eighteen consumer-scope
cases and seven old overlay controls have explicit current/historical mappings.
Twenty-one private-origin guardrails have executed positive/negative replacements;
four obsolete private taxonomy/editorial cases and two selected private-prose
cases retire explicitly. The old twenty integrations become seventeen uninterrupted
product steps, one external hardware regression and two retired card steps.

Independent focused execution passed all 48 migration controls, reproduced
`make docs test`, 184 TypeScript route/policy/fixture/CLI and NIP-46 identity/security
cases, ten integration-placement controls, source-boundary and guide positives/
negatives, and a newly packed SDK installed outside the source workspace. Packed
root/Node behavior, browser execution without Node module globals and strict type
consumers passed; unpublished workspace imports, hidden internal exports, dev
signer and card exposure are rejected. These use explicitly recorded pinned tool
and cache reuse, including an offline dependency install; no new cold-bootstrap
claim is made. Browser VM/bundling is not installed-browser qualification.

The unchanged [Pi oracle](oracle-result.json) independently checks serialization,
event IDs, public keys, libsecp256k1 Schnorr verification/signing and mutation
rejection on public fixtures. The Rust projection imports only JSON/path/sys and
copies committed expected fields into test output; it never invokes an engine or
fixture-answer generator. Generation remains explicit maintenance. Existing
simulator signing-disabled behavior is retained.

All 755 current indexed artifacts and 510 exported command-log hashes were
checked. Every one of the 30 nonzero observations is preserved and explained in
the failure/removal ledger, including failed cold bootstrap, pnpm entrypoint,
restore-branch, import-fixture, projection, API/type, path and report-check runs.
Corrections are declared, not concealed retries. The reviewer also preserves an
initial case-audit failure: its script guessed the wrong retirement enum, then
was corrected to the actual accepted taxonomy/editorial values; no candidate
change was needed.

## Findings and handoff limits

[F01](finding-F01.json) found the stale statement that the completed ledger was
pending. The coordinator corrected the current paragraph. [F02](finding-F02.json)
then blocked the intermediate `c9958ec` package because its current progress index
still carried the prior report hash. Final `bb03361` refreshes only that derived
entry and its package binding. Both findings are resolved by the targeted delta
review, with original observations retained. No executable source or historical
execution evidence changed, so a fresh full product CI or replay would add no
coverage for this correction.

The inherited cargo-deny registry/index warning does not establish complete
Yank-status coverage. Live relay sessions, installed Chromium/Firefox and its
retained service-worker manifest limitation, actual device review/one-use approval,
camera/display/GPIO, entropy, secure-element custody, manufacturing and production
keys remain unqualified. Local software evidence or this agent review closes no
physical release gate.

Canonical source main remains frozen at `f2ef70f`, with selected hardware
`340697d`. Held S03/P02/S04/B01 work is excluded. This verdict does not review a
future adoption diff, close A02, import a pause graph, or assert actual PR/main CI.
The coordinator must separately review the concrete adoption/evidence append and
then-materialized integration, preserve this exact public payload and review,
reconcile the graph once, and run protected PR checks plus actual main CI. Later
notice/archival/publication and ref-refresh work remain concretely scoped steps.
All review files are bound by [the review artifact manifest](review-artifacts.json).
