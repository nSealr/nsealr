# A02 — software consolidation rehearsal specification

Prepared 2026-10-18 by `/root/consolidation_rehearsal`. This is a proposal for
distinct specification review. It contains no source import, implementation,
completed acceptance claim or authorization to adopt the rehearsal publicly.

## Purpose, authority and limits

A02 rehearses the five-owner topology accepted in A01 and
`docs/restart/repositories.md`: `nsealr`, `board-sdk`, `hardware`, `website`,
and `.github`. The coordinator confirmed that its initial assignment's mention
of private `workspace` as the fifth owner was a summary error. Private workspace
evidence/history stays private; its eventual archival requires verified handoff.
The existing three-star `nSealr/nsealr` repository remains the integration owner.

Requirements are the five ordered A02 acceptance statements in the canonical
graph, A01's reviewed module disposition, and the restart architecture/development
contract. Code demonstrates inherited behavior; accepted requirements establish
correctness. No old experimental API, product label or five-family rule creates
a compatibility obligation. External Nostr interoperability remains required.

The current preparation worktree is based on
`1df3eb421e7a0aa3c64964601d80c6c1a4577a99`. Actual R00/A01 integrations have
been reported by the coordinator, while this checkout's graph predates their
metadata reconciliation. `input-notes.json` records these observations and the
exact inspected source tuple. Do not implement against moving worktrees.

Before implementation, the coordinator must publish the bounded assignment,
reconcile the integrated R00/A01 graph, assign a different spec reviewer, and
record approval of this exact brief and input notes. Before import, pin the final
integrated S01 nsealr/companion/specs tuple and its corrected provenance-helper
patch. The checker must reject missing required `SOURCE.json` and fixture changes
hidden behind dotfile exclusions; correct current snapshot bytes alone do not
prove those enforcement properties. Record exact helper preimage, postimage and
patch hashes/manifests, the refreshed coherent active bootstrap input tuple and
default, renewed distinct review and successful affected integration. The earlier
`23e8b37` helper and `41f5d2d193e4a00227737e1f8d71ce57e39ea889` snapshot are
historical observations, not sufficient import admission. S01 is a
source-consistency gate here, not an invented task-graph dependency. Any changed
source affecting this brief needs explicit reconciliation and affected review,
not silent adoption of latest main.

Owned tracked paths are `docs/restart/implementation/A02/` and, after approval,
`tools/migration/`. The isolated target repository and temporary inputs may be
created only under the author's ignored runtime directory. No canonical product
file, other source checkout, main branch, source-repository settings or package
registry is mutated by A02. Later adoption, redirect publication and archival are
coordinator-owned actions under the existing authorization, requiring a separately
recorded concrete scope and review after the rehearsal. This brief does not invent
a further task ID; any independently tracked work must first enter the canonical
graph. The final reviewer must differ from the implementer and review exact commits.

## Source facts that constrain the design

- nsealr currently contains a real no_std core and host desktop simulator; the
  workspace has exactly those two members. A RISC-V core build is possible;
  there is no existing ESP32/P4 device application to claim migrated or tested.
  The simulated USB signing response is explicitly disabled. Preserve that fact.
- Rust fixture loading defaults to `tests/fixtures/specs/vectors`; companion and
  Pi also carry snapshots and prefer sibling `specs` in some loaders. Pi's hardware
  tests use their local snapshot directly. S01 updates complete metadata fixtures,
  so deduplicating an older partial snapshot would resurrect obsolete expectations.
- Companion's SDK root imports smartcard; its CLI, examples, smoke manifests,
  package build list and publication checks also reference it. Retirement requires
  consumer edits, not just deleting `packages/smartcard`.
- Companion currently has fourteen package directories. Existing internal
  package-publication assertions conflict with the adopted single public SDK.
  Browser/root exports already differ; preserve and strengthen real browser/Node
  consumer proof when making those internal modules private.
- Pi's `crypto.py` uses Python serialization/hashlib and libsecp256k1 bindings,
  independently of the Rust core and TypeScript implementation. Keep that oracle
  independent. Its camera/GPIO/ST7789 adapters are actual source worth retaining;
  mock/file/CLI approval paths do not establish physical authority.
- The lab integration recipe has twenty named steps. Some assert obsolete private
  taxonomy prose, two execute smartcards, and one imports separate hardware
  acceptance. Their disposition must be explicit before comparing new results.
