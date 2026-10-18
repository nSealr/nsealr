# Product verification

Use the [pinned cold bootstrap](../tools/baseline/README.md), then run `make ci`.
The full gate executes source/evidence integrity and the complete task validator,
contract inventory tamper controls, independent Python contract tests, Rust
formatting/clippy/default and std tests/device-target compilation, the separate
host oracle, dependency audit, both coverage floors and reproducible builds.
It also executes Bridge build/type/unit and packed Node/browser/type consumers,
Pi checks, selected integration helper tests, replacement product guardrails and
one uninterrupted seventeen-step product integration.

`make rust-ci`, `make bridge-ci`, `make pi-ci`, `make contract-ci` and
`make integration` expose the same gates for focused work. Host Rust commands
use `--manifest-path apps/desktop-simulator/Cargo.toml`; the root workspace is
the embedded graph. Both read the authoritative `protocols/contracts/v1`
artifact. No sibling repository or copied fixture fallback is required.

The generated Rust fixture projections preserve input values and expected
answers from the artifact; they do not compute the expected result with the
implementation under test. Python contract/Pi implementations stay independent.
Every retained consumer scope is checked; an unclassified artifact category
fails the applicable coverage check. The historical before/after case ledger
accounts explicitly for retired card cases and adapted layout/guardrail cases.

The default live-relay test remains visibly skipped. Installed Chromium/Firefox,
attached boards, camera/display/GPIO, real review/approval, provisioning and
physical security need separate evidence. Optional browser/serial helper unit
tests run in normal CI; their success does not claim those resources were used.
External hardware repository regression is separate from product CI. See
[Bridge testing](bridge/testing.md) for the packed SDK boundary.
