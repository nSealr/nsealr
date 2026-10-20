# S03 integration preparation against the consolidated product

Current coordinator source refresh: protected main `b1c90139a651895284b2624da7d12903cf16bc9d`, tree
`0014d51b24ea0b58650d3dee3a5a8616367e6769`. Actual corrected-main [CI39412818666](https://github.com/nSealr/nsealr/actions/runs/39412818666)
completed **successfully** on the exact main commit; distinct source/specification
acceptance remains pending and no product implementation is admitted.
[The exact source-pin addendum](source-pin-addendum.json) classifies every
repair delta and all30 context bindings. The original preparation below is
historical; its target21 paths and all746 target preimages are unchanged.

Author `/root/a02_sol`, 20 October 2026. This is bounded preparation, with no
product patch, dependency resolution, backend change, fixture generation or
product execution. The preparation worktree is based on A02 adoption candidate
`a5f7b9f2e087c9538495a16706644f3390e6b01c`, tree
`e67b1337eaea5cfe3242fe4d83845881764ea5f0`. That candidate remains immutable.
Historical preparation observation: the coordinator subsequently reported normally integrated A02 main
`d931277bebbc5f43514b0e8438d65fb60603fa35`; read-only Git inspection confirms its
tree equals the preparation base. Exact push CI [39408038674](https://github.com/nSealr/nsealr/actions/runs/39408038674)
was initially observed `in_progress`. Its completed result is **failure**:
the cold main-only checkout cannot resolve intermediate provenance commit IDs
rewritten by the protected rebase. That bounded forward repair was subsequently adopted as `b1c90139`;
its actual-main CI passed, as recorded in the current source-pin addendum.
S03 implementation remains held until corrected actual-main input, successful
CI and distinct source-pin/specification acceptance are supplied.

The [source reconciliation](source-reconciliation.json) binds every one of the
746 changes between original S03 input `3cbd818a0bcd4016eb8983dad7605cb57280d913`
and delivery `03216fba02d229bcdb5c81d0573bbe26c6f35abc`, together with current
target preimages. There are 21 product paths, 686 files in 21 new vendor
directories and 39 historical evidence/specification paths. Fourteen product
paths overlap A02: `Cargo.lock` and 13 core paths. Seven other product paths
have no A02 overlap. All modes, blobs, byte counts and SHA-256 values are recorded;
integrated postimages are intentionally absent.

The original implementation review `b03475ccf4a057c7771065126002f2e4e056d28d`
still binds candidate `2d7d465a291c4d4a1324d90595fc45a2fdbefca5`. The separate
three-comment review `8df9f5bb3231eac4d33cc9837851ad3ab9bad537` binds
`95cd3fc79d885c58bdabe71498d2509b6ff4370e`. Neither becomes a review of future
integrated bytes. Reuse their source conclusions and preserved evidence; focus
the new specification/delivery review on the collisions and target interfaces.
Do not restart the old S03 substantive review from scratch.

## Admission gate and requirement authority

Before code, the coordinator must bind the observed normally integrated A02
main commit/tree to an actual successful exact-main CI run and reviewed
integration identity. The historical failed run does not satisfy this requirement; the corrected run must complete successfully.
Reconcile this preparation's 30 requirement/context bindings, all 21 source
paths, both lockfiles, vendor inventory and contract artifact against that actual
main. Classify every difference; do not silently substitute latest main or
overlay an older tree. The source-pin addendum and this concrete integration
specification require distinct acceptance before implementation. An A02 PR or
local PASS does not satisfy this gate, and no future SHA or approval is invented.

Correctness comes from the five unchanged S03 criteria in `plan/work-items.json`,
current `docs/product/{contract,requirements,event-review-contract,threat-models,
client-qualification}.md`, the AUTH contract in `docs/restart/development.md`, and
the accepted S03 split/grammar. Exact preparation bindings are in the JSON.
Current P01 copies are the declared link-relocated reviewed requirements; do not
restore retired normative paths. The accepted S03/P01 NIP pin is newer than the
client-qualification pin; their exact relevant delta is assessed below.
No new wire version, supported catalog, normalization policy or normative vector
revision is proposed. K01/T01/C02 and device/P02 release gates remain separate.
The accepted S03/P01 NIP pin is `37db6395` (17 October); current client
qualification cites `a79e21d9` (5 October). The [primary-source comparison](nip-reconciliation.json)
accounts for the complete NIP-01 delta: relay empty-list filter matching, outside
this event-template/authorization scope. The twelve other compared NIPs have
identical blobs. For S03 retain `37db6395`, the already accepted narrower grammar
and immutable expected data. This does not revise the global client-qualification
baseline or claim a new full review of unchanged protocol documents.

## Concrete source reconciliation

Preserve the current target and port the reviewed behavior by explicit file
changes. No wholesale cherry-pick of S03's old root graph, docs, workspace or
fixture snapshots is allowed. The per-file JSON gives the complete disposition.

| Collision | Required combined behavior |
| --- | --- |
| `Cargo.lock` | Resolve the retained core-only graph with exact reviewed dependencies; update the independent host lock as well. Never restore the combined old workspace lock. |
| `crates/nsealr-core/Cargo.toml` | Retain A02 package/no_std/build setup; add reviewed `k256 = 0.14.0`, defaults off, `schnorr` only, and `serde_json = 1.0.151` as a dev dependency. |
| `src/lib.rs` | Add `authorization`/`event` modules while retaining current portable-core/Pi-oracle documentation and test setup. |
| `src/policy/approval_gate.rs` | Port `ReviewDecisionState` and `review_approved`; retain projected fixture constants/tests. This copied preview record never authorizes execution. |
| `src/policy/policy_change_review.rs` | Port diagnostic method references over generated policy fixtures. No policy-change signing authority is introduced. |
| `src/protocol.rs` | Replace permissive metadata scanning with `event::ParsedRequest`; retain projected device request/response inputs and signing-disabled transport. |
| `src/qr/envelope.rs` | Use the same strict reader, preserve raw spans solely for preview, existing QR limits and generated inputs; remove the old permissive scanner. |
| `src/review/display.rs` | Rename the legacy renderer to `render_preview_page`; retain current expected raster data. Ellipsis remains diagnostic, never consent. |
| `src/review/qr.rs` | Merge diagnostic API/closure-typing changes and strict-intake negatives while retaining generated detail-page expectations. |
| `src/review/qr_flow.rs` | Merge `review_approved` Rust fields/methods and all three reviewed comment corrections; preserve current transcript projections. |
| `src/review/serial.rs` | Merge diagnostic API changes over current projected serial inputs and transport bounds. |
| `src/review/trusted.rs` | Use the renamed diagnostic state/renderer; retain generated basic/tagged functions and reject conversion to execution authority. |
| `src/review/types.rs` | Merge renderer-reference documentation without restoring copied review data. |
| `src/session/source_backup.rs` | Apply only the three reviewed renderer identifier changes; keep current projected recovery inputs, ownership, reveal/cancel and raster behavior. |

Paths beginning `src/` in this table are relative to `crates/nsealr-core/`.
The seven other source paths are the four new authorization/event implementation
and test files, the review module export, host review replay consumer and board
profile test naming adjustment. Their exact source identities and individual
porting rules are recorded; an unchanged target preimage still needs combined
acceptance. Do not restore source-era claims that Pi already uses this engine.

Retain `crates/nsealr-core/build.rs`, all 170 current
`ci/core-test-projections.json` rows, `ci/project_core_fixtures.py`, generated
review/detail/policy helpers and `review/test_fixtures.rs`. Rebase S03 test/API
edits onto those data references, rather than bringing back its embedded copies
of contract JSON, expected pages, hashes or policy values. Historical fixture
keys such as `approved_for_signing` may be mapped to diagnostic replay expectations;
they cannot construct `AuthorizationSession` state or become a public approval API.

Keep original S03 `vectors.json`, Python oracle, pinned BIP340 reference, official
controls, licenses and earlier observations byte exact and bound to their old
commits. A separate declared data-only OUT_DIR projection may copy those immutable
independent vectors for `authorization/tests.rs`; add its explicit rerun input and
include it only in tests. Do not put another committed copy in `protocols/contracts/v1`
or compute expected IDs/signatures through Rust, the renderer or a fixture generator.
Unique hostile raw-JSON test inputs remain legitimate negative inputs.
New actual outputs must go under new `integration/evidence/` paths, never overwrite
the original observed-events files. The independent fixture source and oracle must
not learn their expected values from these outputs.

## Workspaces, dependencies and vendor union

Preserve root core-only and standalone `apps/desktop-simulator` workspaces, both
Rust 1.95.0 pins, both locks, source-replacement configurations and distinct
target directories. The current two-lock union contains 26 package identities;
all are present unchanged in the reviewed source's old combined 47-package lock.
The additional 21 exact versions/checksums are in the reconciliation. Their 686
changed vendor files are all absent from the current target: no same-path vendor
conflict was observed. This does not waive new actual lock/feature verification.

After admission, resolve both exact graphs without upgrading unrelated packages;
record lock/metadata/feature closures and the actual pinned Cargo commands. Build
one vendor union from both locks in an absent owned output, preserving current
host packages plus the used S03 dependency closure, `.cargo-checksum.json` data,
license files and notices. Compare every retained/new file with declared inputs;
do not replace `vendor/` with S03's old workspace snapshot. Check offline/locked
embedded, std and host builds and both dependency audits. `serde_json` stays test/
host-only; verify no accidental std/default/RNG or fixture backend enters the
production target. Retain inherited audit warnings honestly and unchanged floors
of core 100.00% and host 76.70%; establish actual new coverage/reproduction hashes.

## Parser, authority and recovery boundaries

`nsealr.authorization.v1` is the internal boundary. Existing numeric wire version
1 remains a legacy signing-disabled envelope, with exact required fields,
decoded duplicate/unknown-field rejection and one complete strict UTF-8 object.
Canonicalization preserves decoded strings, Unicode form, tag order and duplicate
tags, with the reviewed NIP-01 escaping and finite integer grammar. Authorization
admits only the reviewed kind-1 semantic subset; malformed known semantics and
other kinds cannot fall back to opaque or diagnostic review.

Retain separate limits. The source conformance configuration admits input 4,096,
content 2,048, 32 tags, eight fields/tag, field 256, text storage 4,096, canonical
8,192 bytes and 1,024 review pages. Legacy QR intake overrides input/content/tags/
field to 704/512/16/64 and keeps its existing transport envelope limits. Serial
also retains its outer bounded frame/request policy. No transport gains the
internal conformance capacity merely through the merge. Compare every current
artifact consumer, error mapping and boundary case. An unexplained positive,
negative or expected-value disagreement stops the integration; do not rewrite
fixtures, widen limits or weaken checks to turn it green.

The non-Clone owner derives identity from consumed custody, preflights the complete
injective inspection cursor and consumes consent before correlation, clock or
backend checks. Keep local display/input as a trusted-image adapter, with no
host/transcript/grant conversion or raw-secret callback. Cancellation, lock,
reset, policy/account/configuration changes, expiry, rollback and generation
overflow invalidate prior authority. Fixture signing stays private `cfg(test)`;
production attempts consume and return `SigningUnavailable`, while product
transport returns `signing_disabled`. No backend/model/provider is added here.

Retain the odd-Y scalar limitation: k256 normalizes `d` to `n-d`; fixture keys
1, 3 and n-3 demonstrate this execution-owner behavior. It cannot recover the
original imported nsec. Do not add export/recovery normalization or a NIP-44
service. D02/K01 must preserve original custody before such a consuming conversion.
Recheck static retained bounds in the combined target (pending <=8 KiB, session
<=16 KiB); prior host sizes and successful compilation prove no peak stack/RAM,
latency, physical erasure, trusted clock, entropy or actual-device consent.

## Combined acceptance and handoff

The [acceptance plan](acceptance-plan.json) preserves all five criteria and all
20 original named behavioral families, then adds collision/projection/lock and
consumer checks. Actual implementation must run the combined parser through
core/host, serial/QR, Bridge/Pi/helper/product integration boundaries, not only
recompile renamed unit tests. Existing independent expectations/oracles remain
unchanged; reuse the old review for its source only and add focused independent
adversarial checks on the combined candidate.

`make product-gates integration-tests integration`, the complete 17-step runner,
and the root product-gate controls are affected by parser changes and required.
Preserve each existing case's obligation; account explicitly for error-layer/API
changes, never infer equivalence from equal names/counts. Run complete combined
`make ci` once coherent, including Rust, artifact, Bridge, Pi, packed SDK, helper,
coverage, audit and reproduction gates. Distinct exact delivery review and normal
protected PR/main CI remain required afterward. No graph closure, source archive,
registry operation, hardware/SDK extraction or dependent task implementation is
part of this preparation.

## Exact write boundaries after source/specification admission

The repaired `scripts/verify_contracts.py` and `scripts/test_contracts.py` are
read-only inputs. So are `scripts/check_product_gates.py`,
`scripts/test_product_gates.py`, `tests/integration/run.py` and all v1 contract
bytes. Their appearance as inspected interfaces grants no write permission.
The declared21 product paths, separate host lock, exact used vendor union,
projection generator/configuration, core build script/test helper and new scoped
proof remain the bounded future edit set. Any necessary change outside it needs
a concrete reviewed scope addendum; do not alter a gate to hide disagreement.

The addendum explicitly admits all39 original historical S03 evidence rows
from delivery03216fba, plus all41 regular files of original security review
b03475cc. Its80-file manifest binds each source commit/mode/blob/size/SHA256.
Copy those public files byte exactly after admission, preserving failures and
source-only review identities; append combined observations separately.
No old root graph, old combined lock, copied active fixture literals, private
manuals/history or additional proof directory is admitted by that manifest.
