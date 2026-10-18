# T01 — profile capabilities, routing and evidence specification

Prepared 2026-10-18 by `/root/t01_author` for distinct specification review.
This candidate contains specification, source audit and acceptance plan only.
It does not implement a protocol, admit a device or enable product signing.

## Authority and inputs

T01 implements all five acceptance statements of
[issue 19](https://github.com/nSealr/nsealr/issues/19) and the canonical graph.
Normative product inputs are P01 `PROD-01`–`PROD-12`, its threat models and event
review contract, the graph's profile release gates, and the restart architecture.
Current source establishes observed behavior, including defects; it does not
override those requirements. Four Signer profiles and independent generic
Board/SDK delivery are retained. No universal security rank is introduced.

Preparation starts at actual clean main
`7b5553685dac56029a4379be12054154b6b5e0b5`, graph revision 11. Inspected external
inputs are companion `678796900e462f5504e47fe934e2e5f23d85824f`, specs
`45f8b6ff1123f3f55be4ce457fd1008e91043cc2`, raspberry
`d1534d9dcfba8fe4a35cea2ed3529e32a5003dc6` and NIPs
`37db639582d857e12468dcccd99b2c7f1d657da9`.
[source-audit.json](source-audit.json) records Git blobs, SHA-256 hashes,
observations and consumer disposition. During preparation S01 adoption reached
main `1450e89c53097584de5f2f4eab260eef960690d6`; comparison confirms the inspected
runtime/P01 files are unchanged, while graph, fixture/provenance and bootstrap
inputs changed. The audit records this observation without rebasing preparation.
A02 rehearsal and S03 implementation remain coordination inputs, not silently
accepted new source. Use the complete adopted S01 tuple before implementation.

Only this file, `source-audit.json` and `acceptance-plan.json` are writable during
preparation. Implementation requires recorded distinct approval of this exact
candidate, then a coordinator-approved source tuple and writable scope. Reconcile
A02's actual import/layout/contract manifest and S03's frozen parser/authorization
API before editing shared consumers. No file in another author's worktree is
writable. A02 is rehearsing, so its proposed destination is not already main.

## Source defects and intended outcome

The Rust policy exposes twelve public booleans and enables a diagnostic
`signing_enabled` when every boolean is true, irrespective of profile. Protocol
responses hardcode an ESP32-S3 scaffold. Selected descriptor public keys are
shape-checked and explicitly lack custody-derived proof. The host policy requires
persistent automation for connected accounts, contrary to initial manual consent.
The TypeScript capability validator and JSON Schema disagree about unknown fields
and duplicates. Specs describes `signing_enabled` plus empty gates as authoritative.
Inherited limits lack a per-profile measurement basis; Rust currently builds a
core and host simulator, not an MCU application. These gaps are enumerated as
`G01`–`G10` in the audit.

Replace these contracts with a small typed profile model, a deterministic
diagnostic evaluator and a routing predicate exercised through real Bridge
dispatch. A descriptor tells a consumer what can be requested and the constraints
to apply. It neither authenticates hardware nor approves an action. An evaluator
can explain missing requirements; it cannot make a physical observation true.
Product signing stays unavailable until K01 and actual device admission provide
their respective implementation and evidence.

## Four separate sources of information

Use plain enums, bounded records and explicit functions. Do not create a remote
attestation protocol, new agent/evidence service, generic plugin registry, policy
DSL or second task/release tracker.

| Source | Contents and authority | Required separation |
| --- | --- | --- |
| Static implementation manifest | Known profile, contract revisions, implemented methods/algorithms, custody design, hard capacities and permitted transport set; built with the trusted image | Support does not establish runtime configuration or device/release qualification. Target requirements and implemented features are different records. |
| Trusted local runtime observations | Selected actual custody, device configuration, currently available provider/UI/input, selected identity and local resource state | Constructed by the trusted adapter, never deserialized from a host descriptor. Host values cannot satisfy a local observation. Availability is checked again at execution. |
| Independent release evidence | Existing reviewed procedures/results bound to exact profile, hardware revision, firmware/SDK/bootloader/configuration and limits | Local release tooling reads coordinator-selected evidence, not a remote URL chosen by a descriptor. Reviewed assertions need the cited procedure and result. An enum, signature or digest alone is no physical proof. |
| Untrusted wire descriptor | Bounded reported support, configuration and availability; exact contract/manifest identity and routing dimensions | Always labeled device-reported. Parsing yields `ReportedCapabilities`, never a trusted configuration, release evidence or S03 authority value. It is useful for compatibility and refusal, not attestation. |

Represent the required vocabulary on independent axes, not as a ladder of
increasing trust:

* `support`: `supported`, `unavailable`, `unknown`. Supported means implemented
  for the exact manifest; unavailable means deliberately absent/unsupported.
* `configuration`: `configured`, `unconfigured`, `unavailable`, `unknown`.
  Configured means selected under the local adapter's policy; it does not mean
  tested, healthy or released. Unavailable is not silently converted to configured.
* `availability`: `available`, `unavailable`, `unknown`, with a bounded reason
  such as `locked`, `provider_missing`, `busy` or `not_implemented`.
* `verification`, only in a local release assessment: `verified`, `unverified`,
  `unavailable`, `unknown`, with evidence references and claim scope. Verified
  means the accepted evidence supports that specific assertion at those inputs;
  it is not a statement about the physical device currently attached to Bridge.

An absent required observation/evidence is unknown and blocks its requirement.
An explicitly unsupported method is unavailable and cannot be routed. Contradictory
records, duplicate IDs and a configured-but-unsupported feature reject. The
different condition “boot enforcement is unavailable on this identified kit” can
itself have verified evidence: property availability and verification of the
limitation are distinct. The wire schema has no verification field; a claimed
`verified`, `approved`, `signing_enabled`, `security_rank`, arbitrary evidence URL
or old gate list is rejected, not promoted into any of the trusted records.
An available method requires supported and configured state, known algorithm/
execution semantics and complete finite applicable limits. Known static support
can remain supported while a locked or missing provider makes it unavailable.

## Profile requirements and diagnostic evaluation

Profile IDs are the graph's `esp32_no_se`, `pi_qr`, `p4_qr` and `custom_board`.
Each has a separately versioned requirements ID and exact implementation/limit
manifest ID. `board_sdk` is a separate product class; it is rejected by Nostr
Signer routing and imports no Nostr schema or engine. T01 does not implement B01
or B03's generic SDK interfaces.

All four require the following assertion groups for a **first public release**.
The IDs below are T01 references to accepted requirements, not additional tasks.
Each result names its missing group and evidence owner. None can be satisfied by
a wire field. Optional future features cannot satisfy a missing initial feature.

| Group | Required assertion | Accepted source and evidence owner |
| --- | --- | --- |
| R-ID | One actual custody-derived identity, expected-key binding, separation of transport identity and independent output verification | PROD-01/10; S02, K01, S01, C01 or QH01, actual device task |
| R-AUTH | Complete honest review and physical manual consent; one-use exact-operation authority and invalidation | PROD-04/05, AUTH-01–05; S03, K01, P02 and actual device task |
| R-CATALOG | Get public key and precisely scoped kinds 0, 1, 3, 5, 6, 7, 10002; unsupported kinds/tags rejected under P01 rules | PROD-05/06; K01 and connected/optical client plus renderer qualification |
| R-SECRET | Qualified fallible entropy and backend, secret ownership/placement/clearing limits, no host secret export | PROD-02/03/11; S02, K01 and exact target entropy/memory/failure traces |
| R-BOUNDS | Finite enforced input, output, parse work, retention, pending count and deadlines; actual target feasibility | PROD-09; S01, K01, QH01 where optical, V01/V02/V03/Q02/Q03 as applicable |
| R-RECOVERY | Local nsec backup/import/export and same-identity recovery; no required host plaintext path | PROD-03/11; profile custody/recovery task and P02 |
| R-LIFECYCLE | Exact boot/update/debug/interface/ownership/physical-attacker declaration and applicable measured guarantees | PROD-11 and P01 threat-model row for the selected profile; owners below |
| R-RELEASE | Exact artifacts/inputs, independent closure of blockers, pilot/recovery/reproduction and release documentation | Every applicable release_gate_template condition; D03, Q04, Q05 or R02 |

Additional requirements and permitted limitations are profile-specific:

| Profile | Mandatory configuration and additional assertion groups | What is never inferred |
| --- | --- | --- |
| `esp32_no_se` | USB, manual local consent, explicit `secure_element: absent`; initial persistent release uses `mcu_wrapped_persistent` custody. R-MSG below is mandatory. D01 identifies boot/update/debug feasibility; D02 qualifies encrypted custody, PIN limits, power cuts, host rollback, unsigned/old-image behavior and debug lock; V01 measures target; D03 admits release. A separately labeled volatile engineering mode cannot satisfy persistent-release admission. | No SE-backed protection/non-exportability, custom-board qualification or automatic grants. Unknown persistent/boot configuration blocks release. |
| `pi_qr` | QR, `volatile_session` custody, manual consent, explicit no SE; no DM primitives/workflow or persistent grants. QP01/Q02/Q04 cover exact Linux image/media/adapters, camera/display/input, radios/data paths, no secret writes/swap/logs/dumps, substitution limits and local reload. | Enforced secure boot is not universally required. If unavailable, retain `unavailable` and require reviewed image-integrity/physical-substitution limitations and applicable controls. A signed download is not hardware boot enforcement. Unknown boot properties or missing accepted limitation evidence block R-LIFECYCLE. |
| `p4_qr` | QR, `volatile_session` custody, manual consent, explicit no SE; no DM or persistent grants. QP02/Q03/Q05 cover actual SoC/SDK, boot/update/debug configuration, camera/DMA/RAM, companion chips/radios, permitted channels, session clearing and reload. | No physically absent-radio claim from a disabled companion; no borrowed Pi evidence and no SE non-exportability claim. Exact feasible boot guarantees must be resolved and evidenced by those owners. |
| `custom_board` | USB, manual local consent, `custom_se_assisted_persistent` custody and the exact required SE configuration selected by S04/H04; R-MSG mandatory. S04/H01/H02/H02S specify actual object/API/PIN/wrapping/firmware-owner/vendor boundaries; V02 qualifies lifecycle; V03 repeats on actual assemblies; S05/P03/R01/R02 own applicable pilot/production release. | A generic “SE present” does not establish native BIP340, non-exportability, PIN rollback resistance, independent dual-SE security or complete trusted UI. Unknown/unselected required SE configuration blocks; loss/failure of a required component cannot select MCU custody automatically. |

For all profiles, `consent: manual_local` and `automation: unavailable` are initial
requirements. F01's optional later automation is not a prerequisite for USB,
custom hardware, SDK or any initial release. No runtime `development_accepted`
flag waives a requirement. Test/demo manifests are labeled `conformance_only` and
cannot satisfy public-release assessment, even when their simulated observations
pass a truth table.

The small core evaluator takes a known requirements ID, the locally selected
implementation manifest and typed trusted runtime observations. It returns a
bounded diagnostic list of incompatible/unknown/unavailable requirements and
per-method availability; there is no `signing_enabled` output. Local static
profile selection is not replaced by a profile named in a request. It cannot
produce, deserialize or consume S03's local consent state. The operation owner
rechecks relevant availability and limits at use; a cached ready diagnostic is
never execution authority. Device tasks implement the actual observations.

The contract verifier separately checks release-assessment structure, evidence
coverage and exact binding. It may report `requirements_supported_by_evidence`
or missing/conflicting references; it does not automatically declare hardware
secure or a release shipped. The existing graph/release process remains the
admission authority. T01's real current manifests remain unqualified. Tests use
explicit synthetic evidence in a test-only evaluator context to cover positive
branches; those records cannot be accepted by the production release loader.

## Versioned public compatibility contract

After A02, one normative artifact remains `protocols/contracts/v1/`. Its directory
version identifies the inventory, not all nested wire protocols. New files in
that artifact define capability, implementation-profile, requirements, limits,
account and route-selection schemas with `*.v1` format IDs, and independent
positive/negative vectors. One manifest covers the files and all consumers.
No second snapshot, hidden generated oracle or separate live specification repo
is added. Preserve frozen historical evidence and provenance unchanged.

Use `nsealr.signing.v1` for the new device JSON request/response semantics, with
envelope `version: 2` (the retired `nsealr.signing.v0` used `version: 1`). Make this
mapping explicit in the contract; never infer a protocol version from an artifact
directory or NIP number. All active consumers switch atomically to version 2.
Keep the request ID and S03 strict event-template grammar, canonicalization,
review and disabled production backend unchanged. `get_capabilities` returns
`nsealr.capabilities.v1`; `get_public_key` and `sign_event` retain their defined
operation meaning. Retire `get_signing_status` and its universal all-gates response.
Old version-1 requests, v0 account/route descriptors and removed capability fields
fail explicitly; there is no silent compatibility adapter or retry with v0.

The existing serial and QR byte codecs may retain their existing codec IDs if
their byte grammar is unchanged. Declare the codec ID separately from the JSON
payload revision and limits. T01 does not freeze the future physical QR framing
choice: QH01 must compare static/multipart alternatives on actual screens/cameras.
A01-retained Python remains an independent reference harness, not a qualified
device engine. Its envelope/fixture changes must not replace its independent
crypto oracle with the Rust implementation.

The bounded capability descriptor contains only these categories; the final
schema spells every key and forbids extras at every object depth:

* Format, selected profile and requirements revision, exact implementation and
  limits manifest identities; bounded device labels remain untrusted display text.
* Active custody mode and explicit SE claim: `absent`, `required` with the exact
  configuration reference, or `unknown`. Component “required” and current provider
  availability are separate. A declaration of absence cannot satisfy a required
  SE profile. No generic `has_se: true` shortcut exists.
* Unique method entries with method revision, operation class/catalog revision,
  required algorithm IDs, input/output limits ID, support/configuration/availability
  and manual-consent rule. Advertised support lists actual implementation, never
  all target release requirements. A kind-1 implementation cannot advertise the
  complete P01 catalog.
* Transport entries with codec revision and direction-specific envelope/frame,
  reassembly, retained-state and timeout limits. USB and QR share semantic method
  contracts while keeping different capacities, timeouts and custody.
* Separate NIP-44 primitive, verified-context and named message-workflow entries
  as defined below. Absence means unavailable; unknown does not imply support.

Concrete record keys are fixed here; schema implementation may not add an opaque
extension bag. The full descriptor has `format`, `form: full`, `profile`,
`requirements_id`, `implementation_id`, `limits_id`, `device`, `custody`,
`secure_element`, `consent`, `methods`, `transports` and `messages`. `device`
contains only `name`, `firmware` and `hardware` labels. `custody` contains `mode`
and `configuration_id`; the referenced configuration describes actual key
location, wrapping and MCU/RAM exposure, not just a marketing category.
`secure_element` is a union of `{state: absent}`, `{state: unknown}`, or
`{state: required, configuration_id}`. No selected configuration is invented for
the unresolved custom Board design.

A method entry has `id`, `revision`, `operation_id`, `algorithm_ids`,
`execution_location`, `limits_id`, `support`, `configuration`, `availability`
and `reason`. `execution_location` is `mcu`, `se`, `host_os` or `unknown`;
unknown cannot be advertised as available. Explicit initial algorithm IDs are
`bip340.secp256k1.v1` and `nip44.v2`; generic ECC/ECDSA support is not either.
A transport entry has `id`, `codec_id`, `limits_id`, `support`, `configuration`,
`availability` and `reason`. `messages` has exactly the three feature IDs in the
message section, each containing `support`, `configuration`, `availability`,
`reason` and `workflow_id` (null unless it names a locally known admitted flow).
No message operation payload/API is created by these metadata entries.

The compact form has exactly `format`, `form: reference`, `profile`,
`implementation_id` and `runtime`. `runtime` is a unique bounded list of
`{method_id, configuration, availability, reason}`; omitted entries retain the
manifest's explicitly unavailable/unknown default, never an available default.
The local manifest supplies every immutable full-form field. A reference's
profile must match that manifest. Known method IDs and allowed configurations
are checked before resolving; no delta can create a method or capability.
`reason` in either form is null for available state or a closed reason enum for
unavailable/unknown state, not arbitrary user-facing text. Manifest IDs are
bounded ASCII identifiers bound to their local artifact digest. Exact numeric
limit records use the dimensions and units below, with schema-discriminated
method/transport applicability. These are public data records, not authority
types.

The exact implementation-manifest digest is a consistency key for a locally
selected manifest; it does not prove the attached firmware matches it. A device
cannot cause Bridge to download/trust a new manifest by supplying its URL/hash.
An unknown manifest or revision is an unsupported route, with an inspectable
reason. Changed capabilities, selected account, connection/session or limits
invalidate the route snapshot and pending host work before rediscovery. A
descriptor change cannot preserve approval or upgrade custody silently.

Strict raw JSON ingress rejects duplicate decoded member names, trailing values,
unknown fields, wrong types, invalid Unicode, nonfinite/unsafe/fractional/negative
limit numbers and ambiguous zero values. JSON Schema validates structure, but
does not replace raw duplicate detection or checked resource accounting. Sets
reject duplicate entries rather than normalizing a hostile declaration. Unknown
required enum/revision values fail closed; new capabilities require a versioned
contract change. No unconstrained extension object is introduced.

## Route selection and actual dispatch

Bridge routes an explicit selected account/profile/implementation and method
revision; it does not pick a “strongest” device or choose another account on
failure. Its compatibility check intersects the requested semantics, local
adapter implementation, device report and selected local manifest. Required
algorithms, operation/catalog/workflow revision, transport/codec, custody and
all relevant finite limits must match. Numeric ceilings use the minimum supported
capacity after unit/dimension checks, with explicit deadline policy; a lower cap
is returned before dispatch, never achieved by truncating or changing a request.
Missing values and unsupported algorithms/methods fail before any transport write.

Return a typed reason such as `unsupported_contract`, `profile_mismatch`,
`custody_mismatch`, `required_component_unavailable`, `unsupported_method`,
`unsupported_algorithm`, `transport_mismatch`, `limits_unknown`, `limit_exceeded`,
`runtime_unavailable` or `workflow_not_admitted`. Preserve ordinary authentication,
account-selection and permission checks from S01. Legacy external NIP-46 routing,
if retained by A02, remains a separate external-signer route: it cannot claim a
nSealr profile, physical consent or release evidence. Relay-RPC encryption is a
Bridge transport concern and never advertises user-message custody capability.

The effective route is diagnostic immutable host data, not a device approval.
Bridge must revalidate the operation at dispatch against the selected route and
preserve S01's expected-user/request/session binding and independent ID/signature
verification. Product signing is still rejected by the device until its local
owner authorizes the exact action. An otherwise matching rogue descriptor can
at most invite an attempted compatible exchange; it earns no claim of authentic
hardware/security state. Without a separate implemented and qualified attestation
mechanism, attached-device identity remains subject to the declared threat model.

## Message capability separation

R-MSG is required for the two connected first public releases and forbidden for
the initial offline profiles (PROD-07/08). Define these independent feature IDs:

1. `nip44_v2_primitive`: separate encrypt/decrypt method revisions, exact algorithm
   suite, early plaintext/ciphertext caps and per-operation local consent. A bare
   pubkey/payload API provides no evidence of an unseen signed outer context.
2. `verified_message_context_v1`: the specific event/seal/wrap evidence accepted,
   signatures/author/recipient bindings checked, and what the device can honestly
   display as verified. Primitive support cannot set this to supported.
3. `nip17_59_one_to_one_text_v1`: admitted named client/call-sequence revision,
   kind-14 plain-text rumor, peer and sender copies, verified receiving context,
   reviewed recipient/plaintext bound to encryption and subsequent seal signature,
   cancellation and finite pending context. It includes locally reviewed 10050
   receiving-list setup/replacement and a named NIP-42/22242 flow when its selected
   relay requires AUTH. Reconnect/challenge changes invalidate pending AUTH.

The workflow entry requires both lower-level features and exact C02/device/client
evidence; arbitrary combinations cannot become a usable workflow. A client with
an incompatible call sequence returns unsupported. No NIP-04 fallback, opaque
kind-13 seal signing, conversation-key export, group/file/ephemeral-message
extension or unexplained implicit authentication is admitted. A peer's missing
or invalid 10050 list is unavailable, not permission to use arbitrary relays.
Offline profiles must explicitly reject 10050/22242 and all DM operations in
this initial catalog. Signing and relay publication are separate results.

T01 defines capability dependencies, schemas and routing negatives; C02 owns
the actual compound operation API, crypto, context lifetime and client evidence.
No currently unimplemented DM handler is advertised as supported. A test-only
mock can exercise the compatible route predicate, but cannot make a real product
workflow available. The new version does not change external NIP-07/46 method
meaning or Nostr event/signature/encryption formats.

Pinned NIP-44 defines encryption independently of message workflows and permits
resource-specific caps. Its extended-length framing requires checked expansion;
do not inherit an obsolete universal 65535-byte ceiling as a protocol fact.
T01 tests capability-limit negotiation at 65535/65536 with synthetic limits and
early refusal when actual caps are lower; C02 owns cryptographic vectors there.
[NIP-44](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/44.md),
[NIP-17](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/17.md),
[NIP-59](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/59.md)
and [NIP-42](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/42.md)
support these distinctions; P01 selects the narrower initial product scope.

## Finite limits and current resource boundaries

Every implemented method/transport manifest declares finite limits with explicit
units for decoded request/response JSON, UTF-8 content, tag count/fields/per-field
and aggregate bytes, canonical output, review work/pages, encoded frame bytes,
frame count/reassembly bytes/work, total retained bytes, pending requests,
queued frames/operations, cached responses and monotonic deadlines. DM records
separately bound plaintext, padded/ciphertext/base64 data, signed outer context,
pending compound operations and resulting output. Unsupported transport/method
dimensions are absent under the schema's discriminated union; required dimensions
cannot be absent, null, unlimited or “TBD” on an available route. Zero is permitted
only for expressly disabled queues/caches, with zero retained corresponding data.

Limits must be feasible together: checked encoding/padding/JSON expansion fits
output and transport capacities, simultaneous pending/queue state fits aggregate
retention, and request work/deadlines fit the chosen semantics. Count original
ingress bytes as well as decoded values; compact reserialization cannot erase an
oversized input. Reserve against the cumulative budget before retaining/decoding
or queueing; release reservations on all rejection/disconnect/cancel paths. A
smaller peer limit never raises a local hard ceiling. Host time cannot change
S03's trusted local deadline. Bound capability discovery itself before parsing.

For T01's **portable conformance harness only**, a capability response may contain
at most 8192 decoded JSON bytes, 16 method entries, 4 transport entries and 32
bounded reason/requirement entries; identifiers/labels are at most 128 UTF-8
bytes and nesting at most 8 containers. It uses one pending discovery, no queue
or result cache, and a fixed test clock deadline. Its decoded response storage
budget is 8192 bytes; record separate parser scratch and typed structure sizes.
These are reviewed software-test ceilings, not measured MCU/QR maxima. A
descriptor unable to fit a transport's declared response cap is unavailable on
that transport; do not enlarge the existing 1024-byte serial frame or 704-byte
decoded legacy request ceiling to make discovery pass. A compact manifest
reference plus bounded runtime deltas may be used on constrained transports,
but the receiver must resolve the exact locally trusted manifest and account for
the full resolved limits; unknown references reject. The full form and reference
form have disjoint explicit schema variants and identical resolved semantics.
Compact deltas may only reduce availability or select a configuration explicitly
allowed by that manifest. They cannot change profile, custody, algorithms, method
semantics, hard limits or evidence. Discovery is a non-secret metadata exchange;
it does not require a prior usable operation route. Resolve and validate its
manifest before allowing any operation dispatch. This avoids a discovery/routing
cycle while preserving refusal of unknown implementation manifests.

S03's portable 4096-byte input/2048-content/4096-arena and retained 8 KiB operation
/16 KiB session budgets remain owned by S03. T01 cannot widen them through a
descriptor or embed another operation copy. S01's existing cumulative host limits
remain enforced. Profile owners later replace conformance settings with exact
qualified values and must reject any target exceeding common hard capacities.
No physical resource is available for T01; no measured device ceiling is invented.

## Proposed implementation boundary and sequence

After approval and source reconciliation, the proposed writable scope is:

* Core profile/capability types and replacement of `policy/signing_policy.rs`,
  its module exports, bounded protocol serialization and metadata/version dispatch;
  focused tests under `crates/nsealr-core/tests/`. Preserve S03's parser and
  authorization ownership; metadata parser/version edits require its frozen API.
* Active contract schemas/protocol notes/vectors/verifier under A02's one
  `protocols/contracts/v1/` artifact. Update its manifest/provenance using the
  approved mechanism; preserve historical acceptance bytes.
* Migrated Bridge `packages/{protocol,policy,client,transport,framing,qr,fixtures}`
  and their direct SDK/browser/CLI/service consumers only as necessary for the
  contract cutover and bounded route dispatch. Retire obsolete active readiness
  and connected-automation assumptions. Do not implement F01 or rewrite grant
  state, host pairing or NIP-46 transport-key ownership.
* Simulator replay/fixtures, Pi reference envelope/capability adapters and their
  independent tests; active documentation/examples and affected integration cases.
  Source audit lists original paths and A02 mapping. No device app, hardware,
  board-sdk dependency or alternate Nostr engine is added.
* T01 evidence and acceptance harness; existing build/test entry points only
  where required to run the new boundary tests. No coverage reductions or broad
  CI/toolchain changes.

Implement in this order: exact-input/consumer reconciliation; save existing
behavioral repros; review independent truth-table/vector expectations; implement
types/schemas and diagnostic evaluator; migrate all retained consumers together;
run real Bridge dispatch/retention negatives; delete replaced active contracts;
run affected integration and distinct final review. Unknown input/layout or an
overlapping author freezes the affected edit instead of inventing a second copy.

## Acceptance, delivery and stop conditions

[acceptance-plan.json](acceptance-plan.json) maps all five acceptance criteria to
positive/negative cases, source gaps, independent oracles and exact commands.
It distinguishes commands available at these inputs from proposed commands to
be added with implementation. A failed compile from an absent new API is not a
behavioral reproduction. Schema acceptance alone does not prove dispatch,
retention enforcement, physical consent, device speed or release admission.

Preserve hashes, environments, commands, exit codes, initial failures and final
results. Test hand-authored decision cases in Rust/TypeScript and the independent
Python contract checker; expected results must not come from code under test.
Exercise downstream service-to-transport dispatch with a recording fake transport,
including zero writes on rejection and unchanged S03 zero product crypto output.
Run affected Rust, Bridge, Python, common-fixture and migration/provenance gates;
then the consolidated CI recipe once coherent. Required unavailable hardware
checks remain open under their owning tasks, never marked passed by simulation.

Stop for a missing required security decision, changed source/approved schema,
unbounded state, inability to preserve S01/S03 properties, inability to fit the
declared transport bounds, or loss of an independent oracle. Revise and re-review
the brief before widening scope, capacities or trust. Unknown SE/custody designs
block the affected real-profile admission, not other profiles or portable tests.
No final T01 acceptance without schema, vectors, actual evaluator/routing tests,
consumer cutover and distinct review of the exact candidate. No release closes
from this task. Root owns task graph, integration and final approval.

Additional primary sources read 2026-10-18:
[NIP-07](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/07.md),
[NIP-46](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/46.md),
[RFC 8259 sections 4, 6, 8–9](https://www.rfc-editor.org/rfc/rfc8259.html),
[JSON Schema 2020-12 core](https://json-schema.org/draft/2020-12/json-schema-core).
