# S04 candidate custody protocol, revision 1

**Status: documentary candidate, not approved for implementation or part selection.**
Author: `/root/s04_custody_author`, 2026-10-18. This is the concrete, deliberately
bounded **TM-HMAC-1 experiment** evaluated against the accepted P01 contract.
It is not a claim that a production design has been found. The
[decision](se-decision.md) and [state model](state-machine.json) are inseparable
from this document. The [source register](research-source-register.json) binds
primary sources and failed retrievals; its source IDs are used below.
The seven unchanged parent criteria and independent-review procedures remain in
[acceptance-plan.json](acceptance-plan.json).

The exact preparation was independently accepted at `905f30ea`, with coordinator
receipt `993f3be8`; byte-exact copies and provenance are in
[preparation-review](preparation-review/PROVENANCE.json). That acceptance allowed
this research, not this construction. Main remains `f2ef70f`; the actual source
bindings in [source-audit.json](source-audit.json) still apply. Reconcile A02 and
the separately reviewed S03 before any implementation handoff.

## Decision and scope

Standard Trust M V3 exposes enough public command semantics to specify a
counter-limited HMAC/PIN and release-record experiment. Neither SE051 nor TROPIC01
is silently substituted if this fails. TM-HMAC-1 uses **one** SE and software
secp256k1 operations in one trusted MCU image. It does not claim chip-native
BIP340, NIP44 ECDH, identity non-exportability, hostile-app isolation, two-chip
independence, physical qualification or MCU-compromise secrecy after unlock.

This revision intentionally has a finite SE-key lifetime and terminal retirement.
It has **no same-chip factory re-enrollment after retirement or PIN exhaustion**.
Those are material usability/maintenance limitations, not hidden future features.
H02/H02S and product review must decide whether that bounded result is usable.
This fails the generic Board's practical reusable-platform requirement as a
production architecture. A longer-lived construction needs a separately reviewed key-rotation/reset
protocol; simply granting a reset key access to the counter is unsafe. The pinned
[Safe7 reference](safe7-reference.md) provides a concrete cyclic destructive-reset
alternative for later analysis. It does not modify this experiment; this
experiment's failure is not a proof that all Trust M constructions fail.

The three new decisions in this experiment are:

1. PIN guesses use an SE HMAC under a random, unreadable, unchangeable key.
   A PIN itself is not the key for a public HMAC challenge transcript. Otherwise
   that transcript can become an offline PIN oracle.
2. A successful PIN authorizes a separate release record containing a fresh
   vault factor and the exact active header hash. Rotating that record on PIN
   change prevents an old MCU snapshot from selecting an older vault merely
   because its AEAD tag is valid.
3. All operational metadata is fixed, with protected metadata update disabled.
   There is no maintenance root that can independently restore the attempt
   counter or replace the PIN reference. Retirement consumes this object set.

## Security statement and its limits

The conditional positive claim is narrow: after honest enrollment and a completed
lock that clears SE authorization, an attacker with MCU flash, its platform
binding secret and arbitrary SE command access, but **without prior unlock
transcripts/plaintext, a valid PIN-derived credential, SE extraction/fault bypass
or an already-authorized SE session**, must consume persistent SE queries to
derive candidate PIN credentials. MCU flash rollback does not restore those
queries. A forged 256-bit credential is a separate negligible-probability attack,
not a PIN guess. This is a protocol argument requiring independent review and
physical enforcement evidence, not an observed property of nSealr.

