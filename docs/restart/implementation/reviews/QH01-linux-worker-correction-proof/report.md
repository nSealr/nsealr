# Corrected Linux worker: affected proof review

Root reviewed frozen author candidate
`06d213fd46e654bfe2ac43e4a88963a346d35973`, tree
`c7a11c42776edabe3ca22226dce8c05c8460f850`, for packet correspondence.
A02 independently owns affected code review and runtime execution.

The [audit](audit.py) exited zero. [Validation](validation.json) records 263
manifest members plus the manifest itself, exact modes/sizes/hashes, the 113
additions and five modified paths, and 146 unchanged prior paths. All 136 prior
run files are byte-identical. Five pre-correction entry snapshots and four exact
copies of the blocking independent review retain their source roles. Original
expectations, parameters and session amendment remain unchanged. The regression
expectation and identical RED/GREEN probe match their pre-fix commits.

Four new command/source/summary bindings and 22 final trace bindings match the
recorded evidence. The RED receipt records stale acceptance after 8.275571 seconds
and exit 1; the same probe's GREEN records rejection after 8.275950 seconds and
exit 0, with known cleanup and reusable ownership. The recorded corrected author
campaign has 22 PASS cases. These are checked historical author observations;
this review executed no worker and grants no runtime or product approval.

One metadata-checker error is retained in validation: probe command receipts use
`harness_sha256`, whereas direct harness command receipts use `source_sha256`.
Inspection of all four new receipts established the explicit distinction; both
are compared against actual Git source bytes. No product, threshold or historical
result changed. No QR decoder, TypeScript port, ARM/Pi, secret isolation, physical
or full-task qualification is claimed. Protected integration and any release
remain separate decisions after independent runtime review.
