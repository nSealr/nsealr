# Distinct review: finite host worker ownership experiment

**PASS for the bounded experiment only; findings: none.** Reviewer
`/root/sdk_dependency_probe` is distinct from the ownership author. Reviewed
candidate `a16fa6aae19a98066a206328d20578ce328f34d2`, tree
`104c3444638f2b80e9dfcf4e1f734aa79b197870`. This review does not admit a product
guardian or close a task, resource, physical or release criterion.

## Source and accepted expectations

I read the amended pre-code brief, root scope approval
`8e53a4f4c876974c5bb876a809d8c83a285be9ef`, the full runner, report and result,
the actual selected RGB controller/worker, and the imported Owner/wait helpers.
The [source verification](source-verification.json) checks all 43 manifest
members, the exact 44 additions including that manifest, and all 8,645 unchanged
base postimages from `7996b15d34766e0de1b8c395fb7bcc0b02079935`.
Runner/report/result hashes match the assigned candidate. No product, SDK or
task graph source was changed.

Before execution I separately checked every runner source/tool/ELF pin, both
fixture hashes, the thirteen baseline fields and CORE0 in
[input preflight](input-preflight.json). The retained real worker remains
669,072 bytes, SHA256
`1a4af26b3c738807fb0f1a2e6fb7fcca9d480057642150357ad3c5bf774e6542`.
The original input is 172,800 bytes, SHA256
`1b56f2926382c7da914a877db899494414988d311c65ff459e2f78a8ab4f0216`;
the separate expected 198-byte frame is comparison data only. I used the pinned
R00 Python 3.12.15, with UID/EUID 1000, no effective capabilities and no
privileged interpreter/worker file attributes. No build or dependency fetch was
needed.

## Control flow and ownership

The unchanged RGB `supervise` line 108 follows actual `posix_spawn`, before
`record['pid']` assignment and policy setup; the early C hook really exits73
there. Line 160 follows policy readback at159 and precedes G registration/write.
The normal/held hook therefore observes zero G/image effects before releasing
or stopping W. The real worker reads G before image allocation/decode; EOF at
that gate returns71. No expected output is passed to the worker.

In `worker_ownership.py:77-110`, a fresh, single-threaded O with no children and
default SIGCHLD verifies the frozen inputs and its subreaper setting. C waits
for O's initial handle/start handshake. Lines197-253 acquire initial pidfds only
after kernel PPID verification, compare start ticks/parentage, and consume
terminal status with positive-PID `wait4`. A kernel-proven adopted child receives
an initial handle; this is not reopening a previously lost PID. Late handoff
also verifies `/proc/W/exe`, SID/PGID and actual AS/CPU/CORE readbacks before any
controlled signal. All signal calls retain the owned pidfd and process scope.

Candidate enumeration is not empty-child proof. The source combines candidates
with nonconsuming WNOWAIT observations, preserves a live result when waitid has
no terminal event, and admits final ECHILD only after known C/W status evidence.
This matches the selected primary [wait semantics](https://man7.org/linux/man-pages/man2/wait.2.html),
[subreaper adoption](https://man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html),
[pidfd lifecycle](https://man7.org/linux/man-pages/man2/pidfd_open.2.html), and
the explicit [child-enumeration warning](https://man7.org/linux/man-pages/man5/proc_tid_children.5.html).
The [source observations](primary-source-observations.json) preserve the two
initial viewer timeouts and direct retrieval hashes of the same primary URLs.

The real `WUNTRACED` stop witness is not terminal collection. Normal W status
comes from C's unchanged actual-wait record; O does not steal that status. Fault
W status comes from O after adoption. No status0 or successful cleanup is
manufactured from EOF, PID existence, kill return, waitid None or ECHILD.
Invalidation keeps the reservation unavailable. Cleanup retains one 4 s window,
including teardown; early-exit uses its recorded fault time. A missing status
retains live O and its handles in quarantine. The source review of that fallback
does not claim it was exercised.

## One independent stable sequence

I ran the unchanged final runner once per case, normal → early-exit → held-kill,
stopping dependents on failure. Every command used the actual selected ELF and
the documented CLI; each dedicated O remained the external cleanup owner.
There was no external kill watchdog or command timeout and no rerun. See the
three [command receipts](runtime/), complete raw events/results and
[independent result analysis](independent-results.json).

| Case | Actual independent outcome |
| --- | --- |
| Normal | O1787358; C1787359 raw0 and W1787360 raw0. G1, full RGB172800, exact198 bytes SHA256 `dae39f12a7744d3c82e2d3e1050b02948a3b72612e5835c237054dabc3d8f3cf`; no signals; C collected W. |
| Early C exit | O1787361; C1787362 raw18688/exit73, adopted W1787363 raw18176/exit71, both actually collected by O. Zero G/image, no late policy handoff or claimed installed limits, no signals. |
| Held W / killed C | O1787364; real W1787366 stop status4991/SIGSTOP. C1787365 then had actual raw9/-9. W remained `T`, PPID1787364, stable pidfd not readable and no terminal status. Only afterward O sent W SIGKILL and acquired its separate raw9/-9. |

The held witness at 0.018435 seconds follows C collection and precedes W kill
and W collection. The observed signal sequence was W:STOP, C:KILL, W:KILL;
each target was its verified C/W pidfd, with no group, PID0/-1 or foreign signal.
All six children have actual terminal status evidence. Each O recorded final
ECHILD, restored its FD baseline, SID/PGID and limits, remained single-threaded,
and exited. No observer or unresolved ownership remains. No runtime failure or
cleanup timeout occurred.

## Claims, limits and integration perimeter

The report's narrow conclusion is supported: collecting C did not establish W
termination/collection in this experiment. Separate successful emergency
teardown does not prove C cleaned W. The earlier author smoke/three-case receipts
retain their original source identities; this review adds three independent
cases and six children rather than relabelling old runs.

O/C and the non-forking worker are trusted experimental components. O death,
hostile descendants, arbitrary crash interleavings, secret isolation and failed
quarantine recovery remain untested. This is no product ownership/API design,
hard-time guarantee, engine/signing result, camera/ARM/Pi/P4 qualification or
hardware/release evidence. Libc and the actual native worker bootstrap did run;
there is no zero-native-execution claim. Existing native8b does not spawn this
worker, so the result supplies no leak finding about that caller. Worker512,
JSON704/static947, native5s and client100ms are untouched.

This review is based on the experiment's historical7996/5c ancestry. It must not
be whole-merged or rebased onto current accepted mainbd892b70. Root must select
only the reviewed new experiment/review postimages through its ordinary
integration process. No hosted CI, product suite, old six-image RGB corpus,
SDK write or task graph update was performed here.
