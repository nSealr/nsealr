# Execution and proof

A Codex coordinator maintains the task graph and assigns bounded work to independent implementers/reviewers. Git worktrees, CI and evidence files are sufficient initially. Hardware/security specialists use the maintainer-requested Astra xhigh configuration after checking availability. This foundation does not start an unattended service.

Task lifecycle: planned → ready → running → review → verified → integrated. A blocked task identifies the missing resource, owner and next action. Dependencies must be integrated before dependent acceptance is closed. A code author cannot approve its own final candidate.

Each assignment records objective, input commits, writable paths, constraints, required sources, acceptance commands and stop conditions. Each result records exact candidate and dirty state, command/procedure, timestamp, environment, exit code, artifact hashes and independent review. Physical records add board/assembly/silicon IDs, lifecycle state, instrument setup and conditions. Changed input invalidates affected evidence.

## Acceptance layers

| Claim | Proof required |
| --- | --- |
| Current software behavior | Exact source plus executed behavioral tests/reproduction |
| Correct behavior | Accepted requirement, protocol and threat model; code can be wrong |
| Device implementation | Actual target binary and physical request/review/sign/verify workflow |
| Security boundary | Negative tests for identity, parser/queue bounds, replay, consent, keys and recovery |
| Component capability | Manufacturer revision/section, exact ordering code, silicon/firmware and errata |
| CAD tooling | Nonempty canary, intentional ERC/DRC failures, corrected pass, exports, real IPC operations |
| PCB correctness | Pin/footprint review, ERC/DRC and semantic nets, electrical calculations, DFM/DFT and assembly inspection |
| Assembled hardware | Current-limited bring-up, power/thermal/interface measurements, faults and recovery |
| Release support | Exact binary/board manifest, client interoperability, reproducibility, review and recovery drill |

Zero ERC/DRC findings on an empty board prove nothing useful. A simulated signature, core target build, AI review or test-count total is not physical acceptance or an external security audit.

## Manual review and component freeze

Track document ID, revision, URL, local hash if downloaded, reviewed sections, extracted requirement and open questions. Identify exact package/pin/footprint and electrical interface evidence. Register inaccessible or unread material honestly. Do not claim that all manuals have been reviewed when only relevant sections have been inspected.

H04 cannot freeze architecture until MCU/SE feasibility, power/display/mechanical constraints and owner lifecycle have measured answers. Layout does not begin to make an unresolved schematic look complete. Fabrication waits for the complete package, independent review and concrete order authorization.

## Adoption gates

Test a named client/version matrix, first-use setup and recovery with people outside the implementation team. Record completion rate, confusing approval screens, operation latency and recovery errors by profile. A pilot participant is not a universal dependency for unrelated hardware paths. Publish only demonstrated compatibility.

An independent developer must build and flash a standalone non-Nostr Board example from clean instructions. That demonstrates platform usefulness more directly than promising every future wallet or token. Full FIDO/SSH/wallet products each need their own protocol and security qualification.

## Keeping documentation aligned

Generate supported-device/release tables and API references from structured manifests. Keep requirements and concise decisions next to the owner. Validate links and generated freshness, but test behavior rather than requiring marketing sentences to occur in prose. No unresolved exploitable blocker is waived by renaming it a limitation while retaining the affected guarantee.
