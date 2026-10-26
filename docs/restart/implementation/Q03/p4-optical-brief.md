# P4 public-identity optical vertical slice

Author `/root/phase1_scope`; distinct reviewer/operator/integration owner `/root`.
Parent scope QP02/Q03; no task-state update in this worktree. This is an actual
P4 engineering binary with a conspicuous PUBLIC TEST IDENTITY banner, never a
qualified custody/entropy/release artifact.

## Inputs and owned boundary

Product19ab15d15aa8751174aa87119ae18853007c8222 supplies the unchanged no_std
`crates/nsealr-core`. New narrow consumer lives in `apps/p4`; its Rust staticlib
uses that crate through a relative path, no copied semantic engine, std fixture,
catch_unwind or host-supplied approval. Camera adapter provenance is vendor
870588e62daaf723f3c52f0060d8dc053665ed30 plus the reviewed peripheral candidate
9acf6a074fc8d8ecad27927281fbfe78cbfef8b9. Reuse the existing IDF6.0.2/rev3_x,
BSP2.0.2, pinned27 components, corrected LVGL adapter, toolchain/venv/cache.
The later physically observed peripheral reference is2aaf2d0b62183886cd6bb39dc5b730b457be1fd5:
PPA rotation0/mirror0/0 gave the maintainer's asymmetric marker1 2 /3 4 readable,
centered and stable. This author did not replay that observation. The app's
former83f grayscale180 assumption is superseded by raw-coordinate preservation;
no physical raw parity is inferred from the peripheral screen.

Pixel decoding alone uses dlbeer/quirc927d680904dc95fdff4cd9d022eb374b438ff8f2.
The actual source/header notices grant ISC permission; retain them and hashes.
Only required library sources are imported, no printing vendor scanner/demo.
LVGL9.6 public APIs supply fixed-cell text and response QR rendering.

## Observable contract and bounds

Exactly800x800 RGB565 camera frames, length1280000, before reading pixels.
One preallocated640000-byte grayscale image, with bounded quirc tables/flood
workspace; no hostile resize/allocation. Exactly one detected QR is required:
zero waits, multiple rejects, failed decode rejects. Only a primary
QUIRC_ERROR_DATA_ECC permits exactly one quirc_flip plus second decode on the
same extracted grid, as the upstream README specifies for mirrored QR. No image
retry, resize, larger version or additional engine; non-ECC/prefix/schema failures
have no retry. Both attempts stay inside the same uncollected work/WDT interval.
Payload must be at most947
bytes and static `nsealr1:`; animated frames, nsec/seed import and malformed UTF8,
base64/trailing bits/schema reject before review. Shared core validates signing
payloadv2, canonical event, supported catalog and identity. Initial local caps:
JSON704, content128, tags4, fields/tag4, field64, aggregate text384, canonical2048,
review64 pages; request-id at most32. No claim these are final product capacities.

The single Rust owner keeps the public fixture scalar11x32 (derived4f35...) in
internal DRAM; deterministic fixture-only auxiliary bytes are explicitly labelled,
fallible at the boundary and never an entropy claim. All engine/crypto execution
uses an internal task stack. Camera/decoder/public QR buffers may use PSRAM.
Rust1.95.0 riscv32imafc-unknown-none-elf and IDF GCC15.2 must agree on ELF32 RISC-V
single-float ILP32F ABI; inspect final ELF/map, symbols, memory and stack margin.
No allocation or panic recovery may export partial output. Failure clears output.

Core REVIEW_LIFETIME remains100 ticks: one tick is floor(esp_timer_get_time()/1e6),
an actual monotonic second, fixed from intake and never reset by navigation.
UI additionally checks the same absolute deadline while awaiting local action;
signing and completion use fresh samples. No frozen clock, enlarged lifetime or
host ACTIVE5000/human-wait API adoption. Intake busy never replaces pending work.

## Trusted display and local input

Maintainer inventory: three external buttons PWR, RST and BOOT; this is not a GPIO
measurement. The official board schematic at vendor870588e6, SHA256
3d8b63f8f2a5a89d00c54eaf9798658f3147774e8d3383a1b0a96d5fb9c82d30,
shows BOOT switchK3 between GPIO35 and GND. Verify actual idle/press/release on the
sample before signing evidence; BSP_CAPS_BUTTONS=0 supplies no button proof.
PWR/RST retain their hardware roles. Touch remains navigation only and cannot
produce Approve/Reject. Frame text uses a bounded fixed-cell ASCII font; the
core already escapes non-ASCII, with full label/body/position shown untruncated.

