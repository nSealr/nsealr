# Public API Review

This review records the current pre-alpha public package surface. It is a
release gate for npm publication, not a compatibility guarantee. Breaking
changes remain allowed before the first public package release.

API surface digest: `sha256:eac6f4c4329f95e03e9598ec8b480940c25d19d65bd39649ff61be71ede34149`

Source: `docs/api.md`

## Review Rules

- Public packages must import through package entrypoints, not deep source
  paths.
- Public package production source must pass the import-hygiene gate: relative
  imports stay inside the package `src` boundary, `@nsealr/*` imports use
  reviewed public entrypoints/subpaths, and private apps or test-only packages
  stay out of production code.
- User identity/signing secrets, mnemonics, passphrases and decrypted signing
  material must remain outside Bridge custody. NIP-46 client transport secrets
  have a separate bounded in-memory lifecycle; they do not authorize user signing.
- `@nsealr/dev-signer` must remain private and test-only.
- Companion APIs may prepare requests, validate payloads, verify responses,
  render untrusted review previews, and route to signers. Trusted review and
  approval remain signer-route responsibilities.
- NIP-46 APIs currently handle the already-decrypted payload bridge,
  digest-bound `connect` and auth-challenge review/approval artifacts,
  descriptor-only connection URI parsing, secretless connection-token response
  verification, relay event envelopes, and metadata-only relay request/response
  steps, plus pending-session request gates that block signer dispatch with
  `connect_ack_pending` for
  approved-but-unacknowledged session checkpoints. The separate exported runtime
  session manager and relay adapters perform NIP-44 client transport and direct
  ack/user discovery under the S01 bounds below. Browser URL opening and device
  approval are not implied by either surface.

## @nsealr/browser-provider

Status: reviewed for pre-alpha.

The surface is intentionally small: `createNip07Provider`, the local-service
backend adapter, the browser native-messaging local-service client adapter, and
provider/backend types. It stores no browser-side key material and delegates
signer access to an injected backend. The local-service adapter can read the
selected account public key through authorized route selection and routes
`signEvent` through the local-service dispatch operation, which returns
deterministic signer-unavailable responses until an explicit signer route
dispatcher is configured. The shared route-refusal contract also pins
display-less smartcard acknowledgement requirements and trusted-review
acknowledgement rejection before browser code can fork route semantics.
Dispatch verifies successful signer responses against the selected route public
key before the provider can trust them. The
native-messaging adapter only wraps an explicit `sendNativeMessage` function,
validates the host name, and delegates silent or cancelled exchange bounds to
`@nsealr/client`; it does not install a native host or persist grants.
`signEvent` validates the generated nSealr request and verifies successful
responses before returning a Nostr event. Keep future extension storage,
native-host installation, origin grants, NIP-04, and NIP-44 outside this
package until those contracts are reviewed separately.

## @nsealr/client

Status: reviewed for pre-alpha.

