# Development rules

Build one ESP32-P4 offline Nostr signer. Follow docs/product.md and keep
docs/status.md accurate. Connected devices, Pi and custom boards are later work.

Use Rust for keys, event semantics, authorization and cryptography; C/ESP-IDF/LVGL
for the existing hardware and native UI; TypeScript for the companion. Prefer
deletion and existing libraries to new abstractions. Preserve dependency pins,
licenses, independent vectors and security failure handling when moving code.

Inspect callers before editing. Work on branches. Keep edits and evidence scoped
to the assigned files. Do not copy private archives, real keys, board identifiers,
credentials, session transcripts or historical process logs into this repository.

Tests must exercise behavior or trust boundaries, not merely mirror code. Keep
test fixtures independent from production logic. Review public source and images
before publishing. Host/simulator/build results are not physical device results.
Do not claim a release, audit or hardware qualification that has not occurred.

No raw-ID signing fallback. The device binds the locally displayed supported
operation to its complete immutable event and approval. Secret rendering has
separate ownership and cleanup from ordinary LVGL labels. Cancellation and stale
requests must never reuse authority, outputs or threshold nonces.
