# Source disposition — candidate for independent review

Date: 2026-10-18. Inputs and observation limits are in `repository-observations.json` and `consumer-observations.json`. These decisions prepare A02; they do not move source or archive repositories. S01/S02 candidate source must be reconciled after those tasks integrate.

## Repository boundaries

Keep five active release owners: `nsealr` (Nostr semantics/applications/Bridge/client SDK), `hardware` (generic electronics/mechanics/test data), `board-sdk` (generic firmware services/lifecycle/examples), `website` (release-derived guidance) and `.github` (community navigation). Different chips need distinct target manifests/apps, not separate permanently duplicated semantic engines or one repository per chip.

Keep the explicit name `board-sdk`; a client-facing TypeScript SDK is a different consumer inside `nsealr`. The generic SDK must build a standalone non-Nostr example without importing the Signer. Hardware and SDK versions carry compatibility records; physical design files do not belong in the Nostr crate tree.

## Module decisions

| Current source / module | Disposition and destination | Required proof / reason |
| --- | --- | --- |
| nsealr `protocol.rs`, serial/QR envelopes | Repair/select into versioned Nostr contracts and bounded adapters | Existing parsing and fixture behavior are source evidence, not a frozen v0 API. New exact identity/canonicalization/limits and negative vectors own correctness. |
| nsealr `policy/approval_gate.rs`, signing/policy-change review | Replace defective reusable authority; retain useful review fixtures | S03 proves one-use operation/account/session binding, invalidation and races. Persistent automation is deferred F01, not an implicit base feature. |
| nsealr `session/`, `nip19`, BIP39/SeedQR | Select repaired owned-secret boundaries after S02; keep optional compatibility isolated | Preserve independent encoding/checksum/recovery vectors. First native identity is one scalar; no requirement to expose every historical source format or eight simultaneous accounts. |
| nsealr custom `hash.rs` | Replace with maintained qualified implementation through S02 | Independent known answers, no_std/link and actual ownership/scratch review; no private crypto solely for zero dependency count. |
| nsealr review/display/buttons/text/Unicode | Select and repair for common review semantics; target adapters remain separate | K01 event-review fixtures, hostile controls/long content, actual screen/input proof. A host test does not make a peripheral trusted. |
| nsealr desktop simulator | Retain as host conformance and regression harness | Standalone fixture path, independent expected values and meaningful negative cases; keep signing-disabled source honest until real engine lands. |
| nsealr inherited board JSONs | Replace or revise as exact qualified profile manifests | References to retired apps, unverified pins and disabled/unpopulated radio equivalence are not guarantees. D01/QP01/QP02/H04 own admission. |
| nsealr independent official crypto vectors/research | Retain licensed vectors, provenance and bounded executable probes | BIP340 source license retained; NIP44 fixture redistribution must honor its own rights. A successful vector set is not device entropy/timing qualification. |
| companion `nip46`, `transport`, `protocol`, `framing` | Import selected S01-corrected modules into nsealr | Keep strict identity, duplicates/queue bounds/cancellation and target-specific regressions. Coordinate metadata v1 fixtures and all consumers atomically; no experimental v0 compatibility layer. |
| companion `browser-provider`, `client`, browser extension, service | Select Bridge/client integrations, simplify one public SDK and explicit entry points | Browser/Node bundling, origins/native messaging, service permissions and named-client tests. Host permission is not device approval. |
| companion `core`, `qr`, `review`, `policy` | Retain only host-owned validation/transport/presentation helpers | Device remains normative for keys/canonical review/authorization. Host policy labels/counters never substitute for device enforcement. Avoid permanent duplicate Nostr signing engines. |
| companion `fixtures`, CLI, smoke/example apps | Select independent regression/consumer checks; reduce public package surface | Preserve useful browser/Node consumer checks and independently computed results; update new versioned contracts, replace prose-generation drift with correct reviewed API output. |
| companion smartcard and smartcard-simulator modules | Retire from active package graph after verified disposition | Smartcard repository remains a public research archive. Do not require retired APDU examples for a Board/Signer release; keep historical tests/reference in Git. |
| Raspberry Python signer/crypto | Retain as an independent differential oracle, replace normative production semantics with common Rust engine | Independent expected signatures/recovery results remain valuable; do not maintain two permanent normative engines. A PyO3 boundary is not isolation. |
| Raspberry camera/ST7789/GPIO/UI/image probes | Select adapters and qualified minimal image tooling | Exact Pi kit, driver/power/boot/radio and secret-copy checks; CLI `--approve` or file-backed frames are test harnesses, not physical authority. |
| specs schemas and vectors | Select beside owned implementation in nsealr; keep provenance and CC0 notice | Preserve independently useful canonical/negative oracles, repair incorrect expectations and version contracts explicitly. Do not keep a separate permanent schema owner just to preserve legacy imports. |
| lab integration helpers, release/probe checks | Import selected CC0 tooling after privacy/source review | R00 proves actual launcher/layout/provenance problems and corrected bounded tooling. Preserve complete integration assertions; do not copy private history wholesale. |
| workspace bootstrap/control/plans | Replace obsolete bootstrap; move canonical execution to nsealr through A02 | R00 owns clean bootstrap. Preserve private evidence and backup access until verified handoff; dated research remains historical, never another live status authority. |
| hardware existing native CAD/BOM/OS/security notes | Revalidate facts and design; retain only useful licensed reference | Root license is CERN-OHL-P-2.0, subject to selected-file notices. H01–H09 inspect actual components/pins/layout and measure assemblies; no inherited BOM is approved. |
| old private hardware archive | Reference only; no blanket import permission inferred | No root license was found in tracked sources. Keep private; new design uses independently reviewed component facts and appropriately licensed assets. Selected copied content needs a resolved rights basis first. |
| new board-sdk foundation | Retain MIT foundation; implement only used generic APIs/examples | B01/B02/B03, standalone consumer and lifecycle proof. No empty abstractions or Nostr event imports. |
| website | Repair navigation/status; generate compatibility from qualified artifacts | Build/link tests and actual supported release data; no implied qualified hardware from a marketing table. |
| .github | Retain concise navigation/contribution metadata | Links reflect actual active/migration/archive state and security-reporting owner. |

