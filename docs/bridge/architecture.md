# Architecture

`nSealr/companion` is the untrusted host-side software shared by all signer
lines.

## Responsibilities

- Construct signing requests from Nostr event templates.
- Move requests over selected transports.
- Verify signer responses against `nSealr/specs`.
- Provide CLI and automated harnesses before browser or GUI workflows.
- Reject mismatched event ids, pubkeys, signatures, and request ids.

## Trust Boundary

The companion must not be trusted with production private keys. A development
signer may exist only as an explicit test harness.

Before any production signer I/O, production browser-extension packaging, full
NIP-46 relay session, or file-backed persistent grant use is added, companion
code must pass the M4.5
pre-signing hardening gate. Signing-request validation, NIP-46 bridge
conversion, QR/serial decoding, and policy-file parsing must share explicit
nSealr v0 limits and deterministic rejection behavior. CLI commands should
only adapt file/argument I/O around package-owned validation logic.

The companion is infrastructure, not a first-class signer family. Per-solution
feature status lives in `nSealr/specs`
`vectors/features/signer-feature-matrix-v0.json`. When companion exposes a
feature used by multiple signer families, such as request validation, review
projection, policy decisions, transport framing, or response verification, it
must follow the shared `contract_id` instead of creating a host-only variant.

Browser extension, npm SDK, CLI, local app, local service, and full NIP-46
relay support are companion access surfaces. They must stay thin over
package-owned logic. In particular, a browser extension may expose NIP-07
`window.nostr`, but it must not store production signing material or implement
browser-local production signing. An npm SDK may expose reusable helper
packages, but it must not export test-only signing as a production path.

## Implemented Modules

- `apps/cli`: command-line entrypoint.
- `apps/browser-extension`: private browser-extension boundary scaffold. It
  owns strict internal message parsing and provider-backed request handling for
  `get_public_key` and `sign_event`, validates provider outputs before browser
  callers can trust them, derives sender-bound client identity before provider
  selection, can compose that identity with the native-messaging local-service
  provider path, can request digest-bound local-service pairing intents for the
  same identity, can project those intents into deterministic pairing and
  browser-origin permission review metadata without approving clients, and can
  create origin permission approval artifacts only after explicit local pairing
  digest confirmation. It has a pure background-controller boundary over
  injected native messaging with optional response timeouts and request-scoped
  cancellation, a pure runtime-message adapter that maps raw browser sender
  metadata into the internal sender shape before background handling, an
  injected runtime `onMessage` listener installer with explicit teardown and
  asynchronous `sendResponse` handling, and a pure page-provider boundary that
  maps NIP-07
  `getPublicKey` and `signEvent` calls to validated background requests, and
  has a pure page-bridge envelope and page-side requester adapter for future
  page/content-script messaging. It also has a pure content-script bridge
  handler for sender-bound background forwarding, a pure content-window event
  adapter for source/origin gating before forwarding, an injected
  content-window message-listener installer with explicit teardown and injected
  response posting, and a pure page-script bootstrap that installs the provider
  over an injected bridge exchange.
  It can build a minimal MV3 manifest with `nativeMessaging` as the only
  permission, and an opt-in explicit-origin content-script manifest profile
  that exposes only the packaged page script to those explicit origins while
  still omitting host-permission fields, broad URL matches, extension storage,
  grants, and key custody. Content-script package builds must also embed a
  reviewed origin-permission store covering the packaged origins and methods;
  this is static developer-artifact data, not browser storage. It does not yet ship full extension
  packaging, automatic content-script/page-script injection, packaged
  bootstrap/config loading, native-host installation, permission UI, persistent
  grants, or signer dispatch. Its packaged runtime entrypoints are checked by
  source import hygiene and an esbuild browser bundle smoke before installable
  package generation is allowed. The first package-build CLI writes an explicit
  output directory only after successful in-memory bundling, embeds a
  digest-approved secretless static route config in the background bundle, and
  requires reviewed origin-permission store data before content scripts can be
  packaged. It returns the shared native-host name, explicit route, manifest
  permissions, popup mode, activeTab usage, origin, optional embedded extension,
  and pairing metadata plus a package digest and per-file byte counts plus
  SHA-256 hashes, writes no extension storage, installs no native-host
  manifest, and remains a developer artifact until a full bootstrap/config UX
  is reviewed.
- `packages/core`: NIP-01 event id and BIP-340 verification.
- `packages/protocol`: schema validation, typed request/response models, the
  central nSealr v0 implementation limit profile used by companion parsers,
  and signing-status consistency checks so a signer cannot claim
  `signing_enabled: true` while still reporting missing gates or
  `signing_enabled: false` without reporting at least one blocker. Gate lists
  are also checked for duplicates. Response request ids must follow the same
  v0 profile as requests, and signed-event responses are checked against the
  same integer-safety, content, and tag resource limits before transport or CLI
  callers can treat them as accepted output.
- `packages/fixtures`: shared event, key, trusted-review,
  review-display-frame, review-detail-page, QR review-transcript, NIP-46
  payload, NIP-46 policy-file, NIP-46 connection URI, NIP-46 relay-event,
  NIP-46 relay-step, NIP-46 session lifecycle, NIP-46 session gate,
  account-descriptor, policy-profile,
  grant-descriptor, policy-change review, policy-decision, route-selection,
  source public-key proof, access-surface, feature-matrix, persistent-secret
  custody contract, limit-profile, and invalid hardening fixture loading.
  Package code also owns QR review-transcript fixture validation, including
  `scroll` buttons and rendered-frame `body_line_styles`, so the CLI does not
  duplicate that contract.
  Package code also validates feature matrices so shared feature `contract_id`
  drift and Raspberry/ESP32 stateless QR vault target drift fail in companion
  conformance checks.
- `packages/policy`: secretless account, route, recovery, policy, grant
  descriptor parsing, policy-change review generation, and pure
  policy-decision evaluation. This package owns anti-secret,
  anti-QR-automation, NIP-06 recovery source-fingerprint validation,
  anti-decrypt-grant, and audit-event decision checks,
  including runtime policy-decision request parsing, deterministic expiry,
  revocation, and rate-limit decisions from explicit grant-usage snapshots,
  shared `nsealr-route-selection-v0` response parsing, and digest-bound
  `set_policy` review pages for persistent device routes, so CLI/browser/SDK
  code does not grow a parallel policy parser. The package does not persist
  usage history, grants, or authoritative device policy. External NIP-46
  account descriptors remain external-policy metadata and cannot claim nSealr
  physical review, physical approval, persistent grants, or nSealr-managed
  scoped automation. The v0 nSealr-managed grant menu is intentionally limited
  to `sign_event` kind `1`; broader automated event kinds or methods remain
  future-spec work and must not be added ad hoc in an access surface.
- `packages/review`: deterministic event-template review summary generation
  for untrusted companion previews and conformance checks.
- `packages/dev-signer`: private test-only signing implementation,
  deterministic smartcard APDU simulator, and development signer transport. It
  is not a production signer route and must not become a dependency of
  publishable production packages.
- `packages/transport`: signer transport interface plus JSON file, JSON-lines
  stdio, serial-frame, and serial-line adapters. It is intentionally
  secretless and does not depend on `@nsealr/dev-signer`.
- `packages/qr`: v0 `nsealr1:` QR envelope encoding and decoding.
- `packages/framing`: browser-runtime-clean checksum-protected serial line
  framing draft with the shared v0 serial-frame byte limit. It is a direct
  protocol package for future WebSerial/WebUSB experiments, not a transport
  opener.
- `packages/smartcard`: APDU codec, provider-based PC/SC APDU transport
  boundary, `SmartcardSigner` boundary, and response verification for the
  display-less smartcard line. The codec rejects non-integer byte/status-word
  fields, non-`Uint8Array` payloads, and oversized short-APDU payloads before
  simulator or PC/SC transport. Test-only APDU simulation is private
  `@nsealr/dev-signer` code, not public smartcard API.
