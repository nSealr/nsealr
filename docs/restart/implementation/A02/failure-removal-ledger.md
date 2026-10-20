# A02 failure and removal ledger

This ledger explains the 30 nonzero execution observations in the
[complete machine index](failure-observations.json). Original commands, logs,
exit statuses and digests remain unchanged. A wrapper and its inner command can
describe the same failed run; neither is discarded. Corrections below are exact
numbered [patches](../../../../tools/migration/patches/series.json), followed by
the named passing execution. The final uninterrupted
[cold product run](execution/cold-product-03/evidence/suites/result.json) passed
all product commands at `2bb10013`; the current documentation-only differences
and affected gates are [explicitly bound](execution/model-policy-execution-01/result.json).
No failed run is relabeled successful.

| Failed observation (index log path) | Cause and correction | Passing execution |
| --- | --- | --- |
| `artifact-execution-01/04-independent-contract-verifier.log` | Moved capability contracts still asserted old `hardware`/`firmware` source owners. Patch 5 reconciles the integrated owner assertions; it does not claim hardware qualification. | [Artifact execution 02](execution/artifact-execution-02/commands.json), independent verifier |
| `artifact-execution-02/02-retained-contract-cases.log` | Two rejection probes depended on the removed card route and acknowledgement text. Patch 6 uses retained grant/acknowledgement inputs and checks their rejection at the active boundary. | [Artifact execution 03](execution/artifact-execution-03/commands.json), retained contract cases |
| `artifact-execution-03/03-pi-full-ci.log` | A retained Pi policy documentation assertion opened an absent moved component README. Patch 7 adds actual Pi navigation and preserves the manual-route assertion. | [Pi execution 02](execution/pi-execution-02/commands.json) |
| `rust-projection-execution-01/01-projected-workspace-unit-and-vector-tests.log` | The data projector did not map the retained `normal` review style and raised `KeyError`. Patch 11 completes the existing style mapping and formats declared Rust source; no expected cryptographic answer is computed. | [Rust projection execution 02](execution/rust-projection-execution-02/commands.json) |
| `rust-full-execution-01/01-complete-rust-ci.log` | Generated grant data used single-element loops, rejected by the unchanged Clippy gate. Patch 13 emits the selected elements directly. | [Rust execution 02](execution/rust-full-execution-02/commands.json), Clippy and tests pass before its later audit-option failure |
| `rust-full-execution-02/01-complete-rust-ci.log` | Host `cargo deny` placed `--config` after the subcommand, which this pinned version rejects. Patch 14 places it before `check`. The separate registry/index warnings remain visible. | [Rust execution 03](execution/rust-full-execution-03/commands.json), audit, coverage and reproduction |
| `bridge-layout-execution-01/03-bridge-typecheck.log` | A test still supplied owner `firmware` after the active type became `nsealr`. Patch 16 updates the owner assertion and active solution discovery. | [Bridge runtime execution 02](execution/bridge-runtime-execution-02/commands.json), build; complete cold typecheck |
| `bridge-runtime-execution-01/03-full-retained-vitest-discovery.log` | The fixture loader compared serialized object order and stale extension build paths remained. Patch 17 preserves exact JSON value/type/member/array semantics independent of object-key order and repairs the paths. The first follow-up still exposed the separate card assertions below. | [Bridge retirement execution 02](execution/bridge-retirement-execution-02/commands.json) and final cold suite |
| `bridge-runtime-execution-02/02-full-retained-vitest-discovery.log` | Remaining tests referenced deliberately removed card files/commands, old owner/family lists and a changed general policy-route-mismatch fixture. Patch 18 retires only card behavior and adds named active rejection controls; patch 19 fixes the retained policy semantics. | [Bridge retirement execution 02](execution/bridge-retirement-execution-02/commands.json); [case map](execution/bridge-named-execution-02/case-correspondence.json) |
| `bridge-retirement-execution-01/03-retained-and-replacement-cases.log` | Eleven assertions exposed a real route-dispatch gap, mismatched policy fixture decision and overly specific rejection wording after card removal. Patch 19 checks retired routes before dispatch, reconciles the retained policy values and checks active parser rejection. It preserves object-value drift negatives. | [Bridge retirement execution 02](execution/bridge-retirement-execution-02/commands.json) |
| `sdk-package-execution-01/02-bundled-sdk-build.log` | Declaration relocation truncated the numeric package identity `nip46` to `nip`, producing a forbidden dependency. Patch 21 preserves numeric identities. | [SDK package execution 02](execution/sdk-package-execution-02/commands.json), build and isolated tarball consumers |
| `bridge-api-execution-01/01-consumer-smoke.log` | The bundled SDK emitted an external `@noble/ciphers` import without declaring that direct runtime dependency. Patch 24 declares the exact owned runtime dependencies and rejects workspace-hoisting assumptions. | [Bridge API execution 02](execution/bridge-api-execution-02/commands.json), consumer/examples smoke and browser bundle |
| `bridge-api-execution-02/11-browser-extension-security-check.log` | The previous manifest guard assumed a facade with only indirect dependencies. Patch 25 permits only the exact four reviewed dependencies/versions needed by the bundled owned runtime; facade signing-import restrictions and bundle exclusion remain checked. | [Bridge API execution 03](execution/bridge-api-execution-03/commands.json), extension security and public imports |
| `bridge-api-execution-03/04-release-artifacts-safety.log` | A retained release-safety probe invoked the old script path and therefore saw module-not-found instead of the intended output guard. Patch 27 fixes the consumer path and retains both safety and pack smoke controls. | [Integration layout execution 02](execution/integration-layout-execution-02/commands.json) |
| `integration-layout-execution-01/01-all-selected-helper-unit-cases.log` | One optional browser helper imported the obsolete `scripts` owner; another test expected the npm fallback even when pinned pnpm was installed. Patch 27 fixes module ownership and accepts the actual pinned command branch, preserving all thirteen optional-resource helper cases. | [Integration layout execution 02](execution/integration-layout-execution-02/commands.json), all helper cases and seventeen integrations |
| `product-boundaries-execution-01/01-production-boundaries.log` | A lexical custody guard mistook validated projection of declared secretless metadata fields for a production signing-custody claim. Patch 29 keeps explicit forbidden-claim negatives while separately validating that projection. | [Product boundaries execution 02](execution/product-boundaries-execution-02/commands.json), production and negative controls |
| `product-boundaries-execution-02/03-active-guides.log` | Current guides still advertised the removed `smartcard-sim-sign` command. Patch 31 removes active card instructions and reconciles current product/artifact paths; historical evidence remains frozen. | [Current product execution 01](execution/current-product-execution-01/commands.json), active guides |
| `current-product-execution-01/04-contract-oracle.log` | Running moved contract tests from the product root resolved an unrelated `scripts` namespace. Patch 33 runs the contract gate from its actual owner directory as part of complete CI. | [Product CI execution 01](execution/product-ci-execution-01/commands.json), gate placement and contract oracle |
| `bridge-named-execution-01/02-named-typescript-after-cases.log` | The rejection assertion expected stale acknowledgement wording; Commander printed the intended unknown-command rejection to stderr and exited the case collector. Patch 34 binds the current refusal text and captures command output without treating expected rejection as a runner failure. | [Bridge named execution 02](execution/bridge-named-execution-02/commands.json), named cases and exact correspondence |
| `intake-execution-01/00-all-migration-controls.log` | Six synthetic restricted-intake tests fetched into their unborn checked-out branch, rejected by Git before real import. The corrected sequence initializes an unused intake branch before fetching. Actual intake was deferred until all 43 migration controls passed. | [Intake execution 02](execution/intake-execution-02/commands.json), controls then initial import |
| `declared-transformation-execution/final-navigation/00-stage-declared-paths.log` | The transform retained a relative repository path after changing cwd. Its exact proposed pre/postimages were preserved; recovery stages and commits those same bytes with an absolute target. | [Navigation recovery](execution/declared-transformation-execution/final-navigation/recovery/commands.json); exact replay |
| `cold-product-execution-01/00-cold-product-bootstrap.log` | Temporary DNS failure blocked the hash-pinned Node download. The failed destination remains; a fresh absent destination succeeded with unchanged URL/hash verification and source. | [Cold product execution 03](execution/cold-product-execution-03/commands.json) |
| `cold-product-02/evidence/suites/00-product-ci.log` and `cold-product-execution-02/01-complete-cold-product-ci.log` | Inner and outer records of the same run: `pnpm ci` selects pnpm's reserved unimplemented command. Patch 37 changes the Makefile, current Bridge guide and recipe assertion to `pnpm run ci`. | [Cold product execution 03](execution/cold-product-execution-03/commands.json), uninterrupted complete product CI |
| `rehearsal-02/candidate-recovery/03-restore-selected-branch.log` and `source-replay-execution-01/00-second-source-assembly-and-recovery.log` | Inner and outer records of the same restore: fetch targeted its checked-out `rehearsal` branch. The corrected restore initializes branch `intake`, fetches `rehearsal`, then checks it out. | [Historical corrected restore](execution/rehearsal-02/candidate-recovery-02/result.json); [current 39-patch restore](execution/rehearsal-04/result.json) |
| `resume-navigation-execution-01/02-current-guide-claims.log` | Node `-e` supplies no script filename at `argv[1]`; the checker attempted to convert `undefined` to a path. The corrected probe supplies a synthetic script argument. Product bytes did not change. | [Guide execution 02](execution/resume-navigation-execution-02/commands.json) |
| `final-package-validation-01/00-final-links-source-rights-failure-and-privacy-checks.log` | The new report checker treated Pi/contract case paths as product-root-relative. The first missing file was a Pi hardware-adapter unit test owned by `apps/pi`, despite its test filename mentioning hardware. The checker now resolves the explicit execution-group owner and verifies it against each admitted destination. Product source and recorded case map were correct. | [Final package validation 04](execution/final-package-validation-04/result.json) |
| `final-package-validation-02/00-final-links-source-rights-failure-and-privacy-checks.log` and `final-package-validation-03/00-final-links-source-rights-failure-and-privacy-checks.log` | The next check assumed all opaque replacement results used `source_file`/`source_sha256`; ten executed Python replacements use `path`/`sha256`. Filtering retired cases did not correct that schema assumption, so the third run preserved the same failure. The final checker handles both actual executed-result schemas and still checks every current source hash. No product change or rerun of the complete suite was needed. | [Final package validation 04](execution/final-package-validation-04/result.json) |

