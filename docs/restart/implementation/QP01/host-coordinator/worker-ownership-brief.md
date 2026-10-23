# Worker ownership after coordinator death — pre-code experiment

**Finite experiment admitted; no product coordinator admission.** Root review
`8e53a4f4c876974c5bb876a809d8c83a285be9ef` admits the three cases below,
including this pre-code amendment. Original proposal0c remains in Git. Base is coordinator spec
`7996b15d34766e0de1b8c395fb7bcc0b02079935`; its [brief](brief.md) stays historical.
This answers one question: can termination/collection of a Python coordinator
establish termination/collection of its separately spawned RGB worker?
It is not a bug/leak report about request-engine `8b20b98f1e8962cdce8b2fa4cd3be116e7b2bd9d`,
which does not spawn this worker. No such leak has been observed.

The killed coordinator cannot retain its Python owner or execute `finally`.
For this proposed experiment alone, a live external observer **O** retains the
verified process handles and cleanup responsibility. Coordinator fixture **C**
is O's direct child; real RGB worker **W** is C's child. O is a deliberately
configured child subreaper so it can acquire W's actual terminal status after
C dies. This is finite test instrumentation, not a new daemon or an approved
production ownership design. Ordinary reparenting alone is not application
settlement or permission to reuse a resource.

## Frozen inputs and availability

Select RGB source `9220db123eb7ab9c02ef0d407dc6fc8fa3927bf2`, executed source
`5b69e1655c461624218b6df0e3d112b3dc726114`, distinct review
`10d8c65725a73fe3d55cb962644da9d291af8674` and root acceptance
`c3f39b5a9e45a3ca5354961767e879944258334a`. These prove the earlier fixed host
experiment, not the proposed coordinator-death behavior. Under
`docs/restart/implementation/QH01/rgb-input/` at922:

| Input | SHA256 |
| --- | --- |
| `src/main.rs` | `e60b3bc2baec2eded7ee474e101cfa8debd1a88be76d6d7cffce31b4e3e1dcf1` |
| `controller.py` | `548ddea7c7344956a8aaca86db7bfa280e9e525401b9d7ba47f2d2b7b4a7d0b2` |
| `Cargo.lock` | `eb00e1c6ebaa1e241e64574a62902a7ede995c7582cf11bc9d4620bfb4baf243` |
| `parameters.json` | `373a6ffe05a2a6175467deb686490cefefca9d953cc097a9d999f5103c482e98` |

The controller's imported corrected06d `linux-worker-experiment/experiment.py`
remains SHA256 `97fa6da85a1f83c5535050f6c77c588800a069a26ed9a7cd7470f616352a76eb`.
Reuse its mechanism/source evidence; do not turn the corpus harness into an app API.

Read-only inspection on2026-10-23 found the selected author ELF at
`/home/tux/nsealr/.restart-tools/goal/qh01-linux-worker-experiment/docs/restart/implementation/QH01/rgb-input/.runtime/target/release/nsealr-qh01-rust-qr-worker`:
669072 bytes, mode0775, ELF magic, SHA256
`1a4af26b3c738807fb0f1a2e6fb7fcca9d480057642150357ad3c5bf774e6542`.
This matches922 `stable-6/environment.json`; `build-evidence/candidate-command.json`
binds its original locked/offline Rust1.95 build to5b69. No new build or execution
occurred. An initial source read beside that retained ELF returned FileNotFound:
the current author checkout no longer materializes its RGB source subtree.
The frozen source remains available at
`/home/tux/nsealr/.restart-tools/goal/qh01-rgb-input-review` (HEAD10d8): its five
Rust/controller/Cargo/parameter files and imported06d source were checked against
the pins above. C must use that exact source with the explicit selected ELF,
not the absent source path or an implicit different binary. The original13949
case image SHA256 is `1b56f2926382c7da914a877db899494414988d311c65ff459e2f78a8ab4f0216`;
its expected198-byte frame SHA256 is `dae39f12a7744d3c82e2d3e1050b02948a3b72612e5835c237054dabc3d8f3cf`.
Both case files are present there. Only the normal smoke sends the image to W;
the two faults send neither G nor image. The expected frame is never an input to W.
R00 Python3.12.15 has `os.pidfd_open`, `signal.pidfd_send_signal`,
`os.wait4` and `WUNTRACED`; the inspected host is x86_64 Linux6.12.101+deb13-amd64.
Presence of bindings/version does not prove syscall permission or successful
subreaper adoption. Those are mandatory future preconditions, not measured here.

