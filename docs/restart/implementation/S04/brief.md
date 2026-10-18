# S04 — custody and firmware-owner lifecycle preparation

Author: `/root/s04_custody_author`, 2026-10-18. Assignment: [issue 25](https://github.com/nSealr/nsealr/issues/25).
Input: `nSealr/nsealr` `f2ef70f522af4977e15f81554a8c6eadcdbe8097`.
Branch: `restart/s04-custody`. This candidate contains only this brief,
[source audit](source-audit.json) and [acceptance plan](acceptance-plan.json).
It prepares the subsequent specification work: it does not define a new wrapping
protocol, select a chip, implement custody or close S04. A distinct reviewer must
accept this exact preparation candidate before that work proceeds. The seven
parent acceptance statements are reproduced unchanged in the acceptance plan.
The sole task ledger remains `docs/restart/work-items.json`; the coordinator owns
assignment/state reconciliation after A02. Main and the source tuple remain frozen.

## Authority and bounded outcome

P01's accepted [requirements](../P01/requirements.md),
[threat models](../P01/threat-models.md) and
[event review contract](../P01/event-review-contract.md) determine correctness.
PROD-01/02/03/04/09/11/12 govern identity, entropy, local recovery, authority,
bounds, lifecycle and the generic SDK boundary. S02's
[secret flow](../S02/secret-flow.md),
[entropy contract](../S02/entropy-contract.md) and
[crypto selection](../S02/crypto-selection.md) are integrated constraints.
Code establishes existing behavior and may violate these requirements.

After preparation review, S04 will produce a source-backed custody specification
and persistent-state/fault model for the custom Board, comparing at most the
three retained SE leads. It must say precisely what protection is feasible and
what remains conditional. It may reject all candidates; an inaccessible required
manual, unresolved applicable advisory or missing reset service cannot become a
successful placeholder. Selection of the complete board remains H04, after H02
and H02S. No new firmware, driver hierarchy or orchestration library is needed
to complete this specification task.

S04's eventual outputs are `custody-protocol.md` (including object/authority and
claim tables), `state-machine.json` (transitions and fault expectations),
`se-decision.md` (exact command/advisory/access comparison), and ordinary
hash-bound evidence/review records under this directory. These are later owned
outputs, not files added by this preparation. Generic services belong in B01/B02;
Nostr account semantics remain in the engine. S03/K01 own operation authorization
and signing integration. H01 owns manual admission, H02 MCU feasibility, H02S SE
feasibility, V02 complete custody on the selected host and V03 repetition on the
actual custom assemblies. Independent Board SDK qualification remains B03.

## Current source and contextual limits

The audit records repository commit/tree and each inspected blob's mode, Git ID
and SHA256. It pins these observations:

- `SecretKey`, session keyring, import and backup flows are RAM-only software
  owners. Clear/Drop and redacted formatting narrow exposure; Rust ownership
  does not isolate code sharing the firmware privilege or erase every compiler,
  peripheral and backend temporary. Caller input/output and display copies need
  their own lifetimes. There is no persistent PIN, SE driver, owner-root manager
  or authenticated vault implementation in the inspected product source.
- The source-generation helpers convert caller-supplied material; they do not
  acquire entropy. Account selection validates shape/fingerprint/path, accepts a
  supplied public key and explicitly leaves public-key proof false. Simulator
  recovery replay validates key format, not point derivation. The old persistent
  custody JSON is a declaration excluded from replay, with historical TROPIC/S3
  assumptions; it is not the new product contract or evidence of enforcement.
- `board-sdk` at `043e64ceb745a323f9a332cc02fae2993388fabe` contains instructions,
  README and license, with no implemented drivers. Hardware main is
  `340697d6713a671e9e01b0dc874ec999ab071601`.