- Board SDK has four tracked foundation files and no implemented build consumer.
  A02 can prove the migrated product has no dependency on that repository. It
  cannot prove future SDK/application independence with empty scaffolding; B02/B03
  own the real standalone non-Nostr consumer and lifecycle acceptance.

`source-observations.json` records Git-object identities and inspected paths. It
does not substitute for execution evidence or a full third-party rights audit.

## Rehearsal inputs and selected destination mapping

The implementer will turn this prefix plan into a complete per-file manifest
before import. Every tracked input path receives a disposition: retained exactly,
retained with a reviewed transformation, deliberately retired, or excluded with
a reason. No implicit catch-all import from private sources is permitted.

| Pinned source | Selected source paths | Rehearsal destination and disposition |
| --- | --- | --- |
| nsealr, final reconciled main | Existing public repository and history | Clone into the isolated target; preserve public ancestry and repository identity. Retain core, simulator, research/vector licenses, tooling and historical evidence. Adapt only approved migration consumers/build paths. |
| companion `678796900e462f5504e47fe934e2e5f23d85824f`, subject to S01 reconciliation | `packages/{browser-provider,client,core,dev-signer,fixtures,framing,nip46,policy,protocol,qr,review,sdk,transport}/` | Same `packages/` names initially; all implementation modules private, SDK alone a publication candidate. `dev-signer` stays a private fixture harness and must never enter the public bundle. |
| same companion | `apps/{browser-extension,cli,consumer-smoke,sdk-examples,service}/` | `apps/bridge/<name>/`; preserve origin/native-message, queue, identity, cancellation, error and non-smartcard consumer behavior. |
| same companion | Root package/lock/TS/test configuration, selected `scripts/*.mjs`, documentation supporting retained modules, MIT license | Root JS workspace; scripts under `tools/bridge/`; retained docs under `docs/bridge/`; preserve notice under `LICENSES/companion-MIT.txt`. Reconcile collisions explicitly. Do not import package-publishing workflows as enabled release jobs. |
| same companion | `packages/smartcard/`, smartcard-only CLI/examples/tests and fixture snapshots | Retire active smartcard package/commands and record each removed assertion. Snapshots deduplicate against the contract artifact. Source remains recoverable in its source bundle and public Git history. |
| raspberry `d1534d9dcfba8fe4a35cea2ed3529e32a5003dc6` | `app/nsealr_vault/`, `tests/test_*.py`, `os/stateless-qr-vault-profile.md`, pyproject/requirements, relevant docs, MIT license | `apps/pi/` with adapter and reference-harness scope stated explicitly. Preserve all three Python test modules. Freeze independent crypto/oracle behavior; do not route oracle expectations through Rust or the SDK. Existing signing harness is not a second newly approved production engine. K01 owns the portable engine, QP01 the exact kit/image feasibility, and Q02 the shared-engine Pi integration and physical qualification before product support. |
| same raspberry | `tests/fixtures/specs/`, generic cloned repo validators and scaffolding | Deduplicate fixture data; replace only structure assertions with checks for the actual new boundary. Do not retain empty `.gitkeep` directories as proof. |
| specs `45f8b6ff1123f3f55be4ce457fd1008e91043cc2`, subject to S01 reconciliation | `protocols/`, `schemas/`, `vectors/`, `examples/`, `scripts/verify_specs.py`, `scripts/generate_fixtures.py`, `tests/`, requirements, relevant protocol notes and CC0 license | One artifact `protocols/contracts/v1/` with content, verifier, independent tests, generator and CC0 notice. The artifact's v1 identifies its inventory/schema, not a claim that every inherited wire format is v1. Active smartcard-specific contracts/cases are removed with a per-case ledger; mixed fixtures receive reviewed edits. |
| lab `3303ab17a28ed32419576627d5abb93db3999635` plus exact approved S01 helper delta | Only named integration scripts, `integration_support.py`, `browser_integration_support.py`, corresponding tests and CC0 license needed by the integration matrix below | `tests/integration/` and `LICENSES/lab-tooling-CC0.txt`, after per-file privacy/notice review. Adapt explicit roots/commands, never import private Git objects/history or private wiki/plans. The helper patch is an independently hashed transformation, not a fictitious lab commit. |
| hardware / website / board-sdk / .github | No product source imports | Remain separate owners. Exact source pins may be used by separate regression or navigation checks; none is an SDK/custom-board prerequisite for the product build. |
| private workspace / private legacy hardware | No content/history imports | Preserve protected backups and source access. Missing root license is not resolved by assuming permission from a private repo's existence. |
| public smartcard | No active source imports | Keep existing public archived repository/history and star. No change to archive settings in A02. |

