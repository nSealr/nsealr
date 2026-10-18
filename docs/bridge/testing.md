# Testing

## Current Baseline

```sh
make ci
```

The baseline check verifies repository structure, license policy, docs, CI,
TypeScript type safety, unit tests, integration tests, dependency audit, and
companion package-boundary rules.
The Makefile pins `pnpm@10.33.4`; it uses a global `pnpm` only when that exact
version is present and otherwise falls back to `npm exec` on development
machines that only have Node/npm. Package build, pack, and release-artifact
helpers also invoke the repository-pinned `pnpm` internally, so direct script
runs cannot silently inherit an older global `pnpm`.
The workspace Vitest command is bounded to four workers to avoid local or CI
fork-worker oversubscription while keeping the full test suite enabled.

## Single-Repository CI

Tests prefer the sibling `nSealr/specs` repository when the full local
workspace is present. GitHub Actions checks out `nSealr/companion` by itself,
so tests fall back to fixture snapshots under `tests/fixtures/specs` in
single-repository CI. Cross-repository drift remains guarded by
`nSealr/lab` integration, which runs against the live sibling repositories.

## M2 Tests

- NIP-01 canonicalization tests in `packages/core`.
- BIP-340 verification tests in `packages/core`.
- Request and response shape validation tests in `packages/protocol`, including
  signing-status consistency checks that reject `signing_enabled: true` while
  any `missing_gates` remain and `signing_enabled: false` without at least one
  missing-gate reason, response request-id profile checks, plus signed-event
  response integer-safety, content, and tag limit rejection.
- Shared fixture loading tests in `packages/fixtures`.
  Invalid hardening fixture loading is directory-driven so new shared invalid
  vectors are discovered from the sibling specs checkout or local snapshot
  instead of being maintained in a hand-written name list.
  Account-descriptor, policy-profile, grant-descriptor, policy-change review,
  policy-decision, route-selection, source public-key proof, and
  persistent-secret custody contract loading is also directory-driven through
  package-owned fixture/policy code. Policy parser
  tests pin the v0 nSealr-managed grant menu to `sign_event` kind `1` only, so
  broader automated methods or event kinds fail before CLI, browser, SDK, or
  local-service code can treat a grant descriptor as valid.
  QR review-transcript fixture validation also lives in this package and covers
  `scroll` buttons plus rendered-frame `body_line_styles` mismatch rejection,
  keeping `apps/cli` as a thin fixture-verification wrapper.
- Trusted-review model tests in `packages/review` against every shared review,
  review-screen `approval_digest`, and review detail-page vector from
  `nSealr/specs`, including visible JSON-style control escapes in event
  content and tags.
- Development signer verification tests in `packages/dev-signer`.
- Repository verification now requires explicit `@nsealr/*` package manifests,
  package READMEs with boundary sections, source `src/index.ts` entrypoints,
  built `dist` exports, synchronized package versions, changelog coverage, and
  npm-facing package metadata plus public provenance `publishConfig`,
  changelog coverage, and release/provenance policy; it rejects deep
  cross-package source imports and production package dependencies on private
  `@nsealr/dev-signer`.
- Client package tests cover native-messaging frame encoding/decoding,
  deterministic malformed-frame rejection, secretless local service status,
  deterministic pairing intents, browser-safe shared local-client identity
  parsing, unpaired/revoked/expired/scope-denied client rejection, latest-grant
  selection from in-memory grant history,
  unsupported local-service request and per-operation parameter field
  rejection,
  deterministic pairing-review projection, strict grant-store
  serialization/revocation, strict pairing-approval artifact parsing before
  grant-store persistence, latest-client revocation appending, secretless route
  selection, signer-request validation, signer-response verification, local
  client request-id correlation, malformed service-response rejection including
  pairing digest mismatch, grant-gated signer-request dispatch through an
  explicitly injected dispatcher, deterministic `signer_route_unavailable`
  behavior when no dispatcher is configured, shared route-refusal fixture
  coverage for every route-selection vector, route-aware dispatcher registry
  selection, external NIP-46 route metadata as an injected-dispatch-only
  adapter path with no built-in relay/session driver, missing-route refusal,
  ambiguous-handler rejection, display-less smartcard dispatch refusal without
  a matching external review acknowledgement, rejection of that acknowledgement
  on trusted-review routes, async dispatch through
  `handleLocalServiceRequestAsync`, deterministic refusal when async dispatch
  is accidentally used through the synchronous handler, malformed dispatch
  response rejection, and native-messaging exchange wrapping before any real
  signer transport driver exists.
- Browser-provider package tests cover NIP-07 `getPublicKey` validation,
  `signEvent` conversion into nSealr signer requests, signed-response
  verification, explicit client identity forwarding, signer refusal propagation,
  shared access-surface vector consumption for local-service route selection
  and signer-unavailable behavior, browser native-messaging local-service
  client adaptation, shared native host name use, invalid native-host-name
  rejection, and rejection before backend contact when an event template
  contains forbidden signer-owned fields.