## Deliberate removals and preserved obligations

The [per-file source map](final-source-map.json) and [final tree](final-tree.json)
record every selected source, exclusion, duplicate and declared deletion. The
[named correspondence](execution/case-reconciliation-execution-01/case-correspondence.json)
and [TypeScript correspondence](execution/bridge-named-execution-02/case-correspondence.json)
record cases individually. These records distinguish a stable case name from
unchanged assertion bytes and never infer equivalence from equal pass counts.

- Active smartcard packages, fixtures, routes, public exports and commands retire
  under the accepted clean-break scope. Twenty-five original runnable TypeScript
  card cases, two contract cases and ten helper cases retire explicitly. Their
  original public histories remain recoverable. Five renamed TypeScript cases
  and seven route/acknowledgement assertions preserve active-boundary rejection;
  retired surfaces are also excluded from packed runtime and command inventories.
- The original twenty lab integration steps become seventeen product steps,
  one separately executed hardware regression and two retired card steps.
  Hardware is no product build prerequisite. No empty SDK scaffold or invented
  ESP32/P4 application counts as independence evidence.
- Two selected private-prose assertions and four opaque taxonomy/editorial
  obligations retire. Twenty-one meaningful private guardrail obligations have
  named executed replacements; private original bodies/addresses remain excluded.
  This changes the assertion mechanism while preserving the admitted obligation.
