# S04 SE contribution and ownership decision

**No SE is selected or admitted. S04 remains incomplete.** The [TM-HMAC-1
construction](custody-protocol.md) is a concrete review experiment, not the
generic Board architecture. Its terminal object set fails the practically reusable Board requirement.
Its separately chosen combined-use ceiling allows roughly1024 ordinary unlocks
before setup/change/fault costs; that is a limit of this experiment, not an
inherent Trust M hardware lifetime. Accessibility of its manual is a research advantage, not a
selection criterion. This decision retains all seven parent acceptance criteria.

Read the exact-source [register](research-source-register.json) for hashes,
versions, Git object bindings, read scope and failed retrievals. Sources were
checked on 2026-10-18; a fetched PDF is not a completed manual audit. H01 remains
unaccepted contextual input at 6f95cc29; no moving H01 candidate was silently
adopted. The newer STM32 reading belongs to H01/H02 and has not supplied a
qualified MCU root or hardware sample here.

## Comparison against the actual custody job

| Lead / exact scope investigated | Documented usable operation, actual output and contribution | Missing or contrary evidence |
| --- | --- | --- |
| Standard OPTIGA Trust M V3; IFX-RM3.70, release3.02.2564, cryptolib2.09.002, API03a3ebe8 | HMAC-SHA256 from PRESSEC object returns32 bytes to MCU; AUTOREF HMAC verification establishes retained RAM authorization; linked UPCTR advances on EXE; protected data read returns plaintext to MCU. These can compose a persistent-query and release policy if all real command paths enforce it. | Exact presently orderable OPN/firmware/configuration equivalence, self-authorized AUTOREF replacement, alternate-command counter coverage, reset retention, physical faults and safe reusable lifecycle remain unproved. No native secp256k1/BIP340 in the reviewed algorithm table. |
| SE051C2; public AN12973Rev2.0: OEF A8FA/applet7.2/date>=2201 versus A564/6.0 older tuple | Public configuration guide establishes SCP and recovery credential families and applet/object distinction. AN12907 documents secure-object-preserving vendor applet update. No command-level custody contribution is credited without the restricted semantics. | Required AN12543Rev4.5 and SE051 errataRev1.1 not obtained. A raw URL404 is an access failure, not proof of absence. No fabricated APDU/policy/atomic-delete contract; no admission from ECDSA/curve branding or public middleware declarations. |
| TROPIC01; API1.4.0, PIN note1.2, config1.3, pairing1.3, update1.5; advisory lists T310 Boot2.0.1/App2.0.0/SPECT1.0.0 | MAC_And_Destroy command0x90, slot0..127, input32/output32; hardware slot replacement can give a destructive-query primitive under its internal-key confidentiality assumption. Vendor PIN scheme stores n ciphertexts plus tag/index on MCU and restores consumed slots after correct PIN. | Current advisory defeats the physical premise for listed devices; maintenance restriction is not a remedy. No native BIP340: API key curves P256(0x01), Ed25519(0x02); X25519 channel handshake is not secp256k1 ECDH. Four finite write-once pairing slots limit transfer. |
| MCU-only control | Same local review, original-scalar/nsec handling and software signature policy can keep identity out of an ordinary host client. An authenticated password vault can detect corruption. | MCU flash snapshots expose an offline PIN oracle absent a separately proven hardware secret/service. Software attempt counts roll back. Boot roots/debug/read protection must be proved on exact MCU; none are inherited from the presence of Rust or an SE. |

No lead establishes chip-native Nostr operations from its ECDSA support.
TM-HMAC-1 does not ask a chip to sign a BIP340 message or derive NIP44 shared-x.
The eventual connected profile still needs software NIP44 integration and its
separate authorization/tests. A second chip is not added to repair an unexplained
single-chip gap: common MCU authority, RAM, PIN entry and firmware roots would
remain shared.

