# Scoped ctutils remediation review

PASS for candidate `1d10e7a1c2986a5d244807624377e22ad562a110`, tree `99b8ae91552cd33eb08b45c20f98291fb361e387`; no findings. Root reviewed B01 source independently. This is not delivery adoption.

The [pinned RustSec advisory](https://github.com/RustSec/advisory-db/blob/f7b2f6bc663452200bbe639ebb75e0c762b3422b/crates/ctutils/RUSTSEC-2026-0385.md) identifies0.4.4 as patched. Both active locks now select that exact official archive; no other product package changed. The [finite source audit](validation.json) verifies all80 proof members,24 tested-source bindings,12 changed product paths,21 exact archive files,1,892 unchanged other vendor files, unchanged runtime dependency/features/MSRV/licenses and6 original proof inputs. The archive's own dev-only pins remain upstream bytes rather than new product dependencies.

Affected runtime source uses the existing best-effort opaque conversion for mask generation and explicitly handles u128 comparisons on32-bit targets. Root independently built the unmodified official library tests and ran150 cases, including the u128 half-width boundary matrix; [commands and hashes](commands.json) retain the actual outputs. Existing author workspace, independent S03/K01 output comparisons, RISC-V32 compile, clippy and coverage evidence is reused only after verifying frozen product bytes,16 command receipts, original checker inputs, output hashes and unchanged floors100.00/76.70.

Functional tests and compile checks do not prove constant-time machine code on every architecture or any physical security property. Upstream BINSEC results remain upstream claims. Added upstream proptests are preserved but were not run here. The separately authored audit-data gate requires its distinct review; PR44 and actual-main CI must pass on the final candidate before integration can be accepted. Original failed CI and historical reports stay intact.

See [review.json](review.json) for scope, source correspondence, retained reader observations and precise limits. Local independent executable is ignored under `.runtime/`; no production artifact or corpus was added.
