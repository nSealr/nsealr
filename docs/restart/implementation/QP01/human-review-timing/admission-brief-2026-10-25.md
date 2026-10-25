# Admission brief for supervised human review

Proposed next package under QP01, authored by `/root/human_wait_design` on
25 October 2026. Status: **source-only brief pending distinct root review; no
implementation or runtime admission**. Input identities and source links are in
[source-bindings-2026-10-25.json](source-bindings-2026-10-25.json). The selected
[decision](decision-2026-10-25.md) uses the existing synchronous core API.

## Objective and first scope

Demonstrate one original bounded request, one retained Rust owner, complete local
review with a real elapsed passive interval representing human wait, one consuming signature and one independently
verified response, while compute remains bounded and cancel/expiry/currentness
fail closed. The first executed scope, after separate source admission, is a
Linux x86_64 host fixture with already-public scalar 11x32 only. It is not a
hardware or production-key experiment.

Use a new opt-in Rust fixture executable and a small per-operation local supervisor,
not a persistent service or replacement coordinator. The executable owns the
request, selected key and `AuthorizationSession`. The supervisor owns its exact
process handle, control and result channels, currentness state and publication.
Retain the existing settled decoder owner boundary; admit an original raw frame
only after its unchanged B3 settlement checks. Do not parse/reconstruct the
request in Python or use its reference signer. Direct raw259 fixture input may
be used for the first timing-only experiment, explicitly excluding decode coverage.

The code writer proposes literal new paths in the existing fixture crate and one
scoped host harness. Preserve core, old native export/adapter, old Node helper,
C5000 and original gates. Do not copy the compile-only example into normal targets:
its source contains retained dead-code warnings and never ran the operation.
A source change to any preserved perimeter requires an affected amendment/review.

## Fixed ownership and local protocol properties

The existing caller retains one supervisor; that supervisor retains the exact
Rust child and its channels through termination. The supervisor is an independent
execution context and performs no blocking display/input/provider callback on its
watchdog loop. Every potentially blocking callback lives in the watched child or
a separately identified IO actor whose handles the supervisor also retains. Do
not add an IO actor unless the actual driver requires it. The initial host fixture
needs only the Rust child and bounded synthetic draw/input ports.

Before coding, freeze the versioned record grammar, byte/event/queue caps,
channel directions and process topology. Use a local inherited channel with an
operation incarnation and exact actor/endpoint identity, not a reusable request-ID
lookup. A record includes the expected phase and monotonic sequence; presentation
records include kind/index/total plus the exact complete label/body/position bytes.
Local draw records include an epoch and complete commit. Input is a typed local
neutral/press/release cycle with one action and a unique serial, bound to that
incarnation, invocation and epoch. External QR/host messages never create it.
A digest or epoch routes observations; it grants no signing authority.

The local adapter must, in one `present` invocation:

1. Preflight the full exact frame and verify neutral input/no queued action.
2. Draw every required field and position, then commit the entire presentation.
3. Arm one new local epoch only after commit; notify the supervisor that passive
   HumanWait is now legal for this exact invocation.
4. Await/poll one fresh complete local cycle while the supervisor continues real
   deadline/cancel/caller monitoring. Reject preheld, partial, simultaneous,
   duplicate, stale, cross-channel or wrong-epoch cycles.
5. Return only that invocation's scoped `Next`, final `Approve` or `Reject`.
   On expiry/cancel/error, invalidate and return a closed failure instead.

No borrowed pointer crosses the local protocol. The borrowed frame remains valid
on the child's Rust stack until this callback returns. No callback continues after
its owner is freed. A returned `None` acknowledges nothing and must discard any
partial cycle; it cannot be followed by returning a cached action in another
invocation. The normal experiment waits for one complete cycle rather than using
None as a resume feature. Preserve the existing ceiling of 1024 review calls;
choose record/event caps no greater than required and freeze them before launch.

The driver rechecks cancel, time and local context immediately after the callback
and before the next step/signing. During the borrow it cannot mutate core policy
or key concurrently; a detected change invalidates publication immediately and
cancels the same owner as soon as the callback returns. It never swaps in a new
owner to salvage a pending gesture. Retain raw bytes/hash, actual public key,
request correlation and independent expected catalog throughout the operation.

## Watchdog and expiry contract

One real monotonic origin supplies all engine ticks. `tick=floor(elapsed_ns/1e9)`
retains the existing fixture conversion; do not scale ticks, reset origin, subtract
human time or pause a clock. Supervisor expiry is no later than the absolute
boundary for `intake_tick+100`, and no later than a real active caller's deadline.
Metadata and local waiting cannot extend either. The fixture's 100 ticks are
not a measured usability policy for any device.

The proposed active-time ledger totals all COMPUTE/DRAW intervals from actor
startup through private final staging, with ceiling <=5000ms for the operation.
Each interval uses the real clock; remaining budget decreases, never resets.
An independent timer is armed from that remaining budget whenever work begins.
HumanWait starts only after verified complete draw commit, and ends before
applying the action or any parser/crypto/encoding work. Finite polling/control
work in HumanWait also has frozen per-event and cumulative ceilings; event floods
cannot keep an operation alive or hide active work. Busy-looping under a WAIT
label is a failing implementation, not a budget exception.

