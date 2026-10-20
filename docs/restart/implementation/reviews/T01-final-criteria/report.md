# T01 criteria and proof review

**PASS_criteria_source_only** on delivery
`e83c49d97efcbec4fb54c11609c0d2d21e687719`, tree
`f1c06800f5950aac8efe60f11c76c315d77f202e`; product
`c4a2aa8d6567369caa52d7e0680e7581c2a554c3`, artifact subtree
`b629e75d18190ded2403ffabe965b595a9bcf6a6`. No blocking finding was identified
in this criteria-to-proof perimeter. This is a distinct assessment of source
coverage and evidence composition, not protected adoption, task closure, hosted
CI acceptance or qualification of a signer/device.

The five exact current acceptance strings and the42 scenario dispositions are
in `criterion-assessment.json`. I followed the primary test calls and assertions,
their independent inputs and actual command receipts. An ID, selector or
projection entry alone was not treated as execution proof.

| Criterion | Source and assertion basis | Result and limits |
| --- | --- | --- |
| Profile-specific requirements and distinct states | Rust `assess_profile` tests run all four profiles, remove each required group and assert the specific blocker; independent availability/verification tables and reported-feature contradictions remain separate. Strict metadata parsing rejects authority/evidence assertions. | PASS source. Typed local observations are caller-owned inputs; wire claims do not construct verified evidence or consuming device authorization. |
| Explicit no-SE; no method/custody downgrade | `required_component_and_custody_never_fall_back` checks absent/unknown/wrong/failed custom components, retained custom custody and wrong custody. Account/profile/manual-only and route mismatch tests refuse use without operation writes; shared policy tests preserve QR manual/no-grant restrictions. | PASS source. Conformance checks do not establish physical SE, firmware, storage or key custody. |
| Versioned Bridge routing and local limits | Actual async service calls reach recording USB/QR adapters and the real serial driver wrapper; independent signed response, expected identity, route/catalog/algorithm/codec/limits fields, stale observations and before-write hooks are checked. Boundary/clock/reservation assertions cover refusal and recovery. | PASS source. Host hook revocation is not backend authorization revocation; recording ports and the seven-page local plan are synthetic. |
| Common independent contracts with distinct timing/custody | Common artifact data feed retained Rust/Bridge/Pi/SDK/integration tests. The QR recording positive uses volatile custody and a separately lowered deadline. Fixed expected replay and data-only projection remain independent of production parsers/renderers/signers. | PASS source. External provenance/pin and Pi component reviews are composed below; no new judgment of those author-owned components is made here. |
| Separate primitive, context and workflow; bounded unsupported operations | Protocol helper calls distinguish all three message axes, reject contradictory dependencies, accept only the exact synthetic workflow name and reject another name. Actual service calls refuse unadmitted DM/seal/setup/AUTH and unsupported primitive/export methods before writes. Limits and resource observations remain bounded. | PASS source. D-04 is eligibility only; D-05/06 are routing refusals only. C02 crypto/context/relay/publication and physical qualification remain open. |

The Rust profile test source was read through its actual `assess_profile`,
`ReportedFeature::validate`, expansion and `size_of` assertions. The complete
client profile-dispatch tests were read through actual service calls, write/start
counters, response verification, mutation loops, clocks and promise settlement.
Driver/transport controls were checked at their actual call sites. Metadata
semantics reuse review572 on identical blobs:17of18 remain identical; the account
recovery-schema change is covered separately by root9bb. This does not relabel
the earlier metadata review as a review of changed recovery bytes.

The existing component reviews retain their own candidates and scope:
metadata572, service H01203, portable/protocol rootbf21, Rust correction root187,
Pi rootdf1, provenance H01042 and artifact/pin root9bb plus root's literal
application receipt. I did not re-review Pi, service implementation or the two
provenance scripts I authored. Their external reviews and root's integration
verification remain necessary; hashing a case source reference is only binding
verification, not a fresh semantic approval of that source.

