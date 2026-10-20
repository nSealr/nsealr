# Profile and compatibility metadata v1

`nsealr.capabilities.v1` is bounded reported data. Support, configuration and
current availability are separate axes. Verification and consent are local
typed observations and never wire fields. `verified`, `approved`,
`signing_enabled`, universal gate lists, evidence paths/hashes, security ranks
and physical-approval assertions reject at every nested descriptor position.
Matching metadata is consistency, not device attestation or release acceptance.

The full record has exactly the fields in `capabilities-v1.schema.json`:
`format`, `form`, `profile`, `requirements_id`, `implementation_id`, `limits_id`,
`device`, `custody`, `secure_element`, `consent`, `methods`, `transports`,
`messages`. Profiles are exactly `esp32_no_se`, `pi_qr`, `p4_qr`, `custom_board`.
Methods independently state revision, operation/catalog ID, algorithm IDs,
execution location, limits ID and their three axes/reason. Operation IDs are
`nsealr.discovery.v1`, `nostr.public-key.v1`, `nostr.sign-event.v1`; this last
catalog preserves the strict existing Nostr event-template grammar, not merely
kind 1. An unknown method revision/catalog/algorithm cannot be substituted.
`get_capabilities` has no cryptographic algorithm. Public-key/sign-event methods
use `bip340.secp256k1.v1`. NIP44 IDs are metadata for explicit eligibility tests,
not a new device operation or production custody capability.

An available feature must be supported, configured and have a null reason.
Configured+unsupported rejects. Unavailable/unknown state requires a closed
reason: locked, provider_missing, busy, not_implemented or unknown. IDs are
ASCII 1–128 bytes; device labels are Unicode scalars, 1–128 UTF8 bytes.
There are at most 16 methods, four transports and 32 members per object.
The original UTF8 descriptor is at most 8192 bytes, depth eight. Decoded duplicate
keys/IDs/algorithm entries, unknown fields/enums, unsafe integers, fractional,
negative or exponential number tokens and trailing/BOM/invalid Unicode reject.
An object validator alone cannot recover duplicate evidence from parsed data.

The reference record is exactly `format`, `form: reference`, `profile`,
`implementation_id`, `runtime`. Each runtime entry has exactly `method_id`,
`configuration`, `availability`, `reason`. Resolution uses the caller-selected
exact local `nsealr.implementation-profile.v1` record. No URL fetching, registry,
hash claim or fallback to another manifest occurs. A reference cannot change
static identity, custody, support, execution/algorithm/catalog, transport or
message semantics. Omitted method states may only retain explicit unavailable
or unknown defaults; available states require complete deltas. Unknown/duplicate
deltas reject. If runtime state outside these deltas changes, or the complete
response does not fit actual framed capacity, discovery and stale routes become
unavailable. Never silently omit necessary state or keep a previous route.

The four `examples/profile-manifests/*-conformance-v1.json` records are synthetic
conformance inputs. They identify no actual firmware, PCB, SE configuration,
trusted display, release or operator measurement. Initial consent is manual and
local. Pi/P4 custody is volatile session-only; ESP32 no-SE custody is MCU-wrapped
persistent; custom custody requires an identified, available SE configuration
with no fallback. The custom example intentionally has unknown SE configuration.
Pi boot enforcement can be unavailable only with separate verified limitation
and image/substitution-control observations. Synthetic evidence never passes
production release assessment. Eight common requirement groups are mandatory;
R-MSG is additionally required for connected profiles.

Account v1 records bind selected account/public key, route, profile,
implementation and limits IDs. Their `capabilities.methods` is a bounded unique
list of declared account operations, not a second full device report, evidence
record or consent. Client dispatch separately resolves the current device report
against the explicit local implementation and adapter. The historical
`esp32_qr_vault` route label maps to the explicit `p4_qr` profile in this new
contract; its filename/label does not qualify an ESP32 or P4 device. Existing
policy/grant formats retain their independent historical domains. Every initial
nSealr route is manual_only without a persistent-grant prerequisite. External
NIP46 routes have null nSealr profile/implementation/limits IDs and cannot claim
nSealr physical review or custody. Old account/route formats reject.

Route-selection v1 is immutable diagnostic data: explicit method revision,
operation/catalog, algorithm, contract, transport/codec, profile, implementation,
custody and limits IDs plus account/public-key/policy identity. A selection
is revalidated against current account/connection/capabilities/limits at dispatch.
No downgrade, strongest-device ranking, truncation or alternate account retry
occurs. Existing authentication, client permission, expected-key and response
verification checks remain mandatory.

`nsealr.limits.v1` distinguishes discovery, sign-event, message and transport
dimensions. Every applicable dimension is present, positive, finite and a safe
integer; zero is allowed only for queue/cache counts. No unknown unit or missing
cap means unlimited. Intersections take the minimum for matching dimensions,
then check aggregate retained/pending/queue/cache capacity with checked arithmetic
before allocation/writes. Method limits include original request/response JSON,
parse work, retention, pending/deadline and queues/cache; sign-event adds content,
tags, canonical bytes and review pages. Transport limits include encoded frame,
frame count, reassembly, parse work, retained/pending/deadline and queued frames;
QR explicitly adds static decoded bytes and chunk payload characters. Synthetic
message dimensions do not enable an operation. Peer timeouts cannot extend the
local deadline; unavailable/rollback/overflow clock observations fail closed.

The independent 42-case source is
`vectors/profile-capabilities/cases-v1.json`. Its limits/profile examples are
test inputs, never measured MCU RAM/latency or qualification. NIP44 primitive,
verified message context and a named NIP17/59 one-to-one workflow are separate
features. A primitive does not establish context; subordinate support does not
admit a workflow. Host relay encryption never advertises device message custody.
No NIP04, group/file/ephemeral wrap, conversation-key export or offline DM,
10050/22242 flow is introduced. Synthetic workflow eligibility cannot execute
an opaque seal, establish S03 authorization or expose a production compound API.
