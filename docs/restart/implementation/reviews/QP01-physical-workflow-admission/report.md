# QP01 local-UI fixture experiment: source-only admission

**CHANGES_REQUIRED** for candidate
`a83673409f6b81cb163e1d73d9faa9b0f3afdb7e`, tree
`7bf25c2ac42ba494993eb5053f7d329a5d80739c`.
The source analysis and selected next direction are useful and source-consistent.
The single proposed host render/action experiment is not yet sufficiently frozen
for admission. Close only **R1 and R2** below in a documentary addendum, then obtain
affected admission before implementation/execution. No larger architecture or
physical-workflow investigation is needed to close these findings.

Reviewer `/root/a02_final_review` is distinct from author
`/root/sdk_dependency_probe`; review uses a separate worktree and branch under
Sol6.1/xhigh, without an Astra exception. Shared GitHub identity is not an external
audit. Both author files were read in full. [Source correspondence](source-correspondence.json)
independently matches all 28 declared modes/blobs/byte counts/SHA-256 values at
base `24621023f0c5d181ba41f1a2679a7608e2cdd20a` and the candidate.
The candidate adds only the brief and source proof. No application/test module
was imported; no product, build, test, actor, flash, audit or CI command ran.
Only source/record reads, Git object reads, identity calculations and this report
were performed. PR51 observation remains root-owned.

## R1 — Freeze the exact synthetic callback entrypoint and owner

The brief recommends `EngineAdapter.local_io(Presentation)` and requires C5000,
but does not identify the concrete host fixture entrypoint that installs the new
callback while preserving that watchdog and the existing sole C owner. This is
an execution-contract gap, not a demonstrated product defect.

At the pinned source, `request-engine/exchange.py:279–313` chooses automatic
Next/Approve inside the C entry. `native-leaf.ts:18–113` owns its one subprocess,
readiness, real 5000ms timer, send-once operation and actual stdio/process close.
It has no callback-factory parameter. The existing Python test helper invokes the
real `EngineAdapter` in process and supplies a constant clock by default; that
helper is source evidence, not an unchanged C5000 execution plan for the proposed
experiment. A direct improvised invocation must not be treated as satisfying the
brief's retained owner/watchdog contract.

The addendum must name **one** opt-in synthetic-only entrypoint/command, its
writable paths and trusted configuration, the point where the local-IO fixture
callback is selected, the exact source/library identity bindings and the unchanged
C owner that enforces C5000 from spawn through collection. State what evidence
binds actual callback use, real clock, complete native return/close, and refused
late output. Preserve the existing runtime/handles and unknown-state retention;
no parallel owner, callback timeout thread, direct-CDLL bypass, default provider,
physical callback mode or full optical runner is admitted. Freeze commands and
inputs before execution; a build or actor run is not needed to write this addendum.

## R2 — Freeze fresh-event semantics and the finite local-UI test oracle

“Fresh event after complete draw” is the correct requirement, but the brief does
not yet define an observable local input contract or precise test expectations
that distinguish it from merely returning a queued/held button value. It also
leaves Back/None to unspecified events and provides only a broad sign/reject/fault
summary for the new adapter.

This matters at the actual boundary. `authorization.rs:453–487` checks time around
`present` and trusts its returned event: a successful Next advances coverage.
It cannot establish that an injected renderer drew every byte or that a button
transition happened after that draw. The GPIO adapter sees an already asserted
level, optionally waits for release and returns it; that alone does not prove a
new post-presentation action. Its ordered choice also resolves multiple pressed
buttons. The inherited Pillow draw target deliberately clips at `max_width`, and
its existing clipping test expects truncation. Neither mechanism proves the new
requirement without an explicit adapter contract.

The addendum must freeze the trusted presentation/action association, when a
complete draw is committed, how preexisting/held/queued and simultaneous events
are refused or discarded, and how an event becomes single-use for this exact
presentation and request. Specify Next/Approve/Reject and either define finite
Back/None behavior or explicitly refuse them for this first fixture. A redisplay,
Back navigation or subsequent request must require its own fresh event; scroll
must not silently become Back. No new public protocol or detached approval token
is requested.

Also freeze a finite layout/draw contract: complete `kind/index/total` and exact
Rust `label/body/position` bytes, label/value/position order and original wrapping,
with trusted dimensions/font or glyph metrics, whole-frame fit before acknowledgement,
and failure rather than clipping/ellipsis/normalization. It is acceptable to
refuse an unrenderable frame. Synthetic draw-call evidence must be labeled as
such and cannot establish real glyph readability or a physical panel.

The minimal **future** test expectations are below. These are required admission
inputs, not tests run by this review and not permission to implement them now.

