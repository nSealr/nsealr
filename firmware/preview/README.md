# Native interface preview

This is the actual LVGL screen renderer at 320x480, with a software framebuffer
and pointer input. The preview supplies public fixtures. It does not load keys,
scan a camera, hash/approve/sign an event, clear secret memory or run on the P4.

Build, test pointer navigation and render all screens:

```sh
LVGL_DIR=/path/to/pinned/lvgl python3 tools/ui_preview.py
```

Requires Python 3, a C/C++ compiler, make and CMake >=3.18. Use `--cmake /path/to/cmake`
when CMake is not on PATH. No Python packages, SDL or network fetches are needed.
Obtain LVGL from its upstream repository at the pin below, or reuse the existing
ESP-IDF managed component. The script checks the declared Git/component pin;
it does not authenticate arbitrary local modifications to that source.

Add `--serve` for a local interactive preview at `http://127.0.0.1:8765`.
The browser displays native framebuffer pixels and passes pointer coordinates.
It does not implement the device layout. Click buttons and drag the reader.
Ctrl-C stops the server and native process. No browser opens automatically.

Output is under `.cache/ui-preview/`: `preview.log`, the executable and
`screens/index.html` with fourteen PNGs. The C executable also accepts `--test`,
`--render DIRECTORY` and `--interactive FRAME.ppm` for simple automation.

## Sources and boundaries

- Shared renderer: `firmware/ui/ui.c`; native-only examples/controller/input:
  `firmware/preview/preview.c`. The callback reports user intent to an eventual
  owner; this presentation layer cannot grant signing authority.
- LVGL 9.6.0~1, upstream commit
  `60b614c23c816ca5edc5f2840c9945eff7da0ad4`, from the existing P4 managed component.
  Source: https://github.com/lvgl/lvgl/tree/60b614c23c816ca5edc5f2840c9945eff7da0ad4
  LVGL is MIT; retain its `LICENCE.txt` and `COPYRIGHTS.md` when redistributing it.
- Fonts are LVGL's bundled Montserrat 12/14/16/18/28 and bundled Font Awesome
  symbol glyphs. Their provenance is retained in LVGL's font sources; Montserrat
  and Font Awesome fonts have separate OFL licensing. No SeedSigner artwork is copied.
  Font licenses: https://github.com/JulietaUla/Montserrat/blob/master/OFL.txt and
  https://github.com/FortAwesome/Font-Awesome/blob/5.x/LICENSE.txt
- The result QR uses LVGL's bundled Nayuki encoder (MIT) and encodes only the
  published NIP-19 public identity: https://github.com/nostr-protocol/nips/blob/master/19.md
  It is not a signature, a secret backup, or the nSealr request/response protocol.

All labels are public display data. Mnemonic and secret-QR screens must continue
to use the separately owned secret renderer; ordinary LVGL text/image objects
are not a suitable replacement without a memory-lifetime review.

The review's action/metadata are currently a fixed public-note example. The actual
core must supply validated typed fields and enforce critical-field presentation
before this layout can become a production review adapter. The preview's
`content_seen` flag records reaching the reader's end; it neither proves reading
nor constitutes a core approval token. Unknown kinds and unsupported glyphs are
not parsed or admitted by this fixture controller.

The current typography covers the public Latin example. Production Unicode,
bidirectional text, control-character rendering, secret input, Rust binding,
camera/QR exchange and physical readability remain unqualified. Touch timing
and display/DMA behavior are simulated, not measured on hardware.
