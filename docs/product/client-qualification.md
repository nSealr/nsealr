# Client and optical qualification


Protocol pins and client observations in this dated research are historical inputs.
The current first-release normative protocol baseline and message/setup obligations
are selected by [P01 requirements](requirements.md). Reconcile
these inputs against that accepted baseline and actual client lockfiles before
implementation; the older pin below is not a competing current authority.

Research date: 2026-10-13. This is a source-backed test selection, **not a compatibility announcement**. Source review does not establish successful operation against the deployed website, its dependencies or an actual signer.

## Phase-one host delivery

The connected session-only S3 retains C01 NIP-07/NIP-46 serving and C02 bounded
NIP-44 plus the admitted NIP-17/59 and setup/authentication obligations. Volatile
custody is not permission to drop the public-event catalog or message flows.
Pi/P4 initial manual public-event support remains separately qualified via QH01
and Q04/Q05, without connected DM or another vault as a prerequisite.

Current source consumers include `apps/bridge/cli`, `apps/bridge/service`,
`apps/bridge/browser-extension`, `packages/client`, `browser-provider`, `nip46`,
`transport`, `qr` and the `packages/sdk` browser/Node facade. Their existence,
`pnpm nsealr`/`pnpm nsealr-service` entry points and fixture tests establish no
external-client compatibility. C01/QH01 must qualify the needed installation,
onboarding, pairing/revocation/reconnect/cancellation/errors, compatible versions
and SDK examples together with each actual device workflow. Host transport keys
are distinct from the identity; local recovery never passes plaintext nsec to
these helpers. The generic embedded `nSealr/board-sdk` is deferred and distinct.

## Initial integration candidates