The local-service surface is secretless and limited to service status, pairing
intent creation, deterministic pairing-review projection, manual pairing
approval into a grant, strict pairing-approval artifact parsing, strict JSON
grant-store serialization and output-only revocation appending for
approved/revoked local client grants, digest-bound storage-location review and
approval artifacts for explicit grant/account/route-driver paths, approval
coverage checks before grant-store output writes, secretless route selection,
signer-request validation, grant-gated dispatch through an explicitly injected
dispatcher, display-less external-review acknowledgement binding, and
signer-response verification. Browser runtime code uses the reviewed
`./browser` subpath, while identity-only callers may use the smaller
`./client-identity` subpath. Request-id correlation, native-message framing,
and malformed-response rejection are public helpers.
`LocalServiceClient` also owns optional deterministic response timeouts,
request cancellation, `AbortSignal` forwarding into injected exchanges, and the
explicit external-review acknowledgement dispatch option for display-less
routes so browser-provider, SDK, extension, and future desktop code do not fork
stalled local-service or smartcard-review behavior.
The shared native host name, native-host manifest builder, digest-bound dry-run
install-plan builder/parser, install-approval artifact helpers, and explicit
approval-bound install execution builder/parser remain exported from the
Node-capable root so service manifest/plan/approval/execution generation and
packaging checks do not drift.
`SignerTransportError` is the public typed error host-owned dispatchers should
throw when a transport failure needs to cross the local-service boundary with a
deterministic code instead of a generic dispatch failure.
Route selection returns metadata only and validates response metadata through
`@nsealr/policy`; dispatch is unavailable by default and does not include real
transport drivers. The route-aware dispatcher registry is only a secretless
host-wiring helper: it selects the most specific configured
account/route/transport handler, reports missing route handlers as unavailable,
and rejects ambiguous handler configuration without opening a signer transport.
Display-less `sign_event` routes require a
`nsealr-external-review-acknowledgement-v0` artifact with a matching
`approval_digest` before the injected dispatcher is called, and the same
artifact is rejected on routes with trusted device review.
The async local-service handler is only an awaitable form of the same reviewed
dispatch boundary for future host-owned I/O drivers; the synchronous handler
rejects async dispatchers deterministically. File-backed service loading is now
storage-approval gated. Native-host install approvals remain artifact-only with
`writes_files=false`; the separate execution helper requires the reviewed
install digest again, uses an injected writer, reports `writes_files=true`, and
writes only the reviewed manifest path with write-new semantics. Route-specific
signer transport wiring, production storage writes, and production installer UX
remain future work and must not be implied by this package.

## @nsealr/core

Status: reviewed for pre-alpha.

The core package owns Nostr event serialization, event-id computation, Schnorr
verification, and request/response matching. It must remain verification-only
for production code. Signing stays outside public packages except for the
private test-only development signer.

## @nsealr/fixtures

Status: reviewed for pre-alpha.

Fixtures are conformance tooling for tests, repository integration, and example
verification. This package can parse and load shared vector sets, but it does
not define production signer behavior. It is acceptable as a public developer
package only because it contains no production secret custody path.
Source public-key proof fixture validation must remain secretless: it may load
proof metadata, expected public keys, source fingerprints, and source-vector
paths, but not mnemonic words, raw secret keys, or NIP-19 `nsec` payloads.
Persistent-secret custody contract validation is also conformance tooling. It
may check custom hardware-wallet custody gates and non-claims, but it must not
become a production key store, TROPIC01 capability oracle, or signer route.

## @nsealr/framing

Status: reviewed for pre-alpha.

The framing package only encodes and decodes checksum-protected serial frames.
It has no device-opening, route-selection, policy, storage, or signing
responsibility. It is browser-runtime clean as a direct package for future USB
CDC/UART/WebSerial experiments, but WebSerial/WebUSB exposure remains outside
`@nsealr/sdk/browser` until that access-surface boundary is reviewed.

## @nsealr/nip46

Status: reviewed for pre-alpha.

