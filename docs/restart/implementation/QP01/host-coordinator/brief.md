# Host image/request coordinator — pre-code contract

Source candidate: `5c701113bc2ac2d7b596f7d3fb76574a7cff24b3`, tree `866c12d4569f4ad18df4adb2f496c11818c666af`.
This is PR45 delivery source, not a claim of resulting-main adoption or code admission.
Root must reconcile the actual adopted source once before assigning implementation; no gate is waived here.
Deliver one fixture-only host coordinator connecting the existing supervised equal-channel RGB worker to the reviewed `EngineAdapter`.
It must sign the actual incoming request, present Rust-owned review through injected display/input, render the response and exercise the actual client.
The response-to-client leg is explicitly software-injected; no complete optical return611 or physical consent is claimed.
All47 task criteria/status/dependency/resource/release sets remain untouched; all QP01/QH01/Q02 criteria remain incomplete.

## Exact source facts and missing seam

The existing worker accepts240×240 RGB888/stride720/raw172800, waits for session/policy/G, requires equal channels, then uses rqrr `decode_to` with private512 staging.
It returns original QR-symbol bytes only after successful decoding; it has no key or JSON/signing API.
`rust-qr-worker/controller.py:13–24,28–42,238–255` imports the corpus/base experiment, reads expected files and judges expected outputs.
Its `supervise(case, owner, directory)` returns a test record, has no cancel input, and acquires before fallible file reads outside its cleanup region.
`linux-worker-experiment/experiment.py:24–39` also loads experiment expectations; importing that module does not provide a clean operational boundary.
Therefore neither harness is an application API; the old corpus is not a runtime dependency or an output oracle for the coordinator.
The precise missing implementation is one operational supervisor accepting explicit bytes/binary identity and proving cancellation/settlement before return.
Derive its mechanisms from the reviewed source, bind the correspondence in implementation evidence and keep both historical harnesses byte-identical.
There must be only one active supervision implementation for the new path, used by its coordinator and focused integration driver.
Do not create another pending/session engine, generic process framework or second active loop in the driver.

The current `engine_adapter.py:67–138` already accepts the original frame, owns buffers/callback lifetimes and enters the real Rust owner.
The current engineering exchange instead supplies synthetic Next/Approve (`request-engine/exchange.py:68–76`).
The older `hardware_flow.py:115–152` still decodes into Python review/signing; it must not be used or modified for this path.
The manual service already supplies before-presentation currentness, effective limits and abort, then verifies scanned response/currentness and cleanup.
Its route-store remains serial-only: this package adds no store entry, default wiring, advertised capability or availability promotion.

## Proposed finite API and output

Add `apps/pi/app/nsealr_vault/qr_worker.py` for the single operational supervisor and `host_coordinator.py` for orchestration.
The constructor takes explicit trusted worker path/SHA256 and an explicitly provisioned source-matched fixture `EngineAdapter`.
It also takes injected `render_review(Presentation)`, `read_action()`, `render_response(static_frame)`, monotonic clock, auxiliary and cancellation callbacks.
No key/import/owner handle, seed/session-source namespace, detached approval, selected page or diagnostic digest is accepted.
The API is synchronous: `run_request_image(rgb: bytes) -> bytes` returns the full original response frame only after its required operations settle.
Input is exactly172800 bytes with fixed240×240/RGB888/stride720; no file/JPEG parser, capture API, resize, palette or RGB conversion is added.
Callers own acquisition/allocation before this interface; this contract does not bound a camera or image-loader allocation.
The worker returns a bounded frame of at most512 bytes; pass those exact bytes to `EngineAdapter` without JSON/base64 roundtrip or request reconstruction.
There is no expected-response file or fixture-response lookup in the operational supervisor.
Publish a successful decode only for actual acquired exit0, settled IO, no overflow/error and a fresh final eligibility sample; partial decode stays private.
Blank/noQR, ambiguous detection, non-equal-channel input, decoder error and output overflow are distinct closed failures, with no engine invocation.

For each Rust `Presentation`, first pass all original label/body/position bytes and index/total to `render_review`; only after it settles call `read_action`.
Use the existing action meanings0Next/1Approve/2Reject/3Back/4None; invalid actions and callback exceptions fail closed.
There is no default approving UI, automatic traversal or reuse of Python `screen_review_for_request`/`ReviewControlSession`/`sign_request`.
Rust retains review cursor, complete traversal, consuming approval, fixture owner and raw-ID signing/completion checks.
The explicit identity remains public test-key-1, scalar11×32/public key4f35…71aa; this is not the old scalar3/f930 canary or a production provider.
Clock/aux callbacks preserve the reviewed fallible contract, exact32 bytes and no fallback; injected public aux fixtures prove no entropy quality.

