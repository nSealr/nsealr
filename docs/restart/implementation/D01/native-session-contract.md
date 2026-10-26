# Native S3 public request flow and secret-session boundary

Author: /root/s3_native_finish. Distinct reviewer: /root.
Input: native packet bcad72faaa956e08d8506167abc13c7f35ac56d2;
compiled foundation a159db50af182d134ffce22d4d92826f24f1a651;
ESP-IDF e0991facf5ecb362af6aac1fae972139eb38d2e4 and the admitted native
Cargo lock SHA256 28fb1a218de7a16421e156de24b1153c70d6d905af48205a65226148d50b7640.
This is a reviewable implementation contract. It closes no plan criterion and
does not admit real identities. The sole task state remains plan/work-items.json.

## Next functional delivery

Extend the same apps/s3-session consumer to carry a real existing version-2
request in the existing nsealr1f serial frame through complete on-device review,
fresh physical inputs, AuthorizationSession::sign_approved, and the existing
client's independently verified version-2 response. Only published scalar 3 is
compiled in. There is no function accepting arbitrary scalar/nsec, no recovery
export, and no production entropy endpoint. The same nsealr-core remains the
only parser/catalog/canonicalization/consent/crypto implementation.

Keep USB Serial/JTAG for this first public request flow so the already-built
native peripheral proof can be extended directly. This is a public test mode,
visibly named on every screen. Its hardware JTAG/download channel is unqualified
for secrets. The selected subsequent connected secret-session transport is
USB-OTG CDC, subject to the reset/RAM gate below; do not describe these two
transports as interchangeable security profiles.

The first delivery owns apps/s3-session, its thin Rust static-library adapter,
one attributed bitmap font asset, finite host/device procedures and this D01
evidence. It does not change the core, product capabilities/readiness, Bridge
custody, general plan or the immutable apps/s3-io-probe. Root owns integration,
the distinct review and physical USB operation.

## Public wire and resource contract

Use core serial::input::SerialLineInput and serial::frame for accumulation,
overlong draining, checksum, decode and encode. The checksum detects framing
corruption; it authenticates no sender. Reuse core base64url and strict
event::ParsedRequest; do not add a C++ JSON/base64/Nostr parser.

- Frame capacity: 1024 bytes including newline; one completed request at a time.
- Read quantum: at most 64 received bytes per scheduler iteration.
- Decoded request: at most 320 bytes; content at most 128 decoded bytes,
  at most four tags/four fields each, 64 bytes per field and 160 aggregate text
  bytes; canonical bytes at most 1024; at most 128 complete review pages.
- JSON response staging: 704 bytes; framed response at most 1024 bytes.
  Before source admission, prove that this smaller request bound plus the
  fixed version-2 response fields and signed-event expansion fits that staging.
  Core JSON string serialization does not expand a valid original JSON string:
  it uses the same or shorter control escapes and preserves UTF-8 bytes.
  Keep output-capacity failure closed even after this preflight bound.
- No input queue, hidden result retry, automatic grant or implicit key switch.
  A repeat request requires a new complete physical review.
- Supported public-test methods are get_public_key and sign_event.
  get_capabilities returns an explicit unsupported/unqualified error, without
  claiming the conformance persistent-custody profile or default product readiness.
  The unchanged core determines which public-event kinds/semantics fit the
  declared small limits. Unsupported semantics and incomplete review reject.
- No periodic unbounded logs. Protocol errors disclose only finite public error
  codes. Never echo a received payload as a diagnostic.
- Drain/discard input arriving during a live local review. It cannot replace
  the owned request or act as approval. After settlement, discard residual
  queued bytes before accepting a fresh frame. Test this boundary explicitly.

Copy and retain the completed original frame/decoded request before the first
C display callback; a callback cannot mutate which request is later signed.
Use one synchronous Rust owner. Its private consent never leaves Rust; C only
implements the trusted display/input/clock boundary. Cancel and lock the owner
on every ordinary return; a lost response never recreates consumed authority.
If TX cannot finish within the finite transport limit, discard the result and
require a new review. A fresh real clock sample is required immediately before
the adapter releases the completed framed result.

