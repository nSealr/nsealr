# P4 application

This application is for the Waveshare ESP32-P4-WIFI6-Touch-LCD-3.5 with its OV5647
camera. It uses one owner task, the Rust `nsealr-device` core, LVGL 9.6 and the
board's actual camera, touch screen, display and qualified random-source sequence.
The companion ESP32-C6 is held in reset on GPIO54. No transport is accepted over
USB, Wi-Fi or Bluetooth.

The implemented flow creates or imports an identity, offers an optional BIP39
passphrase and NIP-06 account, displays and verifies recovery backups, collects
animated QR requests, reviews authority and prose, and returns the core response
through QR. Supported local backups are words, nsec, SeedQR and compact SeedQR.
The public identity has a normal npub QR. Lock and inactivity clear the owner.
For a loaded mnemonic, `Identity options` reopens passphrase and account settings.
Viewing the public npub returns to the same confirmation screen. Account changes
take effect only after successful derivation; cancelling retains the current key
and account. `Add / change passphrase` offers typing or `Scan passphrase`: a raw
UTF8 text QR from an offline source, at most 256 bytes before and after BIP39 NFKD
normalization. Never enter this secret into the connected companion. Scanned
Unicode and control characters are shown as explicit escapes for local review
before `Use passphrase`; cancelling retains the loaded identity.
The local 2-of-3 flow creates a group across three devices, compares the complete
setup fingerprint, exchanges authenticated peer packets through the companion,
and signs with two shares after normal event review. Every outgoing packet must
be captured before the scanner opens. The loaded group exposes its public record
and a distinct four-frame secret share backup; it has no mnemonic or nsec export.
Secret share QR capture requires an offline receiver, never the connected
companion. Animated restoration requires confirmation of the recorded group and
member. Scan-back checking compares the share without replacing the loaded one.
Group custody signs events; it does not support private-message decryption.
To load a group into the companion again, choose `Public identity` → `Record` →
`Show QR`. This redisplays the public descriptor without exporting a secret share
or consuming a pending operation. `View text` returns to its fingerprint/member
record; QR pause and manual frame controls remain available.
For durable local backup, the board can deliberately save its unencrypted share
as `NSEALR.NSR` at the root of a FAT-formatted SD card. It never formats a card or
overwrites a file. Save synchronizes the file, invalidates the sector cache, and
reads back every byte before reporting success. Restore reads only this bounded
file and still requires the core's group/member confirmation. Keep the card
offline and separate from other shares; record the public group fingerprint
independently. Missing or unreadable cards produce a recoverable error.
The core determines accepted Nostr methods and event semantics; unknown semantics
are rejected. Private text and backup/response QR pixels use bounded direct
raster buffers rather than LVGL labels or generic image caches.

## Build from a fresh checkout

Use Rust 1.95 and ESP-IDF **6.0.2**, source commit
`7101770dc6db2667b3c477cc31365dd1acd6db4e`, with its installed ESP32-P4 toolchain
and Python environment. Follow Espressif's normal installation and `export.sh`
steps. The target must support `riscv32imafc-unknown-none-elf`.

From this repository root:

```sh
rustup target add riscv32imafc-unknown-none-elf
cargo build --release --locked -p nsealr-device --target riscv32imafc-unknown-none-elf
python3 tools/prepare_adapter.py
export NSEALR_COMPONENT_ROOT="$PWD/.cache/p4/components"
export NSEALR_SOURCE_ROOT="$PWD"
cd firmware/p4
idf.py -DIDF_TARGET=esp32p4 \
  -DNSEALR_CORE_ROOT="$NSEALR_SOURCE_ROOT" \
  -DRUST_LIBRARY="$NSEALR_SOURCE_ROOT/target/riscv32imafc-unknown-none-elf/release/libnsealr_device.a" build
```

`prepare_adapter.py` fetches the exact published adapter 0.6.4 source archive,
checks its SHA-256 and applies `adapter.patch`. The patch only adjusts public
header paths for LVGL 9.6. The remaining managed components use `dependencies.lock`.
`idf.py` reads the checked-in `sdkconfig.defaults`; an older project or its
configuration is not needed. Build outputs and downloaded components are ignored.

`tools/build_p4.py` is an alternative for explicit tool/cache locations, useful
when several worktrees share an SDK. It accepts `--sdk`, `--tools`, `--python-env`,
`--rust-library`, and optional `--core-root` and `--work-dir`. Cached components
may be copied with `--reuse-components`; they are not an authoritative source of
configuration. The tool writes build logs and the image hash but never flashes.

Flash a built image using the usual `idf.py -p PORT flash monitor`. This replaces
the firmware; it does not install persistent user keys. Only use disposable test
identities while qualifying a new firmware image.

## Ownership and limits

`main/main.c` owns the hardware and core allocator. Core allocations use internal
RAM only; public rendering and camera decoding use external RAM. The sole owner
performs signing, camera stop/join, key teardown and fatal cleanup. An acknowledged
LCD transfer precedes completion of a review item. Critical fields are grouped in
one continuous reader. Prose may be skipped only through a separate, local,
per-request confirmation. Unsupported characters and controls have explicit,
lossless escaped representations; literal backslashes are escaped as well.
The SD operation owns slot 0 and its LDO4 lifetime. FatFs uses one sector window,
checked for internal RAM before private I/O and wiped before unmount. File state,
read-back scratch and export/import buffers are also wiped. The SD host receives
an owned internal DMA-aligned bounce buffer, wiped before unmount and freeing;
private unaligned sector transfers cannot allocate an untracked temporary copy.
Driver/controller
remanence and actual removable-media durability require hardware qualification;
the native file test does not establish either property.

The native application exercises the same controller and UI with published test
entropy. It cannot establish camera reliability, physical display/touch ordering,
entropy quality, reset cleanup or radio isolation. A build alone does not establish
those properties either. Production release qualification must include actual
hardware measurements and review of the complete dependency and firmware image.

Hardware source attribution is recorded in `SOURCES.md`. Fonts retain their OFL
licenses and source assets under `../ui/fonts/`.
