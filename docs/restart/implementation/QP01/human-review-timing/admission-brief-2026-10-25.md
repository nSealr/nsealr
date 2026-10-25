# Admission brief for supervised human review

Proposed next package under QP01, authored by `/root/human_wait_design` on
25 October 2026. Status: **source-only brief pending distinct root review; no
implementation or runtime admission**. Input identities and source links are in
[source-bindings-2026-10-25.json](source-bindings-2026-10-25.json). The selected
[decision](decision-2026-10-25.md) uses the existing synchronous core API.

## Objective and first scope

Demonstrate one original bounded request, one retained Rust owner, complete local
review with one real 5500ms passive interval, one consuming signing-API call and
one privately retained response checked afterward by an independent oracle.
This minimum timing canary makes no live-client publication claim. It addresses
HRT-DESIGN-01/02 from the distinct review of preserved candidate `27ddd70d`.
The first executed scope, after separate source admission, is a Linux x86_64 host fixture with already-public scalar 11x32 only. It is not a
hardware or production-key experiment.

Use a new opt-in Rust fixture executable and a small per-operation local supervisor,
not a persistent service or replacement coordinator. The executable owns the
request, selected key and `AuthorizationSession`. The supervisor owns its exact
process handle, control and result channels, currentness state and private-result eligibility.
Use direct original 259-byte fixture input for this timing-only canary, excluding
decode/camera coverage. A later decoder integration must retain unchanged B3
settlement before intake. Do not parse/reconstruct the request in Python or use
its reference signer.

The code writer proposes literal new paths in the existing fixture crate and one
scoped host harness. Preserve core, old native export/adapter, old Node helper,
C5000 and original gates. Do not copy the compile-only example into normal targets:
its source contains retained dead-code warnings and never ran the operation.
A source change to any preserved perimeter requires an affected amendment/review.

## Fixed ownership and local protocol properties

The first canary has exactly two actors: supervisor S and its directly owned Rust
process R, with one thread each and no descendants. S retains R's exact process
handle and channels until actual settlement. S owns the synthetic cell sink and
fresh-cycle fixture; it invokes no external driver, provider or cryptographic
verifier on its monitoring loop. This is a per-operation host experiment. An
actual blocking IO driver would need a separately watched actor and amendment;
that topology is not silently included here.

Freeze the literal versioned record grammar before coding/running. Proposed caps
are 1024 bytes per control record, two queued records per direction, at most 256 bytes
consumed per monitoring turn, 4096 records and 1024 fresh cycles per operation, and
the unchanged 1024 review-call ceiling. An incomplete record retains no more than
its 1024 byte cap. Unexpected data, excess/duplicate records or sequence overflow
invalidates; no retry increases a cap. Use inherited local channels bound to the
operation incarnation and exact endpoints, not a reusable request-ID lookup.
Every relevant record binds expected phase, invocation, epoch and sequence.
Presentation data includes the exact kind/index/total/label/body/position.
The typed local cycle binds neutral/press/release, one action and a unique serial.
Neither QR/host data nor a digest/epoch grants signing authority.

S is the sole phase and budget authority:

1. R's `present` sends the complete bounded frame and remains in that synchronous
   callback. All time is ACTIVE while S preflights the frame, verifies neutral/no
   queued input, draws every required cell and records its own sink commit. A child
   COMMIT/WAIT label cannot establish draw completion or change accounting.
2. Only for the designated one delayed presentation, S checks the exact complete
   sink receipt and matching incarnation/invocation/epoch/sequence, samples S/R OS
   CPU baselines and real deadlines, transitions its own state to HumanWait and
   sends `WAIT_ACK`. R cannot request another exemption; repeat/early WAIT fails.
3. During HumanWait, source restricts R to bounded control/input framing, clock/cancel
   polling and blocking poll. No request/catalog, draw, core, auxiliary, signing or
   response work is permitted. S continues independent CPU and real-time monitoring.
