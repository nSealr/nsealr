# S04 reset and session findings — 20 October 2026

This is an unreviewed research addendum to `e823fecfd4bdc5d2eb0e4b31aedc3ac66cfabe36`,
after the maintainer's explicit resumption. It admits no part or protocol and
closes none of the seven S04 criteria. TM-HMAC-1 remains the frozen failed
reusable-Board experiment. The paused `evidence/explore_reset.py` remains
unexecuted. Source bytes and access failures are bound in
[`resume-source-addendum-2026-10-20.json`](resume-source-addendum-2026-10-20.json).
Original manuals, source and retrieval records remain private.

## Credential changes are not necessarily session revocation

The publicly retrievable [NXP AN12413 Rev2.12, SE050 APDU specification](https://www.nxp.com/docs/en/application-note/AN12413.pdf)
is historical context, **not** the missing SE051C2 applet contract:

- Sections3.6.4–3.6.5 retain a session when its authentication object is updated.
  Deleting that object within another session also leaves the original session
  open. Self-deletion closes its session after the response; deselect and power
  cycle are other closure mechanisms.
- Sections3.2.3 and3.7.4 restrict authentication objects to opening sessions and
  a limited policy set. The contemplated single AES object that both authenticates
  a reset and decrypts stored custody therefore has no established command route.
- Sections3.2.6–3.2.7 distinguish mutable value from fixed attributes and restrict
  reads to non-secret key portions. A read permission is not general secret-key
  export authority.

These facts reject optimistic generic assumptions; they do not establish the
same behavior for SE051C2. AN12543, AN12730 and applicable SE051 errata remain
required exact inputs. The [current SE051 document index](https://www.nxp.com/products/SE051)
still lists the first two as account-required.

The resulting S04/B01 obligation is to distinguish host-handle invalidation from
chip authorization invalidation. A claimed owner transition needs an actual
backend closure/reset sequence, including outstanding sessions on other
interfaces, interrupted closure and a lost response. Changing a credential,
dropping a host session handle or incrementing a host epoch is insufficient
evidence. No new backend API or implementation is added here.

## Reset completion needs a specific witness

The official NXP Community attachment [AN12514 Rev1.4, SE050 User Guidelines](https://community.nxp.com/pwmxy87654/attachments/pwmxy87654/secure-authentication/1757/1/AN12514.pdf)
§4.5.3–4.5.4 preserves provisioned objects and requires an attested read of a
previously existing object after DeleteAll. Sections7.1.3 and7.2.3 require
freshness checks for attestation and finite UserID attempts; a UserID session
alone does not protect communications. These are historical SE050 requirements,
not proof of SE051C2 deletion atomicity.

A fresh absence witness for one object cannot prove that every old factor,
authentication object, platform SCP key or vendor object disappeared.
If a reset can remove an old PIN object while preserving its old release object,
recreation at the same authorization ID remains an unresolved attack condition.
The actual applet must prevent that condition by its documented ordering,
transaction or quarantine behavior, or the design must avoid it with another
source-backed primitive. The old finite model assumes possible answers and
cannot determine which answer silicon implements.

## Middleware policy types do not define silicon permissions

The existing pinned [NXP policy serializer](https://github.com/NXP/plug-and-trust/blob/7102413e0457d3dfa4fc4be686ca8ec50bd9f5e2/sss/src/se05x/fsl_sss_se05x_policy.c)
conditionally ignores `KPolicy_Sym_Key.can_Write` for applet versions at least7.2;
the corresponding `KPolicy_Common.can_Write` branch emits the write flag there.
The UserID serializer can emit a write flag, while the historical
[NXP support answer](https://community.nxp.com/t5/Secure-Authentication/SE050-Overwritting-UserID/td-p/1095593?profile.language=en)
states UserID replacement requires deletion and recreation.
Thus a C field, serializer branch or successful host-side encoding cannot prove
that the selected object supports a requested operation.

The newly fetched versioned write declarations and implementations are pinned
to the same commit. They add source visibility, not an exact-applicable policy,
counter-renewal, torn-write or session-revocation guarantee. No serializer,
driver, chip command or new model was executed.

## Bounded next work

The Trust M manual was re-read at §4.4.1.5, §5 tables71–72 and §6.5.6–6.7.3.
Its protected metadata update resets the addressed target before replacing that
target's metadata. That is not a demonstrated transaction across the release
factor and its linked counter. An off-device signing authority could change the
reset authorization argument, but its loss, transfer and revocation would need
their own concrete lifecycle; it is not an adopted repair.

The next owner should first obtain the exact NXP contract through lawful access
already available to the project, if any. Then decide one concrete reset path
against its actual commands, immutable attributes, session persistence and fault
semantics. Do not elevate the historical SE050 documents, unchanged Trust M
guidance, wallet code or a hypothetical model to SE051C2 admission. If the needed
contract remains inaccessible, report the precise missing obligations to the
coordinator for a bounded scope decision. TROPIC advisory/configuration and MCU
owner-root gates remain unchanged. No fourth SE lead is authorized here.
