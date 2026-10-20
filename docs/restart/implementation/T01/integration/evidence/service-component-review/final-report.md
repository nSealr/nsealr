# T01 dispatch/service component — completed review

**REQUEST_CHANGES** on `104f5e369244dcdc3afe87bb91074067c6ad8ac7`, tree
`cea265276082e920d1b067e3d2ed7cca92ddc01e`. Reviewer `/root/h01_sol`,
`gpt-6.1-sol` xhigh; author `/root/a02_sol`. Three blocking findings remain in
this bounded component. The earlier confirmed-finding checkpoint
`fae35dd9a754cf1936cd7045435ff8bdbbf9284b` and its `report.md` stay historical;
this report completes the assigned perimeter without changing product.

## T01-SERVICE-01 — async dispatch skips client authorization

`packages/client/src/service.ts:928` directly invokes dispatch after service
request validation, bypassing `authorizeClient`, which the synchronous entry
uses. The async entry-point bytes are identical to adopted dbad: this is an
inherited current defect, not a24→104f regression. Existing client-permission
requirements still apply to the real path.

The [reproduction](reproduce-authorization.ts) runs actual
handleAsync→prepareSignerDispatch→service route dispatcher→SerialLineTransport→
recording port. Fixed public account/request/independent signed-response fixtures
and an exact valid local route/capability/limits/review-plan snapshot remove
compatibility ambiguity. For unpaired, revoked, expired and wrong-operation
clients, sync returns the exact `unauthorized_client` reason with zero
opens/writes. Async returns success after one open/write/close for every denied
context. The authorized positive also succeeds. The [paired output](authorization.stdout.log)
records all five cases. Restore permission checks for async dispatch before
adapter/port use and preserve each denied/no-write and authorized positive.

## T01-SERVICE-02 — actual response can exceed effective frame capacity

Planning in `assessSignerCompatibility` checks the known positive response, but
`checkDispatchResponseCapacity` at service.ts:1182 checks only JSON/reassembly
bytes. The driver at drivers.ts:236 passes a work ceiling without the effective
frame ceiling, and SerialLineTransport's `accountWork` at transport.ts:532
checks only the global1024-byte frame ceiling. A valid response larger than the
intersected frame limit can therefore be accepted.

The first [capacity/lifecycle reproduction](reproduce-capacity-lifecycle.ts)
uses an authorized get-public-key request, valid snapshot and actual driver/
serial transport with recording-only I/O. The known positive fits exactly the
effective226-byte frame cap. A schema-valid error response has296 JSON bytes
(within704) but431 encoded frame bytes. The service accepts it as a successful
exchange after one operation write. This is an accepted over-cap response, not
a claim that a peer's unknown response can be predicted before sending.
Enforce the effective encoded-frame ceiling on actual responses, preserving
pre-write positive planning, work/JSON/reassembly bounds and fail-closed cleanup.
Do not increase limits to accommodate this input. Add a regression using the
real narrowed-limit service/driver path, not only `assessSignerCompatibility`.

## T01-SERVICE-03 — stale sync Promise path can emit unhandled rejection

At service.ts:1200 a Promise is wrapped by `trackPending`, then `checkCurrent`
can throw. The catch returns at1204 and skips the only rejection handler attached
after the try/finally at1210. A later adapter rejection becomes an unhandled
rejection even though the caller already received a deterministic failure.
This error path traverses the new104f pending-wrapper behavior.

The second [paired reproduction](capacity-lifecycle.stdout.log) uses an authorized
sync call with a Promise-returning recording adapter that changes the local
connection generation inline. The current-state check correctly fails and the
write hook is revoked with zero writes. Rejecting that existing Promise later
emits an actual `unhandledRejection` carrying the fixed public test error.
A temporary observer records the event; without it Node's default rejection
policy can terminate the service. Attach rejection handling for every exit from
this sync Promise branch, while immediately revoking write hooks/abort and
retaining the finite reservation until actual settlement. Preserve normal sync
and async positives and the existing unsettled-slot refusal/recovery controls.

## Completed source/evidence scope

I read the actual service preparation/dispatch/response path and its changes
from dbad, the relevant24→104f delta, profile-dispatch and service tests, context
provider injection, driver open/write/close path and tests, and serial capacity,
work/deadline/abort/failed-connection hooks and relevant tests. The normative
profile/signing/limit notes remain the source for required behavior; reported
metadata and a local review-plan observation are diagnostic consistency/capacity
inputs. No host acknowledgement, page count or matching report grants device
consent or signing authority. The host-ack rejection, exact account/profile/
implementation/custody/method/catalog/algorithm/codec/limits intersections and
response identity/signature checks remain present in this read perimeter.

The implementation reserves a finite context slot before dispatch. Timeout and
the incompatible sync-Promise API revoke the operation/abort immediately while
an unresolved adapter holds its slot until settlement; settled failures release
it without creating a retry queue. The current hook rechecks the local clock,
selected account/route, fresh observations, connection generation and complete
plan/context/geometry snapshot before the driver writes. Absolute expiry,
rollback, absent observations, stale plans and normal flood/refusal/recovery
controls are exercised by the existing tests. These source conclusions do not
excuse the authorization, actual-frame and rejection-handler findings above.

The [bindings](source-bindings.json) verify22 primary source/input objects,
all15 declared author command receipts and their raw log hashes, the three fixed
independent operation inputs, the eight current source hashes against the
scope JSON, and unchanged artifact subtree24→104f. The13±1 dimension checks use
fixed source requests/responses, retained canonical bytes and standard UTF8/
Base64URL lengths, rather than production-output-derived expected answers.
The author RED/GREEN failures remain intact. Their actual24+dirty-diff command
identities are preserved, not renamed as clean104f executions.

The [reviewer focused run](focused-component-tests.command.json) executes only
the four assigned test files on exact104f source bytes: **81 tests PASS**.
These passing tests omit the three reproduced paths and do not establish
component acceptance. Original meaningful failures are not removed. The first
authorization probe's unsupported synthetic path was correctly refused by the
existing parser; that setup error and exact source remain separately preserved.
The corrected spelling still uses only a recording opener, never a real port.

No product was edited, no new gate/task/source research was introduced and no
broad CI/full T01, all42/all170+3, metadata-schema/parser, Pi, provenance, artifact
pin, hardware or physical/release qualification was performed. Root's separate
artifact/account-schema findings are outside this review. A02 owns corrections;
review their affected delta after a stable checkpoint, reusing unchanged source
and evidence. Final pin, full stable gates, protected delivery and actual-main
verification remain root-owned.

The full staged whitespace observation exits2 on preserved raw patch context
spaces and the raw Vitest final blank line; non-log/non-patch review proof exits0.
[whitespace.json](whitespace.json) retains both outputs without altering logs,
patches, product or an acceptance requirement.
