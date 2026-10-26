# PR57 setup callback phase regression

PR57 source ae77f2e7 failed root-observed CI run40400388223 with one test failure,
854 passes and one skip. The old100ms test required its ready callback to have
received abort, but the same setup budget includes child startup and OPEN.
The CI log records aborted=false; without a callback-entry marker it does not
prove whether ready had never entered or could have entered with an already
aborted signal. No hardware failure is inferred.

The deterministic retained RED withholds only the test relay's OPEN header and
advances the100ms setup scheduler before callback entry. The original aborted
assertion fails with the same false/true result. Production source is unchanged;
this reproduces the invalid test assumption, not a new product abort defect.
The complete original CI log remains preserved privately; the exact relevant
line slice and its original byte/line provenance are archived here.

The corrected original case waits for readyEntered after real child OPEN and
abort-listener installation. It requires readyCalls=1, signal not aborted at
entry, then advances the existing100ms setup timer and still requires abortion,
0 signer requests and no output file. Dispatch rejection is awaited through
actual child/pipe/stream collection. A separate pre-OPEN expiry case explicitly
requires readyCalls=0,0 requests and no file; it does not demand an abort event
from a callback that never started.

Only setTimeout/clearTimeout are controlled in those two test cases. Date,
performance, hrtime, the actual child process and its clocks, Unix socket I/O,
grants, pin and production request/ACTIVE budgets remain real and unchanged.
finally awaits cleanup and restores the scheduler. No100ms increase or new
product hook, deadline, route, protocol or fallback was introduced.

Four focused setup/EOF/settlement cases pass. One complete18-case file run
checks scheduler lifecycle against the subsequent real EOF50ms and operation
timeout80ms cases, and retains the existing >5s real external-wait observation.
This one-file run is justified by the shared timer API restoration; no full
local CI, unrelated typecheck/API, build, oracle or hardware suite was run.

The default operator callback already checks signal.aborted before installing
stdin handlers. The wrapper's awaitOPEN can in principle continue to an already
aborted callback during another scheduling order; the old CI boolean alone
does not establish that order. No stray signer operation was demonstrated and
no product edit is included. The withheld-OPEN test establishes only its stated
finite ordering, not a universal proof against every future callback race.

All historical CI/source/review/physical records stay unchanged. This test/proof
delta requires distinct review and root's normal PR57 push/new-head CI; it does
not rerun the failed head or close a product criterion. Archived test inputs and
logs are losslessly compressed to preserve their bytes without adding runnable
duplicate test files. Original execution paths are provenance, not entrypoints.
