# Independent review of K01 preparation

Reviewer: `/root`; author: `/root/b01_final_review`. Candidate
`a783fd37033f63d04e27b6855ad064b7402ce428`, tree
`561cbd304c107a6a105e75ec1b5c73183d8765ac`, parent actual S03 main
`dbad656997ad8cf9024ca1489291f5f1d4d3094a`.

**REQUEST_CHANGES — specification/integration instructions only.** No K01
implementation, target execution or physical acceptance was reviewed or claimed.

## K01-SPEC-01 — proposed new-kind oracle command cannot run

`acceptance-plan.json`, command phase “independent new-kind output”, proposes
passing the new independent-inputs.json directly to unchanged S03 oracle.py
`--check`, stating that the checker supports the vector-row format. Although the
mathematical row fields are compatible, its rejection-control construction is
not: S03 oracle.py uses substitutions specific to a first fixture with kind 1,
created_at 0 and empty content. K01's first template has kind 0, a nonzero time
and content `{}`. Its first supposed negative mutation therefore leaves valid
input unchanged and fails with `AssertionError: ('accepted invalid input', ...)`
before comparison with observed event output. Later substitutions have the same
problem. Adding the adjacent key witnesses does not correct this.

The bounded [experiment](evidence/oracle-compatibility.py) reproduces the exact
failure using explicitly synthetic public expected witnesses only to reach the
checker stage. [Result](evidence/oracle-compatibility.json) and unmodified
[stderr](evidence/oracle-compatibility.stderr.log) distinguish this verifier
integration defect from a product defect. Synthetic witnesses are **not**
observed K01 output and cannot satisfy a runtime criterion.

Required correction before specification acceptance: describe a viable scoped
K01 observed-output check, reusing the existing pinned canonical/reference
primitives and independently chosen explicit negative cases. Preserve the exact
historical S03 oracle, its eight fixtures and their original separate command.
Admit any necessary narrow K01 checking code in its future runtime scope and
retain all signature/ID/canonical/key/auxiliary and adversarial obligations; do
not reorder fixtures merely to evade hardcoded controls, delete negative cases
or claim a future checker already passed. The checker itself need not be
implemented before the actual T01 dependency is adopted.

## Applicable review evidence

The six unchanged criteria match the actual base graph. All 17 selected Git
file bindings, nine whole-input object identities and five prepared-file hashes
were checked exactly. All seven primary NIP bodies were re-used from the fixed
cache and checked against the supplied lengths/SHA-256; the new follow,
deletion, repost, reaction and relay-list semantics were compared with those
bodies and the accepted P01 event-review contract. Existing S03 authority/parser
and S02 entropy/backend work is reused for unchanged portions; targeted current
owner, raw signing/verification and normalization source was examined.

The experiment separately recomputes all 13 new canonical IDs/raw signatures
from Python JSON/hashlib and the hash-checked upstream BIP340 reference, and all
three original/normalized scalar witnesses. These preparation values agree.
The distinct inner repost author is scalar 1, whereas the outer signer is
scalar 3. The auxiliary-one control has the same event ID and a different
correct signature. Semantic negative expectations remain unexecuted against
future K01 code.

Original-scalar retention, one-use burn before callbacks, complete inspection,
fresh completion checks, fallible auxiliary input, bounded scratch inventory and
the link-only initial target are sufficiently scoped for preparation. Backend
scratch erasure, actual entropy, timing/stack and physical profile guarantees
remain explicitly open. T01 adoption and one affected API reconciliation are
still required before runtime implementation. No other blocker was found in
this bounded preparation review; the affected correction needs review, not a
repeat of the unchanged mathematical/source checks.
