# P01 — Product contract and profile threat-model brief

Author: `/root`. Input: `nSealr/nsealr` `768e8a35ae541f53f5da9c7bea7bf5c577fb474d`. The proposed `product-contract.md`, pinned Nostr specifications and profile source inventory are inputs; implementation and hardware readiness remain unclaimed.

## Outcome

Accept a coherent first-release contract for ESP32 without SE, Pi QR, P4 QR, custom Signer and independent Board SDK. Every promise names a threat, trust boundary, observable behavior and implementation/qualification owner. First public releases are independent. This is a specification milestone; physical measurements belong to the task owning the device claim.

## Owned files and decisions

Own `docs/restart/product-contract.md`, product/threat documents under this directory and their traceability; edit other architecture/navigation files only to reconcile an accepted decision. Do not change implementation acceptance or remove release blockers to make the product appear ready.

1. Adopt or explicitly revise the public catalog (kinds 0, 1, 3, 5, 6, 7, 10002), one active identity, full operation review and rejection of unknown/opaque signing. Keep relay/HTTP authentication separately qualified.
2. Decide the first connected release's DM obligation. Keep NIP-44 primitive permission distinct from an authenticated message context; map NIP-17/59 context and client-order feasibility to C02. Reject an incompatible client workflow rather than silently add blind signing.
3. Specify local generation, import, backup, recovery and key-changing flows. Compare direct NIP-19 backup against inherited mnemonic/custom formats and NIP-49; select a reversible product direction with source-backed reasons. Actual ergonomics and screen/input evidence remain the exact-profile gate. Do not announce an untested backup procedure as safe or usable.
4. Build per-profile threat models: malicious host/client/relay, hostile optical/USB input, physical access/substitution, firmware/debug/boot boundaries, entropy and persistent-state failures, recovery copies and supply-chain assumptions.
5. Separate fixed semantic requirements from measured capacities: limits must be finite and enforced before expensive work; exact byte/frame/time maxima are established and versioned in T01/Q01 and target qualification. No arbitrary value becomes a performance promise.
6. Record first hardware candidates versus admitted exact assemblies. Read actual manuals/board sources before selecting a candidate; admission needs D01/QP01/QP02/H04 evidence. If P01 cannot close an actual required product decision, keep it running with its precise next experiment.

## Evidence and acceptance

For every requirement include success/failure behavior, relevant profiles, implementation owner and actual qualification gate. Review against pinned protocol texts and current code as distinct sources: code proves existing behavior, not correctness. Walk through initialize/pair/sign/message/offline/lock/recover/update and failure transitions. Independent review must assess product coherence and threat adequacy before acceptance.

Do not test whether prose exists. Use source-backed decision records and concrete protocol/user-flow examples. New implementation tests are owned by S01/S02/S03/K01/C02 and device tasks. No real key or physical device is needed to review the specification; all physical/release claims remain open.
