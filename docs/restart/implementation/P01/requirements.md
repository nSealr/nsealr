# First-release product requirements

Date: 2026-10-18. These requirements define the first-release product contract. Source and protocol inputs remain pinned in the parent brief. The task graph records actual independent acceptance and integration; this document does not announce implemented features or qualified hardware.

## Portfolio and user outcome

The first user is a Nostr user who wants the ordinary client to operate without holding the identity secret, and who can understand and approve each supported action on a separate device. The second independent user is a firmware author who wants a programmable security-oriented board without importing Nostr.

Retain four separately qualified Signer profiles: commercial ESP32 without SE over USB, Pi over optical QR, ESP32-P4 over optical QR, and the custom Board's initially connected Signer. Retain generic Board + SDK as a separate release. Smartcards are retired. A profile release never waits for qualification of an unrelated profile. These are capability/threat profiles, not grades on a universal security scale.

## Semantic requirements

| ID | Observable requirement | Implementation / actual admission |
| --- | --- | --- |
| PROD-01 | One active identity per unlocked session. Derive the full public key from actual custody. An account change cancels pending work and requires client rebinding. Device, user and NIP-46 transport identities are distinct. | S01/S02/K01; C01/QH01 and each profile's device/release tests |
| PROD-02 | Native new identities use a valid uniformly sampled secp256k1 scalar from a qualified fallible entropy provider. No timestamp, guessed entropy, deterministic test source or unqualified fallback is permitted. Scalar rejection and provider failure are distinct outcomes. | S02/K01; actual entropy trace and fault tests in V01/V02/V03/Q02/Q03/B02/B03 |
| PROD-03 | Native recovery data is the one identity scalar in NIP-19 `nsec` form. Create/import/export it locally, in a separate conspicuous recovery flow. Bridge, browser and desktop helpers never receive it as part of normal operation or as a required onboarding step. | S02; D02, Q01/Q02/Q03, S04/V02/V03; profile recovery and independent UI tests |
| PROD-04 | The signer validates and owns the exact canonical event, full review state and physical consent. The first execution attempt consumes one operation-bound authorization. Cancel, lock, expiry, reset and identity/policy change invalidate it. A bounded cached-result retransmission cannot execute signing again. | S03/K01; AUTH-01–05 and actual device/transport negative tests |
| PROD-05 | Every signed field/tag is inspectable with honest semantics. The exact field/tag rules in [event review](event-review-contract.md) distinguish interpreted data, completely shown uninterpreted data and rejection. Unsupported kinds or ambiguous/unrenderable input reject before authorization. Never fall back to blind signing. Host names, previews and origins are not authenticated by the device merely because supplied. | S03/K01; renderer fixtures, actual screens and client workflows |
| PROD-06 | The first common public catalog is get-public-key plus kinds 0, 1, 3, 5, 6, 7 and 10002, as precisely scoped below. | K01 and per-profile UI, C01/QH01 and client qualification |
| PROD-07 | Connected first public releases include bounded NIP-44 and the admitted NIP-17/59 one-to-one text-message workflow, including locally reviewed DM-relay setup/replacement (10050) and NIP-42 when the selected relay requires it. Primitive encrypt/decrypt permission is distinct from verified-message review. An incompatible client call sequence is explicitly unsupported. No NIP-04 fallback or opaque seal signing. | C02; D03 and V03/S05/custom release |
| PROD-08 | Initial Pi/P4 profiles are manual, session-only signers. Local recovery import is separate from an operation QR. Power loss requires local reload. No message encryption/decryption or persistent/automatic grants in their first release. | Q01/QH01/Q02/Q03; Q04/Q05 |
| PROD-09 | A versioned profile manifest declares finite input/content/tag/frame bounds, cumulative retained bytes, pending counts, parse work, deadlines and output limits. Enforcement precedes unbounded allocation/expensive processing. Exact maxima are accepted from measured feasibility, not protocol maxima or inherited defaults. | S01/T01/K01/Q01/QH01; QP01/QP02 and each target measurement |
| PROD-10 | The receiver independently validates response correlation, expected user identity, canonical ID and signature. Publication is reported separately from successful signing. A connect acknowledgement or selected origin label never grants device consent. | S01/C01/QH01; V01/V03/Q02/Q03 |
| PROD-11 | Each profile declares boot, firmware authenticity enforcement, update/recovery, debug, persistence, PIN behavior, active interfaces and physical-attacker limits. Replacing firmware/ownership cannot silently inherit privileged secret state. Unsupported hardware properties are not emulated by successful flags. | D01/D02, QP01/QP02/Q02/Q03, S04/H02/H02S/B02/V02/V03 and release |
| PROD-12 | The generic Board SDK provides documented peripheral, entropy, custody, storage, input/display and lifecycle boundaries without Nostr event schemas. A standalone non-Nostr example is independently built and run. Initially one trusted firmware image, with no hostile-app isolation claim. | B01/B02/B03, independently of Signer qualification |

