# Product implementation

The [product requirements](product/README.md) establish correctness; this page
describes the selected implementation. The [task graph](../plan/work-items.json)
alone records task status. Historical all-Rust phase plans remain in Git history.

- `crates/nsealr-core` owns portable Rust protocol, transport, review, policy,
  session and cryptographic primitives. Its embedded workspace and target
  toolchain are separate from the host workspace. The current device dispatcher
  still refuses real signing; compiled primitives do not qualify device custody.
- `apps/desktop-simulator` is the independent host Cargo workspace and vector
  replay harness, with its own lockfile and pinned toolchain.
- `apps/bridge`, `packages` and `tools/bridge` own the host applications, private
  modules and sole public TypeScript SDK. See [Bridge boundaries](bridge/architecture.md).
- `apps/pi` retains the independently implemented Python QR/application oracle.
  Its software signing harness is not evidence of physical Pi qualification.
- `protocols/contracts/v1` is the sole authoritative contract artifact. Its
  version is the artifact inventory version, not a new wire-protocol version.
  Python, Rust and TypeScript consumers keep independent implementations.
- `boards` contains experimental profiles, not qualified hardware claims.

Generic board software remains in the separate Nostr-free Board SDK. Hardware,
website and organization metadata retain their separate repository owners.
Custom board availability is not a prerequisite for the product software build.
Retired smartcard implementations and original source identities remain in their
public source histories; they are outside the active product.

Current requirements and navigation are editable at their declared owners.
`plan/evidence-index.json` binds original closed-task evidence byte-for-byte;
the original reviews do not cover later substantive changes to current contracts.
See [testing](testing.md), [reproducibility](reproducible-build.md) and the
[execution handoff](restart/implementation/handoff.md).
