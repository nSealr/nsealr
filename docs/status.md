# Development status

2026-11-09: clean product restart. No release is available.

The prior implementation is preserved in a separate private archive. The new
history currently contains:

- Portable Rust core, threshold and allocator, recovered without production logic
  changes. 349 executable and 16 compile-fail checks passed, alongside strict
  Clippy, an optimized RISC-V library build and independent threshold verification.
  Source, commands and limits: [core provenance](core-provenance.md).
- Shared native LVGL screens and a desktop framebuffer preview. Fourteen screens
  render; pointer-driven navigation, rejection, cancellation and reader checks
  pass. The displayed public QR was independently decoded. Source and commands:
  [native preview](../firmware/preview/README.md).

These are separate software foundations. The preview does not load keys, scan a
camera or sign. Its partial-review choice is not connected to the Rust approval
engine, which retains its previous complete-traversal behavior. The normal board
firmware has not been replaced by this restart.

Next acceptance: create/import -> backup -> clear -> recover the same identity,
then one complete client request -> device review -> approve/reject -> independently
verified result. This is an internal milestone, not the finished product.

Public/private workflow coverage, threshold ceremonies and physical qualification
remain release work. Report actual results here as candidates are integrated;
do not infer completeness from commit or test counts.