- `packages/nip46`: decrypted NIP-46 payload bridge for `get_public_key`,
  `sign_event`, local `ping`, local `switch_relays` no-change metadata, and
  conversion from nSealr responses back to NIP-46 result/error strings. It also
  validates requested permission strings
  and policy files, and parses `connect` messages into review intents,
  deterministic review pages, and digest-bound local approval artifacts for
  later policy work. It now parses NIP-46
  `kind:24133` relay event envelopes into sender/recipient/content metadata,
  while explicitly leaving relay I/O, NIP-44 decryption, grant creation, and
  signer dispatch outside this package boundary. It also evaluates relay
  request and response steps only after a future NIP-44 layer provides
  plaintext, reusing the same bridge-decision path for requests and
  shape-checking plaintext responses while binding public-key and signed-event
  result pubkeys to the relay event sender. Signed-event response results are
  also NIP-01 id checked and BIP-340 verified. Auth challenge responses expose
  only safe http(s) URL metadata without credentials or fragments for later UI
  and do not open that URL. Signed relay-event envelopes are NIP-01 id checked
  and BIP-340 verified, while the package still avoids opening relays,
  acknowledging `connect`, creating grants, dispatching signers, or persisting
  session state.
  It also evaluates a pending-session request gate for
  `approved_pending_ack` checkpoints: relay sender/recipient binding and
  expiry are checked, but signer dispatch is rejected with
  `connect_ack_pending` until a future acknowledged-session contract exists.
  Permission matching is present as a pure boundary and is pinned by shared
  permission policy fixture checks. Bridge decision output is also present: a
  permitted request can become a signer request, `ping` can produce a local
  response, `connect` can produce a review intent, and missing permissions
  produce deterministic NIP-46 errors before signer transport. Permission
  storage and grant UX remain separate layers.
- `packages/client`: local companion service request/response protocol,
  native-messaging frame codec, service status, pairing intent generation,
  shared local-client identity parsing, deterministic pairing-review
  projection, grant enforcement, a strict
  secretless JSON grant-store contract, digest-bound storage-location review
  and approval artifacts, secretless account-route selection, signer-request
  validation, grant-gated signer-request dispatch through an explicitly injected
  dispatcher, display-less `sign_event` external-review acknowledgement binding,
  signer-response verification, response validation, and a
  high-level client wrapper. The wrapper checks request-id correlation,
  malformed responses, operation-specific result types, and route selections
  through the shared `@nsealr/policy` parser before callers can trust
  native-messaging responses. Its dispatch wrapper can pass the same
  digest-bound external-review acknowledgement accepted by the service for
  display-less routes, so SDK, desktop, CLI, and native-messaging callers do
  not need to fork that smartcard safety gate. The dispatch operation remains
  unavailable by default and adds no real transport driver by itself. Shared
  route-refusal fixtures now pin that behavior across every route-selection
  vector: no dispatcher yields `signer_route_unavailable`, display-less
  smartcard dispatch requires matching external review acknowledgement first,
  and trusted-review routes reject that acknowledgement because review belongs
  to the signer route. The package also
  exposes a route-aware dispatcher registry helper so host apps can attach
  multiple explicit account/route/transport handlers without putting
  route-selection conditionals in browser, SDK, or CLI access surfaces. This is
  the shared client/service boundary for future browser extension, SDK, and
  desktop work. The async service handler is the reviewed path for future
  host-owned signer drivers that need asynchronous transport I/O; the
  synchronous handler rejects async dispatchers deterministically.
- `packages/browser-provider`: NIP-07 provider adapter for browser-extension
  packaging. It accepts an injected companion backend plus explicit client
  identity, validates public keys, converts `signEvent` inputs into nSealr
  signer requests, verifies signed responses, and stores no browser-side
  production keys. Its local-service backend adapter can read the selected
  account public key through authorized route selection and routes `signEvent`
  through local-service dispatch, returning deterministic signer-unavailable
  responses until an explicit signer route dispatcher is configured. Its
  browser native-messaging adapter is intentionally thin: it validates the
  native-host name, calls an injected `sendNativeMessage`, and relies on
  `@nsealr/client` for shared local-service response validation, deterministic
  timeouts, cancellation, and request-id correlation.
- `apps/browser-extension` route configuration is stricter than general
  account-route selection. A packaged NIP-07 bridge must name an explicit
  browser-dispatchable route type: `esp32_usb_nip46`,
  `custom_hardware_wallet`, or future `external_nip46`. Account-only package
  routes, stateless QR vault routes, and display-less smartcard routes are
  rejected before package review or build so the extension cannot imply a
  transport it cannot safely drive.
- `packages/sdk`: public namespace facade for app, browser-extension, and
  companion integrations. It excludes private test signing from the public
  package surface. Browser runtime code must use the reviewed
  `@nsealr/sdk/browser` subpath, which re-exports
  `@nsealr/browser-provider`, `@nsealr/client/browser`, and pure
  core/policy/protocol/QR/review helpers without pulling in the broader SDK root.
- `apps/service`: private native-messaging host scaffold over
  `packages/client`. It processes multiple length-prefixed service messages on
  one stdio session, accepts explicit in-memory authorization context in tests,
  can load explicit storage-approved read-only secretless grant/account JSON
  context files for developer and integration harnesses, can load explicit
  storage-approved secretless route-driver stores for exact account/route/USB
  serial-line developer dispatch, returns deterministic native-frame errors,
  and can print validated Chromium/Firefox native-host manifest JSON plus
  digest-bound dry-run install-plan and install-approval JSON through the
  shared `@nsealr/client` manifest builder. Its explicit install-execution path
  verifies the approval digest again, ensures only the reviewed parent
  directory, and writes only the reviewed manifest path with exclusive create
  semantics.
  It is intentionally secretless and does not write grant/account storage,
  perform production grant persistence, open relays, or include default or
  production signer transport drivers.

Each reusable package has its own `package.json`, source `src/index.ts`
entrypoint, and built `dist` JS/declaration export. Cross-package source imports
must go through `@nsealr/*` entrypoints, not relative paths into another
package's `src` directory. The repository verifier checks this boundary so
future extension, SDK, local-service, and CLI work cannot accidentally fork
validation or signing helper code.

## Access Surface Boundary

The intended access surfaces are:

- CLI: operator and lab harness over package-owned logic.
- Local companion service: future IPC/API boundary for browser extension,
  desktop UI, and high-level SDK clients.
- Browser extension: NIP-07 provider that forwards requests to companion and
  returns only verified results.
- npm SDK: public package set for clients and tools that need nSealr request,
  transport, policy, and verification helpers.
- NIP-46 relay service: encrypted remote-signer compatibility after session,
  grant, and policy contracts are ready.
- Desktop/operator UI: account, route, diagnostics, policy proposal, and audit
  surface over the same local service.

All of them must use the same request validator before contacting a signer
route and the same response verifier before returning signed events. None of
them may store production `nsec`, seed, mnemonic, passphrase, decrypted signing
material, or NIP-49 plaintext. Extension/session pairing data is still
sensitive and needs expiry, revocation, and origin/app binding before
production use.

Native messaging is the preferred first serious browser-extension transport to
the local companion. A localhost HTTP/WebSocket API remains research until
origin binding, CSRF protection, pairing, rate limits, and kill-switch behavior
are explicitly specified and tested. The M4.7 threat-model decision selects
native messaging for browser alpha because it avoids exposing an always-on
loopback service to ordinary web pages. Desktop, CLI, and SDK callers should
reuse the same local-service semantics rather than defining a separate security
model.

