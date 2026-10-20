# S03 implementation candidate

The portable S03 boundary is implemented and passes author acceptance. It is
ready for a distinct review of the exact final diff. It is not merged and does
not qualify a public profile or the remaining event catalog. Product transport
continues to return `signing_disabled`; the new production attempt consumes its
one authorization and returns `SigningUnavailable`.

The complete review candidate is the Git commit containing this handoff and
`acceptance-result.json`. Final product/source commit is
`271bb88cf8a3efef71a01f2130897ab098e537a5`; behavior commit is
`e6747615f13734f8fce3724bc03c7c5b98c90f07`. The later source commit corrects only
obsolete legacy comments claiming preview decisions permitted signing. Source
input is `3cbd818a0bcd4016eb8983dad7605cb57280d913`. Approved specification is
`e63165d95f6094877b031f4baccce32831a50d68`; approval is recorded in
[../reviews/S03-spec.json](../reviews/S03-spec.json). Its three preparation files
remain unchanged, so their historical preparation status is intentional.

`event.rs` owns exact JSON/UTF-8 parsing and NIP-01 canonicalization. Both serial
and QR paths now use that reader; malformed known/unknown/duplicate fields fail
closed. Existing numeric wire version 1 remains. `review/event.rs` admits the
specified kind-1 subset, validates known semantics and presents every signed
field and the actual author through a complete, injective inspection cursor.
Malformed or unsupported known semantics never use raw review as a fallback.

`authorization.rs` owns the consumed key, immutable operation, complete review
commitment and one-use consent. The first attempt consumes before correlation,
clock or backend checks. Cancellation, account/policy/configuration changes,
lock/reset and deadline invalidate prior work. A private execution handle
borrows its original owner and cannot be delivered into another owner. Local
input is only the synchronous trusted-image presentation adapter boundary;
there is no host grant, public approval constructor or raw-secret callback.
Legacy copied preview decisions have no conversion into execution authority.

The 20 approved behavioral families map requirements and source gaps to exact
source/test locations in [acceptance-result.json](acceptance-result.json).
[evidence/commands.json](evidence/commands.json) records UTC, argv, source hashes,
exit codes and complete bounded logs. Final `make ci` passed: both Clippy modes,
workspace/std suites, 15 public-boundary doctests, firmware-target build, deny,
unchanged coverage floors and three clean reproducibility builds. Core coverage
is 100%; simulator coverage is 76.76% against 76.70%. Device rlib SHA-256 is
`a5c17e9a518ccd6f110a2c96638d197b393b2896889882e7f102f2d71ec69260`.

Independent expected vectors were committed in `b2a9bb6` before product changes.
The hash-pinned upstream BIP-340 reference and separately authored Python
JSON/hashlib oracle agree with eight actual signatures and three actual key
imports. Seven official verifier controls pass. The oracle rejects 512 signature
byte mutations, 256 event-ID byte mutations, 32 canonical field mutations, eight
wrong-key cases and eight double-hash cases. Expected vectors were never
regenerated from observed Rust output. All fixture scalars are public disposable
keys. Six intentional baseline behavioral failures, intermediate adapter/lint
failures and the corrected observation-output path failure remain auditable.

The host retained sizes are 5,232 bytes for the event, 5,728 for the pending
operation and 6,016 for the complete session. The 136-byte backend key option is
already included in the session; no retained canonical buffer or page list
exists. Firmware-target const assertions enforce pending <=8 KiB and session
<=16 KiB. These are static type limits, not measured peak stack/RAM or device
latency. The report separately inventories caller input, canonical-output,
frame, execution and backend/compiler scratch.

The root-authorized recovery scope adjustment is exactly three identifier
substitutions each in `session/source_backup.rs` (lines 9, 19, 590) and
`board_profile_tests.rs` (22, 536, 597): `render_review_page` became
`render_preview_page` in documentation, import and call. The same renderer,
recovery payload ownership, reveal/cancel behavior and raster expectations are
preserved. No recovery/secret authorization was added.

k256 normalizes odd-Y input `d` to `n-d`. Actual imports of 1, 3 and n-3 are
verified; the original n-3 scalar is no longer reconstructible from this
execution owner. This establishes no import/export normalization policy.
D02/K01 must preserve original source custody before this consuming conversion
when integrating recovery. The pinned NIP-44 x-coordinate requirement implies
scalar negation preserves the shared x-coordinate; that algebraic observation
is not an implemented or qualified NIP-44 path. Backend conversion temporaries,
physical erasure, entropy and final target linking remain unqualified.

The ASCII cursor is a portable inspection baseline. Real product screens still
need faithful readable Unicode plus exact inspection and owned renderer/device/
P02 usability acceptance; no normalizer or truncation fallback is licensed by
this work. K01 owns remaining catalog reviewers, actual production output,
provider/entropy and output-boundary proof. T01 owns profile capabilities and
routing; neither descriptors nor host persistent grants may become consent.

The reconciliation against main
`f2ef70f522af4977e15f81554a8c6eadcdbe8097` recomputes all 43 approved input hashes:
41 match, and only restart README/work-items lifecycle metadata differs.
Root must coordinate A02 selected-source/layout adoption before integrating this
candidate, then reconcile T01 migration against the frozen API. No graph edits,
merge or physical/catalog acceptance are performed by this author.

To reproduce actual observation and independent verification from this checkout:

```sh
S03_OBSERVED="$PWD/docs/restart/implementation/S03/evidence/observed-events.json" \
  cargo test --locked -p nsealr-core s03_ -- --nocapture
python3 docs/restart/implementation/S03/oracle.py --check \
  --fixtures docs/restart/implementation/S03/vectors.json \
  --observed docs/restart/implementation/S03/evidence/observed-events.json
make ci
```

Review should inspect the complete diff from the pinned source input, preserve
the approved task split, and add independently chosen hostile transitions and
mutations. Author test agreement is evidence, not independent review approval.