The NIP-46 package converts already-decrypted messages into nSealr decisions or
deterministic local responses, parses connect review intents, produces
digest-bound connect review and approval artifacts, produces digest-bound auth
challenge review and approval artifacts, parses descriptor-only `bunker://` and
`nostrconnect://` connection URI metadata, verifies already decrypted
`nostrconnect://` token responses without echoing or storing the returned
secret, parses relay event envelopes, parses and creates reviewed-but-not-active
session lifecycle checkpoints, parses requested-permission metadata, parses
stricter approved-permission inputs, parses read-only policy files, and
enforces permission checks. It also evaluates
relay request and response steps only
after plaintext has been
supplied by a caller: request steps return deterministic bridge
decisions, while response steps shape-check plaintext signed-event, public-key,
ping, auth challenge, and error responses after signed relay-event envelopes
are NIP-01 id checked and BIP-340 verified. Signed-event response results are
also NIP-01 id checked and BIP-340 verified before metadata is accepted,
without opening relays, opening auth URLs, or accepting URL
credentials/fragments.
Auth challenge review renders only the remote signer pubkey, client pubkey, and
auth URL, and approval requires the reviewed auth challenge digest while
recording false side-effect flags for URL opening, relay opening, connect
acknowledgement, grant creation, signer dispatch, secret storage, and session
persistence.
Connection-token response verification returns only secretless metadata for
client pubkey binding, discovered remote signer pubkey, relays, and requested
permissions while recording no relay opening, NIP-44 key derivation, connect
acknowledgement, grant creation, signer dispatch, secret storage, or session
persistence.
Approved `sign_event` inputs must be kind-scoped before signer routing. The
connection URI parser records only secret presence, not the secret value. Relay
event envelope parsing exposes only sender/recipient/content metadata and
signed-field verification; it verifies signed relay event ids/signatures
without decrypting NIP-44 content. Relay response-step parsing also verifies
signed-event result ids/signatures.
Session lifecycle parsing records `approved_pending_ack` checkpoint metadata
only and rejects secret material, NIP-44 key derivation, relay opening, connect
acknowledgement, grant creation, signer dispatch, production secret storage,
and session persistence. Session checkpoint creation validates the
review/approval digest pair, client pubkey, relay list, expiry, and approved
permission subset before returning the same secretless object. This checkpoint API deliberately
excludes relay sessions, NIP-44
encryption/decryption, persistent grants, connect acknowledgement, browser
storage, and signer I/O; connect approval artifacts explicitly preserve those
false side-effect flags.


S01 runtime and metadata contract (independent final candidate review is recorded
under `docs/restart/S01/`, not asserted by this API inventory):

- `Nip46SessionManager` pins the authenticated configured transport author and
  resolves a separate curve-valid user key through `get_public_key` before
  activation. Optional `expectedUserPubkey` constrains first resolution;
  `userPubkey` exposes the active identity. Signed results bind that identity,
  requested template, event ID and signature. The caller owns origin and account
  selection; the remote signer owns user key custody and device approval.
- Fresh per-manager request namespaces and monotonic counters prevent ID reuse.
  Pending requests and unsettled publications each default to 32, capped at 256;
  one unresolved subscription acquisition blocks further acquisition. Timeouts
  default to 30 seconds, capped at 300 seconds. Close is terminal and clears the
  owned transport-key copy. Failed connect retries retain the monotonic counter;
  an unresolved adapter acquisition must settle before retry. Arbitrary adapter
  promises cannot be forcibly cancelled by this interface.
- `buildNip46RequestEvent` and `decryptNip46Event` implement signed NIP-44 client
  transport. `NostrToolsRelay` opens relays via SimplePool; `InMemoryRelay` is the
  deterministic test adapter. Metadata session storage does not restore the
  runtime manager or persist its secret. These exports existed before S01 and
  the regenerated API inventory now includes them accurately.
- Response-step output is explicitly v1: `result_pubkey` and
  `result_pubkey_bound_to_expected_user` replace transport/user equality.
  Optional input `expected_user_pubkey` rejects a conflicting result. Metadata
  alone does not establish an authenticated session. The CLI and shared fixture
  consumers migrate together; there is no experimental v0 compatibility layer.
- Raw NIP-46/serial JSON rejects duplicate keys, trailing data and depth above 32.
  NIP-46 messages remain capped at 1,024 bytes; encrypted content at 2,048 bytes;
  tag count/width/field limits are 16/8/64. These are nSealr profile limits.

## @nsealr/policy

Status: reviewed for pre-alpha.

