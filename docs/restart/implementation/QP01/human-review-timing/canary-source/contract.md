# Supervised human wait source contract

This is a source-only candidate under design `53275345`. No build, native call,
actor, 5500ms delay or signature has run for this candidate. Distinct exact-source
admission is required before compilation or runtime. The sole task graph remains
`plan/work-items.json`; no criterion is closed.

The opt-in example is
`crates/nsealr-pi-engine-fixture/examples/qp01_human_wait_canary.rs`.
`supervisor.py` uses only the Python standard library during the two-actor run.
The separate `verify` invocation loads the existing hash-bound independent S03
oracle after settlement. It neither signs nor starts an engine actor.

## Two actors and scope

S is one Python supervisor process, with one directly owned single-thread Rust
process R and no descendants. A trusted caller captures CLOCK_MONOTONIC nanoseconds
immediately before exec of S; the recipe uses one exec in the same PID, without a
third live protocol actor. This origin includes S image startup, source/input
preflight and R spawn in the operation's aggregate ACTIVE charge. Launcher
preparation before choosing the operation origin has no request, child or owner.
No retry/replacement/reload occurs after an operation starts.

R accepts exactly the original259-byte static fixture and its pinned SHA256. It
selects only already-public scalar11x32. One non-cloneable AuthorizationSession
owns request/key/context/review/one-use consent. No C ABI, external approval flag,
backend hook, C01 source import, recovery or production key is present. The same
borrowed frame remains inside one synchronous LocalReviewIo::present call while
R waits on S's inherited pipe. EOF/error unwinds that call; Owner cancels and locks
on ordinary return/unwind. Forced death is not proof of universal memory erasure.

The only new unsafe/OS FFI in R is internal clock_gettime(CLOCK_MONOTONIC) with a
repr(C) two-i64 timespec, restricted at compile time to Linux x86_64/64bit.
It uses existing platform libc, adds no crate/dependency/Cargo change and exports
no API. This exact layout, symbol/linkage and initialized pointer are explicit
source-admission points. std::time::Instant is not falsely serialized as S's epoch.

Core/legacy sources, catalogs, C5000, adapter, Makefile/default CI, Cargo files and
plan remain unchanged. The actual main19ab tree equals the bound deliveryf1b tree;
the author branch stays on its preserved532753 lineage. No device/ARM/image,
physical draw/input, entropy/custody, B3 decode or connected client is qualified.

## Literal binary record grammar

Each record is a four-byte unsigned big-endian body length followed by that body.
Body length must be33..1020 before allocation; total record size is at most1024.
The common body header is exactly33bytes:

| Offset | Field |
| --- | --- |
| 0..4 | ASCII HRT1 |
| 4..8 | Direction-local u32 sequence, starting1, increasing exactly1 |
| 8 | Opcode u8 |
| 9..25 | Exact16-byte local operation incarnation |
| 25..29 | Invocation u32 |
| 29..33 | Epoch u32 |
| 33..end | Opcode-specific payload |

Each direction permits at most4096records. S queues at most two records and consumes
at most256bytes/one completed record between monotonic checkpoints. Parser storage
is at most1024+255bytes; streams retain at most65536bytes each, stderr4096bytes.
S reserves64bytes inside the outgoing65536byte cap for cancellation, not above it.
Unexpected directions/opcodes/lengths/sequences/incarnations/scopes fail closed.

