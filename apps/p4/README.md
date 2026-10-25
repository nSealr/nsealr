# P4 public optical engineering app

This flashable engineering app connects the real camera to a bounded QR decoder,
the one unchanged Rust Nostr engine, full local review, a GPIO decision and a
public response QR. It uses the intentionally public11x32 identity and deterministic
fixture-only auxiliary bytes. The banner and artifact name identify it as PUBLIC
TEST; it accepts no personal identity/recovery import and has no qualified custody,
entropy, channel-isolation, human-time, liveness or release claim.

Source and acceptance contract: [Q03 brief](../../docs/restart/implementation/Q03/p4-optical-brief.md).
Only this app and its brief/proof change; the core, client, protocol and task graph
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

Camera orientation is provisional: later physical feedback invalidated a claim
that180 without mirroring was already qualified. The implemented gray mapping
has native tests only. Await root's exact acquisition/preview orientation matrix
before flash/signing observations. Startup displays an input-check screen and
requires a fresh observed BOOT cycle before key/session initialization.

After source review and physical admission, root binds exact device/image/offsets
and transfers hashes, flashes, observes GPIO/display/actual scan, rejects once,
rescans, acknowledges every complete data page, holds/releases on the separate
final decision, then verifies the public QR with the unchanged client. The host
callback suite and decoded public fixtures are preparation, not this procedure.

Third-party terms: frozen camera files retain their original CC0-1.0/Apache-2.0
SPDX notices; `vendor/Waveshare-LICENSE.txt` preserves the vendor Apache2.0
license verbatim. quirc ISC copyright/permission/disclaimer remain in each source
and header, with exact upstream and explicit local-patch hashes.
