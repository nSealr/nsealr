# Proposed product contract for P01

Date: 2026-10-18. **These are proposed requirements, not implemented features or release claims.** P01 must resolve the remaining choices and publish the accepted contract; the 47 open work items are an execution outline, not 47 completed specifications. The first working slice can demonstrate one kind-1 post. A public profile release needs the agreed catalog, lifecycle and profile evidence below.

## Product and common boundary

**nSealr Signer** lets a person use a Nostr identity while keeping its secret key out of the ordinary Nostr client and Bridge. The person checks an operation on the signer's own screen and approves it with local input. **nSealr Bridge** connects browsers/clients and relays to the signer, returns checked results, and publishes through the client; a successful signature does not prove relay publication. The generic **Board + Board SDK** are independently usable hardware and platform support.

“Vault” can be an optional name for an offline application, but does not imply persistent storage, extraction resistance, or a higher security rank. Connected/Offline and the exact hardware profile are more useful than another product hierarchy. Keep `board-sdk`: the client-facing TypeScript SDK is a different consumer and API.

**PR-ID — Identity.** The initial product has **one active Nostr identity per unlocked signer session**. It derives and displays the actual full public key; fingerprints are visual aids. Changing identity invalidates pending requests and requires explicit client re-binding. Multiple concurrently active identities, account selectors and derivation trees are deferred. Device identity, NIP-46 transport identity and user signing identity are distinct values.

**PR-KEY — Key lifecycle.** Generate locally with a qualified entropy source or import locally using the selected device's physical input/optical interface. Never require pasting the user's nsec into Bridge, a browser or a desktop recovery helper. Native backup represents the one Nostr secret, with a local export/recovery ceremony; select the concrete encoding/input method and demonstrate usability on each target before admission. Backup is a separate, conspicuous operation, not a signing response. Copying a backup to another device creates another holder of the same identity; it does not revoke the first. Optional NIP-06 recovery remains compatibility support, not the default new-identity scheme ([NIP-06](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/06.md)).

**PR-REVIEW — Authority.** The engine owns key selection through the qualified custody boundary, strict decoded request, exact NIP-01 serialization and review state. Local approval consumes authority once for that operation, account, session and expiry. Host `approved` fields, client names, browser origins or policy labels are never device authorization. Review must expose every signed field/tag without silent truncation; long data needs an inspectable bounded presentation or explicit rejection. Unknown operations/kinds fail explicitly in the initial product; there is no automatic generic blind-signing fallback.

**PR-BOUNDS — Limits.** Publish each profile's supported catalog, input/tag/content/frame bounds and pending-request behavior. Establish the common supported minimum using measured target results; do not copy old arbitrary limits or claim the NIP-44 maximum fits a device. Enforce sizes, cumulative queued bytes, request counts, time and parser work before allocation/expensive work. Invalid, cancelled, expired, mismatched and repeated requests cannot produce fresh signatures. A bounded same-session retry may return an already-produced identical result without another key operation.

## PR-EVENTS — Proposed first public-event catalog

All four profiles should target the following common semantics. P01/P02 must accept this scope and measure its bounds; no row is qualified today. Every renderer needs executable fixtures and actual-screen review. Unsupported extras in a nominally supported kind must be rejected or rendered completely with honest semantics, not hidden.

| Operation | Proposed common support and review obligation |
| --- | --- |
| Get public key | Return the actual selected public key after the local/session access rule; it is identity disclosure, not proof of website login or signed authorization. |
| Post, reply, quote | Kind 1 with NIP-10/NIP-18 context. Show text, mentions, reply/root/quote targets and all remaining tags. A host-provided title or preview is unverified unless the target evidence is verified. Non-kind-1 reply standards are outside this initial catalog. |
| Profile | Kind 0. Show all submitted metadata and the replacement effect. A familiar avatar/name is not an authenticated recipient identity. |
| Follow list | Kind 3. Explain that the submitted event replaces the list; show all affected entries. Do not claim a trustworthy “add one person” diff unless the prior list and freshness are established. |
| Reaction / repost | Kind 7 reactions and kind 6 reposts of kind-1 events. Show the reaction and target; verify included original-event evidence before presenting its author/content as verified. Generic kind-16 reposts and kind-17 external reactions are deferred. |
| Deletion request | Kind 5. Show exact target IDs/coordinates and reason. Explain that a signed request cannot guarantee erasure from relays or other copies. |
| Relay preferences | Kind 10002. Show every relay and read/write role; explain replacement. This operation can change publication and discovery behavior. |

