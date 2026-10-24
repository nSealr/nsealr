# QH01 Bridge/Python RGB composition: oracle checkpoint

Owner `/root/sdk_dependency_probe`, Sol6.1 xhigh. **SPEC ONLY, pending root
admission; no integration implementation or runtime result.** Input actual main
`da8c06aa30a460c1849a1f96f62862259640bf19`, tree
`1bc21a2c2c5cb99a9a1b7efd04a92d81e333a895`; its hosted CI is root-owned and
not asserted here. The existing manual-port brief and all five QH01 criteria
remain unchanged. Implementation28 is frozen and was only read.

The finite gap is composition: `manual-qr.test.ts:60–63` records a presented
string and supplies a scanned fixture. It does not pass that request through
the real Python RGB consumer. One opt-in host test can check this seam without
binding a camera/display/provider or enabling a route by default.

## Exact original inputs and pure result

All paths below are relative to the input tree. `P` denotes
`protocols/contracts/v1/`; `N` denotes
`docs/restart/implementation/QH01/native-qr-probe/`.

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `P/examples/request-kind-1-basic.json` | 252 | `f569e5b2f5bc0a3aa8586cba4b8afdeb96a0b93353e8d44212897fbc388c8377` |
| `P/vectors/transports/qr-envelope-kind-1-basic.json` | 940 | `4ae614411f237f59dc9dd2b8e4f9aef9f227265bc2bf4ecd5207b4dff79beb35` |
| `N/execution-01/request-kind-1-basic.rgb` | 172800 | `64d9be602c821c31c0dfd6e952199a328325acdbf9a7e1b3494921942a11055f` |
| `N/expected/request-kind-1-basic.envelope` | 259 | `88a16190a1b1ed033fc9bebe5452af70e9a9783fd6b92305add2ac7134039ff7` |
| `P/examples/response-kind-1-basic.json` | 540 | `3a398947e46c715a6ceaaeaa7198455ac840727c7f0f78dd079a1de8742350a1` |
| `N/expected/response-kind-1-basic.envelope` | 611 | `f27dbe54785a9510e43f05d27dbb67c488c77def150e0110d51264762cdeec1b` |
| `P/examples/response-get-public-key.json` | 169 | `ec333e4ec4cea4b889d12fd6b927870cc7096d5f553685584fd91f866c97190c` |

The existing manual test loads these original request/response JSON files and
uses compact `JSON.stringify` plus unpadded base64url (`manual-qr.test.ts:21–25`).
The permitted pure command confirms request JSON188 -> frame259 and response
JSON452 -> frame611, byte-exact with the two original expected envelopes and
historical `N/execution-01/{request,response}-kind-1-basic.decoded`. Existing
`encodeQrEnvelope` agrees. No fixture was changed or image generated/decoded.
The RGB-to259 association reuses the source-bound historical proof and B3
results; it was not re-executed for this oracle checkpoint.

Both objects have request ID `req-kind-1-basic`. The original signed event has
public key `4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa`
(also the separate public-key response fixture) and ID
`2977f107ad2668dbd9f09b8594eff3b5276e21bfe098e60ae3e905e3c861e4d3`.

The pure command invokes existing `handleLocalServiceRequestAsync` with the
same admitted `dispatch_signer_request` shape, grant/account/compatibility
fixtures and a dispatcher returning only the existing public response. This
reaches `packages/client/src/service.ts:935–972,1167–1183`, including the selected
route key; the standalone `verify_signer_response` operation does not take an
expected-route-key parameter and is insufficient for that check. The existing
core verifier (`packages/core/src/nostr.ts:84–107`) checks request ID, template,
canonical NIP-01 ID and Schnorr signature. No new crypto verifier or signing is
used. Positive PASS; five independent in-memory mutations of request ID,
template, canonical ID, signature and selected route public key all return
`invalid_signer_response`. Original fixtures remain byte-exact.

Preflight confirmed baseline Node24.22.0, pnpm10.33.4 and Python3.12.15, existing
module exports, and clean implementation28. The command reused its already
built `packages/{client,core,policy,protocol,qr}/dist` and node_modules; those five
tracked package source trees equal DA8. No install/build/fetch or O/W/C occurred.
Local raw command/stdout/stderr/receipt are retained under
`/goal/qh01-python-rgb-composition-oracle-2026-10-24/`. Invocation was baseline
`node --input-type=module`, stdin `oracle-command.mjs`, cwd the frozen28 worktree,
`QH01_SOURCE_ROOT` this worktree and `QH01_SOURCE_COMMIT` DA8. Exit0; elapsed
0.077180543s is command bookkeeping, not a client/decoder latency guarantee.
Command-source SHA256 `a8e38050e6ba562401509a383f1da6dff33d646a2653f8eb08a232bdab5597b9`;
stdout SHA256 `fabdd2039427bf70709e3a286dc44d9d099f834347116f727479045bc61f9f59`;
stderr is empty. The command used synthetic client monotonic time0.

