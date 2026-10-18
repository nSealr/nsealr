# A02 pause checkpoint

The user explicitly paused work on 2026-10-18. Stop here. Resume only after an
explicit new coordinator/user instruction. This checkpoint is not A02 completion,
final review, integration, archive approval or physical qualification. The
canonical task graph and frozen main inputs were not changed.

## Exact state

- Author worktree: `/home/tux/nsealr/.restart-tools/goal/a02`.
- Author branch: `restart/a02-rehearsal`. Last tooling commit before the pause
  evidence checkpoint: `0385cf9b0edaa402f02f6acf4e50429d3dd32007`.
- Isolated product: `tools/migration/.runtime/rehearsal-01/repository`.
- Product HEAD: `2bb10013c9fcaab04c544abcff3f480243200da1`.
- Product tree: `16aa38a3866d28bcbaf7dfd973247ce87823c38e`.
- Product tracked status is clean; its only branch is `rehearsal`. It has no
  remote or push URL. Installed dependencies, build outputs, prior failed runs,
  source recovery and private records remain in the ignored owned runtime.
- The [37 ordered patches](../../../../tools/migration/patches/series.json) bind
  declared preimages, postimages, modes, exact patch bytes, trees and commits.
  Reuse these frozen patches, not mutable earlier authoring templates.
- A protected checkpoint bundle is at
  `tools/migration/.runtime/pause-checkpoint-01/candidate-2bb10013.bundle`,
  SHA-256 `506fbdea69f800be234917ec61df4435b0b1d14908ad9919702a8a00f3fe6f6a`.
  Bundle creation and Git verification passed. Its restoration was not run at
  pause; do not attribute the earlier restoration proof to this newer candidate.

The machine-readable [checkpoint](execution/pause-checkpoint.json) records the
tree, refs, bundle, patch-series hash, process observation and completed cold
result. No tracked WIP source changes were left outside the checkpoint commits.
The prepared documentation transform is committed but unapplied.

## What actually finished before the pause

The new cold bootstrap and complete `make -k ci` finished at the exact product
HEAD above before the pause instruction arrived. The [full result](execution/cold-product-03/evidence/suites/result.json)
records `all_passed: true`, no failed command and no post-suite source change.
The [complete command log](execution/cold-product-03/evidence/suites/00-product-ci.log)
includes both Rust workspaces, device build, dependency audit, coverage and
reproduction, independent contracts, Bridge build/type/unit/packaging and
guardrails, Pi, helper tests and all seventeen product integration steps.
This is local execution, not hosted main CI or final migration approval.

Named execution and reconciliation also finished before the pause:

- [TypeScript correspondence](execution/bridge-named-execution-02/case-correspondence.json):
  all 716 original runnable identities are accounted for; 691 pass afterward,
  25 card cases retire, and the unchanged live-relay skip stays separate.
  There are 686 same-name identities and five renamed identities. Treatment
  counts are different: 668 ordinary adaptations, 16 active-contract adaptations,
  seven route/ack assertions and 25 retirements. A stable name is not a byte
  equivalence claim; the declared source patches still require final review.
- [Other case correspondence](execution/case-reconciliation-execution-01/case-correspondence.json):
  90 contract, 150 Pi and 115 helper cases pass; all 263 original Rust cases
  appear in the full output. The helper count includes all thirteen optional
  browser/serial helper-unit cases. All 21 opaque private-origin replacement
  controls executed, with four private taxonomy/prose obligations retired.
  Two selected private-prose assertions and twelve card-only Python/helper
  cases retire separately. Seventeen former copied-snapshot mechanism cases
  map explicitly to current authoritative-artifact controls, while eighteen
  consumer-scope cases remain with an explicit class rename.
- [Named Python execution](execution/named-python-execution-01/commands.json)
  includes 67 current repository controls and eight current bootstrap controls.
  The seven obsolete active multi-repository overlay controls have individual
  historical-preservation and current-replacement mappings. Original overlays
  were actually applied before the layout transition.
- [Separate hardware regression](execution/external-hardware-execution-01/commands.json)
  passed against selected hardware `340697d6713a671e9e01b0dc874ec999ab071601`,
  including the explicit product/profile alignment. It is not a product
  prerequisite and does not prove physical hardware availability.

The earlier [second assembly and restoration](execution/rehearsal-02/result.json)
reproduced all 36 then-existing patches and exact candidate
`75d08ba7ae82a2e82f8c35ad2e730eab84215395`: 7,923 allowed reachable objects,
327 commits, no other refs/remotes/alternates/hardlinks, equal restored objects
and tree. Patch 37 is the later explicit `pnpm run ci` fix. It is preserved in
the current patch series and checkpoint bundle, but has not yet undergone the
second-assembly/restoration replay.

