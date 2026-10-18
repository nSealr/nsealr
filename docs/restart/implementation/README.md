# Restart execution

The maintainer delegated execution of the complete restart on 2026-10-18, including local engineering, issues, branches, pull requests, merges, commits and pushes. The active goal is to deliver the separately qualified ESP32, Pi QR, P4 QR, Board SDK and custom Board Signer paths. This delegation does not manufacture missing physical evidence or identify a particular purchase, fabrication order, production-secret ceremony or irreversible fuse operation.

Task state remains solely in [work-items.json](../work-items.json). GitHub issues are navigation and discussion; a closed issue alone does not close a task. Implementation briefs and evidence live here or in the repository owning the implementation. Private research stays private unless selected material has been reviewed for publication and provenance.

Read [the execution handoff](handoff.md), then the assigned task and its brief. The October 18 readiness visualization is a dated snapshot of graph revision 5; use the current graph for execution.

## Assignment navigation

Read the graph for current task lifecycle, candidates and reviewers. This table locates the authors' work; it does not override that state. Publish an assignment/candidate transition through a small metadata PR promptly rather than leaving it coupled to a long implementation review. An unmerged task-state diff is a proposed update, not an already updated main. Fresh-session reconstruction compares graph, actual worktrees and PRs and records discrepancies before proceeding.

| Task | Author | Work branch | Writable boundary |
| --- | --- | --- | --- |
| R00 | `/root/baseline_execution` | `nsealr:restart/r00-bootstrap` | Bootstrap/integration tooling; `docs/restart/implementation/R00/brief.md` in that branch |
| S01 | `/root/bridge_execution` | `companion:restart/s01-bridge` | NIP-46 and transport; `docs/restart/S01/brief.md` in companion's branch |
| S01 integration | `/root/baseline_execution` | `nsealr:restart/s01-integration` | Complete core fixture snapshot/provenance and owned S01 integration evidence; accepted brief in that branch |
| S02 | `/root/secret_execution` | `nsealr:restart/s02-secrets` | Secret types/consumers/crypto; `docs/restart/implementation/S02/brief.md` in that branch |
| P01, O01 | `/root` | `nsealr:restart/goal-progress` | Product and coordination; `P01/brief.md` and `O01/brief.md` beside this file |
| A01 | `/root` | `nsealr:restart/a01-inventory` | Source/consumer inventory; `docs/restart/implementation/A01/brief.md` in PR #11 |
| E01 | `/root/cad_execution` | `nsealr:restart/e01-cad` | `tools/cad/` and `docs/restart/implementation/E01/`; exclusive disposable CAD projects/display `:96` |

Current independent review work is assigned to `/root/independent_security_review` (S02, branch `nsealr:restart/security-review-s02`, plus the fresh-session O01 exercise), `/root/independent_bridge_review` (S01, branch `companion:review/s01-final`), `/root/independent_cad_review` (E01, branch `nsealr:review/e01`) and `/root` (R00/integration). Review artifacts bind actual candidates; a reviewer name is not a passing verdict. Candidate branches remain frozen except for fixes explicitly invalidating affected review.

The scoped specialist assignments were started successfully using `gpt-6-astra` with `xhigh` reasoning in this session. This records accepted runtime assignments, not a promise about future model availability. Each author has a distinct worktree. Scoped authors do not write into another active author’s worktree or the coordinator’s task graph. After a recorded final delivery, the coordinator owns integration: it may replay commits and append unchanged reviews/equivalence evidence, while any source change invalidates its affected review. A separate reviewer must assess the precise final candidate before integration. The CAD author is the only writer of its disposable projects; additional operations remain disabled until demonstrated.

No permanent unattended service is installed. Work proceeds through the active goal and durable Git state.