Keep all applicable nested third-party licenses when a selected path contains
them, including current Rust vendor notices and official crypto vector notices.
The imported root MIT/CC0 notice is not blanket relicensing. Public records may
identify approved private-source commits/paths and hashes; do not embed private
bundle objects, unrelated research, credentials, private remote credentials or
private repository content in the public target. An unresolved selected-file
rights/privacy issue blocks that import, not unrelated review work.

## Observable target contract

The result is a locally reproducible repository with an inspectable public-source
ancestry, selected source imports, explicit transformations, one contract artifact
and runnable existing consumers. It is not a public deployment or device release.

1. **One source of fixtures.** `protocols/contracts/v1/manifest.json` identifies
   every active fixture/schema/protocol file, source origin and SHA-256, and the
   explicit consumer ownership/exclusions. Rust, Python and TypeScript loaders
   use that artifact from a repository-relative or explicit root, independently
   of process CWD. Remove tracked snapshot copies. A deterministic test-only Rust
   projection may be emitted into build output for no_std unit tests that currently
   embed copied literals; it must read the authoritative fixture data and cannot
   call the Rust implementation to manufacture expected answers. Handwritten
   primitive known answers that are independently sourced remain separately
   attributed, not overwritten by generated expectations.
2. **Independent expected results.** Preserve Python/libsecp256k1 verification,
   checked-in protocol expected values and official external vectors. Generation
   is explicit maintenance, never an automatic pre-test rewrite of expectations.
   Mutating a fixture, deleting/adding an unclassified fixture, changing a pin or
   pointing a consumer to a stale snapshot must fail with a useful diagnostic.
3. **Real Rust workspace separation.** Root workspace contains the existing core.
   `apps/desktop-simulator` becomes an explicit standalone host workspace, depending
   on the shared core by path. Keep separate lockfiles, target directories and
   explicit toolchain manifests; both start at Rust 1.95.0. Preserve offline
   vendoring/checksums and avoid accidental std-feature unification in the embedded
   build. The embedded gate builds the actual core for
   `riscv32imafc-unknown-none-elf`; no placeholder app, SDK crate or Xtensa target is
   introduced. A future Xtensa app will need its own measured pinned toolchain.
4. **One client package surface.** `@nsealr/sdk` exposes documented browser and
   Node entry points, with the root explicitly platform-neutral. Internal modules
   remain workspace development units. Pack the SDK with required owned runtime
   code and declarations so its tarball has no unpublished internal dependency,
   source-worktree import, private signer, smartcard implementation or credential.
   Browser exports must bundle/run without Node-only modules. This is local pack
   verification; package ownership/publication remains a later coordinator-owned,
   concretely scoped release action.
5. **Existing functionality and honest gaps.** Retain Pi reference signing and
   adapters, Rust review/parsing/vector coverage and Bridge behavior, including
   the corrected S01 identity/queue cases and S02 secret/hash cases. Preserve
   explicit signing-disabled simulator behavior. Reusable approval defects remain
   S03 repair gates; existing code/tests do not authorize a production guarantee.
6. **One canonical plan.** In the isolated target only, atomically move
   `docs/restart/work-items.json` to `plan/work-items.json`; update validator default,
   live navigation/AGENTS/bootstrap/CI consumers and negative tests together. Keep
   one state file. Apply the closed-evidence migration rules below. A later
   coordinator-owned adoption must replay this move against then-current main
   without losing states.
7. **Bounded failure behavior.** Import refuses existing destinations, pin/tree
   drift, unlisted path collisions, unsafe paths/symlinks, missing rights records,
   undeclared deltas and dirty source use. No remote push URL is installed on the
   rehearsal. Every command records cwd, environment, timestamps, exit code and
   output hashes; any required failure keeps the result failing. No retry hides
   the first failure or silently changes a version/expected value.

### Closed evidence and current documentation

