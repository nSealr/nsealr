# Linux worker source/runtime review

**BLOCKED_SOURCE_RUNTIME_NOT_EXECUTED** on candidate
`31df3027a6e0903d8efa183dd3d4f964ebdf3949`, tree
`f947516fd455abf8e8d19aa9a51bd10000294e43`.
One blocking source finding remains. The reviewer created no worker and did not
launch the independent stable campaign. Root confirmed that the finding should
be delivered before author correction, without executing this deficient candidate.

The reviewed harness is the exact 694-line source from the author's stable
`2ba9b73c70b5502130ebd9ec60ca01a7829b79f8`, SHA-256
`e90e6365453b908df084e3fc4636d7e30d7da4c759250a09f07bf48f0d2ab599`.
The reviewer is distinct from B01 and changed only this new review directory.
Root separately owns the complete packet/manifest/provenance/claim audit.

## QH-WORKER-RUNTIME-01 — final eligibility can outlive its deadline

The accepted [brief](../../QH01/linux-decoder-boundary/brief.md) requires
monotonic expiry to make output ineligible; the
[experiment's wall case](../../QH01/linux-decoder-boundary/experiment.json)
requires delayed completion to remain ineligible. These requirements are
separate from the expressly unqualified hard return/kill/reap latency guarantee.

In [experiment.py](../../QH01/linux-worker-experiment/experiment.py), lines
441–443 sample the clock at the loop top. The controller then calls `raw_wait`
at line 454. Acquiring status at lines 468–473 and observing both stream EOFs
can immediately break the loop at lines 478–479. After actual descriptor/selector
settlement, line 599 decides eligibility from `reason`, input, session/policy,
output, status and ownership fields. It does not check the current clock.
The intervening `event()` timestamp calls only record time.

A concrete permitted schedule exposes the gap: both EOFs are already observed,
status is not yet acquired, and all other positive prerequisites hold. The loop
samples elapsed 7.999 seconds against the unchanged 8-second deadline. The
controller is descheduled across the deadline before `wait4`, resumes at 8.001,
acquires the child's actual status 0 and takes the completed-I/O break. Real
cleanup releases the owner, while `reason` remains null. The line 599 predicate
therefore admits the successful result after expiry and the case can report PASS.
No parameter change, invalid fixture, alternate worker or fabricated exit status
is needed for this control-flow counterexample.

The [source-bound witness](deadline-witness.json) records the exact preconditions,
line excerpts and transitions. This is a **static scheduling witness**, not an
executed delayed runtime trace. The original positive trace demonstrates the
relevant two-EOFs-before-status ordering, but took only 0.024933757 seconds;
it does not reproduce this failure. The original 22 author PASS observations
remain unchanged and are not relabelled as failed executions or reviewer results.

The author should check current monotonic eligibility at successful result
admission after the required status and I/O settlement. Expiry must invalidate
the result while preserving cleanup and quarantine semantics. A narrowly scoped
deterministic delayed-completion/settlement control should accompany the repair
under coordinator direction. Do not increase the 8-second budget, rewrite the
original 21 expectations or session amendment, or replace the framework.

## Inspected scope and retained evidence

The review read the complete trusted helper, controller, owner and 22-case
validator. It examined independent dimension/raw-cap preconditions, the explicit
plain-spawn/child-setsid route and parent's kernel identity checks, policy/G/image
ordering, finite AS/CPU helpers, bounded concurrent pipe I/O, abort phases,
acquired wait status, actual first-reaper/ECHILD handling, ownership settlement,
reuse/quarantine and teardown. This inspection does not substitute for the
independent runtime campaign that remains unexecuted.

[Source validation](source-validation.json) verifies the candidate and stable
harness identity, original frozen 21 expectations / 13 parameters/seven overlays,
the exact pre-code additive session amendment, admission/readmission hashes,
read-only R00 interpreter/available stdlib identities, direct environment map
and original public fixture hashes. The author's initial inherited SID/PGID
at spawn return remains distinct from later `last_kernel_identity` and the
kernel-session-established event. A function symbol or self-reported marker
is not credited as actual session establishment.

The original focused 01 optional spawn-flag refusal remains zero workers and
21 historical NOT_EXERCISED obligations. Its explicit readmission selected a
different source strategy before revised execution; no automatic fallback after
a kernel denial is accepted. The author's one stable 22-case campaign, its raw
files and significant earlier observations remain immutable on their own source.
No source, test, threshold, environment, app, graph, dependency or R00 file was
changed by this review. No installation, rebuild, CI/PR action or new corpus ran.

This review establishes no actual QR decoding, secret/key isolation, arbitrary
descendant containment, RSS/cumulative-allocation limit, logical decoder-work
budget, hard realtime, TypeScript integration, camera/ARM/Pi or physical result.
All 47 criteria and QH01/QP01/Q02 completion states remain unchanged. The next step
is coordinator-owned author correction and affected review before any independent
stable runtime acceptance or integration claim.
