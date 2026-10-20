# T01 selected-A provenance component review

**REQUEST_CHANGES** on candidate `0c4c223c94fb0b4b33e3a9fd571cf5fd88cfa4f4`,
tree `7abb5528256e46ccf6e1ffaf7aeaa35c3c043ebf`. Reviewer `/root/h01_sol`,
`gpt-6.1-sol` xhigh; author `/root/b01_final_review`. This is the distinct review
of the two-script component before its final artifact pin, not T01 acceptance.
The scoped product candidate is `2afbd78ca4eaccdab3f7b8ffa434a75b0b22ee15` on
base `793b4d4e800f3e18c1a625b074c0293dc5d974ab`.

## T01-PROV-01 — working executable mode can disagree with Git

`scripts/verify_contracts.py:130` maps a working regular file to `100755` when
**any** of its owner/group/other executable bits is set (`mode & 0o111`). Git
records regular executable mode from the **owner** executable bit. The promised
comparison with the literal approved tree can therefore accept a different
working Git mode.

The [public-fixture reproduction](reproduce-mode.py) uses the existing test
fixture and a deliberately pinned actual fixture tree. It approves `LICENSE`
as `100755` and first validates successfully. After `chmod 0645`, the checker
returns the same successful result, while actual `git diff --summary` reports
`100755 => 100644` and actual `git add`/`ls-files --stage` records `100644`.
Bytes, paths, manifest and the approved tree literal remain unchanged. The
[paired output](mode-reproduction.stdout.log) records the actual tree/blob and
Git observations; the [command receipt](mode-reproduction.command.json) binds
both reviewed scripts. Test-only pinning does not change the production pin or
any product file.

Correct the working mode classification to Git's owner-executable semantics.
Retain the ordinary `100644`/`100755` positives, mode-tamper rejection and exact
restoration. Add a real-Git comparison covering mixed executable bits so that
an approved `100755` file changed to `0645` rejects. Group/other bits alone do
not change Git's mode; this request adds no promise to bind all POSIX permission
bits. Preserve the existing source, schema, tamper and rebase obligations.

## Reviewed source and evidence

I read both scripts in full against the selected-A/strict-format2 section of
`integration/brief.md`, the accepted embedded schema and final current-spec
report, the original root admission and the component README/result/invariants.
The [source bindings](source-bindings.json) pin all primary inputs, verify the
original admission equals the candidate's retained copy, the strict expectation
schema equals the accepted schema, both scripts were still unchanged when
expectations were committed, all21 author-paired artifacts match their declared
length/hash, and all other paths outside the two scripts/scoped proof equal the
base. The delivery delta after product2afbd is14 proof-only files.

The implementation otherwise follows the selected authority model in the read
perimeter: the external literal tree is required, historical45/865 identities
stay metadata and permanent685/596 remain mandatory actual Git authorities;
HEAD, mutable manifest claims, environment and fallback refs do not select trust.
All Git reads disable replacement objects. The exact whole artifact path set,
regular Git modes and bytes include metadata and hidden entries; extra empty
directories, caches, symlinks, gitlinks and special files reject, subject to the
executable-mode defect above. The two current/script bytes are unchanged by this
review.

Strict parsing rejects duplicate decoded/escaped-alias keys, malformed UTF8,
unpaired Unicode surrogates, trailing data, nonfinite/fractional numeric tokens
and format-number coercion. Exact object keys, path/hash/mode types, four
provenance dispositions, immutable original/baseline bindings, maintained
adaptation, changed modified postimages, new authored absence, retired tombstone
absence and complete baseline/active inventories are enforced. Consumers use the
same pinned tree, exact bridge/engine/pi groups and nonempty unique safe patterns
that each match active inventory. These checks do not replace the unchanged
language/semantic coverage gates.

The [independent reviewer run](component-tests.command.json) passed all36 existing
component tests, including the retained24 methods and12 additions. Its actual
[Git observation](component-tests.stdout.log) confirms a divergent rebase,
identical approved subtree, cold fetch with only `refs/heads/main`, no remote,
alternate/shallow/graft state, four old commits absent with exit128, reachable
permanent fixture authorities, rejection of wrong/missing anchors and tampering,
and successful exact restoration. This exercises real Git in disposable
synthetic repositories, not real delivered-main reachability or device/protocol
behavior. The passing tests did not detect T01-PROV-01.

The actual [source command](source-unbound.command.json) exits1 with
`reviewed artifact subtree OID is unbound; final stable pin required`.
`ARTIFACT_TREE_OID=None` remains unchanged and fails before untrusted reads.
This required refusal is **not** source PASS. No other blocking finding was
identified within this component perimeter.

## Limits and next review

The author retains the two-script ownership until root hand-back. Review only
the correction and affected tests/proof next, reusing these unchanged source
conclusions. Root still supplies the exact literal from a02's stable real
artifact, reviews that pin/artifact delta, and owns all stable acceptance,
protected integration, actual normal-rebase/main-only verification and resulting
main CI. No adoption, consolidation, task closure or release is approved here.

No full `make ci`, current artifact/Pi acceptance, all42 cases, all170 semantic
projection obligations/three helpers, target or physical gate was run or inferred
from synthetic fixtures. No hardware source research occurred. A read-only review
inspection initially assumed only3 proof paths after product2afbd; actual Git
showed14, all in the assigned proof prefix. The failed assumption and exact
correction are retained in [inspection-correction.json](inspection-correction.json),
without changing product or acceptance requirements.