Each frame is synchronously committed through the display flush boundary before
input can acknowledge it. Fresh release is required after presentation and every
transition: pre-held touch/BOOT cannot advance/approve a new page. Data pages use
fresh touch Back/Next; BOOT release rejects. Only the separate final decision
page may accept BOOT held1500..5000ms and released (debounce40ms, beyond5000 rejects; too-long or
timeout rejects); short press/release rejects. No action is cached across frames;
the core independently requires all pages seen before consuming local authority.
At startup an observed BOOT press/release check precedes session initialization.

Cancel/reject/error/expiry clears pending authority and any public response;
reset/power-off restarts the public-fixture demo. Signing consumes exactly once,
returns the existing v2 response envelope and shows a fresh public response QR.
The unchanged client must independently verify request correlation, identity,
canonical ID and signature; logs contain only states/counts/latencies, never QR
payloads, nsec, private keys or event/plaintext contents.

## Evidence and physical procedure

First focused native/target checks cover envelope caps/ambiguity, frame shape,
BOOT debounce/fresh release/hold frame binding, clock/expiry, display failure,
correlation/replay/cancel, auxiliary failure and output capacity. Reuse unchanged
core vectors instead of replaying a broad campaign. Build the actual image and
inspect final ABI/memory/providers before asking root for flash. On hardware:
confirm GPIO35 idle/press/release; scan a known actual client request from screen;
read every page and reject once; rescan and approve by final hold+release; scan
the response using the unchanged client verifier. Repeat stale hold/touch,
cancel/expiry, malformed/multiple QR and replay-rejection cases that apply.
Capture actual timing/stack/memory and visible trust labels. Unobserved behavior,
image integrity/C6 isolation, real key lifecycle/entropy and full product/client
qualification remain explicit open gates.

Root reviewed the bounded gesture model before signing implementation. A blocked
DMA wait or quirc call does not gain a hard time bound from checks on return:
measure work/latency and watchdog/supervision separately. This first public slice
closes no liveness gate; its one worker/decoder owner cannot admit a second
operation while the previous call remains outstanding.

## Acquisition coordinates, ownership and measured supervision

Let B(x,y) be the actual800x800 little-endian RGB565 buffer returned by the
unchanged video adapter, and G(x,y)=luma(B(x,y)). The app adds no rotation or
mirror. It rejects all other dimensions/byte counts before reading a pixel.
The sole worker obtains the decoder image through quirc_begin, converts into G,
then releases the camera's borrowed buffer. Camera waits for that copy-complete
semaphore before returning/requeueing; it never calls quirc or Rust. A separate
ownership token and scan_enabled prevent another admitted frame/operation until
the worker finishes and releases it. An outstanding conversion is not an idle
scan and must not feed the worker watchdog.

Before quirc_end thresholds G in place, the worker copies a fixed307200-byte
RGB565 preview from exactly G using V(u,v)=G(144+floor(8u/5),16+floor(8v/5)),
0<=u<320,0<=v<480. This uses the measured peripheral's crop/scale geometry,
with CPU nearest samples rather than presumed bit-identical PPA filtering.
The LVGL snapshot has no app PPA/rotation/mirror; complete flush/DMA commit
precedes reuse. PUBLIC labels have opaque white backgrounds over the image.
The ST7796 BSP source's MADCTL MX1/MY0/MV0 is downstream from G and V. Panel
mounting/sensor optical parity is a separate coordinate basis: a readable LCD
cannot prove an unmirrored raw buffer. Native unequal corners/off-axis gray and
normal/mirrored public QR fixtures establish the software mapping, not optics.
Root's first device probe must present both asymmetric numbered marker and one
public QR and compare preview positions with decoder success/attempts; no sign
or claimed consent while USB-UART data remains connected.

The baseline TaskWDT5s only checked idle tasks and did not panic. This app's
versioned sdkconfig.public explicitly enables TaskWDT panic at the same5s,
silent panic reboot and no coredump, retaining the real esp_timer clock and core
100s absolute deadline unchanged. The unique worker registers with TaskWDT;
only its cooperative UI polling/idle scan yields feed it. No camera, timer,
LVGL/DMA callback, decoder, conversion or crypto call feeds on its behalf.
Every return to scan is after outstanding work is collected. Failed feed,
foreign/repeated owner and unexpected registration fail closed. Native mocks
check ownership/refusals only; they do not prove actual hardware reset timing.

