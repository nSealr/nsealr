# LilyGO T-Display-S3 public IO probe

This app draws a 320x170 border and RGBW bars, reads both active-low buttons
(GPIO0 and GPIO14), and reports debounced edges and a status line over native
USB Serial/JTAG once per second. It accepts no commands. Received bytes are
discarded without echo, up to64 per iteration. It contains no identity secret,
Nostr engine, authorization or persistent writes. GPIO0 remains a BOOT strap.

The source and tool inputs are main19ab15d1, LilyGO1cc41eb1, PlatformIO
Core6.1.18, espressif32 platform6.5.0, Arduino2.0.14/framework3.20014.231204,
and Xtensa GCC8.4.0+2021r2-patch5. The external pinned source closure provides
TFT_eSPI; set `NSEALR_S3_VENDOR_DIR` to that extracted source root.
Run the isolated `pio run -d apps/s3-io-probe -e s3-io` with a separate
PLATFORMIO_BUILD_DIR, and without the vendor-only PLATFORMIO_SRC_DIR override.
This app is a separate source selection from unmodified examples/tft.

Before any flash, bind all four images and offsets from that actual build and
review their hashes. The coordinator alone handles the Mac/USB sample.
Observe all borders/colors and both local press/release counters; compare USB
events to physical actions. A held button at app startup must require release
before a new press counts. Check bounce/hold, reset and unplug/reconnect.
With no button pressed, send `approved\n` over USB: ignored_bytes may increase,
both press counts must remain unchanged. No IO event is signing consent.
Holding GPIO0 through reset intentionally enters the ROM loader; release/reset
recovers and no app behavior may be inferred while the loader is active.

Host debounce regression:
`c++ -std=c++11 -Wall -Wextra -Werror -fsanitize=address,undefined tests/button_probe_test.cpp -o /tmp/nsealr-s3-buttons && /tmp/nsealr-s3-buttons`.
This checks diagnostic state only; actual switches/USB/display remain physical
tests. The inherited Arduino partitions include NVS/SPIFFS/coredump and are only
admitted for this public probe. A session-key app needs its own storage/dump
configuration, entropy trace, Rust ABI and consent lifecycle qualification.


## Opt-in Rust target ABI check

The separate s3-core-abi environment keeps the public IO behavior and adds one
finite FreeRTOS task with a 65536-byte requested stack. It calls the unchanged
shared core to hash abc and derive the x-only public key of published BIP340
vector0 scalar3, then locks/drops that fixture owner. No request, signature,
user key, entropy or clock-based authorization is present. It is not an identity
initialization flow. Its panic handler stalls and the session-firmware panic/
dump policy remains unqualified.

Build rust-abi/Cargo.toml with the pinned esp-rs1.97.0.0 Xtensa compiler and
matching rust-src, -Zbuild-std=core --target xtensa-esp32s3-none-elf --release,
RUSTFLAGS=-C panic=abort. Use --offline --locked and the isolated combined
product/sysroot vendor closure; product vendor/ and dependencies stay unchanged.
Point NSEALR_S3_CORE_LIB_DIR to the generated staticlib directory and build
PlatformIO environment s3-core-abi into its own build directory. link_core.py
only links that archive; it does not fetch or install anything.

The Rust call runs once; its public result is repeated20times at1second intervals
for monitor attachment, then the task exits. Read s3-core-abi-v1 over USB after boot. Require rc0, negative1,
guards1 and exactly the independent SHA256/BIP340 expected public bytes. Null
and capacities0/63/65 must reject without touching the guarded output. Task
allocation failure or absent result is inconclusive/failed, never a passing ABI
claim. The log reports real esp_timer_get_time elapsed microseconds and the
raw FreeRTOS stack watermark; units and total worst-case demand need their own
target qualification. These measurements do not set the engine's100-tick
review lifetime or qualify entropy, crypto side channels, peak product stack,
local recovery, trusted consent or release custody.