4. A fresh complete local cycle terminates the exemption at S. S first charges all
   wait CPU, checks time/currentness/monitor gaps, transitions ACTIVE and arms its
   remaining active watchdog. Only then does it send `RESUME_ACK` carrying the
   exact scoped cycle. R cannot return input, call core/provider or encode before
   accepting that ACK. Child phase labels/heartbeats never arm or disarm the timer.
5. Other presentations stay ACTIVE throughout draw and the fixture's immediate
   post-commit fresh cycle. There is no per-page budget reset or extra passive
   exemption. On cancel/expiry/error S revokes eligibility before any ACK; R returns
   closed failure and invalidates the same owner when its borrow is released.

No borrowed pointer crosses the local protocol. The borrowed frame remains valid
on the child's Rust stack until this callback returns. No callback continues after
its owner is freed. A returned `None` acknowledges nothing and must discard any
partial cycle; it cannot be followed by returning a cached action in another
invocation. The normal experiment waits for one complete cycle rather than using
None as a resume feature. Preserve the existing ceiling of 1024 review calls;
choose record/event caps no greater than required and freeze them before launch.

The driver rechecks cancel, time and local context immediately after the callback
and before the next step/signing. During the borrow it cannot mutate core policy
or key concurrently; a detected change invalidates result eligibility
immediately and cancels the same owner as soon as the callback returns. It never swaps in a new
owner to salvage a pending gesture. Retain raw bytes/hash, actual public key,
request correlation and independent expected catalog throughout the operation.

## Watchdog and expiry contract

One real monotonic origin supplies all engine ticks. `tick=floor(elapsed_ns/1e9)`
retains the existing fixture conversion; do not scale ticks, reset origin, subtract
human time or pause a clock. Supervisor expiry is no later than the absolute
boundary for `intake_tick+100`, and no later than a real active caller's deadline.
Metadata and local waiting cannot extend either. The fixture's 100 ticks are
not a measured usability policy for any device.

S's ledger is `ACTIVE wall_ns + conservative WAIT CPU_ns(S,R) <=5000ms` for the
whole operation, including startup, parsing/catalog, all draw, application of
input, core/auxiliary/signing, encoding, staging and S's bounded protocol/result
shape handling through exact settlement/private retention. ACTIVE wall intervals
include time in which R is blocked or descheduled; simultaneously running S/R
share that wall interval. Only S's acknowledged single HumanWait is exempt from
active wall accounting. Remaining budget is never reset per frame/resume.

Independent work observation uses `/proc/<pid>/stat` process `utime+stime` for S
and R, identity-bound to the same retained live processes. Before launch the
literal source admission must establish `SC_CLK_TCK=100`, exact stat parsing,
one-thread/no-descendant source/topology and fail-closed behavior if unavailable.
For the one wait, each process's conservative bound is its counter delta times
10ms plus 20ms for the two counter-quantization uncertainties. The bounds are
cumulative from the one WAIT baseline, not renewed on each sample. R's cap is 100ms,
S's 400ms; both are charged to the same 5000ms ledger. Missing/decreasing/overflowed
counters or identity mismatch revoke. S checks them before every ACK, on at most 25ms
polls and before private retention. A busy-looping false-WAIT fault exceeding the
R cap must fail despite valid child labels. A counter cannot prove which private
function ran, sub-quantum absence of work, completion of a blocked draw or hostile
unobserved descendants. Exact admitted source and S's independent sink observation
supply those separate trusted-image/host-fixture boundaries.

S uses a 25ms maximum poll timeout and monotonic checkpoints at most 50ms apart.
Each handling turn consumes at most 256 bytes and one completed record before
checking clock/cancel/CPU/remaining budget again. No synchronous crypto verifier,
external callback, unbounded logging or blocking pipe write runs on this loop;
all channels use bounded nonblocking IO. A completed record may not bypass the
checkpoint. If a read/handler/kernel call/scheduling pause causes a gap over 50ms,
S revokes before processing input, sending resume or accepting a result. This is
a fail-closed run threshold, not a guaranteed Linux scheduling/reaction bound. A pause after a guard can still
allow already-started effects; this canary claims no recall or zero internal
backend effects in that race and provides no public release boundary.
While S is stopped, it cannot prove enforcement by that instant; after resumption
the gap and elapsed wall accounting cannot be erased and no candidate becomes
eligible. Source must place the gap/expiry checks before every ACK and private
retention. A SIGSTOP-after-check fault must remain a failed canary, not proof of
an atomic check/write deadline or a hard collection time.

