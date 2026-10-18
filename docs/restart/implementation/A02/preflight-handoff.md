# A02 first tooling/preflight candidate

The accepted four-file specification at `709f09183e7d54937a8562151dd5ac1fbeefc615`
is unchanged. The distinct passing report is copied byte-for-byte in
`spec-review.json`, with its original commit/path/hash in
`spec-review-provenance.json`.

Tooling source is committed separately at
`e2fae138ac545d3cf5f848ecc0aaea7f8365c394`. This increment implements inventory and
blocked preflight only. There is no import, assembly, bundle creation, publication,
canonical-source mutation or workflow edit. The synthetic Git repositories used by
unit tests contain only small purpose-written test fixtures.

The provisional inventory uses actual public main
`7b5553685dac56029a4379be12054154b6b5e0b5`, rather than the obsolete preparation
base, plus the other exact pins in `preflight-inputs.json`. It explicitly does not
admit that main as the eventual import tuple. The corrected S01 candidate's
distinct review is recorded as context; final adopted main and successful main CI
remain required. A later S03 merge must be preserved through a newly pinned
inventory and affected checks, never overwritten from an older source tree.

Executed evidence is under `preflight-evidence/`. The existing R00 Python 3.12.15
runtime was reused explicitly and its binary hash recorded. All eighteen tooling
tests pass. Tests exercise hidden tracked files, changed/deleted frozen evidence,
missing/duplicate closure entries, reviewed-commit mismatch, symlinks and unsafe
paths, private-default exclusion, unread excluded private blobs, destination
collisions, duplicate JSON, manifest/tree/license drift, protected output
permissions, dirty-worktree independence, and tampered inventory rejection.

`prepare` completed with 5,335 classified paths, 281 statically discovered test
files and no destination collisions. The current graph contributes 1,114 closed
artifact references, covering R00, P01, S02, E01, A01 and O01, with 1,111 unique
artifacts. All referenced hashes and checked result-manifest bindings agree.
Twenty core snapshot/source differences remain because the provisional main
precedes final S01 adoption; companion/Pi copied fixtures match the chosen specs
pin. No source bytes were repaired or silently taken from another worktree.

`preflight` repeated the frozen inventory check and returned the documented code
2: inventory correspondence holds, import is blocked. The full per-file map,
notice candidates, static test labels, evidence/link closure and private bundle
plan remain inside a mode-0700 ignored local runtime; its files are mode 0600.
Only the reviewed-source identifiers, public summary and artifact hashes are
committed. The 4.45 MB local inventory is not copied into public Git, because it
also contains excluded private path names and local refs.

This is not a complete test-case or rights review. Static test labels include
historical/vendor tests and cannot substitute for collected runtime cases or
before/after behavioral equivalence. Root license checks identify source notices;
selected-file nested notices and privacy still need their recorded review.
Likewise, the focused evidence checker does not replace the full graph validator
or substantive closed-task review.

Before import: receive and reconcile final adopted S01 main/CI, update source pins
and complete evidence closure, verify the corrected helper/default-bootstrap tuple,
finish selected-file rights/privacy and case dispositions, reconcile remote refs,
and obtain the required admission review. The script currently cannot enable
import even if a manifest flag is changed. Further implementation and the actual
complete after-migration suites remain unexecuted.

When actual migrated CI is changed, evaluate ordinary `push.branches: [main]`,
`pull_request` and `workflow_dispatch` to avoid duplicate branch-push/PR full checks
while preserving required verify/application checks, normal reviewed merges and
actual main post-integration CI. This tooling increment leaves CI unchanged.