| Opcode | Direction and exact payload |
| --- | --- |
| 1 INIT | S->R, invocation=epoch=0; origin_ns:u64, caller_deadline_ns:u64, case_id:u16, raw_length:u16=259, raw259. Payload279bytes. |
| 2 PRESENT | R->S; invocation starts1/increments1, epoch=invocation. kind:u8, index:u16, total:u16, label/body/position lengths:u16 each, then those three byte spans in order. Length limits176/264/9; total<=1024. |
| 3 WAIT_ACK | S->R; current invocation/epoch, empty. Exactly one exemption, after S's own full sink commit. |
| 4 WAIT_READY | R->S; current invocation/epoch, empty. Observation of a live waiting callback; never authority over S's ledger. |
| 5 RESUME_ACK | S->R; current invocation/epoch; action:u8, serial:u32, cycle:u8. Valid full local cycle is7; action0=Next/data,1=Approve/decision,2=Reject. Serial increases exactly1. |
| 6 CANCEL | S->R; current scope, empty; revokes, never approves. |
| 7 RESULT | R->S, scope0; one bounded original static response1..947bytes, parent-private only. |
| 8 TERMINAL | R->S, scope0; status:u16, driver_sign_entries:u32, auxiliary_calls:u32, review_calls:u16. Exactly12bytes, one terminal. |
| 9 SIGN_ENTRY | R->S, scope0; driver public sign_approved entry count:u32, exactly1. |
| 10 AUX_ENTRY | R->S, scope0; injected AuxiliarySource invocation count:u32, exactly1. |
| 11 | Reserved/unaccepted COMMIT claim. A child cannot attest S's sink or suspend accounting. |

R status0 means its normal fixture path returned; 1=protocol,2=clock,3=driver
phase guard,4=cancel,5=closed public-core operation failure. The public LocalReviewIo
error maps closed inner failures to core Display, so terminal5 is intentionally
not labelled an internal backend error. Exceptional process exit/stderr and
missing/partial/duplicate terminal remain independently failing observations.

Case30's first scoped no-event record is action4/serial0/cycle0 and may return
LocalInput::None without a gesture. Its next old-scope ACK must fail; no action or
partial cycle survives into that new invocation. This is only a negative selector.
All positive actions require a fresh complete local synthetic cycle after commit.

## Independent draw and phase authority

S compares every exact PRESENT against inherited-catalog.json before drawing.
That file is a frozen golden from the already-reviewed UI's original basic-fresh
trace, not a new execution or an independent semantic/signature oracle. Its source
archive/member hashes are preserved. The actual main/core source identities equal
that reviewed context. R requires intake tick0; an origin older than1s fails,
rather than resetting the clock or silently producing another catalog. The golden
has31 pages because this exact retained trace does; no APIv2 page count is inferred.

S's synthetic logical32x8 sink validates every ASCII line and full label/body/
position, then records its own complete ordered cell receipt. Child labels never
count as a commit. Partial draw leaves ACTIVE accounting in force and yields no ACK.
No font, pixels, electrical display or physical button claim follows.

Only S changes ACTIVE/WAIT state. For the first presentation, S records CPU
baselines and its own commit, then sends WAIT_ACK. R is source-restricted to
bounded control framing, clock/cancel polling and blocking read while waiting.
A WAIT_READY/heartbeat cannot change accounting. Before RESUME_ACK, S checks
real deadlines/currentness/gaps, ends WAIT, takes a final conservative CPU sample,
arms the same remaining ACTIVE budget, then queues the exact fresh cycle. R's
phase guard prevents returning input/entering core/provider/encoder before ACK.
Other pages stay ACTIVE; no additional exemption or per-page allowance is granted.

## Clocks and work accounting

Both actors use the same real CLOCK_MONOTONIC origin. Normal ticks are
floor((now-origin)/1e9), with no scaling, reset, subtraction or frozen clock.
The fixed core deadline is100ticks; S uses the same absolute origin+100s boundary
and any earlier explicit caller deadline. Case caller-100ms uses actual100ms,
not a synthetic client extension. The clock-unavailable/rollback/expired selectors
are explicitly negative provider simulations; S's real clock continues unchanged.

The aggregate ledger is ACTIVE wall nanoseconds plus conservative CPU charged
for S and R during the single WAIT, at most5000ms. All active startup, input/
request/catalog/draw, core/auxiliary/signing, encoding/staging, parent protocol/
shape handling, known settlement and private retention are covered. Simultaneous
active S/R work shares one real wall interval. No resume replenishes the budget.

