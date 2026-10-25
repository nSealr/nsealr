# First Pi public-fixture workflow: source checkpoint

2026-10-25; author `/root/sdk_dependency_probe`; source-only proposal, pending
distinct admission. Base `24621023f0c5d181ba41f1a2679a7608e2cdd20a`, tree
`5e983fe208858665df97071aa6765a4a625df15c`. No implementation, import of product
code, build, application/test execution, device access or hosted-CI observation.
[source-proof.json](source-proof.json) binds the inspected files and private
context without publishing the private handoff. PR51 qualification belongs to root.

The reported kit is Zero1.3 non-W, Waveshare1.3 HAT240×240/joystick/three keys,
OV5647-compatible camera and3D case. SKU14972/ST7789 is the reference description;
received markings/revision, camera/cable variant, image, operator/access and driver
stack remain unverified. The separate identification session owns those facts.
This proposes disposable **public-fixture** feasibility, never custody/production
or SeedSigner compatibility. All47 contracts/statuses, frozen1508, P01/T01 and five
release paths remain unchanged. [physical-probe.md](../physical-probe.md) gates
identification, image/channels, optical/display/input and persistence separately.

## Actual call graph and reusable boundaries

Paths below are repository-relative; line ranges are bound in the source proof.

| Existing source | Actual behavior and reuse |
| --- | --- |
| `apps/pi/app/nsealr_vault/cli.py:334–354,467–524`; `hardware_flow.py:178–240` | `flow` constructs file adapters, Python review and Python `sign_request`. Neither CLI nor hardware flow calls the Rust engine/RGB owner. Keep as an independent reference; do not wire a physical approve boolean through this signer. |
| `seed_signer_hardware.py:315–378,568–572` | Default factory creates `PiCameraJpegFrameSource` at480×480/24fps, `picamera.capture(format="jpeg")`, then Pillow/Pyzbar. It is not raw240 acquisition or the bounded Rust decoder. Reuse injectable capture ownership/explicit `close`, not JPEG/Pyzbar as a substitute for O/W. |
| `qr_owner_adapter.py:102–157,173–251,450–518`; `apps/pi/qr-worker/src/main.rs:45–105` | Trusted pre-request W path/SHA → explicit `RgbOwnerRuntime.reserve` → `open`, exact readiness, `start(bytes)`, poll verified phase, `acknowledge`, full settlement → one `take_result()` returning original bytes/parsed object → known `close`. O owns W; top Python owns O. G admits decoding, never human consent. Keep this boundary unchanged. |
| `engine_adapter.py:47–138`; `crates/nsealr-pi-engine-fixture/src/lib.rs:181–298,322–340` | SHA-checked source-matched cdylib, synchronous `run_request_frame(raw,local_io,clock,aux,cancel)`. Rust parses raw input, constructs fresh public11×32-key owner, emits full32×8-cell inspection, consumes one-use approval and privately stages the response. Callback exceptions refuse; callback blocking is not interruptible in process. |
| `seed_signer_hardware.py:140–197,381–470,560–595` | Configurable GPIO, Pillow framebuffer/draw target and review-display factories exist. `present_image(image)` must be injected: there is no SPI panel initialization/presenter here. GPIO uses BOARD pull-ups/LOW; reference next37/scroll35/approve33/reject40, reject precedence and release waiting. These are source values, not verified sample wiring. Factories inherit unbounded waits; constructor/review calls expose finite poll bounds. |
| `seed_signer_hardware.py:473–536,539–558,589–595` | Existing response display + Python QR matrix renderer accept an envelope, fit the matrix/quiet zone and call the same presenter. Reuse for exact Rust response bytes decoded as ASCII, without re-encoding/signing. Static/multipart optical reliability and actual font/rotation still need measurement. |
| `docs/restart/implementation/QP01/request-engine/exchange.py:279–313`; `native-leaf.ts:18–113` | Current C-leaf loads the library before R+EOF, reads raw once, records all pages but returns Next/Approve automatically, zero aux and cancel=false. `prepareNative` owns that one C, real5000ms watchdog, capped stdout and actual code/signal/stdio-close. It exposes no injectable physical callback/factory today. |
| `docs/restart/implementation/QH01/manual-port/python-rgb-composition/{run-composition.py:225–237,335–349,bridge-child.mjs:220–263}` | Reviewed host composition retains Python runtime/op/Node; after actual B3 settlement it sends raw259 to the one guarded C, then supplies C-produced611 to an in-memory scanner/client verifier. There is no physical camera, physical callback or optical return in that proof. Reuse ownership/settlement logic, not synthetic scanner/consent as device evidence. |