- SDK examples also consume the shared browser-provider access-surface vector
  through built public package entrypoints and import `@nsealr/sdk/browser`,
  so the npm-facing facade does not drift into a separate browser/local-service
  behavior. The same browser facade now also imports `@nsealr/qr`, which keeps
  static and animated QR helpers under the browser-runtime import gate.
  The browser-runtime import hygiene check walks packaged browser-extension
  entrypoints plus `@nsealr/browser-provider`, `@nsealr/framing`, and the
  browser SDK facade. It fails if that runtime graph imports Node builtins, uses
  `Buffer`/`process`, or imports the Node-capable `@nsealr/client` root instead
  of `@nsealr/client/browser`. Run it directly with
  `make browser-runtime-imports`. The browser-runtime bundle smoke then
  runs esbuild against the packaged background, content-script, page-script,
  and popup entrypoints with `platform: browser` and browser-compatible IIFE
  output, and fails if bundled outputs contain Node builtin specifiers,
  `Buffer`, or `process`. Run it directly with
  `make browser-runtime-bundle`. The browser-extension security audit runs with
  `make browser-extension-security` and fails if the extension or
  browser-provider runtime starts depending on test signing packages,
  signing/key-generation libraries, unreviewed browser storage APIs, or direct
  signing helper calls. The only storage path allowed by design is the
  package-owned origin-permission storage adapter plus packaged-global
  resolver. These gates keep the extension as a secretless NIP-07 access
  surface over the local companion service. Installable extension packaging
  still needs a reviewed production bootstrap/config contract. Package-build
  tests cover the first private developer artifact
  builder: route-config tests require digest-bound review and approval for the
  secretless selected route, and require that the route config name an explicit
  browser-dispatchable route type instead of account-only, stateless QR-vault,
  or display-less smartcard routing; package-build requires that approval
  before embedding the route config, requires a new output directory outside
  the companion source tree unless it is under
  `release-artifacts/browser-extension/`, and package verification enforces
  the same safe artifact-location rule. It requires the reviewed package-plan
  artifact to match the manifest profile being built, writes manifest, popup
  HTML, and bundled entrypoints only after successful in-memory bundling,
  returns explicit route, shared native-host name, manifest-permissions,
  popup-mode, activeTab, origin, extension, and pairing metadata plus a package
  digest and per-file byte counts plus SHA-256 hashes. The package-owned
  `package-verify` script requires the digest-bound package-plan review
  artifact, parses that review plus the build result, recomputes the package
  digest, checks the written manifest exactly against the externally reviewed
  package-plan digest and plan body, checks the popup HTML exactly against the
  deterministic template,
  checks packaged popup-mode binding, packaged background native-host, route,
  and origin-permission metadata binding, packaged
  content-script and page-script bridge/provider entrypoint bindings, bundled
  entrypoint byte counts and SHA-256 hashes, and rejects unexpected output
  files plus Node runtime references in packaged JavaScript, so release
  rehearsals do not depend only on external lab assertions. Package build still
  performs no native-host installation, build-time browser storage writes, key
  custody, or signer dispatch. Firefox package-build output is covered through
  the same builder with explicit Gecko extension settings. Package-plan and
  package-build tests both cover the explicit storage-backed origin-approval
  profile and pin its `activeTab` plus `storage` permissions.
