# Execution and proof

A Codex coordinator maintains the task graph and assigns bounded work to independent implementers/reviewers. Git worktrees, CI and evidence files are sufficient initially. Hardware/security specialists use the maintainer-requested Astra xhigh configuration after checking availability. This foundation does not start an unattended service.

The [development contract](development.md) defines specification readiness, first-tranche substeps and a worked one-use authorization contract. A roadmap task is not automatically an implementation-ready brief. Requirements and experiments must be resolved at the boundary being implemented before claiming conformance.

Task lifecycle: planned → ready → running → review → verified → integrated. A blocked task identifies the missing resource, owner and next action. Dependencies must be integrated before dependent acceptance is closed. A code author cannot approve its own final candidate.

`plan/work-items.json` is the only task-state authority. `required_resources` refers to its resource registry; an unknown resource cannot support a ready/running claim. Preparatory research on a planned task is allowed without closing its dependent acceptance. Assign a concrete person for physical procedures and confirm the sample/instrument/access record before starting them. An AI role name is not a physical operator.

Each assignment records objective, input commits, writable paths, constraints, required sources, acceptance commands and stop conditions. Each result records exact candidate and dirty state, command/procedure, timestamp, environment, exit code, artifact hashes and independent review. Physical records add board/assembly/silicon IDs, lifecycle state, instrument setup and conditions. Changed input invalidates affected evidence.

The structural validator requires `input_commits` for active work and, for verified/integrated tasks, matching `reviewed_input_commits` / `reviewed_candidate_commits`, distinct assignee/reviewer, passing verdict and repository-relative `result_artifacts` with `path` and `sha256`. `result_manifest` names one of those hashed JSON artifacts. Its `input_commits` and `candidate_commits` must match the task, and its `review` contains the same `assignee`, `reviewer` and `verdict: "pass"`. Its `acceptance_results` contains exactly one result per zero-based acceptance index, with `index`, `outcome: "pass"`, `proof_kind` (`document`, `source`, `executed_test` or `physical_measurement`) and nonempty `evidence_paths` pointing to underlying hashed artifacts, not the manifest itself. Record commands/procedures, environment, timestamps, limits and observations in that underlying evidence.

The manifest also preserves the exact `acceptance` string list; changed requirements invalidate closure even if their count stays equal. Artifact paths are canonical repository-relative paths without aliases or duplicates; a manifest cannot cite itself as underlying proof.

Tasks marked `requires_physical_evidence` additionally require measured evidence and a `physical` record containing `sample_ids`, `operator`, `instruments`, `conditions` and the historical `resource_snapshot`. A resource currently marked available needs `confirmed_by` and an `availability_record` identifying actual sample/access arrangements. Later loss or consumption of a sample does not invalidate an already completed experiment; changing its relevant design inputs can. Current availability gates ready/running work, not historical closure.

Do not publish secrets or confidential reports. A public redacted/hash-bound report needs authorized review of the underlying restricted evidence. Hashes and structurally consistent records do not prove correctness, reviewer independence in practice or access authorization. Record the later integration commit separately; a review record must not require a commit containing its own hash. Closing metadata can follow the reviewed product candidate without changing that candidate's evidence scope.

Run `make test` for the graph/evidence check and its negative cases; full affected CI remains required. This implements part of O01, not its fresh-session handoff, substantive review or autonomous operating acceptance. Rework creates a new candidate and invalidates affected results; do not insert cycles into the dependency graph.

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

Those pre-layout answers combine reviewed requirements, electrical calculations and representative bench measurements. Assembled-board claims are repeated on H08/H09 hardware. Before routing, pin the selected service's stackup/assembly/test rules. B03 owns generic-platform production/provisioning proof; S05 owns safe pilot enrollment/recovery before real identities; R01 scales and repeats the final Signer production controls. None may borrow a later dependent task as its evidence.

## Adoption gates

Test a named client/version matrix, first-use setup and recovery with people outside the implementation team. Record completion rate, confusing approval screens, operation latency and recovery errors by profile. A pilot participant is not a universal dependency for unrelated hardware paths. Publish only demonstrated compatibility.

An independent developer must build and flash a standalone non-Nostr Board example from clean instructions. That demonstrates platform usefulness more directly than promising every future wallet or token. Full FIDO/SSH/wallet products each need their own protocol and security qualification.

## Keeping documentation aligned

Generate supported-device/release tables and API references from structured manifests. Keep requirements and concise decisions next to the owner. Validate links and generated freshness, but test behavior rather than requiring marketing sentences to occur in prose. No unresolved exploitable blocker is waived by renaming it a limitation while retaining the affected guarantee.