Policy descriptors are internal nSealr records rather than Nostr events. The
package rejects embedded secret fields, QR-vault automation, wildcard grants,
decrypt/export grants, and invalid route targets. It also exposes pure
secretless account-route request parsing and selection from parsed descriptors
and supported methods, `nsealr-route-selection-v0` response parsing, runtime
parsing for policy-decision requests, plus deterministic expiry, revocation,
and rate-limit decisions from explicit grant-usage snapshots. It also exposes
secretless policy-change proposal
parsing, explicit account/policy/grant context validation, and deterministic
review-page/approval-digest generation for device approved `set_policy`
changes. Persistent grant storage, usage history storage, authoritative device
policy mutation, signer dispatch, and account custody remain outside this
package.

## @nsealr/protocol

Status: reviewed for pre-alpha.

The protocol package owns nSealr v0 request, response, capability,
signing-status, implementation-limit validation, and small browser-safe
encoding helpers shared by QR and serial framing packages. Its limits are
nSealr safety limits for constrained signers, not Nostr protocol limits. All
access surfaces should validate through this package before contacting signer
routes. `parseStrictJson` adds bounded raw JSON syntax, duplicate-member and
32-container depth validation before schema checks.

## @nsealr/qr

Status: reviewed for pre-alpha.

The QR package transports already-validated request/response payloads through
static and animated envelopes. It owns envelope parsing, frame ordering,
checksums, digest checks, and byte limits. It must not grow signing, storage,
policy, compression, or fountain-code behavior without a separate review.

## @nsealr/review

Status: reviewed for pre-alpha.

The review package produces deterministic summaries, screen pages, detail
pages, and approval digests for conformance and host-side previews. Companion
review output remains untrusted. Hardware routes and display-less external
review routes own trusted approval.

## @nsealr/sdk

Status: reviewed for pre-alpha.

The SDK package is a platform-neutral facade over curated public namespaces for
browser, app, and companion integrations. It intentionally excludes the private
`@nsealr/dev-signer` package and does not import Node-only fixture loading or
host transport adapters. The `@nsealr/sdk/browser` subpath is the reviewed
browser-safe facade over the NIP-07 provider, `@nsealr/client/browser`, and
pure core/policy/protocol/QR/review helpers. Use `@nsealr/fixtures` and
`@nsealr/transport` directly when test/lab or Node host code needs those
specialized surfaces. The SDK must remain a secretless convenience layer: no
production key custody, browser-side signing material, grant database,
native-host installation, or signer dispatch.

## @nsealr/smartcard

Status: reviewed for pre-alpha.

The smartcard package exposes APDU codecs, PC/SC boundary normalization, and
display-less signer helpers. Test-only APDU simulation lives in the private
`@nsealr/dev-signer` package, so this publishable package does not expose
software signing helpers. Its signer path must remain bound to shared request
validation and external review acknowledgement. The public APDU constants include
the exact v0 profile status words, including incorrect P1/P2 rejection, but not
any production card compatibility claim. It must not claim trusted event review
because current smartcard routes have no display.

## @nsealr/transport

Status: reviewed for pre-alpha.

The transport package owns secretless host-side transport interfaces and
adapters for JSON files, JSON-lines stdio, serial frames, and serial-line
ports. It validates requests and responses and verifies successful `sign_event`
responses before returning them. Production transport code must not depend on
software signing helpers. `SerialLineStreamPort` now bounds total retained bytes
(default 1,024; maximum 1,048,576), buffered lines including a partial tail
(default 64; maximum 4,096), and pending read/write counts (one each). It pauses
queued input, honors output drain and discards data on terminal error/close.
Owned listeners are removed after stream closure, including asynchronous
destruction with `emitClose: false`; error handlers remain through Node's queued
destruction errors. Streams must be live and exclusively owned, with replaceable
`_destroy` hooks. Constructor rejection rolls back hooks/listeners. Normal EOF
drains bounded data.

## Open Before npm Alpha

- npm trusted publishing/provenance setup must be configured outside the local
  repository.
- If an intentional API-surface change updates `docs/api.md`, repeat this
  review and record the new digest before publication.
