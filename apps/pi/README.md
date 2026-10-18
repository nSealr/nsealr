# Pi QR vault reference and adapters

This component owns the retained Python reference harness, Pi-facing adapters,
and independent signing/review comparisons in the nSealr integration repository.
It is not a qualified Pi image or a second approved production signing engine.
K01 owns the portable engine; QP01 establishes the kit/image feasibility; Q02 owns
shared-engine Pi integration and physical qualification in the [task plan](../../plan/work-items.json).

The `nsealr-account-descriptor-v0` route is `raspberry_qr_vault` with policy
`policy-manual-only-qr-vault` and `persistent_grants: false`. Each signing request
requires local trusted review and physical approval. Imported sources live only
in the current RAM session; Python wiping is best effort and does not establish
physical power-cycle or production secret-custody guarantees.

Run `make -C apps/pi ci` from the repository root using the pinned Python
environment. The component tests consume the single [contract artifact](../../protocols/contracts/v1/)
and exercise independent Python/libsecp256k1 behavior plus injected camera,
display and GPIO boundaries. Optional physical drivers are not a main build
prerequisite. A successful safe probe is setup evidence, not full qualification.

See [architecture](docs/architecture.md), [testing](docs/testing.md), and the
[stateless image profile](os/stateless-qr-vault-profile.md) for retained behavior
and explicit physical limitations. Current requirements are in [docs/product](../../docs/product/).