| Case | Frozen expectation needed |
| --- | --- |
| Complete basic catalog | Exact retained raw259/SHA88a1 input, published 4f35 identity and zeroaux; all 30 data presentations plus distinct decision, complete indexed bytes and successful draw before each accepted fresh action. Native response is exact611/SHA2501 and the already independent complete event, never a newly generated golden. |
| Fit and draw faults | Boundary fit; overflow/unsupported layout refuses before acknowledgement. Draw failure before output, after a partial draw, at final decision, presenter exception and input exception/BaseException all yield no usable response. No clipping path or fake “draw completed” can stand in for these checks. |
| Action freshness | Preheld/queued action, stale action from an earlier page or request, duplicate event and ambiguous simultaneous approval never authorize. Freeze each expected refusal/discard result; fresh events after successful redisplay must remain usable. |
| Native actions | Early Approve cannot authorize; Next at decision cannot bypass it. Reject at data and decision refuses. Back/None retain the same deadline and cannot skip coverage, or are explicitly refused by the scoped adapter. Boolean/unknown actions fail display. |
| Currentness and one use | Cancel/expiry across a callback returns no response; no old action queue survives a new request. Every successful new native invocation requires a fresh full review, even when correlation is reused. Preserve existing Rust context/consume-first tests; do not invent a new context setter or imply that the FFI exports a reusable approval handle. |
| Failure/output/ownership | Freeze real callback/error statuses and actual C settlement evidence under unchanged C5000. Before-consent failures must not call the auxiliary/provider; later failures may have consumed authority but release no staged result. No unknown operation is retried or silently replaced. |

Source-grounded status expectations already exist: native early/invalid state -9,
Reject -5, display callback failure/invalid action -6, unavailable/expired clock -7,
auxiliary failure -8 and cancellation -11. `EngineAdapter` refuses bool actions,
catches callback BaseException and checks failure output is empty. Existing tests
are evidence of those old boundaries, not completed coverage of a new local-UI
adapter. In particular:

- `EngineAdapterTests.test_P02_P03_real_basic_and_tagged_requests` checks presented
  field roles, actual key/event ID and independent event values;
  `test_P04_changed_correlation_is_fresh` and
  `test_A01_A02_no_premature_or_rejected_authority` cover their named ABI cases.
- `test_T01_T02_callback_failures_are_closed`,
  `test_L01_reentrant_first_clock_and_presentation`,
  `test_L02_native_reservation_survives_blocked_callback` and
  `test_N01_no_reference_signer_or_loader_fallback` preserve callback, ownership
  and no-fallback properties. Their controlled clocks/waits are existing test
  mechanisms, not a human timing profile for the new experiment.
- Rust `s03_review_has_complete_indexed_coverage`,
  `s03_failed_or_skipped_display_cannot_approve`,
  `s03_attempt_binds_context_and_consumes_mismatch`,
  `s03_first_attempt_is_irrevocable` and `s03_old_session_aliases_and_time_fail_closed`
  establish core catalogue/currentness/consume-first obligations. Reuse their
  source-qualified proof; do not relabel it as testing the new renderer/input.

## Accepted facts and unchanged limits

The source checkpoint correctly distinguishes legacy Python signing and detached
bool approval from the Rust owner. Camera capture is JPEG480/Pyzbar, not raw
240×240 RGB888/172800B for the bounded W. The ST7789 presenter is injected, with no
actual SPI initialization. Actual camera geometry/driver and GPIO/display teardown
remain gaps. The kit description is a user declaration; exact revision/image/
operator remain with the already assigned identification session. No duplicate
resource question or manufacturer research was performed.

The source-matched Rust owner copies the original input before callbacks, derives
the public fixture identity, binds the complete inspection/context and consumes
approval before providers and publication. None of this permits a Python signer,
`approved=True`, cached blanket consent or re-encoded replacement request.

O8/shared4, W512, JSON704/static947, parent reply512, Node2048/4096/4096/max5,
client100 and C5000 remain distinct and unchanged. The synchronous native ABI
cannot suspend/resume review; callback blocking is not interruptible in process.
Thirty-one human-read pages within C5000 and a human optical transaction within
client100 remain **OPEN**. The proposed host-only synthetic adapter cannot solve
or qualify them. Do not raise/ignore the watchdog, freeze a runtime clock, change
budgets, insert a direct native bypass or enable a default route to obtain a pass.

The next concrete step is only an **R1/R2 documentary addendum** with exact
entrypoint/ownership and local draw/action/test expectations, reusing these same
28 bindings and the named prior proofs. Then affected distinct admission can
consider that frozen scope; only a later explicit bounded assignment may authorize
code and execution. No physical callback, full runner, kit test or timing-policy
replacement follows from this review. All 47 formal criteria/dependency/resource
sets, frozen evidence, contracts and five release paths remain unchanged and open
as applicable; no QP01/Q02/QH01 criterion or physical release closes.
