# Fonts

These are the same Inter and JetBrains Mono source assets used by the nSealr
website, distributed under the enclosed SIL Open Font License texts. Inter is
used for body text and JetBrains Mono for headings and controlled secret raster.
Source assets are preserved in `source/`; generated C tables need no font tool at
firmware build time.

Regenerate with `fonttools==4.68.0`, `brotli==1.2.1` and `lv_font_conv@1.5.3`:

```sh
python3 tools/generate_fonts.py --converter /path/to/lv_font_conv
```

The script instantiates weight500, emits uncompressed4-bit LVGL tables, and
converts the ASCII secret font into fixed16×24 alpha cells with explicit pixel
bounds checks. Secret text never passes through LVGL's font cache.

Upstream projects and licenses: <https://github.com/rsms/inter> and
<https://github.com/JetBrains/JetBrainsMono>. No endorsement is implied.
