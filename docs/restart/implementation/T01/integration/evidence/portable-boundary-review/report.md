# T01 portable and protocol boundary source review

**No blocker in the read perimeter; final complete gates remain pending.**
Reviewer `/root`, author `/root/a02_sol`, exact candidate
`24b0b58a6ee085d8176a801a7bad5595d39965b7`. The paired
`source-review.json` binds20 files and records the exact limits of this result.
This is source review, not complete T01 or release acceptance.

Read the entire582-line portable capability module and480-line profile tests,
the changed event/protocol behavior and assigned QR/review/session wrappers,
the simulator device-replay transition, the complete current TS protocol and
changed account/route runtime. The portable module keeps reported support,
configuration and availability separate from typed local verification. Missing,
unverified, unavailable or contradictory required observations produce blockers;
the Pi-only boot limitation needs separate verified evidence. Custom custody
requires the matching component configuration and never falls back. Synthetic
observations cannot qualify a production release. This diagnostic API does not
construct consuming authorization or expose a signing backend.

Portable finite limits validate endpoint arithmetic before dimension-wise
intersection. Required dimensions stay positive and bounded; allowed zero
queues/caches remain explicit. Checked expansion rejects overflow before
allocation. These values and host-layout assertions are not physical RAM,
stack, timing or driver measurements. Current metadata is not another portable
JSON parser; original-byte host intake remains separately bounded.

The original strict event reader changes only numeric device revision1→2 and
removes the retired status method. Parsed event grammar, canonical bytes,
authorization ownership, crypto implementation, independent S03 proof and
dependencies remain unchanged. Static Git comparison confirms that only the
assigned test file changes inside the authorization/S03-proof/projector/lock
perimeter. All20 S03 test-family names remain, with only the retired-status
family renamed; its production-unavailable assertion remains. The old universal
boolean-readiness helper is retired rather than used as authorization.

Protocol discovery reports a bounded explicitly synthetic implementation
reference, public-key lookup remains a public identity operation, and signing
still returns `signing_disabled` after diagnostic preview. Dynamic request IDs
are strict ASCII; responses use numeric2. Retired status and numeric1 inputs
reject. QR framing/checksum and response-display grammar remain separately
versioned. The old device replay's enabled/status booleans are replaced by exact
disabled wire2 request/response replay and separate typed profile diagnostics.

The current TS parser checks original request/response bytes before object
validation, preserving duplicate/token/Unicode evidence. Account/route matching
binds current format, explicit method revision/catalog/algorithm, profile,
implementation/limits, transport/codec, custody and public identity. Local
routes remain manual-only; external NIP46 cannot claim a local profile or
custody. Route diagnostics do not supply consent. This review identified the
separately recorded retired-recovery schema/reference inconsistency
T01-ARTIFACT-01; runtime already rejects that recovery type.

All170 original projection objects remain identical, followed by five data-only
profile/case rows; the projector itself is unchanged. Two historical targeted
author command receipts and all paired logs were hash-verified. They retain
their recorded65 source/dirty-diff identity, and are not claimed as fresh root
execution on24. Full stable tests, audits, required floors and integration remain
mandatory. The separate service review owns its three actual findings; this
perimeter does not resolve them or approve the artifact literal, all42 cases,
production provider, protected adoption or any physical device.