Source correspondence: the entire `apps/bridge/service` Git subtree is
`de11840ac496f48867bcce67328485658685843e` on both8f andDA8.
B3 `apps/pi/app/nsealr_vault/qr_owner_adapter.py` is24312bytes, SHA256
`da6f36c966e2b27407e1025456d1f72c6d061d9463eb9ad25af85f594bf5a203`, byte-exact
with28; its rewritten assembly commit is `44454976e18329e1398f46a3196b084488d3c6ee`.
Client verifier source is52924bytes/SHA256
`d230d65ec2eb505afd940951c792c6ed0ac93a13e781ca70116db464ff59c509`;
core verifier source is3364bytes/SHA256
`f95f8a86053d612cb5f0ae460f7c2654322a841646780576cc09f240a9a86bdd`.

## Proposed single integration test, before implementation

Use `runServiceOnceAsync` with an explicitly injected context containing the
existing `createManualQrRouteDispatcher` and one trusted **test-only** port.
`present` checks currentness and exact original259 request bytes, then hands the
unchanged frozen RGB240x240, packed RGB888/stride720, to B3 with an explicit
pre-request worker path and actual build SHA. After real ready/phase/G, require
actual O/W collection, all EOF, closed owned FDs, and B3's single-use released
raw259 bytes plus parsed request equality. No reserialization may replace the
raw comparison. `scan` then returns original response611; the actual client must
accept it with the independently selected fixture key. Record exact presented,
decoded and scanned hashes, child IDs/statuses and actual service result.
The response611 is a scanner string, **never input to the worker512 cap**.

The test's top-level Python invoker must own and strongly retain B3's runtime
and operation; the Bridge Node test process is its child, not the Python owner's
supervisor. A Node/client refusal must still drive Python cancellation/polling
to actual known collection and only then close/reuse. If cleanup is unknown,
keep the Python invoker/runtime/exact execution handle alive and reserved,
report the condition, and stop acceptance: no timeout-kill of Python/O, abandoned
child, destructor assurance or replacement. This is a proposed local test
ownership rule, not implemented proof; bounded test IPC, failure-finally handling
and clock pumping require root admission before code, not a new product guardian.

Use the existing test timer facilities and injected monotonic clock explicitly
for this composition test; advance them only by the declared test steps. Keep
the client100ms boundary unchanged and label its clock synthetic. O8s/shared
cleanup4s remain actual monotonic clocks; native C5000ms is not exercised.
This gives no human-review, real-client latency, signing, camera/display,
ARM/Pi/physical or production-provider result. No old39 replay, new framing
decision, limit/default/acceptance/task-graph change is proposed. STOP for root
admission of the test-only implementation.

## Root admission — 24 October 2026

ADMITTED: freeze a minimal test-only composition harness, then ONE real positive
before completing the component or running full gates. Root read the complete
brief and original66-line pure command, verified all seven original byte/hash
bindings and exact command/stdout receipts. Actual mainDA8 is now accepted after
protected PR48, both original PR/main captures and a fresh main-only check.

Python is the top-level owner of both its retained B3 operation and one Bridge
Node child. Use a fixed trusted child script and bounded fixture-only IPC; frame
data cannot select commands, worker configuration or keys. Freeze wire shapes,
byte/record limits and failure/finally behavior before the first spawn. Reuse
the existing explicit worker producer/binding and test helpers where sufficient.
Do not create a general coordinator, provider or new runtime dependency.

The monotonicNow hook alone does not replace the actual setTimeout in the client
deadline wrapper. Confirm the real timer interface first. Prefer the installed
Node test timer facilities, with a tiny pure preflight and primary documentation,
isolated to the Node child. Preserve and record the100ms argument and synthetic
clock progression; do not change shared client code/defaults or claim actual
client/human latency. Python/O8s and cleanup4s remain real; C5000 is untouched.
If the timer or bounded-ownership design cannot be established, report that
exact missing property before execution rather than guessing an API.

The early result must bind actual presented259, decoded259, scanned611 and the
verified service response; actual O/W and Node collection/EOF must precede
successful teardown. Refusal does not abandon a live owner. Unknown cleanup
retains the owning invoker and exact handles and blocks acceptance/reuse; no
Python/O timeout-killer, implicit recovery or destructor guarantee is admitted.
Return the frozen source/command/result and STOP at that early checkpoint.
No old39 replay, broad full-gate run or physical/default-provider qualification
is admitted by this first positive checkpoint. General Rust rewrites stay deferred.

## First implementation freeze — before code or composition spawn

