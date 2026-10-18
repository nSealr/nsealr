# Explicit project pause — 18 October 2026

**Development is suspended at the maintainer's explicit request. Resume only when the maintainer explicitly asks.** Do not start research, agents, builds, models, hardware operations or integration merely because a task is eligible. A subtask's reference to a coordinator instruction is subordinate to this project pause.

This is a durable checkpoint on `coordination/pause-2026-10-18`, based on public main `f2ef70f522af4977e15f81554a8c6eadcdbe8097`. Main remains unchanged to preserve the A02 source freeze. The same-path task graph in this branch records the proposed reconciliation of actual assignments and paused WIP; it is not a second adopted roadmap. Do not merge this checkpoint blindly over a future A02 layout. The existing main graph remains the adopted graph until reviewed reconciliation. No task or release is declared complete by the pause.

The enclosing Git commit identifies this handoff. Local checkout: `/home/tux/nsealr/.restart-tools/goal/pause-2026-10-18`. The coordinator sets the platform goal to `paused`, verifies the returned state, then stops; the document does not run a scheduler. Goal thread: `01a13411-3e17-7dc0-bae8-61a3b5dafdcd`.

## Integrated foundation and source mains

Seven foundation tasks are integrated: R00, P01, S01, S02, E01, A01 and O01. Their frozen evidence and acceptance remain unchanged. There are 47 tasks; this checkpoint records seven assigned incomplete tasks and 33 planned tasks, with no new acceptance closure. All 16 physical-resource records remain unknown; all five release gates remain planned. No device, PCB or product release is qualified.

| Repository / local directory under `/home/tux/nsealr` | Default branch checkpoint |
| --- | --- |
| `nSealr/nsealr` / `firmware` | `f2ef70f522af4977e15f81554a8c6eadcdbe8097` |
| `nSealr/hardware` / `hardware` | `340697d6713a671e9e01b0dc874ec999ab071601` |
| `nSealr/board-sdk` / `board-sdk` | `043e64ceb745a323f9a332cc02fae2993388fabe` |
| `nSealr/companion` / `companion` | `678796900e462f5504e47fe934e2e5f23d85824f` |
| `nSealr/specs` / `specs` | `45f8b6ff1123f3f55be4ce457fd1008e91043cc2` |
| `nSealr/raspberry` / `raspberry` | `d1534d9dcfba8fe4a35cea2ed3529e32a5003dc6` |
| `nSealr/website` / `website` | `9cec39a89d6a2d2cc5747b8aae9d4b47a52eb7cd` |
| `nSealr/.github` / `.github` | `67dad0dfea9ced6b822454f504b26c2a04f43021` |
| `nSealr/smartcard` / `smartcard` | `ec5da94a05882122e8a794f55f1af3f96a95c696`; already public archived |

The canonical public repository identity/stars are preserved. Do not recreate the old `firmware` slug or toggle visibility. Private `workspace`, `lab` and legacy hardware histories stay private. Source repositories were not archived during shutdown; A02 archive admission is incomplete.

## Published incomplete work

All paths in this table are relative to `/home/tux/nsealr/.restart-tools/goal/`. Task-specific handoffs are in the corresponding repository at the exact commit.

| Task | Repository, branch, worktree | Exact published checkpoint |
| --- | --- | --- |
| A02 | `nsealr`, `restart/a02-rehearsal`, `a02` | `52288f8f31237c7f96a22caf63d07c48621012c0` |
| S03 | `nsealr`, `restart/s03-authorization`, `s03` | `2d7d465a291c4d4a1324d90595fc45a2fdbefca5` |
| T01 | `nsealr`, `restart/t01-capabilities`, `t01` | `03c2616518d6d9a32fe5cc9a945624a72cd32ac0` |
| P02 | `nsealr`, `restart/p02-compatibility`, `p02` | `8525ce01ad02466b78654e31c672774c99d256da` |
| S04 | `nsealr`, `restart/s04-custody`, `s04` | `e823fecfd4bdc5d2eb0e4b31aedc3ac66cfabe36` |
| H01 | `hardware`, `restart/h01-manuals`, `h01` | `40cdb6c519285ab81922b382440ef6c02a6fc89a` |
| B01 | `board-sdk`, `restart/b01-sdk`, `b01` | `8377f9264ca0c426dad0d79578c01be2e1d32509` |

Coordinator specification/acceptance receipts are pushed in `nsealr` branch `review/next-specifications` at `89a7af0ce18a59ece959a142aba47ebdbe134d85`, worktree `spec-reviews`. No counterpart task branch has been merged merely to stop.