- Browser-extension app tests cover the private internal message parser for
  `get_public_key` and `sign_event`, including unsupported-method rejection,
  malformed-envelope rejection, and shared signer-request validation for event
  templates. Handler tests cover injected provider success paths, request
  rejection before provider contact, and malformed provider-output rejection
  before browser callers can trust returned pubkeys/events. Sender-boundary
  tests cover page-origin derivation from full URLs, origin/URL mismatch
  rejection, deceptive localhost rejection, extension-page-origin rejection,
  and shared local-client identity construction. Sender-aware handler tests
  prove malformed requests and malformed senders fail before provider
  selection, provider-selection failures produce deterministic errors, and the
  native-messaging provider selector binds sender-derived identity to the
  local-service dispatch path while `sign_event` remains deterministically
  unavailable until a signer route dispatcher is configured. Pairing tests prove the
  same sender-derived identity can request a digest-bound local-service pairing
  intent, deterministic pairing-review metadata, and deterministic
  browser-origin permission review metadata without creating grants, writing
  extension storage, injecting providers, or touching native host installation.
  They also prove origin permission approvals require explicit local pairing
  digest confirmation and still create no grants, storage writes, provider
  injection, or key material. Origin-permission store tests prove already
  approved origin artifacts can be normalized into deterministic secretless
  records, exact origin/extension/pairing-digest/method lookup is required,
  route-only approvals cannot authorize `sign_event`, duplicate approvals are
  rejected before shadowing, exact approved-origin upsert/revoke mutations do
  not keep stale method scopes or move the store clock backward, and malformed
  or secret-looking store fields fail before any storage-adapter write, grant,
  signer dispatch, or key material exists.
  Origin-permission storage-adapter tests prove the extension can load a
  deterministic empty store, parse an existing store, persist only the
  validated fixed-key artifact, upsert and revoke approved origins without
  touching unrelated records, remove the store only through an explicit injected
  remove dependency, and reject malformed dependencies, malformed reads,
  secret-looking stored objects, or stale write timestamps.
  Origin-permission CLI tests prove private artifact commands can approve a
  reviewed origin permission, create an empty store, upsert an approval, and
  revoke an exact origin/pairing key through package-owned parsers while
  rejecting digest mismatches, unsupported options, malformed approval inputs,
  and backward store timestamps. The CLI writes JSON to stdout only.
  Origin-permission view tests prove the future popup approval card renders the
  validated origin, app name, full local-pairing digest, method effects, and
  no-key/no-grant/no-storage-write chips, passes the exact digest to injected
  approval controls, accepts only parseable approval artifacts, handles
  rejection without creating an approval, and restores controls on malformed
  approval output.
  Popup active-tab origin tests prove future approval UI can resolve exactly
  one injected active tab into normalized sender/origin metadata, accepts local
  development HTTP origins, rejects browser-internal pages, rejects ambiguous
  tabs, malformed ids, invalid extension ids, and invalid injected APIs, and
  still stores no browser secrets or key material.
  Popup origin-permission orchestration tests prove selected active-tab
  metadata is passed to the review-control boundary, returned review origin and
  extension id plus app name must match the selected tab, unsupported result
  fields and authorizing or secret-carrying control results are rejected,
  unsupported active tabs fail before controls are contacted, and the result
  remains storage-free, grant-free, provider-injection-free,
  signer-dispatch-free, and secretless.
  Popup origin-permission view tests prove the active-tab review renders
  through the existing approval card, approval remains digest-bound and
  secretless, mismatched active-tab review metadata renders an unavailable
  state, and the popup refresh control can reload the review without browser
  storage, grants, provider injection, signer dispatch, or key material.
  Control, popup-control, background-controller, and browser-entrypoint tests
  now prove digest-confirmed origin permission approval is routed through the
  extension-internal control protocol into an explicitly injected storage
  adapter, without native messaging, grants, signer dispatch, or key material.
  Packaged-entrypoint tests now also prove the storage-backed origin-permission
  launcher uses the browser runtime sender id when no static extension id is
  configured, the explicit origin-permission popup launcher resolves only
  injected runtime, tabs, and document globals, renders the active-tab review,
  and sends digest-confirmed approval back through the same control protocol
  without signer dispatch or key material.
  Sender-aware handler and background-controller tests prove an injected
  approved-origin store can authorize exact `get_public_key` access while
  denying method-mismatched, stale-digest, or malformed-store requests before
  provider selection or native messaging. They also prove the same gate can
  load the store through an async injected loader, denies loader failures and
  ambiguous authorization sources, and still stops before provider selection or
  native messaging. Browser-entrypoint tests prove the
  same gate is forwarded through browser-like runtime handling over injected
  dependencies without calling native messaging on denied methods. Packaged
  entrypoint tests prove the launcher preserves the same authorization option.
  Background-controller tests prove request handling, pairing-intent requests,
  pairing-review projection, and origin-permission review projection share the
  same injected native-messaging boundary, silent or
  cancelled native messaging can be bounded by the shared local-service
  timeout/abort handling in `@nsealr/client`, and malformed browser requests
  fail before native messaging is contacted. Runtime-message tests prove raw
  browser sender metadata is reduced
  to the internal sender shape, invalid senders return deterministic
  `invalid_sender` responses before native messaging, and abort signals are
  forwarded before native messaging. They also prove the injected runtime
  listener installer returns `true` for asynchronous response delivery, sends
  responses only through the injected responder, converts unexpected handler
  failures into deterministic `runtime_handler_failed` responses instead of
  leaving callers without a response, reports responder failures through an
  injected error callback, and removes the listener through `dispose()`.
  Pending-request tests prove the injected
  `nsealr-browser-extension-pending-request-state-v0` lifecycle emits
  secretless pending/resolved/rejected/cancelled request state, cleans up
  active requests, rejects duplicate active ids, enforces the active-request
  bound before publishing state, aborts the native-message signal for UI-driven
  cancellation, suppresses stale duplicate rejection after cancellation, and
  never exposes event templates, key material, extension storage, grants, or
  signer dispatch. Pending-control and runtime-message
  tests prove the separate `nsealr-browser-extension-control-v0`
  `list_pending_requests`, `cancel_pending_request`, and
  `request_origin_permission_review` paths accept extension-internal senders,
  reject page-origin senders, reject oversized pending-state lists, reject
  settled states from `list_pending_requests`, keep list/cancel operations away
  from native messaging, return deterministic `list_failed` responses if the
  internal pending lifecycle cannot enumerate active requests, route
  origin-review requests through the background controller, and can use the
  background entrypoint's default in-memory lifecycle.
  Popup-control tests prove future visible UI can call the same list/cancel and
  origin-review protocol through injected `runtime.sendMessage`, rejects
  mismatched, settled, or unsafe response envelopes, and remains secretless. Popup-view
  tests prove the visible pending-request card renders request id, selected
  route account/type, timestamps, and no-key/no-event-payload state while
  keeping cancellation bound to the validated pending request id and absent
  from already settled states.
  Page-provider tests prove
  NIP-07 `getPublicKey` and `signEvent`
  calls become validated background requests, unsafe templates fail before the
  background boundary, malformed responses are rejected, and cancellation is
  forwarded without content-script injection. Install tests prove the frozen
  provider is attached only to an explicit target and does not overwrite an
  existing provider. Page-bridge tests prove future page/content-script
  envelopes reject malformed direction, mismatched request ids, malformed
  background responses, malformed bridge responses, invalid page-side requester
  input, and already-cancelled requests before any browser listener exists.
  Page-side requester tests also prove bridge-envelope wrapping and
  cancellation forwarding through an injected bridge exchange. Content-script
  bridge tests prove accepted page envelopes are bound to an explicit sender
  and injected background requester without adding browser listeners. They also
  prove the runtime requester forwards validated internal requests through an
  injected runtime-message sender, forwards cancellation, and rejects
  already-cancelled or in-flight-cancelled requests before trusting a runtime
  response. Content-script bootstrap tests prove the injected window listener,
  runtime-message sender, and response poster can be composed behind one
  install/dispose handle while still ignoring unrelated messages and reporting
  malformed accepted page envelopes. Content-script entrypoint tests prove the
  page-script injection helper and runtime bridge can be installed as one
  pre-packaging unit, forward accepted page requests to runtime messaging, clean
  up both resources through one dispose handle, and remove the injected script
  if bridge listener setup fails. Content-runtime API adapter tests prove
  reviewed resource paths are passed to injected `runtime.getURL`, unsafe paths
  are rejected before runtime contact, runtime messages are forwarded through
  injected `runtime.sendMessage`, and already-cancelled sends stop before the
  runtime API is called.
  Packaged-entrypoint filename tests prove the manifest and page-injection
  defaults use filenames reserved for packaged entrypoint modules,
  distinct from internal pure modules that only export helper functions.
  Packaged-entrypoint launcher tests prove the background, content-script,
  page-script, and popup packaged source modules call the reviewed browser
  adapters through explicit packaged global scopes; they accept unambiguous
  `browser.runtime` or `chrome.runtime`, reject ambiguous runtime globals before
  listener/script installation, and continue to avoid storage, grants, signer
  dispatch, and key custody.
  Package-plan tests prove the reviewed manifest, packaged output filenames,
  and source launcher paths stay aligned before bundle generation exists. They
  reject storage permission, host-permission, background-output,
  popup-output, content-script-output, and page-script web-accessible-resource
  drift without installing native-host manifests or writing extension storage.
  Package-plan
  CLI tests prove the private
  browser-extension script renders deterministic JSON from explicit target and
  content-script arguments, rejects incomplete or broad-match inputs, keeps the
  default embedded-origin profile storage-free, exposes the explicit
  `extension-storage` origin-approval profile only for reviewed content-script
  origins, renders a digest-bound review envelope for package-build gating, and
  has no output-path/install behavior.
  Package-build tests require a reviewed package-plan artifact plus explicit
  extension id, reviewed origin-permission store, and local pairing digest
  before content-script artifacts can embed an origin gate. Storage-backed
  package-build tests prove the build can omit static extension-id metadata and
  bind approvals to the runtime extension id instead. The default
  embedded-origin result remains extension-storage-free; every package-build
  profile remains grant-free, signer-dispatch-free, and secret-free.
  Content-script browser entrypoint tests prove explicit browser-like
  document/window/location/runtime dependencies compose into page-script
  injection, runtime messaging, response posting, and teardown without reading
  global browser objects or injecting after invalid dependency validation.
  Page-script browser provider entrypoint tests prove explicit browser-like
  window/location dependencies install NIP-07 over the page-window bridge,
  reject invalid dependencies before provider injection, and avoid global
  browser reads.
  Background browser entrypoint tests prove explicit browser-like runtime
  dependencies install runtime message handling over `runtime.onMessage`, route
  accepted requests through `runtime.sendNativeMessage`, dispose listeners, and
  reject invalid or cancelled dependencies before native messaging. Route-config
  tests prove the selected browser account config is secretless, fixed to
  `sign_event`, parsed through package-owned policy route-request validation,
  and rejected before listener installation when missing, duplicated,
  malformed, or carrying unsupported fields.
  Page-origin tests prove the browser-extension bridge accepts HTTPS page
  origins and local HTTP developer origins while rejecting non-origin URLs,
  unsupported schemes, extension URLs, and overlong values through one shared
  validator used by page-window and content-window boundaries.
  Content-window tests prove already-received page messages are source/origin
  gated, unrelated messages are ignored, and malformed nSealr envelopes fail
  before background contact without registering listeners or calling
  `postMessage`. They also prove the response-poster adapter posts only to
  reviewed `postMessage` targets and normalized page origins, and that the
  injected listener installer registers only on an explicit target, posts
  accepted responses only through an injected poster, reports malformed nSealr
  envelopes through an injected error callback, and returns deterministic
  `content_window_bridge_failed` responses for parseable accepted bridge
  requests when downstream handling fails unexpectedly,
  and removes the listener through `dispose()`. Page-window
  bridge-exchange tests prove the page side posts only to the exact reviewed
  origin, accepts only matching extension responses, ignores unrelated
  messages, and cleans up listeners on response, abort, timeout, and
  `postMessage` failure. Page-script bootstrap tests prove the explicit-target
  NIP-07 provider can be installed over either an injected bridge exchange or
  the injected page-window bridge without overwriting an existing provider or
  adding browser injection. Page-script injection tests prove the content-side
  DOM adapter rejects duplicate targets, unsafe script files, unsupported URL
  protocols, wrong URL paths, and missing parents while exposing explicit
  teardown.
  Manifest tests pin the minimal MV3 permission boundary: native messaging
  only, action popup, no host permission fields, no content scripts, no storage
  permission, and explicit Firefox extension ids. They also pin the opt-in
  explicit-origin content-script manifest profile and the separate
  storage-backed origin-approval profile, where `activeTab` and `storage` are
  explicit and still do not introduce host permissions. They reject broad URL access such as
  `<all_urls>`, wildcard hosts, non-local `http`, duplicate matches, host
  permission fields, and implicit storage.
