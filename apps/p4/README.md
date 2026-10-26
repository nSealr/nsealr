# P4 public optical engineering app

This flashable engineering app connects the real camera to a bounded QR decoder,
the one unchanged Rust Nostr engine, full local review, a GPIO decision and a
public response QR. It uses the intentionally public11x32 identity and the
fallible public P4 auxiliary experiment described below. The banner and artifact name identify it as PUBLIC
TEST; it accepts no personal identity/recovery import and has no qualified custody,
entropy, channel-isolation, human-time, liveness or release claim.

Source and acceptance contract: [Q03 brief](../../docs/restart/implementation/Q03/p4-optical-brief.md).
This app and its brief/proof change, plus the explicitly reviewed0.7.9 vendor/root lock adoption; the core, client, protocol and task graph
are unchanged. `inputs.json`, the dependency lock and quirc notices pin provenance.
The frozen camera source is reused; no old std host fixture is a runtime dependency.

Build with the already admitted Linux tool environment:

```sh
python3 apps/p4/build.py rust
python3 apps/p4/build.py configure
python3 apps/p4/build.py app
```

`NSEALR_P4_TOOLS` selects the existing P4 tool root; `NSEALR_RUST_TOOLS` selects
the existing isolated Rust1.95.0 tool/cache root. Defaults match the active root.
The temporary peripheral input remains read-only at its admitted source location.
The recipe reuses its component store, versions and corrected LVGL adapter;
no second SDK/toolchain installation is needed. The new consumer omits unused
bsp_extra/audio-player/file-iterator/MP3 code. No retained component version/hash
changed. Normal source migration and an independently reproduced distribution
recipe remain Q03/Q05 work.

The Rust owner is allocation-free and section-bound to internal DRAM; the worker
allocates/checks an internal96KiB stack. The final ELF/map proves link placement
and ILP32F ABI, while physical stack margin, execution, memory and wipe behavior
remain to be observed. All parser/crypto/authorization semantics stay in core.
Static947-byte frames and JSON704 are initial measured-input candidates, with
smaller local content/tag/review caps declared in the brief. QR rendering uses
LVGL; excessive results fail instead of truncating. Logs omit input/QR/secret data.

The fixed-cell32x8 renderer commits complete label/body/position before arming
fresh input. Touch only navigates data pages. BOOT tap rejects; a final decision
requires a fresh1500..5000ms hold and release; pre-held/released input does not
act on a new frame. Real esp_timer ticks keep the core's100-second deadline.
Fresh clock checks surround review callbacks, signature/result construction and
physical QR rendering. Blocking DMA/decoder calls still have unqualified hard
return bounds; only one worker/decoder owner can be outstanding.

## Physical admission still required

The official schematic identifies BOOT K3 as GPIO35-to-GND, but GPIO35 also joins
U6 EMH4T2R auto-download circuitry controlled by USB-UART DTR/RTS (and ESP_EN).
A GPIO edge alone therefore cannot prove human origin with that data path active.
Do not count it as trusted physical consent until the actual channel arrangement
and operator procedure are separately admitted. A disconnected/data-absent UART
path needs physical evidence; a software flag is not that evidence. PWR/RST keep
their hardware roles, and touch approval remains disallowed.

The original180-degree grayscale assumption is superseded. Gray now preserves
raw camera coordinates; the scan preview snapshots that same gray before quirc
thresholding, with crop144,16 size512x768 scale5/8 and no app rotation/mirror.
The physically observed peripheral reference2aaf used PPA0/mirror0/0, but panel
MADCTL is downstream: raw optical parity needs the asymmetric marker+QR probe.
A mirrored QR gets at most one ECC-only quirc_flip retry, in the same ownership
and watchdog interval. Native normal/mirror fixtures recover identical bytes.

The single worker explicitly registers with TaskWDT5s. Only cooperative UI/idle
scan waits feed it; no feed during conversion/decode/flush/signing, and no second
owner while work is outstanding. The explicit sdkconfig.public enables watchdog
panic/silent reboot/no coredump, with effective hashes recorded. This does not
prove a hard return bound, secret-free diagnostics, reset/wipe or core100s timing.
The approved public fault packet has three compiled modes, normal/busy-cpu/
blocking-wait; fault modes autonomously start before engine/key initialization:

```sh
python3 apps/p4/build.py configure --probe-mode busy-cpu
python3 apps/p4/build.py app --probe-mode busy-cpu
python3 apps/p4/build.py configure --probe-mode blocking-wait
python3 apps/p4/build.py app --probe-mode blocking-wait
python3 apps/p4/build.py configure --probe-mode normal
python3 apps/p4/build.py app --probe-mode normal
```

Root reviews frozen sources/artifacts before separate bounded physical reset
observations and restores normal. No host-triggered approval/fault mechanism.
Startup requires a fresh BOOT check. With USB data connected this is only an
input diagnostic and public marker/QR probe; no claimed consent or signature.

After source review and physical admission, root binds exact device/image/offsets
and transfers hashes, flashes, observes GPIO/display/actual scan, rejects once,
rescans, acknowledges every complete data page, holds/releases on the separate
final decision, then verifies the public QR with the unchanged client. The host
callback suite and decoded public fixtures are preparation, not this procedure.