The first native-messaging scaffold accepts `service_status`,
`request_pairing`, `select_account_route`, `validate_signer_request`,
`dispatch_signer_request`, and `verify_signer_response`.
`@nsealr/client/browser` owns the browser-runtime local-service client
boundary, and `@nsealr/client/client-identity` remains the minimal
identity-only subpath. Browser extension, SDK, desktop, CLI, and native-host
code must reuse those contracts before deriving client ids, requesting pairing,
selecting account routes, or trusting pairing responses.
It rejects unsupported surfaces, non-origin URLs such as
`https://example.com/path`, deceptive localhost names, overlong app names,
invalid instance ids, and extra client fields. The service request parser also
rejects unsupported top-level request fields and unsupported per-operation
`params` fields before pairing, route selection, signer validation, or signer
dispatch can inspect payloads.
Pairing requests return a deterministic intent for later user review; they do
not approve the client. Validation and verification require explicit grants
supplied by the caller/test harness. When grant history is supplied, the latest
matching grant by `approved_at` wins, so newer revocation or narrower scope
cannot be bypassed by an older grant. Revoked, expired, missing, or
operation-scoped grants fail before signer payload handling. This lets browser,
SDK, and desktop code integrate against the authorization, validation, and
verification boundary before any signer I/O or persistent session state is
exposed. `@nsealr/client` now includes the caller-side wrapper for both object
exchange and native-messaging frame exchange; it validates service responses and
request-id correlation before returning them to higher-level callers.
The CLI `nsealr local review-pairing` command exposes the same deterministic
pairing-review projection for local/manual inspection. It validates the
digest-bound intent and writes review metadata only; it does not create grants,
approve clients, or write grant-store files.
The companion CLI also has `nsealr local approve-pairing`, which creates a
pairing approval artifact only after the caller supplies the reviewed pairing
digest. The artifact contains the approved grant metadata, but the command does
not append it to a grant store, choose storage locations, or contact signer
transports.
`nsealr local grant-store append-approval` is the first explicit grant-store
artifact builder. It validates a pairing approval artifact through
`@nsealr/client`, creates or extends a caller-supplied secretless grant-store
JSON object, and writes only a requested output path already covered by a
storage approval artifact. If an input grant store is supplied, the same storage
approval must cover that input as read-only. It never chooses a default storage
location, overwrites an existing output file, mutates the input store, approves
clients by itself, or contacts signer transports.
`nsealr local grant-store revoke-client` appends a latest-client revocation to
a new output grant-store artifact. Revocation is selected by
`client_id + origin + surface`, keeps prior grants in the history, and fails
deterministically if the storage approval does not cover the read-only input
and new output paths, if no matching grant exists, or if the latest matching
grant is already revoked.
`nsealr local review-storage` renders digest-bound review metadata for explicit
grant/account/route-driver store paths. `nsealr local approve-storage` then
creates an approval artifact only after the caller supplies the reviewed storage
digest. These commands require absolute, expanded, non-relative paths and
record read-only versus new-output access intent, but they do not choose default
paths, approve clients, dispatch signers, or turn reviewed paths into
production storage. Grant-store artifact builders consume those approvals before
writing requested output paths, and still refuse to replace existing output
files.
`nsealr local native-host` is the public CLI boundary for browser native-host
onboarding. It renders Chromium/Firefox manifests and digest-bound install
plans without installing anything, creates approval artifacts only after the
reviewed install digest is supplied, and executes only the approved manifest
write with exclusive-create semantics plus an execution report.
The private `@nsealr/service` app now runs a tested multi-message native-host
stdio loop, so a future browser extension can keep one native-messaging port
open and receive one deterministic response per length-prefixed service
request. It keeps equivalent native-host artifact helpers for service-level
harnesses, but operator-facing onboarding goes through the companion CLI and
the shared `@nsealr/client` manifest builder.
`@nsealr/client` also defines
the persistent grant-store JSON contract used to serialize approved and revoked
local client grants without secret material. The private service app can now
load explicit read-only grant/account context files for local harnesses only
when a digest-bound storage approval artifact covers those paths. It can also
load an explicit secretless route-driver store for exact account/route/USB
serial-line dispatch through the async local-service boundary only when the
same storage approval covers the driver-store path and a loaded account-store
contains a matching account id, route type, and transport. That driver store
does not contain keys, does not approve clients, does not choose default paths,
does not make QR vaults connected signers, and rejects remote, relative, or
whitespace-tainted serial path forms before opening only supported local serial
device identifiers. Per-driver timeout and ignored-log controls are bounded at
parse time. Serial-line open, timeout, protocol, I/O, close, and fallback
failures are normalized into deterministic local-service transport error codes
before they cross the service boundary.
Install approvals still keep `writes_files=false`; install execution is a
separate digest-confirmed gate that reports `writes_files=true` only after the
reviewed manifest writer runs. Default storage locations, grant/account file
writes, relay sessions, browser packaging, and production driver acceptance
remain separate gates.