- Seventeen copied-snapshot helper mechanisms map to current authoritative-artifact
  controls. Eighteen consumer-scope cases remain under the explicit class rename.
  Seven old active multi-repository overlay bootstrap cases have separate historical
  preservation/current replacement mappings. The original S01 overlays were
  actually applied before the consolidated layout transition; their four selected
  source files are then removed by declared patches.
- Duplicate contract snapshots have one active owner at `protocols/contracts/v1`.
  The maps distinguish 498 surviving deduplicated counterparts from 24 duplicates
  of retired contracts. Rust projection copies committed expected data into build
  output; it does not regenerate expected cryptographic answers. Independent
  Python/libsecp256k1, TypeScript, official vector and handwritten verifier checks
  remain separate oracles.
- All 263 original Rust cases, 90 retained contract cases, 150 Pi cases and 115
  helper cases execute, including thirteen optional browser/serial helper-unit
  cases. TypeScript accounts for all 716 original runnable identities: 691 pass,
  25 retire. One inherited live-relay skip is recorded separately. Root controls,
  packed Node/browser/type consumers, artifact tampering and retired-surface
  negatives add current boundary proof; they do not replace a missing live session.

## Open limits

Both dependency audits exit zero with inherited registry/index warnings; an
explicit index refresh did not establish complete yanked-version coverage.
The [skip record](execution/cold-product-03/evidence/suites/skips.json) retains
live relay, installed browser and physical-resource limits. Firefox's retained
service-worker manifest limitation remains C01/P02 work. Physical review,
camera/display/GPIO, manufactured hardware, production custody and entropy remain
unqualified. A02 neither archives a source nor publishes a package nor closes a
release gate. Distinct review and coordinator adoption/main CI remain required.