All13 baseline entries remain: width240, height240, pixels57600, raw172800;
RGB888/3bytes/stride720; AS268435456; CPU soft1/hard2 seconds; wall eligibility8s;
cleanup observation4s; stdout512, stderr512, chunks4096. CORE0 also remains.
No reuse of the request-engine947/read948/5s wrapper for this RGB operation;
no change to client100ms, native5s, worker512, JSON704 or static947.

## Three admitted cases, in order

1. **Normal real-worker smoke**, before fault injection and before completing
   fault instrumentation: the new O/C wrapper uses the exact unchanged worker,
   original image and explicit `supervise(binary=...)`. It must record real
   bootstrap/session/policy → G → 172800 RGB bytes → exact198 output → actual
   wait0 and settled IO/owner. No stopping/killing in a successful smoke. This
   is a generic public QR response, with no Node/native-engine/signing operation.
   Select the fixture by both input and output hashes above; the tinted case
   shares output but has a different input and is not selected.
2. **Early coordinator exit before handoff**: a source-bound trace hook exits C
   immediately after actual W spawn (controller line108), before policy/late
   handoff, using explicit exit73 without Python finally. The hook snapshots
   zero G/image counters first. O must discover its actually adopted W through
   kernel parentage, acquire an initial stable handle, and obtain actual terminal
   status. W may already be a zombie after EOF; no status is predicted as success.
   This initial handle of a kernel-proven owned child is not reopening a lost
   known PID. Any owned live remainder gets prompt finite teardown; unsupported
   ownership/accounting blocks the dependent held fault.
3. **Held worker/coordinator kill**: the discriminating sequence below. It may
   begin only after normal and early-exit cases satisfy all cleanup checks.

Each case runs in a dedicated single-threaded O with no preexisting children,
default SIGCHLD and no competing waiter. C waits for O to obtain its initial
handle before proceeding. The source-controlled C creates only selected W;
W's pinned source creates no descendants. `/proc/<tid>/children` is a candidate
list only: its primary manual warns it can omit children during exit. Verify
PPID==O for adoption, acquire pidfd before reaping, and use `waitid(P_ALL,
WEXITED|WNOHANG|WNOWAIT)` to observe terminal child identity without consuming
status; collect via positive-PID wait4. Only ECHILD after every known status is
acquired establishes no remaining children. None/zero event with live children
is not empty, and ECHILD for an expected uncollected child is not success.
All partial setup paths use this accounting, not only the late handoff. If
ownership cannot be proven, do not signal an unproven process or exit O cleanly:
retain O/quarantine and report the exact unresolved state. No watchdog may kill O
while descendant ownership is uncertain. These are test-only ownership measures,
not an adopted product guardian architecture.

## Held-worker discriminant

1. O starts as a dedicated, single-threaded finite observer, with default
   SIGCHLD behavior, no auto-reaper/competing waiter and no inherited worker
   input writers. Before creating C, set/read back O's child-subreaper attribute;
   use the existing R00 environment and no privilege escalation. Unsupported or
   denied operations stop admission, without fallback or retry through another API.
   O owns C from its actual spawn; acquire a pidfd for C immediately.
2. C invokes the unchanged922 controller for the existing original public
   response-get-public-key case. A narrowly source-bound external trace hook
   intercepts `supervise` after line159's policy-readback event and before
   line160/G registration. It reports only the owned W PID and phase facts to O,
   then waits for the test instruction. It does not alter clocks, limits or source.
   The original image may be read by that harness, but **zero G/image bytes** may
   reach W. No new corpus, request processing, QR decode, engine or signing occurs.
3. O verifies W's PPID==C, executable identity, SID==W and PGID==W, plus actual
   unchanged prlimit readbacks; acquire W's pidfd before any signal and recheck
   identity. Retain only verified C/W handles. O sends SIGSTOP to W through that
   handle; C acquires the real WUNTRACED stop status and reports
   WIFSTOPPED/SIGSTOP. A stop status is explicitly **not** terminal collection.
   Missing identity/stop/policy proof makes the intended fault NOT_EXERCISED.