At inspected metadata candidate `b040f03`, closed task records contain 322 R00,
12 P01, 91 S02 and 8 A01 artifact references. All are under
`docs/restart/implementation/` except P01's `docs/restart/product-contract.md` and
`docs/restart/client-qualification.md`. This is an observation of that candidate,
not the final import inventory; include every additional closed task at the final
source pin, including subsequently integrated S01/E01/O01 evidence.

Preserve frozen evidence bytes and paths in the target. Do not make a reviewed
result manifest or embedded `evidence_paths` claim a newly edited file has its
old reviewed hash. Generate `plan/evidence-index.json` as a derived navigation and
equivalence index, not another status tracker. Each historical artifact entry
binds task ID, original full commit/path, Git blob/mode, SHA-256, current unchanged
artifact path, and pinned reviewed source reference. Audit all `result_artifacts`,
`result_manifest` contents, acceptance evidence paths, review/input/candidate
references, and relative links; the index must cover the complete referenced
closure, not just a top-level summary. Verify original and current bytes from
Git objects and the working tree. Keep the graph's artifact records valid.

Historical evidence is immutable reference material, not the current normative
contract owner. In the isolated target, current editable product requirements
move to `docs/product/contract.md` and `docs/product/client-qualification.md`.
Their initial content comes from the accepted P01 source with an explicit
source-equivalence record; subsequent changes receive their own review. The old
reviewed P01 bytes remain only as cited historical evidence. Current documentation
and generated navigation identify exactly one normative path for each contract
and point historical readers to the original reviewed commit. This is evidence
retention, not an old API/layout compatibility tree.

Repair links in current instructions/navigation. Preserve links embedded in
immutable evidence as historical text, inventory their original resolution and
provide pinned-source links from the generated evidence index so a reader can
browse the source at the reviewed commit. Do not rewrite frozen Markdown merely
to make an old relative link appear current. No placeholder, symlink, duplicate
task state or redirect copy remains at `docs/restart/work-items.json`.

Add focused negative tests for changed frozen bytes with an unchanged digest,
missing evidence closure entries, duplicate/escaping aliases, a wrong historical
commit/blob, dangling current links, a second live task graph, and a modified
current contract falsely attributed to the old review. Restoring the exact frozen
source must pass. The tests validate evidence equivalence and navigation without
pretending that provenance alone establishes product correctness.

## Reproducible sequence and evidence

Implementation will provide ordinary scripts under `tools/migration/`, a frozen
manifest, readable patches and a README. These commands are the proposed CLI
contract, not commands claimed to exist or pass in this preparation commit:

```sh
python3 tools/migration/rehearse.py prepare --manifest docs/restart/implementation/A02/inputs.json --source-root /absolute/authorized/sources --destination /absolute/absent/a02-runtime
python3 tools/migration/rehearse.py import --destination /absolute/a02-runtime
python3 tools/migration/rehearse.py verify-tree --destination /absolute/a02-runtime
python3 tools/migration/rehearse.py run --destination /absolute/a02-runtime
python3 tools/migration/rehearse.py verify-result --destination /absolute/a02-runtime
```

`prepare` verifies the finalized commit tuple and source licenses, records local
and remote commit/tag references, creates verified recoverable bundles in private
runtime storage, and checks every selected source blob. Public target origin is
the canonical public repository's pinned history, never a merge of private repos.
Record absent tags as an observed empty set, not inferred aliases. Bundles are
local recovery artifacts; publish only permitted manifest/evidence content.

Establish before-state coverage for all eight existing software CI suites and the
twenty-step lab integration on the final S01 tuple using the R00 runtime pins.
Independently reviewed exact final-S01 evidence may be reused only after checking
source commits/declared deltas, environment/tool versions, commands, case inventories
and artifact hashes for equivalence to this comparison. Record the exact approved
corrected helper overlay and a per-gate reuse/equivalence decision. Repeat affected
checks when source, environment, commands, cases or relevant concerns change;
missing or non-equivalent evidence requires fresh execution for that boundary.
The corrected provenance/default bootstrap boundary requires renewed independent
review and successful affected integration before import. Do not rerun unrelated
unchanged suites merely to create new timestamps. The baseline may include archived
smartcard tests for comparison without making them product gates. Preserve all
failures and classifications. Always execute the complete after-migration
acceptance below against the actual migrated candidate; historical evidence cannot
replace it.