Three source-identical configured public variants are built in the same existing
build directory: normal(mode0), busyCPU(mode1), blockingwait(mode2). Fault modes
run autonomously before BOOT check or Rust engine/key initialization. BusyCPU
keeps interrupts enabled with no feed; blockingwait waits forever on a private
empty semaphore whose handle has no producer/export. Neither accepts host
commands/approval. Each reports only public mode, reset reason and real start
milliseconds. Root separately bounds each observation, measures reset reason/
time/actual UART behavior, then restores exact normal hashes. Normal must retain
UI wait beyond5s without reset and return/expire on the real100s deadline. A
stuck decoder/flush is not proven to return by5s: WDT supervision is a separate
fault-reset mechanism, still physically unobserved. TaskWDT source may print
triggered task/CPU names and, when both cores fail, a backtrace before silent
panic; quiet config/no-coredump is not a secret/log safety guarantee. Debugger,
interrupt failure, memory/stack margin, reset/wipe, custody and entropy remain
open. This public fixture opens no real-key route and closes no liveness gate.

The crypto dependency now adopts reviewed official crypto-bigint0.7.9 from
563d10b3, proof9d312f3e, plus the explicit83f P4-lock patch. Core/FFI/local limits
are unchanged. Old83f binaries/proofs remain historical; the new target and host
producer get new hashes. Two existing public positives/replay and the unchanged
client verifier are rerun for that producer; original unaffected host negatives
are reused instead of repeated as a new campaign.

The new consumer omits only the three unused audio-player/file-iterator/MP3
components formerly pulled by bsp_extra; every retained component version/hash is
identical to the original pinned set.

Concrete BOOT trust finding: the same GPIO35 node also reaches U6 EMH4T2R
controlled by USB-UART DTR/RTS in the official schematic. Physical button origin
cannot be inferred solely from its level while that path is active. Root was
notified before hardware signing; actual data-path absence/isolation and the
operator procedure require distinct admission. This is not replaced by a flag,
callback or touch approval. The candidate remains controlled/public engineering.

### Frozen-source build packet (26 October 2026)

Source0227ce5b4a20e074152333be7c454674ad1425bc produced all three variants in
one existing build directory; source/commands/config/artifact hashes and focused
proof live in `proof/raw-mirror-wdt-079/`. The normal image was rebuilt after the
two faults and is byte-identical to the first frozen-source normal image. ELF is
32-bit little-endian RISC-V/RVC/single-float; internal Rust owner remains5920bytes
at0x4ff57358. Worker stack is an explicitly internal96KiB allocation with endpoint
checks; stack margin and actual runtime remain unobserved. Effective SDK config
SHA256 is a5d508d745eff91de953d6e6f5d48f384f130dd6e1cd8ee13422440862cb494d,
with the complete config and raw baseline delta preserved compressed.

quirc retains its fixed upstream254 regions/32 capstones/64 grids and
800x800 preallocation under the700000-byte decoder allocation cap. The decoder's
internal supported maximum remains version40; this consumer accepts at most117
modules/version25 before bitstream decode. No hostile resize or open retry.
These caps and native~7.5ms normal/mirror observations are not a measured P4
worst-case time. WDT5s is neither core100 ticks nor an ACTIVE5000 cost budget.
Because ticks are floor seconds, elapsed time from the first core clock sample to the deadline is within
99..100 seconds depending on its fractional phase; navigation never restarts it.

Root's controlled probes, after distinct source/artifact review:

1. Normal, with USB data: public marker1 2/3 4 plus one public QR, compare preview
   positions, decoder count/attempts/latency and public banner. Startup BOOT check
   is GPIO diagnostic only. Do not acknowledge a final approval/sign while that
   USB-UART data path can drive GPIO35. A separate admitted battery/data-absent
   procedure is needed before any local-consent/signature observation.
2. Normal cooperative wait: observe more than5 real seconds without WDT reset.
   On a public review request, leave the review until its fixed floor-second
   deadline; record refusal/cleared authority, not a signature or extended clock.
   Actual complete review/consent/response procedure remains gated separately.
3. BusyCPU then blockingwait: flash each exact reviewed hash separately, bound
   each observation to one reset/20 seconds and interrupt the repeating probe
   with the operator's controlled reflash/reset procedure. Check autonomous mode
   log, real start time, observed reset reason/elapsed time and lack of engine
   initialization/operation. Failure to reset within the observation window is
   a failure/unavailable measurement, never a new time limit or automatic retry.
4. Restore the exact normal hash. Record actual flush/decode/stack/memory and
   watchdog behavior before widening inputs. Only then can the root decide which
   further physical negatives apply. No physical outcome is claimed by this packet.

The initial target compile failed on the missing public cache API declaration;
adding its actual LVGL9.6 public header corrected it without warning suppression.
The original upstream quirc NULL/zero memcpy RED and precise guard remain
preserved in the earlier proof; no new algorithm patch was made here. Root must
review this affected consumer and that inherited correction before admission.

### Affected correction after distinct review of4be7d8f

