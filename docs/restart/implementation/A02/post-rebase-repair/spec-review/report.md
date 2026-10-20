# A02 immutable-anchor repair — preparation review

**PASS_preimplementation_scope_only** for exact preparation
`7618ea42a86a1c25790955090b2dee3350943ff8`. No scope blocker found. This permits
only the bounded implementation described by its brief; actual failed main CI
remains unresolved until repair, exact final review and required CI pass.

Reviewer `/root/b01_final_review` is distinct from specification author `/root`.
The fresh review branch is `review/a02-contract-spec`. No product code, fixture,
manifest, source main or previous review worktree was changed.

The captured API files and all nine ZIP members match their preserved hashes;
the ZIP SHA256 is
`0c074b0fdd3253b5518683cd5ba853db58b0c095c264167f87cdb0c2f7fe291d`.
Actual push run39408038674 is a failure on
`d931277bebbc5f43514b0e8438d65fb60603fa35`. Bootstrap succeeded. The complete
product acceptance log has two terminal Make failures: `test` invokes
`verify_contracts.py` and cannot `git show 5cb16...:.../manifest.json` (exit128);
integration step1 calls the same validator and repeats that failure. No distinct
terminal cause was found in the captured job. Integration steps2–17 were not
executed; they cannot be represented as passing from this run.

The code explains the ancestry-dependent failure. `INITIAL_IMPORT` currently
serves both as historical manifest identity and as a Git lookup source;
`BASELINE` is also dereferenced from the cold product checkout. The first failing
baseline guard prevents the log from reaching the old-import lookup. Source
inspection and ancestry establish that second affected lookup; it is an inference
from code, not another observed CI traceback.

Independent Git checks verified both entire-tree equalities, artifact modes/blob
inventories, inventory hashes/counts and reachability against actual adopted main:

| Historical object | Adopted object | Equal whole tree | Artifact rows |
| --- | --- | --- | ---: |
| `86569e073da4faec0811d67137bbb0fd4f74c7c6` | `68508ea1eea1e07b0064fadd65b33433d72701f8` | `59008a6e0fdb4475d03bbe4f1761f8514f552e84` | 260 |
| `5cb16cbaffc6b90ca9dfbb1ce7a5388e731d1ae0` | `59653fcc15c4cbc21a39d0a0dd5548abe46165b0` | `d3ee175dbdcd91bcd01f1cde50be2451251ebd96` | 263 |

Both adopted objects are ancestors of main; neither old intermediate object is.
The failed main's entire tree equals the reviewed adoption tree `e67b1337...`.
The preparation delta contains only its two new documentary files. All four
audited checker/test/manifest/consumer input hashes match actual main objects.

The brief correctly separates immutable historical identity from immutable
runtime comparison anchors. Keeping the original `86569...` manifest value and
strict identity check, while pinning the exact adopted source and postimage,
preserves provenance without extra branch fetches, dynamic ancestor selection,
HEAD-based trust or accepting a rewritten manifest. Artifact bytes and consumers
remain outside writable scope. Existing frozen files/closed records, historical
rehearsal/template/patch bytes, apps, locks, toolchains and CI are protected.

The required acceptance is adequate and remains unperformed: retain actual RED
from a main-only cold fetch; patch historical metadata and runtime anchors
separately in isolated tests; exercise a real rewritten-history/cold-fetch Git
regression with old objects absent and adopted objects reachable; reject missing
and incorrect source/postimage anchors; preserve every existing positive and
negative `test_contracts.py` obligation. No count of “48 contract tests” is
adopted: 48 referred to unrelated migration controls. Those unchanged controls
need no repetition without a concrete affected concern.

Affected docs/test and artifact tests, all 17 actual integration obligations,
fresh committed-repair cold validation, inspection for the same reachability
class in remaining current executable dependencies, exact final-diff review and
actual protected PR/main CI are explicitly required. Discovery of another issue
must be reported rather than silently expanding this repair. These requirements
cover the branches masked by the failing baseline guard and the incomplete
integration run. Scope PASS does not predict their outcome or admit S03 work.

The read-only probe and preparation whitespace check passed. No product tests,
cold-fetch RED, implementation, replay, CI rerun, merge, A02 closure or physical
qualification was performed by this review. Exact input/capture bindings and
probe outcomes are retained beside this report.