## Minimum missing code, with one recommended next artifact

Recommend one opt-in **Rust-presentation-to-local-IO fixture adapter** first,
using the existing `EngineAdapter.local_io(Presentation)` boundary. It must draw
the exact Rust `label/body/position` plus index/total and accept only a fresh local
event for that presentation. Reuse Pillow draw primitives and injected presenter/
GPIO, not `screen_review_for_request`, detached approval digests or Python signing.
The existing review-display frame shape differs; its title/body scales and
`_clip_text_for_width` can truncate (`st7789_layout.py:50–85`, hardware:419–426,
692–697). Require complete fit or refusal, never silently clip a Rust fragment.
Bind Next→0, Approve→1 only at separate decision, Reject→2; Back→3/None→4 only
from explicitly defined local events. Existing `scroll` is not implicitly Back.
Reject/display/input failure must not acknowledge; stale/held/ambiguous input
cannot become a fresh approval. Core `authorization.rs:453–487,618–675` owns
page coverage, request/key/context binding and consume-before-provider behavior.

The device chain has these further gaps; none is admitted for implementation:

1. An image-specific camera source producing exactly240×240 packed RGB888,
   top-to-bottom rows, RGB byte order, stride720,172800B. No JPEG/header/padding;
   any crop/resize/rotation/colour conversion must be explicit and source-bound.
   Choose its API only after effective OS/camera stack is known; current scanner
   cannot be passed directly to `start`. Do not move unbounded native decode upstream.
2. The actual ST7789 SPI presenter and verified GPIO profile, with finite read/
   release fault behavior and explicit camera/display/GPIO resource close evidence.
   Camera `close` exists; panel/GPIO teardown is not supplied by these protocols.
3. The opt-in capture→B3→raw→engine→local UI→QR runner/callback binding does
   not exist. The current fixed C entry autoapproves; simply installing physical
   callbacks there puts human waiting inside C5000. That is **not a human-workflow
   solution**. Preserve Python's owning runtime/exact handles and the existing
   C owner; no direct-CDLL bypass, new coordinator or changed spawn capability is
   admitted. Trusted library/W/configuration must be fixed before RGB/request;
   existing C initialization/readiness follows actual B3 settlement.

## Clocks and blockers before a full human workflow

O8s admission and shared4s cleanup belong to decode, not page reading. Begin C
only after B3 settlement; its real5000ms starts at C spawn, including load/setup
and any blocking local callback. Timer attempts a C-only SIGKILL, then awaits
actual close; it is not a hard collection deadline. Do not kill/restart Python/O
or release/reuse unknown state. In-process cancellation is sampled between
callbacks and cannot interrupt a blocked display/GPIO call.

Core lifetime is100 trusted ticks; existing `MonotonicSeconds` gives whole host
seconds. It is distinct from C5000 and client100ms. The current host composition
mock advances client0/99/100 while preserving the real `setTimeout(100)` argument;
`packages/client/src/service.ts:1237–1253` uses a real timer in ordinary execution.
Neither mock clock nor logical monotonic input proves human/optical latency.
There is **no established human-review profile** for31 pages inside C5000 or a
live optical transaction inside client100ms. This is OPEN, not conditional PASS.
The missing requirement/decision separates bounded computational work from human
review time while verifiably retaining exact request, inspection catalog, identity,
currentness and Rust-owned one-use approval. The present synchronous ABI has no
suspend/resume review operation. A required future test must retain those bindings
across delayed local review, then refuse on cancellation/expiry/context change or
spent authority and never release a late response. Neither a Python bool nor
freezing the clock, extending/ignoring C5000 or the legacy flow supplies that proof.
Preserve all present budgets/tests; this checkpoint chooses no replacement timer/API.
An offline optical fixture/scan-back can measure feasibility without calling it
that transaction; it cannot silently become a timing waiver or custody route.