## Exact public-event catalog and review

| Kind / action | Required presentation and rejection behavior |
| --- | --- |
| Public key | Disclose the selected full public key under the local/session rule. This is neither a login authorization nor proof of publication. |
| 1: post, reply, quote | Text and all tags; identify root/reply/mention/quote references. Unverified referenced content is marked unverified. Non-kind-1 reply conventions are outside this catalog. |
| 0: profile | Every submitted metadata field and the replacement effect. Do not render an avatar/name as verified identity. |
| 3: follow list | The whole submitted list and replacement effect. A trustworthy add/remove diff needs independently established prior state; no such state is assumed. |
| 7: reaction | Reaction value, target and all tags. Target author/content is verified only from checked original-event evidence. |
| 6: kind-1 repost | Target and included original-event evidence, with its ID/signature/author checked before verified display. Generic kind-16 reposts remain unsupported. |
| 5: deletion request | Exact IDs/coordinates and reason; explain that signing cannot ensure erasure from relays and copies. |
| 10002: relay preferences | Every relay and read/write role plus replacement effect. |

Relay authentication (22242/NIP-42) is mandatory for an admitted DM workflow when its relay requires AUTH, as specified below. Other relay authentication and HTTP authorization (27235/NIP-98) require a separate named-client workflow, exact challenge/URL/method/body-hash scope and freshness model. They are not implied by public posting. Zaps/payments, arbitrary app kinds, concurrent multi-account, persistent automation and generic opaque signing remain outside the first catalog. F01 is optional and cannot bypass the first-release gates.

## Connected-only message setup and authentication

The initial admitted NIP-17/59 flow is one-to-one plain-text rumor kind 14,
sealed and gift-wrapped to the peer and sender individually. Group/file-message,
message-reaction, edit/deletion and disappearing-message extensions are deferred.
This does not reduce the separate common public-event catalog.

A newly generated identity must be able to configure receiving relays without
exporting its secret. Connected message profiles therefore support a distinct
locally reviewed kind-10050 setup/replacement action. Show the selected identity,
every exact relay URI and the fact that this replaces the whole DM-receiving
list. Require empty content and well-formed unique `relay` entries using admitted
WebSocket URL rules; malformed known tags reject. Other permitted metadata must
be fully shown under the event-review rules, never hidden. An empty list requires
an explicit withdrawal prompt: the identity will not be advertised as ready to
receive messages. No trustworthy before/after diff is assumed without verified
prior state. This action is connected-only and belongs to C02 plus the connected
renderer/engine tasks; it does not enable 10050 on the initial offline profiles.

C02/client qualification must exercise a fresh identity's setup, signature and
publication, then receiving on those relays. Outgoing delivery uses only relays
from the intended recipient's checked kind-10050 event; an absent/invalid list
means the recipient is unavailable, with no arbitrary-relay fallback. Check the
advertisement's author, ID and signature, and document discovery/freshness
limits rather than claiming global latest-state proof from a hostile relay.
A signed setup event and successful publication remain different outcomes.

If a selected DM relay requires NIP-42, that named workflow must qualify it before
admission. Authentication is a distinct kind-22242 action bound to the exact
relay URI, current connection challenge and a declared freshness/time model,
with local consent separate from message approval. Reconnect/challenge change,
cancellation and timeout invalidate pending authentication. Show the full
challenge with bounded inspectable presentation; reject unsupported tags, hidden
payload, stale/wrong relay or replayed challenge. Relay URI, challenge and time
supplied by a host remain host claims unless independently authenticated;
displaying them does not attest remote origin or a trusted wall clock. C02 must
name and test the trust needed for its claimed freshness. Publish no AUTH event
as an ordinary post. A client/relay that cannot meet this contract is unsupported for
that message workflow; no silent fallback to an unprotected mailbox. C02 owns
this evidence and connected device/client tasks exercise it. NIP-98 and other
authentication flows still require separate admission.

