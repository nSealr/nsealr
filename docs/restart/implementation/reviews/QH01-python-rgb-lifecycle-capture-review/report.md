# Independent lifecycle capture review

**CHANGES_REQUESTED** on `9703d03d0cf2e57bbf4de523b70aa0a2c7110768`, tree
`9a11a5c1ac6699af616332c5b80dc5d4d11afc86`. Two P2 findings concern the new
capture oracle, not the product or the original runtime outcomes. Candidate
source was not edited. Original review4314 and CI-wrapper review292 remain
applicable to their unchanged scopes.

## QH01-LIFECYCLE-CAPTURE-01 — incomplete status wire and FD validation

New `verify_qh01_lifecycle` lines359–361 checks canonical base64 and compares
ordinary `json.loads` results with the phase/terminal dictionaries. It does not
check the4096-byte status cap or the canonical wire encoding. Lines325/331–332
check FD numbers and distinct identities but not the declared pipe target.

Two independent data-only witnesses on the original null-case receipt return the
same successful checker result as the original:

- Prepend4096 ASCII spaces to its1423-byte status wire. The resulting5519-byte
  wire exceeds4096 and is noncanonical, while both parsed records remain exact.
- Change phase FD0 target to `/definitely-not-a-pipe` and rebuild its canonical
  status wire. The1429-byte wire and phase dictionary agree, yet the claimed
  descriptor is not the required `pipe:[ino]`.

The source-bound B3 rejects both. `qr_owner_adapter.py:93–99` requires exact
canonical ASCII/LF JSON and rejects duplicate/float/nonfinite forms; lines278–300
require ordered phase keys, canonical unsigned decimal identities and exact pipe
targets; lines322–339 enforce STATUS_CAP4096 before accepting a channel. The new
checker must retain these finite record/cap constraints rather than accept a
semantically similar but impossible successful B3 receipt. Add corruption controls
that preserve the phase/terminal cross-binding while violating these constraints.
This request is scoped to the new lifecycle evidence path, not a second B3 engine
or a re-review of the historical positive checker.

## QH01-LIFECYCLE-CAPTURE-02 — preG stderr admits an impossible source path

Lines344–349 permit arbitrary canonical/count-bound stderr up to512 for the preG
case. Root independently flagged the source discrepancy during this review;
inspection and a data-only witness confirm it. With G0, W-image0, actual W−9/raw9
and all original statuses retained, setting observed/retained stderr to1 and
base64 to `eA==`, then rebuilding the canonical status wire, still returns success.

The fixed worker's `main.rs:45–58` emits setup stderr only for failed setsid and
returns70, which this successful-policy fixture excludes. Its preG EOF/invalid
gate return71 emits none. With session policy already established, SIGKILL before
G also cannot pass through the later decoded diagnostic. Decoded cases emit the
33 bytes at line105; they remain separately valid. Require zero preG stderr for
the admitted71/−9 alternatives and retain decoded33 correspondence. Preserve the
original failed zero-for-all checker and its first correction as historical;
`verifier-correction.json`'s setup-stderr-for71 rationale needs an explicit erratum,
not replacement of the original evidence.

## Checks completed and limits

The full changed function and pure-control script were read. Existing checker AST
is byte-independent AST-identical to actualmainBD after removing exactly the new
function and its one `verify_product` call. No old full15-build or source/build
check was relaxed. The19 manifest members plus self20 match frozen Git bytes;
the worker/B3 source identities match the f7 runtime source.

One independent execution of the **unchanged pure script** on the original616947B
log/SHA `e3b31f6f629f45eefeb0e2374c98958a850425738b63347f7e1ec48c82cf8eac`
passed the existing positive, three lifecycle records and38 corruption controls,
exit0 in0.379686918s. Root's earlier27 positive corruptions are reused because
that function is AST-identical; they were not rerun. Missing/duplicate/order,
source/generated identity, collection/waits, timeout close0→close1 and preG API0
checks are present, with source-qualified synthetic client100 and actual O8/shared4.
Their passing controls do not cover the two gaps above.

Witness source was frozen before execution at
`0540b76c` on this review branch. One further pure inspection/witness command
returned0 in0.136211728s: **exit0 means all three invalid-evidence acceptances
reproduced**, not gate acceptance. `witness-result.json` binds original/mutated
wire hashes, exact lengths and source. A quick progress message initially gave a
wrong padded length; the actual receipt always said5519 and the message was
corrected. No evidence, expectation or runtime was changed.

No O/W/C/Node, build, install, Pi suite, full-product or hosted CI was run or
queried. No product source, threshold, fixture, graph or author report was edited.
This review establishes neither physical/target qualification nor component/task
completion. Correct only this checker perimeter, retain the RED and witness
history, then request affected review before protected/full integration.