References: [NIP-01](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/01.md), [02](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/02.md), [09](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/09.md), [10](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/10.md), [18](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/18.md), [25](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/25.md), [65](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/65.md). These sources define event semantics; the chosen minimum catalog is a product proposal.

Relay authentication (kind 22242/NIP-42) needs a separate scoped review of relay and challenge, not a public-post prompt. HTTP authorization (kind 27235/NIP-98) needs exact URL, method and applicable body hash, with explicit freshness rules. Add either only for named qualified client workflows. Optical timing may make a specific flow unsupported; never bypass approval to satisfy a timeout. Zap requests/payments, arbitrary application kinds, automatic grants and signing opaque encrypted events are not implied by this catalog.

## Profile matrix: separate capabilities, not security levels

“Required” below means a proposed release obligation. “Conditional” requires the exact implementation/assembly to qualify. “Deferred” is explicitly unsupported in the first release of that profile.

| Capability / property | Commercial ESP32, no SE | Raspberry Pi QR | ESP32-P4 QR | Custom Board running Signer |
| --- | --- | --- | --- | --- |
| Common event catalog, canonical-event local approval, expected-key binding | Required | Required | Required | Required |
| Normal request/response transport | Connected USB through Bridge | Optical request/response through Bridge | Optical request/response through Bridge | Qualify connected path first; additional interfaces separately |
| First engineering slice | Volatile test key, real display/input/signature | Existing camera/UI adapter with shared engine | Camera/display adapter with shared engine | Board bring-up independently, then same engine |
| Proposed release custody | Persistent local vault only after D02 lifecycle qualification; no-SE explicitly declared | Stateless session import; reload after power loss | Stateless session import; reload after power loss | Conditional persistent custody after MCU/SE command and lifecycle proof |
| NIP-44 / NIP-17/59 messages | Connected release requirement under C02 | Deferred initially | Deferred initially | Connected requirement, conditional on selected custody capabilities |
| Native non-exportable BIP-340/ECDH inside an SE | Not present | Not claimed | Not claimed | Not assumed; actual command support determines key exposure |
| Radios / physical air gap | Exact board interfaces declared | Exact Pi and assembly checked; “disabled” differs from absent | Exact assembly checked, including companion modules | Exact populated components and enabled interfaces declared |
| Boot, update, debug, recovery | Exact MCU/profile evidence | Exact model and shipping-image evidence | Exact silicon/SDK/profile evidence | Exact board revision, provisioning and owner-transition evidence |
| Automatic signing policies | Deferred | Deferred | Deferred | Separate F01 experiment, not base release |

The common promise is control of the selected operation and identity. Physical extraction resistance, boot enforcement, persistence and interface exposure vary independently. A volatile prototype is not a persistent daily-use vault; an authenticated downloaded image is not proof of enforced verified boot. A failed optional DM claim does not prevent a separately qualified offline public-event release.

On Pi, retaining Python camera/UI code keeps that interpreter and its relevant drivers/kernel inside the trusted system. A Rust/PyO3 interface does not isolate a hostile caller or erase copies of a key already decoded in Python. Keep the boundary small and account for those copies explicitly; shared Rust semantics are not a claim of whole-device memory safety.

## Complete user journeys

