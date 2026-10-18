# Working on nSealr

Read `docs/restart/README.md`, then the relevant task in `plan/work-items.json`. These restart decisions supersede historical five-family, model-specific and mandatory-all-Rust phase instructions. They do not waive security or evidence requirements.

- Verify the actual source and current checkout before relying on documentation. Code establishes current behavior; accepted requirements and protocol specifications establish correct behavior. A bug does not become the specification.
- Keep the portable Nostr engine in this repository. Board SDK has no Nostr semantics. Bridge has no custody of user identity/signing keys or authority to approve device actions. NIP-46 client/transport keys have a separate, bounded host-owned lifecycle.
- No compatibility obligation exists for experimental nSealr APIs or old product names. Version new contracts explicitly; preserve external Nostr interoperability and provenance.
- Select a task whose dependencies are satisfied. Record scope, input commits, exact candidate, acceptance commands, resources and remaining unknowns. No task is complete from prose or simulation alone.
- Use one worktree and editable scope per implementer, one writer per live CAD project. A different agent reviews the final diff. Changed candidates invalidate affected reviews.
- The maintainer's latest model policy (2026-10-20) minimizes Astra: coordinator, implementers and reviewers default to `gpt-6.1-sol` with `xhigh` reasoning. Use `gpt-6-astra` `xhigh` only for an exceptional genuinely complex task/review, with a concrete assignment-specific reason recorded before escalation; hardware/security alone is insufficient. Verify actual runtime model/effort. Transfer existing assignments at safe checkpoints, preserving results/reviews. Historical model records remain unchanged.
- Run targeted checks, then affected integration gates. Preserve commands, environment, exit codes and artifact hashes. Record skips and inherited failures explicitly. Do not weaken checks merely to obtain green output.
- Hardware claims require exact part/revision documentation and applicable errata; assembled-board claims require identified physical measurements. ERC/DRC is necessary but insufficient.
- Reuse the maintainer's recorded authorization; do not request it twice. Repository reorganization/publication is authorized for this restart. No specific purchase, factory submission, production key ceremony or irreversible fuse operation is authorized merely by a research budget.
- Keep private research and credentials out of public history. Import selected licensed material; do not copy private repository histories wholesale.
- Update the task evidence and handoff with the change. Do not build a new orchestration service where Git, CI and small scripts suffice.

No unattended agent service is enabled by these files. Maintain release-specific guarantees; an unavailable security property cannot be replaced with a successful boolean.
