# External Nostr interoperability handoff

This handoff belongs to A02 candidate
`daf8ba03a9eb820f99b0f1bf5c4f553a7961e008`. It carries existing requirements
and source-bound local evidence into the consolidated layout. It is not a new
protocol specification, named-client qualification or hardware-signing claim.

The current normative owner is candidate `docs/product/client-qualification.md`
with `docs/product/contract.md`, `requirements.md`, `event-review-contract.md`
and `threat-models.md`. Their P01 source bytes remain frozen separately and their
current copies differ only by declared links. NIPs are pinned there at
`a79e21d90fce5465b50ef385dd368bba99ec4a0b`. Retained BIP340 and NIP44 official
source/vector provenance is in the existing `research/2026-10-13/crypto` source
records and S02 evidence. The migration preserves those bytes and licenses; it
does not silently replace requirements with whatever current code happens to do.
Before later qualification, reconcile any newer normative revision explicitly.

| Boundary | Retained local proof | Next real-session obligation |
| --- | --- | --- |
| NIP-01 event serialization/id and BIP340 signatures | Rust core/host, independent Python/libsecp256k1 Pi oracle, TypeScript vectors and complete request/review/sign/verify differential integration | Send approved event from an identified client to an identified device, compare reviewed bytes with event/hash, verify signature and expected account key independently |
| NIP-07 browser provider | Bridge provider, extension origin/tab/frame permission controls, browser export/bundle and isolated packed SDK consumers | Exact installed browser/extension/client versions; fresh permissions, account identity, reject/cancel/disconnect, cross-origin isolation and truthful device review |
| NIP-46 client/transport | Corrected metadata-v1, expected user identity separate from transport peer, auth/queue/replay/cancellation and terminal error cases | Exact client/relay/device tuple; fresh pairing, expected-user-key confirmation, reconnect/revocation, changed peer/user keys, late/duplicate responses and one-use authorization |
| NIP-44 v2 and related encoding/crypto | Retained independent official vector checks, parser/length/rejection cases and declared encoding contracts | Advertised payload limits, checked arithmetic, invalid encoding rejection, exact encrypt/decrypt call sequence and independently checked response identity |
| NIP-17/59 messaging context | Existing requirements distinguish primitives from authenticated full-message review | Trace actual client calls; bind reviewed plaintext/recipient to the encrypted seal before signature; refuse a promise that cannot be established from supplied context |
| Unsupported and retired operations | Explicit smartcard surface removal/route rejection and existing validation negatives | Test unsupported NIP-04 and other unadvertised requests without weakening validation; record the affected workflow as unsupported |

The inherited NIP-46 implementation is a host client/transport path. It is not a
hardware-backed signing server, and host routing/approval is not device consent.
The simulator still refuses signing. Disposable test identities and dev-signer
harnesses are excluded from the public SDK production bundle and cannot establish
production custody. Pi reference signing remains an independent oracle pending
QP01/Q02 and actual physical review integration.

P01's source-bound candidate list starts with noStrudel
`0476cad1944dcc999da5eae21ea5224e27014042` (package 1.1.0) and Coracle
`8f4d34cc16bfb4380208923d26307fab561a867d` (package 0.6.41).
These are historical test-selection inputs, not a claim about current deployed
versions or compatibility. Pin full lockfiles/builds and exact Chromium/Firefox,
extension, relay and device versions for each future session. Later client
selection changes require source reconciliation rather than reusing these pins
as proof of a newer deployment.

For each named client/profile, record fresh pairing, public-key confirmation,
kind-1 post, rejection, disconnect during review, late/repeated response, changed
peer/user identity, oversize input, unsupported NIP-04 and the agreed NIP-44/DM
workflow. Capture the actual operation/account reviewed on the device, approval
consumption, output bytes and independent verification. Record prompt usability
and whether a person could identify what they authorized. No host-provided
application name is a hardware-attested website identity.

P02 owns the qualification matrix; C01/C02 own connected integration, while
QH01 and each optical release task own their optical path. S03/S04 and later
device-boundary work must reach reviewed adoption before their properties can
be included in a session claim. Their held branch contents are not in this
candidate. The Firefox service-worker manifest limitation remains a named
C01/P02 gate. One skipped relay case and absent installed-browser/device tests
remain visible in the full suite's [skip record](execution/cold-product-03/evidence/suites/skips.json).

The [named case maps](execution/case-reconciliation-execution-01/case-correspondence.json)
and [Bridge case map](execution/bridge-named-execution-02/case-correspondence.json)
bind local checks to source identities. They preserve local behavioral evidence
only. A failing real DM workflow blocks that advertised DM guarantee; it cannot
be relabeled successful because local fixtures pass, nor does it automatically
block a separately qualified public-event-only profile.
