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
The later180-degree preview retest is separate input; QR grayscale acquisition
will explicitly normalize180 degrees rather than claim9acf was already oriented.

Pixel decoding alone uses dlbeer/quirc927d680904dc95fdff4cd9d022eb374b438ff8f2.
The actual source/header notices grant ISC permission; retain them and hashes.
Only required library sources are imported, no printing vendor scanner/demo.
LVGL9.6 public APIs supply fixed-cell text and response QR rendering.

## Observable contract and bounds

Exactly800x800 RGB565 camera frames, length1280000, before reading pixels.
One preallocated640000-byte grayscale image, with bounded quirc tables/flood
workspace; no hostile resize/allocation. Exactly one detected QR is required:
zero waits, multiple rejects, failed decode rejects. Payload must be at most947
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

Orientation update: later physical feedback invalidated an assumption of the180
preview being qualified. The grayscale180 conversion currently has native mapping
checks only and is provisional. Await the root source/physical orientation matrix
before any device signing evidence; decoder/ABI/build work remains independent.
The new consumer omits only the three unused audio-player/file-iterator/MP3
components formerly pulled by bsp_extra; every retained component version/hash is
identical to the original pinned set.

Concrete BOOT trust finding: the same GPIO35 node also reaches U6 EMH4T2R
controlled by USB-UART DTR/RTS in the official schematic. Physical button origin
cannot be inferred solely from its level while that path is active. Root was
notified before hardware signing; actual data-path absence/isolation and the
operator procedure require distinct admission. This is not replaced by a flag,
callback or touch approval. The candidate remains controlled/public engineering.