OS observation is identity-bound /proc/pid/stat utime+stime, SC_CLK_TCK exactly100.
One-thread/no-descendant source/topology is required; process starttime, parent
relation, thread/children lists and loaded ELF SHA are checked. During the one
wait, each upper bound is delta_ticks*10ms+20ms for two quantization uncertainties.
The final sample is after switching ACTIVE but before sending the gesture, so
boundary work is conservatively double-charged. Subcaps R100ms/S400ms are deducted
from the same5000ms. Counter/identity errors revoke. CPU counters do not identify
private calls, prove sub-quantum absence of work, attest blocked IO completion or
isolate hostile unobserved descendants. A false-WAIT busy loop must hit the R cap
without trusting a child phase label; source guards separately prevent early API
calls. S's independent cell receipt proves only the separate synthetic draw step.

S polls at most25ms; every IO/record step checks monotonic time, with checkpoints
at most50ms apart. All pipes are nonblocking on S; no provider/driver/crypto verifier
runs on its monitoring loop. Any gap over50ms revokes before later input/ACK/result.
This is a run refusal threshold, not a Linux scheduling or hard kill guarantee.
A paused/descheduled S cannot enforce by that wall instant; after resumption,
elapsed work and the failed gap cannot be erased. Already-started effects cannot
be recalled. supervisor-gap injects an actual75ms sleep, not an OS SIGSTOP claim.

## One use, settlement and evidence roles

R invokes public sign_approved only after core's complete distinct final approval.
It counts driver API entries and auxiliary calls only. Core's consuming approval,
internal backend verification and staging remain unchanged. No new backend counter
or arbitrary backend-fault injection is claimed. Existing source-identical K01
private test evidence keeps original bf51/4bab identities and is not rerun here.

S stages a bounded candidate privately, requires actual direct-child wait4 status,
stdout/stderr EOF, its input FD closed, complete one terminal and fresh guards,
then retains at most one eligible private candidate. Any revocation discards it.
The separate existing oracle runs afterward and cannot restore expiry/currentness
or qualify live publication. Wrong-key/template/signature/id/correlation/trailing
mutations are post-core oracle negatives only. No result is written to a client,
QR service or default route.

After invalidation S clears queued gestures, attempts scoped CANCEL and then kill
after50ms if needed. Cleanup shares one4s boundary from first invalidation. Unknown
wait/IO keeps S, original process/pidfd/channels and reservation quarantined; no
replacement, early successful close or fabricated zero-effect count follows.
The startup-error path is also owned: if pidfd_open fails, the still-unreaped direct
child PID is retained for cleanup, never reused or published. EOF drains precede
reaping to preserve CPU identity while a split terminal is still arriving. Raw
ineligible protocol capture remains available even when parser tails are discarded.
A signal request/terminal/EOF alone is not collection. No O-death recovery or forced
kill erasure is inferred from the old C-death proof.

## Finite first tranche

cases.json fixes33 closed source selectors. Only15 are proposed as the first
future runtime tranche: positive; cancel-wait; caller-100ms; partial-draw;
stale-epoch; false-wait-cpu; resume-before-arm; guard-before-resume; aux-short;
wrong-correlation; policy-change; truncated-result; child-stop; supervisor-gap;
post-core-cancel. These discriminate real wait, authority, independent CPU,
currentness/sign-entry/auxiliary and known collection without a broad campaign.

Other selectors are separately marked later-source-only. Their presence is not
runtime admission, evidence or permission for an automatic full matrix. The recipe
runs no batch automatically. A different failure, lost count or unknown settlement
must remain RED/inconclusive; thresholds cannot be raised to force an expected class.
Parent crypto verification/publication under a responsive additional/incremental
verifier remains a separately admitted future contract under the same remaining
budget and real expiry. This source candidate does not implement that release path.