| Attacker / condition | Actual contribution and residual |
| --- | --- |
| Flash copy alone, SE unavailable | The random SE HMAC key and release factor are absent. Ciphertext does not by itself supply the PIN-derived credential. An MCU-only password vault normally has an offline oracle. |
| Arbitrary MCU commands while cleanly locked | Linked counters and AUTO permissions, if enforced for **every** applicable command, limit credential queries and deny release/reset. Malicious commands can exhaust counters, terminate objects or otherwise deny service. |
| Hostile USB/Bridge | No custody command takes PIN/nsec from that interface. This policy and local consent are enforced by the trusted MCU, not understood by the SE. |
| Physical bus observer | Full shielded command **and response** protection is required. Pairing authenticates channel possession, not the user. No forward-secrecy claim is made for later compromise of the shared binding secret and recorded traffic. |
| MCU compromise during or after successful unlock | It can obtain PIN-derived credential, release factor, original scalar, backups and signing authority; it can retain them and alter mutable data/counter thresholds while AUTO is active. Future lock does not undo this compromise. |
| Malicious firmware already installed before a later unlock | It can capture the next PIN and secret. Owner firmware authenticity/rollback and UI integrity are essential independent H02/V02 requirements. |
| Old valid MCU snapshot after a completed PIN change | Current SE release record selects a different header/factor. A missing matching slot yields recovery-required, never old-vault fallback. An attacker who already retained an old release factor/identity is outside this revocation claim. |
| Full SE-state extraction plus MCU ciphertext | Extracted A_target and R reconstruct Kv without knowing the PIN. The PIN is not an independent factor against this attacker. No protection is claimed. |
| SE invasive faults | Secrecy, counter and logical-erasure claims are unproved. H02S owns exact attacks/advisories; certificates and unreadable-object flags do not supply this proof. |
| Two SEs sharing this MCU | No independence credit. This experiment has no second SE; collecting both factors in compromised MCU RAM would not establish independence. |

Possession of an nsec backup independently grants the identity. Changing PIN,
firmware owner or device does not revoke that backup or previously copied scalars.

## Exact bounds and primitives

These are proposed **experiment limits**, not measured product maxima:

- One identity, two logical vault slots, one outstanding SE command, one
  authorization session. No queue, hibernate restore, background crypto or
  concurrent SDK consumer may touch the SE.
- PIN is 8–12 ASCII decimal digits, preserved including leading zeros, locally
  entered and confirmed. No Unicode conversion, trimming or host PIN API.
  Ten completed candidate-credential queries are allowed between successful
  authentications. A counter threshold of 11 with initial value 0 implements
  that interpretation of IFX-RM p80; the off-by-one and every error path are a gate.
- A separate lifetime counter limits **combined HMAC credential-generation and
  AUTO-verification uses** to at most 2048. A normal unlock costs two uses.
  Initial enrollment checks and PIN changes also consume uses. This is a
  **chosen experiment policy**, conservatively applying IFX-RM §6.5.6's
  recommended2048 uses per shared secret; it is not an immutable chip limit
  or the NVM endurance rating. The real counter stores32-bit count and32-bit
  threshold and its CHA permission can rewrite both (IFX-RM pp55/95). A
  differently justified bound is possible in principle, but changes require
  cryptographic/lifetime review and do not solve cross-object safe reuse. Do
  not market this as2048 unlocks or Trust M's inherent lifetime. No software
  override or counter refresh is allowed within this experiment.
- Sequence generation is unsigned 64-bit, initial 1, no wrap. One PIN-change
  transaction at a time. Generation saturation retires this enrollment.
- SE command deadline 10 seconds; total unlock transaction deadline 60 seconds,
  excluding local input. No automatic retry after uncertain SE dispatch.
  Cancellation clears owned RAM and forces SE authorization reset.
  Preflight requires at least2 remaining combined uses for unlock/retirement,
  6 for a PIN change including fresh old/new proofs and final new-PIN unlock,
  and5 for pending-change repair including final new-PIN unlock. Additional
  wrong entries or faults still spend uses and can prevent completion; these
  are not hardware reservations or refunded budgets.
  These are experiment deadlines; release must measure worst-case monitor/
  transport delays and distinguish timeout from known command rejection.
- Maximum transient custody working set budget: 4096 bytes, excluding the
  separately measured local renderer and crypto backend. Exact stack/heap,
  driver copies, DMA and timing remain target gates; this number is not a
  successful memory measurement.
- SHA-256, HMAC-SHA-256, HKDF-SHA-256 (RFC5869), and
  AEAD_CHACHA20_POLY1305 (RFC8439; key32, nonce12, tag16).
  No truncation, PBKDF2, bespoke stream cipher, XOR wrapping or custom Schnorr.
  HMAC is an SE service; HKDF and AEAD are proposed MCU services whose exact
  implementation/dependency selection still needs S02/B02 review.

All random objects use S02's fallible, qualified entropy contract. A failed or
partial fill clears its whole destination and ends the operation. No fixture,
clock, previous bytes or unqualified fallback. The source/provider is still
unqualified on actual hardware. Valid native scalars use rejection sampling,
not reduction modulo n; use at most 128 draws in this experiment.

## Byte-level records and derivations