Sources: the pinned [NIP-17 Publishing/Relays sections](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/17.md#publishing)
and [NIP-42](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/42.md).
These are requirements for future implementation, not tested client support.

## Recovery decision and user journeys

NIP-19 defines `nsec` as a user-facing encoding for the existing private scalar; it does not add encryption. Select it as the native interoperability baseline rather than creating another mnemonic-to-identity scheme. The backup is a secret copy under the person's physical custody. Copying it neither revokes the first device nor creates a different identity. A PIN protects device unlock only where the profile proves it; losing or exposing the backup has separate consequences.

For the first release, local text entry/display is the common semantic fallback. Optical import/export may use the same `nsec` locally on qualified camera/display profiles. Every target must demonstrate usable, checksum-validated entry and an actual expected-public-key recovery drill before admission. A two-button board with impractical recovery fails its product gate even if it can sign. No host-assisted plaintext fallback is allowed. The precise UI is designed and measured on each target rather than imposed as identical hardware interaction.

NIP-06/BIP-39/SeedQR compatibility is optional migration work, not required for the initial native identity flow. Preserve useful legacy test/oracle knowledge without promising all historical source formats. NIP-49 encrypted export is deferred pending an explicit password/KDF/memory and usability design; do not weaken its parameters merely to fit an MCU. This decision does not invent a new password-based vault encryption scheme; persistent custody is separately specified in D02/S04.

| Journey | Required user-visible behavior and failure |
| --- | --- |
| Initialize | Identify hardware/profile/firmware; locally create or import; show actual full public key; create backup and demonstrate same-identity recovery before profile admission. Entropy/import failure yields no usable secret output. |
| Pair | Bind transport and user identity separately. Show the selected local account and capabilities; pairing grants no blanket signature. Unexpected identity changes fail. |
| Connected operation | Receive, bound, validate, review and locally approve exact action; return verified result; client independently handles relay publication. Cancel/disconnect/timeout does not become consent. |
| Offline operation | Keep the original client request, display request QR, scan and validate on signer, locally review/approve, display public response QR, correlate and verify at Bridge. Mixed/incomplete/replayed frames fail predictably. |
| Message | Show admitted plaintext/recipient and bind them to the operation/seal actually authorized. Verify incoming context only when that context was supplied and checked. Client/Bridge can see plaintext when the admitted workflow returns it; never export stable conversation keys for convenience. |
| Lock / recover / update | Cancel authority and clear owned session material within documented limits. Offline reloads locally; persistent restore reproduces the expected identity. Test interrupted writes/updates, reset, rollback behavior and permitted firmware-owner transitions on actual target. |

## First hardware candidates versus admission

The historical source contains candidate manifests, not a verified inventory. It also contains statements equating disabled/unpopulated radios and referring to retired firmware targets. Do not inherit these as guarantees. D01/QP01/QP02 must select and identify their actual samples from source-backed candidate investigations. H04 owns the exact custom architecture freeze.

Current engineering leads are the existing no-camera LILYGO T-Display S3 class for a bounded USB/display/button experiment, a Pi Zero 1.3 / camera / ST7789 control kit for the initial radio-absent Pi investigation, and the existing Waveshare ESP32-P4-WIFI6-Touch-LCD-3.5 class for P4 camera/display investigation. These are not admitted assemblies, purchasing instructions or a promise that their existing pin/bus descriptions are correct. The P4 reference includes an ESP32-C6 companion-radio question; software-disabled is never advertised as physically absent.

Each candidate needs exact revision/package, manufacturer drawings/source, board connectivity, direct review/input, boot/update feasibility and custody evidence. A failed candidate is replaced without a legacy compatibility obligation. Public source descriptions that imply already-qualified hardware must be corrected during migration.

## Proof and remaining work

Read with [the threat models](threat-models.md). The requirement owner is responsible for a positive case and hostile variants at the boundary of its claim, including identity substitution, changed/hidden fields, invalid parsing, queue floods, authorization replay, lock/reset/account switch, malformed QR, opaque DM substitution, interrupted vault write and firmware rollback.

P01 can accept semantic scope and threat assumptions through source-backed review. Numeric capacities, actual recovery ergonomics and exact hardware admission remain measured task/release gates; this document does not close them. If final P01 review identifies a missing semantic decision, resolve it before acceptance rather than treating this document's existence as proof.

Primary additional sources: [NIP-19](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/19.md), [NIP-49](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/49.md); opened and reviewed on 2026-10-18. Their definitions support the format/KDF comparison, not a claim of tested nSealr recovery.

Protocol baseline for the common flows is Nostr specifications commit
`37db639582d857e12468dcccd99b2c7f1d657da9`:
[NIP-01](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/01.md)
for event serialization,
[NIP-07](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/07.md) and
[NIP-46](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/46.md)
for client methods/remote transport, and
[NIP-44](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/44.md),
[NIP-17](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/17.md) and
[NIP-59](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/59.md)
for encryption versus complete private-message context. Public-event tag
semantics have their individual pinned references in the event review contract.
The selected catalog, recovery default and workflow qualification are product
decisions; protocol source support alone proves no implemented client workflow.
