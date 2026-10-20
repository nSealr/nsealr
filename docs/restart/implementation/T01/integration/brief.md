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
`7eee22fbc269033756e53020b1370fc6671da3ab`, is a separately pinned **unaccepted
proposal**, absent from this main. Its final review/adoption and actual-main CI
remain prerequisites. Root has not selected the complete T01 implementation
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
are recorded. Thirty-eight rows contain potentially affected version/status
material. Retaining their obligations does not imply a numeric 1 positive request
can remain an accepted numeric 2 fixture. Before code, distinct review must approve
each affected row's exact source-transition disposition, new independent expected
bytes or historical rejection role. Do not silently drop rows, change pointers,
compute answers from implementation or leave an old active snapshot. Unaffected
values remain unchanged. The three generated helpers remain data projections.

The eight independent S03 vectors contain event templates/canonical bytes/IDs/
signatures, not the outer wire envelope. Their bytes, oracle, BIP340 reference,
licenses and old observations remain unchanged. After S03 acceptance, only
explicit device-version/method parsing and positive test-wrapper adaptations are
proposed; preserve all 20 families, decoded duplicate/unknown/trailing/UTF8/numeric
rejections, exact canonicalization, consuming authority and lifecycle invalidation.
Numeric1 rejection and numeric 2 success need new explicit transition controls.
Production remains `SigningUnavailable`/`signing_disabled`; no raw-secret callback,
fixture backend exposure, provider, recovery/export or original-scalar claim.

## Minimal provenance transition proposed for review

Current `scripts/verify_contracts.py` pins historical import86569, permanent
original-source68508ea and immutable postimage59653fc, plus exact manifest and
consumer hashes. It verifies every data file against committed sources, including
hidden/extra files, and rejects a forged manifest or new unrelated commit. New
T01 files do not exist in 68508ea. Merely editing the current manifest cannot be
an implementation plan; old import identities must not be reassigned to authored
wire2 expectations. Historical templates, patches, index and frozen results stay
byte exact.

Two viable minimal approaches are distinguished in the JSON. The preferred
proposal pins a separately reviewed **artifact subtree Git OID** as a literal
in the root checker, outside that subtree. It reads the approved expected
manifest/data/consumer bytes from that immutable object, never from current HEAD
or an untrusted manifest's claimed baseline. Tree/blob identities survive normal
commit rebase; the actual 5cb16cb/59653fc artifact subtree equality is recorded.
The other approach uses a newly adopted permanent-main commit, requiring a
separate reviewed staging/adoption before its identity exists and careful
avoidance of a second active artifact. Trusting mutable HEAD/manifest is rejected.
No future commit or tree SHA is invented here.

The proposed tree approach extends the existing Git mechanism without another
registry, service or expected-data snapshot. Before approval, specify the exact
strict manifest representation for retained/imported/modified/new/retired files:
keep 86569/45f8/68508ea/59653fc as historical provenance; validate old originals
against 68508ea and independently reviewed new postimages against the new pinned
tree; never fabricate original hashes for new files. Exact manifest field/format
changes remain an explicit addendum decision. Review independent expected vectors
before runtime output exists, then bind all postimage modes/hashes and complete
consumer coverage. The pinned tree must be reachable in a real main-only cold
fetch after rebase with old author commit IDs absent. Valid source passes;
missing/wrong anchors, forgedHEAD/manifest, new unreviewed commits, file/mode/
hidden-extra/consumer tampering reject, and exact restoration passes. Do not
repeat PR31's transient-commit-anchor failure.

## Proposed future edit set; no permission granted here

This preparation writes only these four integration documents. A separate root
admission after exact S03 acceptance must approve the following concrete edit
set and each normative postimage before implementation:

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

Before implementation: complete S03's distinct exact review, normal adoption and
actual-main CI; let root choose the full actual source tuple; approve this current
map, exact writable list, projection deltas and provenance alternative/addendum.
Then save meaningful current behavioral repros, review independent expectations,
implement the atomic cutover, run focused and complete affected acceptance on a
stable candidate, and obtain distinct exact delivery review/protected PR/main CI.
No T01 criterion closes in preparation. Resource/physical inventory and every
device qualification remain with their actual owners.
