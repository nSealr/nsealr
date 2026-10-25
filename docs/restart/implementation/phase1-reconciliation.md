# Phase-one scope reconciliation

Authority: maintainer direction of 2026-10-25. Input product is
`19ab15d15aa8751174aa87119ae18853007c8222`; the source-qualified handoff is private
workspace `d4eb109dae14440ea65492c76af2585de7377b70`. This bounded delivery changes
the sole [task graph](../../../plan/work-items.json), current requirements and
the two relevant candidate manifests. It does not implement a device profile.

Author: `/root/phase1_scope`. Distinct affected reviewer and integration owner:
new coordinator `/root`. One worktree and one candidate; no hardware operation,
CI observation, replay of unchanged experiments or new research campaign.

The observable contract is three independently releasable products: connected
LILYGO T-Display-S3 with local review, two buttons and session-only identity
custody; offline Pi and P4 with local reload and session-only custody; and the
Bridge, CLI/service, browser/client and TypeScript SDK necessary to use them.
D01 identifies the S3; V01 proves a public-test-identity vertical flow; D02 admits
its session lifecycle; D03 still requires D02 and connected C01/C02. Preserve
the old persistent D02 requirements as a deferred extension. Retain custom PCB,
embedded Board SDK and S04 history outside phase one, without bypassing S04.

Review must reject a hidden persistent/PIN prerequisite, plaintext recovery via
Bridge, incomplete review, unrelated release dependency, invented radio absence,
physical closure from host evidence, changed historical proof or abandoned
connected message/catalog requirement. Existing touch approval policy is unchanged.

Validation uses the existing plan validator and its negative tests, board-profile
validator, JSON parsing and diff review. These checks establish structure and
consistency; physical lifecycle, entropy, boot/update, human usability and named
client qualification remain the implementation/release gates in the graph.
Existing PR52 adoption proof is copied unchanged from `eb69e559`; P4 build-only
and human-wait canary receipts keep their original candidate and limited role.

Validation on Linux: `python3 scripts/validate_restart_plan.py` PASS (47 tasks),
`python3 scripts/test_validate_restart_plan.py` PASS (18 tests),
`python3 scripts/validate_firmware.py` PASS, and `git diff --check` PASS.
No product runtime or full-CI campaign was run for this metadata/document change.
The selected root device receipt is sanitized; raw unique identifiers and private
hardware logs stay in the existing private preservation path. Original PR52
packet bytes and historical closed-task records are retained unchanged.
