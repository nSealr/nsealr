# P4 public optical engineering app

This flashable engineering app connects the real camera to a bounded QR decoder,
the one unchanged Rust Nostr engine, full local review, a GPIO decision and a
public response QR. It uses the intentionally public11x32 identity and deterministic
fixture-only auxiliary bytes. The banner and artifact name identify it as PUBLIC
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