- H01 context is frozen at `6f95cc298c5a8108d5c0bdaedfd53e7b81b130ed`
  (substantive `6b45f6f79e1888bdf2ec6680d14dd951b7019327`), with bounded
  independent follow-up `2f9ea3a18d8fb18e3fbaa8f58b6272102f83b9c2`.
  That review keeps H01 incomplete and admits no part. The inherited register's
  readings and access gaps are contextual evidence, not S04 manual sign-off.
  Current RM0456 Rev7 was subsequently retrieved by the coordinator (SHA256
  `6edaaaae0c5d57c58ffc3a576d44e7b62e8d9cd0e495e8f61bab688226fc327c`);
  retrieval does not complete the required MCU lifecycle reading.
- A separate, unintegrated S03 candidate
  `2d7d465a291c4d4a1324d90595fc45a2fdbefca5` documents that its signing-key
  conversion retains the backend's normalized scalar and drops the imported
  `SecretKey`. It offers no recovery export. The audit pins that narrow source
  observation separately; it is not silently substituted for the initial input.
  Reconcile source and review when A02/S03 land before implementing any consumer.

## Claims and candidate comparison to resolve

The trusted boundary is initially one trusted MCU firmware image plus whatever
specific SE service is proved. No interapplication security isolation is claimed.
The MCU owns review pixels, physical input, authorization and any software
signing/decryption. An SE that authenticates its bus cannot know whether the
display was honest or the user consented. A privileged MCU compromise can invoke
available SE commands, steal host pairing credentials/PIN entry and capture
material released to RAM, subject only to separately demonstrated SE policy.

For each candidate compare flash-copy/offline PIN guessing, untrusted USB/host,
bus interception/replay, hostile MCU firmware before and after unlock, rollback,
partial reset/re-enrollment, supply-chain/vendor update authority and the declared
physical fault/extraction threat. State the asset, attacker ability, service,
prerequisites, residual exposure and evidence for every claimed contribution.
Distinguish confidentiality, authorization, availability and recoverability.
An opaque ciphertext or non-exportable wrapping key alone proves neither
identity non-exportability nor secrecy after MCU compromise. Releasing an
unwrapping result to the MCU changes the claim even if the wrapping key stays
inside the SE. PIN observation during an authorized unlock also matters.

| Bounded investigation | Frozen H01 evidence to inspect after preparation review | Required decision, without capability inference |
| --- | --- | --- |
| SE051C2 | SE051 DS Rev2.0; AN12973 Rev2.0; AN12907 update authority; missing AN12543 Rev4.5 and SE051 errata Rev1.1 | Resolve exact OPN/OEF/applet/configuration, lawful API/errata access, object/session policies, SCP/default/recovery key ownership and update delivery. Public headers cannot close missing command semantics. |
| Standard OPTIGA Trust M V3 | DS/reference manual Rev3.70; release notes Rev3.02; I2C protocol Rev2.03 | Resolve the standard purchasable order/configuration and firmware tuple, HMAC/authorization/counter/metadata/reset semantics, shielded channel and host reset/concurrency caveats. A customized wallet part is a different candidate. |
| TROPIC01 | API1.4.0, PIN note1.2, pairing note1.3, catalogue2.0; ODR_TR01_SA_2026012900 v1.0 | The frozen advisory record includes TR01-C2P-T310 Boot2.0.1/App2.0.0/SPECT1.0.0 and establishes no qualified remedy. Resolve actual applicability/remediation and MAC-and-Destroy/host state/default pairing replacement before crediting protection. Forecasts and branding are insufficient. |

Every service row must cite the exact command, parameters, allowed key type and
curve, object policy, session privilege, output material, persistent effects,
failure status and applicable errata. Compare native BIP340 on the raw event
digest and NIP44's required raw shared-x separately from ECDSA, generic ECDH and
channel key agreement. Do not assume any candidate supports native Nostr custody.
The native backup requirement also excludes describing the identity as never
exportable throughout its entire lifetime. Distinguish local recovery export,
prohibited host export, SE object read restrictions and transient MCU use.

A single SE assisting software custody is a comparison case, not a selected
design. A two-SE composition is considered only if a concrete unmet requirement
justifies it. Identify every shared MCU/PIN/channel/root and show what an attacker
who controls either chip or the MCU can still do. A common MCU that obtains both
outputs defeats a claim of independent protection unless an exact, reviewed
construction proves otherwise. Reject additive component-count security claims.
An MCU-only control case establishes what the SE actually adds; it does not
silently change the accepted custom-board promise or select the commercial profile.