- `make package-smoke` builds package artifacts, then runs the private
  `@nsealr/consumer-smoke` app. The smoke imports every public `@nsealr/*`
  package through its built package entrypoint plus the public
  `@nsealr/client/browser`, `@nsealr/client/client-identity`, and
  `@nsealr/sdk/browser` subpaths, and exercises a minimal no-signer consumer
  path. It also checks the `@nsealr/sdk` facade namespaces without
  importing private signing helpers. This catches broken exports that relative
  in-package tests would miss.
- `make examples-smoke` builds package artifacts, then runs private
  `@nsealr/sdk-examples`. The examples are executable documentation for public
  package usage. They import every publishable public package and cover
  request/QR handling, fixture loading, policy decisions, review rendering,
  serial framing, local companion-service calls, browser-provider refusal
  behavior, already-decrypted NIP-46 bridge decisions, `@nsealr/sdk` and
  `@nsealr/sdk/browser` facade namespace imports including QR, smartcard APDU
  round-trip, and in-memory serial-line transport refusal without importing
  `@nsealr/dev-signer`.
- `make readme-examples` builds package artifacts, then extracts
  `nsealr-readme-example` TypeScript snippets from every publishable package
  README and executes each snippet from the private SDK-example app context.
  This keeps public README examples aligned with built package entrypoints and
  prevents undocumented source/deep-import drift.
- `make api-docs` verifies that `docs/api.md` matches the exported symbols
  reachable from every public package entrypoint. `make api-docs-update`
  regenerates the file after an intentional public API change. This keeps the
  npm-facing surface visible and reviewable before publication.
- `make api-review` verifies that `docs/api-review.md` records the current
  `docs/api.md` digest and includes a review section for every publishable
  package. Intentional export changes must update both API docs and the API
  review before CI can pass.
- `make package-registry` verifies that the public package set is derived from
  actual package manifests, that private packages such as
  `@nsealr/dev-signer` cannot enter the publishable set, and that public
  packages do not reference private/test-only workspace packages anywhere in
  their publishable manifests.
- `make public-imports` verifies that production source for public packages
  imports other `@nsealr/*` packages only through reviewed public
  entrypoints/subpaths, keeps relative imports inside the package `src`
  boundary, and never imports private apps or the test-only signer package.
