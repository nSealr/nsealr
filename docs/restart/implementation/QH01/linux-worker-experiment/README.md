# Linux worker: one host process/IPC experiment

The one new stable campaign on [correctedsource0d29f42e](https://github.com/nSealr/nsealr/commit/0d29f42eda4a59c93c98ef361af6bf81c4eef028) observed **22/22 rows PASS in26.279s**, using16 explicitly owned direct children. The parent collected every child, restored its descriptor set and retained its original session, group and resource limits; one parent thread remained. The final owner is deliberately quarantined after the stolen-status negative. These are author observations pending distinct root runtime/code review.

This helper does **no QR decoding or signing**. It consumes the existing public240×240 RGB888 buffer (172800bytes, stride720) and, on the positive path, returns the existing predetermined198-byte public envelope. The [original assets](../native-qr-probe/expected/response-get-public-key.envelope) retain their13949e4e source identities; no image corpus was copied or generated. Exact hashes, source roles and all case receipts are in [result.json](result.json).

## What executed

The [harness](experiment.py) uses the pinned R00 CPython3.12.15 and standard library, an explicit nonsecret child environment, absolute executable and `-I -B`. Plain `os.posix_spawn` creates the trusted bootstrap with pipe fd actions. The child calls `os.setsid` before reading control or image data. The parent queries actual kernel SID/PGID until both equal the owned PID, then sets and reads back AS/CPU/core limits before sending the gate and image. Kernel identity is checked again before every write. No reported ready marker or additional control channel substitutes for these queries.

The parent supervises stdin/stdout/stderr concurrently with nonblocking descriptors. Temporary reads/writes stay within4096bytes; stdout and stderr retention each stay at or below512bytes, including overflow. Direct `wait4(ownedPID, WNOHANG)` acquisition plus I/O settlement controls reuse. Only positive owned PIDs receive signals. The trusted helper creates no descendants or threads.

| Group | Stable observation |
| --- | --- |
| Positive | Exact198-byte output; actual status0 and I/O settlement before reuse. |
| Dimensions | Width239, height239, pixel57599 and separate stride/length relation each refused before spawn. |
| Raw cap | Actual buffer remains172800bytes: cap172799 refuses;172800/172801 reach the helper. |
| Policy | Real EPERM trying to raise already-lowered AS hard limit; effective256MiB unchanged, zero input. Added no-session fixture sends zero control/image bytes and refuses at the existing8s deadline. |
| AS | New virtual mapping over256MiB returns actual ENOMEM; no large mapping pages are touched. |
| CPU | Helper first validates finite1/2s limits; kernel SIGKILL at1.996160 CPU seconds, with no parent signal. |
| Wall | Sleeping helper becomes ineligible at8s and is collected after the parent's owned-PID SIGKILL. |
| Stdout | Finite513-byte output observed,512 retained; stderr quiet. |
| Stderr | Finite513-byte diagnostics observed,512 retained; stdout bounded. |
| Backpressure | Helper does not read image; parent remains responsive with65536bytes written, then invalidates/collects at8s. |
| Abort | Before spawn; after spawn/before session; after policy; during input; after output/before settlement. All stay ineligible. |
| Status | Valid prior input/output, controlled first `wait4` really consumes status0, then the owner receives actual ECHILD. Its missing status is never credited as0; subsequent ownership is permanently refused. |

The actual trace records inherited identity at spawn return separately from `last_kernel_identity` and the later `kernel-session-established` event. Session establishment is not atomic with process creation. Each live operation refuses a second acquisition; another refusal occurs before parent I/O/selector settlement. Subsequent actual operations use the same owner after known cleanup. The no-session negative is followed by another real worker; the final lost-status negative deliberately ends reuse.

## Source and execution history

Original expectations78372015 fixed21 rows/12 groups and [parameters.json](parameters.json) before code. The thirteen baseline values and seven independent cap overlays remain byte-identical. AS256MiB, CPUsoft1/hard2s, wall8s, cleanup4s, stdout/stderr512B, chunk4096 and core0 are host experiment inputs, not hardware capacities or defaults.

The first focused run on37d112e1 failed before creation: optional `posix_spawn(setsid=True)` was unavailable. [focused-01](focused-01/summary.json) remains unchanged: zero workers/data/signals and21 historical NOT_EXERCISED obligations. That was a missing Python flag, not a kernel EPERM. The [preserved blocker result](historical-blocker-result.json) and [copy inventory](historical-copy-inventory.json) retain exact original bytes/roles.

Root [readmissiona94c24e7](../../reviews/QH01-linux-worker-blocker/readmission.json) explicitly selected the child-setsid strategy. [Amendment72dd25ad](strategy-amendment.json), committed before revised code, adds exactly one no-session gate case. There is no automatic fallback after a denied call. Required [focused positive](focused-02-positive/summary.json) passed first; [startup/abort focus](focused-03-startup-abort/summary.json) and [remaining isolated causes](focused-04-boundaries-causes/summary.json) passed next. The [original stable campaign](stable-01/summary.json) ran on2ba9b73c, SHAe90e6365453b908df084e3fc4636d7e30d7da4c759250a09f07bf48f0d2ab599. It remains historical; the later distinct review identified a scheduling case it did not execute. All original raw files remain byte-identical.

Each run directory contains exact command, source hash, environment, bounded raw stream bytes, case events and summary. The command receipt binds the R00 environment file as a **direct map**, plus scoped TMPDIR/XDG/PYTHONDONTWRITEBYTECODE overrides. A reproducible invocation uses that map and exact argv, with a fresh `--out` directory; the harness refuses overwriting prior output. There were nine controller executions in total,56 created children, one original historical complete campaign and one new complete campaign on the corrected source. No install, interpreter rebuild, R00 mutation, hosted CI or PR operation occurred.

## Final-admission deadline correction

Distinct [A02 review33799c83](deadline-correction/reviewer-before/review.json) found QH-WORKER-RUNTIME-01: an earlier loop clock sample could be stale by final result admission after wait/cleanup. [The expectation](deadline-correction/expectation.json) was committed before probe or fix. The finite external [regression](deadline-correction/regression.py) uses standard-library tracing to pause the actual controller at its final eligibility assignment, after verified real status0, exact output and closed descriptors. It changes no clock, record, worker code or numeric budget and needs no internal test hook.

The [old-source RED](deadline-correction/red/regression.json) slept8.250101 real seconds and reached admission at8.275571 seconds, yet old code reported eligible=true/PASS; regression exit1 preserves the defect. The minimal correction samples monotonic time directly in the final predicate after required settlement. The [same-probe GREEN](deadline-correction/green/regression.json) slept8.250099 seconds, reached admission at8.275950, and rejected output with wall-at-admission; known cleanup/reuse remained intact. Its raw original-positive validator says NOT_EXERCISED because that positive was deliberately expired; the regression's required rejection passes. This does not change any original22-case meaning.

[Six affected checks](deadline-correction/focused/summary.json) and [one new stable22 campaign](deadline-correction/stable-02/summary.json) then passed on source0d29f42eda4a59c93c98ef361af6bf81c4eef028, SHA97fa6da85a1f83c5535050f6c77c588800a069a26ed9a7cd7470f616352a76eb. No runtime source changed afterward. The new clock sample defines result eligibility; it is no guarantee of return or cleanup before a wall time. Exact earlier entry metadata and the four distinct review files are preserved with [source/target bindings](deadline-correction/before-entry-inventory.json) and [review copy bindings](deadline-correction/review-copy-inventory.json). Root's23d6 provenance check was not runtime approval. Distinct affected review remains pending.

## Limits

AS bounds virtual address space, not RSS, cumulative allocation, parent/kernel or total-job resources. CPU seconds are not a logical decoder-work budget. The monotonic deadline invalidates output and starts cleanup; the4s cleanup observation is not a universal spawn/kill/reap or hard wall-time guarantee. Existing bootstrap footprint is recorded and is not retroactively reclaimed or atomically bounded.

The experiment uses a trusted deterministic worker, finite output floods and no descendants. It establishes no protection against a compromised/privileged worker, escaped descendants or access to parent files, memory or secrets. It exercises no QR decoder, actual TypeScript port, camera, ARM/Pi, physical screen/readability, real-client timing or target resource profile. All47 criteria and all QH01/QP01/Q02 completion states remain unchanged. Product adoption and any future decoder/optical work require their own reviewed scope and real integration gates.
