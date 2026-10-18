# S02 review handoff

Product candidate `b64afa7a8e3dd9e0e155eea55bf402715ddf32ad`, based on
`768e8a35ae541f53f5da9c7bea7bf5c577fb474d`. The coordinator accepted specification
`d9f8c2d4ecdf2efe8c5cd4e87fa4f6f31ca4f3b2`; the baseline reproduction is separately
committed at `9b9da56`. This document requests independent exact-candidate review;
it does not approve or close S02. [Tracking issue](https://github.com/nSealr/nsealr/issues/4).

Draft PR: [#10](https://github.com/nSealr/nsealr/pull/10). After coordinator PR #8
merged, the branch was rebased onto `61b0c39131012c40ff76321bb3650def6e7a9d83`.
`evidence/rebase-reconciliation.json` compares all 670 changed product/dependency
source files with the original tested candidate: zero differences. The new base
changes only restart documentation/task metadata. Original evidence remains under
`evidence/integration/`; the refreshed whole-candidate run is recorded separately
under `evidence/rebased-integration/`, without overwriting the first run.

| Parent acceptance | Evidence and practical limit |
| --- | --- |
| Remove secret Debug/unnecessary Clone/public access | `evidence/baseline-exposure.*` reproduces old public exposure; `secret_boundary.rs` checks fixed redaction, intake, cancellation and checksum failure; 11 external compile-fail doctests deny cloning/raw fields/direct builder/ownership replay. Full candidate command logs are in `evidence/integration/`. |
| Lifetimes/copies/zeroization/internal memory | `secret-flow.md`, owned types, maintained zeroizing scratch, consumed insertion/import and no duplicated IO result. Live wipe checks; no unsafe post-drop observation. No claim for compiler copies, registers, physical erasure or target placement. |
| Maintained candidates, vectors and targets | `crypto-selection.md`, `evidence/dependencies.json`, `source-review.json`, target feature tree, fresh vector/compile/final-link logs and exact pins. Actual device stack/timing/custody remain device gates. |
| Raw BIP340 and NIP44 shared-x; C ABI failure | Fresh `evidence/crypto/vectors.log`, all pinned official vectors plus negative prehash/default-ECDH checks. Uncorrected C RISC-V link fails for the intended floating ABI reason; corrected explicit flags link, with ELF hashes and empty undefined-symbol tables. |
| Entropy provider provenance/failure contract | `entropy-contract.md`: no provider exists in current production source; conversion does not qualify randomness. Source/FFI/weak/runtime tracing and real invocation/fault evidence are required independently at device gates. |

Full `make ci` passes: validators, formatting, clippy default/all features,
workspace/std tests, RISC-V library build, vector harness, advisory/license/source
checks, unchanged coverage floors (core 100.00%, simulator 76.76%), and same-tree
plus cross-path release reproduction. The separately exercised actual core final
link passes without undefined symbols. `evidence/integration/commands.json` records
exact candidate, initial dirty state (only new crypto evidence), environment,
timestamps, commands, exits and log hashes. `evidence/artifact-index.json` binds
underlying logs; `tested-source-hashes.json` permits source reconciliation after
documentation-only integration/rebase.

Remaining admission gates: S03 must replace legacy caller-supplied approval
semantics; K01 must integrate actual key-derived identity/signing and evaluate
backend temporary lifetime; device tasks must demonstrate internal memory,
entropy provenance/failure, stack/RAM, runtime/side channels, boot/custody and
physical input/output. Selected k256's key Drop does not wipe every nonce/scratch
temporary; this is explicit in the selection report and blocks any unsupported
whole-backend erasure promise or real-key admission relying on it. The product
protocol still returns signing disabled.

Useful independent adversarial checks: attempt public secret Clone/raw access and
direct backup construction from a separate crate; format a nested backup result;
retry import with a consumed source; insert a checksum-invalid seed; exercise IO
rejection/early approval and verify no emitted/retained payload; inspect backend
raw-message/ECDH semantics and the preserved actual C ABI failure. All fixtures
are published test material. Do not use production keys or flash link-only ELFs.