The browser-provider package is intentionally one layer above this service
boundary. Each provider instance is bound to a client identity so the future
native-messaging backend can route pairing, revocation, and origin decisions
without inferring identity from unsigned browser data. It does not include an
extension manifest, native-host install flow, permission UI, account routing,
persistent grants, NIP-04, NIP-44, or relay sessions. It is the package-level
contract that a future extension will expose as `window.nostr`.
The first local-service backend adapter uses the same local-service route
selection and dispatch operations. It still returns deterministic
signer-unavailable responses for `signEvent` unless the local service host
injects a reviewed signer route dispatcher.
The package also includes a browser native-messaging local-service client
adapter over an explicit `sendNativeMessage(hostName, message)` function. This
keeps browser API integration thin while reusing `LocalServiceClient` response
validation, optional deterministic response timeouts, request cancellation,
request-id correlation, and the shared native host name and manifest contract
exported by `@nsealr/client`. `dispatchSignerRequest` also carries the explicit
external-review acknowledgement option for display-less routes through this same
client boundary, so access surfaces cannot create a separate smartcard dispatch
path. Timeout and cancellation behavior lives in the client package so SDK,
browser extension, and future desktop callers cannot fork that boundary.
It does not install native-host manifests, persist grants, or open signer
transports.
The background browser entrypoint adapter is the browser-like wrapper over the
background controller and runtime-message listener. It accepts an explicit
runtime object with reviewed `onMessage` and `sendNativeMessage` capabilities,
installs the runtime listener, and forwards native-messaging calls through the
same local-service client path. It now accepts either an already parsed route
request or a secretless `nsealr-browser-extension-route-config-v0` selected
account config that is parsed into a `sign_event` route request before listener
installation. It does not read global browser objects, write extension storage,
create grants, dispatch signers, or hold key material.
The packaged background source entrypoint
`nsealr-background-entrypoint.ts` is a thin launcher over that reviewed adapter:
it accepts an explicit packaged global scope, resolves an unambiguous
`browser.runtime` or `chrome.runtime`, requires the secretless route config, and
then installs the background listener. It still does not read extension storage,
create grants, dispatch signers, or hold key material.
The private `@nsealr/browser-extension` app now defines the internal extension
message boundary for `get_public_key` and `sign_event`. The parser rejects
unsupported NIP-07/NIP-44/NIP-04-style methods, malformed request ids, extra
fields, and unsafe event templates before provider handling. The first handler
is still browser-API-free and receives an injected provider; it validates
public keys, checks signed events against the original request, and returns
secretless deterministic errors for malformed requests or malformed provider
outputs.
The same app now has a browser-API-free page-provider boundary that exposes the
minimal NIP-07 `getPublicKey` and `signEvent` methods over an injected
background requester. It constructs only validated internal extension messages,
rejects unsafe event templates before contacting the background boundary,
verifies signed event responses, forwards cancellation signals, and can install
the frozen provider on an explicit target without overwriting an existing
provider. It does not inject content scripts, write browser storage, create
grants, or hold key material.
The page-bridge boundary defines a validated `page_to_extension` envelope over
the internal browser-extension request format and an `extension_to_page`
response envelope over the internal response format. It rejects malformed
directions, mismatched request ids, unsafe inner requests, and mismatched
background responses before a future content script can forward data across the
isolated-world boundary. The matching page-side requester adapter wraps
validated internal requests in that envelope, validates the returned bridge
response, forwards cancellation signals through the injected bridge exchange,
and rejects malformed input before the bridge is contacted. It has no
`postMessage` listener, no browser runtime dependency, no storage, and no key
custody.
The content-script bridge handler composes the page-bridge parser with an
injected sender-aware background requester. It binds each accepted page
envelope to the explicit sender object supplied by the future browser adapter,
forwards cancellation as a background request option, and rejects malformed or
already-cancelled page messages before the background is contacted. It has no
`postMessage` listener, no browser runtime dependency, no storage, no grants,
and no key custody.
The content-script runtime requester is a thin adapter for the real
content-script-to-background hop. It accepts an injected runtime-message sender,
forwards the validated internal request, combines bootstrap and per-request
abort signals, and rejects already-cancelled or in-flight-cancelled requests
without relying on global `browser`/`chrome` APIs. It still performs no
storage, grants, signer dispatch, or key custody.
The content-script runtime bridge bootstrap composes the injected window
listener with that runtime requester. It wires expected page source, exact page
origin, explicit sender metadata, injected runtime-message sender, injected
response poster, cancellation, and diagnostics into one install/dispose handle
without touching global browser APIs, storage, grants, signer dispatch, or key
material.
The content-script entrypoint composer is the pre-packaging adapter for the
future browser content script. It injects the reviewed page script through
explicit document and extension-URL dependencies, installs the runtime bridge
through explicit window/runtime/poster dependencies, disposes both pieces
together, and removes the injected page script if bridge installation fails.
It still does not call global `document`, `window`, `browser`, or `chrome`
APIs directly and does not write storage, create grants, dispatch signers, or
hold key material.
The content-script browser entrypoint adapter is the first browser-like
composition over that composer. It accepts explicit document, page-window,
location, and runtime-like dependencies; derives the reviewed page origin,
runtime URL resolver, runtime message sender, and response poster; and then
delegates to the pure composer. It still does not read global browser objects,
choose storage locations, create grants, dispatch signers, or hold key
material. Trusted runtime sender identity remains a background/runtime-message
boundary, not content-script metadata.
The packaged content-script source entrypoint
`nsealr-content-script-entrypoint.ts` is the matching launcher over that
adapter: it resolves document, window, location, and an unambiguous
`browser.runtime` or `chrome.runtime` from an explicit packaged global scope
before installing the page-script injector plus runtime bridge. It does not add
host permissions, browser storage, grants, signer dispatch, or key custody.
The content-runtime adapters are the next browser API boundary below that
composer. They turn an injected runtime-like object into a reviewed extension
resource URL resolver and a runtime-message sender, reject unsafe resource
paths before `runtime.getURL`, and reject already-cancelled sends before
`runtime.sendMessage`. They do not read or write extension storage, register
listeners, dispatch signers, or hold key material.
Page-window and content-window boundaries share one page-origin validator:
HTTPS page origins are accepted, local HTTP origins are accepted for developer
harnesses, and path/query/fragment URLs or non-page schemes are rejected before
use as trusted bridge origins.
The content-window event adapter handles one already-received window message at
a time. It accepts only messages from the expected page source and normalized
page origin, ignores unrelated data without responding, and forwards only
nSealr page-bridge envelopes to the content-script bridge handler. It still
does not register a `postMessage` listener, call `window.postMessage`, use
browser runtime APIs, write storage, create grants, or hold key material.
The content-window listener installer is the next thin adapter around that
event handler. It registers a `message` listener only on an injected target,
returns an explicit `dispose()` handle, posts accepted bridge responses only
through an injected response poster, and reports malformed nSealr envelopes
through an injected error callback. If an accepted page-bridge request reaches
the listener and the downstream background path fails unexpectedly, the
listener reports the internal exception through that callback and posts a
generic `content_window_bridge_failed` response back to the page instead of
leaving the page-side provider waiting for a timeout. It still does not touch
global `window`, browser runtime APIs, extension storage, grants, provider
injection, signer dispatch, or key material.
The content-window response poster is the reviewed default poster for that
listener. It sends extension responses only through the `postMessage` function
on the accepted message source and only to a normalized HTTPS or localhost page
origin. It does not register listeners, touch global `window`, use browser
runtime APIs, write storage, create grants, dispatch signers, or hold key
material.
The page-window bridge exchange is the matching page-side adapter over an
injected window-like target. For each request it registers a temporary
`message` listener, posts the validated `page_to_extension` envelope only to
the exact reviewed page origin, ignores unrelated sources, origins, request
ids, and outbound envelopes, accepts only the matching `extension_to_page`
response, and removes the listener on response, abort, timeout, or posting
failure. It does not touch global `window`, browser runtime APIs, storage,
grants, signer dispatch, or key material.
The page-script bootstrap composes that requester with the NIP-07 page
provider and explicit-target installer. It gives the future injected page
script a single pure entrypoint while still requiring an injected bridge
exchange and still refusing to overwrite an existing `window.nostr` provider.
It does not include an injection mechanism, content-script registration,
browser runtime dependency, storage, grants, or key custody.
The page-script window-provider bootstrap is the page-side convenience wrapper
over the same provider installer and the page-window bridge exchange. It
installs the NIP-07 provider on an explicit target, posts through the injected
window-like bridge target, enforces exact origin and source filtering through
that exchange, and still contains no direct browser API dependency, storage,
grants, or key material.
The page-script browser provider entrypoint adapter is the browser-like wrapper
over that page-side bootstrap. It accepts an explicit page window and location,
derives the reviewed page origin, installs NIP-07 on that explicit target, and
uses the page-window bridge for requests. It still does not read global browser
objects, write storage, create grants, dispatch signers, or hold key material.
The packaged page-script source entrypoint
`nsealr-page-script-entrypoint.ts` is the matching launcher over that adapter:
it resolves the explicit packaged window and location scope and installs only
the reviewed NIP-07 page-window provider. It has no extension runtime, storage,
grants, signer dispatch, or key custody.
The page-script injection helper is the content-script-side DOM adapter. It
accepts only explicit document and extension-URL resolver dependencies, injects
the reviewed packaged page-script entrypoint resource as a module script with
a stable element id, rejects duplicate targets, unsafe script filenames,
unsupported URL protocols, wrong URL paths, and missing parents, and exposes
explicit teardown. Packaged extension filenames are intentionally distinct from
the internal pure modules such as `background.js`, `content-script.js`, and
`page-script.js`, so a future bundle cannot accidentally point the manifest or
page injection at a module that only exports helpers. It does not call global
`document`, `window`, `browser`, or `chrome` APIs directly.
The browser-extension package-plan boundary is a deterministic pre-bundling
artifact. It joins the reviewed manifest, shared native-host name, packaged
output filenames, and source launcher paths into
`nsealr-browser-extension-package-plan-v0`, then rejects drift such as
unprofiled storage permission, host permissions, native-host name mismatch,
mismatched background output, mismatched popup output, or mismatched
content-script output. It deliberately does not build an installable extension,
install native-host manifests, write browser storage, dispatch signers, or hold
key material.
The private `@nsealr/browser-extension` app exposes this boundary through
`pnpm --filter @nsealr/browser-extension package-plan -- --target ...`, which
prints JSON to stdout only. The command can now also render the explicit
extension-storage origin-approval manifest profile through
`--origin-permission-mode extension-storage`, requiring reviewed content-script
origins and pinning `activeTab` plus `storage` before package build. With
`--review`, it wraps the exact package plan in a digest-bound review envelope
that must be supplied intact to `package-build`. It still has no output-path
option and performs no filesystem install or browser-storage mutation.
The `route-config-review` command first projects the selected account/route
into `nsealr-browser-extension-route-config-review-v0`, binding the exact
secretless route config to a digest without writing storage or approving a
client grant. The `route-config-approve` command turns that review into a
digest-confirmed approval artifact after the reviewed route-config digest is
supplied. Its `package-build` command then writes only a reviewed developer
artifact to a new explicit output directory after in-memory bundling succeeds,
the supplied `package-plan --review` artifact matches the package plan being
built, and the supplied route-config approval matches the embedded route config. The
output directory must either be outside the companion source tree or a child of
`release-artifacts/browser-extension/`, so a package rehearsal cannot create
unreviewed files under `apps/`, `packages/`, docs, scripts, or tests. The
returned `nsealr-browser-extension-package-build-v0` result includes the
reviewed package-plan digest, route-config digest, selected account/route,
shared native-host name, content-script origins, optional embedded extension
id, local pairing digest, manifest permissions, popup mode, origin-permission
mode, activeTab usage, package digest, and per-file byte counts plus SHA-256
hashes for the manifest, packaged popup HTML, and bundled entrypoints. Lab
integration verifies both the explicit binding metadata and the files that were
actually written. It still installs no native-host manifest, writes no extension
storage, creates no grants, dispatches no signers, and holds no key material.
`package-verify` is the package-owned audit path for an already written
developer artifact: it requires the digest-bound `package-plan --review`
artifact in addition to the package-build result, parses both artifacts,
recomputes the package digest, rejects source-tree artifact paths outside
`release-artifacts/browser-extension/`, rechecks the exact manifest against the
externally reviewed package-plan digest and plan body, the exact popup HTML
against the deterministic template, popup bundle binding to the reviewed
`popup_mode`, native-host binding, selected route metadata, origin-permission
metadata in the packaged background script, content-script bridge entrypoint
binding, page-script provider entrypoint binding, file hashes, byte counts,
exact output directory contents, and bundled JavaScript browser-runtime
hygiene, and writes no files.
The same private app has a browser-API-free sender context boundary. The future
adapter must pass only sanitized `extension_id`, `page_origin` or `page_url`,
and optional reviewed app name. The boundary strips full URLs down to origins,
rejects mismatched origin/URL pairs, rejects deceptive localhost names and
extension-page origins, and creates the `browser_extension` local client
identity through `@nsealr/client/browser`. It stores no browser-side
production secrets and does not grant a page by itself.
The sender-aware handler composes both boundaries before provider selection: it
parses the internal request, validates sender-derived identity, and only then
asks the injected provider factory for a provider bound to that client context.
Malformed requests and malformed senders return deterministic secretless errors
without provider selection or signer I/O.
The runtime-message adapter is the pure boundary a future
`browser.runtime.onMessage` listener will call. It copies only sender id,
origin, and URL into the internal sender shape, ignores unrelated runtime
metadata such as tab or frame fields, validates the result through the same
sender parser, returns deterministic `invalid_sender` responses on sender
failure, and forwards request-scoped cancellation to the background controller.
It does not register browser listeners, call browser runtime APIs, write
storage, create grants, or hold key material.
It can emit `nsealr-browser-extension-pending-request-state-v0` snapshots
through an injected lifecycle for future visible pending/cancel UI. Those
snapshots expose only request id, method, extension id, page origin, optional
app name, selected route account/type when configured, status, and timestamps;
they do not include event templates, key material, grants, storage writes, or
signer dispatch. The lifecycle has a
small explicit active-request bound before publishing state. The same lifecycle
owns the per-request cancellation hook: cancelling an active snapshot aborts
the in-flight native-message path and emits one `cancelled` state instead of
leaking a later duplicate rejection. The background entrypoint owns an
in-memory lifecycle by default, and extension UI can query or cancel it through
separate `nsealr-browser-extension-control-v0` `list_pending_requests` and
`cancel_pending_request` runtime messages. Those messages accept
extension-internal senders only; page-origin senders cannot list or cancel
pending requests. A popup-control client now wraps those messages over an
injected `runtime.sendMessage`, validates response envelopes and secretless
active pending-state snapshots, rejects settled states and request-id
mismatches, and exposes only list/cancel operations for the packaged action
popup. The popup view renders
only safe pending-state metadata: request id, method, status, page origin,
optional app name, selected route account/type, timestamps, and explicit
no-key/no-event-payload chips. The
same internal control protocol can also request browser-origin permission
review metadata from the background controller for an explicit sanitized page
sender. That path does not approve the origin, write browser storage, create
grants, inject a provider, dispatch a signer, or carry key material. The popup
path is not a storage, grant, native-host installation, or signer-dispatch
boundary.
The runtime-message listener installer is a thin adapter over an injected
`runtime.onMessage`-like target. It registers exactly one listener, returns
`true` for asynchronous `sendResponse` delivery, sends deterministic responses
only through the injected responder, reports responder failures through an
injected error callback, and provides explicit teardown. It still does not
touch global `browser`/`chrome` APIs, extension storage, grants, signer
dispatch, or key material.
The origin permission boundary projects digest-bound local-service pairing
reviews into page-visible NIP-07 method effects and parses them before any
approval artifact is created. Approval requires the exact reviewed local pairing
digest, records the approved page-visible methods, and only authorizes a future
provider-injection step. It does not create local-service grants, write browser
storage, inject a provider, or contain key material. The matching
`nsealr-browser-origin-permission-store-v0` contract accepts only already
approved origin artifacts, sorts them deterministically, rejects duplicate
`origin + extension_id + local_pairing_digest` records, and answers exact
origin/extension/pairing-digest/method lookups. That store contract is still
pure data validation: its upsert/revoke helpers replace or remove exact
approved-origin records without calling browser storage APIs, choosing a
persistence backend, creating grants, dispatching signers, or storing secrets.
The private browser-extension CLI exposes the same approval, empty-store,
upsert, and revoke operations as stdout-only artifact commands. Those commands
let operators and tests produce reviewed JSON without adding browser storage,
default paths, grant creation, provider injection, signer dispatch, or key
material.
The origin-permission storage adapter is the first reviewed persistence
boundary for that data shape. It accepts only an explicit injected storage area,
reads and writes one fixed storage key, returns a deterministic empty store
when the key is absent, validates stored artifacts through the same parser, and
records every write as secretless extension-storage metadata. It still does not
read global browser APIs, create grants, inject a provider, dispatch signers,
or store production secrets; packaged manifests do not request storage
permission by default.
The packaged browser-global resolver is the only reviewed place that can adapt
`browser.storage.local` or `chrome.storage.local` into that injected storage
area. It rejects ambiguous `browser`/`chrome` globals, requires `get` and `set`
methods, and keeps the storage key/parser boundary in the package-owned
origin-permission storage module. Package builds use that resolver only for the
explicit storage-backed origin-approval profile.
The matching origin-permission review card is also pure: it renders the
already-validated review, the full pairing digest, requested method effects,
and approve/reject actions over injected controls. It accepts approval only
when the injected control returns a parseable approval artifact, and it still
does not persist storage, create grants, inject a provider, dispatch signers,
or hold key material.
The popup active-tab origin selector is another pure boundary for future
approval UI. It queries an injected `tabs` API for exactly one active tab,
normalizes the tab URL through the same sender/client-identity parser, and
returns secretless page-origin metadata plus a sender object suitable for the
existing background request path. It does not add manifest permissions, read or
write browser storage, create grants, inject a provider, dispatch signers, or
handle key material.
The default package does not include this permission surface; the
storage-backed origin-approval package profile requests `activeTab` explicitly
so the popup can read the active tab URL only after the user opens the action
popup.
The active-tab origin permission review orchestrator composes that selector
with the popup control client. It requests review metadata for the normalized
active-tab sender, parses the returned review, and rejects origin or extension
id mismatches, app-name mismatches, unsupported result fields, or
authorizing/secret-carrying control results before any card rendering or
approval path can consume it. It is still review-only and does not write
browser storage, create grants, inject a provider, dispatch a signer, or carry
key material.
The popup origin-permission view composer binds that orchestrator to the
existing approval card and popup refresh surface. It renders exactly the
reviewed active-tab origin state, delegates digest-bound approval/rejection to
injected controls, reports errors through the popup status/list region, and
does not itself call browser storage APIs, create grants, inject a provider,
dispatch a signer, or handle key material. The extension-internal control
protocol can now carry that reviewed origin permission plus the reviewed local
pairing digest back to the background controller. Approval constructs the
approval artifact in the background and writes the approved-origin store only
through an explicitly injected origin-permission storage adapter; missing
storage, digest mismatch, malformed storage-write metadata, or page-origin
senders fail deterministically without native messaging or signer dispatch.
The sender-aware request handler can also consume that approved-origin store as
an injected authorization gate. The gate accepts either a static reviewed store
or an async injected store loader, then checks the exact
origin/extension/pairing-digest/method tuple after request and sender parsing
but before provider selection, native messaging, route selection, or signer
dispatch. Denied, stale, malformed, ambiguous, or unavailable
origin-permission state returns `origin_permission_denied` deterministically.
The browser-like background entrypoint exposes the same injected gate, so
packaged runtime handling can be tested without introducing browser storage or
global browser APIs. The packaged background entrypoint forwards that option
rather than dropping it at the launcher boundary.
Package builds now have two origin-permission gate modes. The default embedded
mode keeps the reviewed approved-origin store in secretless background gate
data and requests no storage permission. The explicit `extension_storage` mode
does not embed approvals: it requests `storage`, resolves the reviewed storage
adapter at runtime, loads the store before provider selection, and lets the
action popup write new approvals only through the digest-confirmed background
approval path. Storage-backed packages bind approvals to the browser runtime's
actual extension id at runtime, so unpacked Chromium development builds do not
fail because their runtime id differs from reviewed package metadata. A
build-time extension id is optional metadata for `extension_storage` packages
and remains mandatory only for embedded-store content-script packages, where
the reviewed store must be keyed before packaging.
Build-time side effects remain unchanged: package builds write only package
files, never extension storage, grants, signer output, or native host
manifests.
Its manifest builder is intentionally restrictive: the default Chromium
manifest omits host permissions, optional host permissions, content scripts,
web-accessible resources, and storage; Firefox manifests require an explicit
reviewed extension id and otherwise follow the same zero-host-permission
boundary. An opt-in content-script profile may list explicit reviewed origins such as
`https://example.com/*` or local development origins such as
`http://localhost:5173/*`, but it rejects `<all_urls>`, wildcard schemes,
wildcard hosts, non-local `http`, duplicate matches, host-permission fields,
and implicit storage. When content scripts are enabled, the manifest exposes
only the packaged page-script entrypoint as a web-accessible resource for those
same explicit matches so page injection can work without granting wider host
access. A separate explicit origin-approval profile may add only `activeTab`
and `storage` for popup-mediated browser-origin approval; it still rejects host
permission fields and broad URL access. Origin injection and durable extension
metadata remain blocked on production permission UX.