Protected workspace recovery was refreshed after its metadata-only advance to
`aa4b286436e05a8c543d2e7f0a8271253807a370`. Its current refs were restored and
verified. The [safe summary](execution/workspace-recovery-04-summary.json) binds
the bundle SHA-256 `0e77222b814f3c9e2c41449df875ef0a1314eb390ffcbde1d46061db43432822`.
Raw bundles, refs and private source paths remain only in
`tools/migration/.runtime/workspace-recovery-04`. This is dated recovery, not
archival or a promise to include later refs.

## Preserved failures and limitations

- Cold run 01 failed on transient DNS for the hash-pinned Node download. The
  destination and [failed log](execution/cold-product-execution-01/00-cold-product-bootstrap.log)
  remain. No source or download-hash override was used.
- Cold run 02 correctly failed because `pnpm ci` invokes pnpm's reserved,
  unimplemented command. [Its full output](execution/cold-product-02/evidence/suites/00-product-ci.log)
  remains. Patch 37 changes the Makefile, current Bridge guide and recipe
  assertion to `pnpm run ci`; cold run 03 executes the full package script.
- The first candidate bundle restoration attempted to fetch into its checked-out
  branch and failed. [That attempt](execution/rehearsal-02/candidate-recovery/commands.json)
  remains; the corrected restore into an unused branch passed separately.
- The guide/receipt transformation initially used a relative target path after
  changing cwd. Its declaration and failure remain under
  `execution/declared-transformation-execution/final-navigation/`; the same
  declared postimages were checked and committed with an absolute target.
- Earlier meaningful migration failures remain in the exported execution
  directories; no failed observation was overwritten. A final explanatory
  failure ledger is still pending.
- `cargo deny` exits zero with inherited registry/index warnings. Its current
  output is retained; do not claim complete yanked-version coverage.
- Live relay, installed Chromium/Firefox, attached device approval/signing,
  camera/display/GPIO, manufacturing, production custody and physical entropy
  were not qualified. The retained Firefox service-worker manifest limitation
  remains C01/P02 work, not an A02 compatibility claim.

## Prepared but not applied

Author commit `85e28b9` adds
`tools/migration/repro_navigation_stage.py`. It corrects only the live
`docs/reproducible-build.md` guide: separate host/embedded commands and output
paths, the sole artifact location, and honest measured reproducibility limits.
The product still contains its older guide. The transform has not run, and no
post-pause documentation change or new suite was started.

The proposed continuation was to apply this bounded prose correction, prove the
exact one-file difference from full-tested `2bb10013`, and execute affected
docs/navigation checks. Any later semantic change needs its affected acceptance.
Do not claim that the current passing suite reviewed an unapplied future patch.

## Remaining work after an explicit resume

1. Re-read the coordinator's source-freeze decision and actual remote pins.
   Canonical core remains frozen at `f2ef70f522af4977e15f81554a8c6eadcdbe8097`.
   Never overwrite new merged code with this historical source tree. S03, P02,
   S04 and B01 branch work is not implicitly part of this target.
2. Decide/apply the prepared documentation correction and record its exact patch
   and affected validation. Preserve the original source and prior result.
3. Replay the full current series into an absent destination, compare its exact
   tree/commits, audit allowed objects, bundle and actually restore that candidate.
   `tools/migration/replay.py` and the protected approved privacy postimages are
   available. The last full replay is 36 patches, not the current 37.
4. Complete the final source-to-current-path/rights report, draft source notices,
   interoperability handoff, final failure/removal narrative and reviewed
   acceptance report. The admitted selected-file rights/map and individual
   transformation records already exist; no full final report is claimed here.
5. Reconcile actual final source/evidence hashes, current dated backups and
   final public evidence export. Obtain a distinct review of the exact final
   candidate, then hand it to the coordinator for normal reviewed adoption,
   canonical graph reconciliation and actual main CI. No source archival,
   registry publication or canonical main mutation is authorized by this
   checkpoint itself.

Useful resume commands are documented in [the tooling README](../../../../tools/migration/README.md).
Every replay destination must be absent. Before running them, verify the current
source freeze and explicit resume authorization; this file schedules no job.

## Process shutdown

The last full-run tool session was `18521`; it had exited zero before the pause.
The preceding sessions `29385` (failed overall cold run 02), `80503` (DNS-failed
bootstrap), `80241` (first restore failure), `22435` (corrected restore), `93084`
(named Python execution), `94486` (push), `35842` (focused controls), and `80715`
(earlier push) had all already exited. No command was interrupted or left running
at pause. The checkpoint's `/proc` observation found no owned process. No
background job, child agent, queued development command or automation was created.
Only evidence export, bundle preservation, this handoff and checkpoint publication
were performed after the explicit pause.