## Actual display and two buttons

Use the same I80/ST7789 peripheral sequence, one PSRAM framebuffer and DMA
completion ownership from the foundation. Use the already retained LilyGO
1cc41eb1 TFT_eSPI glcdfont.c bitmap data (original Adafruit_GFX 5x7 font), with
its original copyright/BSD notices. No TFT_eSPI runtime is added.

Render 26 columns by eight text rows, with a 6x8 cell scaled two in each
dimension: 312x128 pixels. A fixed PUBLIC TEST KEY banner and contextual button
legend fit outside these rows in the 320x170 screen. Draw the complete core
InspectionFrame label, body and position, in order, preserving its explicit
wrapping; reject any line or total that cannot fit. No abbreviated key, hidden
suffix, clipped label, replacement glyph or automatic page acknowledgement.
The core's escaped ASCII review is rendered as the actual printable ASCII
glyphs. Physical readability and edge pixels still require distinct readback.

GPIO 0 owns Back/Reject/Rotate; GPIO 14 owns Next/Approve/Enable.
These names identify stable functions, not a claim about upper/lower physical
positions. Root observed the current foundation's buttons on the left edge. Keep the 40 ms stable transition rule and
require both inputs released after every successful complete frame commit.
An initial held button cannot acknowledge the new page.

- Idle: a fresh local Right press/release enables the known public-test identity.
  The screen shows its actual full derived public key before requests.
- Data page: a fresh short Right press/release advances; Left returns a page.
  Both buttons held for 1.5 real seconds reject the request and disable the
  public-test session. A gesture is never inferred from USB data.
- Final decision: Right alone held for 1.5 real seconds approves only this distinct
  final frame; a fresh Left press/release rejects. Both held locks as above.
  Both takes precedence over Right approval, including a pending raw Left press.
  A held Next from the prior page cannot become Approve.
- Result/rejected/expired/locked screens require a fresh release/gesture before
  another request. A no-event callback returns no authority.

The draw-completion point and subsequent release/press/hold timestamps are
observable public evidence. A source-level call or counter does not prove pixels
or a physical gesture. Display/DMA failure returns a display error, with no
acknowledged page or signature output.

## Time and ordinary cancellation

Root selected the existing core unchanged for this bounded public flow:
now() is floor(esp_timer_get_time()/1_000_000), explicitly real monotonic seconds.
The unchanged 100-tick lifetime therefore expires at intake_seconds + 100. Flooring can make expiry up to
one second earlier than 100.000 elapsed seconds from the intake instant.
Use the same clock/unit before intake, on both sides of every presentation,
before the signing attempt, after signing and before adapter result release.
Reject missing/negative/rollback/overflow/expired readings. Never reset, subtract
wait time, freeze or change the clock unit during an operation. Retain the
microsecond clock separately for measured latency and the 1.5 s gesture timer.

The display callback checks the same absolute deadline while polling physical
inputs. It cannot remain blocked indefinitely after expiry. Serial SOF loss
cancels/locks and discards pending data; SDK usb_serial_jtag_is_connected detects
SOF, not whether an application has the serial port open. Port-close revocation
is therefore unqualified in this public profile. The later CDC transport must
supply its own disconnect/reset/DTR semantics and evidence.

No human-WAIT/ACTIVE exemption is implemented in the core or relabelled as
already qualified here. The 81dbf81a host canary remains a separate source-bound
precedent, including real 100 s absolute time, aggregate C5000 work accounting,
its one WAIT and original failures. A native work ledger or semantic API change
needs a separate brief, exact counters/owners and affected review; it cannot be
created by slowing the clock or simply extending C5000.

## Public auxiliary provider and evidence

