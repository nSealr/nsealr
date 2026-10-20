# A02 exact final review request

Review the published `restart/a02-rehearsal` author commit supplied by the
coordinator and isolated product commit
`daf8ba03a9eb820f99b0f1bf5c4f553a7961e008`, tree
`db0687a5ec15228e944360e00e391a4fff863f5d`. The author must not act as the
final reviewer. The [content manifest](final-review-package.json) binds the
complete report/evidence/tooling payload; it deliberately excludes itself and
this does not claim a review verdict. The coordinator must record the exact
published author commit and the distinct review identity before adoption.

The source is frozen at canonical core
`f2ef70f522af4977e15f81554a8c6eadcdbe8097` and selected hardware
`340697d6713a671e9e01b0dc874ec999ab071601`. The latest operational-policy
proposal at `7c9b9a9` supplies only current AGENTS/execution wording and the
new `execution_model_policy` field. No other pause-branch graph changes or
held S03/P02/S04/B01 branch contents are source inputs.

The [final report](final-report.md) and [five-criterion acceptance receipt](acceptance-receipt.json)
lead to the exact initial/final maps, declared transformations, full cold suite,
named case correspondence, failure/removal explanations, rights/notices and
interoperability handoff. The [39-patch replay/restoration](execution/rehearsal-04/result.json)
reproduces the exact commit/tree and all 7,943 allowed objects/330 commits.
The actually restored candidate bundle is protected at
`tools/migration/.runtime/rehearsal-04/candidate-recovery/candidate.bundle`,
SHA-256 `e4e28dc2fdee6aff9fc318eaa3e0ab254aa5aa3f18ddc44a82d492603cda5f03`.
The current candidate and restored repository have no remote or push URL.

The full cold suite actually ran at `2bb10013`; the later difference is exactly
four documentation files, explicitly checked with another passing `make docs test`
and the current reproduction-guide/shell checks. No executable input, fixture,
lockfile, toolchain or recipe changed after that complete run. All 47 task records,
seven closed tasks and 1,508 unique frozen evidence files/1,511 references remain
unchanged. Current policy changes no historical O01 criterion/model/evidence.

For independent reproduction, use the pinned interpreter and an absent owned
runtime destination; preserve the approved exact privacy postimages:

```sh
PYTHON=/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/python/bin/python3
"$PYTHON" tools/migration/replay.py --author-repo "$PWD" \
  --source-root /home/tux/nsealr \
  --privacy-root "$PWD/tools/migration/.runtime/privacy-01" \
  --destination "$PWD/tools/migration/.runtime/independent-final-replay" \
  --expected-target "$PWD/tools/migration/.runtime/rehearsal-01/repository"
```

Review privacy and rights as source selection requirements: selected licensed
private files only, no whole private history, no original private manual
addresses, preserved nested notices and independent oracles. Inspect all semantic
test changes against accepted obligations; equal names/counts alone prove nothing.
The failure ledger preserves unsuccessful runs and the correction mechanisms.

Author final reports/tooling are outside the isolated source tree to avoid
self-referential candidate evidence. Eventual integration must preserve this exact
candidate identity, append the reviewed final evidence and reconcile task state
once in its own explicit reviewed scope. Canonical main remains the sole adopted
plan until that atomic integration. The pause graph is an unmerged proposal.

The latest model policy defaults the coordinator and reviewer to Sol `xhigh`.
Any Astra exception needs a concrete assignment-specific complexity reason;
hardware/security category alone is insufficient. Prior runtime/review records
remain historical.

No archival, registry publication, force/admin merge, canonical reset or source
history deletion is part of this request. Local software proof does not qualify
live relay/browser sessions, physical review, camera/display/GPIO, production-key
custody, manufacturing or entropy. The inherited audit-index warning and Firefox
manifest gate remain recorded. Coordinator adoption and actual main CI are still
pending.
