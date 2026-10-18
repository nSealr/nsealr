# A02 two-file pre-import privacy exception

This addendum narrows the exact-copy sequence in the approved `709f091` brief for
two selected CC0 lab files only. The four approved preparation files remain
unchanged. It does not authorize target assembly or full migration admission.

Source is `nSealr/lab` at `3303ab17a28ed32419576627d5abb93db3999635`.
`scripts/integration_feature_matrix.py` and
`tests/test_integration_feature_matrix.py` contain three addresses of excluded
private documents. Copying their original bytes into a public import commit would
publish those addresses even if a later commit removed them. Preserve the source
Git objects in protected recovery storage; never publish the original patch or
the excluded addresses.

Before the first public import commit, run the source-bound sanitizer from tooling
commit `325448c126ba1bc9f95a8a4ed593b6105a331986`. It reads the three string literals
in the helper's `LAB_DOCS` assignment and replaces their seven occurrences across
the two files with `docs/historical-feature-contract-01.md` through `-03.md`.
It edits only those AST literal spans: three in the helper, four in its tests.
The public sanitizer contains neither original addresses nor their basenames.
No placeholder documents, private history or compatibility tree are created.

The [exact source and result hashes](privacy-evidence/summary.json) bind both
Git blobs, original SHA-256 values, sanitized SHA-256 values, CC0 notice and the
protected full patch. That patch has SHA-256
`105c114f92f96fa18b7ca54dd3245658ab5ba94722323af2718f2693fc49734d`.
It is retained only at the owned ignored runtime `privacy-01/private-full.patch`.
The independent reviewer must inspect that protected patch and source objects;
the public hash alone is not substantive review.

All nonliteral bytes remain identical. The AST is equal under the inverse literal
mapping, and all five original and five sanitized unit cases pass with pinned
Python 3.12.15. This establishes bounded code correspondence under the address
renaming. It does **not** establish byte equality or unchanged external document
addresses: the original addresses intentionally cease to resolve in the sanitized
copy. The initial import map must record this explicit exception and compare the
two imported blobs to the exact sanitized postimages. Every other selected blob
retains the exact-copy gate before its separately declared transformations.

Later behavior adaptation remains separate. The two tests requiring references
in historical private prose are explicitly retired, with their source identities
kept in the case ledger. Their current replacement is validation of the actual
authoritative artifact and live owner/profile contract, including missing inputs
and stale contract references. The three useful feature-matrix tests retain their
shape, missing/extra profile and incorrect-owner obligations, adapted to accepted
restart requirements. Removing the obsolete five-family taxonomy is a functional
change requiring its own patch and after-migration tests; this privacy exception
does not approve it implicitly or attribute it to old byte-equivalence evidence.

The coordinator independently inspected the protected pre/postimages and reran
both five-case suites. Its narrowly scoped review receipt must be bound to this
exact addendum and summary before import. All other admission conditions remain:
frozen current source refs, full closed evidence, selected-file rights/map,
original-versus-new case/gate dispositions, restored recovery bundles, distinct
whole-package admission review and the coordinator's record. Complete actual
after-migration acceptance and final review remain mandatory.