Executable SDK examples live in private app `@nsealr/sdk-examples`. They are
not another access surface and do not own production behavior. Their role is to
prove that a consumer can use the built public package entrypoints for request
validation, QR envelopes, local-service calls, browser-provider integration,
the browser-safe SDK facade, and already-decrypted NIP-46 decisions without
importing private test-only signing code or storing secrets. The
browser-provider example consumes the shared access-surface vector, so
SDK-facing examples stay pinned to the same secretless local-service
route-selection and signer-unavailable contract as package tests.
The public package import-hygiene gate checks production source separately from
package manifests and tarball contents. It rejects `@nsealr/*` imports that do
not resolve to reviewed public packages or exported subpaths, rejects relative
imports that escape the package `src` boundary, and keeps private apps plus the
test-only signer package out of production package code.

## Current CLI Flow

The M2 CLI flow is:

1. Build a request from an unsigned Nostr event template.
2. Produce a development response with an explicit software test key.
3. Verify the response against the original request before any downstream use.

The same commands support JSON files and v0 `nsealr1:` QR envelope files so the
desktop companion can drive the Raspberry QR vault flow before camera/display
hardware is integrated.

`nsealr review-request` can render the same deterministic review JSON from a
JSON or QR `sign_event` request. With `--screen-review` it emits the
digest-bound screen-page model; with `--detail-pages` it emits the complete
constrained-display detail-page model used by Raspberry and ESP32 review UI
tests. Detail-page rendering defaults to the T-Display S3 sized profile and
accepts explicit title/body/compact line limits so lab and device adapters can
compare the same display envelope. These modes are deliberately labeled as
untrusted previews: they help users and automated tests see what a conforming
signer should display, but approval authority still belongs to the vault,
firmware, or card line holding the key.