Do not alter the legacy native timer. A delayed-human run must use a distinct
explicit provider; passing it must not relabel it as a C5000 run. Thresholds for
new IO/control intervals and exact record caps require source admission, not
measurement-driven relaxation after RED. The literal first probe uses one real
5500ms passive delay, with both sides of the observed monotonic interval recorded,
strictly below the absolute core/caller deadline and with zero provider/sign calls
during that wait. Shorter logical boundary tests complement this one elapsed wait;
they are labelled simulations and do not substitute for real delay evidence.

If the existing caller uses client100ms, it must fail at that existing deadline;
do not change it for the standalone delayed fixture. A connected acceptance uses
the actual intersected method/transport limits, 30000ms caps and live
account/connection/generation observations. No pending status or reconnect extends
a request or attaches a late signature to a new one.

## Signing, publication and settlement

Use `sign_approved` exactly once after complete separate final consent. Core spends
approval before clock/provider/backend work, checks the same request ID and
context, verifies the actual signature, then releases into a child-private staging
area. The supervisor separately verifies the wire response against the original
request, expected actual key and full event template. It rechecks caller/local
currentness and time at the sole publication boundary; no callback or await may
separate that final guard from the release action.

Candidate result bytes travel only to a private parent buffer. Public output
requires successful actor exit/wait status, complete bounded result/control
records, all required IO EOF/close and eligible currentness. Cancel or expiry
revokes eligibility before cleanup and discards late bytes. A kill request,
terminal report or EOF alone does not establish full settlement. Retain original
handles/reservation under unknown wait/IO/report outcome, quarantine the operation,
and prohibit automatic actor replacement, reload, replay or another reservation.

Control EOF/parent loss must invalidate the child's pending review and result.
A stopped child may be killed by the surviving supervisor; the recorded wait/IO
facts decide collection. Supervisor death cannot be advertised as proven cleanup
by old C-death tests: its own loss/EOF and stopped-child combinations need explicit
qualification. The first experiment makes no stronger O-death recovery guarantee
than its actual topology/evidence; no result remains publishable if its only
publisher is gone. Unknown custody erasure after forced kill remains a device gate.

## Discriminating acceptance

Freeze literal source, argv, toolchain/environment, raw input, expected catalog and
signature oracle, fault selectors and all thresholds before runtime. Record each
case's source/binary SHA256, elapsed monotonic timestamps, process/channel identities,
provider/backend counters, result eligibility and exact settlement. An independent
reviewer checks the frozen candidate, affected source and original raw proof.

| Case | Required observation |
| --- | --- |
| Real delay positive | One 5500ms passive wait exceeds legacy5s while the legacy timer/source remains unchanged; same owner/raw/key/catalog/context, no provider/sign work during wait; later complete fresh review, one signature and independent verification. No claim that legacy C5000 was passed. |
| Core/caller boundaries | Below/at/after fixed expiry, clock unavailable/rollback/overflow, and shorter client100ms: no release at or after the applicable boundary, no extension on redraw/Next/Back/None or busy intake. Test engine and supervisor boundaries independently. |
| Cancel races | Before draw, during partial draw, after commit, during wait, immediately before/after final gesture, during auxiliary/backend/staging, and immediately before parent publication: zero eligible output. Pre-attempt cancel also means zero backend calls; post-attempt cancel cannot claim recalled effects. |
| Gesture replay | Preheld/queued/duplicate/partial/simultaneous events, wrong invocation/epoch/channel/incarnation, action after None and an old request ID reused in a new operation: no page/consent reuse. Approve on a data page and Next on decision fail. |
| Presentation/context | Missing/reordered/truncated draw, fit/commit failure, changed raw bytes/key/account/policy/geometry/limits/session or caller generation: no inherited approval or late release; fresh operation requires fresh complete review. |
| One-use signing | Wrong correlation, unavailable/short/long/stuck auxiliary input, backend error/wrong identity/wrong signed bytes, insufficient staging capacity and post-consumption expiry: spent consent, zero eligible output or public partial bytes and no second provider/backend attempt. |
| Work/protocol bounds | Compute or draw overrun, false/repeated WAIT transitions, work hidden in WAIT, too many None/Back/records, control flood/overflow, malformed or duplicate terminal records: revoke, attempt kill as needed, do not raise any cap. |
| Actor and IO settlement | Fault/stop/kill child in each phase; early result/partial output, missing EOF, bad wait status, blocked report/close and supervisor/control loss: retain exact handles under unknown ownership, zero release/new reservation. Distinguish actual kill/watchdog events from injected labels. |
| Positive release once | Same public key, request ID, entire template, canonical event ID, independent signature and complete bounded wire frame; at most one publication. Reject, retry and late bytes cannot release it again. |

No new runtime runs with this brief. After root accepts the design, the next
reviewable artifact is the literal source and executable contract for this finite
scope; distinct source admission precedes build/runtime. If A cannot satisfy
supervision without cached input or a callback outside the watched topology,
stop with that concrete failure and propose B's split core contract. Do not widen
budgets or import an APIv2 under the guise of a correction.
