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

Recovery interaction references also include the ESP32 port's pending-word and
scan-purpose flows at commit `fd9ba8fc766f715668bc37fbb5485499def9e52f`, and native
entry screens at `33ddc0763c31b5ae0b6380147ba624a7fc0c9273`. The implementation
here uses its own bounded C word-entry and backup-check controllers. Candidate
selection needs one deliberate tap, and a long passphrase is paged before apply;
the upstream two-step touch selection and overflow issue were not copied.

- <https://github.com/kdmukAI-bot/seedsigner/tree/fd9ba8fc766f715668bc37fbb5485499def9e52f>
- <https://github.com/kdmukAI-bot/seedsigner-lvgl-screens/tree/33ddc0763c31b5ae0b6380147ba624a7fc0c9273>
- <https://github.com/kdmukai/seedsigner-micropython-builder/issues/61>