The separately traced [Safe7 reference](safe7-reference.md) supplies a concrete
cyclic destructive-reset alternative. Its wallet reset retains factory authority;
it is evidence for a bounded follow-up, not an accepted reusable-Board solution.

## Trust M command and permission analysis

[IFX-RM](https://github.com/Infineon/optiga-trust-m-overview/blob/a45b86bda014efeebfb85f084f779cedb07b32dc/docs/pdf/OPTIGA_Trust_M_Solution_Reference_Manual_v3.70.pdf)
pp54–60 and80–91 distinguish data read, data change, execute and metadata update.
This matters more than the label “secure element”:

- EncryptSym0x14/0x94 HMAC mode accepts PRESSEC/session objects and returns a
  MAC. DecryptSym0x15/0x95 HMAC verification accepts AUTOREF; verification uses
  a fresh session challenge and leaves AUTO in RAM on success. A caller must
  clear it explicitly. A release record protected by AUTO is readable by any
  caller holding that authorization; there is no chip-local display approval.
- Linked-counter Luc increments on EXE and permits the action only before its
  threshold is reached. SetDataObject counter CHA can rewrite **both** count
  and threshold. A public reset capability therefore is not a retry limiter.
  The security-event monitor is a rate/delay mechanism, can be configured with
  zero delay, and is not the persistent PIN budget.
- The HMAC API's default is command protection, not full response protection.
  The proposed credential output must be shielded too. Its transcript/copy
  exposure is explicitly inside the MCU compromise boundary.
- V1 lacks a host random contribution; RM §6.6.3 requires an additional
  freshness check. The proposed F1D3 write/read nonce flow follows §6.6.3.1.
  Full-protection settings reset after each API invocation. Application
  hibernate may persist achieved authorization across power loss; clean
  OpenApplication(0x00) invalidates saved application context. These are
  mandatory guards, not properties supplied by encrypted I2C alone.
- PRESSEC read/change asymmetry has a specific restriction in §6.5.6: a mutable
  secret requiring tighter READ than CHANGE needs integrity-and-confidentiality
  protected update. TM-HMAC-1 avoids field mutation of Kp entirely. It does not
  generalize that exception to arbitrary secret formats or assert that its
  self-authorized AUTOREF path is proven.
- E140's structural table specifies64-byte binding secret; §6.5.8 recommends at
  least32. The proposed exact record follows the64-byte structural format.
  No default/fleet secret is acceptable. Host binding does not survive an
  attacker extracting the MCU-held copy as an authentication boundary.
- Metadata is at most44 bytes. Ordinary lifecycle progresses1→3→7→15.
  Omitted tags are retained; absence and an explicit NEV are not interchangeable
  when updating an existing factory object. C0 operational plus D8=NEV is the
  proposed hardening, subject to actual standard-part readback and negative tests.

The open source API and examples are
[pinned at03a3ebe8](https://github.com/Infineon/optiga-trust-m/tree/03a3ebe8e87216cb60b8572eafa1e46c13fb87fb).
Their top-level MIT license is available; no code has been imported, and no claim
is made about every dependency's license. A different customized wallet chip,
Express/MTR provisioning service or factory credential is a different tuple.

The [current official OPN note](https://community.infineon.com/t5/Knowledge-Base-Articles/OPTIGA-Trust-M-Latest-OPN-status-and-active-variants/ta-p/1195051)
lists older A2 variants as NRND; the current product page lists MK…TMB2 and
ML…TMC1. No actual sample proves either has the inspected build/policies.
Release3.02's improved asymmetric SCA library is a fact about that release,
not a complete assurance argument. [EUCLEAK's primary report](https://ninjalab.io/wp-content/uploads/2024/10/20241022_eucleak.pdf)
observed Trust M ECDSA inversion leakage and inferred vulnerability; it did not
complete key extraction on that Trust M target. It does not establish HMAC
extraction or a blanket exemption for this proposal. Direct original retrieval
failed; the web-readable sections and limitation are recorded. Exact physical
applicability and current advisory closure remain H02S gates.

### Protected update and destructive-reset alternatives

SetObjectProtected0x03/0x83 accepts a signed CBOR manifest, optional
confidentiality protection and a target object. A metadata update requires its
current D8 integrity trust anchor and applies the **current target object's F0
reset before new metadata**; without F0 it fails. F0 can flush that object with
zero or random data, clear its used length, and select lifecycle state. These
are useful, real features. They do not assert atomic reset of Q, A, Kp, counters,
PBS and all MCU copies together. Certificate objects also have a documented
non-atomic write caveat; they cannot be assumed to be an atomic root journal.

| Proposed reuse route | Concrete security problem or missing proof | Decision |
| --- | --- | --- |
| Keep mutable counters/AUTO with a publicly available reset/update signer | Attacker resets C or replaces A while Q/Kp survive. A reusable counter reset can enable guesses against the old vault. | Reject as a backdoor/rollback bypass. |
| Keep an off-device owner reset signer | Its holder can independently target C/A unless an exact chip-enforced object dependency prevents it. “The tool first erases Q” is only trusted-tool order. MCU owner signing authority and SE custody-reset authority are different privileges. | Not adopted; needs an explicit product authority decision and proof of surviving-object attacks. |
| Put reset signer only inside the PIN-protected vault | Correct PIN can maintain objects, but lost PIN/exhaustion cannot release the signer. This does not provide the required lost-PIN reset/re-enrollment route. | Insufficient as reusable-platform answer. |
| Signed F0 reset of each object in sequence | Power loss leaves mixed generations. A signed update for only C/A may remain valid independently of Q erasure. Version15-bit anti-replay is per target, not a global transaction or proof that another object was destroyed. | No safe protocol yet; require an enforced prerequisite and revocation proof. |
| Safe7 cyclic AUTO dependency: overwrite PIN_SECRET before reset/replacing verifier chain | Real pinned source construction destroys an old derivation factor before granting reset authority; retained AUTO, old factors, alternate commands, interruption, factory pairing and RM guidance applicability still need proof. | Prioritized same-lead follow-up; no impossibility claim or adoption. |
| Permanently deny mutation/metadata update as TM-HMAC-1 does | Locked-state argument is simpler but Kp/PBS/lifetime budget and terminated object set are not renewable. | Bounded experiment only; fails reusable-Board architecture acceptance. |
| Trust MCU erasure or owner software to implement all reset order | Privileged MCU compromise can skip steps. Physical flash/SE remnants and rollback still need actual proof. | Can describe ordinary firmware behavior, not SE-enforced erasure or hostile-MCU secrecy. |

The specific next documentary question is whether the source-backed cyclic AUTO
dependency, or an exact standard-part protected-update policy, can make **irreversible old-vault-factor destruction a
chip-enforced prerequisite** of every path that replenishes C/L or replaces A,
and revoke the old update/binding authority without relying on its cooperation.
A counterexample to any alternate permitted command is failure. The Safe7 source establishes a concrete construction to evaluate, but its
full safety and independent-owner lifecycle have not been proved here; do not
infer impossibility of every Trust M design from the failure of this one.

Budget accounting is explicit: Kp/A/Q/freshness consume4 of12 140-byte data objects;
C/L consume2 of4 counters; PBS uses E140; the128-byte Q fits140 bytes.
The proposed lifetime threshold2049 permits at most2048 combined Kp/A uses,
roughly1024 normal unlocks **before** enrollment checks/PIN changes and faults.
Wrong-guess HMAC plus failed AUTO normally costs2 lifetime uses and1 attempt.
Every A update does not magically renew L. Generationu64 never wraps.
The real counter is count:u32 plus threshold:u32 (8 bytes); the threshold
field can represent values through0xffffffff, and CHA writes both fields as
data. The manual recommendation of2048 uses per shared secret is not a fixed
maximum encoded by the hardware. Our combined Kp/A cap is an intentionally
conservative policy choice. A larger justified policy would require independent
security/lifetime review, while safe reset and authority revocation still remain
unresolved. The manual's600000 per-counter/2million aggregate object-update
endurance numbers are separate reliability ratings, not2048-use policy values
or evidence of an actual measured system lifetime. Denied/hostile commands may also cause
monitor writes; no bounded wear guarantee is made against command flooding.
The protocol currently has zero safe
post-retirement re-enrollments.

## NXP authority/access and reset investigation

[AN12973](https://www.nxp.com/docs/en/application-note/AN12973.pdf) §2.3 explicitly
identifies platform SCP key set11 and recovery key set12. Generic recovery
ownership is initially NXP's; production must replace key set12 with
customer-owned values. UUID, platform/recovery SCP and EC session/import object
families are not simply customer-erasable. Default values are published; they
are not security credentials for a deployed Board. Merely changing ordinary
application objects does not establish that the previous recovery authority is
gone. Exact replacement privilege, interruption behavior and reset reachability
need the missing API/errata and a named configuration.

[AN12907](https://www.nxp.com/docs/en/application-note/AN12907.pdf) §§1–4.3 separates
A/C preinstalled IoT applets from P-variant custom development. NXP controls IoT
applet update scripts, distributed via EdgeLock2GO to an entitled OEM account.
Updates preserve secure objects and SCP keys. Normal version rejection is
insufficient for all older-script cases; a separate SEMS key-rotation script
invalidates previously signed scripts where applicable. MCU owner roots do not
authorize these scripts or delete vendor authority.

Offline execution of an already acquired valid script is a reasonable inference
from local distribution, **not** proof of offline acquisition, perpetual service,
custom-signing rights or recovery entitlement. Account/terms/service/license
access has not been established or requested. The required command document,
errata and exact policy/reset semantics remain missing. This blocks a concrete
SE051 custody protocol; the other comparisons continue. Do not substitute an
imagined DeleteAll/FactoryReset API or assume that deleting an applet erases all
credentials and reopens safe initialization.

## TROPIC advisory, maintenance and finite ownership

The [advisory](https://github.com/tropicsquare/tropic01/blob/90747cac7c0261408c0ca767d272894f481f2cf2/doc/security_advisories/ODR_TR01_SA_2026012900_1v0.pdf)
and [vendor follow-up](https://www.tropicsquare.com/blogs/potential-bypass-of-firmware-verification-by-laser-fault-injection)
include the T310 production tuple and potential access to MAC-and-Destroy
internal keys/slots and other secrets. Disabling maintenance narrows attack
access; it does not eliminate the disclosed physical attack. A projected future
silicon fix is not qualified remediation. Therefore the PIN note's proof
assumption cannot be credited against that attacker on the listed parts.

The PIN note specifies n <= 128 MCU ciphertexts of 32 bytes each plus tag/index, one hardware
MAC-and-Destroy slot per allowed try, and restoration of consumed slots after
successful PIN. Its hardware primitive replaces persistent slot state before
returning32 bytes. This is substantially different from “store opaque seed
under a non-exportable key”; it still releases an unlocking factor to MCU.
No nSealr parameters or alternate crypto are chosen for this rejected route.
Full-state extraction in TM-HMAC-1 is also explicitly fatal: Q contains A_target
and R, so a captured vault can be opened without guessing the PIN. An SE
non-export flag does not convert this into independent PIN-factor protection.

Pairing note1.3 establishes four write-once public X25519 slots. Default slot0's
private key is public; replacing it consumes another slot, then invalidation
permanently disables slot0. At most3 initially blank slots remain, and once a
slot is written/invalidated it cannot be reclaimed by resetting R-memory.
An invalidated former-owner slot is not a reusable fresh slot. Arbitrary
ownership churn therefore cannot be promised. Exact custom factory pairing or
vendor-root configuration requires a different part and arrangement; none was
requested.

Config note1.3 defines effective policy as I-config AND R-config; I-config is
one-way1→0, R-config may change subject to UAP, and changes take effect after
restart. Irreversibly disabling maintenance also removes that firmware-update
route. Reversibly disabling it retains an authority that can reopen it; both
the surviving authority and attacker access must be stated.

Update note1.5 applies to Boot>=2.0.1/ACAB; older bootloaders differ and may allow
downgrade. ROM holds Tropic's immutable boot root. The vendor public key in
I-memory is signed by that root; its private counterpart authorizes CPU/SPECT
firmware. Standard parts use Tropic's vendor key. Customer-signed firmware
requires a specially manufactured vendor-key configuration, not ordinary MCU
ownership transfer. Two firmware banks per engine use signature/hash-chain
verification and version comparison with the protected bank. Update interruption
and disabling maintenance before both banks are valid can affect recoverability;
the advisory prevents accepting this logic as a physical bypass defense.

The pinned current part index recommends T301 and does not supply the guessed
T310 page; the advisory/catalog still name T310. Do not merge those identities.
T005's page links a September10 RNGTEST_DIS erratum; the external page retrieved
only a JavaScript shell and the web tool could not expose its body. Preserve
that access failure and resolve exact affected parts before use. It neither
supersedes the June advisory nor proves the production parts unaffected.
Libtropic's pinned license is Clear BSD with no patent grant; this is not
evidence of custom manufacturing, field-root replacement or support rights.

## Blocking decisions and next bounded work

| Gate | Exact unresolved result / owner |
| --- | --- |
| G01 | Distinct exact crypto/spec review of TM-HMAC-1; S04 reviewer. No implementation authorization from this author. |
| G02 | Safe same-hardware erase/re-enrollment and practical lifecycle, or a deliberate separately bounded profile decision; S04 + product coordinator. Terminal replacement cannot satisfy generic Board by default. |
| G03 | Trust M orderable OPN/build/config equivalence and actual default metadata; H01/H02S. |
| G04 | Self-authorized AUTOREF change, linked counter boundaries/all command paths, retained AUTO and full shielded response protection; S04 documentary review then H02S physical evidence. |
| G05 | Safe protected-update/reset authority composition, no surviving factor/counter-reset bypass, interrupted reset/root rotation and lost-owner-key behavior; S04, then H02S. |
| G06 | Trust M firmware-update/recovery rights and lifetime service reality for exact OPN; S04/H01. No claim from object ProtectedUpdate. |
| G07 | NXP lawful command/errata/middleware/license access, recovery-key replacement and exact reset semantics; S04/H01. Required material unavailable; no outreach authorized. |
| G08 | TROPIC exact part mapping, current advisories/errata and independently qualified remedy; H01/H02S. No available remedy established. |
| G09 | Actual MCU root-manifest encoding, boot/update/debug/rollback and erasure/re-enrollment feasibility; H02. No provisional roots accepted. |
| G10 | Target entropy, time/memory/endurance, original-scalar integration, recovery UI and flash/SE cutpoints; B02/K01/D02/V02; repeat complete result V03. |
| G11 | Full primary-original advisory pinning and actual IFX-I2C driver reset/context/re-handshake/retry audit; S04 documentary continuation and H02S. A tool-readable excerpt is not a whole-source audit. |
| G12 | A02/S03 source reconciliation, independent review and coordinator integration; root. Sole task ledger remains unchanged. |

The narrow next comparison stays inside the same three leads: (1) the actual
Safe7 cyclic destructive-reset/host-held-factor construction, reduced to a
single-SE permission graph where possible, plus exact protected-update paths; (2) SE051's actual
credential-deletion/reset and recovery-authority semantics if lawful existing
access becomes available; (3) whether a currently documented TROPIC configuration
can satisfy finite pairing/maintenance/re-enrollment **and** has a qualified
advisory remedy. No fourth-chip search, purchase, account enrollment or
manufacturer contact is implied. If all three fail, present those exact failures
and request a separately reviewed comparison extension; do not weaken the
product requirement or attach a success label to this experiment.
