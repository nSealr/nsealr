# A02 materialized adoption — distinct delivery review

**PASS_materialized_adoption_candidate_only** for exact candidate
`a5f7b9f2e087c9538495a16706644f3390e6b01c`, tree
`e67b1337eaea5cfe3242fe4d83845881764ea5f0`, directly based on reviewed product
`daf8ba03a9eb820f99b0f1bf5c4f553a7961e008`. No blocking finding.

This is the required review of the actual delivered append and metadata, distinct
from rehearsal source review and scope preparation. It does not close A02,
report protected PR/main CI as passed, authorize a bypass of normal integration,
or qualify a release/physical boundary. Reviewer `/root/b01_final_review` is
distinct from materializer `/root/a02_sol` and coordinator `/root`. I previously
reviewed the scope; that prior verdict was not substituted for this audit.

## Inputs and exact delivery

I read coordinator admission `b507e00dbbc7992841836cc769a27d8efdbac75a`, scope
`81a9a12140c1ace260f9ed280146b7d663e11ac9`, scope review `100edeb`, and actual
source review `0b55449aeea6b296805b786fd4822fc625ba74dd`. The last binds author
`bb033619b5346302833d717eb501bfa4e3653a1b` and product `daf8ba03`, with an actual
passing rehearsal verdict. Their report/manifest hashes and admission bindings
match the committed objects. This review uses its own fresh worktree and writes
only `docs/restart/implementation/reviews/A02-adoption/`.

The independent probe resolved source and destination Git trees and actual blob
bodies. All 1,134 copied rows match source mode/blob/length/SHA256 and inventories:

| Copy | Files | Actual source |
| --- | ---: | --- |
| Public author reports/tooling | 983 | `bb033619` |
| Final rehearsal review | 143 | `0b55449a` |
| Scope review | 5 | `100edeb7` |
| Scope, prospective payload and admission | 3 | `81a9a121` / `b507e00d` |

The 983 author files are exactly the 982 manifest members plus its manifest.
All 73 existing entries remain identical; 910 are additions, zero are replaced.
Every prospective preimage matches the actual product entry. The other copy
inventories cover all files in their pinned source review directories, not just
the report. The final-review artifact manifest matches its delivered bodies.

The coordinator index correctly binds 38 files and excludes itself; those plus
the index cover all 39 coordinator files. Eight are exact copied scope/review
files, leaving 31 new coordinator records. Overall the candidate adds 1,092
files and modifies exactly three existing files: current restart README,
execution handoff and `plan/work-items.json`. There are no deletions. Its exact
tree has **4,704 files**. No other product source, application/crate, fixture,
contract, lockfile, toolchain, recipe, CI policy or attribute changed. Added
executable migration tools equal reviewed public author bytes. No runtime/cache,
bundle/archive or original-manual asset was added. Copied accepted public bodies
and the scoped coordinator records account for every added path; no private
history import or unrelated source import is present in this delivery delta.

## Graph, checkpoint and recovery semantics

All 1,508 frozen paths match original core `f2ef70f`, product and delivery
mode/blob/SHA256. All 47 criteria and dependency sets are unchanged. The other 40
complete task records preserve both values and exact serialized JSON fragments,
including all seven closed tasks R00/P01/S01/S02/E01/A01/O01. All 16 resource and
five release records remain unchanged. Revision 14 changes only the seven
permitted assignment/checkpoint records and the declared current reconciliation
metadata. The sole graph is `plan/work-items.json`; no old live graph was added.

All 18 source checkpoint artifact bindings match actual Git objects across
nsealr, hardware and Board SDK. Their immutable URLs match those objects. The
seven records preserve their distinct historical inputs: for example S03 keeps
its original source/review binding and separately reviewed comment correction,
T01 retains its older accepted preparation input, and P02's `f2ef70f` input is
confirmed by its actual input notes. Only A02 explicitly reconciles its old core
placeholder to the accepted pre-import source tuple.

The status descriptions are bounded: A02 remains running with zero criteria
closed; T01 has no implementation; P02 has planning evidence without runtime
qualification; H01 remains incomplete host/manual research; B01's four parent
criteria remain open, including H04 electrical pinning. S04 is **blocked**, has
no assignee/active author, preserves its terminal platform/source gates and
prohibits an alternate-model retry to evade the control. None of these source
checkpoints is imported as a new product implementation.

Preflight/materialization records bind the admitted bundle, new branch/worktree,
existing repository identity and unchanged source mains. Actual fetch/create
commands have intact logs; they do not reset main or fetch a whole private
repository. Earlier recovery evidence remains source-bound rather than being
claimed freshly repeated here. The short stop is historical: the leading
resumption receipt and current handoffs explicitly supersede it. No pause guard
or pause pipeline was introduced or started by this review.

All 26 local links in the two current restart handoffs and coordinator handoff
resolve in this actual checkout. They accurately distinguish candidate graph
state from adopted main, local source PASS from delivery review, and later
protected PR/main CI and closure gates. The main ref was independently observed
still at `f2ef70f`; the publication branch still points to this exact candidate.

## Independent affected validation and observations

I independently ran `make docs test` and all appended migration unit controls on
this exact worktree. Both exited zero: the affected target executes structural
validators plus five unit groups totaling 65 cases, and migration controls run
48 cases. The latter exercise real temporary-fixture admission/recovery,
corruption, destination/ancestor refusal, private-source and record-obligation
boundaries; they do not launch the project replay/pause pipeline. Exact copy,
frozen/graph/serialization, checkpoint-object and link checks also passed.
Author validation/materialization command logs were independently hash-checked.
No unchanged full product suite, replay/restoration or hardware operation was
repeated. Actual protected full PR CI and exact integration/main CI remain gates.

The final whole-candidate whitespace check exits **2**. The non-log source check
exits **0**. The final warning set contains **13 raw log files**: the historical
12-file staged observation plus
`validation-03/00-complete-staged-whitespace-observation.log`, which faithfully
copies trailing-space warning lines into the saved observation itself. The
author's 4,689-file check and 12-file warning snapshot remain correct observations
at their recorded time, before final scoped records/logs were appended. This
review separately checks all 4,704 final files and preserves the final 13-file
output. No raw byte, attribute or check was changed to hide warnings.

Early reviewer-probe failures were expectation mistakes: the copy preimage schema
uses mode/kind/blob while the prospective inventory separately binds length/hash;
the initial metadata whitelist omitted the required S04 blocker; and the first
whitespace comparison treated a historical staged snapshot as the final set.
The observations/corrections are retained in `probe-initial-failure.json`.
Corrected checks bind exact source preimages, explicitly allow only the recorded
S04 blocker metadata, and verify the single additional self-recording log.
No candidate file was edited to satisfy the probe.

The delivery passes this bounded review. A changed candidate invalidates affected
approval. Normal protected PR checks/review, normal merge, actual CI on the exact
resulting main commit and a separately reviewed closure/evidence-index change
remain required. Source notices/archive, registry publication, production keys,
fuses, manufacturing and physical qualification remain outside this verdict.