- `make release-plan-check` verifies the digest-bound public package release
  plan and review envelope. The plan lists every public package, tarball name,
  package directory, synchronized version, MIT license, publish provenance
  config, and required local gates, while proving private packages and local
  npm publishing stay excluded.
- `make pack-smoke` packs public `@nsealr/*` tarballs, verifies they contain
  only `dist`, README, and package metadata, verifies `workspace:*` dependency
  protocols were rewritten, installs the tarballs into a temporary npm consumer
  project, and imports them by package name. Packed public manifests must not
  mention private/test-only packages.
- `make release-artifacts-safety` proves the release-artifact helper refuses
  destructive output paths such as the repository root, `packages/`, or the
  top-level `release-artifacts/` directory before any cleanup occurs. It also
  rejects missing, duplicated, or unknown release-artifact CLI options so an
  ambiguous invocation cannot select the wrong cleanup target.
- `make release-artifacts` builds package artifacts, packs every public
  package, validates the same tarball boundaries, and writes
  `release-artifacts/packages/manifest.json` with the reviewed
  `release_plan_digest` plus each tarball filename, byte count, and SHA-256
  digest for the manual package release rehearsal workflow. It does not publish
  to npm.
- Service app tests prove the private native-messaging host scaffold stays a
  thin wrapper around `@nsealr/client`, passes injected in-memory authorization
  context to the local service, loads explicit read-only secretless
  grant/account JSON files for local harnesses only when a storage approval
  covers the paths, rejects secret-bearing or malformed account-store files,
  parses explicit storage-approved secretless route-driver stores, rejects
  empty, duplicate, broad, secret-bearing, non-USB, QR-vault, and unsupported
  serial-path driver mappings, bounds serial-line timeout and ignored-log
  controls, rejects stale route-driver entries that do not match the loaded
  account-store account id, route type, and transport, dispatches matching
  developer serial-line requests only through an injected opener or explicit
  route-driver file, maps serial-line open, timeout, protocol, I/O, and close
  failures to deterministic transport error codes, returns deterministic
  `signer_route_unavailable` for authorized dispatch without a configured
  driver, awaits async dispatchers through the async native-message helpers,
  and returns deterministic errors for malformed native-message frames.
- Local service tests cover deterministic pairing intent creation, digest-bound
  pairing-review projection, manual approval into a grant, strict secretless
  JSON grant-store parsing, serialization, persistent revocation history,
  tamper rejection, expiry rejection, authorization, and revocation/expiry/scope
  failures. The high-level client tests also reject operation/result mismatches
  such as a valid service-status result returned to a pairing, validation, or
  route-selection call.
- Negative response verification tests for request id mismatch, template
  mismatch, event id mismatch, and invalid signatures.
- Transport exchange tests proving successful `sign_event` responses are
  verified against the original request before file, stdio, or serial adapters
  return them to higher layers.
- End-to-end CLI tests for `request -> dev-sign -> verify-response`.
- CLI request-generation tests for parameterless device requests:
  `get_capabilities`, `get_public_key`, and `get_signing_status`, including
  caller-supplied request ids and rejection before writing output on invalid
  request ids.
- CLI `verify-response` tests reject invalid original requests before accepting
  otherwise valid response shapes.
- End-to-end CLI tests for QR envelope `request -> dev-sign -> verify-response`.
- CLI failure-mode tests for malformed event-template JSON and unsupported
  request methods.
- CLI review-request tests for rendering review JSON, digest-bound screen-review
  pages, constrained-display detail pages, and caller-supplied detail-page
  display limits from QR signing requests.
- CLI fixture verification tests against `nSealr/specs`, covering both
  signed-event fixtures, trusted-review fixtures, review-display-frame
  fixtures, review-detail-page fixtures, QR review-transcript fixtures, NIP-46
  payload fixtures, NIP-46 policy-file fixtures, NIP-46 connection URI
  fixtures, NIP-46 relay-event fixtures, NIP-46 relay-step fixtures,
  NIP-46 session lifecycle fixtures, NIP-46 session gate fixtures,
  account descriptors, policy profiles, grant descriptors, policy-change
  review vectors, policy-decision vectors, route-selection vectors, source
  public-key proof vectors, access-surface vectors, and persistent-secret
  custody contract vectors, plus the shared implementation-limit profile and
  invalid hardening vectors. Grant
  descriptor tests reject the removed `decision` field so the companion cannot
  revive an ambiguous grant mode outside expiry, rate-limit, revocation, audit,
  and device-confirmation semantics. Policy-profile parser tests also reject
  unsupported policy vocabulary so new manual-review, forbidden-permission, or
  risk-tier strings cannot appear without a specs update.
- CLI policy-change review tests covering contextual
  `nsealr policy review-change --proposal ... --account ... --current-policy
  ... --proposed-policy ... [--grant ...] --out ...` execution against shared
  policy-change vectors, including deterministic output and no output after a
  rejected companion-authoritative proposal.
- CLI fixture verification rejects review detail-page style drift, including
  unknown body-line style names and continuation lines that are not styled as
  `value`.
- Transport contract tests for in-memory development signing, JSON file
  handoff, one-shot JSON-lines stdio exchange, and serial-frame exchange.
- JSON-lines stdio transport tests proving unterminated oversized stdout is
  rejected before process-close fallback errors and stderr diagnostics are
  capped before being included in exit failures. They also prove silent signer
  processes are rejected by a deterministic response timeout.
- Transport boundary tests require outbound request payloads and inbound device
  response payloads to pass standard nSealr protocol validation for
  development signer, JSON file, JSON-lines stdio, and serial-frame adapters.
  Exchange tests also reject validly shaped responses with mismatched
  `request_id` values and surface `nsealr1f:error` payloads as deterministic
  transport diagnostics.
- CLI serial-frame tests covering validated request wrapping, response-frame
  unwrapping, and optional request-bound rejection before output is written.
- Fixture verification rejects valid serial frames whose decoded request
  metadata violates the shared specs profile.