This build uses one explicitly named deterministic auxiliary fixture for BIP340,
only with published scalar 3. It remains a fallible AuxiliarySource at the core
boundary; provider error/short reports must produce no response containing a
signature. This is not the next secret-session RNG and cannot be selected by a
host command. No statistical result upgrades it to entropy.

Focused adapter checks must demonstrate exact signature verification by the
existing independent Python/reference oracle and the existing client verifier;
wrong signer/event/request ID, mutated callback input, duplicate/trailing JSON,
unknown methods, frame overflow/checksum/base64 faults, missing/late/rollback
clock, failed/partial draw, reused/early/held input, reject/lock and auxiliary
failure all fail closed. Exercise actual pointer/capacity guards and sentinel
preservation at the native boundary. Reuse unchanged core and framing tests;
run new adapter/gesture tests plus the necessary changed target build.

Root hardware evidence must include full readable public key, actual overview/
all data pages/final decision, Back, Reject, one valid physical approval, an
expired operation, held-start buttons, local lock, malformed/oversized input,
flood during review, unplug/reset and host not reading. Preserve exact binary,
commands and device association privately. Verify the actual resulting signed
event under scalar 3's independently pinned public key. This is the useful
vertical slice, not secret-session or release admission.

## Concrete connected secret-session design and remaining admission gates

1. USB-OTG CDC owns the internal PHY in the running app. Candidate source is
   Espressif esp_tinyusb 3.0.0, repository commit
   68bf7f9613dbb1a31094fdb903209ae3e4bf388d, registry component hash
   0ff29f6113c4922691b3d7eee2f29af5fb98b799ef8b198a2956328f7c2296a9.
   Its published manifest requires IDF >=5.3 and bundles the TinyUSB source,
   avoiding a floating >= dependency. Archive SHA256 is
   af8bc85bc4e23ea1fc3be5b4b352f2100ed663e642aec5d62a333d4a17443b4b;
   registry CHECKSUMS SHA256 is
   fa811f2f8dd00f82fdd6a1fd3189c20210901c35dc8021a9d4bab28605c720b8.
   Existing Component Manager validation plus an exact set comparison passed
   all 439 members (run 75). Run 74's interpreter error is preserved: resolving
   the venv executable symlink selected the base interpreter without packages.
   No source/build qualification follows from this retrieval.
2. Enable one CDC function only: no MSC/MTP/network/HID/debug console, no serial
   JTAG driver, no host reboot/ROM helper, and no CDC 1200-baud/DTR reset action.
   tinyusb_driver_install creates USB_PHY_CTRL_OTG on the internal PHY; inspect
   generated descriptor/config, linked code and S3 HAL mux readback, then test
   hostile control requests. Changing descriptors alone does not isolate JTAG.
3. Qualify each reset domain separately using only public RAM markers:
   USB bus reset, suspend/resume, port close/DTR, disconnect/reconnect,
   esp_restart, watchdog/panic, EN and power cut/ROM download. Capture endpoint
   enumeration, OpenOCD/ROM accessibility, read/write/reset abilities and retained
   internal/RTC/PSRAM marker contents. No generic reset-erases-RAM claim.
   Runtime mux selection is reversible software. If hostile host reset can
   expose secret RAM before trusted erasure, this profile is not admitted for
   real keys. Read-only eFuse inventory is evidence; fuse burns are not authorized.
4. One owner reserves SAR ADC and RNG resources; no battery-voltage ADC client,
   Wi-Fi/BT/radio initialization or other ADC owner runs while sampling.
   For each collection, bootloader_random_enable must establish the exact S3
   register state; verify the relevant clock/timer/mux/reference readback before
   and after bounded esp_random collection, and call bootloader_random_disable
   on every return path. The SYSTEM_WIFI_CLK_RNG_EN bit enables RNG clocking;
   it is not evidence that RF was initialized or physically absent.
   esp_fill_random has no failure report or readiness guarantee by itself.
   The adapter must return typed unavailable/ownership/readback/timeout/health
   errors and erase partial output, with no deterministic or host fallback.
   Stuck/repeated injected output checks test detectable failures, not entropy
   quality. Source provenance/errata, actual invocation and fault-injection
   evidence remain required; unexplained hardware health is not entropy_ok=true.
