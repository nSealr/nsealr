# Provenance

Native I80/ST7789 wiring, orientation and driver sequence follow the already
pinned LilyGO-Display-IDF b1a1cc54994bf1b417e3bb30c437bbe1036bff7f,
main/display_s3.c, MIT, copyright2024 Shenzhen Xinyuan Electronic Technology.
Its MIT license is retained here as LICENSE-LilyGO-IDF.

The included board pins, extra ST7789 commands and diagnostic debounce helper
are read from the immutable sibling apps/s3-io-probe files. Their LilyGO1cc41eb1
MIT notice and provenance remain there. No TFT_eSPI runtime or LVGL is linked.
Seven-segment diagnostic drawing here is native application code.

The Rust source is the existing public ABI check from that same immutable probe
and one nsealr-core dependency. No second semantic or cryptographic engine is
introduced. ESP-IDF sources/dependencies remain in the isolated build-tool root
with their original licenses and Git pins.