**A02:** read `docs/restart/implementation/A02/PAUSE-HANDOFF.md` and `execution/pause-checkpoint.json` on its branch. Product source is an isolated, clean Git repository at `a02/tools/migration/.runtime/rehearsal-01/repository`, HEAD `2bb10013c9fcaab04c544abcff3f480243200da1`, tree `16aa38a3866d28bcbaf7dfd973247ce87823c38e`; it has no remote. Corrected cold full `make -k ci` passed before the pause, with no post-suite source drift. This is local software evidence, not final migration review or main CI. The checkpoint bundle is `.runtime/pause-checkpoint-01/candidate-2bb10013.bundle`, SHA256 `506fbdea69f800be234917ec61df4435b0b1d14908ad9919702a8a00f3fe6f6a`; bundle verification passed, its restoration has not run. Full replay/restoration last covered 36 patches at `75d08ba7ae82a2e82f8c35ad2e730eab84215395`; the current 37th `pnpm run ci` patch still needs replay. Documentation transform `85e28b9` is committed but unapplied. Final source/rights map, notices, failure narrative, interoperability handoff, final distinct review and coordinator adoption remain open.

A02 preserves the transient DNS bootstrap failure, the real `pnpm ci` entrypoint failure and corrected full run, original restore-branch failure and corrected older restore, prior migration failures and the inherited cargo-deny index/yanked-status limitation. All original 716 runnable TS cases have explicit treatment: 691 afterward pass, 25 card cases retire; unchanged live-relay skip is separate. Cases/claims must be read with their per-file patches, not counts alone. Pi 150, contracts 90, selected helpers 115 and 21 private-origin guardrail replacements have their executed records; no installed-browser/device proof follows from those tests.