- QR envelope round-trip and rejection tests.
- QR envelope encode-side limit tests proving static v0 QR writers reject
  payloads that would exceed `max_static_qr_decoded_json_bytes` before emitting
  an envelope.
- Animated QR frame-set tests against the shared specs vector, including
  reversed input order, missing-frame rejection, and frame-checksum rejection.
- CLI tests proving `qr-animated` request and response files round-trip through
  `request sign-event`, `dev-sign`, and `verify-response`.
- Serial frame round-trip, unsupported type, checksum mismatch, and encode-side
  `max_serial_frame_bytes` rejection tests.
- Shared `nSealr/specs` QR and serial transport vector conformance tests.
- Serial-line transport tests proving a future native USB/WebSerial adapter can
  write a request frame, ignore device log lines, normalize common serial line
  endings, reject stalled writes and silent ports with deterministic timeouts,
  close stream-backed ports, and reuse the verified serial-frame response path
  through an injected line port. The package-owned one-shot exchange helper is
  also tested to validate requests before opening a port and to close an opened
  port after the exchange.
- Stream-backed serial-line port tests proving chunked readable-stream output
  and writable-stream request frames behave like the injected port contract
  without a native serial dependency. They also prove unterminated oversized
  input is rejected without rejecting batched short complete lines.
- CLI serial-line tests proving `nsealr serial-line exchange` remains a thin
  file/argument wrapper around the package-owned one-shot serial-line exchange,
  writes output only after verification, and still rejects invalid requests
  before any port is opened. They also prove device `nsealr1f:error` frames are
  surfaced as deterministic transport errors without writing output.
- Shared `nSealr/specs` capability response conformance tests.
- Shared `nSealr/specs` ESP32-S3 signing-disabled response conformance
  tests.
- Shared `nSealr/specs` smartcard APDU vector conformance tests, including
  deterministic APDU rejection status vectors for wrong length, non-zero P1/P2,
  unsupported Le, unsupported CLA, and unsupported INS.
- Smartcard APDU codec tests covering deterministic rejection for non-integer
  byte/status-word fields, non-`Uint8Array` payloads, invalid Le values, and
  oversized short-APDU payloads before simulator or PC/SC transport.
- Smartcard signer tests covering mandatory review acknowledgement, APDU-backed
  public-key retrieval, event-id signing, Schnorr verification, and standard
  signed-event response verification, including rejection of invalid card
  signatures before returning a response.
- Smartcard signer negative tests covering shared unsafe request rejection
  before an event id is sent to a card transport and rejection of
  `trusted-display` acknowledgement plus missing or mismatched
  `approvalDigest` for display-less cards.
- CLI tests covering `review-request --screen-review` output against shared
  screen-review vectors, `review-request --detail-pages` output against shared
  detail-page vectors, and `smartcard-sim-sign --approval-digest` rejection.
- Smartcard PC/SC boundary tests covering fake reader exchange, malformed
  reader-list rejection, malformed transmit-result rejection, malformed response
  data-shape rejection, malformed response data-byte rejection, and clear
  provider/no-reader/connection setup and APDU transmit errors without requiring
  native PC/SC dependencies or hardware.
- CLI smartcard simulator tests covering rejection without
  `--review-acknowledged` and `request -> smartcard-sim-sign ->
  verify-response`.
- NIP-46 payload bridge tests covering already-decrypted `sign_event` and
  `get_public_key` messages, local `ping`, local `switch_relays` no-change
  metadata, nSealr response mapping, and rejection of unsafe or unsupported
  payloads. The same tests consume shared `nSealr/specs` NIP-46 payload
  vectors.
- NIP-46 requested-permission parser tests covering method-only permissions,
  `sign_event:<kind>` selectors, empty permission strings, and rejection of
  malformed or unsupported entries.
- NIP-46 `connect` intent and review renderer tests covering remote-signer
  pubkey validation, optional secret capture, secret-presence display without
  secret-value echo, requested permissions, and rejection of signer-transport
  routing for `connect`. The shared specs fixture suite now includes a
  `connect` policy-review intent, review-page vector, and digest-bound local
  approval artifact that still records no `ack`, grant, relay, signer dispatch,
  persisted session state, or production secret storage.
- NIP-46 connection-token parser tests covering `bunker://` and
  `nostrconnect://` descriptor parsing, relay validation, requested
  permissions, optional client metadata, required `nostrconnect` secret
  presence, unsupported parameter rejection, and proof that descriptor output
  does not echo shared secret values. Shared invalid hardening vectors cover
  malformed connection URI schemes, invalid or duplicate relays, relay
  credentials or fragments, unsafe `sign_event` permission kinds, duplicate
  secrets or permission strings, empty secrets, unsafe client metadata URLs,
  forbidden bunker client metadata, and missing `nostrconnect` secrets.
- NIP-46 relay event envelope tests covering shared `kind:24133` request and
  response vectors. The parser checks sender pubkey, exactly one recipient `p`
  tag, opaque encrypted content, tag arrays made only of strings, and optional
  signed relay-event fields. When signed fields are present it verifies the
  NIP-01 event id and BIP-340 relay event signature without decrypting NIP-44
  content, opening relays, creating grants, or reaching signer transport.
- NIP-46 relay step tests covering shared post-decryption request and response
  vectors. The request evaluator binds the validated relay event envelope,
  plaintext message, and reviewed permissions to the same bridge decision path
  used by local decrypted payloads. The response evaluator shape-checks
  plaintext signed-event, public-key, connect ack, switch-relays, ping, auth
  challenge, and error response messages, rejects arbitrary result/error pairs
  outside `auth_url`, rejects auth URLs with credentials, fragments, or
  non-http(s) schemes, rejects unsafe switch-relays relay lists, and rejects
  public-key or signed-event results that conflict with an explicitly expected
  user key. Response-step v1 preserves distinct transport and user identities.
  Signed relay-event envelopes and signed-event response results are NIP-01 id
  checked and BIP-340 verified. Neither opens relays, decrypts NIP-44 content,
  acknowledges `connect`, creates grants, dispatches signers, or persists
  session state.
