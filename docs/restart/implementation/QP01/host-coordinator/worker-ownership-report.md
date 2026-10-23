# Host worker ownership experiment

The held-worker case disproved the tested implication **“C collected implies W
collected.”** After O killed and collected coordinator C, worker W was still
stopped (`T`), its parent was O, its pidfd was not readable, and no W terminal
status had been obtained. O refused reuse, then separately killed and reaped W.
This is an observed software dependency for a future coordinator, not a leak or
defect in native request-engine8b, which does not spawn this worker.

Root scope review `8e53a4f4c876974c5bb876a809d8c83a285be9ef` admitted the
[amended brief](worker-ownership-brief.md), committed as00c3 before runner code.
The [runner](worker_ownership.py) is finite experimental instrumentation, with
an external, dedicated single-threaded subreaper O and its child C. The worker,
RGB controller,13 parameters+CORE0, original fixture, R00 interpreter and ELF
are unchanged and hash-checked before each run. No product owner architecture,
daemon, route or formal task/resource/release state was added.

| Run | Source | Actual outcome |
| --- | --- | --- |
| Early normal smoke | af15dbf7ca53973253df311f34805f5bf8d48d44 | C0, W0; G1, RGB172800, exact198; no signals |
| Stable normal | 34e7769705a2a519908d9dacfec90e3cf9a18624 | C0, W0; G1, RGB172800, exact198; no signals |
| Stable early exit | same34e77697 | C73 before late handoff; adopted W71; both actual wait4; no signals |
| Stable held kill | same34e77697 | W stopped4991/SIGSTOP; C killed/wait9; W still live; separate O kill/wait9 |

The stable sequence ran normal → early exit → held kill, stopping dependents on
failure. All three passed. The first smoke preceded completion of the fault
instrumentation. The stable normal check also exercised the added reservation
and final-settlement logic, so it is a separate run rather than relabelled early
evidence. Four actual runs total, eight C/W children, all terminal statuses
acquired; the stable three account for six. No runtime run failed and no rerun
followed the stable sequence. [Result and command bindings](worker-ownership-result.json)
point to original receipts, stdout/stderr, kernel/status events and raw decoded
bytes. Timing fields are observations only, with no target latency guarantee.

The selected input is the original response-get-public-key image SHA256
`1b56f2926382c7da914a877db899494414988d311c65ff459e2f78a8ab4f0216`, not the
tinted image sharing the expected output. In both normal runs, the real unchanged
worker decoded198 bytes with SHA256
`dae39f12a7744d3c82e2d3e1050b02948a3b72612e5835c237054dabc3d8f3cf`.
The expected frame is comparison data; it is never passed to W. O additionally
hashed `/proc/W/exe` and read kernel SID/PGID and actual AS/CPU/CORE policy before
allowing G in the normal case or sending SIGSTOP in the held case.

The early-exit case intentionally exits C immediately after W spawn, before
policy installation and before the late PID message. O first finds W from its
own kernel child accounting and obtains an initial pidfd while W is already an
adopted zombie. Only after that does O read C's disk snapshot to correlate the
PID and zero G/image counters. W's actual71 is consistent with the pinned worker's
gate-read failure on EOF; it is not fabricated or treated as a successful decode.
This case does not claim the resource limits were installed before C exited.

The held case acquires real stop status via C's positive-PID
`wait4(W, WNOHANG|WUNTRACED)`; stop is not terminal collection. O then sends
SIGKILL to C's verified pidfd alone. The observed surviving W remains adopted
and reserved. The separate W SIGKILL and actual wait4 occur within the same4s
cleanup window, which starts before the C kill and is not reset for teardown.
In the early case the window starts at the recorded pre-exit invalidation time.
The unchanged8s activation deadline remains. No process group, PID0/-1 or
unrelated process receives a signal, and O is not killed by a watchdog.

The dedicated O uses `/proc/.../children` only for candidates, verifies PPID
before initial handles, observes child status without consuming it using
`waitid(...WNOWAIT)`, and consumes status only with positive-PID wait4. Final
ECHILD follows all known terminal statuses; None and unknown status are never
success. All stable runs restore O's FDs, preserve its SID/PGID and resource
limits, and remain single-threaded. The controller's own normal IO/FD settlement
is also recorded. The reservation refusal uses the existing experimental Owner;
it is not a production scheduling or reuse API qualification.

Both fault hooks remain before G and record zero G/image effects. Neither fault
decodes a QR or calls an engine. The normal smoke does decode a real public QR
response; it performs no Node/native request-engine/signing operation. Loading
libc for the subreaper syscall and starting the real native QR ELF are genuine
native bootstrap effects, not “zero native execution.”

The source availability lookup failure from pre-code work is preserved in the
brief: the retained author ELF exists, while its old worktree no longer contains
the source subtree. The runner explicitly imports the frozen10d8 review checkout's
byte-identical922 source and passes the verified retained ELF path. This does not
rebuild anything or modify either source worktree. Kernel semantics and their
limits are linked in the brief; notably `/proc/.../children` alone is insufficient
for complete accounting while children exit.

This tests three specific host cases with trusted, non-forking W and trusted C.
It does not test O death, hostile descendants, secret isolation, arbitrary
crashes at every instruction, camera images, ARM/Pi/P4, hardware latency or a
physical/profile release. The cleanup-error path deliberately retains live O
and its handles instead of claiming successful exit; that path was not exercised,
and SIGKILL/wait has no hard real-time guarantee. All completed observers exited,
with no remaining child or process handle. No build, dependency acquisition,
full product suite, hosted CI or PR operation was performed. Distinct affected
review of this exact package is still required.