`||` concatenates bytes. All record integers are unsigned **big endian**.
ASCII domain literals below include exactly one final zero byte. All reserved
bytes must be zero; all sizes and algorithm/profile IDs must match before
decryption. Unknown versions, noncanonical fields and trailing bytes reject.

`E` is a fresh random 16-byte enrollment ID; it is public and is not an
authentication key. `G` is the generation. `D` is the original valid 32-byte
big-endian scalar, saved **before** signing-library normalization.
`P = x(D*G_secp256k1)` is the actual 32-byte x-only public key.

The PIN credential is:
`A = HMAC-SHA256(Kp, ASCII("nsealr:S04:pin:v1") || 00 || E || len(PIN):u8 || PIN || zeroes(12-len(PIN)))`.
The input is exactly 47 bytes: domain18 || E16 || length1 || digits/padding12.
No PIN string, verifier, A, Kp or release factor is stored in MCU flash.
The domain bytes are hex `6e7365616c723a5330343a70696e3a763100`.

The vault header `H` is exactly 160 bytes:

| Offset | Bytes | Value |
| --- | ---: | --- |
| 0 | 8 | ASCII `NSEALR01` |
| 8 | 2 | schema 1 |
| 10 | 2 | suite 1 = this HKDF/AEAD combination |
| 12 | 2 | profile 1 = this custom-board custody experiment |
| 14 | 2 | flags 0 |
| 16 | 16 | E |
| 32 | 8 | G |
| 40 | 32 | SHA256 of H02-defined MCU owner-root manifest |
| 72 | 32 | SHA256 of exact raw SE UID object E0C2 |
| 104 | 32 | P |
| 136 | 12 | fresh AEAD nonce N |
| 148 | 4 | plaintext length 96 |
| 152 | 8 | zeros |

The UID and owner-root digests prevent accidental cross-context reuse when the
trusted firmware checks them. They are public descriptors, **not SE-attested
firmware measurements**. The SE cannot establish that the caller used the
current MCU root or honest firmware. The exact H02 root-manifest format, UID
readback tuple and physical storage map are blocking consumer-input gates.

The plaintext `M` is exactly 96 bytes: D32 || P32 || E16 || G:u64 ||
profile:u16(1) || source:u8 || reserved:u8(0) || zeroes(4).
Source 0 means native random scalar, 1 means local nsec import. Other values
reject in this revision. Store original D, not the signing backend's normalized
d or n-d representation.

For independent random release factor `R` (32 bytes):
`PRK = HKDF-Extract-SHA256(salt=R, IKM=A)`;
`Kv = HKDF-Expand-SHA256(PRK, ASCII("nsealr:S04:vault:v1") || 00 || SHA256(H), 32)`.
`(C,T) = ChaCha20Poly1305_Encrypt(Kv, N, aad=H, plaintext=M)`.
A slot contains exactly `H160 || C96 || T16` = **272 bytes**. No detached
verifier or unauthenticated recovery hint is appended. Two slots require
independently erasable storage regions of at least 272 bytes each; actual erase
granules, alignment, ECC behavior and barriers are H02/B02 inputs.

Every newly encrypted slot obtains a fresh R and N. After interrupted preparation,
discard both and start with fresh entropy; do not re-encrypt altered content under
a retained key/nonce. Retransmitting the identical already-prepared bytes is not
a new encryption. Only a slot whose header hash equals the current SE record
may activate, and the full AEAD tag and plaintext equality checks must pass.
AEAD alone is not antirollback; this protocol's current SE record supplies that
selection under the stated honest-MCU and SE-enforcement assumptions.

The SE release record `Q` is exactly 128 bytes:
magic `NSR1` (4) || version1:u8 || state:u8 || reserved:u16(0) ||
E16 || G:u64 || SHA256(H)32 || R32 || A_target32.
State 1 means active/pending activation; state 2 means retirement tombstone
with hash, R and A_target zero. Pending PIN change is recognized only after
authentication, when the authenticated input credential differs from A_target.
No unauthenticated MCU commit marker is authoritative.

## Stored objects, permissions and copies

