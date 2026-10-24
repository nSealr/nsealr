# Bounded attention reporting correction

The f6 diagnostic could raise while writing, observing, serializing or printing
its attention report before reaching the ownership hold. Corrected source
`441a400da0981b31d4c953c10980d97d93a91ad8` wraps the two original reporting
statements separately in best-effort `BaseException` guards. Either report may
still succeed if the other fails. The original hold body, cleanup and all other
runtime methods remain unchanged; no new recovery, timeout or process killer
was added.

The six pure tests were frozen before the fix at
`2c4c9d397eda8316efcf6f43429dfee99f4d5463`. On that commit the invoker was byte-exact
f6/SHA07525e11…. Baseline Python3.12.15 ran
`test_attention_reporting.py AttentionReportingTests.test_write_failure -v`:
original RED exit1, OSError escaped, hold/poll/sleep iterations0 and child API
calls0. This is the reproduced harness defect, not a B3/product failure.

After the source fix, `test_attention_reporting.py -v` passed6/6, exit0: write,
print, both, observation, serialization and reporting BaseException failures.
Each fixture reached two unchanged hold iterations. A mocked ordinary polling
error on the first iteration was tolerated; the second reached the pump. After
GC, every snapshot retained the identical runtime, operation, Node-handle and
child fixture objects, including runtime.operation. Reporting exceptions could
not bypass that control flow.

**These are pure mocks, not processes.** Fixtures have synthetic nonnumeric PID
labels; creation APIs are prohibited and were called zero times. Only the mocked
fixture clock raises `HoldSentinel(BaseException)` after the second iteration.
No sentinel/test hook was added to B3 or production code. This proves scoped
control flow and object ownership, not actual cleanup, quarantine, recovery,
scheduling, indefinite liveness or survival of external process death.

`controls.tar.gz` retains13 original pure command/output/case members plus its
hash manifest (14 regular members). Commands record exact argv, source/test
hashes, clean before/after source and actual test exits. The raw RED was preserved
without relabeling; all GREEN expectations precede the fix. These dedicated
stdlib commands are separate from the normal Pi/full gate; no automatic CI
coverage or full-gate result is claimed.

`source-correspondence.json` compares actual f6/current ASTs: six other class
methods are identical; restoring only attention makes the entire module AST
identical. The original hold `while` AST and the original two reporting
statements are identical; only the two exception guards surround reporting.
Node child, historical inputs and all original proof files remain byte-exactf6.
The other28 tracked input bindings remain exact; only the invoker source binding
changes from07525e11… toafe76bc4…. The original `inputs.json`, README and artifact
manifest intentionally retain their historical715/f6 packet identity. This
affected packet binds the corrected source; the old positive does not qualify it.

No additional author O/W/Node positive, full gate or old39 run occurred. The
historical positive still contains13 raw files under positive-01 plus four outer
command/output receipts and its internal manifest (18 archive members).
The19-member preparation archive still binds five TS source inputs through its
receipts and retains ten compiler JS/declaration outputs plus the original
package context. No preparation,
worker, compiler or native C execution was repeated for this correction.

**STOP for distinct review and one reviewer-owned actual positive on the corrected
candidate.** No task acceptance, production/default route, camera, optical,
physical, key/signing, client/human timing or release claim follows from this fix.