`import` creates one exact-copy import commit and then separate declared migration
commits. Record `repository + commit + tag(s) + old path + blob/mode + SHA-256 ->
target commit/path/blob/mode`, with reason for exclusions. The initial exact-copy
tree comparison must cover every selected blob before adaptation. The final
comparison accepts only manifest-listed moves/patches/removals and records their
pre/post hashes. It must reject missing, additional or changed unlisted content.
No working-tree copy from another author's checkout is an import mechanism.

Pin Python 3.12.15, Node 24.22.0, npm 11.19.1, pnpm 10.33.4, Rust 1.95.0,
cargo-deny 0.20.2 and cargo-llvm-cov 0.9.1 through the existing R00 hashes/installer.
Keep Node frozen lockfiles and Python wheel constraints. Reusing an installed R00
runtime requires verifying its manifest and recording reuse; do not claim a cold
bootstrap from reuse. Use separate clean product output/cache directories. Avoid
duplicating all tool archives or hardware CAD caches; record free space and stop
before exhausting disk. No new orchestration service is needed.

After migration, `run` executes these gates from the target, with exact environment
and tool versions in its command log:

| Boundary | Required acceptance |
| --- | --- |
| Graph/evidence | Existing validator and all negative tests using `plan/work-items.json`; root `make test` after live-path updates; no second canonical graph. |
| Core and host Rust | Format/clippy/default+std tests, desktop simulator vector replay/completeness, embedded core build, dependency/license audit, all existing coverage and reproducibility gates. Run host/core workspaces separately; preserve denominator/threshold or document a reviewed mathematically equivalent split. Carry S02 no_std/final-link/official-vector acceptance forward where affected. |
| TypeScript | Frozen install; build/typecheck/full retained Vitest tests; CLI and service tests; readme/API freshness and reviewed API output; package registry; browser import/bundle; extension security; public imports; release artifact safety; isolated packed SDK Node/browser/type consumers. Keep S01 negative identity, replay/cancellation and queue/terminal-error tests. |
| Python/Pi | Install pinned dependencies; execute all retained Python unit tests, compile and dependency checks; GPIO/camera/display mock and safe-probe tests; independent event/signature/review/recovery comparisons. No Rust/SDK-derived expectation generator. |
| Contracts | Original independent verifier and negative tests adapted to the active artifact; complete inventory/source-hash checks; all retained schemas/vectors classified. Verify two differently located checkouts resolve the same artifact. |
| Integration | One uninterrupted invocation of the adapted integration recipe below; per-step before/after mapping and all remaining behavioral assertions preserved. Test package consumers outside the source workspace. |
| Topology | Build/run the product in an isolated tree with no sibling board-sdk/hardware/private source checkout. Existing Pi path and RISC-V core work without custom hardware source. This proves current graph independence only. |
| Reproduction/recovery | Repeat deterministic source assembly into a second absent destination and compare tracked tree hashes. Independently verify bundle restoration of each selected source commit and the rehearsal candidate; preserve the successful restore log. |

The tool must retain before/after test names, category/case inventories and
disposition records, not just aggregate pass counts. A deliberately removed check
names its source file/test/case, reason, affected claim and replacement assertion
where applicable. Failures inherited from source remain visible; do not weaken
security tests or omit suites to match a desired green summary.

## Integration-step disposition

The numbered source rows are the order in pinned lab `Makefile:integration-pnpm`.
Final commands will be captured verbatim with adapted path arguments. Retained
scripts and their corresponding regression tests are the lab import allowlist;
private taxonomy/docs and retired-smartcard scripts are excluded.