The absolute core/caller expiry stays armed in every phase, including HumanWait,
settlement and private retention. Cancel/expiry invalidates before cleanup;
cleanup attempts share one 4s interval from first invalidation, with unknown
ownership retained afterward. No callback, poll, redraw or resume moves it.
The old native C5000 remains byte-identical. The new provider's ledger is a new
admitted contract, never a claim to have passed the old continuous5s timer.

The single real 5500ms wait must stay below the actual core/caller deadline, with
zero observed driver `sign_approved` entries and zero auxiliary calls during it.
Record real endpoints and all OS CPU samples. Shorter logical boundary tests
remain labelled simulations. These proposed thresholds are frozen before source
admission; RED stops without relaxing them. If monitoring/accounting cannot meet
this small canary contract, report that exact failure. Do not add a process
framework, change clocks or increase allowances as an unreviewed correction.

If the existing caller uses client100ms, it must fail at that existing deadline;
do not change it for the standalone delayed fixture. A connected acceptance uses
the actual intersected method/transport limits, 30000ms caps and live
account/connection/generation observations. No pending status or reconnect extends
a request or attaches a late signature to a new one.

## Signing, publication and settlement

Use `sign_approved` exactly once after complete separate final consent. Count
**driver sign-entry** immediately before that public call and count the injected
`AuxiliarySource` invocations. The API exposes clock, auxiliary and output only;
it exposes no backend hook/counter. Core spends consent before these callbacks,
checks the same correlation/context, verifies its actual signature and releases
into R-private staging. All this work stays ACTIVE.

For this minimum canary, S accepts at most one bounded response into a private
buffer only after successful R wait status, complete bounded records and required
IO EOF/close, plus its fresh gap/clock/currentness/budget guards. Parent shape/hash
handling remains on the ACTIVE ledger through this retention. There is **no
public/client publication**. The unchanged independent oracle checks the retained
artifact afterward under its original separate harness/evidence role; it cannot
resurrect expired eligibility or prove that S verified a live dispatch responsively.
Post-core wrong-key/wrong-byte/signature mutation is solely an independent-oracle
negative. It is never a core/backend fault injection.

For a later live release package, parent cryptographic verification, currentness
and publication must remain within the same aggregate remaining budget and real
expiry. Either a separately watched verifier actor or an explicitly bounded
incremental verifier must keep S's monitoring loop responsive. The final guarded
release has no intervening callback/await, and must define behavior under
preemption; an ordinary clock-check-plus-write is not an atomic real-time expiry
guarantee. No such release mechanism is qualified by the first canary. Stop at
private artifacts until the additional source/ownership/timing contract is
independently admitted; a new verifier actor is not required in this first scope.

Cancel/expiry revokes eligibility before cleanup and discards late bytes. A kill
request, terminal report or EOF alone is not full settlement. Retain the original
handles/reservation under unknown wait/IO/report outcome, quarantine and prohibit
automatic replacement, reload, replay or another reservation.

Control EOF/parent loss must invalidate the child's pending review and result.
A stopped child may be killed by the surviving supervisor; the recorded wait/IO
facts decide collection. Supervisor death cannot be advertised as proven cleanup
by old C-death tests: its own loss/EOF and stopped-child combinations need explicit
qualification. The first experiment makes no stronger O-death recovery guarantee
than its actual topology/evidence; no result remains publishable if its only
publisher is gone. Unknown custody erasure after forced kill remains a device gate.

## Discriminating acceptance

