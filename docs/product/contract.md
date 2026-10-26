# nSealr product contract

The current first milestone (maintainer direction 2026-10-25) is the connected
session-only S3 without SE/persistent identity vault, independent session-only
Pi/P4 offline products, and their usable host integration and qualified releases.
Custom Board and its generic embedded SDK remain retained later work.
`packages/sdk` TypeScript remains in phase one. The sole normative set is:

- [Product requirements and device feature catalog](requirements.md): the three phase-one Signer profiles, retained future custom Board/embedded SDK, identity/recovery decisions and complete user journeys.
- [Event review contract](event-review-contract.md): exact public-event field/tag treatment, honest presentation and rejection rules.
- [Profile threat models](threat-models.md): trusted boundaries, attacker assumptions and profile-specific qualification obligations.

Read [the P01 brief](../restart/implementation/P01/brief.md) for source inputs and the
[task graph](../../plan/work-items.json) for its actual review/integration status. These are
requirements for implementation, not a claim that the features or hardware are
already built or qualified. Quantitative device limits, local recovery ergonomics
and exact hardware admission remain the measured gates named by each requirement.

The earlier proposed contract is preserved at input commit
`768e8a35ae541f53f5da9c7bea7bf5c577fb474d`; it is not a second current authority.
Protocol inputs are the pinned Nostr specifications named in the requirements,
event contract and source-backed research. Code demonstrates existing behavior
and must be corrected when it violates these requirements.

[PCB development](../restart/pcb-development.md) owns hardware/tool qualification.
[Development](../restart/development.md) defines specification, implementation, independent
review and evidence. [Client qualification](client-qualification.md) owns actual
interoperability rather than assuming that a simulated exchange qualifies a client.
