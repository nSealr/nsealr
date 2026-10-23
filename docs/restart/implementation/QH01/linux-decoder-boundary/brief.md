# One-shot Linux image worker: limited resource boundary

A keyless, one-job worker is a feasible **host experiment boundary** for checked
input/IPC bytes and Linux per-process AS/CPU limits. Complete end-to-end resource
containment is **not established**: startup, total wall latency, arbitrary
children, RSS/cumulative allocation and logical decoder work are distinct.
This is source/specification only, based on current994a8b; its actual-main gate
was pending at assignment. No worker, decoder or sandbox is selected or executed.
The prior615bf51f/132b4c42 decision remains source-API-only acceptance.

| Property | Source-supported mechanism | Limit of the claim |
| --- | --- | --- |
| Dimensions/raw bytes | Parent checks declared dimensions, stride/product and exact available length before conversion, copy or IPC | Checks do not qualify camera capture or an encoded-image parser |
| Worker address space | RLIMIT_AS affects VM growth, page-granular | Not RSS, kernel/parent memory or cumulative allocation; lowering below current usage does not reclaim it |
| Worker CPU | RLIMIT_CPU is CPU-seconds, with soft/hard actions | Not wall time, hard realtime or logical parse_work |
| Deadline | Parent monotonic expiry makes output ineligible and initiates cleanup | Popen creation may exceed timeout; timeout/signal is not exit/reap |
| Output/diagnostics | Independent bounded binary readers before append | communicate/capture-all is not a byte cap |
| Reuse | Actual child cessation plus owned I/O/callback settlement | Direct-child wait and group signal do not prove arbitrary-subtree cessation |

Linux limits are process attributes; descendants inherit limits but do not share
a single aggregate job budget. A privileged worker may raise hard limits.
The proposed run must record credentials/limit support and refuse unsupported
policy before input, without elevating privileges. Lowering AS below bootstrap
usage may succeed: a limit readback alone proves neither reclamation nor an
all-time VM ceiling. Startup footprint/accounting and target behavior remain
unqualified. [Linux getrlimit(2)](https://man7.org/linux/man-pages/man2/getrlimit.2.html)
is authoritative for these Linux distinctions, rather than generic RSS labels.

The minimal proposed sequence uses a fixed absolute executable, shell=False,
explicit non-secret environment, closed unrelated descriptors and a fresh session.
The trusted worker entry blocks before image/decoder initialization and accepts
hostile bytes only through the parent's gated input. After Popen returns, the
parent applies and reads back the worker's finite soft/hard AS/CPU limits using
Linux prlimit, then releases bounded input. No preexec_fn is used in a threaded
parent. This does not bound loader/interpreter work before that point.
[Python3.12 subprocess](https://docs.python.org/3.12/library/subprocess.html) documents
the spawn/preexec/pipe constraints; [resource](https://docs.python.org/3.12/library/resource.html)
provides Linux prlimit/set/get bindings. A missing/error/mismatched policy means
zero hostile input, rejected output and cleanup; it is not permission to proceed.

Parent readers/writers must progress concurrently in bounded chunks with separate
stdout/stderr retained-byte counters; overflowing either stream stops eligibility
before further append. Input backpressure is covered by supervision too. No
unbounded read, readline, capture_output or post-timeout communicate is the quota
mechanism. Bounded retained logs carry explicit overflow/truncation metadata,
never a claim to contain the complete flood. Process AS does not cap these parent
buffers. The unchanged manual-port frame/JSON/retained/parse_work limits still
apply in their original units; none becomes AS bytes or CPU seconds.

Expiry/cancellation marks the operation stale immediately. Its process owner
continues cleanup, records actual termination status and waits for owned pipe and
callback settlement. An expired spawn that returns later must still be collected
and cleaned up. Kill success only reports signal delivery; a process-group signal
covers current members and is not an ownership boundary for escaped descendants.
[Linux kill(2)](https://man7.org/linux/man-pages/man2/kill.2.html) supplies that scope.
The existing CPython wait path waits on self.pid, not a subtree. Exclusive wait
ownership is required; missing/stolen status cannot establish successful work.
Unknown children, unreaped work, held pipes or failed cleanup prevent reuse.
No same-UID process or rlimit is claimed to protect parent keys, memory or files
against a compromised worker. Descriptor/environment minimization is not a secret
sandbox, decoder safety proof or trusted-UI/authorization gateway.

This maps to the existing createManualQrRouteDispatcher without changing it:
open/present/scan/close remain one owner's lifetime; before_present remains host
currentness, not physical approval. Abort invalidates results, not device recall.
The client retains pending capacity until the real dispatcher settles. close()
may resolve only after confirmed owned quiescence; a rejection keeps the factory
quarantined. A timer, signal, closed pipe or early scan rejection cannot substitute
for that close condition. The future Python host experiment does not itself prove
integration into the TypeScript port/client.

Exactly one proposed host experiment is in experiment.json. It uses disposable
public fixture bytes and deterministic helper behaviors to distinguish each
resource/lifecycle failure, with no decoder choice or QR-decode claim. Budgets
are explicit run inputs, with no default numeric profile; absence blocks running.
Implementation and execution need a later concrete root admission. Sources and
immutable input/artifact bindings are in source-bindings.json. All five QH01,
three QP01 and six Q02 criteria remain incomplete; no app/graph/gate changes.