Freeze literal source, argv, environment, input, independent expected catalog,
signature oracle, fault selectors and all thresholds before runtime. Record exact
source/binary hashes, monotonic checkpoints/ledger charges, OS CPU samples,
actor/channel identity, driver sign-entry and auxiliary-call counts, private-result
eligibility and settlement. A distinct reviewer checks the frozen source and raw
proof. Lost/incomplete observations cannot establish absence of a sign entry.

| Evidence role | Cases and required observation |
| --- | --- |
| New two-actor canary | Real 5500ms wait; same owner/raw/key/catalog/context, zero driver sign-entry/aux calls during wait; later one sign-entry and one successful auxiliary invocation, exact settlement/private response, then independent oracle verification. No backend-attempt count or live-publication claim. |
| New supervisor authority | Child WAIT/COMMIT before S's full sink commit, repeated/wrong-phase WAIT_ACK, fake heartbeat, blocked draw continuation: ledger stays ACTIVE or revokes. A false-WAIT busy loop crossing 100ms R CPU cap fails independently of child labels. Attempts to dispatch core/provider/encoder before RESUME_ACK must fail at the driver phase guard without entering those operations; resume-before-watchdog-arm fails at S. The separate busy-loop fault tests actual hidden CPU work; no sub-quantum absence claim follows from CPU alone. |
| New responsiveness/accounting | Actual S/R pause/stop during ACTIVE/HumanWait/resume/result retention; monitoring gap over 50ms, exhausted shared ledger, CPU counter failure, partial/overflow records and handler flood: zero eligible private result/resume; retain handles if unsettled. Distinguish observed scheduling gap from a claimed hard reaction guarantee. |
| New boundary/cancel/input | Before draw, partial draw, post-commit wait, before/after final gesture, before sign entry, inside injected auxiliary wait, post-core staging and private retention; real core/caller expiry or clock failure: zero eligibility. Pre-entry cancel means observed sign-entry 0/aux 0; after entry no claim to recall backend effects. Preheld/queued/duplicate/partial/simultaneous/stale/cross-channel cycles, post-None action, Approve-on-data and Next-on-decision fail without consent reuse. |
| New public-API negatives | Wrong correlation, fallible/short/oversized/stuck injected auxiliary source, too-small public API output and completion-clock failure: report sign-entry/aux counts and API result honestly, no eligible/partial public response, no second driver sign/aux attempt. The auxiliary fault point is injectable; a private backend fault point is not. |
| New context/settlement | Changed raw/key/account/policy/geometry/limits/session or caller generation, child fault/stop/kill, early/partial result, missing EOF, wrong wait status, report/close failure or control/supervisor loss: revoke; no inherited consent, replacement or new reservation under unknown ownership. Mutate through existing public methods only at legal serialized boundaries; cancellation during a borrow revokes eligibility immediately and mutates core only after the callback returns. |
| Reused unchanged core evidence | Original K01 consume-before-clock/provider, exact binding/expiry, auxiliary-prefix wipe and second-attempt negatives retain original 4bab/bf51 run identities. The four source-bound core files equal current f1b byte-for-byte. Private test backend counts remain evidence from those original core tests, never new executable observations. See bindings and existing K01 evidence/result.json, proof-final-core/commands.json and auxiliary-prefix-observed.json. |
| Parent after-core verification | Mutate the retained response's key, request ID, template, event ID, signature, shape or trailing bytes; the existing independent oracle rejects. This proves that verifier's response checks only, not injected core/backend corruption or a backend attempt count. |

No new backend-internal failure/wrong-signature experiment is required or claimed.
`observe_backend_attempt` is cfg(test) inside private core tests. If a future
indispensable experiment needs it, stop for a separately scoped core amendment;
no hidden seam, invented counter or automatic core rerun belongs to this scope.

No new runtime runs with this brief. After root accepts the design, the next
reviewable artifact is the literal source and executable contract for this finite
scope; distinct source admission precedes build/runtime. A monitoring/accounting
failure stops at its exact missing property; it does not establish a need for B.
Propose B only for a concrete live-callback/borrow integration restriction. Do not
widen budgets or import an APIv2 under the guise of a correction.
