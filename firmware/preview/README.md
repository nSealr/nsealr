# Native device UI

This executable runs the production controller, LVGL UI and Rust C ABI with real
pointer events. Its framebuffer uses the target RGB565 colors and controlled
secret raster. The host has published test entropy, a synthetic camera picture
and simulated battery status. Never use it for a real identity. Optical frames
are fed into the actual collector; no host test proves physical camera, power,
entropy, display transfer or memory cleanup behavior.

```sh
cargo build --release --locked -p nsealr-device
python3 tools/ui_preview.py --lvgl /path/to/lvgl-9.6 \
  --rust-library target/release/libnsealr_device.a
```

Use `--cmake /path/to/cmake` when needed. `--core-root` supports an isolated core
worktree. The runner checks the LVGL pin, builds, replays the flows and writes
framebuffer PNGs and source identities under `.cache/ui-preview/`. `--serve`
opens a loopback viewer that forwards pointer events to the native executable.

The replay covers load-first and scan-first signing, wrong-key refusal, fixed
request expiry, idle clear, cancellation, explicit session clear and simulated
power faults. Camera checks cover capture, retake, acceptance, cancellation and
idle cleanup. Dice entry checks edits and independent 50/100-roll public-key
vectors. Backup checks cover every position for all five BIP39 word counts,
supported QR menus, paper-copy grid navigation and wrong/correct scan-back.

Recovery checks include prefix entry, Back/edit, checksum repair, controlled
passphrase editing, spaces, Unicode, account changes and complete review before
use. The published 12/24-word fixtures take 60/119 entry taps; these are host
replay counts, not measured human speed. Nostr checks retain complete rendered
review, explicit partial prose consent, signing, rejection and returned QR bytes.

Threshold checks use the UI as one participant and two core peers. They complete
group setup, every exchange packet, share backup/check/recovery, public-record
QR, two-device signing, and lost-share repair followed by signing with either
survivor. The native file adapter checks explicit save/read-back/restore, absent
media, overwrite refusal, missing/oversize input and error-buffer clearing. It
uses public test data in `.cache/ui-preview/NSEALR.NSR` and removes it afterward.