The suspended-discovery proof is real on the current test afterimage: a valid
compact get_capabilities starts one adapter operation; while its promise remains
pending, further discovery/public-key/signing requests refuse without another
start or write. Actual settlement releases the slot and fresh discovery succeeds.
The focused receipt records **1 passed,18 unselected**, with a separate typecheck
success and root39ef affected review. Its actual identity remains d234 plus the
recorded test-only diff, subsequently committed as c4. The old discovery-flood
label is not credited with this missing behavior.

The broader proof is compositional. Full stable `make -k ci` on ae340 exited2;
its three failed Rust recipes and raw logs remain preserved. The actual recorded
Bridge725 plus one optional-live-relay skip, Pi162 and all17 retained integration
steps passed in that campaign. Only four reviewed Rust paths changed for d234,
whose complete affected `make rust-ci` passed. The later fifth non-proof path is
the current discovery test, covered separately above. No broad campaign is
relabeled as a fresh c4/e83 run or as hosted/protected CI success.

## The170 mappings and three helper mechanisms

All170 original mapping objects remain, with119 semantic dependencies and51
independent preimages. Only48 projected values actually change;119 is not an
execution count or a changed-byte count. I ran only the existing unchanged
data-only projector into a disposable directory and checked all179 outputs:
170original projections, five added data rows, three helper files and the
unchanged S03 vector byte-copy. Hashes and sizes match the source-bound postimage
record. This projection run proves extraction/binding, not behavioral success.

162original output names have literal references in retained Rust test sources.
Eight remaining outputs are historical development-gate strings whose admitted
disposition is KEEP_HISTORICAL_STATUS_VALUE_ONLY_FOR_REJECTION_NO_READINESS.
They remain inventory identities, not eight executed gate checks. Actual
protocol tests reject both numeric2 and historical get_signing_status requests;
the actual CLI integration rejects the retired command without writing a request
and separately checks the numeric2 discovery positive. No current path interprets
those retired strings as readiness, physical approval or authority. The retained
source-public-key diagnostic test still asserts that the selected account has
no verified proof.

The three helpers extract fixed data only. Their actual consumers assert:
basic/tagged review request IDs, approval digests and every summary page;
detail-vector digests, titles, lines, styles, actions, indicators and logical IDs;
and policy proposal IDs, digests and complete pages, including trusted-review
wrapping in tests. They do not generate expected answers from the implementation
under test or supply actual device consent. The original S03 vector byte-copy
remains a separate independent expected input.

The earlier root3653 fixed-input replay is still applicable: all92 current
postimage hashes match its recorded bindings, including the four explicitly
reviewed error-message-only negative dispositions and six request-bound digest
pairs. Its initial wrapper failure and correction remain historical. I did not
repeat that replay. All42 original semantic case objects retain exact values and
order from bb20; this fact alone is not42 executions. The behavioral conclusions
come from the inspected calls/assertions and their actual recorded campaigns.

P-08 does not implement or qualify a production image/firmware/SDK/procedure
evidence loader. Its scoped result is conformance-production refusal, unknown
local-evidence blockers and rejection of metadata evidence claims. L-07 records
host typed layouts and finite serialized/count reservations, not exact VM heap
bookkeeping, MCU stack/RAM, latency or an attached sample. D-04 does not execute
peer/sender copies or10050/22242. D-05/06 do not prove cryptographic substitutions,
AUTH, mailbox discovery or publication. Those limits are part of this verdict.

`probe-result.json` binds13 case-reference paths and seven command/log pairs,
checks current independent-data bindings and records the projection result.
The probe's JSON-only read of the fixed-replay output correctly skips its actual
one-line preamble; no historical raw file was changed. No scenario suite, full CI,
hardware test, source verifier, graph edit, criterion closure or product change
was performed here. Root retains final delivery/scope verification, normal
protected PR/full CI, actual rewritten-main source/reachability and resulting-main
CI before adoption or closure.