Third-party terms: frozen camera files retain their original CC0-1.0/Apache-2.0
SPDX notices; `vendor/Waveshare-LICENSE.txt` preserves the vendor Apache2.0
license verbatim. quirc ISC copyright/permission/disclaimer remain in each source
and header, with exact upstream and explicit local-patch hashes.

The affected display correction after4be review owns the IO callback from startup
through public BSP handles and preserves the adapter callback behavior via its
public completion notification. Every stripe now waits for actual color-done,
with one2s deadline per complete frame and sticky failure before input/feed.
Dummy mode and its inherited20ms delay alone are not ACK evidence. Response QR
is drawn dark, published only after ACK plus fresh deadline checks, and cleared
with its output buffer at the same absolute deadline even without BOOT. See the
brief for correlation, physical latency and cache-off limits; prior builds remain
historical. The scan feed takes/retains the camera's admission token.

Normal public mode0 now holds/checks the pinned board's C6 GPIO54 before engine
admission and across critical UI/output/feed boundaries. It has no SDIO/reset
cycle or radio initialization. Abnormal reset reasons stop without engine.
See docs/restart/implementation/Q03/p4-normal-c6-guard.md for the exact sampled
pad policy, USB/PMIC/operator precondition and remaining physical/reset limits.
This remains a public fixture, not an offline/custody-qualified release.

## Public fallible P4 auxiliary experiment

The original33a6b4e3 image/proof remains historical and immutable. The current
private callback replaces target0x22 bytes with the exact SDK6.0.2 helper and
esp_random, through the same core AuxiliarySource. No identity import, generation,
backup/recovery, production entropy admission or protocol/core/time change.
Deterministic0x22 exists only in the synthetic host test provider.

This identified rev3.2 target uses minrev300 and hw_ver3: WDEV_RND_REG selects
LP_TRNG data base+4. The helper also configures ADC1 internal channel10, calibration
2166, XTAL/divider0, SAR divider15, trigger100 and enables LP_TRNG clock/reset/
sample/timer. The collected preliminary TRM describes an older data address;
the exact rev3 source mapping remains a production qualification gap. Sample
counter8bit wrap/alias is diagnostic only. No S3 DATA_STATUS/DONE/ADC183 policy is
borrowed. Configured clock getters and output screens do not measure entropy.

The one worker takes both real ADC try-locks, claims/frees the SDK ADC bus, and
pairs helper enable/disable. ADC2 is locked because disable clears both calibration
values. Empty reset-lock functions are not an ownership mechanism. The analog
master is shared with PLL/MIPI; existing SDK references remain balanced and never
rewritten to match a guessed baseline. One persistent helper reference and one
temporary REGI2C reference require headroom<=253 in the SDK8bit count. Unexpected
active consumers, register/ownership changes or missing cleanup refuse/poison.
Camera/SPI LCD/FT5x06 touch and C6 guard remain their existing paths; no new
battery/PMIC sampling, GPIO54 release, SDK patch, IRQ handler or scheduler freeze.

A global50ms monotonic between-call budget and finite256settle polls surround
eight SDK words into32bytes INTERNAL staging, all0/FF/repeated/duplicate-block
screens, cleanup and final C6 checks. SDK/ROM calls that do not return cannot
be interrupted by these checks; unchanged5sWDT is never fed in collection.
This detects specified faults and never qualifies source quality. Gated or
unpowered banks are UNKNOWN; disable does not promise every ADC block powered
off or all registers restored. Busy/partial lock acquisition leaves unowned
hardware untouched, and owned errors wipe full destination/staging/history.

Only a fresh full review and the existing final BOOT hold/release can reach the
callback. Touch never approves; the USB BOOT/DTR/RTS human-origin limitation
remains. C6 pad/config is checked at entropy-before/after and between operations;
samples are not chip-pin/RF/offline/reset-hold proof. One auxiliary attempt per
CPUboot includes failure; after it the public app requires restart, never retries
until green or reuses approval. No raw auxiliary/identity/payload logs.

Build.py supports --entropy-mode normal or fixed-unavailable; fixedUnavailable
is a separate compile-time public image, only with normal C6 guard mode0. It has
no runtime host selector and returns a typed error after the same local review.
Both images need distinct source/config/ELF/staticlib/flash identities and root
review before flash. --host-proof on the single Rust build command also emits
the existing Linux consumer for actual focused FFI negatives, using the same
cached target/dependency/tool environment. It is not a new hardware port.

Provider retained state<=256bytes and report<=512bytes INTERNAL,32byte staging,
no new task/heap/DMA/DRBG; existing96KiB INTERNAL worker stack unchanged. Selected
static frames and affected physical minimum>=4096bytes free remain separate
checks. One fixedUnavailable public boot and one normal public boot are proposed
for root only, with a new request/fresh confirmation per boot and explicit host
expectedPublicKey plus independent BIP340 verification. No extra draw screen,
output-statistical campaign, real identity or device/task closure is authorized.
