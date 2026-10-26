# C01 account key pin correction

When a dispatcher changed, replaced or removed its route copy's public key,
the local service could accept a valid event signed by identity B for an account
configured as identity A. Both sync and async final verification trusted that
adapter-owned copy.

The fix captures the original selected public key before any external callback
and retains it only in private PreparedSignerDispatch state. Both final paths
verify against that pin. It is public identity metadata, not host custody of an
identity secret. The adapter still receives its own mutable route copy; neither
a shared reference nor Object.freeze is used as the fix.

Base main: de388c9548bc04cdb44ea8ccd2197b2ab29befab.
RED source: b59289df9d448f18c74f50e5c15efdcdf3f718f7.
Production fix: 0ebfb45bd9c68dc0324b5b4bc5e48ed45a9a8ed6.
Final source/test candidate: b2d9875aca08c8811cbcc3081560304a8a13e8ce.
The delivery metadata commit changes no product source after that candidate.
Distinct root review and normal protected integration remain pending.

The product diff is limited to service.ts (13 lines) and service.test.ts.
The unchanged signed fixture B and known public scalar1 generator key A supply
the counterexample. No signing backend, schema, public API, core, custody, S3,
plan or hardware state changes.

| Evidence | Result |
| --- | --- |
| 03 initial old-code RED | Six mutation cases fail as expected; four controls pass |
| 06 first fixed regression run | All ten pass |
| 08 focused service/profile/browser/driver checks | 79 tests pass across four files |
| 13 final exact-test GREEN | All ten pass |
| 14 old production with the same final test bytes | Six expected failures and four passing controls |
| 05 actual consumer workspace resolution | 84 workspace links target this checkout; no S3 dist |
| 07 current production workspace build | PASS |
| 10 complete workspace typecheck | PASS |
| 11 restart-plan validator | PASS; structural check only, 47 tasks unchanged |
| 12 existing public API review check | PASS; current API unchanged |

The six regressions cover changed key, replaced route and removed key, each in
sync and async paths. Matching-key success, unchanged valid foreign-key rejection,
two normal before_write calls and an unchanged configured account are asserted.
The broader existing checks preserve correlation, account/capability/connection/
limit invalidation, browser routing and the standard serial driver behavior.

The initial regression tests needed a TypeScript fixture-narrowing correction
(09 failure). b2d9875a captures the already-validated fixture for its nested
helper; production code is identical to 0ebfb45b. The exact final tests then pass
against the fix (13) and fail for the original acceptance defect against the
old production blob (14). The temporary old production file was restored byte
for byte; restored-green-source.json records its hashes and empty Git diff.
The other 69 unchanged checks from 08 were not repeated for this test-only alias.

Two setup/verifier mistakes remain explicit. The first recorder invocation
needed its execution parent directory (no product command had started).
The first resolution check 04 incorrectly assumed @nsealr/transport was a direct
root dependency. Check 05 follows every actual workspace consumer's dependency
links, including CLI/service transport links; no dependency or threshold was
changed to make it pass. All raw errors and corrections are preserved. Raw captures retain the CLI blank
lines/trailing spaces byte for byte; authored source and metadata are checked
separately for whitespace.

The current workspace was installed offline from the existing shared pnpm store.
Build 02 supplied this new checkout's dependency exports before RED; build 07
updated the changed production client export before browser/driver verification.
Node/pnpm/cache and the existing recorder are reused. proof/tool-and-input.json,
manifest.json and SHA256SUMS bind source, tools, commands, exits and log hashes.

Limits: the dispatcher is same-process TCB code, and the stock serial driver did
not perform this mutation. This is a confirmed internal binding-invariant repair,
not an observed USB-only attack or general isolation against arbitrary hostile
callbacks. Raw generic transports and verify_signer_response still do not select
accounts. Physical device identity, complete client interoperability, secret
custody and human-wait/ACTIVE timing qualification remain separate gates.

No C01/H01 criterion or hardware readiness is closed. S3 delivery a1e9052a remains
unchanged; no hosted CI, push, merge or USB operation was performed by this author.