## Consumers, packages and rights

At observation time the public npm registry returned 404 for all twenty names declared by the companion workspace/apps/packages, including `@nsealr/sdk`. Bounded authenticated GitHub search for that SDK reference returned only organization-owned repositories. This is not proof of zero external or unpublished consumers, ownership of the npm scope, or absence of installations from Git/tarballs. Before publishing, verify package ownership and actual release scope. No public repository tag/release was observed in this inventory; the private workspace has one draft evidence release, which is not a product release.

Internal consumers are the companion apps/tests, lab cross-repository integration, Raspberry/spec fixture loaders, existing workspace scripts and website/repository links. Their new contract/imports must migrate together in A02. S01 also changes metadata fixture versions in its CLI/fixture consumers; sibling specs and any complete snapshots need an explicit synchronized transition. R00's pinned baseline remains historical rather than silently following a moving main.

Software roots are MIT except specs/lab CC0; hardware has CERN-OHL-P-2.0. Private workspace and the legacy private hardware archive lack a root license in this inventory. Nested third-party files retain their own notices; a root license does not relicense Trezor/TROPIC/manual/fixture material. These observations are source/provenance checks, not legal clearance for arbitrary copying. Preserve licenses on actual selected imports and do not expose private research by importing its Git history.

## Archive admission

For each migration source: pin latest selected input, enumerate retained/replaced/retired content, preserve recoverable history, rehearse import and consumer updates in isolation, pass affected behavior/integration, independently review exact candidate, update old/new navigation, then archive. A named replacement module without an executed working consumer is insufficient. Pi/P4 functionality and independent oracles remain active through parity; no repository is archived by this A01 candidate.

The source graph currently includes twelve repositories because `board-sdk` was created during restart. The target of five active release owners remains justified by independent consumers, qualification and release responsibility. There is no intrinsic need to preserve eleven historical product boundaries.