5. Generation rejection-samples a 32-byte scalar through core SecretKey::take_from,
   with finite retry bound and distinct invalid-scalar versus provider failure.
   Signing obtains fresh 32-byte auxiliary input from the same admitted fallible
   provider. No key or signature leaves a failed attempt. This path remains
   absent from the first public build.
6. Allocate the owner, key/import/export scratch and crypto stack explicitly in
   internal 8-bit RAM; framebuffer may remain PSRAM only while it contains public
   review pixels. A recovery display would contain secret pixels and therefore
   needs its own internal framebuffer or qualified clearing/memory design.
   Retain no arbitrary secrets in PSRAM, RTC storage, DMA buffers, serial logs or
   crash records. Audit Rust/backend compiler moves and wipe owned current
   locations on lock/disconnect/return. Reset/panic/Drop do not prove universal
   erasure; qualify residual stack, allocator and reset windows on exact artifacts.
   Rust's public spin panic must be replaced by an affected-reviewed terminal
   secret-session policy before secret admission. No flash/NVS/FS/OTA-state writer
   is added; retain the linked closure and actual no-persistence fault checks.
7. Recovery uses local NIP-19 nsec only, never Bridge plaintext. Proposed two-button
   entry uses the fixed nsec1 prefix and five binary button choices per each of
   58 data/checksum characters: 290 short selections plus explicit edit/finish
   gestures. Display current position, recent characters and Backspace/Cancel;
   full checksum/scalar validation is by core decode_nsec. Measure a complete
   independent human entry/correction/cancellation and expected-full-public-key
   restore; the arithmetic is not a usability pass. New-key backup is local,
   conspicuous and followed by a same-identity recovery drill. Generic secret
   entry/export stays absent until host/reset/RAM and source/provider gates pass.
8. A qualified session starts Locked, enters a distinct local create/import/
   backup flow, binds one derived full public identity and starts no operation
   while recovery is visible. Local Lock, relevant disconnect, reset, key change
   and terminal failure cancel all authority and clear owned session material.
   Reconnection never resurrects a grant or key. The precise detectable USB
   disconnect rules must follow actual CDC/board power behavior.

These gates define the intended session-only profile without inventing a
persistent vault or SE. They are separate from custom-board work and do not
authorize irreversible provisioning or real identities.

Primary implementation sources are the exact SDK docs/source
docs/en/api-reference/system/random.rst, docs/en/api-guides/usb-serial-jtag-console.rst,
components/bootloader_support/src/bootloader_random_esp32s3.c,
components/esp_hw_support/hw_random.c, components/usb/usb_phy.c and S3 USB HAL,
plus the exact core authorization/event/nip19 source and registry component
notices. The web tool was unavailable; pinned local primary sources and the
captured official registry responses supply these source observations.

## Maintainer orientation steering (26 October 2026)

The maintainer requested a manual 180-degree choice, with no auto-rotation.
The menu accepts a new GPIO0 short press/release only in Idle/Locked, rotates,
clears pending ingress and remains Locked. Orientation lives in RAM only; boot
restores the physically observed buttons-left foundation orientation. Local Lock
preserves the RAM choice. A completed Lock/rotation redraw creates a new gesture
object: a held Both gesture or its release cannot rotate the menu.

The synchronous review callback cannot execute the menu handler, so orientation
is fixed from request intake through settlement. GPIO functions and the 26x8
request geometry remain unchanged. SDK panel_st7789_mirror toggles both MADCTL
MX/MY bits between (false,true) and (true,false), preserving swapXY and gap(0,35).
The banner states BUTTONS LEFT/RIGHT and the legend aligns to that edge. No upper/
lower physical GPIO position is guessed. Root qualifies both actual orientations
on the exact new image; the old a159 evidence qualifies only its original view.
