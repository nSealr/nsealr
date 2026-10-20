# P02 — client and profile qualification planning specification

Prepared 2026-10-18 by `/root`, assigned in [issue 24](https://github.com/nSealr/nsealr/issues/24).
This is a specification for distinct review before research implementation. It does not announce compatibility or complete P02.

## Purpose and authority

Enable a future tester to determine exactly which client, operation and device profile work together, what evidence is missing, and which release owns the result. Use all five unchanged P02 criteria in the sole task graph. P01's accepted requirements, threat models and event-review contract determine correct behavior; current source determines observed implementation. Source support alone cannot establish interoperability or adoption.

Initial source is `nSealr/nsealr@f2ef70f522af4977e15f81554a8c6eadcdbe8097`. [Input notes](input-notes.json) bind eleven inspected source files. The normative NIPs baseline is `37db639582d857e12468dcccd99b2c7f1d657da9`; the older baseline inside the dated client research is historical. A newer protocol/source revision requires a described delta and deliberate requirement review, never an implicit upgrade.

P01 is integrated. A02 is executing against frozen main. This independent preparation branch changes only `docs/restart/implementation/P02/`; the coordinator records assignment/state in the single graph during reviewed post-A02 reconciliation. This file is no second status tracker. Reconcile actual A02 paths and then-current requirements before final integration.

## Owned result and observable contract

Produce these reviewable documents, not a new testing framework or compatibility service:

- `compatibility-plan.md`: named client/browser candidates; per-profile scenario matrix, exact evidence required, owner task and decision rules.
- `source-register.json`: immutable official source URLs/commits/files/regions, file digests, package versions and actual lockfile resolution facts; distinguish read bodies from link-only leads. Include current observation time and changes from the dated candidates.
- `research-protocols.md`: opt-in interview, setup/recovery observation, connected/QR workflow and independent Board-developer scripts, including consent wording and a minimal result template.
- `result.json`: input/output digests, criteria mapping, actual source observations and explicitly unperformed runtime/human work.

Research checkouts and raw fetch metadata stay in owned ignored runtime storage. Publish concise derived facts and source links, not copied client trees, private participant records or copyrighted manuals. No existing product code, protocol contract, package export, firmware, repository setting or release status changes in this task.

## Required planning behavior

**PLAN-01 — exact candidates.** Start with the two independently implemented integration stacks identified in the dated research: noStrudel and Coracle. Inspect official current source and release/tag/default-branch facts; choose explicit candidate commit/package version and lockfile, explaining retention or replacement. Trace actual NIP-07/NIP-46 call paths, requested permissions and NIP-44/17/59 behavior. Record unsupported/uncertain paths, including NIP-04 requests, rather than inventing a fallback. Add an alternative only when it fills a concrete observed coverage gap. A package version is insufficient without source and dependency inputs.

**PLAN-02 — five independent delivery profiles.** Connected ESP32 without SE, connected custom Signer, offline Pi QR, offline P4 QR and generic Board/SDK each have a qualification plan. Common public-event scope covers key disclosure and kinds 0/1/3/5/6/7/10002 with complete review. Connected messaging has separate NIP-44 primitive, verified context and admitted one-to-one NIP-17/59 requirements, kind-10050 setup and conditional relay AUTH/22242. Initial offline profiles remain manual, volatile and public-signing-only. Generic Board development requires no Nostr client or Signer qualification. No universal security ranking or unrelated release prerequisite.

**PLAN-03 — evidence at its actual boundary.** Every scenario identifies inputs, preconditions, expected result and negative cases, exact profile/owning task, evidence to capture, and conditions that leave the result inconclusive. Separate source-supported, locally simulated, observed client/browser, observed physical device and release-admitted claims. A software source trace, valid fixture signature or local relay is never a device/UI/recovery/optical proof. Signing and relay publication are separate outcomes.

The common matrix includes fresh identity/pairing, expected full public-key confirmation, supported public actions, complete review/rejection, disconnect/cancel/late/duplicate response, wrong signer/session/account, oversize input, unsupported NIP-04, local recovery and independently verified output. Device consent cannot be replaced by a host-origin label. Bounds and timeout budgets come from each accepted profile, not invented protocol maxima.

Connected plans trace the real client's call sequence, NIP-46 transport versus user key, explicit unsupported errors, DM relay discovery/setup, required AUTH challenge changes, recipient/plaintext-to-seal binding and incoming verified-context limitations. Unsupported DM may block that advertised connected guarantee; do not silently reduce the accepted first connected release to public-only.

QR plans keep the client request pending through the separate optical request/response protocol. Test actual scans, interruption, mixed/dropped/reordered/duplicated/oversize frames, request timeout and independent response correlation. A nostrconnect pairing QR is not an offline signing transaction. Pi and P4 have separate device/optical gates; no actual decoder/framing choice is frozen by this planning task.

Board-developer plans cover documented exact hardware/SDK/toolchain inputs, clean independent build, non-Nostr example, real input/display/peripheral behavior where claimed, owner lifecycle and secret reset limits. One trusted firmware image implies no hostile-application isolation. Unsupported hardware features cannot pass through successful placeholder flags.

**PLAN-04 — runnable human protocols without outreach.** Prepare manual scripts a future researcher can follow, with voluntary participation, consent before observation, disposable fixture identities, no production-key/backup collection, a stop/withdraw option, anonymized minimal notes and no automatic telemetry. A recovery observation checks the expected identity locally without recording recovery material. Do not contact or recruit anyone under this task. Name who later identifies participants and an independent Board developer; do not make all profiles wait for the same person.

**PLAN-05 — measurable learning, honest decisions.** Record exact client/source/build/dependency/browser/OS/device/firmware/relay/profile revisions for a run, actual steps and timings, observed failures and independent signature/identity checks. Select desktop Chromium and Firefox candidate versions from official source/release information; reconcile exact executable builds before execution. Mobile selection waits for an explicit connector/device choice. Distinguish source test builds from changing deployed websites. Define pass/fail/inconclusive and stop on unexplained signing/identity changes regardless of usability scores. Keep prior pilot numerical targets as hypotheses; participant counts, source inspection and AI review cannot prove demand, retention, security certification or popularity.

## Sequence, alternatives and review

1. Distinct reviewer approves this exact brief/input notes/acceptance plan before research implementation.
2. Inspect primary official sources, lockfile dependencies and accepted profile/task boundaries. Preserve retrieval failures and name unresolved questions.
3. Draft scenario/evidence matrix and opt-in scripts. Make source-backed deductions explicit; give every unknown its owner and resolution experiment.
4. Review all five parent criteria, source references and the adequacy of the plan against the actual client call paths. Documentation-only work needs substantive/source/link consistency review, not tests that only assert prose exists.
5. Commit/push the exact final candidate. A distinct reviewer checks it; coordinator reconciles actual A02 paths, updates the one graph and integrates through ordinary PR/CI.

A single undifferentiated client checklist would hide device and DM boundaries. Requiring new mobile support, a new client, a large participant campaign or real hardware before writing the plan would add unrelated prerequisites. Executing runtime/client/physical pilots is deliberately owned by C01/C02, QH01 and the relevant device/release tasks, not claimed by P02.

Stop the affected assertion on inaccessible source, unresolved lockfile/call-path ambiguity, contradictory accepted semantics or a missing exact revision. Retain an uncertainty and a concrete resolution task instead of marking support. No purchase, fabrication, real secret use, irreversible operation, external message or participant outreach is part of this scope.
