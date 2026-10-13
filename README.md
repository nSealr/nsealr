# nSealr

Open-source signing tools for Nostr, with a separate programmable security-board platform.

**Status: restart and engineering validation. No production-ready device release is claimed.**
This is the original `nSealr/firmware` repository, renamed without replacing its history or community stars.

The first user problem is simple: use Nostr clients without giving them your private key, while understanding and approving what the device signs. nSealr Signer owns key custody and authorization; nSealr Bridge connects clients and transports requests. The Bridge cannot grant device approval.

## Retained device paths

| Path | Purpose | Qualification needed |
| --- | --- | --- |
| Commercial ESP32, no secure element | Accessible connected signer | Exact board, storage, boot/update, display and input |
| Raspberry Pi kit | Offline QR signer | Exact model/image, camera/display, key lifetime and radio policy |
| ESP32-P4 kit | Embedded offline QR signer | Exact board/silicon, camera pipeline, memory and radio policy |
| Custom nSealr Board | Signer plus an independent firmware-development platform | Component decisions, PCB, custody, lifecycle and physical validation |

Connected and Offline describe interaction modes, **not security levels**. Each release declares its custody, active interfaces, boot protection, review path and recovery behavior. The first three paths can ship independently of custom-board fabrication.

## What is here today

- `crates/nsealr-core`: a portable Rust core with bounded protocol, review and session foundations. Its authorization and secret-handling design is under revalidation.
- `apps/desktop-simulator`: a host conformance harness. The current Rust path deliberately returns `signing_disabled`; it is not a working MCU signer.
- `boards/`, `tests/`, `ci/`, `scripts/`: experimental profiles, fixtures and checks inherited from the measured baseline. A profile file is not hardware qualification.
- `docs/restart/`: the accepted restart direction, migration gates and resumable work graph.

Host and Pi code currently remain in their original repositories until selected code has migrated and passed its gates. We are consolidating ownership, not claiming consolidation has already happened.

Start with [the restart plan](docs/restart/README.md), [architecture](docs/restart/architecture.md), [repository mapping](docs/restart/repositories.md) and [agent instructions](AGENTS.md). Earlier phase documents describe the historical implementation; they do not freeze the new architecture.

## Build the existing Rust baseline

Install the toolchain pinned in `rust-toolchain.toml`, then run:

```sh
cargo test --workspace
cargo test -p nsealr-core --features std
cargo fmt --all --check
python3 scripts/verify_repo.py
```

`make ci` adds target compilation, lint, dependency, coverage and reproducibility gates. Host tests and a compiled core library do not demonstrate a complete device application or physical security.

## Project boundaries

- [nsealr](https://github.com/nSealr/nsealr): Signer, Bridge, Nostr contracts and software verification.
- [hardware](https://github.com/nSealr/hardware): generic board, mechanics, component evidence and manufacturing tests.
- [board-sdk](https://github.com/nSealr/board-sdk): generic board software and lifecycle tooling; initial development foundation.
- [website](https://github.com/nSealr/website): user/developer documentation and release-derived compatibility.
- [.github](https://github.com/nSealr/.github): organization and contribution metadata.

A custom board can host independently developed authentication, SSH or wallet firmware. Those applications each require their own implementation and qualification; an SDK does not provide multi-application isolation or native support for every cryptographic algorithm.

## License

MIT; see [LICENSE](LICENSE). Imported third-party material retains its own notices and license. Hardware licensing is owned by the hardware repository.