4. Only after that witness, O sends SIGKILL to **C alone**. Acquire C's actual
   terminal wait4 status; never manufacture a return code. Observe W's stable
   handle, kernel state and reparenting to O; only then use O's positive-PID
   wait4 for W. C's status, closed Python pipes, EOF, PID existence or a returned
   kill call alone must never be credited as W's acquired terminal status.
5. Expected discriminant, still unmeasured: W remains stopped/live while C is
   already collected, falsifying “C closed implies W settled”. The retained
   owner is O, with the experiment invalidated and reuse forbidden. If W instead
   terminates, record its actual status and timing; do not force the predicted
   outcome or call absence of a live PID a successful wait. ECHILD/unknown status
   is unresolved ownership, not status0. There is no second worker/request.
6. Immediately after the discriminating observation, O terminates any remaining
   owned W through its pidfd and actually reaps it; no SIGCONT is needed for
   SIGKILL. C must also have an acquired terminal status. Close the known control
   pipes/pidfds and verify O's FD baseline. Always execute this teardown on setup,
   assertion and observation failures as well; never signal a group, PID0/-1,
   an unrelated process or an identity reconstructed after its handle was lost.

Use one bounded activation period within8s, then one shared4s cleanup-observation
window starting at invalidation/coordinator termination, not successive resets
for observation and teardown. Do not consume the window merely waiting to prove
survival: obtain the witness and kill/reap promptly. SIGKILL/status acquisition is
not a hard real-time guarantee. Missing terminal status by4s is **failed cleanup**:
no clean exit/reuse claim, no new experiment, and the live O must retain its
handles/quarantine for explicit root-directed cleanup. Admission must retain this
external cleanup owner; if that cannot be arranged, do not run the fault. A
timeout must never silently abandon an owned child or become a successful result.

## Evidence and narrow kernel basis

The eventual single receipt must bind exact sources/ELF/environment, C/W identities,
phase order, policy readbacks, actual stop and terminal wait statuses, signals,
per-case G/image/decoded-output effects (normal172800→198, faults0), zero
engine/signing effects, shared deadlines, quarantine/refusal and final
FD/child collection. Separate the failed implication from successful emergency
teardown: O's intervention does not prove C cleaned W. The fault-free decoded
image results remain the old922/10d8/c3 evidence, not another run here.

Primary Linux man-pages project pages inspected2026-10-23 (6.19 rendering):

- [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html): SIGSTOP and
  SIGKILL cannot be caught, blocked or ignored; C cannot execute Python cleanup
  in response to SIGKILL.
- [setsid(2)](https://man7.org/linux/man-pages/man2/setsid.2.html) and
  [setpgid(2)](https://man7.org/linux/man-pages/man2/setpgid.2.html): sessions/groups
  are distinct from parent ownership; retain the actual SID/PGID witness. Do not
  substitute process-group signalling or infer cleanup from session separation.
- [PR_SET_CHILD_SUBREAPER](https://man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html):
  an orphan is reparented to its nearest living ancestor subreaper, which can wait
  for it. This scopes O's proposed instrumentation, not a measured product guarantee.
- [pidfd_open(2)](https://man7.org/linux/man-pages/man2/pidfd_open.2.html) and
  [pidfd_send_signal(2)](https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html):
  retain stable process references; use flags0/process scope only. Readability
  indicates termination, not acquired wait status. Permission/errors still matter.
- [proc_tid_children(5)](https://man7.org/linux/man-pages/man5/proc_tid_children.5.html):
  child enumeration can omit entries during exit; it cannot alone establish
  empty ownership. Terminal WNOWAIT observation and final ECHILD remain required.
- [wait(2)](https://man7.org/linux/man-pages/man2/wait.2.html) and
  [wait4(2)](https://man7.org/linux/man-pages/man2/wait4.2.html): distinguish stopped,
  exited and signalled states; wait4 selects the actual child and supplies status
  and usage. WNOHANG0 and ECHILD are not successful terminal collection.

The pre-code amendment performs no signal, subreaper mutation, worker/coordinator
experiment, test suite, build, CI observation or product edit. Still missing are
the admitted runtime witnesses for pidfd permission/adoption, the held-worker
negative and finite actual teardown. The production owner surviving coordinator
death remains undecided; this baseline tests that seam before implementing it.
No camera/ARM/Pi/P4, hostile descendants, secret isolation, hardware latency,
task/profile/release or PR45 acceptance claim follows.