## Complete object and authority inventory required

The later protocol must enumerate every concrete object and copy, including
absent/not-used categories explicitly. Each row needs an identifier/version,
exact encoding/size/location, creator and entropy source, secret/public status,
read/write/use/delete authority in each lifecycle state, authenticated binding,
durability/rollback behavior, lifetime/cleanup, backup/recovery and reset outcome.
Do not fill these fields with an invented universal SE API.

| Object family | Mandatory detail and distinction |
| --- | --- |
| Original identity scalar and recovery data | Preserve original native/imported scalar for canonical local `nsec` recovery; inventory input text/camera, pending import, storage plaintext, crypto backend, framebuffer, backups and scratch. Expected x-only public key is public evidence, not a secret or authority credential. |
| Authenticated stored identity record and auxiliary ciphertexts | Enumerate plaintext fields, algorithm/version, nonce generation and crash-safe uniqueness, tag length, complete authenticated metadata, length encoding, schema migration and corruption rejection. Bind identity/public key, profile, owner/enrollment, object purpose and generation as required by the concrete design; identify exactly what those bindings prevent. AEAD authenticity alone does not prevent replay of an old valid record. |
| Storage/release/wrapping keys and factors | Inventory independent random keys, SE-resident objects, any MCU-held shares/derivation inputs, wrapping outputs and caches. Say which keys/plaintexts leave each chip, which service can reconstruct the identity and which authority can call it. A chip serial/MCU UID is not a secret binding key. |
| PIN material and persistent enforcement | Local input, verifier or equivalent SE construction, salts, parameters, retained host state, retry/authorization objects, change transaction and exhaustion state. Identify an authoritative non-rollbackable limiter or show why the proposed design fails. A slow MCU KDF alone is not a persistent retry counter. |
| KDF contexts | For each derivation record source and destination, standard/algorithm, exact byte serialization, salt/info/domain/version, output length, parameter floor and maximum work, and purpose separation. Explain whether a flash snapshot enables an offline PIN oracle. Choose concrete values only after command/threat/resource review; no ad hoc crypto in this preparation. |
| MCU–SE host binding and pairing | Inventory static authentication keys, certificates/pins, vendor defaults, replacement/revocation, transient channel keys/nonces/counters and reconnect/reset state. Distinguish authentication of a chip/MCU from local human consent. Record whether host credentials are extractable under the relevant MCU compromise. |
| Other pairing/transport state | Decide whether the custom device stores any USB/application pairing secret or only public identifiers. Keep Bridge-owned NIP46 transport keys outside identity custody; do not copy them onto the board by implication. Any device-held extra key requires its own purpose, revocation and reset row. |
| MCU firmware trust | Owner public verification roots/digests, bootloader/recovery roots, antirollback counters, debug authorization, provisioning/flash-encryption keys and irreversible configuration. Private firmware-signing keys remain separately owned off-device, not derived from `nsec` or PIN. State owner replacement and lost-owner-key behavior. |
| Vendor SE trust | Manufacturer attestation/transport/default/recovery keys, applet/firmware update roots and authorization credentials, immutable/retained vendor objects and version counters. Identify the vendor-controlled authority even when MCU firmware is owner-controlled. No assertion that a whole chip is erased when immutable vendor state survives. |
| Transaction and session metadata | Durable journals/slots/commit markers, enrollment and policy generations, expected-public-key record, SE IDs/configuration digest, session handles and operation grants. Define integrity, retention, sequence exhaustion and replay boundaries; no unbounded retries/logs. |

Local recovery intentionally creates a secret copy controlled by the person. A
PIN does not protect that plaintext backup. PIN change, firmware-owner change and
device reset do not revoke copies or change the Nostr identity. Any identity
rotation is a separately reviewed user action, not an error fallback.

## Persistent state and failure contract to instantiate