The development signer exists only for local testing. Production signer lines
must replace it with a hardware, vault, or smartcard transport while preserving
the same request/response verification boundary.

## Transport Boundary

Every transport implements a single `exchange(request)` contract. Transport
adapters are responsible for moving JSON request and response envelopes only.
The companion remains responsible for validating request/response shape and
cryptographically verifying successful signed-event responses after transport
completion.

The shared transport boundary now enforces that verification before returning
from `exchange`: request shape is checked before sending, response shape and
`request_id` are checked after receiving, and successful `sign_event` responses
must pass NIP-01 event-id and BIP-340 signature verification against the
original request. Error responses such as `signing_disabled` can still return
as valid refusals.

Trusted-review vectors are loaded from `nSealr/specs` so host tools and
device implementations can agree on what must be shown before approval. They do
not make the companion trusted; they are conformance data for signer UIs.

Review-display-frame vectors are loaded and shape-checked as bounded rendering
contracts for small trusted screens. The companion treats them as conformance
data for Raspberry and ESP32 adapters, not as host-side approval authority.

Review-detail-page vectors are also loaded and shape-checked as complete
physical review-page contracts for constrained signer displays. They preserve
the shared `approval_digest` but pin scroll windows, line styles, continuation
indentation, visible JSON-style escapes for decoded control characters, and
explicit codepoint fallback separately from the digest-bound `screen-pages`
model. The companion can render these pages for previews and cross-repo
comparison, but still treats them as conformance data, not as a trusted
approval surface.

QR review-transcript vectors are also loaded and shape-checked by
`nsealr fixture verify`. They bind raw QR input to frame/button/decision
sequences for Raspberry and ESP32 adapter tests; the companion treats them as
conformance data, not as trusted approval authority. The transcript validator
lives in `packages/fixtures`, and `apps/cli` only calls it while iterating the
loaded fixture set.

NIP-46 payload vectors are loaded and verified by `nsealr fixture verify` so the
host bridge and shared specs agree on decrypted `get_public_key`, `sign_event`,
local `ping`, response mapping, and permission policy behavior before relay and
encryption work begins.

NIP-46 policy-file vectors are loaded and verified by `nsealr fixture verify` so
explicit approved-permission inputs stay normalized across specs, companion,
and lab integration. Package code owns the parser; the CLI only reads files and
passes parsed policies into bridge decisions. They are read-only conformance
files, not a grant store.

Account, policy, and grant descriptors are loaded through `packages/policy`.
The companion may keep labels, public keys, signer routes, recovery
descriptors, capabilities, policy ids, and scoped grant metadata. It must not
store production `nsec`, mnemonic, seed, passphrase, NIP-49 ciphertext, or raw
private key material. The descriptor parser is closed-schema at the record,
route, capability, policy-profile, grant, client, permission, and rate-limit
levels, so unsigned metadata cannot silently alter route or policy meaning.
Stateless QR vault routes remain manual-only and cannot receive persistent
grants. Display-less smartcard routes also remain manual-only; they require
explicit external review acknowledgement and cannot claim trusted device review
or persistent grant automation. External NIP-46 routes remain external-policy
metadata and cannot receive nSealr-managed scoped automation grants. The local
service accepts that acknowledgement only as
`nsealr-external-review-acknowledgement-v0`, only for display-less
`sign_event`, and only when its `approval_digest` equals the digest recomputed
from the request; acknowledged metadata is rejected on routes with trusted
device review.

Policy-change review vectors are also consumed through `packages/policy`.
Persistent-device account descriptors start on
`policy-manual-only-persistent-device`; switching to scoped automation is a
secretless `set_policy` proposal that renders deterministic device-review
pages and an approval digest. The companion can carry the proposal, but it does
not make the policy authoritative, write a grant store, or bypass local device
approval.
The CLI exposes only a thin `nsealr policy review-change` file adapter over the
same package function. That adapter now requires the account descriptor,
current policy profile, proposed policy profile, and proposed grant descriptors
that define the proposal context. Rejection happens before output is written
when the proposal does not match that context, and the command still does not
install policy or create grants.

Route-selection vectors are also consumed through `packages/policy`. The
selector is pure and secretless: it accepts parsed account descriptors plus a
requested account/method and returns selected route metadata only. It does not
open transports, create grants, approve clients, dispatch signer I/O, or claim
route readiness. Route-selection request and response parsing also live in
`packages/policy` so browser extension, local service, CLI, SDK, and future UI
code do not fork account-id, route-type, repository, custody, transport,
review, policy-support, or secret-material validation.

