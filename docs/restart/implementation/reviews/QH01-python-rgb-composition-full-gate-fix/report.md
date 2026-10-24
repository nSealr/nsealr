# Distinct full-log oracle correction review

**PASS_SCOPED_FULL_LOG_BUILD_ORACLE_CORRECTION_ONLY**, findings[]. This resolves
QH01-COMPOSITION-INTEGRATION-01/P2 for candidate
`f8adb7dd0b8cfb22f0b7d7c7cf5c7ad65104d683`, tree
`5ca1890add82b4d14aec298eb3b07c9e16a8722b`. The original10ab review and RED remain
unchanged. All its unaffected integration/source conclusions are reused.

Only the checker and pure control script change executable behavior from5b.
`verify_product` unconditionally requests full mode; early single-build mode is
isolated to the explicit pure block test. Full mode requires exactly15 individual
build occurrences and one command/case. It selects the actual pre-command build,
then validates the17 ordered markers against PRODUCT_STEPS in the named Git
source. Exactly one build must lie in each interval3–15 and17, with none in1,2,16
or after completion. One pre-command occurrence plus14 required intervals and an
exact total15 also excludes builds between command/case or case/first marker.
An identical second record cannot compensate for a missing record elsewhere.

All15 complete build payloads must match the validated first payload and the
composition's consumed outputs. Sorted JSON equality preserves the distinction
between booleans and numbers (including False versus0), before the original
integer/status/source/argv/output assertions. There is no deduplication, arbitrary
at-least-one allowance, suppressed build or test/gate bypass. Build records have
no individual execution identifier; these checks depend on trusted complete-log
provenance and the serial source-defined command order, not runtime attestation.

The source-only oracle is byte-exact to2db4. All26 referenced postimages match5b,
the author source and this candidate. AST inspection confirms the14 single direct
main() build calls at the recorded lines, positions and ROOT argument. The three
other steps do not call that builder. The unchanged helper inherits stdout and
executes pinned pnpm build; the unchanged builder emits once per such invocation.
The checker intentionally qualifies this current command plan, not arbitrary
future reordering or parallel make invocations.

One independent pure `test_capture_extension.py --full` replay passed with
baseline Python3.12.15: exit0, 0.445918 seconds bookkeeping time. The unchanged
751120-byte original log has SHA256
`21965321b2537b213549f04e4fdcf266a8932877963ab297d903a68fea96c244`.
The positive validates15 builds/14 later intervals and the existing composition
bindings. All32 mutations were rejected, including same-total missing-step3 plus
duplicate-step4, a post-completion build, late initial build, changed later status
and boolean status substitution. The first27 controls remain equal to their
original results. The root's source-qualified early27 proof is retained; no new
reviewer early replay or second full-block replay occurred.

The original complete make-k-ci remains a5b run, exit0/344.658s, not an f8 run.
Its original checker RED1 is retained at the singleton assertion. Root's separate
complete-addon GREEN uses checkereaf on that same read-only log. This reviewer
ran only the added block's full pure controls, plus static metadata inspection;
no product O/W/Node/C, compilation, installation, full Pi, whole product gate or
hosted query ran. Python and immutable Git reads are not product processes.

The correction manifest's15 members plus itself and the archive's97 raw members
plus manifest all verify. Eight selected outer files are byte-exact archive
copies. All60 runtime/build inputs match5b; removing only the new imports,
function and call restores f129's whole legacy AST. The original10ab14-file
packet is byte/mode-exact. All47 formal/status sets and other45 task records
remain unchanged; current evidence still marks protected adoption pending.
Historical a118 capture manifests retain their original source qualification.

This closes only the P2 full-log oracle defect. Protected PR/actual-main checks
remain root-owned. Composition timeout/cancel seams, camera/display/optical
transfer, ARM/Pi, secret custody, production/default provider, framing freeze,
general reproducibility, component/task completion and physical releases remain
unqualified. Original synthetic client100 and real O8/shared4 are unchanged.

`command.json` and raw replay streams bind the sole independent replay;
`controls.json` retains every result. `inspect.py`, its command/streams and
`checks.json` retain the bounded source/proof inspection. The ignored extracted
log is recoverable from the unchanged original archive. No product handle was
created and no process remains active from this review.
