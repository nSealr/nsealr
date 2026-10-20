# Public SDK API review

API surface digest: `sha256:f9b54ad5243e155aa0cafb037f5b2d368cb9e86d8da15f429d06e0ea1b774b25`

Source: [generated API](api.md). This migration records a proposed pre-release
surface with the T01 wire2/profile cutover proposed for distinct review. It does not claim a new production-security,
physical-device, live-relay or browser qualification.

## @nsealr/sdk

The root and `@nsealr/sdk/browser` export browserProvider, client, core, policy,
protocol, qr and review namespaces. The explicit `@nsealr/sdk/node` entrypoint
adds framing, nip46 and host client helpers. The generated inventory records
all namespace members as well as entrypoint names, so member drift is checked.
Owned MIT runtime code and declarations are bundled. Exact third-party packages
retain their own distributions and license notices. No unpublished workspace
package is a production dependency. Internal declaration files are included for
type resolution, but package exports reject deep runtime access.

`@nsealr/dev-signer` remains private and test-only. The SDK does not expose
software signing helpers. Fixture loading and host serial port adapters stay
internal. Smartcard APIs are retired; unsupported card routes, old commands and
host acknowledgement bypasses are rejected before dispatch. Trusted device
review remains a signer responsibility; host review output is untrusted.

The browser provider validates requests and verifies successful signed-event
responses before returning them. Native messaging requires an injected exchange;
it does not install a native host, persist grants or authorize signing. Browser
client timeout, cancellation, request correlation and malformed-response checks
remain in force. Browser root does not export file-backed grant stores.

The Node client exposes strict secretless grant history, explicit pairing and
storage review/approval artifacts, request-bound route dispatch and response
verification. A supplied host review acknowledgement is unsupported. Route
selection is metadata only; an injected route dispatcher must enforce device
approval. Native-host execution requires the reviewed install digest and writes
only the approved new manifest through an injected writer. These interfaces do
not establish production storage, installer UX or device transport qualification.

Core owns Nostr serialization, event-id computation and signature verification.
Protocol owns bounded request/response validation and strict raw JSON parsing.
Policy rejects secret fields, wildcard or unsupported grants and invalid route
targets; it does not mutate authoritative device policy. QR and framing encode
validated payloads without signing or custody. Review renders untrusted previews.

The NIP-46 pure helpers parse already-decrypted payloads, produce digest-bound
connect review and approval artifacts, parse descriptor-only connection URIs,
verify secretless connection-token metadata, and enforce approved permission
subsets. The parser parses relay event envelopes and verifies signed relay event
ids/signatures without decrypting NIP-44 content. It evaluates relay request and
response steps only after plaintext is supplied and verifies signed-event result
ids/signatures. Those metadata relay request/response steps run without opening
relays or auth URLs. Pending metadata checkpoints do not restore a live session.

The explicit Node runtime has different side effects: Nip46SessionManager owns
an in-memory client transport key, and NostrToolsRelay opens relays. The manager
pins the authenticated transport author and resolves a separate curve-valid user
key through get_public_key before activation. expectedUserPubkey can constrain
resolution. Signed results bind that user key, the requested template, event ID
and signature. The remote signer owns user custody and approval.

Fresh request namespaces and monotonic counters prevent reuse. Pending requests
and unsettled publications default to 32, capped at 256; one unresolved
subscription acquisition blocks another. Timeouts default to 30 seconds, capped
at 300 seconds. Close is terminal and clears the owned key copy. Failed retries
retain counters; arbitrary adapter promises cannot be forcibly cancelled.
Metadata persistence never stores or restores the runtime secret. Raw JSON rejects
duplicate keys, trailing bytes and depth above 32. Message, encrypted content and
tag limits remain the existing nSealr profile limits. Response metadata v1 binds
result_pubkey independently of the transport author; it does not authenticate a
session on its own.

The actual packed artifact is installed outside the workspace. Node behavior,
browser bundling/execution without Node globals, strict TypeScript imports and
hidden-import rejection are mandatory. Browser-like VM execution is not installed
Firefox or Chromium qualification. Live relay and attached-device checks remain
explicitly resource gated. npm publication and trusted-publishing configuration
require the coordinator's later adoption; no package is published by this review.

The current device wire is `nsealr.signing.v2` with numeric2. Account and route
records use `nsealr.account.v1` and `nsealr.route-selection.v1`; local pairing,
external NIP46 and authorization domains retain their own revisions. Numeric1,
old account/route records and `get_signing_status` reject without fallback.
`parseReportedCapabilities` preserves bounded original-byte spelling and decoded
duplicate evidence. `resolveReportedCapabilities` uses only the exact locally
selected implementation manifest; full/reference forms cannot add immutable
semantics or omit necessary state to fit a transport. `parseLimitsManifest` and
`intersectMethodLimits` enforce finite applicable dimensions and aggregate bounds.

Support, configuration, availability and local verification stay distinct. No
wire field becomes evidence, physical review, approval or a production release.
The local service requires an application-owned current compatibility provider
for local dispatch, intersects actual adapter/device limits, binds selected
account/connection generation, and checks again before the operation write and
after response. Expiry/cancellation revokes the binding. Missing providers fail
closed; this API adds no automatic device attestation or provider scaffolding.
NIP44 primitive, verified context and the named NIP17/59 workflow are separate
eligibility axes; no compound message execution API is introduced.

For sign-event feasibility, a current local complete-page observation binds the
exact request digest, implementation, connection generation, review context and
geometry ID. Missing/stale/changed observations reject before writing, including
after opening a port. Four logical preview sections cannot stand in for this
count. The host does not duplicate the renderer, infer consent or qualify display
fit; the device/S03 owner retains complete inspection and its own bounds.