Access-surface vectors are loaded through `packages/fixtures` and consumed by
browser-provider tests. The current shared vector pins the NIP-07 browser
provider over local companion service route selection: an authorized browser
client can read the selected public key, while `signEvent` without an explicit
host signer dispatcher returns a deterministic `signer_route_unavailable`
protocol response. The vector is secretless and does not create grants, store
keys, install a browser extension, or enable production signing.
External NIP-46 bunker routes are treated the same way at this layer: they are
secretless external adapter metadata, not a built-in relay session, NIP-44
state machine, permission grant, or companion-owned key vault. The local
service can pass such a selected route to an explicitly injected dispatcher,
but it returns deterministic route-unavailable errors when no adapter has been
provided.

Those descriptors model the resulting signing public key and route. The
mnemonic, BIP-39 passphrase namespace, standalone `nsec`, device slot,
smartcard slot, or external bunker is a key source or route; policy attaches to
the resulting public key. Companion can prepare a policy proposal and transport
it, but a persistent nSealr device must review and accept authoritative
policy changes locally before they affect signing.

Policy-decision vectors are also consumed through `packages/policy`. The
current evaluator is pure and stateless: it accepts an explicit policy profile,
explicit grant descriptors, and an explicit request snapshot, then returns a
deterministic allow, deny, or manual-review decision plus a
`nsealr-grant-audit-event-v0` object. It deliberately does not create a grant
store, persist approvals, acknowledge NIP-46 `connect`, open relay sessions, or
contact signer transports.

The current scoped-automation fixtures are deliberately minimal conformance
data. They prove bounded decisions, denial, manual-review routing, revocation,
expiry, rate limits, and audit-event shape before grant storage exists. They do
not introduce a separate grant decision mode: one-use behavior is represented by
a scoped grant whose rate limit allows one use. These fixtures are not the
final product policy menu and should not grow into companion-owned rule-engine
state. The policy profile vocabulary is closed in package code, so new
manual-review requirements, forbidden-permission names, or risk-tier strings
cannot be treated as live semantics by an access surface. These fixtures also
are not the default account policy for persistent nSealr devices; a reviewed
policy-change proposal must activate them.

Pre-signing hardening vectors are the companion's rejection oracle for unsafe
input. They must be evaluated before signer transport, dev signing,
smartcard-sim signing, or NIP-46 routing can proceed, and failures must not
write output artifacts. The same invalid-vector suite also covers unsafe
signed-event response payloads so a real device output cannot bypass the v0
integer-safety, content, and tag limits after signing.

The current adapters cover these development paths:

- `DevSignerTransport`: in-memory test signer in private `@nsealr/dev-signer`
  for deterministic harnesses.
- `JsonFileTransport`: file handoff for QR vault and offline workflow tests.
- `JsonLineStdioTransport`: one-shot process bridge for external signer
  adapters and future hardware simulators. It bounds the pre-newline response
  buffer and captured stderr before returning or reporting process output, and
  terminates silent signer processes after a bounded response timeout.
- `SerialFrameTransport`: one-shot `nsealr1f:` request/response exchange for
  USB-serial, UART, and firmware smoke-test adapters. It treats
  `nsealr1f:error` as a transport diagnostic and includes the device error code
  in the thrown error instead of returning it as a signer response.
- `SerialLineTransport`: newline-oriented serial transport boundary with an
  injected port. It writes a validated `nsealr1f:` request frame, skips
  non-protocol device log lines, normalizes `LF`/`CRLF` line endings, rejects
  stalled writes and silent ports with deterministic timeouts, then returns
  through the same response shape, request-id, and signed-output verification
  gate as `SerialFrameTransport`.
- `SerialLineStreamPort`: dependency-free Node stream adapter for the
  serial-line boundary. It buffers chunked readable-stream output into complete
  lines, rejects any buffered line that exceeds the shared v0 serial-frame byte
  limit, writes newline-terminated request frames to a writable stream, and can
  close its underlying streams after failed exchanges.
- `exchangeSerialLineRequest`: package-owned one-shot serial-line exchange
  helper. It validates the request before opening a port, delegates exchange to
  `SerialLineTransport`, and closes the opened port in a `finally` block. CLI
  and future native bindings should use this boundary instead of duplicating
  validation/open/close sequencing.
- `nsealr serial-frame wrap-request` and `nsealr serial-frame unwrap-response`:
  offline CLI helpers for producing validated serial request frames and
  decoding validated serial response frames during ESP32 bring-up. With
  `--request`, response unwrapping also verifies the original request id and
  signed-output binding before writing output. These commands do not open a
  physical USB, CDC, HID, WebUSB, or WebSerial connection.
- `nsealr serial-line exchange`: one-shot local USB-serial CLI helper over
  `exchangeSerialLineRequest`. It opens a newline-oriented device path only
  after request validation, writes the chosen output format only after response
  verification, and is not a browser transport, relay session, persistent
  signer connection, or permission grant mechanism.
- `nsealr request get-capabilities`, `nsealr request get-public-key`, and
  `nsealr request get-signing-status`: host-side generators for non-sensitive
  parameterless device requests. They validate caller-supplied request ids
  before writing output and are useful for serial-frame hardware captures
  without involving signing.

## Smartcard Boundary

The first smartcard package covers the display-less APDU contract from
`nSealr/specs`: `GET_PUBLIC_KEY` and `SIGN_EVENT_ID`. It can protect key
material in a card-like boundary, but trusted event review must still happen
before the companion sends a 32-byte event id to a card.
The v0 command profile is intentionally exact: CLA `0x80`, P1/P2 `0x00`, no
Le byte, and one fixed payload shape per instruction. The private simulator and
shared vectors reject profile-shape mismatches before any signature is
produced.

`SmartcardSigner` models the companion side of that boundary. It retrieves the
card public key, computes the NIP-01 event id from the requested template, asks
the card to sign only that 32-byte id, verifies the returned Schnorr signature,
and emits the standard signed-event response. It refuses to sign unless the
caller supplies an explicit review acknowledgement. That acknowledgement is a
workflow guard for display-less smartcards, not proof that the untrusted host is
a trusted display. The display-less signer boundary therefore accepts only
`external-review` acknowledgement; any future trusted-display smartcard product
must be modeled as a separate trusted-review surface. External
`approvalDigest` input is mandatory, and the signer recomputes the shared
screen-review digest and rejects missing or mismatched values before APDU
exchange. It also reuses the shared request validator before APDU exchange, so
package callers cannot bypass CLI validation with host-supplied `id`, `pubkey`,
`sig`, malformed tags, oversized content, or other unsafe `sign_event` shapes.

`nsealr review-request --screen-review` renders the same deterministic screen
pages and `approval_digest` used by the shared vectors. `nsealr
smartcard-sim-sign` exposes the APDU flow through the private test-only
simulator in `@nsealr/dev-signer` and requires `--approval-digest` whenever
`--review-acknowledged` is used. Real PC/SC and NFC transports must implement
the same APDU exchange interface without weakening the review acknowledgement
requirement.

The PC/SC boundary is provider-based: tests can inject fake readers and future
desktop adapters can inject a real PC/SC provider without making a native card
driver a required companion dependency. It normalizes provider enumeration
failures, malformed reader-list results, and reader connection failures into
`PcscUnavailableError` before any APDU exchange, and normalizes APDU transmit
failures into the same error family after a connection is opened. It also
validates transmit-result shape, response status bytes, response data shape, and
numeric response data bytes before constructing response APDUs, so a malformed
provider response cannot be silently truncated or surfaced as a generic runtime
type error. It is not a real-card compatibility claim.

## NIP-46 Bridge Boundary

The first NIP-46 module handles only already-decrypted JSON-RPC-like payloads
from NIP-46 kind `24133` content plus descriptor-only parsing for official
`bunker://` and `nostrconnect://` connection tokens. It does not implement
relay subscriptions, NIP-44 encryption/decryption, connection
acknowledgements, permission persistence, or active auth-flow browser UX. Relay
response-step evaluation accepts `connect` `result: "ack"` only as normalized
metadata while keeping `acknowledges_connect: false`; it accepts
`switch_relays` JSON relay-list and `null` results only as normalized metadata
without opening or switching relay transports; it also accepts the official
auth challenge shape only as normalized http(s) URL metadata without
credentials or fragments. It never opens the URL or treats these responses as
approval.
For client-initiated `nostrconnect://` flows, the package can also verify an
already decrypted connection-token response against the original local token
secret without storing or echoing that secret. The output is secretless
metadata that binds the response recipient to the client pubkey and discovers
the remote signer pubkey from the response envelope; it does not open relays,
derive NIP-44 keys, acknowledge `connect`, create grants, dispatch signers, or
persist session state.
The package can also project that metadata into deterministic auth-challenge
review pages and a digest-bound local approval artifact. That approval proves
which URL was reviewed, but still records `opens_url: false`,
`acknowledges_connect: false`, `creates_grants: false`, `opens_relay: false`,
`dispatches_signer: false`, and `persists_session_state: false`.

