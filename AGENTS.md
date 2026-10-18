> **Explicit project pause, 2026-10-18:** development is suspended until the maintainer explicitly resumes. Read `docs/restart/implementation/PAUSE-HANDOFF.md`. This branch is a checkpoint; preserve the A02 source freeze and do not infer execution authority from task eligibility.

# Working on nSealr

Read `docs/restart/README.md`, then the relevant task in `docs/restart/work-items.json`. These restart decisions supersede historical five-family, model-specific and mandatory-all-Rust phase instructions. They do not waive security or evidence requirements.

- Verify the actual source and current checkout before relying on documentation. Code establishes current behavior; accepted requirements and protocol specifications establish correct behavior. A bug does not become the specification.
- Keep the portable Nostr engine in this repository. Board SDK has no Nostr semantics. Bridge has no custody of user identity/signing keys or authority to approve device actions. NIP-46 client/transport keys have a separate, bounded host-owned lifecycle.
- No compatibility obligation exists for experimental nSealr APIs or old product names. Version new contracts explicitly; preserve external Nostr interoperability and provenance.
- Select a task whose dependencies are satisfied. Record scope, input commits, exact candidate, acceptance commands, resources and remaining unknowns. No task is complete from prose or simulation alone.
- Use one worktree and editable scope per implementer, one writer per live CAD project. A different agent reviews the final diff. Changed candidates invalidate affected reviews.
- The requested specialist configuration is Astra `xhigh` for hardware and security. Verify availability in the current Codex installation; do not assume a model identifier is perpetually valid or silently substitute it.
- Run targeted checks, then affected integration gates. Preserve commands, environment, exit codes and artifact hashes. Record skips and inherited failures explicitly. Do not weaken checks merely to obtain green output.
- Hardware claims require exact part/revision documentation and applicable errata; assembled-board claims require identified physical measurements. ERC/DRC is necessary but insufficient.
- Reuse the maintainer's recorded authorization; do not request it twice. Repository reorganization/publication is authorized for this restart. No specific purchase, factory submission, production key ceremony or irreversible fuse operation is authorized merely by a research budget.
- Keep private research and credentials out of public history. Import selected licensed material; do not copy private repository histories wholesale.
- Update the task evidence and handoff with the change. Do not build a new orchestration service where Git, CI and small scripts suffice.

No unattended agent service is enabled by these files. Maintain release-specific guarantees; an unavailable security property cannot be replaced with a successful boolean.
