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

The essential flow checks creation, all-position backup quiz, 12/24-word prefix
entry with real pointer events, Back/edit and checksum repair, QR import,
request collection, complete rendering before approval, explicit partial prose
consent, rejection, cancellation, response clearing and lock. This is host evidence;
physical camera, entropy, LCD transfer completion and hardware cleanup still need
separate device measurements.

The ordinary entry paths use 60 taps for 12 words and 119 for the published
24-word test vector. Additional tests exercise repair navigation, explicit
passphrase spaces and multi-page passphrase confirmation, mismatch/retry during
QR backup comparison, and pause/manual frame controls. These are measured tap
counts in the host replay, not claims about human or physical-device speed.

The threshold replay uses the real UI as one participant and two independent
core contexts as its peers. It completes three-device group creation, captures
every outgoing packet, renders group consent, checks a wrong and correct animated
share backup without replacing the identity, restores the share, and completes
two-device signing. The displayed QR bytes are compared with the actual queued
protocol message. Native rendering does not establish optical capture quality.
