# F1/F2 correction of the first host gate

This addendum supersedes the affected clock/parser claims of author1ba, following
root's distinct [changes-requested review e480](https://github.com/nSealr/nsealr/blob/e4807ce2a2757f1058a72ce9c4b32c7720f9a321/docs/restart/implementation/reviews/QP01-host-owner-component/review.json).
It does not rewrite old reports or claim a reviewed component/device result.
[Expectations](expectations.json) were committedcba7117d before the source change;
[inputs](inputs.json) and executable8104c501 were frozen before all three runs.
[Result](result.json) binds commands, counts, source correspondence and limits.

F1 removes the constant monotonic clock from the new first-gate context. The
actual client now uses its unchanged default performance.now. The existing
100ms timer and C5000ms safety are unchanged; now:1 remains explicitly synthetic
fixture wall metadata. After real W/IO/O settlement and259 private decoded bytes,
the new test holds JavaScript synchronously for110ms of real elapsed time. Before
the timer callback can run, the same before_present rejects with CapabilityError,
reason runtime_unavailable and the exact deadline-expired message; abort is still
false and C input is0. In the stable run the measured hold was110.023384ms.
This is a negative test hold, not a changed deadline or hard real-time guarantee.
The later outer signer_transport_timeout occurred during awaited actual C cleanup;
it is recorded separately and cannot substitute for the synchronous guard proof.

F2 requires worker_ready in the existing presented/P/not-unused state, and unused
with no phase/worker/G/image/input. A decoded record now requires exact bounded
stdout observed=retained=result and stderr observed=retained. Nine pure controls
check the named relations against valid synthetic baselines. They spawn no process;
all synthetic PID/pipe fields are excluded from worker accounting. Truthful decoded
records committed before late cancellation remain valid evidence; the real late
currentness/private-cancel gate still prevents C exposure. No second state engine
or change to operational O was introduced.

Parser focus9/9 and the real elapsed-deadline focus passed, then exactly one stable
full matrix passed on the same8104 source:39 subcases in8 groups, preserving all29
original cases plus one real deadline case and nine pure parser controls. Stable
kernel descendants total64 distinct PIDs:20 native C implementations,1 malformed-C
handshake helper,21 operational O,11 real RGB W and11 no-W channel helpers. All
actual children closed and all W terminal statuses/IO were collected; phase and
terminal never count the same W twice. The separate deadline focus collected3
additional distinct C/O/W processes; parser focus spawned none. No other runtime
was performed for this correction.

Operational qr_worker.py, its five focused tests and the entire existing C-owner/
default Node source are byte-identical. Their scoped5-unit and5+14 evidence is
reused. The eleven generated Python helpers are also byte-identical to their
previous actual export/py_compile. Of the old77 postimages,76 remain exact; only
first-gate.ts changes. The old manifest is verified against1ba, not incorrectly
against the current driver. This addendum's manifest covers the current delta.

All original false-green/helper/reader failures and rootF1/F2 findings remain.
The older runs prove their real timer observations but cannot substantiate a real
monotonic currentness clock. This correction alleges no O leak and does not prove
O-death or failed-quarantine recovery, cold-source provisioning, camera/device,
ARM/Pi/P4, secrets/provider, default route, task completion or physical release.
No fullPi/Bridge/Rust suite, build/install/feed, hostedCI or PR ran. The graph is
unchanged. All processes and command sessions are closed; distinct affected review
and independent replay remain pending.
