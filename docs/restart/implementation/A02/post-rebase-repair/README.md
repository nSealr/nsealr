# A02 contract-anchor forward repair

This repair fixes the deterministic cold-checkout failure of adopted main
`d931277bebbc5f43514b0e8438d65fb60603fa35`. Protected PR31 CI passed before the
normal rebase, but actual main CI39408038674 failed when the immutable checker
looked up rewritten intermediate commits. The artifact and whole paired trees
were unchanged. The [admitted brief](brief.md), [source audit](source-audit.json),
[distinct scope review](spec-review/review.json) and
[coordinator admission](scope-admission.json) precede implementation.

The historical manifest identity remains literal
`86569e073da4faec0811d67137bbb0fd4f74c7c6`. Runtime Git comparisons now use the
equal adopted source and postimage trees at permanent main ancestors:

| Role | Historical intermediate | Permanent adopted ancestor |
| --- | --- | --- |
| Source postimage | `86569e073da4faec0811d67137bbb0fd4f74c7c6` | `68508ea1eea1e07b0064fadd65b33433d72701f8` |
| Reviewed baseline | `5cb16cbaffc6b90ca9dfbb1ce7a5388e731d1ae0` | `59653fcc15c4cbc21a39d0a0dd5548abe46165b0` |

Only `scripts/verify_contracts.py` and `scripts/test_contracts.py` change product
controls. Metadata identities, manifest equality, source/postimage hashes, file
inventory, modes, hidden-file checks and consumer scope remain strict. Current
restart README/handoff describe the observed failure and remaining gates. The
whole contract tree, plan, seven closed records and 1,508 frozen evidence files
are unchanged; see [scope invariants](scope-invariants.json).

Actual local acceptance:

- [24 artifact tests](targeted-checks/commands.json) passed. All 20 original test
  bodies are unchanged. Four new real-Git controls prove rewritten-history
  validation with historical metadata, missing-anchor rejection, wrong-source
  rejection and wrong-postimage rejection.
- [Affected `make docs test`](precommit-checks/commands.json) passed after the
  current README/handoff edits. Product/current-docs whitespace checks passed.
- [All 17 retained integration steps](integration-checks/commands.json) passed
  under the recorded pinned user-space tools. These include the real contract
  provenance gate, Bridge/browser flows and Pi/vault integration.
- [A fresh public fetch of committed source repair `63ada7b4`](cold-candidate-green/summary.json)
  passed the real contract and frozen-evidence checkers. Only its selected ref
  exists, all 8,748 fetched objects are reachable from it, both old intermediate
  IDs are absent, and the two permanent anchors plus original source `f2ef70f`
  are present ancestors. There are no extra refs, shared/hardlinked objects,
  alternates, shallow boundaries or grafts. Manifest bytes and historical ID are
  unchanged. The follow-up proof commit changes no tested script/current-docs
  bytes; [result.json](result.json) binds the source hashes.
- The [current executable dependency audit](runtime-dependency-audit/summary.json)
  found no other broken historical Git dependency. The remaining frozen-evidence
  source `f2ef70f` was proved reachable and validated in the same cold fetch.

The [failed hosted run](failed-main-CI/copy-inventory.json) and
[actual cold-main RED](cold-main-red/summary.json) are preserved. The hosted ZIP
is byte-exact SHA256
`0c074b0fdd3253b5518683cd5ba853db58b0c095c264167f87cdb0c2f7fe291d`;
all four API/log captures and nine decompressed log members passed the recorded
bounded privacy check. [Copy inventories](local-proof-copy.json) select only
public command/environment/log proof, with no runtime Git objects or caches.
The first scope diagnostic incorrectly equated filesystem0664 with Git100644;
the corrected regular nonexecutable check passed. The
[all-staged whitespace diagnostic](all-staged-whitespace.json) exited2 on two
unchanged raw logs containing the validator's emitted trailing space. Their
hashed bytes are preserved.

No unchanged migration48/replay or local full product suite was rerun. A distinct
exact final-diff review, actual full protected repair PR CI, normal merge and
actual corrected-main CI remain required. A02 stays incomplete and S03
implementation stays held until those and its own admission gates pass. This
repair closes no task/release and authorizes no archive, registry publication or
physical qualification.
