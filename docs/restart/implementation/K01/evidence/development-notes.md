# Admitted K01 development observations

The pre-runtime 70-case inputs and first actual RED remain at commit
3a609e78f2e04e93feb31a053ee7dbd257177ac3. The first implementation checkpoint
adds the seven-kind inspector, original-scalar owner, explicit auxiliary source
and consuming engine-only output API. It is work in progress, not final source
acceptance, transport enablement or hardware/provider qualification.

Raw failures are retained. `catalog-development-01` found a test still assigning
an old normalized backend key to the newly original-scalar owner. The test now
assigns the original owner type and retains its wrong-key rejection obligation.
`signing-development-01` records an unnecessary completeness check mistakenly
expecting `Reader::object` to return a seen-bitset; that existing helper already
requires every member and returns unit, so the redundant check was removed.
`signing-development-02` records a test expectation error: intake at tick 10 has
deadline 110, so completion at 100 is timely. Its controls now use 110/111 for
late completion, preserving rollback/missing-clock negatives. The expected
caught panic in the first-clock test observes the real public call after consent
was consumed; it is not a failing test or production recovery guarantee.

`catalog-development-02`, `core-development-01` and `signing-development-03`
record the actual affected passing checks at their recorded dirty source hashes.
These are provisional development observations. Final source-bound runs,
independent checker adversaries, target link, coverage, all integration and stable
complete gates are still required. Whole raw logs are unchanged even where they
contain trailing blank lines; source whitespace is checked separately.

Metadata depth counts the root and each child value. A scalar at depth 9 rejects,
just as a container would. `metadata-boundaries.json` fixes literal finite-bound
expectations before that affected depth correction and its tests. The retained
preparation, original eight S03 vectors, thirteen K01 mathematical cases, three
identity expectations and twenty-seven negatives are not rewritten.

Subsequent development receipts preserve the actual coverage progression and
lint failures. `coverage-development-01` ran all tests successfully but report
creation failed because build/ did not exist; -02 reports the same unchanged
profiles after creating it. -03 onward add actual missing semantic/original-event
controls. The one remaining -10 miss was a failure while streaming an inner tag
at a partial canonical sink bound, resolved by testing every bound below the
independent fixture's exact canonical length; -11 measures100% on all12958 lines.
The walker depth and member-count checks were consolidated using the already
mandatory value-node invariant; no limit was enlarged or error case waived.
-05 retains a compile error from one missed mutable visitor borrow during the
shared-visitor refactor. -04's unused field warning was corrected. The critical
signing/visitor bodies now use borrowed trait objects to avoid separate parser
and signing-body instantiations per callback type; no allocation or new backend
was added. `lint-development-01` rejected a manual5|6|7 pattern; the equivalent
5..=7 correction passes -02 without allowances or changed lint gates.

`target-development-01` preserves the initial isolated probe's --locked refusal:
the historical S02 probe lock lacked the now-existing k256 dependency. -02
regenerates only the new admitted K01 probe lock offline, proves every registry
package equals the existing product lock, and successfully links the actual
engine. Root/host/historical locks, vendor/features and target are unchanged.
The final probe/source-bound target run remains required after this checkpoint.
The target probe is not executed hardware; its missing-provider assertions are
link-time code only, while the host provider refusal tests actually execute.

`checker-controls-01` actually rejects30 malformed/tampered input controls. The
strict checker validates record/effect structure before costly crypto mutation
checks, retaining all13+3+27 mathematical/identity/rejection obligations. The
original70-case source/RED component received distinct review2aaed50ae7c47a303ce79d3e0deae5d98a1d365b,
PASS_independent_expectation_component_only; that verdict does not accept later
runtime or full K01. The subsequent current-base Q01 delta is documentary only;
no mid-development rebase or inheritance of a later source acceptance is claimed.