Proposed operational metadata uses IFX-RM p80–91 expressions, not an invented
generic SE API. C0 is operational 0x07; D8 is explicitly NEV on every owned
object; read back the entire existing metadata before and after hardening.
Omitted TLVs leave old values in place, so omission is not a way to remove a
factory MUPD policy. No protected-update trust anchor or update secret is
provisioned for this construction. Reject unexpected factory policies, capacity,
unremovable tags or existing operational objects. D0/D1/D3 encode CHA/RD/EXE;
Conf(E140) means shielded protection as appropriate for the direction.

| Object | Exact content and placement | Operational authority / lifetime |
| --- | --- | --- |
| Kp, F1D0 | 32 random bytes; PRESSEC(0x21) | RD=NEV; CHA=NEV; EXE=Conf(E140) AND Luc(E120) AND Luc(E121). Secret was temporarily in trusted enrollment MCU RAM; no lifetime-never-exported claim. No backup. |
| Q, F1D1 | BSTR(0x00),128 bytes above | RD=Auto(F1D2) AND Conf(E140); CHA=same; EXE=NEV. Returns plaintext Q to authorized MCU. Each full replacement revokes selection of previous vault generation. |
| A, F1D2 | AUTOREF(0x31),32 bytes | RD=NEV; CHA=Auto(F1D2) AND Conf(E140); EXE=Conf(E140) AND Luc(E121). Self-authorized full replacement is a specific unresolved permission/tear gate; do not assume it works because an example initializes AUTOREF. |
| Attempt C, E120 | UPCTR(0x01), count:u32 || threshold:u32, initially0,11 | RD=ALW; CHA=Auto(F1D2) AND Conf(E140); EXE=Conf(E140). Successful PIN holder can write **both count and threshold** by the real API. Honest firmware writes exactly0,11; this cannot protect against a previously authorized hostile MCU widening the threshold. |
| Lifetime L, E121 | UPCTR(0x01), initially0,2049 | RD=ALW; CHA=NEV; EXE=Conf(E140). Never reset. Direct increment can cause DoS. Linked updates of Kp/A share this bound. |
| Platform binding PBS, E140 | PTFBIND(0x22),64 fresh random bytes in SE and MCU protected storage | RD=NEV; CHA=NEV after enrollment; EXE=ALW as required for channel. MCU extraction defeats host binding. No PBS backup, vendor default or fleet-wide key. Fixed PBS means owner transfer/re-pairing is not supported by this revision. |
| Host freshness, F1D3 | BSTR(0x00),32-byte fresh host nonce; public value, overwritten after each new channel | RD=Conf(E140); CHA=Conf(E140); EXE=NEV; D8=NEV. Full protected write/read comparison follows IFX-RM §6.6.3.1. This adds one NVM write per established channel; stale/replayed value rejects. |
| Vault slots, MCU | Two272-byte records | Readable untrusted ciphertext. Only successful local custody transaction writes; flash replacement can destroy availability. Previous slot remains until Q selects the new slot and A transition completes. |
| Source and crypto RAM | D32, normalized signing scalar/backend temporaries, A32, Q128, R32, Kv32, PRK32, PIN<=12, H160/M96/C96/T16, channel/session buffers | Single trusted image. Clear each owned temporary on success/error/cancel, retaining only original D in the active session and backend material needed for an authorized operation. Compiler/peripheral copies require target audit; Rust Drop alone is insufficient. |
| Local input/display | nsec text, keypad/edit buffer, optional camera buffer, recovery framebuffer and display controller memory | Local recovery flow only. Clear after dismissal/timeout/cancel; target proves controller behavior. No logs, crash dump, USB trace or host export. No automatic optical/host fallback. |
| Recovery copy, off-device | Original scalar encoded as NIP19 nsec; expected P stored separately by user | User-controlled plaintext secret. Device reset cannot erase it. Expected P is public but must come from independently retained trusted evidence. |
| Channel session | Shielded V1/PVER0x01: TLS-PRF-SHA256 derivation labeled Platform Binding;40-byte result split into two AES128 keys and two4-byte nonce prefixes; CCM8, RND32, MSEQ/SSEQu32; one auth session E100..E103 | Exact wire/KDF ordering remains the pinned vendor IFX-I2C §§6.3.2/6.3.5 contract, not an additional nSealr KDF. No hibernate save/restore or claimed PFS. Volatile driver copies/zeroization and transparent retry behavior need closure; no homegrown channel. |
| Other pairing | None on device | Bridge NIP46 transport keys remain Bridge-owned. No USB client pairing key, automation grant, NIP49 password, BIP39 seed, device account database or second SE share. |
| MCU boot/firmware roots | Owner public roots/digests, rollback state, debug/recovery policy and any hardware protection key | H02 must provide exact MCU-specific encodings and erase/re-enroll semantics. Private owner signing/debug credentials stay off-device, independent of D/PIN. Unknown fields cannot become zero-filled mock roots. |
| Vendor SE state | E0E0 factory certificate, E0F0 factory key, UID, firmware/ROM/library version, factory trust and monitor state; any existing E0E8/E0E9/E0EF anchors and other objects | Inventory/read policies from actual standard part before admission; do not repurpose factory authority. Their existence does not authorize nSealr custody. Terminating our objects does not erase immutable manufacturer state or establish MCU control of SE firmware. |