| Step | Original check | Target obligation |
| --- | --- | --- |
| 1 | `check_fixture_snapshots.py` | Replace duplication comparison with authoritative-artifact provenance, completeness and consumer-root checks; keep tamper/missing/extra/pin failure tests. |
| 2 | `integration_feature_matrix.py` | Replace fixed five-family/private-prose assertions with the accepted owner/profile boundary and honest existing-component status; retain useful feature consistency assertions. Record every removed old-label/taxonomy assertion. |
| 3 | `integration_companion_fixtures.py` | Retain independent fixture loading/validation for every active case. |
| 4 | `integration_companion_policy_cli.py` | Retain host-policy validation; no elevation to device approval. |
| 5 | `integration_companion_nip46_cli.py` | Retain corrected metadata-v1 and transport/user identity boundary. |
| 6 | `integration_companion_serial_frame_cli.py` | Retain framing/invalid-input behavior. |
| 7 | `integration_companion_service_context.py` | Retain service session/origin/client context. |
| 8 | `integration_companion_route_identity.py` | Retain route identity; remove retired smartcard routes with explicit unsupported-route rejection. |
| 9 | `integration_companion_sdk_browser.py` | Retain browser behavior using the single packed SDK consumer. |
| 10 | `integration_browser_extension_package_plan.py` | Retain extension packaging assertions against the new paths. |
| 11 | `integration_browser_extension_package_build.py` | Retain actual package build and manifest checks. |
| 12 | `integration_browser_extension_origin_permission_cli.py` | Retain origin permission isolation. |
| 13 | `integration_browser_extension_origin_review_control.py` | Retain origin review binding and controls. |
| 14 | `integration_browser_extension_origin_approval_control.py` | Retain host approval routing; never claim device consent. |
| 15 | `integration_browser_native_messaging_manifest.py` | Retain browser/host manifest boundary. |
| 16 | `integration_hardware_validation.py` | Run as a separate external-hardware regression against the pinned hardware source; preserve assertions, but remove it as a prerequisite of the self-contained product suite. Do not import CAD into nsealr. |
| 17 | `integration_raspberry_hardware_probe.py` | Retain safe software probe; identify physical tests as unexecuted. |
| 18 | `integration_smartcard_protocol.py` | Deliberately retire from active software acceptance; source/archive history remains recoverable. |
| 19 | `integration_vault_companion.py` | Retain complete request/review/sign/verify differential flow and negative/error behavior using independent Pi reference implementation. |
| 20 | `integration_smartcard_companion.py` | Deliberately retire along with smartcard consumers; require absent public exports/commands and unsupported-route rejection. |

This yields seventeen product integration obligations plus separate hardware
regression, rather than silently relabeling a truncated recipe as the old twenty.
No claim is made for live relays, installed-browser sessions, physical camera/
GPIO/display approval, entropy, SE lifecycle or manufacturing. These remain
explicitly unexecuted gates with their existing owners and resources.

## Interoperability, notices and rollback

Prepare (do not publish) source-repository README notices pointing to the intended
new paths and a migration map. Identify the canonical repository by identity;
never recreate the `firmware` slug or change public visibility. The coordinator
applies notices and archives only as a separately scoped later action after final
tree/consumer review and integration under the existing authorization.

Maintain an external-Nostr interoperability plan tied to named NIP-01/BIP340,
NIP-07/NIP-46 and supported encoding/crypto revisions already captured in source.
Existing fixture tests prove local behavior. Later named client/version, relay,
browser and device sessions must exercise request -> actual device review ->
one-use authorization -> independently verified identity/response. Do not call
the inherited host NIP-46 client a hardware-backed signing server. A02 must not
weaken wire validation to retain an old experimental fixture.

Rollback is local and reversible: source repositories/main are untouched; retain
private recovery bundles and their hashes; preserve the exact import commit,
transformation commits, final candidate bundle and logs. On a failed gate, stop
the result at failure and keep evidence. Discard only the owned disposable target
after verifying its identity and preserving evidence; reproduce it from manifest
and bundles into another absent destination. No force push/reset or canonical
repository deletion is part of rollback. Future coordinator-owned adoption needs
its own reviewed revert and navigation procedure; this rehearsal does not perform
it.

## Review and stop conditions

Before implementation: distinct spec approval and the reconciled assignment.
Before import: the final repaired S01 provenance checker, exact corrected helper
pre/postimage and patch manifests, refreshed coherent bootstrap tuple/default,
renewed distinct review and successful affected integration; complete selected-file
rights/privacy record, exact import map and original-vs-new gate disposition.
Snapshot byte equality and earlier helper/snapshot candidates alone do not meet
this prerequisite. Stop affected work
on missing source object, unreviewed changed input, unexplained fixture mismatch,
unresolved rights, undeclared delta, non-reproducible import or failing required
behavior. Missing future device/SDK implementations are recorded limitations,
not grounds for inventing scaffolding or making hardware block unrelated software.

Delivery includes scripts/manifest/patches, exact import and final tree reports,
before/after command logs, inherited-failure/removal ledger, artifact hashes,
local recovery proof, draft notices and distinct final review. The coordinator
owns task-state closure, PR integration and post-integration CI. This preparatory
brief does not mark A02 running, verified or integrated by itself.
