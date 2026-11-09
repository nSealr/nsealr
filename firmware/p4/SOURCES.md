# Source provenance

The application and controller are new for this repository. The following
low-level routines were adapted from the prior nSealr P4 integration source
`0563d692a3ab9c53903c586cac261c14b1702dd0`: camera lifecycle, display transfer
acknowledgement, raw-frame conversion, decoder allocation bounds, C6 reset guard,
TRNG qualification/lease logic and bounded secret QR encoding. There is no old
protocol owner or fixture/family router in this application. Secret glyphs are
regenerated from the current JetBrains Mono source asset.

- ESP-IDF 6.0.2: <https://github.com/espressif/esp-idf/tree/7101770dc6db2667b3c477cc31365dd1acd6db4e>
- Waveshare BSP 2.0.2: <https://components.espressif.com/components/waveshare/esp32_p4_wifi6_touch_lcd_3_5/versions/2.0.2>
- Espressif video 2.5.0: <https://components.espressif.com/components/espressif/esp_video/versions/2.5.0>
- LVGL 9.6: <https://github.com/lvgl/lvgl/tree/60b614c23c816ca5edc5f2840c9945eff7da0ad4>
- LVGL adapter 0.6.4: <https://github.com/espressif/esp-iot-solution/tree/5d75f3f0dc499d9ed4b69284a3741187c2b75a70/components/display/tools/esp_lvgl_adapter>
- quirc: source identity and retained ISC notices in `vendor/quirc/UPSTREAM.json`.
- SeedSigner flow reference, without copied artwork: <https://github.com/SeedSigner/seedsigner/tree/995ce5c65df4bd333f61cd3dd992b39a49138a1d/src/seedsigner/views>

Public upstream licenses remain in the source and vendor directories. The two
secret QR mask-history wipes are applied to a hash-admitted original source at
build time; the generated file lives in the build directory.

`main/patch_sdmmc.py` also admits the pinned IDF SD transaction source by SHA-256
and generates a build-local replacement. It still performs the required final
cache synchronization, but retains an existing failed transaction result. An
otherwise successful cache synchronization must not turn a data timeout into a
successful read or write. The SDK checkout and its Apache-2.0 source stay intact.

- <https://github.com/espressif/esp-idf/blob/7101770dc6db2667b3c477cc31365dd1acd6db4e/components/esp_driver_sdmmc/src/sd_trans_sdmmc.c>

Recovery interaction references also include the ESP32 port's pending-word and
scan-purpose flows at commit `fd9ba8fc766f715668bc37fbb5485499def9e52f`, and native
entry screens at `33ddc0763c31b5ae0b6380147ba624a7fc0c9273`. The implementation
here uses its own bounded C word-entry and backup-check controllers. Candidate
selection needs one deliberate tap, and a long passphrase is paged before apply;
the upstream two-step touch selection and overflow issue were not copied.

- <https://github.com/kdmukAI-bot/seedsigner/tree/fd9ba8fc766f715668bc37fbb5485499def9e52f>
- <https://github.com/kdmukAI-bot/seedsigner-lvgl-screens/tree/33ddc0763c31b5ae0b6380147ba624a7fc0c9273>
- <https://github.com/kdmukai/seedsigner-micropython-builder/issues/61>

The photo flow follows the preview, capture and explicit acceptance pattern in
the ESP32 app above. Its incremental frame hashing was compared with
`cam_pipeline_entropy` at `be2d8f55f39932021af3682834a0b498d15747d0`; this board
uses its own fixed-size, domain-separated core hash and caller-owned buffers.
Uniform/repeated frame rejection is a failure check, not an entropy estimate.

- <https://github.com/kdmukAI-bot/esp-camera-pipeline/tree/be2d8f55f39932021af3682834a0b498d15747d0/components/cam_pipeline_entropy>

Power admission uses the AXP2101 at I2C address 0x34. Both USB-C connectors share
USB0_5V, routed through input protection to VCC_5V and PMIC VBUS pin 37. The
read-only status mapping is VBUS-good bit 5 and battery-present bit 3 at 0x00;
discharging is bits 6:5 = 2 at 0x01. Chip ID at 0x03 must equal 0x4a. Sources
were inspected on 2026-11-09. No PMIC power-rail writes are required.

- <https://github.com/waveshareteam/ESP32-P4-WIFI6-Touch-LCD-3.5/blob/main/schematic/ESP32-P4-WIFI6-Touch-LCD-3.5-schematic.pdf>
- <https://github.com/kdmukAI-bot/seedsigner-micropython-builder/blob/a9f865c68b20457692ab4547e3394785114b507f/ports/esp32/XPowersLib/src/XPowersAXP2101.tpp>
