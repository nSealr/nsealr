#!/usr/bin/env python3
"""Run companion fixture verification against the live specs repository."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    from tests.integration.integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[2]
COMPANION = ROOT
SPECS = ROOT / "protocols/contracts/v1"


@dataclass(frozen=True)
class CommandPlan:
    cwd: Path
    argv: list[str]


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return run_command(command, cwd, capture_output=True)


def build_fixture_verify_command(*, companion: Path, specs: Path) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "fixture",
            "verify",
            "--specs",
            str(specs),
        ],
    )


def vector_count(specs: Path, relative: str) -> int:
    return len(list((specs / relative).glob("*.json")))


def fixture_count_label(count: int, singular: str, plural: str | None = None) -> str:
    return f"{count} {singular if count == 1 else plural or singular + 's'}"


def expected_fixture_output(specs: Path) -> str:
    return (
        f"verified {fixture_count_label(vector_count(specs, 'vectors/events'), 'event fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/review'), 'review fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/review-screens'), 'review-screen fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/review-display-frames'), 'review display-frame fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/review-detail-pages'), 'review detail-page fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/review-transcripts'), 'review transcript fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/nip46'), 'NIP-46 payload fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/nip46-policy-files'), 'NIP-46 policy-file fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/nip46-connection-uris'), 'NIP-46 connection URI fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/nip46-connection-token-responses'), 'NIP-46 connection token response fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/nip46-relay-events'), 'NIP-46 relay event fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/nip46-relay-steps'), 'NIP-46 relay step fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/nip46-auth-challenges'), 'NIP-46 auth challenge fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/nip46-sessions'), 'NIP-46 session fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/nip46-session-gates'), 'NIP-46 session gate fixture')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/accounts'), 'account descriptor')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/policies'), 'policy profile')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/grants'), 'grant descriptor')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/policy-changes'), 'policy change vector')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/policy-decisions'), 'policy decision vector')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/route-selections'), 'route selection vector')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/route-refusals'), 'route-refusal contract')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/access-surfaces'), 'access-surface vector')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/features'), 'feature matrix')}, "
        f"{fixture_count_label(vector_count(specs, 'vectors/custody'), 'persistent-secret custody contract')}, "
        f"and {fixture_count_label(vector_count(specs, 'vectors/invalid'), 'invalid hardening fixture')}"
    )


def main() -> int:
    for repo in (COMPANION, SPECS):
        if not repo.exists():
            raise FileNotFoundError(f"missing product component: {repo}")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)
    command = build_fixture_verify_command(companion=COMPANION, specs=SPECS)
    result = run(command.argv, command.cwd)
    output_lines = [line for line in result.stdout.splitlines() if line.strip()]
    expected_output = expected_fixture_output(SPECS)
    if not output_lines or output_lines[-1] != expected_output:
        raise AssertionError(f"unexpected fixture verification output: {result.stdout.strip()!r}")

    print("nSealr integrated companion fixture verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
