# Paused reset follow-up — incomplete and unreviewed

User explicitly paused work before this follow-up was completed. This is a
capture of existing findings, not a protocol adoption, new experiment, part
selection, implementation handoff or S04 completion. The exact preceding partial
checkpoint is `46ad56440c1e9f86dfdb9ccc8c9ee4e6c9fdb5ea`.

The frozen TM-HMAC-1 experiment fails reusable-Board acceptance. Safe7's actual
cyclic PIN_SECRET/verifier relationship supplies a concrete alternative, but its
factory pairing and vendor-controlled firmware roles do not implement nSealr's
independent-owner lifecycle. See `safe7-reference.md`; no dual-SE inference.

The already-read Trust M RM3.70 §6.5.6 includes AUTOREF as well as PRESSEC in its
recommended maximum2048 shared-secret uses. A proposed minimal cycle has S as a
publicly replaceable AUTOREF release factor, V as a PIN-related AUTOREF, S READ
under Auto(V), V CHANGE under Auto(S), and counter reset under the other secret's
authorization. If both authorization-use budgets are exhausted, replacing S
alone does not renew the counter needed to authenticate new S. Publicly resetting
that counter can instead renew queries against surviving old S. An unlimited S
EXE avoids that dependency but does not discharge the usage recommendation.
These are specific obligations for this proposed graph, not a proof that every
Trust M construction is impossible. The protected-update command addresses one
target; F0 resets that target before metadata replacement. No cross-object
revoke-before-reset primitive was established in the sections read. Mutable
PRESSEC still requires integrity/confidentiality-protected update under the
manual's READ/CHANGE guidance.

The new public NXP middleware input is
`7102413e0457d3dfa4fc4be686ca8ec50bd9f5e2`. Its API header documents real DeleteAll,
not an imagined generic reset: reserved authentication object `0x7FFF0205`,
INS_MGMT with P2_DELETE_ALL=`0x2A`, deletion of application objects/curves/crypto
objects, preservation of NXP trust-provisioned objects, and session closure with
an unwrapped response. WriteUserID documents4–16 value bytes, a2-byte maximum
attempt field, and a PIN limit below256; zero means unlimited in the header.
These declarations do not establish actual SE051C2 torn-reset atomicity,
existing-PIN update/reset semantics, exact policy permissions or errata closure.
The official AN12543 download redirects to sign-in, preserved in the
[addendum](reset-source-addendum.json). Public source does not replace it.

The concrete interrupted-reset obligation is: if DeleteAll can delete an old PIN
object while its old release object survives, and a caller can recreate the PIN
at the same authentication-object ID, the old release policy might authorize the
new PIN. An atomic deletion or persistent chip-enforced quarantine blocking all
normal operations until deletion finishes would prevent that specific trace.
Neither behavior is claimed for actual NXP silicon. The unwrapped final reset
response alone cannot prove completion or absence of all old objects.

Application-object deletion also does not revoke prior owner platform/recovery
SCP credentials, manufacturer objects or vendor applet-update rights. Runtime
rotation protected only by an old compromised symmetric binding key does not
hide the new key from a holder recording that transfer. A fresh-owner ceremony,
its authenticated channel, complete surviving-object inventory, and MCU/root
re-enrollment remain unresolved; wallet wipe is insufficient.

An author-only finite exploration script was written before pause at
`evidence/explore_reset.py`. It models the reduced AUTO cycle with a scaled
counter of2, and three hypothetical DeleteAll semantics. It has **not run**;
there is no `reset-exploration.json`, no reported state count and no accepted
counterexample execution. Its old/new/invalid write assumptions, optimistic
AUTO clear, and persistent quarantine are explicitly model assumptions, not
source-backed hardware observations. No complete next protocol was specified.

On explicit resume, first review these incomplete assumptions and exact source
bindings. The smallest next work is to finish the reduced permission/ownership
question and its independent oracles, with the exact APDU/reset contract and
errata as an access gate. Do not raise2048, leave reset unlimited, adopt vendor
factory roots, add another chip, or call a partial model an accepted protocol.
All seven S04 criteria, distinct crypto/spec review, H02/H02S and V02/V03 remain
open. No physical resource/operator availability is established.
