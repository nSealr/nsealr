# Pinned Safe7 custody reference — construction evidence, not inherited assurance

The pinned Trezor firmware contains a concrete destructive-reset dependency that
is absent from TM-HMAC-1. It is therefore **not established that Trust M cannot
support reusable custody**. The finite, nonrenewable result in the current
[experiment](custody-protocol.md) applies to its chosen object policies. This
reference does not change those policies or adopt dual-SE custody for nSealr.

The source is commit `5fdc180b99bd763c3d18411bba686909875eb337`, root tree
`07fa1a89dd1b8bc25f96166d9115e527bc25fd36`. It is the H01-pinned firmware reference,
read directly here; no moving H01 author branch was adopted. Every inspected file
has a blob, mode, SHA256 and read scope in the [register](research-source-register.json).
T3W1's model selects STM32U5G, default revC, and Optiga/Tropic board features;
the corresponding build modules define USE_OPTIGA/USE_TROPIC and select real
STM32 sources rather than emulator implementations. This is a source profile,
not proof of the firmware, revision or provisioning on any physical Safe7.

Primary entry points: [model](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/models/T3W1/model.toml),
[board](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/models/T3W1/boards/revC.toml),
[storage constants](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/storage/storage.h#L62),
[Optiga build](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/sec/optiga/build.rs), and
[Tropic build](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/sec/tropic/build.rs).
The older [Optiga explanation](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/docs/core/misc/optiga.md) explicitly describes
Safe3/Safe5. Its single verifier, sixteen-attempt and two-iteration figures must
not replace the actual Safe7 branch traced below.

## Actual PIN and object composition

`storage.h` sets ten attempts when Tropic is present and ten stretched-PIN
objects. `storage.c`'s multi-verifier branch sets PIN_ITER_COUNT=1, not20000;
this work does not import that parameter or assert a host-password-hardening
work factor. The MCU path combines hardware/storage/optional external salts and
has a USE_STORAGE_HWKEY branch through privileged or unprivileged hardware AES.
The hardware-key availability and root enforcement are separate physical claims.

The caller sequence is MCU stretch → Optiga CMAC/P256-ECDH stretch → Tropic
per-attempt MAC-and-Destroy stretch → Optiga HMAC/authorization chain → Tropic
KEK-mask recovery → MCU storage decryption. It is not Nostr signing in either
chip. Each step yields material usable by the MCU; the chips do not understand
local transaction consent or a Nostr public key.

[Storage callers](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/storage/storage.c#L628),
[Optiga operations](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/sec/optiga/optiga.c#L532), and
[Tropic operations](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/sec/tropic/tropic.c#L1710) establish that flow.

| Optiga object in this source | Actual configured use and dependency |
| --- | --- |
| F1D0 PIN_SECRET, AUTOhttps://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/ | READ requires last verifier; CHANGE always; EXE always. A random replacement destroys this old secret before new authorization can reset the verifier counter or replace the last verifier. |
| Verifiers F1D4,F1D1,F1D2,F1D3,F1D5,F1D6,F1D7,F1D9,F1DA,F1DB | Ten AUTOhttps://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/ objects. First READ never, CHANGE requires second verifier. Intermediate READ requires previous and CHANGE requires next. Last READ requires previous, CHANGE requires PIN_SECRET. Every verifier EXE links E120. |
| F1D8 PIN_HMAC, PRESSEC | READ never; CHANGE requires first verifier; EXE links E122. HMAC output goes to MCU. |
| E120 verifier counter | CHANGE requires PIN_SECRET. Set-counter writes count0 and chosen threshold as an8-byte object. Setup temporarily supplies ten verifiers plus ten attempts; verification resets to10 or11 depending on additional reset authorization. |
| E122 HMAC counter | CHANGE requires first verifier; configured limit10. This independently bounds HMAC candidate queries even though a successful verifier walk consumes several E120 uses. |
| E121 total counter | Initialized to600000 while mutable, then CHANGE never. Links the CMAC and ECDH operations, and survives ordinary wallet reset. |
| E200 PIN_CMAC and E0F3 PIN_ECDH | AES256/P256 generated keys with CHANGE always, READ never and EXE linked to E121. Regenerating them invalidates old derivation, but does not renew the locked total counter. |

These are the actual [metadata and initialization paths](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/sec/optiga/optiga.c#L390).
They are not a claim that the same metadata is accepted by an arbitrary standard
Trust M OPN. In particular, `optiga_pin_set` writes mutable PRESSEC F1D8 through
SetDataObject under AUTO; RM3.70§6.5.6 requires protected update where READ is
stricter than CHANGE. Exact variant/guidance applicability and that apparent
source-to-manual tension must be resolved, rather than treating wallet source as
permission to bypass the manual.

The host repeatedly applies a one-way HMAC before sending a verifier/chip input,
and applies the returned chip material to a host-held stretched secret. This is
a concrete difference from TM-HMAC-1's extracted A_target/R directly revealing
the vault key. It merits an independent composition proof; this document does
not claim that extracting one or both chips, the MCU, or a retained transcript
leaves the required host entropy unavailable.

## What destructive reset does, and what remains to prove

`optiga_pin_set` regenerates the stretching inputs, writes a fresh PIN_SECRET,
authorizes it, then walks **last verifier to first**, writing and authorizing the
new verifier chain. It finally replaces PIN_HMAC and resets its counter. The
first verifier's reset credential and Tropic's reset secret are stored inside
encrypted storage, not as a free plaintext counter-reset file.

In the other direction, [verification](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/sec/optiga/optiga.c#L1014)
authorizes the selected attempt's verifier, reads/authorizes following
verifiers, and only then reads PIN_SECRET. It incorporates PIN_SECRET into the
host result, authorizes it and resets E120. First-attempt success can reset
E122 immediately; later success requires the first-verifier reset credential
recovered after storage decryption.

The important structural inference is that a locked attacker who overwrites
PIN_SECRET to gain counter-reset authority also loses the previous secret needed
for the old derivation. Unlike a freely signed counter reset, the dependency is
in object access conditions. This is **not a complete proof**: cached AUTO,
previously disclosed secrets, verifier-chain reads, preserved SE/MCU state,
partial writes and every alternative permitted command must be considered.
An attacker who already obtained the old PIN_SECRET or live authority is not
forced to forget it by an overwrite. The ordinary locked-attacker assumption
must say that explicitly.

[Storage unlock](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/storage/storage.c#L1160) increments and checks persistent MCU
attempt state before checking the PIN. On successful decryption it restores
Optiga/Tropic reset state before resetting the MCU log. On exhaustion it calls
wallet wipe. `storage_change_pin` requires an unlocked store;
`set_pin` mutates SE state before committing the new encrypted key record through
norcow. This reading does **not** prove cross-chip/norcow atomicity or lossless
PIN-change recovery. A fault after SE replacement can leave old ciphertext with
new derivation state; the complete allowed failure/recovery outcome needs a
separate proof and physical tests.

`storage_wipe` erases norcow/cached keys and initializes new storage with an
empty PIN. It re-enters the PIN setup paths. It is wallet-data reset, not a
factory pairing/root reset. T3W1's secret layout separately describes a BHK page
refreshed on wallet wipe; the inspected `secret_bhk_regenerate` erases and rewrites
that page. This bounded reading does not claim every caller or all MCU remnants
have been independently audited.

The reference also requires a separate channel audit. `optiga_init_and_configure`
at this pin attempts the shielded handshake, but on failure soft-resets and opens
the application; its comment limits the expected loss to attestation services.
Its PIN metadata is not uniformly Conf(PBS)-bound. `optiga_clear_all_auto_states`
clears only locally tracked successful authorizations and returns on error;
several PIN callers discard that return. The inspected handshake obtains random
material from the chip, not a fresh host nonce. These facts are not a complete
attack finding against Safe7, but they do prevent treating its call sequence as
the independent freshness/clear proof required by TM-HMAC-1. Full transcript
replay, lost-clear response and partial-reset oracles remain mandatory.

## Tropic slots, counters, retries and maintenance

The source splits128 MAC-and-Destroy slots into64 privileged and64 unprivileged
slots. For attempt i and normalized PIN-change count c, its slot is
`role_base + ((11*c+i) mod64)`, with role_base0 or64 and i0..9. Ten attempts
consume ten distinct slots for one PIN generation. Shift11 is coprime to64,
so the start position repeats after64 increments, not after a hardware-enforced
nonrenewable lifetime. Counter slot4 stores a decrementing value relative to
0xfffffffe; invalid/depleted state is reinitialized to0xfffffffd. It is not a
permanent antirollback root.

Setup generates a32-byte MAC-and-Destroy reset key, writes it to a slot, probes
the correct digest, then restores the slot with the reset key. Unlock consumes
the chosen slot. Successful storage decryption releases the reset key and
restores consumed slots0 through the successful attempt index. A random KEK is
masked with each final stretched PIN; the resulting ten32-byte masks occupy
R-memory slot128 or256 (role-specific). This actual Safe7 composition differs
from the vendor PIN note's generic n-ciphertext-on-MCU construction.

[Slot mapping and reset](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/sec/tropic/tropic.c#L1580) and
[role constants](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/sec/tropic/inc/sec/tropic.h#L55) are the authority
for these figures. None is an endurance measurement. Optiga's E121 policy is
600000 CMAC/ECDH operations; Safe7 chooses one paired stretch iteration, so the
source's nominal ceiling is300000 normal unlocks before setup/failed attempts
and other work. That is separate from the manufacturer's recommended2048 uses
per shared secret and from write-endurance ratings. The code does not establish
that a fixed key may safely ignore that recommendation; no such bound is adopted
by nSealr.

The [retry macro](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/sec/tropic/tropic.c#L180) allows up to ten calls
for selected transport/CRC/alarm errors and may restart the chip/session. The
MAC-and-Destroy caller expressly anticipates that retry after execution can make
PIN verification fail. That is a meaningful availability/fault outcome, not an
atomic-success guarantee or evidence for refunding an attempt. By comparison,
TM-HMAC-1 forbids automatic retry after unknown dispatch.

Safe7's pinned build uses libtropic gitlink
`0aa7e8873f08b0727138b7887b942268afca468a`, default ACAB/boot2.0.1 and the
`fw_v_2_1_0` directory. Its tree contains a CPU2.1.0-named image and
SPECT1.3.0-named image; these are path/build facts, not runtime readback or
qualification. They differ from the advisory's listed App2.0.0/SPECT1.0.0 tuple.
No statement that the pinned Safe7 build is vulnerable or fixed follows from
those names. Exact revision, advisory applicability and qualified remediation
remain open; an updated application alone does not prove a silicon attack fixed.

The [maintenance code](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/sec/tropic/tropic.c#L1130) temporarily
reenables the reversible maintenance bit after storage unlock, flashes bundled
firmware with bounded retries, restores configuration and records version in
R-memory. Boot recovery finishes an already pending update without deliberately
opening maintenance. The irreversible bit must still permit that operation;
an irreversible disable makes the update unavailable. The MCU-side unlock check
is ordinary firmware policy. It cannot establish that a hostile MCU holding the
privileged pairing key cannot enable maintenance, nor does it remove the vendor
firmware signing root or the advisory's residual physical attack.

## Factory authority versus a transferable Board

[Optiga provisioning](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/projects/prodtest/cmd/prodtest_optiga.c#L115)
loads the MCU-derived PBS, pairs, and locks PBS CHANGE/READ never. Production
locking also fixes device/FIDO certificates and private-key policies. The MCU
root that decides which firmware receives those secrets is not an end-user
replaceable custody policy merely because wallet data can be wiped.

[Tropic provisioning](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/projects/prodtest/cmd/prodtest_tropic.c#L449)
consumes slot1 for unofficial/HSM-related access and slot2 for official firmware,
invalidates factory slot0 and verifies slot3 is empty. Its own comments describe
pair/lock as irreversible. Lock writes and verifies both reversible and
irreversible config. These code checks are not physical power-loss evidence.
One initially empty slot after provisioning does not permit arbitrary new-owner
pairing rotations. Neither wallet wipe nor R-memory erase restores consumed
pairing slots.

The factory tool's `tropic-erase-all-slots` loops32 ECC slots,512 R-memory slots
and128 MAC-and-Destroy slots. It explicitly preserves pairing keys and does not
reset I-config, vendor roots, counters or MCU master secrets. Its aggregate
success string must not be interpreted as return to an unprovisioned chip. On a
locked part the actual ACLs can also prevent a requested erase.

The [MCU secret-key functions](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/sec/secret_keys/stm32u5/secret_keys.c)
derive Optiga PBS and privileged Tropic pairing from a privileged master slot;
unofficial Tropic pairing comes from the unprivileged master slot.
[secret_prepare_fw](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/core/embed/sec/secret/stm32u5/secret.c#L598) selects full
versus public cached secrets based on firmware trust/provisioning state.
This vendor-defined official/unofficial distinction is **not** nSealr's desired
owner-controlled firmware lifecycle or isolation between arbitrary applications.
Transferring nSealr requires proving destruction/revocation of all prior owner
factors and authority on the same board while documenting immutable manufacturer
objects. Reusing a vendor-owned factory pairing across wallet wipes does not
answer that requirement. No complete MCU boot-root audit is claimed here.

The repository [license map](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/LICENSE.md) identifies core/storage as GPLv3;
file headers allow v3 or later. Analysis and citations are committed here,
not Trezor implementation code or firmware images. Any later code reuse needs
its own dependency/license decision; the libtropic gitlink is a different input
from the separately inspected upstream9085ea53 API. No license compatibility or
security guarantee is inherited from either repository.

## Bounded follow-up and independent oracles

Within the same Trust M lead, first evaluate a single-SE cyclic destructive-reset
construction with a host-held one-way derivation factor. Do not port the Safe7
chain, assume its two chips are independent, change the current experiment or
raise its2048 policy cap without an exact revised protocol and distinct review.
The required result is a complete permission graph and the following independently
derived counterexamples/invariants:

- An attempt to replenish any counter or replace any verifier while retaining
  every old vault factor must fail. Enumerate direct data writes, metadata and
  protected-update routes, challenge/AUTO reuse, intermediate-verifier reads,
  old signed updates and surviving pairing/reset authority.
- Cut power before dispatch, after each object commit and after lost response
  during every chain step. Replay old MCU slots, whole bus transcripts and stale
  authorization across MCU-only reset, SE-only reset, hibernate and joint reset.
  No trace may grant old-vault access with renewed guesses; an explicit
  recovery-required/data-loss outcome is preferable to unsafe fallback.
- Test the ten-attempt versus multi-verifier counter accounting against an
  independent command oracle, including denied calls, later-attempt success,
  duplicate destructive calls and every partial-reset combination.
- Separate wallet reset from lost-PIN same-board owner transfer. The new owner
  must establish fresh authority while old retained PBS/pairing/update credentials
  cannot recover old factors, reset the new budget or impersonate the new root.
  Enumerate immutable manufacturer material and finite slot/endurance limits.
- Prove what remains secret under flash-only, locked hostile-MCU, one-chip
  extraction, two-chip extraction and previously unlocked-MCU attackers. A
  host-held factor in a drawing is not a proof of entropy or inaccessible state.

These are later S04 proof obligations, H02 MCU feasibility, H02S exact SE
fault/reset tests, and V02/V03 integrated physical gates. No device, operator or
qualification resource is established. The current seven acceptance criteria
remain incomplete.
