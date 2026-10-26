# nSealr

Open-source Nostr signing devices and their host software. Device signing and
local authorization belong to the shared Rust engine. Bridge connects clients
and transports requests; it cannot approve a device action.

**In development. No device release or real-identity custody is qualified.**
See the [current delivery state](docs/restart/README.md) for verified results,
limits, blockers and the next delivery. [Requirements](docs/product/requirements.md)
and [plan/work-items.json](plan/work-items.json) define the complete scope.

## First milestone

| Product | Scope | Current limit |
| --- | --- | --- |
| Connected S3 | Non-touch LILYGO T-Display-S3, display/two buttons, USB only; no SE or persistent vault | Public-fixture signing exercised; entropy-source and session recovery/lifecycle gates open |
| Offline Pi | Session-only custody and manual QR on the identified kit | Image/adapter work exists; physical boot, custody and full optical qualification open |
| Offline P4 | Session-only custody, camera/display and manual QR | Public-fixture signing exercised; complete local custody, offline conditions and release open |

The three releases are independent. The agreed catalog, connected serving,
NIP-44/NIP-17/59 and the TypeScript SDK remain in scope; kind-1 fixtures do not
complete the milestone. Custom Board and its generic embedded Board SDK are
deferred. The USB-only S3 requires no battery.

## Source and responsibilities

- [crates/nsealr-core](crates/nsealr-core): shared device engine, bounded parsing,
  review, authorization and signing. Oracles and fixtures are independent
  development tools, not another product signing engine.
- [apps/s3-native](apps/s3-native), [apps/p4](apps/p4), [apps/pi](apps/pi):
  device adapters and target-specific build/qualification work.
- [apps/bridge](apps/bridge): CLI, local service and browser integration.
- [packages/sdk](packages/sdk): public TypeScript browser/Node entry points;
  other workspace packages implement client, protocol and transport layers.
- [docs/product](docs/product): requirements, threat models and compatibility.
  [docs/restart](docs/restart/README.md) links current work to source-bound evidence.

Host NIP-46 transport keys have a separate lifecycle from user identity keys.
Software-signing utilities and synthetic fixtures are test tools; their presence
does not qualify a device or user installer.

## Develop and verify

Use the public [pinned Linux bootstrap](tools/baseline/README.md), then:

    pnpm install --frozen-lockfile
    make ci

This checks software, contracts, packed consumers and integration. It does not
test installed browsers, live relays, hardware, custody or recovery. Each profile
requires its own target builds and finite physical batches.
[P4 instructions](apps/p4/README.md) identify its engineering build scope.

No production installer or supported private-key workflow is available yet.
Matched release artifacts and instructions require the D03, Q04 or Q05 gates.

## Project and contribution

[nsealr](https://github.com/nSealr/nsealr) owns Signer/Bridge and Nostr semantics.
[hardware](https://github.com/nSealr/hardware) and
[board-sdk](https://github.com/nSealr/board-sdk) retain the deferred platform;
[website](https://github.com/nSealr/website) presents the project.
[Contribution](https://github.com/nSealr/.github/blob/main/CONTRIBUTING.md) and
[security](https://github.com/nSealr/.github/blob/main/SECURITY.md) policies are shared.

This is the renamed original firmware repository; public history is preserved.

## License

MIT, with third-party notices retained; see [LICENSE](LICENSE).
