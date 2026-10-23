# Independent corrected Linux worker review

PASS for the corrected finite host IPC/resource experiment on candidate `06d213fd46e654bfe2ac43e4a88963a346d35973`, tree `c7a11c42776edabe3ca22226dce8c05c8460f850`. Finding **QH-WORKER-RUNTIME-01 is resolved on this candidate**. No new finding remains within this review scope. This is neither task acceptance nor permission to enable a product route.

The reviewer is `/root/a02_resume`, distinct from B01. Root owns the separate whole-packet provenance/manifest/claims review. This review reuses the complete 694-line source review at `33799c83e1d4fb67b79092aa68c3bd07c28a0111` and covers the 11-addition/1-deletion controller change, the entire external 95-line regression, their precommitted expectations and exact execution bindings. The unchanged helper, validator, state/IO/ownership paths were not audited from scratch again.

## Correction and scheduling point

At `experiment.py:602`, the last successful eligibility condition samples `time.monotonic()` after acquired child status, both EOFs, parent FD closure and owner settlement. It requires a sample strictly before `start + 8.0`. The late branch records `wall-at-admission` and `expired-at-result-admission`; it does not reset quarantine, alter cleanup or reacquire the clean owner. This makes the fresh sample the logical admission point. It does not promise a hard return deadline or prevent later descheduling.

The external driver locates the unique eligibility assignment using its AST, traces only `run_case`, and sleeps once for 8.25 real seconds at that line event. Before sleeping it requires actual owned exit 0, full 172800-byte image and one control byte, exact 198-byte output, closed parent I/O/FDs, no prior error and a released, nonquarantined owner. The fixed timestamp is evaluated after the pause. There is no fake clock, record mutation, internal test hook, altered worker or budget change.

The [preflight](source-validation.json) verifies the pre-fix expectation at `a080e5a459f98b881f767bda064afcf7431d6cbf`, identical driver bytes across RED/GREEN/final candidate, corrected harness equality with executed source `0d29f42eda4a59c93c98ef361af6bf81c4eef028`, and the original parameters, 21 expectations and additive session amendment. Eleven source/tooling/input hashes were checked before execution and again afterwards.

The original author RED remains an actual failure: old harness admitted the result at 8.275571 seconds after the controlled pause, so that regression exited 1. The same author driver on the fix rejected it at 8.275950 seconds and exited 0. Both receipts remain untouched; the reviewer did not rerun the defective source. The old review's blocked verdict remains correct for old candidate `31df3027a6e0903d8efa183dd3d4f964ebdf3949`; the original author 22 PASS observations and initial unsupported `posix_spawn(..., setsid=True)` failure also remain historical evidence.

## Independent execution

Exactly two reviewer commands ran, sequentially, using the pinned R00 CPython 3.12.15 interpreter, `-I -B`, and the exact R00 direct environment map with only scoped TMPDIR, XDG_CACHE_HOME and PYTHONDONTWRITEBYTECODE overrides. The unmodified author driver/harness ran from this candidate checkout. There was no rebuild, install, R00 mutation, source change or additional campaign.

| Reviewer execution | Result | Measured evidence |
| --- | --- | --- |
| [One delayed regression](regression-01/regression.json) | PASS, exit 0 | Actual pause 8.250305970 s; final admission 8.276367387 s; eligible false, wall-at-admission; known owner remains reusable |
| [One complete stable campaign](stable-01/summary.json) | 22 PASS, 0 masked, exit 0 | 26.292557265 s inside harness; 16 actual direct children, all collected |

The deliberately expired positive row correctly has `NOT_EXERCISED` under the original positive validator. That is the expected negative observation for this separate regression, not a masked member of the stable 22. Its existing `duration_seconds` field was sampled after settlement but before the controlled pause; the late decision is measured by `admission_elapsed_seconds` and the regression clocks. No claim of an 8-second total return is made.

Exact arguments, timestamps, scoped environment differences and source hashes are in [regression-command.json](regression-command.json) and [stable-command.json](stable-command.json); corresponding controller stdout/stderr, both contexts, all 22 campaign JSON traces and bounded retained stream bytes are included. [runtime-analysis.json](runtime-analysis.json) records 37 passing checks derived from the actual traces and raw data, beyond the aggregate PASS fields.

## Actual observations and scope

- The positive child established kernel SID=PGID=owned PID before policy readback, one-byte G and image input. All admitted rows retain that ordering, with an actual identity check before each write. The initial SID/PGID fields at spawn return are inherited identities; they are not the later session-established observation. Positive output was exactly the predetermined 198 public bytes after actual `wait4` exit 0.
- The same frozen 240×240 RGB888 image remained 172800 bytes with stride720. Independent width239, height239, pixel57599 and raw-cap N−1/N/N+1 rows exercised their separate boundaries; only the relation row used a transient N−1 view. Caps need not have a mutually consistent maximum product.
- Actual child AS policy was 268435456 bytes; the oversized virtual mapping returned ENOMEM 12 and exit40, with no parent signal. CPU policy was soft1/hard2; actual kernel SIGKILL arrived after 1.998574 CPU seconds, without a parent kill or wall invalidation. CORE stayed0. The permission row produced real EPERM1 after the lowered AS ceiling and sent no control/image bytes.
- Separate stdout/stderr cases each observed 513 bytes in the selected stream, retained512, and invalidated on its own overflow. The requirement is retained≤512, not mandatory filling. Read/write requests stayed within4096. Wall invalidation occurred at8.008632 seconds after complete input; backpressure remained supervised and invalidated at8.002854 seconds after65536 image bytes. Observed cleanup remained within the unchanged4-second window.
- All five abort phases remained ineligible, with phase-specific input/policy/output preconditions. Live ownership and the interval after acquired wait but before parent I/O closure both refused another operation without changing the generation.
- The controlled missing-session child retained the inherited identity, received no policy/G/image, and was invalidated at8.004888 seconds. Actual wait and FD settlement left the owner reusable. The next real child, generation22, established its session and completed valid I/O.
- That final stolen-status row acquired real exit0 through its controlled first reaper, then the owner received actual ECHILD10. The owner received no fabricated/default status, remained ineligible and entered terminal quarantine; another acquisition was refused. Quarantine was never reset to make the suite pass.
- All16 campaign children and the separate regression child were collected; their17 `/proc` entries and both controller entries were absent after return. Parent SID/PGID and AS/CPU/CORE limits were unchanged, initial/final actual thread counts were1, and FD sets were restored. The reviewed trusted helper creates no extra helper process/thread. The harness's `new_threads`/`new_descendants` fields are static source declarations; they are not independent arbitrary-descendant measurements.

This proves only the finite Linux x86_64 host experiment with these trusted helpers and public inputs. RLIMIT_AS and retained IPC bounds do not establish RSS, cumulative allocation/work, arbitrary subtree containment, hostile decoder safety, secrets isolation or real-time return guarantees. The experiment emits a predetermined envelope; it does not decode QR or exercise keys/crypto. No TypeScript/product port, ARM/Pi/target, camera, actual client latency, physical qualification, task completion or release is claimed. All47 criteria/dependencies/resources/releases remain unchanged; no PR or CI was started.

The source, original failures, original run receipts and old review are untouched. The new review and its raw proof are confined to this review directory. Root's separate affected provenance review is frozen at `00c93399804b83410440c8f4fe3383ff62dc63e3`; it ran no worker campaign. Any later integration decision remains with root.
