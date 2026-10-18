# Execution handoff

Date: 2026-10-18. This handoff gives navigation and recovery procedures, not a second task-status ledger. Read the current graph before choosing work.

## Recover the actual state

1. Read the repository `AGENTS.md`, `docs/restart/README.md`, `execution.md` and the task in `work-items.json`.
2. Run `git status --short`, `git log -5 --oneline`, `git worktree list` and `python3 scripts/validate_restart_plan.py`. Check remote branch and PR heads before assuming a local candidate is current.
3. For running/review tasks, follow the current graph's assignment and owning brief. For integrated tasks, follow their result manifest, immutable review/evidence and integration record. The first-tranche table in `implementation/README.md` is historical navigation, not a current assignment list. Compare actual worktrees and PRs with the graph; report publication lag instead of assuming an unmerged update is authoritative. Do not duplicate an active author. Read exact input commits, writable paths, known failures and required resources.
4. For a review, inspect the actual candidate and scope, then check the specification, threat adequacy and maintainability separately. Record candidate hashes and substantive findings. Changed candidates invalidate affected approval.
5. Integrate only after required CI passes on the relevant candidate; preserve branch protection and use a normal reviewed PR. Record integration commit separately from the reviewed implementation commit.

Local integration directory: `/home/tux/nsealr`; it is not a repository. Local `firmware/` is the public `nSealr/nsealr` repository. Isolated authors work under `.restart-tools/goal/`. Existing `companion`, `raspberry`, `specs`, `lab` and private `workspace` remain source repositories until A01/A02 disposition and migration gates pass. Do not archive them early.

## Historical first-tranche input baseline

| Repository | Input commit |
| --- | --- |
| `nSealr/nsealr` | `768e8a35ae541f53f5da9c7bea7bf5c577fb474d` |
| `nSealr/companion` | `13414320537d0208fc3ef8e43bd0723c98c1d5e0` |
| `nSealr/raspberry` | `d1534d9dcfba8fe4a35cea2ed3529e32a5003dc6` |
| `nSealr/specs` | `8bb8cca71355bcf8d81a093bcee9f3fe6915b121` |

These inputs precede implementation; later task input records supersede them. Each author must reconcile its actual source, not reuse historical results as current proof.

## Product outcome and remaining gates

The first device outcome is a request reaching an actual device, exact local review, one-use authorization, a valid signature and expected-key verification. R00 owns repeatable tools, S01 Bridge boundaries, S02 secret ownership/crypto selection and P01 the product contract. Their actual completion and evidence are recorded in the graph. K01 and device work start only after their declared dependencies integrate. First experiments use public disposable identities.

Read the current profile release gates before making support claims. The historical baseline's secret defects are not a statement about repaired source: inspect S02's exact result and later changes. Disabled signing paths and outstanding authorization/device requirements need their own implementation and acceptance; a passing software baseline does not qualify a production signer. Physical availability comes only from the graph's resource records and concrete confirmations. A server USB inventory is not an inventory of the maintainer's hardware. Do not mark resources available from an AI role name, installed tools or assumed shipping dates.

## Commit and publication policy

Preserve implementation, meaningful failed/positive evidence, current instructions and independent review. Keep raw sensitive material out of public Git. Publish reviewable branches/PRs as work becomes concrete, then merge with the required checks. Issue text points to canonical task state; do not synchronize a second complete tracker manually.

Missing physical resources block the corresponding experiment and release, while independent software and design preparation continue. Purchases and irreversible operations need a concrete reviewed package; the project's general research budget is not a specification for an order.
