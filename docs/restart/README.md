# Current nSealr delivery

The milestone is connected USB-only S3 without SE or persistent vault, independent
session-only offline Pi/P4, shared Rust device engine and complete required
CLI/service/Bridge/browser/client/TypeScript SDK delivery. C01/C02, the agreed
catalog and NIP-44/NIP-17/59 remain in scope. Custom Board/embedded SDK remain
deferred; S04 stays terminally blocked.

## Verified result

Protected main 5686cbe60fe34ffd3478c707d804571096cd3a2d includes the real public
S3 CLI/service/USB flow and D01 feasibility
([PR57](https://github.com/nSealr/nsealr/pull/57), PR/main CI passed).
P4 public fallible entropy and exact-kit QP02 feasibility were integrated through
[PR58](https://github.com/nSealr/nsealr/pull/58), with PR/main CI passed.
These are component/feasibility results, not qualified device releases.

## Limits and blockers

- S3: ADC-183 source assurance remains open; ADC1 completion is not entropy
  quality. Two-button manual recovery and reset/debug/RAM need early physical
  qualification. USB-only operation does not require a battery.
- P4: complete local custody/recovery and actual offline conditions remain open.
  USB-connected BOOT does not establish hostile-host-independent consent; offline
  use requires every USB cable physically absent.
- Pi: diagnostic media was written and read back; physical boot awaits the
  operator's power resource. No repeated write or inventory is needed.
- The unmerged manual-QR host candidate has a blocking live-grant expiry finding
  at final publication. Software checks and a digital QR do not admit the route.

## Next delivery

Make target recipes/public entries independent of historical coordinator
checkout scripts, preserve unfinished work and finish justified cleanup.
Then fix the manual-host grant finding and frontload profile-invalidating
S3 recovery/reset/entropy and P4 offline experiments.
Complete usable paths: installation, applicable pairing, real client request,
readable review, physical Approve/Reject, verified response, error/cancel,
backup and same-identity recovery. Record actual binary/operator/client versions.

The sole [47-task graph](../../plan/work-items.json) records priorities,
dependencies, criteria and results. Preparatory feasibility cannot close a full
task. D03/Q04/Q05 release independently after all applicable gates and review.

## Sources and evidence

- [Requirements](../product/requirements.md), [threat models](../product/threat-models.md),
  [compatibility](../product/compatibility-plan.md), [architecture](architecture.md).
- [Scope](implementation/phase1-reconciliation.md) and [execution](execution.md).
- [D01](implementation/D01/board-qualification-20261026/result.json),
  [S3 host](implementation/V01/public-s3-live-flow/actual-public-lot-20261026/README.md),
  [QP02](implementation/QP02/exact-kit-20261026/result.json).
- Detailed historical results remain in their original artifacts and the
  [previous entry at verified main5686](https://github.com/nSealr/nsealr/blob/5686cbe60fe34ffd3478c707d804571096cd3a2d/docs/restart/README.md).
  Historical paths do not require operational checkout copies to remain.

A build, signature, coverage percentage or AI review does not establish custody,
usability, external certification, firmware/debug isolation or physical erasure.
