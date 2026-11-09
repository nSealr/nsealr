# Native device UI

This executable uses the production `device.c`, LVGL UI and Rust C ABI. Its
software framebuffer reproduces the target RGB565 colors. Secret text and QR
pixels use the same controlled raster code. The host supplies **published test
entropy**, so it must never be used for a real identity. There is no host camera;
the tests feed complete optical transport frames into the actual collector.

Build the native Rust static library, then pass its location and the pinned LVGL
source to the runner:

```sh
cargo build --release --locked -p nsealr-device
python3 tools/ui_preview.py --lvgl /path/to/lvgl-9.6 \
  --rust-library target/release/libnsealr_device.a
```

Use `--cmake /path/to/cmake` when needed. `--core-root` supports an isolated core
worktree during integration. The runner checks the LVGL source identity, builds,
executes the owner/navigation tests and writes actual framebuffer PNGs under
`.cache/ui-preview/screens/`. `--serve` starts a loopback viewer; its browser only
forwards pointer input to the native executable and displays its pixels.

The essential flow checks creation, backup, clear and recovery, QR import,
request collection, complete rendering before approval, explicit partial prose
consent, rejection, cancellation, response clearing and lock. This is host evidence;
physical camera, entropy, LCD transfer completion and hardware cleanup still need
separate device measurements.
