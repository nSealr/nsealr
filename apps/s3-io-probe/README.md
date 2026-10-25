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