- NIP-46 auth challenge review tests covering the shared auth URL review vector.
  Package code renders the remote signer pubkey, client pubkey, and URL into
  deterministic pages, binds them to `auth_challenge_digest`, writes approval
  artifacts only after digest confirmation, and keeps URL opening, relay I/O,
  `connect` acknowledgement, grants, signer dispatch, secret storage, and
  session persistence disabled.
- NIP-46 connection token response tests covering the shared `nostrconnect://`
  response vector. Package code verifies the returned secret against the
  original local token while keeping the output secretless, binds the response
  recipient to the client pubkey, discovers the remote signer pubkey from the
  response envelope, and keeps relay I/O, NIP-44 derivation, `connect`
  acknowledgement, grant creation, signer dispatch, secret storage, and session
  persistence disabled. Shared invalid hardening vectors also reject recipient
  mismatch, explicit token-response errors, and returned-secret mismatch
  deterministically through package code and fixture verification.
- NIP-46 session lifecycle checkpoint tests covering shared
  `approved_pending_ack` vectors. The parser validates client/signer pubkeys,
  relay URLs, connect digest shape, approval/expiry safety, requested
  permissions, approved permission subsets, and false side-effect flags, and it
  rejects embedded secret material, NIP-44 key derivation, relay opening,
  `connect` acknowledgement, grant creation, signer dispatch, production
  secret storage, and session persistence. Creation tests also prove a
  canonical connect review plus matching approval can produce the same
  checkpoint while rejecting approved permissions outside the reviewed request.
- NIP-46 pending-session request gate tests covering shared
  `connect_ack_pending` vectors. The evaluator binds the relay event sender to
  the session client pubkey, binds the recipient `p` tag to the remote-signer
  pubkey, derives the same permission requirement as the standard NIP-46 bridge,
  and rejects signer dispatch until a future acknowledged-session contract
  exists.
- NIP-46 permission matching tests covering derived `sign_event:<kind>`
  requirements, broad requested-permission compatibility, explicit approved
  `sign_event:<kind>` inputs, method-only grants, denied requests, and
  `connect` exclusion from post-connect request permissions. Package and CLI
  tests reject broad approved `sign_event` inputs before decision output is
  written. The CLI fixture verifier also rejects drift in shared permission
  policy checks.
- NIP-46 bridge decision tests covering permitted signer routing, denied signer
  routing, local `ping`, denied `ping`, and `connect` review intent output. The
  CLI fixture verifier also rejects drift in shared bridge decision vectors.
- CLI NIP-46 decision and review tests covering `nsealr nip46 decide` against
  shared permitted, denied, and `connect` bridge-decision vectors plus
  `nsealr nip46 review-connect` against the shared `connect` review-page vector
  and `nsealr nip46 approve-connect` against the shared connect approval vector.
  They also cover `nsealr nip46 review-auth-challenge` and
  `nsealr nip46 approve-auth-challenge` against the shared auth challenge
  review/approval vector without opening URLs, relays, or signer transports.
  Approved decision inputs must use
  explicit `sign_event:<kind>` selectors; broad `sign_event` is accepted only
  as requested-permission metadata for review. Digest-mismatch approval
  attempts fail before writing output.
- CLI NIP-46 connection URI tests covering `nsealr nip46 parse-connection-uri`
  against shared `bunker://` and `nostrconnect://` vectors, including
  no-secret-echo output and invalid-token refusal before output files are
  written.
- CLI NIP-46 session checkpoint tests covering `nsealr nip46
  create-session-checkpoint` from a review/approval pair, explicit relays,
  client pubkey, expiry, and policy-file approved permissions.
- CLI NIP-46 session gate tests covering `nsealr nip46 gate-session-request`
  against the shared `connect_ack_pending` vector and every shared invalid
  session-gate vector before output is written.
- CLI NIP-46 policy-file tests covering read-only
  `nsealr-nip46-policy-v0` permission input and rejection of ambiguous
  `--permissions` plus `--policy-file` usage. The positive case consumes the
  shared `nSealr/specs` policy-file vector instead of an inline local copy.
  The CLI fixture verifier also rejects drift in shared policy-file vectors.
- CLI local-service pairing review tests covering
  `nsealr local review-pairing`, including deterministic review metadata for a
  pairing intent and rejection of tampered pairing intents before output files
  are written.
- CLI local-service pairing approval tests covering
  `nsealr local approve-pairing`, including explicit reviewed-digest
  confirmation, expiry handling, and refusal to write approval artifacts when
  the digest does not match.
- CLI local storage-review and approval tests covering
  `nsealr local review-storage` and `nsealr local approve-storage`, including
  digest-bound metadata for explicit grant/account/route-driver locations, no
  creation of reviewed storage files, duplicated storage-location option
  rejection, stack-free executable validation errors, digest-confirmed approval
  artifacts, and refusal to write review or approval metadata for ambiguous
  paths or mismatched digests.
- CLI native-host onboarding tests covering
  `nsealr local native-host manifest`, `plan-install`, `approve-install`, and
  `execute-install`, including dry-run manifest/plan rendering, digest-bound
  approval, execution-report generation, exclusive-create manifest writes, and
  refusal to write approval, execution-report, or manifest files when reviewed
  digests or output paths do not match.
- CLI local grant-store artifact tests covering
  `nsealr local grant-store append-approval`, including new-store creation,
  explicit input-store extension without input-file mutation, required
  storage-approval coverage for grant-store input/output paths, existing-output
  refusal, and malformed approval rejection before output files are written.
- CLI local grant-store revocation tests covering
  `nsealr local grant-store revoke-client`, including output-only revocation
  appending behind storage-approval coverage, input-file immutability,
  deterministic authorization denial after revocation, and no-match rejection
  before output files are written.