The bridge maps `get_public_key` and `sign_event` messages into standard
nSealr v1 requests so any signer transport can handle them behind the same
verification boundary. `ping` is answered locally with `pong` because it does
not require a key-holding device. `switch_relays` is answered locally with
`result: "null"` no-change metadata until a later relay-session engine owns
live relay switching. Signed-event responses are returned as NIP-46 result
strings containing JSON-stringified Nostr events; public-key responses return
the hex key string; connect ack relay responses remain metadata-only session
input; switch-relays responses remain metadata-only relay-list input; nSealr
error responses become NIP-46 error strings.

This keeps NIP-46 as a host transport/bridge layer. Trusted event review and
approval remain with the Raspberry, ESP32, smartcard-assisted, or future
hardware-wallet signer boundary.

Permission parsing is intentionally separate from permission grants. The parser
accepts the NIP-46 `method[:params]` string form, validates numeric
`sign_event:<kind>` selectors, and rejects `connect` as a requested permission.
The matching helper derives a required permission from a later request and
checks it against an already-approved permission set. For compatibility and
request-review rendering, raw requested-permission parsing can represent broad
`sign_event`; `sign_event:<kind>` matches only that kind. Approved-permission
inputs are stricter: CLI `--permissions` and `nsealr-nip46-policy-v0` policy
files reject broad `sign_event` and require an explicit kind selector before a
request can reach a signer route. Shared specs fixtures now include the derived
requirement and positive/negative permission checks for conformance. The bridge
decision helper uses the same matching result to produce signer routing, local
`ping`, `connect` review, or permission-denied responses. Actual grant storage,
revocation, auth challenge UI/session handling, and user approval UX remain
future policy layers.
This broad NIP-46 permission matching is a read-only compatibility boundary;
it is not the nSealr-managed persistent grant descriptor menu, which remains
limited to `sign_event` kind `1` in v0.

`nsealr nip46 decide` exposes that boundary as a file-backed test harness for
already-decrypted payloads. It writes the same deterministic decision JSON used
by shared vectors. The command accepts either an explicit permission string or
a read-only `nsealr-nip46-policy-v0` policy file pinned by shared specs
vectors, and both approved-permission paths reject broad `sign_event`. It does
not create or update policy files, open relay sessions, decrypt NIP-44
payloads, persist grants, or contact signer transports.

`nsealr nip46 review-connect` exposes only the review projection for an
already-decrypted `connect` request. It writes deterministic pages with the
remote signer pubkey, secret presence, and requested permission labels. It does
not echo the secret value, return `ack`, persist a grant, or authorize the
client.

`nsealr nip46 approve-connect` consumes that review projection and writes a
local approval artifact only when the reviewed connect digest is supplied back
to the CLI. The artifact binds the approval to the exact review pages while
recording `acknowledges_connect: false`, `creates_grants: false`,
`opens_relay: false`, `persists_session_state: false`, and
`stores_production_secrets: false`.

`nsealr nip46 review-auth-challenge` and `nsealr nip46
approve-auth-challenge` expose the same boundary for auth URL response steps:
the first command renders the remote signer, client pubkey, and auth URL; the
second writes an approval only after the reviewed auth challenge digest is
supplied back. These commands are file-backed harnesses only. They do not open
the URL, acknowledge `connect`, open relays, create grants, dispatch signers,
store secrets, or persist session state.

The NIP-46 package now also parses a shared session lifecycle checkpoint, but
this remains a checkpoint rather than a session engine. The
`approved_pending_ack` descriptor binds a reviewed connect digest, client and
remote-signer pubkeys, relay URLs, approval time, expiry, requested
permissions, and approved permission subsets while rejecting embedded secret
material and keeping NIP-44 key derivation, `connect` acknowledgement, relay
I/O, grant creation, signer dispatch, production secret storage, and session
persistence disabled. The package can also create that checkpoint from a
canonical connect review plus matching approval artifact, explicit client
pubkey, relay list, expiry, and approved permissions. Source vector paths stay
in specs fixture metadata, not in runtime session objects.

The pending-session request gate consumes that checkpoint only as immutable
review metadata. It binds the relay envelope sender to the session client
pubkey, the recipient `p` tag to the remote-signer pubkey, and the decrypted
request to the normal NIP-46 permission requirement logic, then returns a
deterministic `connect_ack_pending` error. It does not use session permissions,
acknowledge `connect`, open relays, derive NIP-44 keys, create grants, dispatch
signers, store production secrets, or persist session state.
`nsealr nip46 gate-session-request` is only a file-backed harness over that
same package boundary. It reads a checkpoint, relay event, decrypted message,
and evaluation timestamp from local files and writes the deterministic gate
result without opening transports or creating session state.

`connect` parsing is also intentionally non-committal. The bridge can extract
the remote-signer pubkey, optional secret, and requested permissions into a
review intent and deterministic review pages, but it does not return `ack`,
echo secrets, persist grants, or authorize a client. A later policy layer must
review and explicitly approve that intent. The same boundary is now covered by
a shared `nSealr/specs` NIP-46 vector and `nsealr fixture verify`.

Connection-token parsing follows the same boundary. `bunker://` descriptors
validate the remote-signer pubkey and relay list for a client that wants to
talk to an external signer; `nostrconnect://` descriptors validate the client
pubkey, required secret presence, relay list, optional client metadata, and
requested permissions for a signer that is being asked to approve a client.
The returned descriptor intentionally includes only `secret_present`, never the
secret value. Parsing a token does not subscribe to relays, derive a NIP-44
session key, return a NIP-46 acknowledgement, create a grant, or choose a
signer route.

`nsealr nip46 parse-connection-uri` is only a file-backed harness over that
package parser. It reads a local text file containing the token and writes the
same descriptor JSON after validation. The command intentionally avoids a
direct `--uri` argument so shared secrets are not encouraged into shell
history, process lists, or copied logs.

## QR Envelope

The companion follows the shared `nSealr/specs` QR v0 format:

```text
nsealr1:<base64url-json>
nsealr1a:<payload-sha256-hex>:<index>/<total>:<base64url-json-chunk>:<frame-checksum-hex16>
```

The static v0 envelope is deliberately uncompressed and single-part. The
animated v0 frame set keeps the same uncompressed JSON payload but splits the
base64url text across bounded `nsealr1a:` frames. Each frame carries the full
decoded JSON SHA-256 digest, a one-based index/total pair, and a short frame
checksum so receivers can reject missing, duplicated, reordered, or tampered
frames before parsing JSON. Compression and fountain codes remain out of scope.
The decoder enforces the shared static QR decoded JSON byte limit and rejects
padded base64url, invalid UTF-8, malformed JSON, and malformed prefixes before
any review or signing flow can consume the payload.
Animated decoding enforces separate decoded-JSON, frame-payload, and frame-count
limits from `nSealr/specs`, then still relies on request/response validation
to decide whether the reassembled payload is acceptable for the caller.

## Serial Frame Draft

The initial serial frame is one newline-terminated ASCII line:

```text
nsealr1f:<type>:<base64url-json>:<checksum>\n
```

Supported frame types are `request`, `response`, and `error`. The checksum is
the first 16 lowercase hexadecimal characters of SHA-256 over
`<type>:<base64url-json>`. This is not an authentication mechanism; it only
catches accidental framing and transport corruption before the companion applies
schema and signature verification.
The decoder enforces the shared complete-frame byte limit and rejects malformed
payloads before JSON parsing. The framing package is browser-runtime clean, but
browser access surfaces still need separate origin, permission, and transport
review before WebSerial/WebUSB support is exposed through `@nsealr/sdk/browser`.