The host-freshness object adds a write on every new channel, and the two counters
consume NVM writes on every linked use. IFX-RM p79 gives
600000 updates per counter and 2 million across all objects; count protected
operations/monitor changes too. The finite 2048-use experiment does not prove a
target lifetime, endurance margin or future re-enrollment count.

## Real command path and mandatory guards

Use the pinned IFX-API/IFX-UTIL semantics and IFX-RM command format:

1. OpenApplication0x70/0xf0 with Param0x00 initializes a clean context and
   invalidates any saved application context. Never use restore Param0x01 or
   CloseApplication(hibernate); the latter can persist achieved security state.
   Establish shielded V1/PVER0x01 with PBS; do not infer V2 support from the
   generic I2C protocol document. Obtain a fresh32-byte host nonce, write it to
   F1D3 and read it back with full protection, comparing all32 bytes before any
   custody operation (IFX-RM §6.6.3.1). V1 alone has no host freshness challenge.
   Every new/re-established channel requires this test again; a driver that
   transparently re-handshakes without exposing it fails the adapter gate.
   A mismatch, lost result or entropy failure ends the transaction and resets.
   Every custody command requests full command and response protection.
   The HMAC API defaults to command-only protection; relying on that default
   would expose A. Reject downgrade or failed authentication. Reapply the full
   protection setting before **each** API call: IFX-RM §6.6.2 says it resets to
   the configured default after invocation. No transport-level automatic APDU
   re-execution is accepted as harmless result retransmission.
2. `optiga_crypt_hmac` with SHA256, secret F1D0, fixed PIN message, exactly32
   output bytes uses EncryptSym0x14/0x94, suite0x20, **start-and-final**.
   No output truncation or host retry. Link-count changes precede returned A.
   Other accessible Kp uses (HKDF/TLS PRF/HMAC variants/chaining) must be
   independently shown not to bypass the counter or export Kp.
3. `generate_auth_code` obtains32 random bytes in one acquired session, optional
   data empty. Host MAC is HMAC-SHA256(A, random32 ||
   ASCII("nsealr:S04:auth:v1") || 00 || E).
   `hmac_verify` uses F1D2, SHA256 and that exact arbitrary suffix.
   The driver marshals session OID in the device verification data; it is
   **not** prepended a second time to the host MAC input. IFX-AUTH-EX and
   IFX-RM pp59/116–117 establish this distinction.
4. Successful AUTO is retained in SE RAM. Read Q with GetDataObject0x01/0x81,
   offset0,length128; require exact length, magic/version/E/state/hash.
   Counter reset is SetDataObject0x02/0x82, erase-and-write0x40, offset0,
   bytes count0/threshold11. Never use SEC monitor delay as the PIN counter.
5. Full A/Q replacements also use SetDataObject erase-and-write, exact lengths.
   Clear AUTO via `optiga_crypt_clear_auto_state` at every boundary and force a
   jointly verified SE/MCU reset before advertising locked state. A failed/
   uncertain clear is not success. MCU-only reset is not assumed to clear the SE.
   Repeated protected read with AUTO absent must fail in the physical campaign.

Known command failure is not a partial successful unlock. Unknown dispatch or
lost response consumes whatever chip counters were advanced; no counter credit
is restored from a host journal. Return no secret or operation authority until
all checks, cleanup and identity derivation have completed.

## Enrollment, unlock and PIN change