Owner retains root admission `d72b0f1d25823d461c576448d39064557336bee7`.
The installed Node24.22.0 pure timer preflight passed: `mock.timers.enable({
apis: ['setTimeout'] })`, a100ms timer does not fire at99, fires at100, and a
cleared second timer stays inactive; reset succeeds. The official
[Node24 test-runner documentation](https://nodejs.org/docs/latest-v24.x/api/test.html#timersenableenableoptions)
currently identifies24.22.1; the versioned24.22.0 documentation URL was
inaccessible to the web reader. API availability is grounded in the actual
installed24.22.0 preflight and its bundled mock-timers source SHA256
`06b114f37a3104e66a991de1c583a10df6fb12c2923cf21e01303fe8d1a2457b`, not an
assumed version upgrade. No O/W/C or product integration ran in that preflight.

Freeze one fixed Node child script and one Python parent invoker under the
adjacent `python-rgb-composition/` prefix. Reuse implementation28's already
qualified explicit W path/SHA and built JS modules only after checking their
source inputs equal this checkout; no build/install is needed for this first run.
The parent takes those trusted local paths before any request, never from IPC.

Fixture-only ASCII JSON/LF IPC is v1, canonical compact objects with exact keys:
Node stdout `present(frame259,timer_args[100],clock99)`, `scan(frame611)`, `close`,
then `result(native_response_base64,timer evidence)`; at most4successful records.
An error record may terminate a prefix, never count as success. Parent stdin to
Node is exactly one `decoded(frame259)` record then EOF. Each record has `v` and
`event` first. Exact ordered key suffixes are `present:[frame,timer_args,clock]`,
`scan:[frame]`, `close:[]`, `result:[native_response_base64,timer_args,clear_calls,
deadline_fires,clock_steps]`, `error:[name,message]`, `decoded:[frame]`; v is1,
events are those literal strings and error strings are capped at256characters.
Node output caps are2048bytes/record including LF,4096bytes total,
and4096stderr bytes; parent reply cap512bytes including LF. Parsing rejects
extra/duplicate keys, noncanonical input, wrong order/shape/fixture bytes, excess
records and partial EOF. Caps are checked during reads, before parsing. Pipe
data selects no paths, programs, keys or worker options.

Only Node's setTimeout/associated clearTimeout are mocked. A transparent child
observer records the actual unchanged client's100ms argument and actual clear;
after that timer exists, tick99 and set the injected monotonic clock to99 before
emitting present. Keep that synthetic time fixed during real Python/O/W work.
After validated service completion and timer clear, tick1 to100 and require no
deadline callback. No synthetic ticks affect O's actual8s/shared4s clocks.

Python owns its runtime/op and Node Popen handle throughout a try/finally. On
present, open B3, bind real ready/phase/live W ELF, send G, drive actual settlement,
require O/W statuses0, all EOF and no owned FDs, then take and compare raw259 and
parsed original request before sending decoded. Node scan uses only response611,
the real manual dispatcher/client/native-message functions and selected fixture
public key. Record exact IPC, actual statuses/ELF/FDs/EOF and native response.
Final success requires Node wait4(raw0), stdout/stderr EOF and all parent pipe
closure in addition to B3's known collection. Keep parent liveFDs unchanged.

Any assertion, malformed/partial IPC, Node failure or refusal enters the same
finally: invalidate/cancel active B3 and continue polling/draining owned handles
until actual collection; successful settlement permits explicit close. Never
kill Python/O or assume a failed assertion released children. A20s observation
expiry or quarantine reports exact handles and retains the live parent/runtime
without returning success/reuse; it is not a second cleanup deadline or recovery.
Node refusal never controls the parent's lifetime. This is one fixed diagnostic
test, not a general supervisor; unhandled external process death has no guarantee.
Freeze source/inputs clean before ONE actual positive; preserve any RED and STOP
at the first result before full gates or extension.

### Exact preparation dependency found before implementation

The reusable library dist files and W3c92 exist and their source inputs equal
DA8, but Bridge service has no prebuilt `dist/index.js` or `dist/manual-qr.js`.
Its actual package script uses `node --no-warnings --import tsx/esm src/index.ts`.
Installed tsx4.21.0 uses esbuild0.27.7; the latter's `lib/main.js:2268–2311`
spawns/unrefs a service child, while `stopService` destroys pipes and kills it
without exposing joined terminal proof. The ESM loader can run in a worker;
a main-thread observer would not establish that child status. No TSX loader,
composition Node/O/W or implementation source was started on that assumption.

Required narrow preparation decision: admit ONE isolated Bridge JS emission with
the already pinned TypeScript6.0.3 and the existing
`tools/bridge/build_packages.mjs:43–77` compiler recipe, applied only to the five
non-test Bridge source files, with generated output and hashes outside tracked
source and implementation28 left read-only. This needs no new dependency,
esbuild process, W/C build or per-test compilation. A suitable prebuilt Bridge
artifact with an exact source binding would also satisfy the missing input, but
none was found in the inspected reusable worktree. Until that preparation is
admitted, STOP before code or the first positive; the timer preflight is PASS,
not a composition result. The preflight path lookup failure is an absent build
artifact, not a product failure.
