# T01 current-source integration preparation

This four-document preparation reconciles the accepted T01 specification
`03c2616518d6d9a32fe5cc9a945624a72cd32ac0` and its distinct preparation review
`8d3a0acf2daa1a6b3b836b6d2241b99a8477ad8a` with adopted core main
`503719d5c607bdbcd1da30a89b0c3c6f5983c01b`, tree
`65d4faeaffb02b62ea8d3b8c8929862a9396d8cb`. Root reports actual resulting-main
[CI39420363820](https://github.com/nSealr/nsealr/actions/runs/39420363820),
verify118619497395, successful. That accepts the A02 input, not T01 or S03.
Author `/root/a02_sol` uses the current Sol6.1 xhigh assignment policy.

S03 candidate `c358229777d2582964a4f326ce8d15709841a395`, product checkpoint
`7eee22fbc269033756e53020b1370fc6671da3ab`, is a separately pinned **reviewed source proposal**, absent from this main.
Distinct final review `23d76b2c15d8dd41627f58c7b2018e06d40e821c` now passes all
five portable criteria on that exact candidate. Normal adoption and successful
actual-main CI remain prerequisites. Root has not selected the complete T01 implementation
tuple or admitted product edits. This preparation grants no brief PASS or task
acceptance and starts no package, browser, MCU, SDK or hardware implementation.

The [source reconciliation](source-reconciliation.json) verifies all 44 original
audit inputs by their immutable Git modes/blobs/byte counts/SHA256, retaining old
repository/commit/path identities alongside current targets. Nineteen current
postimages differ. The [consumer map](consumer-map.json) reconciles all 135 old
consumer references: 129 retained references and six references to the two retired
card fixture paths. An old matched path is navigation, not write permission.
The [acceptance reconciliation](acceptance-reconciliation.json) preserves the
exact JSON values of all five criteria and 42 cases in suites A/P/S/R/L/D.
Historical preparation and reviews remain bound to their original candidates.

## Actual target interfaces

The current core still exposes `SigningReadiness` and
`evaluate_signing_readiness`, a twelve-boolean diagnostic, plus scaffold device
metadata and numeric wire version 1. Current Bridge still accepts legacy
capabilities and connected account requirements for persistent grants. A02 moved
these consumers and fixtures; it did not implement T01. Proposed S03 replaces
the core scanner with `event::ParsedRequest`, adds the private consuming
`AuthorizationSession`, and renames preview APIs to diagnostic `review_approved`.
Those proposed bytes are mapped separately and must not be treated as adopted.

The real service path is `handleLocalServiceRequestAsync` →
`prepareSignerDispatch` → `selectAccountRoute` → the selected dispatcher and
`createServiceRouteDispatcher`/serial transport. T01 must enforce method,
algorithm, catalog, custody, profile, manifest, codec and finite-limit
intersection before any operation write. Preserve S01's client/account
authorization, expected-user/request/session binding, independent response
verification, cumulative budgets and rejection of host review acknowledgements.
An available diagnostic or route snapshot never constructs S03 consent.

The public facade is **`@nsealr/sdk`**: root and `/browser` export browser-safe
namespaces; `/node` additionally exposes framing/NIP46. Internal packages stay
internal. Browser-provider and extension request builders, CLI request/status
commands, service dispatch, both SDK entrypoints/types, developer fixture signer,
simulator replay and Pi envelope adapters are actual cutover consumers. Keep
developer signing private/test-only and the Pi Python/libsecp crypto reference
independent. Add no empty MCU app or Board SDK scaffold as evidence.

## Explicit version and expected-data boundaries

| Identity | Meaning |
| --- | --- |
| `protocols/contracts/v1/`, `nsealr-contracts-v1` | One normative artifact inventory; not a wire-version selector |
| Current `nsealr.signing.v0`, numeric 1 | Retired by the proposed T01 atomic cutover |
| Proposed `nsealr.signing.v2`, numeric 2 | New device request/response semantics |
| `nsealr.capabilities.v1` and profile/implementation/limits/account/route `*.v1` | Separately versioned data formats from the accepted T01 brief |
| S03 `nsealr.authorization.v1` | Internal authorization/binding domain; unchanged by numeric 2 |
| `nsealr1:`, `nsealr1a:`, serial codec ID | Byte framing; keep only if that codec grammar remains unchanged |

Do not replace every `version:1`: enclosing local-service/browser/native formats
have their own contracts. Update the nested device payload and its validators
explicitly. External Nostr/NIP07/46/44 meanings stay unchanged. Numeric1 device
requests, old account/route descriptors and `get_signing_status` reject without
fallback. JSON Schema supplements bounded raw-byte duplicate/Unicode/grammar
checks; parsing JSON into an object first cannot preserve duplicate evidence.

All 170 A02 projection obligations and their original hashes/pointers/preimages
are recorded. Distinct review
[`36a98263`](https://github.com/nSealr/nsealr/blob/36a982639b33a393cb5e9ab28080d03cbabd3773/docs/restart/implementation/reviews/T01-current-spec/review.json)
requested changes on `6324aaa9`: its 38 textual version/status classifications
missed encoded wire1 positives and their dependent values. This correction is
pending the same reviewer's delta review; the old result remains historical.

The source JSON now assigns an explicit semantic group/value action to **every
one of the 170 rows**. There are 119 affected values or containing-source/paired
contexts, including the original 38, and 51 explicitly independent unchanged
values. This does not mean all 119 projected bytes change. Stable request IDs,
case names, event fields and display lines retain their bytes while the paired
request, diagnostic digest or descriptor format changes. The three reported
fields `field-7bc474...`, `field-b69c96...` and `field-275b00...` explicitly receive
wire2 positive payload/envelope/frame replacements preserving the same operation.
Frozen wire1 bytes remain historical rejection input, never a substitute for a
wire2 positive. The finite family closure includes four transports, three
transcripts, two screens, four detail-helper inputs, their five source reviews
and one display-frame source.

Update each encoded/raw pair together: UTF8 request/response, unpadded Base64URL,
static envelope or serial frame, animated payload digest/chunks/frame checksums,
and matching transcript request/envelope/diagnostic digest. The existing codecs
use SHA256 and truncated SHA256 checksums, not CRC. The review diagnostic digest
explicitly includes `request.version`; its value changes under wire2 even when
all event fields and displayed pages stay fixed. Preserve the independent
canonical event bytes, IDs, signatures, key/import/backup oracles and their own
domains; do not confuse them with outer-request or diagnostic digests. Keep each
framing negative isolated: valid wire2/checksum around a bad request ID, a
deliberately wrong checksum around fixed wire2 input, padding rejection, and the
unchanged malformed-payload/unsupported-frame-type failures. Numeric10 remains
an unsupported-version input; numeric1 rejection and numeric2 success remain
explicit obligations.

Define independent semantic inputs/dispositions before the corresponding runtime
changes. Deterministic framing/Base64/SHA256 transformations may define future
expected transport and diagnostic bytes from those fixed independent inputs;
never take expected values from production parser/renderer/signer output. Final
serialized bytes/hashes follow when the artifact is stable, before adoption.
No original preimage, projection obligation or positive/negative family is
dropped. All three generated helpers remain data projections: their source
requests/digests and pages stay paired, with no expected-answer calculation in
the projector, build or runtime tests. Separate policy/NIP46/key-import/backup
domains are explicitly unchanged; legacy status fields remain rejection-only.

The eight independent S03 vectors contain event templates/canonical bytes/IDs/
signatures, not the outer wire envelope. Their bytes, oracle, BIP340 reference,
licenses and old observations remain unchanged. After S03 acceptance, only
explicit device-version/method parsing and positive test-wrapper adaptations are
proposed; preserve all 20 families, decoded duplicate/unknown/trailing/UTF8/numeric
rejections, exact canonicalization, consuming authority and lifecycle invalidation.
Numeric1 rejection and numeric 2 success need new explicit transition controls.
Production remains `SigningUnavailable`/`signing_disabled`; no raw-secret callback,
fixture backend exposure, provider, recovery/export or original-scalar claim.

## Selected provenance transition and strict manifest format

Current `scripts/verify_contracts.py` pins historical import86569, permanent
original-source68508ea and immutable postimage59653fc, plus exact manifest and
consumer hashes. It verifies every data file against committed sources, including
hidden/extra files, and rejects a forged manifest or new unrelated commit. New
T01 files do not exist in 68508ea. Merely editing the current manifest cannot be
an implementation plan; old import identities must not be reassigned to authored
wire2 expectations. Historical templates, patches, index and frozen results stay
byte exact.

Root has selected alternative A: pin the independently reviewed **artifact
subtree Git OID** as a literal
in the root checker, outside that subtree. It reads the approved expected
manifest/data/consumer bytes from that immutable object, never from current HEAD
or an untrusted manifest's claimed baseline. Tree/blob identities survive normal
commit rebase; the actual 5cb16cb/59653fc artifact subtree equality is recorded.
Alternative B's separate staging/adoption is not selected; trusting mutable
HEAD/manifest is rejected. No extra staging phase, registry or future SHA is
required. The literal is filled from the real stable artifact before adoption.

Manifest **`artifact_format: 2`** versions the changed inventory schema;
`artifact_id: "nsealr-contracts-v1"` and the directory remain unchanged and
separate from `nsealr.signing.v2`/numeric 2. The source JSON embeds the strict
schema: retain the existing top-level identity/coverage/generation/retirement/
wire-version fields and replace each `files` row with exactly
`path, disposition, original, baseline, current, adaptation`. Each non-null
digest record is exactly `{mode, sha256}`; regular modes are `100644`/`100755`,
and hashes are lowercase SHA256. Four dispositions have these meanings:

| Disposition | Original at 68508ea | Baseline at 59653fc | Current postimage |
| --- | --- | --- | --- |
| `maintained` | Required, exact original mode/hash | Required, exact adopted mode/hash | Exactly baseline |
| `modified_t01` | Required, unchanged historical binding | Required, unchanged historical binding | New reviewed mode/hash; differs from baseline |
| `authored_t01` | `null`; path absent there | `null`; path absent there | New reviewed mode/hash |
| `retired_t01` | Required, preserved | Required, preserved | `null`; path absent from active data |

Every baseline data path occurs exactly once, including tombstones, plus each
new authored path. Historical pre-A02 card retirements remain in the unchanged
historical adaptation record; they are not invented T01 deletions. `adaptation`
preserves the old baseline row's value for maintained files and states the
declared T01 change for other dispositions. Keep historical source45f8/import86569
identities literal. Original and baseline records are checked against their
permanent 68508ea/59653fc sources, never fabricated for a new file. The manifest
does not contain its own subtree OID or hash. Its exact bytes and mode, all active
data and metadata, and `consumers.json` are bound by the externally pinned tree.
Reject duplicate/unknown fields and paths, unsafe paths, wrong modes/hashes,
unclassified/hidden/nonregular entries, missing retired paths' tombstones and
missing/extra/stale consumer coverage. No second active artifact is introduced.

The normal sequence is approval of these four documents and the actual S03 input
tuple, then implementation under that scope with requirement-derived semantic
expectations and all semantic dispositions established before affected runtime edits.
Once the artifact/candidate is stable, bind its actual postimage modes/hashes,
complete consumers and literal subtree OID; distinct final review approves those
real bytes and the candidate before protected adoption. Routine edits inside the
approved semantics do not each require a new admission. Preserve source/tamper
controls and run rewritten-history/main-only regression before adoption, then
check actual main-only reachability after the real normal rebase. Old author
commit IDs may be absent; the approved tree and permanent 68508ea/59653fc anchors
must remain available. Valid source passes; missing/wrong anchors, forged
HEAD/manifest or a new commit over tampered data, byte/mode/hidden-extra/consumer
tampering reject; exact restoration passes. Do not repeat PR31's transient-anchor
failure. Final hashes/OID are intentionally pending, not an implementation gate.

## Proposed future edit set; no permission granted here

This preparation writes only these four integration documents. A separate root
admission after exact S03 acceptance approves the concrete edit set and semantic
transition below. Final normative postimage hashes and the subtree OID are
reviewed on the stable candidate before adoption, not required before coding:

* Core: new `src/capabilities.rs` and `tests/profile_capabilities.rs`;
  `src/{lib,event,protocol}.rs`, `src/policy/{mod,signing_policy}.rs`,
  `src/session/account.rs`, and the actual version-wrapper/test consumers in
  `src/authorization/tests.rs`, `src/qr/{envelope,limits}.rs`,
  `src/review/{qr,qr_flow,serial,trusted,test_fixtures}.rs` and
  `src/board_profile_tests.rs`, all beneath `crates/nsealr-core/`. Authorization
  ownership, event canonicalization, complete reviewer and scalar behavior stay
  read-only; wrapper changes need the frozen S03 API and independent review.
* One artifact: explicitly reviewed replacements/retirements for the old audit's
  mapped signing/account/route/status/limits schemas, notes, examples and vectors;
  proposed new `schemas/{signing-request-v2,signing-response-v2,capabilities-v1,
  profile-requirements-v1,implementation-profile-v1,limits-v1,account-v1,
  route-selection-v1}.schema.json`, corresponding protocol notes, independently
  authored `vectors/profile-capabilities/` cases and explicit conformance-only
  profile examples. The final per-file list, not a wildcard grant, is required.
* Provenance and projection interfaces: `scripts/{verify_contracts,test_contracts}.py`,
  `protocols/contracts/v1/{manifest,consumers}.json`, its
  `scripts/verify_specs.py`, `tests/test_verify_specs.py` and proposed
  `tests/test_profile_capabilities.py`; `ci/{core-test-projections.json,
  project_core_fixtures.py}` and `crates/nsealr-core/build.rs`. Changes are needed
  to admit independently reviewed new provenance, enforce strict profile data,
  cover all consumers and preserve projection obligations. Extend existing
  meaningful negative controls; never remove source/tamper checks to obtain PASS.
* Actual mapped Bridge protocol/policy/client/transport/framing/QR/fixtures
  modules and their tests, proposed `capabilities.test.ts`,
  `profile-routing.test.ts`, `profile-dispatch.test.ts`, browser-provider,
  extension `messages.ts`/nested request constructors, CLI and service context/
  drivers, SDK root/browser/Node consumers and private developer-fixture signer.
  `consumer-map.json` pins the exact existing paths. Do not rewrite NIP46 crypto,
  pairing/grant storage or host transport-key ownership.
* `apps/desktop-simulator/src/{lib,replay}.rs`, its affected replay modules and
  `tests/vectors.rs`; `apps/pi/app/nsealr_vault/{signer,qr,limits}.py` and affected
  independent adapter tests; existing affected `tests/integration/` modules and
  their helpers. Replace obsolete status assertions with new contract/refusal
  obligations while retaining every one of the17 integration steps. Update
  `docs/bridge/{api,api-review}.md`, direct SDK/CLI/service examples and API docs
  only to describe the new interface. No new package or browser feature.

No current evidence justifies changing `scripts/check_product_gates.py`, its
tests, `tests/integration/run.py`, Makefile, toolchains, locks, dependency sets,
coverage floors, CI workflows, graph, resources, hardware or Board SDK. Existing
gate entrypoints cover the new work; a genuinely necessary additional path must
be justified and reviewed before editing it. Keep real target properties
unknown/unavailable rather than using synthetic profile truth tables to claim
four working devices. Connected initial use is manual, not dependent on F01.
Primitive/context/workflow metadata remains separate; T01 implements no C02 DM.

## Completion and next gates

Preparation checks are source hashes, links, criteria/case preservation and the
existing structural/source validators only. No runtime/full product suite is
run here. The acceptance JSON maps old commands to current executable roots and
marks proposed test entrypoints as absent/not executed. Current `make ci` already
includes both Rust workspaces, Bridge/Pi/common contracts, audits, unchanged
100.00/76.70 floors, reproduction, SDK/pack checks and all 17 product steps; no
second broad acceptance pipeline is needed.

Before implementation: retain the actual S03 distinct review PASS, complete its
normal adoption and actual-main CI; let root choose the full actual source tuple;
approve this four-document map, writable scope, semantic projection dispositions
and format-2/tree-anchor mechanism in one distinct preparation review.
Then save meaningful current behavioral repros, establish independent semantic
expectations before affected runtime edits, implement the atomic cutover, and
pin the actual stable artifact bytes/modes/OID for distinct exact delivery review
before protected PR/adoption. Run focused and complete affected acceptance on
that candidate and verify actual resulting-main CI/reachability. No separate
staging adoption or admission for every in-scope edit is introduced.
No T01 criterion closes in preparation. Resource/physical inventory and every
device qualification remain with their actual owners.

The maintainer now declares an ESP32-S3 with two buttons, a Waveshare P4 with
camera/battery/touch, a Pi Zero SeedSigner kit with240x240 display/three buttons/
joystick/camera, and Tropic development boards. Exact models, revisions, tools
and operator access remain unidentified. This supersedes an inference of wholly
unknown inventory; original historical preparation declarations remain preserved
under their own source identity. Pi QR is proposed as the first real end-to-end
path with a declared complete kit; this adds no T01 scope and does not block
independent profiles or PCB work. No physical property is qualified.