**Enrollment:** only on an identified unowned development sample with a qualified
entropy source, under the later separately authorized hardware procedure.
Generate E/Kp/PBS/R/D and local PIN; derive actual P. Initially provision these
objects under their exact factory permissions, stage the first vault and Q/A,
then set every operational policy and verify readback/negative accesses. Clear
all provisioning copies of Kp/PBS except the designated MCU PBS store. No usable
product identity exists until metadata hardening, power-cycle checks and local
expected-public-key recovery drill succeed. Interrupted provisioning is
quarantined; never accept a partly initialized sample using permissive defaults.

**Unlock:** confirm trusted MCU lifecycle and reset/clear AUTO first. Strictly
parse at most two slots. Both candidate headers must agree on E/profile/owner/
SE binding; a stale or inconsistent header may force recovery-required, never
choose a different E and silently try a second PIN. Perform one credential
query and one AUTO proof. Failure leaves the persistent cost spent. On success
read Q; select **only** its matching H; decrypt/verify M and independently derive
P from D. Check P against both stored P fields, E/G/profile equality and Q.
If any mismatch occurs, clear/reset and require recovery; do not return a
self-reported descriptor key. Reset C only after those checks. Clear AUTO, A,
R/PRK/Kv/Q/PIN and release any session before enabling an operation using D.

**PIN change:** require a separate local flow and fresh successful old-PIN
authentication; current D alone is insufficient. Confirm new PIN twice.
While old AUTO is valid, reset C, derive A_new using Kp (spending C/L), generate
fresh R/N and G+1, stage/read back/AEAD-check the new slot. Write Q_new containing
A_target=A_new and the new header hash. This is the **vault-generation commit**.
After readback, replace F1D2 with A_new, explicitly clear AUTO and prove A_new
using a fresh challenge, reset C, then clear/reset again. This is the
**PIN-credential commit**. Report completion only after fresh new-PIN unlock;
erase the older MCU slot only then. Final command loss never implies completion.

Between those commits the old PIN may still authenticate, but Q only selects
the new slot. A recovery continuation uses A_target from Q to validate the new
slot and complete F1D2 replacement; it **does not** open an ordinary old-PIN
session or export D. The prior new-PIN confirmation authorized that transition.
New PIN works after F1D2 becomes A_new. If F1D2 is torn/invalid so neither PIN
authenticates, only independent nsec recovery remains. This deliberately permits
availability loss rather than a guessed rollback or bypass. Independent review
must challenge this two-commit mechanism before implementation.

Identical old/new PIN is rejected locally. A previously observed/captured A or D
cannot be revoked by claiming these transactions completed.

## Power loss, rollback, exhaustion and reset

[state-machine.json](state-machine.json) names each cut and its outcome.
A full Q/A/counter write may be old, new or invalid after a fault until the exact
part proves stronger semantics. The protocol never assumes a transaction across
SE and MCU storage. Invalid state is recovery-required. Fault injection that
creates a valid unauthorized Q, restores counts or retains AUTO violates a
required assumption and fails the candidate.

A snapshot containing only old H cannot satisfy new Q. New H before Q commit
cannot force activation. Corrupt/missing Q is never reconstructed from MCU
metadata. Replacing the SE, losing PBS, losing slots, lifetime exhaustion or
unprovable counter state requires local recovery on a fresh admitted target.
Do not reset C on power cycle or failure. At ten failed credential queries,
the next query releases no A; a correct PIN entered afterward cannot bypass it.
No remote PIN reset, security questions, vendor credential or firmware reflash
recovers device-held identity.

**Authenticated retirement** requires independent recovery availability and
separate local destructive consent: authenticate, overwrite Q with the tombstone,
read it back, clear sessions/MCU plaintext, and erase both MCU slots. The
proposed termination order is Q(F1D1), A(F1D2), Kp(F1D0), C(E120), L(E121),
host-freshness(F1D3), then PBS(E140), using SetDataObject metadata with C0=0x0f, checking each
acknowledgement and available metadata readback before advancing. Remove MCU
PBS only after the last chip step; losing the protected channel is not an
authenticated acknowledgement of that step. Every uncertain step stops in
retirement-uncertain. This exact order still needs H02S permission/reset proof.
A chip termination flag is not proof of physical erasure. Completion requires
positive readback before channel loss plus target reset tests. Failure is
retirement-uncertain, never a success banner.

