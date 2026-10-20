# T01 artifact pin pre-adoption review checkpoint

**REQUEST_CHANGES** on artifact subtree
`86ffb0c249aea5ac15c84541f925d35adf1cdc20` from author candidate
`24b0b58a6ee085d8176a801a7bad5595d39965b7`, also unchanged at
`104f5e369244dcdc3afe87bb91074067c6ad8ac7`. Reviewer `/root`;
author `/root/a02_sol`. This checkpoint identifies one concrete schema/reference
inconsistency, not a complete T01 review. No literal pin is approved here.

## T01-ARTIFACT-01: retired smart-card recovery survives the new contract

`schemas/account-v1.schema.json` still declares `card_slot` recovery and
`scripts/verify_specs.py` still accepts it in `check_account_descriptor_shape`.
The actual current `packages/policy/src/policy.ts::validateRecovery` rejects
that type. Smart-card routes are already retired; this is an inherited branch
copied into the new schema/reference rather than a request to add another device.

The [actual reproduction](recovery.command.json) uses the public
`esp32-usb-device-slot-0.json` account. Its unchanged device-slot recovery passes
both the independent Python reference and the exact-candidate locally built TS
runtime. Changing only its recovery to a fixed public card-slot object still
passes the reference but the runtime rejects `recovery.type is unknown`.
The schema branch was read directly; no general JSON Schema engine was executed.
Source, command, pinned environment and paired output hashes are recorded.

Remove only the retired recovery alternative from the new account schema and
reference validator. Preserve all four supported recovery forms, current runtime
rejection and all original test obligations. Add a focused reference negative
and schema validation with an existing sufficient command where available;
do not add a permissive compatibility branch to runtime. Retain this witness and
review as historical evidence. Refresh the manifest current postimage and the
literal subtree proposal after the bounded correction, then review that delta.
The already reviewed metadata component excludes this account schema and is
therefore not invalidated by this finding.

## Other inspected input and remaining review

Read the complete profile-capabilities, implementation-limits and signing-v2
notes; account and route-selection schemas; consumer scope list; the four
modified non-signing note/recipe diffs; all authored/retired inventory paths;
the 228-line fixed-preimage expected-data transform; and the account/route and
new capability/limits reference sections. The manifest records143 maintained,
97 modified,15 authored and11 retired paths. Ninety-two modified paths come
from the fixed-preimage transform; the other five are the three current notes,
error schema and the unsupported-version negative's expected message.
This reading does not claim execution of all42 cases, all170+3 projections or
the complete reference suite. Final exact inventory/mode/byte verification,
corrected stable literal, full T01 gates, distinct source review and protected
PR/resulting-main CI remain open. Production and physical release gates remain
unchanged.