After successful engine settlement, recheck cancellation before response presentation; decode only the ASCII frame to the renderer's existing text interface.
Reuse `SeedSignerSt7789ResponseQrDisplay`/`PythonQrcodeMatrixRenderer` with injected draw target and already-selected optional host prerequisites.
Preserve the returned frame bytes; the renderer must not reserialize JSON, choose multipart, change scale/ECC to pass, or supply authorization.
Record the actual renderer/callback source and host output; its successful return is trusted software settlement, not proof of screen visibility.
The injected Bridge port checks `control.before_present()` immediately before exposing its outbound request and honors existing limits/abort.
Its scan supplies the coordinator's exact response frame directly to the unchanged actual client verifier: label this leg software-injected in every result.
No descriptor, constructor, success boolean or source hash is evidence that physical resources were actually used or quiesced.

## Ownership, resource limits and cancellation

Reserve one coordinator owner before any external callback or fallible operation; every pre-spawn failure is inside a cleanup/finally path.
Validate bytes/relationships and trusted executable identity before spawn; failure with no child releases cleanly and invokes neither engine nor renderer.
The worker suboperation uses that owner; do not release the whole coordinator merely because the child exits while IO remains pending.
Preserve plain `os.posix_spawn`, trusted worker `setsid`, kernel SID==PID/PGID==PID and parent prlimit/readback before G or any image byte.
Only owned/verified PID targets may be signalled; never PID0/-1, the coordinator group, unknown/reused identities or arbitrary descendants.
Retain nonblocking bounded stdin/stdout/stderr, actual `os.wait4` acquisition and final monotonic admission after status/IO settlement.
Missing/stolen status cannot become success via a default return code; unknown status or uncertain cleanup quarantines and retains ownership.
Cancel must be implemented and tested as a cooperative input, not attributed to the old Rust corpus controller.
Pre-spawn cancellation creates zero child/control/image bytes; after spawn, stop input and terminate only the owned child, then acquire status and settle IO.
Deadline/cancel refusal alone is not cleanup; no fresh operation starts until real settlement is known, otherwise quarantine persists.
Once native engine execution starts, retain ownership until it actually returns; a blocked display/input/aux callback cannot be forcibly interrupted.
After cancellation, discard any late result; signing/provider effects may already have occurred and cannot be recalled.
Renderer failure may have partial display effects; do not report success or automatic safe retry if renderer quiescence is unknown.
Ordinary returned errors allow reuse only after all begun child/native/callback/render operations are settled; no automatic retry or cached approval.

Keep all13 worker baseline entries, not just the image dimensions: maximum width/height240, pixels57600, raw172800 and RGB888/3/stride720;
AS268435456 bytes, CPU soft1/hard2 seconds, wall eligibility8 seconds, cleanup observation4 seconds, stdout512/stderr512 and IO chunk4096.
These are fixed host experiment parameters, not hardware capacities; RLIMIT_CORE0 remains unchanged.
AS bounds virtual address space, not RSS/cumulative allocation; CPU seconds are not wall time, hard real time or logical parse_work.
Spawn/bootstrap and arbitrary trusted callback execution are not forcibly time-bounded; cleanup observation expiry is not proof of cessation.
Ordinary Linux processes/rlimits are not a sandbox protecting parent memory/files/secrets or controlling arbitrary compromised-worker descendants.
The worker8-second eligibility window and engine100-tick conformance lifetime are distinct; neither is a new whole-session/client deadline.
Client deadlines/currentness and pending ownership remain in the existing client/manual service, never replaced by this coordinator.

## Required independent cases and focused delivery proof

