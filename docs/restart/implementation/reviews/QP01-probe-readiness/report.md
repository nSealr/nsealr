# Pi setup probe: independent correction review

**PASS_scoped_Pi_probe_readiness_correction_only**, with no blocking finding,
on candidate `4ab6e46e3f6e332d38bb049ed4988bec9f3550cf`, tree
`06190f8ed998edf76092baefadc8887fd88b91bd`. Root reviewed the complete product
delta and added tests independently of B01. This is acceptance of two preliminary
configuration guards, not QP01 or hardware qualification.

The boot guard now parses only its declared small text subset. Whole-line
comments cannot enable a setting. Contradictory target assignments and unresolved
includes, filters, overlay scope, combined parameters, other directives, long
entries and non-ASCII syntax cannot produce pass. The 80-character limit is a
conservative supported-input choice, not an asserted firmware capacity. This can
block legitimate configurations outside the subset; it does not evaluate their
actual firmware effect or current loaded state.

The service guard accepts only explicit disabled/masked plus inactive responses
with the supported return-code pairs and empty diagnostics, for both queried
unit names. Full responses remain visible; unknown errors and inconsistent or
multiple states cannot become evidence of safety. Unsafe state text is a
conservative refusal even with contradictory diagnostics. The official
[systemctl manual](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html)
distinguishes enablement from activity and warns against relying on return codes
alone. Root reread these sections; the code uses both fields. The exact rc1/rc3
pairs are the probe's narrow supported subset, not a universal portability claim.

Root executed [70 independent cases](independent-results.json), including valid
profiles, the three original false-positive classes, unresolved boot constructs,
individual failures of either query on either service, unexpected diagnostics,
states, return codes and multiline responses. The default missing-command path
also blocked. Every query argument list matched the four read-only operations.
These are actual product function executions with injected file/module/command
inputs: **no hardware, boot file, GPIO, service or actual systemctl was touched**.
[Command](command.json), script and raw output are retained.

The [source/proof audit](validation.json) verifies both final product/test bytes
against executed source `69a090254738cbf6368b37c2ebb820a99bf83ea4`, all 21
manifest members, pre-code expectations, original RED/focused/full-CI receipts,
and all 93 original test-definition AST nodes. Existing vault tests, Makefile,
R00 map and task graph are byte-identical to main994. Author full Pi CI actually
ran 173 tests and all unchanged recipe gates on that same source; it is reused,
not described as a second independent full-suite execution. Original RED ran
the old product bytes and failed three tests; its synthetic-input nature is
preserved, with no claim that a host OS permission error was reproduced.

The source-recorded optional HTML archival403, metadata-checker mistakes,
retained native cache and raw-diff whitespace remain explicit historical
observations. No source archival retry, body-hash invention, raw normalization
or threshold change was needed. The author's tracked candidate is complete;
its retained old Rust cache is untracked and is not part of this delivery.

The probe does not attest actual loaded configuration, camera/SPI/display
operation, all remote-access paths, sockets, other SSH implementations, radio
absence or production security. Exact kit/image/operator resources and all
QP01/Q02/QH01 criteria remain open. The candidate is ready for selected-file
assembly; final delivery review, protected PR checks and actual resulting-main
verification remain mandatory before integration acceptance.
