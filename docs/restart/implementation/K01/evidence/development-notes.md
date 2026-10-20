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