The following are required model dimensions and outcomes, not a selected storage
layout or chip command sequence. The later specification must resolve their
concrete implementation and finite bounds before it can be accepted for coding.
Model MCU persistent state, each SE's persistent state, volatile session/review
state and off-device owner/recovery credentials separately. Model retained
authorization, counter/generation saturation, bootloader/recovery state and
partial loss/replacement of each component; a single `locked: bool` is inadequate.

| Transition family | Required observable outcome and crash/rollback question |
| --- | --- |
| Manufacture/developer → enrollment | Default credentials cannot retain access to owner secrets. Creation/import is local, finite and fallible; setup records the complete owner/SE tuple and expected public key. Interrupted enrollment cannot silently produce an enrolled usable identity or orphan a recoverable copy outside the declared inventory. |
| PIN creation and unlock | PIN syntax, entropy expectation, confirmation, attempt budget and any delay semantics are explicit. Durable attempt enforcement precedes any success-dependent release; interrupted/unknown attempts are conservatively accounted for. Define an allowed lost-attempt bound and availability limit. Reset, power cut or flash restore cannot manufacture additional attempts. No assumed trustworthy wall clock. |
| PIN change | Require the specified current authority and local confirmation; inventory old/new verifier/wrapping state. At every cut, a documented old or new committed state, or explicit recovery-required state, results. No permissive intermediate state, dual valid rollback path or trial budget reset without its authorized transition. A change never alters the identity silently. |
| Exhaustion | Define whether the result is irreversible destruction of a release factor, durable lockout or another exact documented state. No reboot/software downgrade/host snapshot clears it. Explain availability loss and the separate backup-based recovery route; do not call a recoverable lockout erasure. |
| Lock, timeout, cancellation and crash | Invalidate operation authority and SE authorization/channel lifetime as specified, drop owned plaintext and document inaccessible scratch limits. Every boot starts without an old unlock/grant; partial SE-only or MCU-only reset must be included. UI timeout and SE authorization timeout are different mechanisms. |
| Native recovery | Enter validated `nsec` locally, derive the actual full x-only public key independently of a host descriptor and compare with an independently retained expected value before reporting restoration of that identity. Mismatch never replaces the expectation silently. Re-enroll fresh device factors/PIN; do not restore stale retry journals or device pairing roots from an identity backup. |
| Destructive reset / new owner | Invalidate the old enrollment across MCU storage, SE objects, channels and boot/recovery credentials as specified before accepting new owner secrets. Enumerate residual vendor/immutable state and inaccessible remnants. If exact hardware cannot erase/revoke/re-enroll safely, declare the transition unsupported and the affected hardware unsuitable for reuse; do not promise universal factory reset. |
| Firmware update / rollback | Clear active session/grants, authenticate the update under the correct root, validate version and transaction format, and handle interruption of bootloader/application/data/SE updates separately. An accepted old signed image must not regain secret access or reset retry state. Pin recovery fallback and compatibility policy; signed firmware can still be malicious if its authorized signer is compromised. |
| Component replacement / corrupt storage | Wrong MCU, SE, owner root, ciphertext record or generation fails closed. Define when local backup can establish a new enrollment and when the board is unrecoverable. Missing acknowledgements, torn writes, contradictory states and exhausted counters produce typed errors and no operation/secret output. |

For every durable write/erase/SE command, identify a linearization point or an
explicit uncertainty interval. State what is permitted if power fails before,
during and after it, including response loss after commit. Firmware cannot assume
cross-chip atomicity; reconciliation must be demonstrable without granting
another PIN guess or resurrecting an old owner. Fault tests allow documented
availability loss but never conceal it as successful recovery.

Bounds to resolve in the reviewed protocol include PIN alphabet/length/attempts,
KDF work/memory, transaction sizes/slots/endurance, all secret buffers, channel
and command deadlines, recovery retries, generation/counter maximum and supported
version windows. Measured H02/H02S results qualify these on target. No inherited
default number is a security or performance promise.

## Recovery interoperability and firmware lifecycle

