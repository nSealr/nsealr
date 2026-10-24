# Distinct normal-composition integration review

**CHANGES_REQUESTED**: one full-log capture-checker finding for
`5b32621d24bf06fe523f28f83ac51ebce6d870fc`, tree
`f2e9aceefd9fced53fdc803d26dd0cf2c7cf5034`. This reviews the three SDK integration
files and two root capture-checker/control files independently of their authors.
It does not accept a complete component, protected delivery or physical release.

**QH01-COMPOSITION-INTEGRATION-01 / P2 — global build-record uniqueness rejects
valid full integration output.** `verify-cold-capture.py:95–99` requires exactly
one `bridge_service_build` across the complete product log. `Makefile:87–105`
runs bridge/Pi and later `tests.integration.run`; that runner's required seventh
step is `integration_companion_service_context` (`run.py:16,30–33`). Its main
calls `build_pnpm_workspace(COMPANION)` at line146, with COMPANION equal to ROOT
at lines17–18. `integration_support.py:79–80` executes `pnpm build`, using normal
inherited stdout (`47–63`). The newly changed builder always emits another valid
record at `build_packages.mjs:81–88,99`. This is one sufficient source witness;
deriving the full count/order is deliberately left to the assigned source owner.
The complete run therefore can contain a legitimate additional build record,
which the global `len(rows) == 1` rejects before case verification. This is a
checker/oracle integration defect, not a composition/product runtime failure.

Root reported this during its still-running full make-ci before this verdict
was frozen. This review independently confirms the source witness, and does not
claim a completed full-log RED execution; root owns that forthcoming receipt.
The required correction must bind the build used by this composition and handle
the source-required later build sequence without accepting arbitrary duplicates,
silencing builds, skipping tests or weakening the existing gates. Review the
bounded checker/oracle delta and its pure controls before adoption. All following
source, metadata and early-log results remain valid within their stated scope.

The builder retains the package order, compiler options and production Bridge
sources/launcher. Its new final compilation emits the five existing service TS
files as ten JS/declaration files, using the existing ESM context. Compiler status,
signal/error, actual argv, source hashes and output hashes are recorded. A failed
compiler or missing/changed inputs cannot produce a successful target.

`exchange.py:85–158` preserves provisioning and the complete old CI prefix. The
new suffix runs the six pure reporting controls and one composition only after
the full Pi target and both existing client commands. It passes the provisioner's
actual worker path/SHA and this checkout's compiled Bridge/packages. The existing
two ProvisioningControls retain the four-entry prefix, shared environment and
failure stop; the remainder of the test module and all test method names are
unchanged. The new synthetic ordering record is suppressed, not published as
actual runtime evidence.

The existing corrected harness owns runtime collection; this wrapper waits for
that invoker and reads its actual receipts. The fresh output directory is removed
only after successful collection, source/output comparison and case emission.
Failure preserves it and propagates failure. The wrapper adds no timeout or kill
of an uncertain owner. Failures before launch create no product child; failure
to remove already-settled output still fails the command. Unknown-owner retention
and B3/O/W behavior reuse review `1e0453fe7af476275b749fbff116899093cbeced` and its
byte-identical corrected b6 sources; no new recovery or owner-death claim follows.

The new checker is an additive source/capture check. Its unique command/case
requirements and the single-build early-log checks cover exact current Git source,
five compiler sources and ten
outputs; 60 dynamic sources and 62 generated files; the actual provisioned/live
worker identity; original259/259/611 frames; the verified response and independent
fixture key; exact synthetic timer observations; and actual wait/collector,
session/limits, EOF and FD evidence. It rejects an explicit composition failure.
Removing only the added import, function and call restores the complete f129 AST.
The original generic completed-capture/status checks remain mandatory, including
for failures occurring after a case record has been emitted. This is evidence
validation from trusted source-bound logs, not independent runtime attestation.

One independent **pure** execution of the unchanged `test_capture_extension.py`
passed with baseline Python3.12.15, exit0, 0.326526 seconds bookkeeping time.
It used source8a80 and this candidate's checker, the original496870-byte early log
SHA256 `63382b6d98cbe5bcb63bd23e207363f439187600bd9f13a161019330f9dc02ee`,
and a fresh result. The real recorded positive passed and all27 targeted mutations
were rejected, including missing/duplicate records, stale source/generated code,
worker/collector mismatch, absent collection, false taken state, timer/key/G-type
changes and missing pure controls. Python/Git inspection processes ran; no
product O/W/Node, compilation, installation, signing, Pi suite or CI ran here.
In particular, rejecting a duplicated build in this one-build early log does not
prove the correct full-scope build oracle; finding01 prevents that inference.

Git/AST/archive inspection also passed. The normal-ci manifest has **12 members
plus itself (13 total)**; capture extension has9+1. All91 regular archive members
are accounted for by90 hashes plus its manifest. The outer build/case records
equal the records in the original log. Original author source8a80, clean-status
receipt, default Cargo targets and one normal make-pi-ci remain historical;
neither that run nor the prior715/b6 runs are relabelled as executions of5b.
The old review's12 files and DA8 adoption's8 files are source/mode-exact imports.
All47 formal sets/statuses and the other45 task records are identical; only QH01
and QP01 evidence/checkpoint fields differ, with the active new checker explicitly
pending review, complete gates and integration. Lifecycle expectations5138 are
copied unchanged and remain informative, unexecuted and not admitted by this review.

Required complete stable-candidate, protected PR and actual-main gates remain
root-owned and separate. This verdict does not consume a later live gate result.
The client clock remains synthetic0/99/100; O8/shared4 is real and C5000 unchanged.
Timeout/cancel composition cases, camera/display/physical transfer, ARM/Pi,
production provider/keys/default route, framing freeze, reproducibility, task
completion and releases remain unqualified. Original failures and raw whitespace
are preserved. A reviewer README lookup initially omitted `proof/`; the correct
path was then read, with no source/test change or failed product run. A later
bounded search also named absent optional `tools/integration` and
`tools/baseline/commands.json` paths; the actual Makefile/tests source was read
directly. These lookup diagnostics are not product or checker-test failures.

Reproduction inputs and command are in `command.json`; raw stdout/stderr and
`controls.json` retain the sole replay. `inspect.py`, its receipt and `checks.json`
retain the bounded metadata inspection; `proof-bindings.json` records same-run
comparisons. The original log is recoverable from the unchanged author archive;
its extracted local copy is ignored. No live product handles remain from this review.
