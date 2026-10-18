#!/usr/bin/env python3
"""Check plan structure/evidence records, not the truth of security claims."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"planned", "ready", "running", "blocked", "review", "verified", "integrated"}
ACTIVE = {"running", "review", "verified", "integrated"}
CLOSED = {"verified", "integrated"}
PROOF_KINDS = {"document", "source", "executed_test", "physical_measurement"}


def validate(plan: dict, root: Path) -> list[str]:
    errors: list[str] = []
    tasks = plan.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        return ["tasks must be a nonempty list"]
    by_id = {}
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get("id"), str):
            errors.append("each task needs a string id")
            continue
        if task["id"] in by_id:
            errors.append(f"duplicate task {task['id']}")
        by_id[task["id"]] = task
    resources = plan.get("resources", {})
    if not isinstance(resources, dict):
        return errors + ["resources must be an object"]
    for key, resource in resources.items():
        if not isinstance(resource, dict) or resource.get("status") not in {"unknown", "available", "unavailable"}:
            errors.append(f"invalid resource {key}")
        elif not resource.get("owner_role") or not resource.get("next_action"):
            errors.append(f"resource {key} needs an owner and next action")
        elif resource["status"] == "available" and (not resource.get("confirmed_by") or not resource.get("availability_record")):
            errors.append(f"resource {key} needs concrete confirmation and availability record")

    def commits(value: object) -> bool:
        return isinstance(value, dict) and bool(value) and all(
            isinstance(k, str) and isinstance(v, str) and re.fullmatch(r"[0-9a-f]{40}", v)
            for k, v in value.items()
        )

    dependencies = {}
    for key, task in by_id.items():
        status = task.get("status")
        if status not in STATUSES:
            errors.append(f"{key}: unknown status {status}")
        deps = task.get("depends_on")
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            errors.append(f"{key}: depends_on must be a string list")
            deps = []
        dependencies[key] = deps
        if len(deps) != len(set(deps)):
            errors.append(f"{key}: duplicate dependency")
        for dep in deps:
            if dep not in by_id:
                errors.append(f"{key}: missing dependency {dep}")
            elif status in ACTIVE | {"ready"} and by_id[dep].get("status") != "integrated":
                errors.append(f"{key}: dependency {dep} is not integrated")
        needed = task.get("required_resources", [])
        if not isinstance(needed, list) or any(not isinstance(r, str) for r in needed):
            errors.append(f"{key}: required_resources must be a string list")
            needed = []
        for resource in needed:
            item = resources.get(resource)
            if not isinstance(item, dict):
                errors.append(f"{key}: unknown resource {resource}")
            elif status in {"ready", "running"} and item.get("status") != "available":
                errors.append(f"{key}: resource {resource} is not available")
        acceptance = task.get("acceptance")
        if not isinstance(acceptance, list) or not acceptance or any(not isinstance(a, str) or not a.strip() for a in acceptance):
            errors.append(f"{key}: acceptance must be a nonempty string list")
            acceptance = []
        if not task.get("owner_role"):
            errors.append(f"{key}: owner_role required")
        if status == "blocked" and not task.get("blocker"):
            errors.append(f"{key}: blocked task needs blocker/next action")
        if status in ACTIVE and (not task.get("assignee") or not commits(task.get("input_commits"))):
            errors.append(f"{key}: active task needs assignee and exact input commits")
        if status not in CLOSED:
            continue
        candidate = task.get("candidate_commits")
        if not commits(candidate):
            errors.append(f"{key}: exact candidate commits required")
        if task.get("reviewed_candidate_commits") != candidate or task.get("reviewed_input_commits") != task.get("input_commits"):
            errors.append(f"{key}: review input/candidate mismatch")
        if not task.get("reviewer") or task.get("reviewer") == task.get("assignee") or task.get("review_verdict") != "pass":
            errors.append(f"{key}: independent passing review required")
        artifacts = task.get("result_artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{key}: evidence artifacts required")
            continue
        verified_paths = set()
        for artifact in artifacts:
            if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
                errors.append(f"{key}: artifact needs path and sha256")
                continue
            path = (root / artifact["path"]).resolve()
            if Path(artifact["path"]).is_absolute() or not path.is_relative_to(root.resolve()) or not path.is_file():
                errors.append(f"{key}: unavailable repository artifact {artifact['path']}")
                continue
            if artifact["path"] != path.relative_to(root.resolve()).as_posix() or artifact["path"] in verified_paths:
                errors.append(f"{key}: artifact aliases/duplicates are not allowed: {artifact['path']}")
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != artifact.get("sha256"):
                errors.append(f"{key}: artifact hash mismatch {artifact['path']}")
            else:
                verified_paths.add(artifact["path"])
        manifest_path = task.get("result_manifest")
        if manifest_path not in verified_paths:
            errors.append(f"{key}: result_manifest must identify a verified artifact")
            continue
        try:
            result = json.loads((root / manifest_path).read_text())
            if not isinstance(result, dict):
                raise ValueError("result must be an object")
            if result.get("input_commits") != task.get("input_commits") or result.get("candidate_commits") != candidate:
                errors.append(f"{key}: evidence input/candidate mismatch")
            if result.get("acceptance") != acceptance:
                errors.append(f"{key}: evidence acceptance requirements changed")
            review = result.get("review", {})
            if review != {"assignee": task.get("assignee"), "reviewer": task.get("reviewer"), "verdict": "pass"}:
                errors.append(f"{key}: evidence review mismatch")
            outcomes = result.get("acceptance_results", [])
            indices, kinds = [], set()
            for outcome in outcomes:
                index = outcome.get("index")
                if type(index) is not int:
                    raise ValueError("acceptance index must be integer")
                indices.append(index)
                kind = outcome.get("proof_kind")
                if outcome.get("outcome") != "pass" or kind not in PROOF_KINDS:
                    errors.append(f"{key}: invalid/failing acceptance result {index}")
                else:
                    kinds.add(kind)
                paths = outcome.get("evidence_paths")
                if not isinstance(paths, list) or not paths or any(p not in verified_paths or p == manifest_path for p in paths):
                    errors.append(f"{key}: acceptance {index} needs hashed underlying evidence")
            if sorted(indices) != list(range(len(acceptance))):
                errors.append(f"{key}: missing/duplicate/out-of-range acceptance results")
            if task.get("requires_physical_evidence"):
                physical = result.get("physical", {})
                if "physical_measurement" not in kinds or any(not physical.get(f) for f in ("sample_ids", "operator", "instruments", "conditions", "resource_snapshot")):
                    errors.append(f"{key}: physical evidence and historical resource record required")
        except (OSError, ValueError, TypeError, AttributeError) as error:
            errors.append(f"{key}: invalid result manifest: {error}")

    visiting, visited = set(), set()

    def walk(key: str) -> None:
        if key in visiting:
            errors.append(f"dependency cycle at {key}")
            return
        if key in visited:
            return
        visiting.add(key)
        for dep in dependencies.get(key, []):
            if dep in by_id:
                walk(dep)
        visiting.remove(key)
        visited.add(key)

    for key in by_id:
        walk(key)
    profiles = plan.get("active_profiles", [])
    gates = plan.get("release_paths", {})
    invariants = plan.get("release_forbidden_ancestors", {})
    if not isinstance(profiles, list) or not profiles or len(set(profiles)) != len(profiles) or set(profiles) != set(gates) or set(profiles) != set(invariants):
        errors.append("active profiles require complete unique release paths and invariant declarations")
    for profile, gate in gates.items():
        if gate not in by_id:
            errors.append(f"{profile}: missing release gate {gate}")
            continue
        ancestors, pending = set(), [gate]
        while pending:
            key = pending.pop()
            if key not in ancestors:
                ancestors.add(key)
                pending.extend(dependencies.get(key, []))
        rule = invariants.get(profile)
        if not isinstance(rule, list) or any(not isinstance(r, str) for r in rule) or (profile != "custom_board" and not rule):
            errors.append(f"{profile}: explicit independence rule required")
            rule = []
        forbidden = set(rule)
        if not forbidden <= by_id.keys():
            errors.append(f"{profile}: unknown forbidden ancestor")
        if overlap := ancestors & forbidden:
            errors.append(f"{profile}: forbidden release dependencies {sorted(overlap)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "plan/work-items.json")
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text())
        if not isinstance(plan, dict):
            raise ValueError("plan must be an object")
        errors = validate(plan, ROOT)
    except (OSError, ValueError, TypeError) as error:
        errors = [str(error)]
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    ready = [t["id"] for t in plan["tasks"] if t["status"] == "ready"]
    print(f"Restart plan valid: {len(plan['tasks'])} tasks; ready: {', '.join(ready)}")
    print("Structural check only; hardware, review quality and security remain evidence gates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