| Candidate and exact source | Observed integration path | Qualification still required |
| --- | --- | --- |
| [noStrudel `0476cad`](https://github.com/hzrd149/nostrudel/tree/0476cad1944dcc999da5eae21ea5224e27014042), package version 1.1.0 | [NIP-07 extension login](https://github.com/hzrd149/nostrudel/blob/0476cad1944dcc999da5eae21ea5224e27014042/src/views/signin/start.tsx); [NIP-46 bunker/nostrconnect and separate getPublicKey](https://github.com/hzrd149/nostrudel/blob/0476cad1944dcc999da5eae21ea5224e27014042/src/views/signin/connect/index.tsx) | Extension injection, remote-signer handshake, cancellation, late responses, reconnect, public event review and actual DM call sequence |
| [Coracle `8f4d34c`](https://github.com/coracle-social/coracle/tree/8f4d34cc16bfb4380208923d26307fab561a867d), package version 0.6.41 | [NIP-07 login](https://github.com/coracle-social/coracle/blob/8f4d34cc16bfb4380208923d26307fab561a867d/src/app/views/Login.svelte); [NIP-46 pairing/getPublicKey](https://github.com/coracle-social/coracle/blob/8f4d34cc16bfb4380208923d26307fab561a867d/src/app/views/LoginBunker.svelte) | Same workflow matrix using its independent signer stack; confirm requested/granted permission behavior and errors |

These candidates exercise two integration stacks (applesauce and welshman). Pin their lockfiles, build inputs and browser versions for a run; package version alone is insufficient. For example, this noStrudel source uses `next` package ranges resolved by its lockfile. Reconcile newer versions before release.

Both sources request NIP-04 as well as NIP-44 ([noStrudel permissions](https://github.com/hzrd149/nostrudel/blob/0476cad1944dcc999da5eae21ea5224e27014042/src/const.ts), [Coracle permissions](https://github.com/coracle-social/coracle/blob/8f4d34cc16bfb4380208923d26307fab561a867d/src/util/nostr.ts)). The new product does not silently add deprecated NIP-04 to satisfy that request. Test explicit unsupported responses and whether login/public posting/NIP-44 still work. A client that requires a rejected operation is unsupported for that workflow until corrected; requesting a permission is not approval of it.

Start with desktop Chromium and Firefox extension flows plus NIP-46. Select Android/iOS clients separately after a concrete connector and test-device choice. A web demo does not prove USB access on every mobile browser.

## Identity, consent and encryption boundaries

The normative source set is [NIPs at `a79e21d`](https://github.com/nostr-protocol/nips/tree/a79e21d90fce5465b50ef385dd368bba99ec4a0b). Reconcile revisions deliberately; do not use an older mirror as the specification.

- **NIP-07:** the extension can bind browser tab/frame/origin within its browser trust boundary. A compromised Bridge can lie about a displayed application name. Neither NIP-07 nor USB supplies a hardware-attested website identity. Device review must bind the actual operation and account; label host-supplied context honestly.
- **NIP-46:** distinguish authenticated transport peer from the user's signing key. Pairing, expected-user-key confirmation, reconnect and revocation need separate tests. A remote peer key does not certify a human-readable application name. Host-owned transport keys must never be confused with custody of the user's identity key.
- **NIP-44:** v2 uses raw-x secp256k1 ECDH, HKDF, ChaCha20 and HMAC-SHA256. It does not supply forward secrecy. The current specification supports an extended length prefix; the device must advertise and enforce its own smaller bounded payload limit, with checked arithmetic before decoding/allocation.
- **Decryption context:** standard NIP-07/NIP-46 methods pass a peer key and payload, not the complete signed outer event. A primitive decryption call cannot prove that an outer event was verified. A trusted signed-message workflow needs the full context and verification at the appropriate boundary. Do not describe bare-payload decryption as authenticated message review.
- **NIP-17/59:** supporting NIP-44 primitives alone does not demonstrate usable private messaging or meaningful device review. Trace real client calls; bind reviewed plaintext/recipient to the resulting encrypted seal before authorizing its signature. Fail closed if the device cannot establish that relationship. A host-composed opaque kind-13 ciphertext is not a readable message. A proposed compound device operation needs implementation and client integration; it is not an existing standard method.

Current normative details are in [07](https://github.com/nostr-protocol/nips/blob/a79e21d90fce5465b50ef385dd368bba99ec4a0b/07.md), [44](https://github.com/nostr-protocol/nips/blob/a79e21d90fce5465b50ef385dd368bba99ec4a0b/44.md), [46](https://github.com/nostr-protocol/nips/blob/a79e21d90fce5465b50ef385dd368bba99ec4a0b/46.md), [17](https://github.com/nostr-protocol/nips/blob/a79e21d90fce5465b50ef385dd368bba99ec4a0b/17.md) and [59](https://github.com/nostr-protocol/nips/blob/a79e21d90fce5465b50ef385dd368bba99ec4a0b/59.md). These are product deductions from those interfaces, not claims that nSealr has implemented them.

## QR is a transport, not an authorization scheme

The QR in the clients' `nostrconnect://` login screen establishes a relay connection. It is **not** an offline signing transaction. Offline Pi/P4 need a Bridge that keeps the client request pending while displaying and scanning a distinct device protocol.

Compare a bounded single-frame format with [UR](https://github.com/BlockchainCommons/Research/blob/e4a4fbb186e2e7625ccdf7149aec4f0a5adaf850/papers/bcr-2020-005-ur.md) / [multipart UR](https://github.com/BlockchainCommons/Research/blob/e4a4fbb186e2e7625ccdf7149aec4f0a5adaf850/papers/bcr-2024-001-multipart-ur.md) on the chosen cameras/displays before freezing framing. Reuse a maintained decoder if its allocation and CPU bounds can be enforced. Do not add a fountain implementation just because it exists, or invent incompatible framing without measuring the simpler options.

Multipart UR defines CRC-32 and matching sequence metadata. These detect corruption and aid assembly; they do not authenticate an adversarial sender. The nSealr envelope must separately bind version, operation, request/session, expected signer, payload and response. Reject unknown types, mixed sessions, duplicate completion, expired/cancelled requests and seed material on the normal signing-output path. Cap frame bytes, decoded bytes, fragment counts, retained decoder state, work per frame and total duration before accepting attacker-controlled sizes.

QH01/Q02/Q03 must test actual scans, dropped/reordered/duplicated frames, deliberate malformed frames and client cancellation/timeouts. Local encoding/decoding round trips do not establish optical usability. Initial QR delivery is manual public-event signing; private messaging and unattended automation require separate acceptance.

## Experiment and pilot protocol

For each exact client/profile, capture: fresh pairing; public key confirmation; kind-1 post; rejection; disconnect mid-approval; late/repeated response; changed peer/user key; oversize input; unsupported NIP-04; and the agreed NIP-44/DM workflow. Verify signed output independently. Use disposable public fixture identities before profile admission. Record every prompt and whether the person could identify what was authorized.

Provisional usability targets are hypotheses: at least 8/10 participants complete setup unaided, 7/10 still use the tested workflow weekly over four weeks, and every exercised recovery restores the expected identity. Any unexplained signature or identity change stops the pilot regardless of these scores. Record elapsed setup/recovery time and connected/optical approval latency before setting performance budgets; participant counts are directional learning, not statistical proof of adoption.

P02 defines the matrix; C01/C02 qualify connected integration; QH01 plus each Q release qualify optical integration. A failing DM test blocks the affected advertised DM guarantee, not a separately qualified public-event-only offline release. Do not claim universal compatibility, market demand or future popularity from source inspection.