Other exact prerequisites: actual board/revision and effective image/kernel/libc/
Python ABI; ARMv6/float ABI, loader/sysroot and source-qualified W/cdylib; actual
Linux limits/FD/proc/session facilities; compatible camera capture, SPI/GPIO/Pillow/
QR packages and Node/helper runtime if that existing leaf owner is retained.
Pinned R00 is x86_64; historical ARM-target recognition is not an ARM build/run.
No actual image/driver/package choice or Node-on-this-Pi qualification follows.

## Smallest acceptance after separate admission

First test the local-IO adapter with injected draw/input and the real fixture
engine: full ordered31 Rust pages (30data+decision), all indexed bytes retained,
fresh event only after complete draw, one-use sign/reject/fault assertions. Label
draw/input synthetic; this is the **single next proposed experiment**, a host
render/action-binding prerequisite, not physical proof or human timing acceptance.
Freeze commands/inputs before execution; retain C5000 and fail closed if it expires.
It does not admit a physical callback mode or solve the open time-domain property.

On an identified kit, retain a finite disposable-fixture smoke with these outcomes:

| Case | Required observation |
| --- | --- |
| Startup | Exact image/tool/ELF/driver hashes, W/library initialized from trusted local inputs; camera/presenter/input readiness; no request/sign on setup/SHA failure. |
| Request | Actual captured raw geometry/bytes/hash → real O/W phase, wait/EOF/FD settlement → raw request equality/correlation; wrong shape, blank or malformed request releases no usable result. |
| Response | Complete actual Rust inspection + fresh physical decision → actual response611; panel displays it; independently identified client scans and verifies key/template/ID/signature/correlation. Record scan bytes and conditions, not an in-memory scanner as optics. |
| Reject | Fresh reject during review/final decision → ABI REJECTED(-5), no response bytes/QR, actual cleanup. No detached approve boolean or later retry using old authority. |
| Timeout | Decode wall, native watchdog/clock expiry, GPIO no-event/stuck-release and client deadline have separate sources/roles. Require refusal/no late release and actual known collection; combined human timing remains unqualified. |
| Cancel | Pre-G cancel uses existing O collection and zero W-image/release; post-decode review cancel uses ABI CANCELLED(-11), no signature/response release. Freeze actual callback/physical cancel binding before this test; old synthetic lifecycle proof is not that binding. |
| Close | Actual camera/presenter/GPIO close plus O/W/Node/C status/EOF/FD restoration where present. C reports code/signal/close, never invented raw wait. Unknown cleanup retains the same live owner/handles and poisons reuse; reporting cannot prevent retention. |

Reuse original public RGB SHA64d9…/request259 SHA88a1… as digital oracles only:
camera pixels will differ; require exact decoded request. With explicit zeroaux,
the existing Rust oracle is response611 SHA250167d1137f6da25676b00b62913a3d8f29391a1ff5331d64f7079d953f5ded,
public key4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa.
Do not substitute the legacy f27d response or generate new goldens/keys. W512,
JSON704/static947, parent reply512, Node record2048/stdout4096/stderr4096/max5,
O8/shared4/client100/C5000 remain distinct and unchanged. Do not duplicate old39.

Finish for this checkpoint: two source-only files committed/pushed, exact hashes
reported, STOP for distinct admission. No QP01/Q02/QH01 acceptance or physical
release closes; kit/image and the human clock/callback policy remain explicit gaps.