**S03:** exact source has bounded independent PASS in `b03475ccf4a057c7771065126002f2e4e056d28d`, `docs/restart/implementation/reviews/S03-security/report.json`. Draft [PR23](https://github.com/nSealr/nsealr/pull/23) stays held. Before integration, correct the three misleading diagnostic comments in `qr_flow.rs`, adapt the actual A02 workspace/artifact paths and obtain affected review/tests. Never overwrite the migrated tree with the old branch. Production signing remains disabled; real signatures exist in a private test backend. Preserve original scalar before k256 normalization; equal x-only public keys do not prove equal recovery bytes.

**T01:** preparation `03c2616` passed coordinator review `8d3a0acf2daa1a6b3b836b6d2241b99a8477ad8a` on `review/next-specifications`. No product implementation started. New wire contract proposal is signing.v2/numeric2; artifact inventoryv1 is a different version. Before writing code, pin actual adopted A02 plus S03 input/layout/API and scope. No descriptor/manifest/readiness flag may mint authority.

**P02:** all five documentary planning criteria passed review `d9305d811f3adc889ba799b63e4fc95f9c1876f2` at author candidate `50d32a08e3e5fd245b4c8c8179c3619874b66076`; delivery adds review files byte-exact. [PR28](https://github.com/nSealr/nsealr/pull/28) stays draft. There are 31 per-profile scenarios and four opt-in research scripts; no client build, installed browser, real device, pilot or market test was performed. Reconcile actual A02 normative paths and graph before adoption. Issues [26](https://github.com/nSealr/nsealr/issues/26) (Firefox service-worker-only packaging) and [27](https://github.com/nSealr/nsealr/issues/27) (Coracle client-generated nostrconnect legacy-ack source risk) remain C01/P02-C02 qualification work; neither is a reproduced runtime exploit here.

**S04:** read `docs/restart/implementation/S04/PAUSE-HANDOFF.md`. All seven criteria remain incomplete and final crypto/spec review is pending. TM-HMAC-1 is a failed reusable-Board proposal, not an accepted architecture or a claim that all Trust M designs have the same limit. The 2048-use recommendation, actual 32-bit counters/endurance, owner/vendor roots, Safe7 factory provisioning and incomplete cyclic reset alternatives are distinguished. The new `evidence/explore_reset.py` is committed WIP and **was never executed**. NXP DeleteAll public middleware does not prove exact applet, torn-reset or owner-SCP behavior; required APDU/errata access remains unresolved. TROPIC advisory/firmware applicability and physical remedies remain unproved. Do not select parts, waive source gaps or adopt a dual-SE claim by analogy.

**H01:** read `docs/restart/H01/PAUSE-HANDOFF.md` and `pause-state.json`. Source checkpoint `136d9ccea3422fa47e530b41c2fb2720a2a090a4` preserves already-read findings and the VIQ package correction. Latest distinct limited review `9d5ed3baf936157a26b55bf42e51da4ce6d240c2` covers older `e39015a`, not these newer configurations. Existing `result.json`/`handoff.md` intentionally remain historical and do not bind current source. Two U585/S3 host paper configurations plus the G9 comparison and six documentary signoff rows are unfinished. Native RM0456Rev7, USB originals and selected module/controller bodies are available privately; retrieval is not full reading or part admission. Preserve the corrected SMPS pin interpretation: VIT6Q lacks PC4/PC5; PA7/PB0 remains a proposal with branch/boot checks. Display identity/power, USB current/disconnect, driver bounds, reset/entropy and owner lifecycle remain open. No host, panel or bench procedure is admitted.

**B01:** preparation `c82b065f30309c5a8f3db3e81f8addfce7b8ad30` passed review `09bd394a6fc1502f192ee84cd99ad6ceb5e40f07`; review copy `779d9a7d1114dcbdcb7eaae1f39af0ef2314add5`, coordinator admission `8377f9264ca0c426dad0d79578c01be2e1d32509`. Read `docs/restart/B01/{brief.md,source-audit.json,acceptance-plan.json,preparation-acceptance.json}` and `preparation-review/`. Actual four documentary decision outputs have **not** been written. No crate, driver or dependency is selected. Root's private input survey is `b01-research/`: five official checksum-verified Rust crates, nine source-body correspondences and a preserved stale crate-level repository/404 correction. It is preparation knowledge, not API adoption. Literal electrical pinning remains H04-dependent, so B01 cannot close on a schema or placeholder.

## Other retained review and recovery evidence

Hardware verifier fix remains on `fix/checkout-independent-verification` at `d407d8ec93d5c43aa0045390c80bfcfcf64c9854`, worktree `hardware-verifier`; [draft PR1](https://github.com/nSealr/hardware/pull/1) is held for the A02 source freeze. Distinct review `26585a1d640726771f1409625f82f82016bf7c25` covers the actual checkout-name/license/directory enforcement fix. It does not qualify electronics. Do not merge or archive anything during pause.

Historical closed-task evidence remains under `docs/restart/implementation/`; reviewed task outputs and failed logs stay in their owned branches. The private `workspace` archive retains dated publication/research receipts under `docs/restart/2026-10-18-execution/`; its pause capsule preserves the private complete worktree/process inventories and root's source survey. It is not a second plan. A02 workspace recovery04 covers exact `aa4b286436e05a8c543d2e7f0a8271253807a370`; later pause metadata is a later Git commit, not covered by that older bundle. Refresh the protected all-refs backup before eventual archival.

## Files deliberately outside public Git

All owned active author/reviewer worktrees were clean after their final checkpoint. The initial complete private inventory covers 60 registered worktrees. The detached `h01-ci/hardware` checkout at `4d50d155c994e8e770d2b868c371cc04b646ad35` retains three untracked generated Python bytecode files in `scripts/__pycache__/` and `tests/__pycache__/`; these are build caches, not authored changes. They are deliberately uncommitted. No useful source diff is hidden there.

Ignored runtimes, build outputs, original manufacturer PDFs/extractions/drawings, protected bundles and raw research captures stay in their owned private filesystem directories. They are not discarded or publicly uploaded. Important roots: `h01-private/`, `s04-private/`, `manual-retrieval-root/`, `b01-research/`, and `a02/tools/migration/.runtime/`. Their source manifests/hashes and task handoffs identify what can be reacquired. This is not a claim that every local cache is remotely backed up. Never commit all ignored files or private histories wholesale.

The parent integration directory is not a Git repository. Its local `/home/tux/nsealr/AGENTS.md` now has a pause guard pointing here; that intentional local metadata change and exact after-image are preserved in the private pause capsule. It is not an uncommitted product source change.

## Shutdown and resume controls

The three active specialist authors stopped and published their handoffs; earlier agents were already idle/completed. No goal-owned development process, child agent, model or daemon remains. The two inherited push CI runs 39162763207 (S04) and 39162707278 (A02) were cancelled for explicit pause; partial logs are preserved privately and cancellation is not a test pass/failure. No scheduled agent service was installed. The pause commit uses `[skip ci]` to avoid launching fresh checks for an unmerged metadata checkpoint; this does not waive any future merge gate. PRs remain open/draft and no auto-merge should be enabled.

After the user explicitly resumes:

1. Verify actual goal authorization, repository visibility, worktree status and remote heads against this checkpoint. Read the task-specific handoffs before any build/model/fetch. Recheck that no other actor has advanced source mains. Missing private resources are unknown, not assumed unavailable.
2. Keep one task graph. Reconcile this pause proposal with actual main and A02's atomic move to `plan/`; preserve all closed-task bytes and criteria. Do not treat this metadata revision as an adopted product change.
3. Resume A02 from its exact checkpoint: inspect the prepared one-file guide correction; run only its affected checks if applied; replay/restore the full resulting patch series into an absent destination and audit all objects. Source changes or unresolved failures require the appropriate affected acceptance; do not repeat every old suite merely to make timestamps fresh.
4. Complete final migration reports and distinct exact review, then normal protected integration and actual main CI. Before any source archive, verify dispositions/navigation/current recovery backups. No force/admin bypass.
5. Reconcile and integrate S03 with its required comment fixes/affected review, then authorize T01 on actual interfaces. Resume H01/S04/B01 within their accepted scopes and source dependencies; physical/SE/custody uncertainty must not become an optimistic flag. P02 integration remains documentary; actual browser/device/optical/pilot gates stay open.

No development resumes from a timer, eligible-task status or coordinator initiative alone. Await the maintainer.