1. **Acquire and initialize.** Identify exact hardware, firmware and profile; verify the installation/update process supported by that profile. Create or import the identity locally, display the derived public key, create the external backup, then perform a recovery rehearsal that reproduces that identity. Configure local unlock only if persistent custody is supported. State what loss of the device, backup or PIN means.
2. **Pair and connect.** Bridge receives a browser NIP-07 request or operates the qualified NIP-46 signer service. Obtain and pin the user's key separately from the NIP-46 transport peer. Show the local account and requested capabilities, with host-provided names clearly identified as such. Approve the operation family/session locally as designed; pairing never grants blanket signing. Reject unexpected key changes rather than silently updating a pin.
3. **Connected signing.** The client prepares an event; Bridge submits its exact request with expected identity. Signer validates and shows the operation; the person approves or rejects. Engine serializes and signs exactly the reviewed event. Bridge/client independently check request, expected author, ID and signature before accepting the response. The client publishes it and reports publication status separately.
4. **Offline signing.** Bridge keeps the original client request pending and displays the signing-request QR. The signer scans, bounds and validates it, reviews locally, then displays only the approved public response. Bridge scans and verifies the response against the pending request and expected key before returning it to the client. A `nostrconnect://` pairing QR is not this transaction. Mixed/repeated frames, interrupted scans and client timeout must end predictably; cancellation never becomes approval.
5. **Private messaging on qualified connected profiles.** Distinguish a NIP-44 encryption/decryption primitive permission from a trusted message operation. A bare peer-key/payload API cannot prove a signed outer event was supplied. For meaningful NIP-17/59 send review, bind the visible plaintext and recipient to the constructed rumor/seal and its authorized signature; arbitrary opaque kind-13 signing is insufficient. Incoming trusted-message review needs full context and signature/author consistency checks. Plaintext returned to the client is visible to it and Bridge as applicable; NIP-44 does not provide forward secrecy. Never export a user conversation key merely to make a host client work. C02 must demonstrate the actual client call sequence or mark that workflow unsupported; a new compound device operation is not automatically a standard NIP-07/NIP-46 method.
6. **Finish, lose power, recover or update.** Lock/detach/reset cancels authority and clears session material under the profile's documented lifecycle. Offline sessions reload locally next time. Recovery restores and confirms the same public identity; a PIN reset must not bypass vault protection. Install only through the profile's accepted authenticated update/recovery process, exercising interrupted update, incompatible storage schema and rollback behavior. Firmware reprogramming/owner transition must not silently hand existing privileged state to a replacement image. Antirollback enforcement claims require actual hardware evidence.

Identity and encryption references: [NIP-07](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/07.md), [46](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/46.md), [44](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/44.md), [17](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/17.md), [59](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/59.md). Authentication references: [42](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/42.md), [98](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/98.md).

## Decisions to close, then tests to require

P01 must accept or adjust the common event catalog, select exact first hardware assemblies, and decide whether connected first public release must include trusted DM review as currently scheduled. Engineering can decide internal modules and adapters autonomously. Quantitative capacities, QR framing, local import/backup ergonomics and supported client authentication flows require measured results before freezing, not guessed defaults.

For each accepted requirement, name its implementation task, exact success and negative test, profile scope and evidence. Required failures include wrong expected identity, valid foreign-author response, hidden/changed event field, duplicate/trailing JSON, unsupported kind/NIP-04, unbounded queues, approval replay, key switch, lock/reset mid-operation, malformed optical assembly, opaque DM substitution, interrupted vault write and update rollback. Unit tests cannot close physical display/input, entropy, power-loss or extraction-resistance claims. Independent code review and actual profile evidence remain separate release requirements.

Local optical key import is a separate recovery ceremony, never an ordinary signing-request feature. Test that camera frames, thumbnails, logs, crash dumps, swap and diagnostic exports do not persist or disclose recovery material under the profile's actual environment. A local camera does not by itself make a key-import path safe.

The following map assigns specification ownership; it records no completed acceptance. Product details become binding when P01 accepts them, and concrete device/client limits close in the referenced feasibility tasks. Existing task state remains solely in [work-items.json](work-items.json).

| Requirement / journey | Owning implementation and qualification tasks |
| --- | --- |
| PR-ID: selected identity and re-binding | S01, S02, K01, C01, QH01; exact-profile release |
| PR-KEY: generation, local import/backup and custody | P01, S02, S04, D02, Q02/Q03, V02/V03; profile recovery proof |
| PR-REVIEW: local, operation-bound one-use consent | S03, K01; V01/V03, Q02/Q03; see AUTH-01–05 in [development](development.md) |
| PR-BOUNDS: bounded hostile input and explicit capabilities | S01, T01, K01, Q01/QH01; QP01/QP02 and target measurements |
| PR-EVENTS: supported public-event semantics | P01/P02, K01; C01 or QH01; actual screen and client qualification |
| Journeys 2–3: pairing and connected operation | S01, V01, C01; custom integration V03 |
| Journey 4: optical operation | Q01, QH01, Q02/Q03; independent Q04/Q05 releases |
| Journey 5: private messaging | C02; D03 or V03/S05; initially excluded from Q04/Q05 |
| Journey 6: lock, recovery, updates and ownership | D02, QP01/QP02, Q02/Q03, S04, B02, H08/H09; relevant release gate |

Physical architecture and tool capabilities are specified separately in [PCB development](pcb-development.md). The generic Board/SDK release B03 must demonstrate non-Nostr usefulness and its own lifecycle; it does not inherit the Nostr product catalog.
