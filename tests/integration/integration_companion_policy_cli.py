#!/usr/bin/env python3
"""Run companion policy-change review CLI against live specs vectors."""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from tests.integration.integration_support import build_pnpm_workspace, env_for_command, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from integration_support import build_pnpm_workspace, env_for_command, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[2]
COMPANION = ROOT
SPECS = ROOT / "protocols/contracts/v1"


@dataclass(frozen=True)
class CommandPlan:
    cwd: Path
    argv: list[str]


def run(command: list[str], cwd: Path) -> None:
    run_command(command, cwd)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def policy_change_vectors(specs: Path) -> list[dict[str, Any]]:
    return [load_json(path) for path in sorted((specs / "vectors/policy-changes").glob("*.json"))]


def find_vector_path_by_field(root: Path, field: str, value: str) -> Path:
    matches = [path for path in sorted(root.glob("*.json")) if load_json(path).get(field) == value]
    if not matches:
        raise AssertionError(f"missing {field}={value} under {root}")
    if len(matches) > 1:
        raise AssertionError(f"ambiguous {field}={value} under {root}")
    return matches[0]


def policy_change_context_paths(specs: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "account_path": find_vector_path_by_field(specs / "vectors/accounts", "account_id", proposal["account_id"]),
        "current_policy_path": find_vector_path_by_field(
            specs / "vectors/policies", "policy_id", proposal["current_policy_id"]
        ),
        "proposed_policy_path": find_vector_path_by_field(
            specs / "vectors/policies", "policy_id", proposal["proposed_policy_id"]
        ),
        "grant_paths": [
            find_vector_path_by_field(specs / "vectors/grants", "grant_id", grant_id)
            for grant_id in proposal["proposed_grant_ids"]
        ],
    }


def build_policy_review_command(
    *,
    companion: Path,
    proposal_path: Path,
    account_path: Path,
    current_policy_path: Path,
    proposed_policy_path: Path,
    grant_paths: list[Path],
    out_path: Path,
) -> CommandPlan:
    grant_args = [arg for grant_path in grant_paths for arg in ("--grant", str(grant_path))]
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "policy",
            "review-change",
            "--proposal",
            str(proposal_path),
            "--account",
            str(account_path),
            "--current-policy",
            str(current_policy_path),
            "--proposed-policy",
            str(proposed_policy_path),
            *grant_args,
            "--out",
            str(out_path),
        ],
    )


def assert_review_matches(path: Path, expected: Any) -> None:
    if load_json(path) != expected:
        raise AssertionError(f"policy-change review output mismatch: {path}")


def assert_rejected_without_output(command: CommandPlan, out_path: Path, expected_error: str) -> None:
    result = subprocess.run(
        command.argv,
        cwd=command.cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env_for_command(command.argv),
    )
    if result.returncode == 0:
        raise AssertionError(f"policy-change proposal unexpectedly accepted: {out_path}")
    output = f"{result.stdout}\n{result.stderr}"
    if expected_error not in output:
        raise AssertionError(f"policy-change rejection mismatch: expected {expected_error!r}, got {output!r}")
    if out_path.exists():
        raise AssertionError(f"policy-change rejection wrote output: {out_path}")


def main() -> int:
    for repo in (COMPANION, SPECS):
        if not repo.exists():
            raise FileNotFoundError(f"missing product component: {repo}")

    vectors = policy_change_vectors(SPECS)
    if not vectors:
        raise AssertionError("missing shared policy-change review vectors")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)

    with tempfile.TemporaryDirectory(prefix="nsealr-policy-cli-integrated-") as temp_dir:
        temp = Path(temp_dir)
        for vector in vectors:
            proposal_path = temp / f"{vector['name']}-proposal.json"
            review_path = temp / f"{vector['name']}-review.json"
            write_json(proposal_path, vector["proposal"])
            command = build_policy_review_command(
                companion=COMPANION,
                proposal_path=proposal_path,
                **policy_change_context_paths(SPECS, vector["proposal"]),
                out_path=review_path,
            )
            run(command.argv, command.cwd)
            assert_review_matches(review_path, vector["review"])

        invalid = dict(vectors[0]["proposal"])
        invalid["companion_authoritative"] = True
        invalid_proposal_path = temp / "companion-authoritative-proposal.json"
        invalid_review_path = temp / "companion-authoritative-review.json"
        write_json(invalid_proposal_path, invalid)
        command = build_policy_review_command(
            companion=COMPANION,
            proposal_path=invalid_proposal_path,
            **policy_change_context_paths(SPECS, vectors[0]["proposal"]),
            out_path=invalid_review_path,
        )
        assert_rejected_without_output(command, invalid_review_path, "companion_authoritative must be false")

    print("nSealr integrated companion policy-change review CLI verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