- Policy package tests cover secretless account descriptors, NIP-06 recovery
  source fingerprints, manual-only QR vault policy, manual-only display-less
  smartcard policy, manual-only persistent-device defaults, scoped grants for
  ESP32 USB/NIP-46 and custom hardware-wallet routes, policy-change review
  pages and approval digests, policy-change account/policy/grant context
  mismatches, wildcard/decrypt/export rejection, rejection of
  grant targets outside ESP32 USB/NIP-46 and custom hardware-wallet persistent
  policy routes, closed-schema rejection for descriptor, route, capability,
  policy-profile, grant, client, permission, and rate-limit records, external
  NIP-46 metadata that cannot claim nSealr persistent grants or scoped
  automation, shared route-selection response parsing, and deterministic
  policy-decision transcripts for allowed, expired, revoked, decrypt,
  export-secret, and unknown-method requests.
- Pre-signing hardening tests must reject every shared invalid vector that
  reaches companion-owned parsing: unsafe event-template fields, unsafe integer
  values, resource-limit violations, malformed or ambiguous responses,
  malformed response request ids, contradictory or reason-less signing-status
  readiness, malformed QR/serial envelopes, malformed NIP-46 payloads, invalid
  NIP-46 connection URIs, invalid NIP-46 session lifecycle checkpoints,
  invalid NIP-46 session gates, invalid policy files, duplicate signing-status
  gate entries, and signed-event response integer-safety, content, or tag
  violations.
- Nostr conformance oracle tests must compare companion event id/signature
  behavior with `nostr-tools` in tests, while keeping production code free of
  unnecessary oracle coupling.

## Next Test Additions

- Third-party consumer import tests for future `@nsealr/*` publication:
  no test-only signer leakage and no production secret storage in public
  helpers.
- Package release workflow tests should eventually add trusted-publishing dry
  run or npm provenance verification once npm organization settings exist.
- Local companion service tests with a fake extension/app client: user approval
  UX, production storage writes, production signer dispatch, and additional
  built-package consumer tests after explicit policy gates exist. The current
  test suite already covers pairing intent generation,
  deterministic pairing-review projection, digest-bound storage-location
  review and approval artifacts, strict grant-store serialization/revocation,
  explicit storage-approved read-only context loading, selected account route,
  malformed native-message rejection, shared Chromium/Firefox native-host
  manifest building, digest-bound dry-run install-plan building,
  install-approval artifact generation in `@nsealr/client`, explicit
  approval-bound install-execution through a write-new adapter, multi-message
  native-host stdio behavior, public CLI native-host onboarding artifacts, and
  the private service CLI wrapper that renders manifests/plans/approvals,
  rejects duplicated singleton install options, and can write an approved
  manifest path without overwriting existing files.
  Current service
  route-driver tests cover the developer serial-line dispatch boundary through
  fake ports and supported local serial path forms only; hardware serial smoke
  remains a later gate before production driver acceptance.
- Browser extension provider tests over fake companion/local-service backends
  cover authorized selected-account public-key lookup, `signEvent` routing
  through local-service dispatch, explicit dispatcher success, deterministic
  signer-unavailable responses before a real signer transport driver exists,
  malformed companion outputs rejected through shared route-selection parsing,
  already-cancelled requests, in-flight cancellation, `AbortSignal` forwarding
  into injected exchanges, thrown native-host sender failures, and latest-grant
  revocation before browser callers trust route selection or signer dispatch.
- Local-service client tests cover the high-level dispatch wrapper carrying a
  digest-bound external-review acknowledgement through to display-less signer
  routes, so SDK, desktop, CLI, and native-messaging callers reuse the service
  safety gate instead of inventing a parallel smartcard path.
- Package consumer smoke currently runs against built JS/declaration artifacts,
  packed tarballs, every manifest-declared public export subpath from a
  temporary npm consumer, executable examples importing every publishable
  public package, and the digest-bound package release plan. README snippets
  for every publishable package are now executed from CI, and the public API
  review is digest-bound to `docs/api.md`. The remaining npm-facing gate is
  trusted-publishing/provenance activation.
- Named external NIP-46 client/version interoperability and device approval
  workflows. The in-repository relay harness does not establish those claims.
- Large QR payload strategy tests once chunking or compression is designed.
- Hardware serial smoke tests before adding WebUSB, HID, CDC, or persistent
  local transport session adapters.

## Rule

Production behavior changes require test-driven development.


## S01 boundary regressions

`packages/nip46/src/session-security.test.ts` uses public fixture scalars and
nostr-tools as an independent signing/public-key oracle. It reproduces the
baseline manager's changed-user and conditional foreign-author acceptance;
its default SimplePool control replaces only WebSocket I/O and confirms foreign
author filtering. Identity discovery, curve points, signed content, request
correlation/replay, retry, cancellation and bounded unsettled operations are
covered independently of relay subscription filters.

`packages/transport/src/stream-security.test.ts` reproduces exactly 20,000 queued
bytes from 10,000 short lines under a four-byte limit. It tests aggregate bytes,
line count, UTF-8 boundaries, pending reads/writes, backpressure, EOF, errors and
shared-duplex cleanup. F01 regressions cover synchronous/asynchronous destruction
with/without close events, delayed and queued errors, callback identity and
deduplication, thrown/suppressed errors, descriptor restoration and transactional
constructor rejection. Protocol/framing tests reject duplicate, escaped duplicate,
trailing and overly nested JSON without changing existing schema limits.
F02 additionally checks recorded destruction errors after EOF with emitted or
suppressed error/close events, alongside error-free EOF tail-draining controls.

Run targeted checks after `pnpm build`:

```sh
pnpm exec vitest run --maxWorkers=4 packages/nip46 packages/transport packages/protocol packages/framing
```

`make ci` includes all browser/Node consumers and package gates. The separately
gated Docker harness uses `NSEALR_LIVE_E2E=1`; its results, image digest and all
baseline/failure evidence are recorded under `docs/restart/S01/`. This is an
in-repository signer harness, not third-party client or physical-device proof.