Freeze literal inputs, expected outputs, effects and intended failure layer before runtime edits; preserve genuine RED and corrections.
Use original13949 equal-channel assets and exact nonce-amended expectations, not output learned from a new encoder/decoder/native result.
- HC01: getkey image98 -> exact frame/identity response198; no review/provider, actual worker status/IO settled.
- HC02: real sign-request image259 -> every actual Rust review frame/action -> exact independent event/ID/signature response611 -> actual client acceptance.
- HC03: render that response611 with the existing renderer; direct software injection to the client is explicit, never described as a decoded response image.
- HC04: blank/noQR and original response611 image/512 overflow refuse before engine/render; zero partial public output, distinct statuses.
- HC05: raw length/format/relationship errors and wrong/missing executable/hash refuse at their intended pre-spawn boundary; zero child/engine/render effects.
- HC06: genuine non-equal-channel input refuses in the unchanged worker; do not claim this path accepts ordinary camera RGB or import the separate RGB922 experiment.
- HC07: cancel before spawn, during session/policy/input and after decode; prove the phase reached, no later engine/output and actual owned-child collection/IO settlement.
- HC08: wall/IO-overflow/unknown-status and failure before spawn preserve owner cleanup/quarantine; final eligibility is checked after status/IO, including controller delay.
- HC09: Reject, premature Approve, invalid action and display/input/clock/aux BaseException refuse; every shown byte precedes its corresponding action.
- HC10: cancellation during auxiliary/native completion refuses publication without asserting no backend effect; no retry authority survives.
- HC11: reentry from cancellation/presentation and a deliberately held callback refuse concurrent ownership until actual release; unknown native/render settlement quarantines.
- HC12: wrong response request/key/template/ID/signature reach the unchanged client's intended verifier; late/currentness failure cannot return a stale success.
Tests must assert counters, actual boundaries/status/IO/byte hashes and ordered presentation/effects, not names or prose presence.
Use controlled finite helpers only for otherwise unreachable supervisor error/status/held-IO paths; no new decoder, corpus or whole22 replay by default.
Add focused tests in `apps/pi/tests/test_qr_worker.py` and `test_host_coordinator.py`; do not rewrite historical tests/proofs or weaken negative inputs.
Default unit tests may inject explicit IO/process boundaries, but must not count those as actual rqrr/native/client execution.
The scoped host integration driver under this prefix must invoke the one operational supervisor, real pinned worker and real `EngineAdapter` for HC01–04/HC12.
Use existing verified worker source/lock and pinned local build closure; explicit path/SHA provisioning is a prerequisite, not a hidden fetch, fallback or default route.
No new registry dependency, library/backend selection, lock/vendor/policy/toolchain change or assumption of preinstalled worker is authorized by this brief.
If that exact provisioning is unavailable, report the missing input before dependent runs; never skip or fabricate a native result.
After focused checks, run the default full Pi CI and actual client exchange using the existing `request-engine/exchange.py --ci apps/pi` provisioning/order.
That existing command does not itself provision/exercise the new worker: preserve the separate real host-integration receipt and do not mislabel Pi unit coverage.
Preserve full setup/test/lint/audit/docs, Bridge prerequisite, all17 integration obligations, existing coverage floors/checkers and mandatory protected PR/resulting-main gates.
Reuse source-identical core/S03/K01/old corpus evidence explicitly; no blanket full suite rerun, audit feed fetch or hosted CI polling for this preparation.

## Units, remaining physical dependency and source bindings

Codec/engine input and response limit704 is JSON bytes; one static frame can require947 ASCII bytes. Worker512 bounds the entire decoded QR-symbol frame.
Original67/188/142/452 JSON bytes correspond to98/259/198/611 static frame bytes. The611 return remains outside this worker experiment.
This package changes none of512/704/947, framing, checksums, multipart support or effective manual-port accounting, and promises no complete optical loop.
Physical comparison and actual client/screen/camera timing still decide framing/decoder/profile; synthetic renderer output is not legibility evidence.
Exact kit/revision, SoC/userspace ABI/OS image, camera interface/pixel format, display/buttons, operator/access remain unidentified; root's question is already pending.
Before real deployment, those inputs and native target provisioning must be reconciled; no ARM/Pi/P4/no_std, real-key/provider/custody/release qualification follows.

All following paths are bound to source5c above; SHA256 values identify the actual reviewed mechanisms, not an execution on a future coordinator:
- `docs/restart/implementation/QH01/rust-qr-worker/controller.py` lines13–42,92–155,175–255: `81a1b8c2a607f6aa918a62af98c1d6a2e9ec110dce6a4f5c076b02255b1cc142`.
- `docs/restart/implementation/QH01/linux-worker-experiment/experiment.py` lines24–39,127–159,231–240: `97fa6da85a1f83c5535050f6c77c588800a069a26ed9a7cd7470f616352a76eb`.
- `docs/restart/implementation/QH01/rust-qr-worker/src/main.rs` lines9–12,38–100: `d4fb28a16316907abec5f3d20a79baf61ce70e67a4ff8858752d60534218fdde`.
- Worker `parameters.json` SHA256 `ef85f58625943dc831158700d9fbf7df342eef1eb79e51e11398c285b73db52f`; existing `Cargo.lock` SHA256 `eb00e1c6ebaa1e241e64574a62902a7ede995c7582cf11bc9d4620bfb4baf243` in that same subtree.
- `apps/pi/app/nsealr_vault/engine_adapter.py` lines47–138: `c7d7778e538dc787e328295c67f9702473b87cb7c35d7576d37eab06a51137c7`.
- `apps/pi/app/nsealr_vault/seed_signer_hardware.py` lines323–375,473–557: `c9d2fb3f4c5b17d1e12083b759bed02e22d2676e04041edba15dbb02c64001d3`.
- `apps/bridge/service/src/manual-qr.ts` lines57–171: `d2c9aa73f723739a5682f0a2a4b6c88f4b319a70d879766fe7b8f862ee5e82f9`.
- `docs/restart/implementation/QP01/request-engine/exchange.py` lines16–87: `a6a8aa3e908401727fe83fa5ec42dee09e5dd7e58164a0ce3eea1541d907029c`.
- Its `client-exchange.ts` lines28–65,68–169: `dc59a9189a245f8b45961e3bb1e1d6f349396989db37acd9053d89f4df0b9456`.
Reuse immutable worker5fa/A02 independent build review, corrected supervisor06d reviews, request-engine review025b and root delivery review0aa88190 in their original roles.
The actual API, cancellation and new coordinator correspondence still require implementation, measured focused evidence and distinct review; no current harness supplies those guarantees by declaration.
