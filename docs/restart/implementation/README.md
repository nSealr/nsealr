# Restart execution

The maintainer delegated execution of the complete restart on 2026-10-18, including local engineering, issues, branches, pull requests, merges, commits and pushes. The active goal is to deliver the separately qualified ESP32, Pi QR, P4 QR, Board SDK and custom Board Signer paths. This delegation does not manufacture missing physical evidence or identify a particular purchase, fabrication order, production-secret ceremony or irreversible fuse operation.

Task state remains solely in [work-items.json](../work-items.json). GitHub issues are navigation and discussion; a closed issue alone does not close a task. Implementation briefs and evidence live here or in the repository owning the implementation. Private research stays private unless selected material has been reviewed for publication and provenance.

Read [the execution handoff](handoff.md), then the assigned task and its brief. The October 18 readiness visualization is a dated snapshot of graph revision 5; use the current graph for execution.

## First assignments

| Task | Author | Work branch | Writable boundary |
| --- | --- | --- | --- |
| R00 | `/root/baseline_execution` | `nsealr:restart/r00-bootstrap` | Bootstrap/integration tooling; `docs/restart/implementation/R00/brief.md` in that branch |
| S01 | `/root/bridge_execution` | `companion:restart/s01-bridge` | NIP-46 and transport; `docs/restart/S01/brief.md` in companion's branch |
| S02 | `/root/secret_execution` | `nsealr:restart/s02-secrets` | Secret types/consumers/crypto; `docs/restart/implementation/S02/brief.md` in that branch |
| P01, O01 | `/root` | `nsealr:restart/coordinator` | Product and coordination; `P01/brief.md` and `O01/brief.md` beside this file |

The three specialists were started successfully using `gpt-6-astra` with `xhigh` reasoning in this session. This records accepted runtime assignments, not a promise about future model availability. Each author has a distinct worktree. No agent writes another author's files or the coordinator's task graph. A separate reviewer must assess the precise final candidate before integration. One writer owns each CAD project when CAD work begins.

No permanent unattended service is installed. Work proceeds through the active goal and durable Git state.
