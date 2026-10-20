# A02 coordinator adoption — specification for distinct review

Prepared by `/root`, 20 October 2026. This is a proposed concrete integration
scope under the existing maintainer authorization, not executed adoption,
rehearsal acceptance, a task closure or permission to bypass protected checks.
The canonical source main remains frozen at `f2ef70f522af4977e15f81554a8c6eadcdbe8097`.

## Exact inputs and allowed publication

- Reviewed source candidate to be accepted: isolated product
  `daf8ba03a9eb820f99b0f1bf5c4f553a7961e008`, tree
  `db0687a5ec15228e944360e00e391a4fff863f5d`; 39 declared transformations.
- Author reports/tooling: `bb033619b5346302833d717eb501bfa4e3653a1b` on
  `restart/a02-rehearsal`. Content-manifest SHA256:
  `38b2fb69ef3f1e8a2414d168b005d6f674e2eabebe84d252f2239494cea0917e`.
- Actual restored candidate bundle:
  `a02/tools/migration/.runtime/rehearsal-04/candidate-recovery/candidate.bundle`
  under the local goal directory; SHA256
  `e4e28dc2fdee6aff9fc318eaa3e0ab254aa5aa3f18ddc44a82d492603cda5f03`.
- The independent final rehearsal review must bind **both** exact source and
  author commits and actually pass before materialization/publication. Its
  enclosing review commit and file hashes will be pinned in the adoption receipt.
  Review must not be guessed from a pending assignment.

[a02-adoption-payload.json](a02-adoption-payload.json) is the prospective exact
append, derived from Git objects rather than mutable worktrees. It binds all 983
public author files: 982 content-manifest members plus that manifest itself.
Seventy-three already match the product; 910 are additions; there are **no
replacements**. The namespace is only `docs/restart/implementation/A02/` and
`tools/migration/`. All modes are regular files; no runtime/cache/private bundle
or private history is allowed. Original manufacturer bodies are not allowed.
This is the already-public durable proof/tooling payload, not a second product
source tree or a copy of ignored build outputs. Preserve required failed logs.

## Materialization after passing scope and rehearsal reviews

1. Recheck main, repository identity/visibility, clean worktrees, free disk,
   bundle hash/refs, exact allowed objects and product ancestry. Stop on drift;
   never replay an old tree over new merged code. Preserve the author's no-remote
   repository unchanged. Import the verified candidate bundle into the existing
   canonical repository as new branch `restart/a02-consolidation`, with worktree
   `/home/tux/nsealr/.restart-tools/goal/a02-adoption`. No reset/force-push, whole
   private repository fetch, source settings change or new repository identity.
2. Append the prospective payload byte-for-byte from the pinned public author
   Git objects. Before/after mode/hash and scope must equal the manifest. Copy
   only the pinned passing final review's report/receipt/probe/log files under
   `docs/restart/implementation/reviews/A02-final/`, with a separate exact copy
   inventory. A changed/unlisted/escaping file or collision stops the append.
3. Write coordinator receipt, payload/review-copy verification and current
   adoption handoff under `docs/restart/implementation/A02/coordinator-adoption/`.
   Bind original full-suite source, documentation-only equivalence, source tree,
   author/review commits and this scope. The enclosing Git commit identifies new
   receipts; do not invent a self-hash or a future CI result. Update only current
   `docs/restart/README.md` and `docs/restart/implementation/handoff.md` to lead to
   actual adoption state and the sole graph. Do not rewrite frozen evidence.
4. Reconcile `plan/work-items.json` with actual assignments once. Keep exactly 47
   tasks, their criteria/dependencies unchanged, all seven closed records and
   1,508 frozen files unchanged, and all 16 resource/five release records unchanged.
   The pause graph is a proposal, never another adopted tracker. Record actual
   A02/S03/T01/P02/H01/S04/B01 checkpoints with source-bound references. Previously
   ready P02/S04/B01 work was assigned; show its incomplete state honestly. S04's
   interrupted research has a recorded platform/source gate and no active author;
   do not retry via another model to evade that control. Keep **A02 unclosed** in
   the initial adoption PR. No new release/physical readiness or B01 completion.
   Preserve historical O01 model records; current policy remains Sol `xhigh`.
5. Validate exact append/closed-evidence integrity, current links and the sole
   graph; run affected `make docs test` plus the appended migration tooling's
   meaningful controls. Compare the final diff against the reviewed product:
   no crate/application, fixture, lockfile, toolchain, recipe or unrelated owner
   change is authorized. All added executable tooling must equal reviewed author
   bytes; current metadata/prose changes are explicit in the receipt.

## Final adoption review, protected delivery and closure

Obtain a distinct review of the exact materialized adoption diff, including
receipts, copied evidence and graph reconciliation. This is separate from the
rehearsal-source review: appending evidence and writing coordinator metadata
changes the delivery candidate. Changed content invalidates affected approval.

Publish a normal PR from `restart/a02-consolidation`, preserve branch protection,
and require its actual full CI and independent review before normal merge.
Never substitute the earlier local full suite for this PR or actual main CI.
After merge, inspect the run for the exact main integration commit. If it fails,
preserve the log/failure, repair through normal reviewed changes and keep adoption
unaccepted; do not close A02 or archive sources to make the checkpoint look done.

After actual main CI passes, prepare a separately reviewed closure metadata
change: bind all five unchanged A02 criteria to exact rehearsal/review/integration
evidence, update the derived evidence index using its supported future-closure
path, and record actual integration/CI identities. Preserve all previously closed
records. No closure is authorized without the exact review and actual CI proof;
the initial publication PR need not pretend those future results already exist.

Source redirect notices/archival and package registry releases are **excluded**
from this scope. They need their own concrete dispositions/current backups and
normal reviewed changes afterward. Hardware/Board SDK/S03/P02/T01 work remains
outside the product import until its own actual integration. No manufacture,
purchase, fuse, production-key or physical qualification action is included.

Recovery uses ordinary Git: source main and the restored candidate remain intact
before merge; failed publication branches/evidence remain inspectable. After any
merge, use a reviewed forward repair/revert that preserves history and current
task/evidence validity. Do not delete/reset history or discard the failed proof.

## Affected source correction before scope acceptance

The original full substantive review anchor is author `f9a09ba`; final exact author
`bb03361` corrects three files: stale pending-ledger prose in the final report,
its derived current progress-index hash, and the content-manifest binding/receipt.
Independent review caught the intervening stale index at `c9958ec`; that finding
and source state remain preserved. All 755 current artifact hashes and 982 package
member hashes now verify. The isolated product and all other payload bytes/modes
remain unchanged. The final reviewer checks this bounded delta and binds the
corrected author; the scope reviewer checks the prospective-map update. No
unrelated suite/replay or historical command/result is rewritten.