Native creation remains uniformly sampled valid secp256k1 scalar plus local
NIP19 `nsec`, per PROD-02/03. An independent expected public key is mandatory for
the recovery drill; recording the just-restored device's own answer as the
expectation is circular. Also compare original and recovered scalar/encoding
using public fixtures: BIP340 backend normalization can preserve the x-only
identity while changing a raw scalar. Preserve the original recovery source
before conversion if promising its original encoding. The future S03 observation
does not imply NIP44 failure; point negation preserves raw ECDH x. No new ECDH
behavior is inferred from a signing test.

Optional NIP06 migration preserves explicit format/version, mnemonic/passphrase
normalization, complete derivation path/account and expected-key checks against
the pinned external specification and independent fixtures. It does not become
the default generation path or a reason to retain a legacy source forever. The
later decision must say exactly what source is retained and exported after
migration; losing a passphrase/path cannot be papered over with a valid checksum.
NIP49 remains deferred; no new password vault format is selected here.

Developer, owner-secured and product-qualified are distinct lifecycle conditions:

- Developer state permits documented development access and public fixture
  material. It claims no production identity custody merely from a mode label.
- Owner-secured state requires an identified owner's MCU boot/update roots,
  documented debug/recovery policy, SE enrollment, persistence and all required
  boundaries. Replacing the trusted firmware owner cannot silently inherit
  privileged identity state. Root rotation under the same owner and transfer to
  another owner need separate authorization and erasure/re-enrollment rules.
- Product-qualified is an evidence designation for an exact hardware, firmware,
  configuration and lifecycle tuple after its physical gates. It is not an SE
  command, a boolean set by firmware or a promise that arbitrary owner firmware
  remains a qualified Signer. Replacing relevant firmware/configuration
  invalidates affected qualification. Returning to development requires the
  specified safe reset path or an explicit irreversible restriction.

The SE decision must separately state who can install/authorize its applet or
firmware, who operates any required service, what credentials and network access
are needed at manufacture/enrollment/ordinary operation/recovery/maintenance,
and what happens when service access ends. Distinguish offline operation from
offline update-package acquisition and offline update application. Record public
API/document access, account/NDA restrictions, source/binary redistribution and
driver/update-tool licenses for a new independent developer; public documentation
does not imply update rights. Owner MCU roots do not confer vendor SE authority.
List finite fuse/counter/key-slot resources and irreversible states, with the
last safe abort and lost-credential consequences. No provisioning/fuse recipe
or permission to execute an irreversible action is created by this brief.

## Review, evidence and stopping conditions

The acceptance plan binds all seven original criteria to concrete review and
fault procedures, independent expected results, later outputs and physical
owners. Preparation verification checks source/blob correspondence, unchanged
criteria and scope; it does not run a test that merely searches for prose.

After preparation acceptance: read exact lawful sources, fill the command and
object tables, resolve the state model, obtain distinct cryptographic/specification
review, then hand the frozen protocol to implementation/physical task owners.
An independent reviewer challenges both specification adequacy and eventual
implementation compliance, including a separate adversarial state trace/oracle.
AI engineering review is not external security certification. A changed
candidate invalidates affected review; record remaining findings honestly.

Hardware, sacrificial units, operator and instruments are **UNKNOWN** here.
No device or physical gate is established. H02 owns MCU owner-root/boot/debug/
erasure/re-enrollment feasibility; H02S owns exact SE permission, PIN, reset and
re-enrollment traces. V02 combines the complete lifecycle and power-cut campaign;
V03 repeats it on identified custom boards with actual trusted UI/buses. Model
success, API labels, compile/link checks and source review cannot substitute.

If mandatory API/errata/terms or remediation are unavailable, keep that candidate
unselected, record the precise missing source and continue other bounded
comparisons. If no candidate supports the required claim, report that outcome
for a reviewed requirement/design decision; do not weaken a gate. The current
delivery stops after committing/pushing these three files for distinct review.
No main merge, product code, tracker edit, external outreach, purchase,
fabrication, production secret or irreversible hardware operation is in scope.
