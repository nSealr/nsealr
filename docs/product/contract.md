# nSealr product contract

The first-release contract has one normative set of requirements:

- [Product requirements and device feature catalog](requirements.md): four Signer profiles, generic Board SDK, identity/recovery decisions and complete user journeys.
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