The root-assigned distinct reviewer found that the adapter's v9 wait checks only
rendering_in_progress then sleeps20ms; LVGL clears that render flag before the
last asynchronous color DMA completes. The previous comment/claim that dummy
mode was a physical commit was wrong. That reviewed RED and the4be/0227 builds
remain historical. No flash of them is admitted by this correction. The reviewer
also identified the shown QR waiting indefinitely for BOOT despite the stated
expiry-clear contract. The code now implements that contract rather than
reinterpreting the original deadline after the finding.

The app uses only public APIs to retain the BSP's exact OTHER/rotation0/320x480/
50-row/internal-single-buffer/no-PPA/tear-none profile and unchanged underlying
BSP panel/touch initialization. It initializes the adapter, disables its automatic
IDF callback registration before register_display, installs one IO callback plus
custom_draw_bitmap, enters dummy mode, registers touch and only then starts the
adapter. Brightness stays off until a fully committed status screen. There is
no prior LVGL color transaction or callback-owner handover to drain. The app's
IO callback forwards every actual color completion to the adapter's public
notify_color_trans_done_from_isr so normal LVGL flush_ready is retained.

Every stripe submission captures the current frame generation and an increasing
serial before esp_lcd_panel_draw_bitmap. It waits on a fresh binary completion
signal without any watchdog feed; an unexpected residual signal is an error.
The frame has one absolute2s commit deadline from start_screen, never restarted
by another stripe or ACK. Success requires an ACK matching the pending generation/
serial, collected before the deadline, and all submitted stripes completed with
no pending work. Input freshness begins only after that whole-frame success.
Missing/late/unexpected/duplicate/out-of-generation ACK, display error, counter
wrap or a frame with no submitted stripe latches failure until restart. Failure
prevents further physical submissions and subsequent cooperative watchdog feeds.
The adapter's20ms delay remains an inherited implementation detail with no role
as evidence of completion. A blocking IDF/adapter call can still require the
separate watchdog reset mechanism; this adds no qualified hard return bound.

Important correlation limit: the IDF IO callback supplies no hardware transaction
ID. Matching is established by zero-inflight startup, this one serialized sender,
one ST7796 tx_color per draw and IDF's one callback on its final color segment.
The native ACK model tests explicit stale identifiers and state/refusal behavior;
it does not prove an ID that the hardware/API does not provide or arbitrary
spurious-IRQ resistance. The callback/clock/ACK helper are placed in IRAM and their
state in internal RAM for the current configuration; this is not qualification
of the complete inherited ISR/cache-off path or physical pixel visibility.

Response rendering starts with backlight off. The complete response QR is committed
with those stripe ACKs, then the same real absolute core deadline is checked before
and after backlight activation. The response wait uses that unchanged deadline,
not a new TTL: on the first observed expiry (poll up to10ms, scheduler behavior
still to measure) or fresh BOOT clear, the1536-byte output is zeroed before the
UI clear callback. The lamp is disabled, the QR widget is removed and a complete
clear/status frame is acknowledged before the lamp is re-enabled. Display/clear
failure keeps the lamp off and stops/restarts without returning to feed/scan.
This does not revoke a previously verified public Nostr event or promise an
instantaneous hardware transition exactly on a wall-clock boundary. Actual
expiry-to-dark/clear latency remains a controlled device measurement.

The resume feed now occurs while the worker retains the camera-admission token;
only after the feed/yield does it enable/release admission. An idle-scan feed also
takes that very token around check/feed, so an outstanding raw buffer cannot race
the idle feed check. Core/Rust FFI, crypto079, grayscale/crop, quirc/decode fallback,
input gesture FSM, sensor adapter and SDK configuration remain unchanged. Reuse
their frozen proofs; only ACK/response-clear/feed-token fixtures and three affected
app variants are rebuilt for the new source. Distinct review and physical reset/
DMA/expiry/BOOT-DTR gates still precede flash/signature admission.

Frozen affected source53094ba7906eff671d7a2dd0a8b83d1120a94821 builds all three
variants successfully in the same build directory. New proof is under
`proof/display-ack-expiry/`, including the immutable prior distinct RED receipt,
new native commands/hashes, actual target compile failure/correction, source
boundary and final ELF. Normal is restored byte-identical after both fault modes.
Effective SDK remains a5d508d745eff91de953d6e6f5d48f384f130dd6e1cd8ee13422440862cb494d;
Rust staticlib/vendor/locks are byte-identical to the earlier admitted079 producer.
New ELF places the5920-byte owner at0x4ff574e0, ACK state at0x4ff5be80 and own
clock/color-callback/ACK-complete in IRAM. Internal96KiB stack is still requested
and checked; no physical stack margin is invented. Builds and native mocks are
preparation; only the distinct reviewer/root can admit the source for controlled
physical observations. No previous RED binary is relabelled or flashed.