**Lost PIN/exhaustion:** this revision provides no authenticated Q overwrite and
no whole-chip factory reset. Local MCU erase/SE termination may retire use, but
secret remnants can persist and the chip cannot be represented as wiped or
reusable. Quarantine/replace it; restore nsec elsewhere. Do not introduce a
counter reset backdoor to improve availability. Manufacturer certificates,
immutable roots and one-way state survive any application-data operation.

## Recovery and optional compatibility

Native restore accepts only locally supplied canonical NIP19 nsec with exactly
32 bytes representing 1 <= D < n. Retain those original bytes before constructing
a signing key. Derive P with a separately reviewed secp256k1 implementation and
compare the **full32 bytes** with an independently retained expected P; confirm
that value locally. A fingerprint, host descriptor, own freshly computed
expected field or equal d/n-d public key is not enough to establish original
recovery encoding. Recovering with a new PIN/E/R/SE creates the same identity;
device/transport bindings and pending authorizations are new.

The unintegrated S03 input normalizes its signing scalar and drops the original
input. Reconcile that interface before consuming it; this specification does not
claim S03 already stores D. Raw ECDH x is invariant under point negation, so this
observation does not itself establish a NIP44 defect.

NIP06 compatibility is **preserved as deferred optional migration**, consistent
with P01. Its historical path m/44'/1237'/account'/0/0 and published fixtures
remain in the pinned NIP06 source and independent acceptance plan. This revision
does not accept BIP39/SeedQR input, store a seed/passphrase/path, or create new
mnemonic identities. Any later migration must separately bind language,
normalization, passphrase, account/path and expected P, then deliberately select
what recovery data is retained/exported. It may not silently make that route
the native default. NIP49 export remains deferred.

## Firmware ownership and deployment lifecycle

Developer state allows test firmware/debug and contains **no production secret
claim**. Transition to owner-secured state requires H02's exact boot root,
rollback/debug/recovery plan and erasure of developer material, plus H02S's
exact SE provisioning/readback and reset proof. Product-qualified additionally
requires V02 integrated host evidence and V03 actual custom-assembly repetition,
local recovery ergonomics, entropy and independent review. A simulator state
label or this document cannot perform those transitions.

An MCU update signed by the same accepted owner must lock/cancel everything,
verify the entire image/manifest and monotonic policy, then reconcile the same
custody schema before use. Incompatible schema has no automatic migration in
TM-HMAC-1. Interrupted update boots only a fully verified allowed image or a
recovery mode with no secret release. Whether STM32 roots/rollback storage can
enforce this, and how debug/recovery regressions erase state, remains **H02**.

MCU owner-root replacement or transfer must retire old custody and provision a
fresh supported SE/object set before the new owner can enroll. There is no
permission to carry over PBS/vault solely because the new firmware can read
flash. Lost owner signing credentials do not grant an unsigned recovery path;
H02 must name an actually supported destructive recovery route or declare the
device unusable. Firmware-owner private keys are never derived from nsec/PIN.

Trust M's object ProtectedUpdate service changes data/key/metadata objects; the
reviewed material does **not** establish user-controlled SE firmware replacement
or an offline field-firmware recovery entitlement for the exact standard OPN.
That remains a candidate gate. NXP/TROPIC's separately documented vendor
authorities are compared in se-decision.md. Owning an MCU root never transfers
those vendor rights. No credentials, production fuses or hardware were created.

## Review and evidence required before a consumer

The executable format example and finite-state review traces in
[specification-checks.json](specification-checks.json) are author evidence only.
They do not exercise a device, replace independent cryptographic analysis or
satisfy all seven parent criteria. The final candidate needs a **distinct**
reviewer to check the exact source, KDF/nonce/byte layouts, all alternate command
paths, active/pending state, downgrade/retirement attacks and secret-copy claims.

The reviewer must supply an independently produced scalar/public-key/nsec oracle,
published HKDF/AEAD vectors, mutated-encoding tests and adversarial state traces;
sharing this author's expected outputs is not independence. H02S later cuts
power before/during/after every persistent command, including response loss,
all counter boundaries, MCU-only resets and channel replay. H02 separately
proves MCU roots/erasure/rollback. V02/V03 prove their composition on actual
identified assemblies. Resource/operator availability is UNKNOWN.

No implementation handoff occurs while a blocker in se-decision.md is open,
while exact cryptographic review is missing, or before A02/S03 source
reconciliation. The coordinator alone updates the sole task ledger. S04 remains
incomplete.
