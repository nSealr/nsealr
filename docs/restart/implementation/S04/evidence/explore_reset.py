#!/usr/bin/env python3
"""Author's finite permission models, not chip firmware or independent proof.
Secret identity/knowledge and small counters are abstract. Full-state physical
rollback and cryptographic guessing success are deliberately outside this model.
"""
from collections import deque
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LIMIT = 2  # Scaled finite budget, not a proposed hardware threshold.


def explore(start, steps):
    todo = deque([start])
    paths = {start: []}
    while todo:
        state = todo.popleft()
        for label, new in steps(state):
            if new not in paths:
                paths[new] = paths[state] + [label]
                todo.append(new)
    return paths


@dataclass(frozen=True)
class Cycle:
    s: str = "old"
    v: str = "old"
    known_s: bool = False
    known_v: bool = False
    auto_s: bool = False
    auto_v: bool = False
    cs: int = LIMIT
    cv: int = LIMIT
    old_s_uses: int = 0
    leaked_old_s: bool = False


def cycle_steps(policy):
    def steps(q):
        # Optimistic full-write outcomes. In-place mixed secret values cannot be
        # authenticated merely by knowing the newly supplied fragment.
        yield "write S: complete known replacement", replace(q, s="new", known_s=True, auto_s=False)
        yield "write S: torn invalid value", replace(q, s="invalid", known_s=False, auto_s=False)
        # Old outcome is q itself and adds no reachable state.
        if q.auto_s:
            yield "write V: complete known replacement", replace(q, v="new", known_v=True, auto_v=False)
            yield "write V: torn invalid value", replace(q, v="invalid", known_v=False, auto_v=False)
        if q.s != "invalid" and (q.cs > 0 or policy == "unlimited"):
            uses = min(LIMIT + 1, q.old_s_uses + int(q.s == "old"))
            yield "authenticate S: succeeds iff known; consumes use", replace(
                q, auto_s=q.known_s, cs=q.cs if policy == "unlimited" else q.cs - 1,
                old_s_uses=uses)
        if q.v != "invalid" and q.cv > 0:
            yield "authenticate V: succeeds iff known; consumes use", replace(q, auto_v=q.known_v, cv=q.cv - 1)
        can_reset = policy == "public" or policy == "self" and q.auto_s or policy == "cross" and q.auto_v
        if can_reset:
            yield "reset S-use counter", replace(q, cs=LIMIT)
        if q.auto_s:
            yield "reset V-use counter", replace(q, cv=LIMIT)
        if q.auto_v and q.s != "invalid":
            yield "read S", replace(q, known_s=True, leaked_old_s=q.leaked_old_s or q.s == "old")
        yield "joint reset/clear: volatile AUTO lost only", replace(q, auto_s=False, auto_v=False)
    return steps


cycle_results = []
for policy in ("none", "self", "cross", "public", "unlimited"):
    all_states = explore(Cycle(), cycle_steps(policy))
    depleted = Cycle(cs=0, cv=0, old_s_uses=LIMIT)
    after = explore(depleted, cycle_steps(policy))
    recovered = next((s for s in after if s.s == "new" and s.v == "new" and s.cv > 0), None)
    bypass = next((s for s in all_states if s.old_s_uses > LIMIT), None)
    leaked = next((s for s in all_states if s.leaked_old_s), None)
    cycle_results.append({"S_counter_reset_policy": policy,
                          "states_from_initial": len(all_states),
                          "states_from_both_counters_depleted": len(after),
                          "can_reset_new_S_V_after_depletion": recovered is not None,
                          "reset_trace": after[recovered] if recovered else None,
                          "old_secret_usage_limit_bypass": bypass is not None,
                          "bypass_trace": all_states[bypass] if bypass else None,
                          "old_secret_released_without_initial_PIN_or_authority": leaked is not None})
assert all(not r["can_reset_new_S_V_after_depletion"] for r in cycle_results[:3])
assert all(r["old_secret_usage_limit_bypass"] for r in cycle_results[3:])
assert all(not r["old_secret_released_without_initial_PIN_or_authority"] for r in cycle_results)


@dataclass(frozen=True)
class DeleteState:
    pin: str = "old"
    factor: str = "old"
    authenticated: bool = False
    deleting: bool = False
    leaked: bool = False


def deletion_steps(variant):
    def steps(q):
        if variant == "atomic":
            yield "DeleteAll atomically destroys both application objects", DeleteState(pin="absent", factor="absent", leaked=q.leaked)
        elif variant == "quarantine":
            if not q.deleting:
                yield "persist quarantine before any deletion", replace(q, deleting=True, authenticated=False)
            else:
                yield "delete PIN while quarantine persists", replace(q, pin="absent")
                yield "delete release factor while quarantine persists", replace(q, factor="absent")
                if q.pin == q.factor == "absent":
                    yield "finish deletion and clear quarantine", replace(q, deleting=False)
        else:
            yield "partial DeleteAll deletes PIN first", replace(q, pin="absent", authenticated=False)
            yield "partial DeleteAll deletes factor first", replace(q, factor="absent")
        # A power cut never restores persistent data in this optimistic model.
        yield "power cut: preserve committed data/quarantine, clear session", replace(q, authenticated=False)
        if not q.deleting:
            if q.pin == "absent":
                yield "create known new PIN at same object ID", replace(q, pin="new")
            if q.pin == "new":
                yield "authenticate new PIN", replace(q, authenticated=True)
            if q.authenticated and q.factor == "old":
                yield "old release object accepts reused auth ID", replace(q, leaked=True)
    return steps


delete_results = []
for variant in ("atomic", "quarantine", "partial_unrestricted"):
    states = explore(DeleteState(), deletion_steps(variant))
    leaked = next((s for s in states if s.leaked), None)
    delete_results.append({"assumed_DeleteAll_semantics": variant, "states": len(states),
                           "old_factor_release_after_PIN_recreation": leaked is not None,
                           "counterexample": states[leaked] if leaked else None})
assert [r["old_factor_release_after_PIN_recreation"] for r in delete_results] == [False, False, True]

result = {"schema_version": 1, "task": "S04", "author": "/root/s04_custody_author",
          "status": "ABSTRACT_AUTHOR_EXPLORATION_NOT_INDEPENDENT_OR_CHIP_PROOF",
          "command": "python3 docs/restart/implementation/S04/evidence/explore_reset.py",
          "scaled_counter_limit": LIMIT,
          "Trust_M_cycle": cycle_results,
          "NXP_DeleteAll_conditional_models": delete_results,
          "assumptions": [
              "Known versus unknown full secret; no lucky guesses or side-channel leakage.",
              "Successful full writes are old/new/invalid, with no physical rollback; no atomic multi-object operation assumed.",
              "The model optimistically clears tracked AUTO on reference replacement and joint reset; real behavior must be established separately.",
              "Trust M reduced graph only: S public replacement, V change under AUTO(S), S read under AUTO(V); no Kp, protected-update service or MCU trust-root proof.",
              "NXP model deliberately compares three possible applet contracts. Public middleware does not prove which real chip implements.",
              "Factory reset credential, reserved manufacturer objects, SCP replacement, update authority and hardware wear are outside the abstract model and remain explicit gates."
          ],
          "bindings": {name: hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in
                       ("reset-followup.md", "reset-source-addendum.json", "evidence/explore_reset.py")}}
(BASE/"reset-exploration.json").write_text(json.dumps(result, indent=2)+"\n")
print("PASS: finite cyclic deadlock/bypass cases and conditional DeleteAll counterexample; author model only.")
