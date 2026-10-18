#!/usr/bin/env python3
"""Run companion NIP-46 decision CLI against live specs vectors."""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.integration_support import build_pnpm_workspace, env_for_command, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from integration_support import build_pnpm_workspace, env_for_command, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[1]
ORG = ROOT.parent
COMPANION = ORG / "companion"
SPECS = ORG / "specs"
SIGN_EVENT_KIND_1_POLICY = SPECS / "vectors/nip46-policy-files/sign-event-kind-1-approved.json"


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


def permission_string(granted_permissions: list[dict[str, Any]]) -> str:
    values = []
    for permission in granted_permissions:
        if permission.get("method") == "sign_event" and "parameter" in permission:
            values.append(f"sign_event:{permission['parameter']}")
        else:
            values.append(str(permission["method"]))
    return ",".join(values)


def build_nip46_decide_command(
    *,
    companion: Path,
    message_path: Path,
    permissions: str,
    out_path: Path,
) -> CommandPlan:
    argv = [
        "pnpm",
        "nsealr",
        "nip46",
        "decide",
        "--message",
        str(message_path),
        "--out",
        str(out_path),
    ]
    if permissions:
        argv.extend(["--permissions", permissions])
    return CommandPlan(cwd=companion, argv=argv)


def build_nip46_policy_file_command(
    *,
    companion: Path,
    message_path: Path,
    policy_path: Path,
    out_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "nip46",
            "decide",
            "--message",
            str(message_path),
            "--policy-file",
            str(policy_path),
            "--out",
            str(out_path),
        ],
    )


def build_nip46_connect_review_command(
    *,
    companion: Path,
    message_path: Path,
    out_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "nip46",
            "review-connect",
            "--message",
            str(message_path),
            "--out",
            str(out_path),
        ],
    )


def build_nip46_connect_approval_command(
    *,
    companion: Path,
    review_path: Path,
    reviewed_connect_digest: str,
    approved_at: int,
    out_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "nip46",
            "approve-connect",
            "--review",
            str(review_path),
            "--reviewed-connect-digest",
            reviewed_connect_digest,
            "--approved-at",
            str(approved_at),
            "--out",
            str(out_path),
        ],
    )


def build_nip46_auth_challenge_review_command(
    *,
    companion: Path,
    step_path: Path,
    out_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "nip46",
            "review-auth-challenge",
            "--step",
            str(step_path),
            "--out",
            str(out_path),
        ],
    )


def build_nip46_auth_challenge_approval_command(
    *,
    companion: Path,
    review_path: Path,
    reviewed_auth_challenge_digest: str,
    approved_at: int,
    out_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "nip46",
            "approve-auth-challenge",
            "--review",
            str(review_path),
            "--reviewed-auth-challenge-digest",
            reviewed_auth_challenge_digest,
            "--approved-at",
            str(approved_at),
            "--out",
            str(out_path),
        ],
    )


def build_nip46_session_checkpoint_command(
    *,
    companion: Path,
    review_path: Path,
    approval_path: Path,
    name: str,
    client_pubkey: str,
    relays: list[str],
    policy_path: Path,
    expires_at: int,
    out_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "nip46",
            "create-session-checkpoint",
            "--review",
            str(review_path),
            "--approval",
            str(approval_path),
            "--name",
            name,
            "--client-pubkey",
            client_pubkey,
            "--relays",
            ",".join(relays),
            "--policy-file",
            str(policy_path),
            "--expires-at",
            str(expires_at),
            "--out",
            str(out_path),
        ],
    )


def build_nip46_session_gate_command(
    *,
    companion: Path,
    session_path: Path,
    event_path: Path,
    message_path: Path,
    evaluated_at: int,
    direction: str | None = None,
    out_path: Path,
) -> CommandPlan:
    argv = [
        "pnpm",
        "nsealr",
        "nip46",
        "gate-session-request",
        "--session",
        str(session_path),
        "--event",
        str(event_path),
        "--message",
        str(message_path),
        "--evaluated-at",
        str(evaluated_at),
    ]
    if direction is not None:
        argv.extend(["--direction", direction])
    argv.extend(["--out", str(out_path)])
    return CommandPlan(
        cwd=companion,
        argv=argv,
    )


def build_nip46_connection_uri_command(
    *,
    companion: Path,
    uri_path: Path,
    out_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "nip46",
            "parse-connection-uri",
            "--uri-file",
            str(uri_path),
            "--out",
            str(out_path),
        ],
    )


def build_nip46_connection_token_response_command(
    *,
    companion: Path,
    uri_path: Path,
    step_path: Path,
    out_path: Path,
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "nip46",
            "verify-connection-token-response",
            "--uri-file",
            str(uri_path),
            "--step",
            str(step_path),
            "--out",
            str(out_path),
        ],
    )


def assert_decision_matches(path: Path, expected: Any) -> None:
    if load_json(path) != expected:
        raise AssertionError(f"NIP-46 decision output mismatch: {path}")


def assert_review_matches(path: Path, expected: Any) -> None:
    if load_json(path) != expected:
        raise AssertionError(f"NIP-46 connect review output mismatch: {path}")


def assert_approval_matches(path: Path, expected: Any) -> None:
    if load_json(path) != expected:
        raise AssertionError(f"NIP-46 connect approval output mismatch: {path}")


def assert_session_matches(path: Path, expected: Any) -> None:
    session = load_json(path)
    if session != expected:
        raise AssertionError(f"NIP-46 session checkpoint output mismatch: {path}")
    if "secret-1" in json.dumps(session, separators=(",", ":")):
        raise AssertionError(f"NIP-46 session checkpoint echoed secret: {path}")


def assert_session_gate_matches(path: Path, expected: Any) -> None:
    gate = load_json(path)
    if gate != expected:
        raise AssertionError(f"NIP-46 session request gate output mismatch: {path}")
    if "secret-1" in json.dumps(gate, separators=(",", ":")):
        raise AssertionError(f"NIP-46 session request gate echoed secret: {path}")
    if gate.get("dispatches_signer") is not False:
        raise AssertionError(f"NIP-46 session request gate dispatched a signer: {path}")


def assert_descriptor_matches(path: Path, expected: Any, secret_probe: str) -> None:
    descriptor = load_json(path)
    if descriptor != expected:
        raise AssertionError(f"NIP-46 connection URI descriptor output mismatch: {path}")
    if secret_probe in json.dumps(descriptor, separators=(",", ":")):
        raise AssertionError(f"NIP-46 connection URI descriptor echoed secret: {path}")


def assert_connection_token_response_matches(path: Path, expected: Any, secret_probe: str) -> None:
    response = load_json(path)
    if response != expected:
        raise AssertionError(f"NIP-46 connection token response output mismatch: {path}")
    if secret_probe in json.dumps(response, separators=(",", ":")):
        raise AssertionError(f"NIP-46 connection token response echoed secret: {path}")


def invalid_connection_uri_vectors(specs: Path) -> list[dict[str, Any]]:
    vectors = []
    for vector_path in sorted((specs / "vectors/invalid").glob("*.json")):
        vector = load_json(vector_path)
        if vector.get("category") == "nip46-connection-uri":
            vectors.append(vector)
    return vectors


def invalid_connection_token_response_vectors(specs: Path) -> list[dict[str, Any]]:
    vectors = []
    for vector_path in sorted((specs / "vectors/invalid").glob("*.json")):
        vector = load_json(vector_path)
        if vector.get("category") == "nip46-connection-token-response":
            vectors.append(vector)
    return vectors


def invalid_auth_challenge_relay_step_vectors(specs: Path) -> list[dict[str, Any]]:
    vectors = []
    for vector_path in sorted((specs / "vectors/invalid").glob("*.json")):
        vector = load_json(vector_path)
        relay_step = vector.get("relay_step")
        decrypted_message = relay_step.get("decrypted_message") if isinstance(relay_step, dict) else None
        if (
            vector.get("category") == "nip46-relay-step"
            and isinstance(relay_step, dict)
            and relay_step.get("format") == "nsealr-nip46-relay-response-step-v0"
            and isinstance(decrypted_message, dict)
            and decrypted_message.get("result") == "auth_url"
        ):
            vectors.append(vector)
    return vectors


def invalid_policy_file_vectors(specs: Path) -> list[dict[str, Any]]:
    vectors = []
    for vector_path in sorted((specs / "vectors/invalid").glob("*.json")):
        vector = load_json(vector_path)
        if vector.get("category") == "nip46-policy-file":
            vectors.append(vector)
    return vectors


def assert_nip46_decide_rejected(command: CommandPlan, out_path: Path, expected_error: str) -> None:
    result = subprocess.run(
        command.argv,
        cwd=command.cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env_for_command(command.argv),
    )
    if result.returncode == 0:
        raise AssertionError(f"NIP-46 decision unexpectedly accepted: {out_path}")
    output = f"{result.stdout}\n{result.stderr}"
    if expected_error not in output:
        raise AssertionError(f"NIP-46 decision rejection mismatch: expected {expected_error!r}, got {output!r}")
    if out_path.exists():
        raise AssertionError(f"NIP-46 decision rejection wrote output: {out_path}")


def assert_connection_uri_rejected(command: CommandPlan, out_path: Path, expected_error: str) -> None:
    result = subprocess.run(
        command.argv,
        cwd=command.cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env_for_command(command.argv),
    )
    if result.returncode == 0:
        raise AssertionError(f"NIP-46 connection URI unexpectedly accepted: {out_path}")
    output = f"{result.stdout}\n{result.stderr}"
    if expected_error not in output:
        raise AssertionError(f"NIP-46 connection URI rejection mismatch: expected {expected_error!r}, got {output!r}")
    if out_path.exists():
        raise AssertionError(f"NIP-46 connection URI rejection wrote output: {out_path}")


def assert_connection_token_response_rejected(command: CommandPlan, out_path: Path, expected_error: str) -> None:
    result = subprocess.run(
        command.argv,
        cwd=command.cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env_for_command(command.argv),
    )
    if result.returncode == 0:
        raise AssertionError(f"NIP-46 connection token response unexpectedly accepted: {out_path}")
    output = f"{result.stdout}\n{result.stderr}"
    if expected_error not in output:
        raise AssertionError(
            f"NIP-46 connection token response rejection mismatch: expected {expected_error!r}, got {output!r}"
        )
    if out_path.exists():
        raise AssertionError(f"NIP-46 connection token response rejection wrote output: {out_path}")


def assert_auth_challenge_review_rejected(command: CommandPlan, out_path: Path, expected_error: str) -> None:
    result = subprocess.run(
        command.argv,
        cwd=command.cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env_for_command(command.argv),
    )
    if result.returncode == 0:
        raise AssertionError(f"NIP-46 auth challenge review unexpectedly accepted: {out_path}")
    output = f"{result.stdout}\n{result.stderr}"
    if expected_error not in output:
        raise AssertionError(
            f"NIP-46 auth challenge review rejection mismatch: expected {expected_error!r}, got {output!r}"
        )
    if out_path.exists():
        raise AssertionError(f"NIP-46 auth challenge review rejection wrote output: {out_path}")


def assert_connect_approval_rejected(command: CommandPlan, out_path: Path, expected_error: str) -> None:
    result = subprocess.run(
        command.argv,
        cwd=command.cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env_for_command(command.argv),
    )
    if result.returncode == 0:
        raise AssertionError(f"NIP-46 connect approval unexpectedly accepted: {out_path}")
    output = f"{result.stdout}\n{result.stderr}"
    if expected_error not in output:
        raise AssertionError(f"NIP-46 connect approval rejection mismatch: expected {expected_error!r}, got {output!r}")
    if out_path.exists():
        raise AssertionError(f"NIP-46 connect approval rejection wrote output: {out_path}")


def assert_auth_challenge_approval_rejected(command: CommandPlan, out_path: Path, expected_error: str) -> None:
    result = subprocess.run(
        command.argv,
        cwd=command.cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env_for_command(command.argv),
    )
    if result.returncode == 0:
        raise AssertionError(f"NIP-46 auth challenge approval unexpectedly accepted: {out_path}")
    output = f"{result.stdout}\n{result.stderr}"
    if expected_error not in output:
        raise AssertionError(
            f"NIP-46 auth challenge approval rejection mismatch: expected {expected_error!r}, got {output!r}"
        )
    if out_path.exists():
        raise AssertionError(f"NIP-46 auth challenge approval rejection wrote output: {out_path}")


def assert_session_gate_rejected(command: CommandPlan, out_path: Path, expected_error: str) -> None:
    result = subprocess.run(
        command.argv,
        cwd=command.cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env_for_command(command.argv),
    )
    if result.returncode == 0:
        raise AssertionError(f"NIP-46 session request gate unexpectedly accepted: {out_path}")
    output = f"{result.stdout}\n{result.stderr}"
    if expected_error not in output:
        raise AssertionError(f"NIP-46 session request gate rejection mismatch: expected {expected_error!r}, got {output!r}")
    if out_path.exists():
        raise AssertionError(f"NIP-46 session request gate rejection wrote output: {out_path}")


def main() -> int:
    for repo in (COMPANION, SPECS):
        if not repo.exists():
            raise FileNotFoundError(f"missing sibling repository: {repo}")

    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)

    sign_event = load_json(SPECS / "vectors/nip46/sign-event-kind-1-basic.json")
    connect = load_json(SPECS / "vectors/nip46/connect-policy-review.json")
    auth_challenge = load_json(SPECS / "vectors/nip46-auth-challenges/auth-challenge-review.json")
    auth_challenge_step = load_json(SPECS / auth_challenge["source_relay_step_vector"])
    connection_token_response = load_json(
        SPECS / "vectors/nip46-connection-token-responses/nostrconnect-client-secret-response.json"
    )
    connection_token_source = load_json(SPECS / connection_token_response["source_connection_uri_vector"])
    session_vector = load_json(SPECS / "vectors/nip46-sessions/nostrconnect-approved-kind-1-checkpoint.json")
    session_gate_vector = load_json(SPECS / "vectors/nip46-session-gates/approved-pending-ack-sign-event-blocked.json")
    invalid_session_gate_vectors = [
        load_json(path) for path in sorted((SPECS / "vectors/invalid").glob("nip46-session-gate-*.json"))
    ]
    if not invalid_session_gate_vectors:
        raise AssertionError("missing shared invalid NIP-46 session gate vectors")
    session = session_vector["session"]
    checks = [
        ("sign-event-permitted", sign_event, sign_event["bridge_decisions"][0], True),
        ("sign-event-denied", sign_event, sign_event["bridge_decisions"][1], False),
        ("connect-review", connect, connect["bridge_decisions"][0], False),
    ]

    with tempfile.TemporaryDirectory(prefix="nsealr-nip46-cross-repo-") as temp_dir:
        temp = Path(temp_dir)
        for name, vector, check, use_policy_file in checks:
            message_path = temp / f"{name}-message.json"
            decision_path = temp / f"{name}-decision.json"
            write_json(message_path, vector["request_message"])
            if use_policy_file:
                policy_path = SIGN_EVENT_KIND_1_POLICY
                policy = load_json(policy_path)
                if policy.get("approved_permissions") != check["granted_permissions"]:
                    raise AssertionError(f"NIP-46 shared policy file does not match expected grants: {policy_path}")
                command = build_nip46_policy_file_command(
                    companion=COMPANION,
                    message_path=message_path,
                    policy_path=policy_path,
                    out_path=decision_path,
                )
            else:
                command = build_nip46_decide_command(
                    companion=COMPANION,
                    message_path=message_path,
                    permissions=permission_string(check["granted_permissions"]),
                    out_path=decision_path,
                )
            run(command.argv, command.cwd)
            assert_decision_matches(decision_path, check["decision"])

        broad_permission_message_path = temp / "broad-approved-permission-message.json"
        broad_permission_decision_path = temp / "broad-approved-permission-decision.json"
        write_json(broad_permission_message_path, sign_event["request_message"])
        command = build_nip46_decide_command(
            companion=COMPANION,
            message_path=broad_permission_message_path,
            permissions="sign_event",
            out_path=broad_permission_decision_path,
        )
        assert_nip46_decide_rejected(
            command,
            broad_permission_decision_path,
            "approved sign_event permission must include parameter and event_kind",
        )

        invalid_policy_vectors = invalid_policy_file_vectors(SPECS)
        if not invalid_policy_vectors:
            raise AssertionError("missing shared invalid NIP-46 policy-file vectors")
        for vector in invalid_policy_vectors:
            invalid_policy_path = temp / f"{vector['name']}.json"
            invalid_decision_path = temp / f"{vector['name']}-decision.json"
            write_json(invalid_policy_path, vector["policy_file"])
            command = build_nip46_policy_file_command(
                companion=COMPANION,
                message_path=broad_permission_message_path,
                policy_path=invalid_policy_path,
                out_path=invalid_decision_path,
            )
            assert_nip46_decide_rejected(command, invalid_decision_path, vector["expected_error"])

        connect_message_path = temp / "connect-review-message.json"
        connect_review_path = temp / "connect-review.json"
        write_json(connect_message_path, connect["request_message"])
        command = build_nip46_connect_review_command(
            companion=COMPANION,
            message_path=connect_message_path,
            out_path=connect_review_path,
        )
        run(command.argv, command.cwd)
        assert_review_matches(connect_review_path, connect["connect_review"])
        connect_approval_path = temp / "connect-approval.json"
        command = build_nip46_connect_approval_command(
            companion=COMPANION,
            review_path=connect_review_path,
            reviewed_connect_digest=connect["connect_review"]["connect_digest"],
            approved_at=connect["connect_approval"]["approved_at"],
            out_path=connect_approval_path,
        )
        run(command.argv, command.cwd)
        assert_approval_matches(connect_approval_path, connect["connect_approval"])
        auth_challenge_step_path = temp / "auth-challenge-step.json"
        auth_challenge_review_path = temp / "auth-challenge-review.json"
        auth_challenge_approval_path = temp / "auth-challenge-approval.json"
        write_json(auth_challenge_step_path, auth_challenge_step)
        command = build_nip46_auth_challenge_review_command(
            companion=COMPANION,
            step_path=auth_challenge_step_path,
            out_path=auth_challenge_review_path,
        )
        run(command.argv, command.cwd)
        assert_review_matches(auth_challenge_review_path, auth_challenge["review"])
        command = build_nip46_auth_challenge_approval_command(
            companion=COMPANION,
            review_path=auth_challenge_review_path,
            reviewed_auth_challenge_digest=auth_challenge["review"]["auth_challenge_digest"],
            approved_at=auth_challenge["approval"]["approved_at"],
            out_path=auth_challenge_approval_path,
        )
        run(command.argv, command.cwd)
        assert_approval_matches(auth_challenge_approval_path, auth_challenge["approval"])

        invalid_auth_challenge_vectors = invalid_auth_challenge_relay_step_vectors(SPECS)
        if not invalid_auth_challenge_vectors:
            raise AssertionError("missing shared invalid NIP-46 auth challenge relay-step vectors")
        for vector in invalid_auth_challenge_vectors:
            invalid_auth_step_path = temp / f"{vector['name']}-step.json"
            invalid_auth_review_path = temp / f"{vector['name']}-review.json"
            write_json(invalid_auth_step_path, vector["relay_step"])
            command = build_nip46_auth_challenge_review_command(
                companion=COMPANION,
                step_path=invalid_auth_step_path,
                out_path=invalid_auth_review_path,
            )
            assert_auth_challenge_review_rejected(command, invalid_auth_review_path, vector["expected_error"])

        session_path = temp / "connect-session-checkpoint.json"
        command = build_nip46_session_checkpoint_command(
            companion=COMPANION,
            review_path=connect_review_path,
            approval_path=connect_approval_path,
            name=session["name"],
            client_pubkey=session["client_pubkey"],
            relays=session["relays"],
            policy_path=SIGN_EVENT_KIND_1_POLICY,
            expires_at=session["expires_at"],
            out_path=session_path,
        )
        run(command.argv, command.cwd)
        assert_session_matches(session_path, session)
        session_gate_event_path = temp / "session-gate-event.json"
        session_gate_message_path = temp / "session-gate-message.json"
        session_gate_path = temp / "session-gate.json"
        write_json(session_gate_event_path, session_gate_vector["event"])
        write_json(session_gate_message_path, session_gate_vector["decrypted_message"])
        command = build_nip46_session_gate_command(
            companion=COMPANION,
            session_path=session_path,
            event_path=session_gate_event_path,
            message_path=session_gate_message_path,
            evaluated_at=session_gate_vector["evaluated_at"],
            out_path=session_gate_path,
        )
        run(command.argv, command.cwd)
        assert_session_gate_matches(session_gate_path, session_gate_vector["expected_gate"])
        for invalid_session_gate_vector in invalid_session_gate_vectors:
            invalid_session_gate = invalid_session_gate_vector["session_gate"]
            invalid_session_gate_session_path = temp / f"{invalid_session_gate_vector['name']}-session.json"
            invalid_session_gate_event_path = temp / f"{invalid_session_gate_vector['name']}-event.json"
            invalid_session_gate_message_path = temp / f"{invalid_session_gate_vector['name']}-message.json"
            invalid_session_gate_path = temp / f"{invalid_session_gate_vector['name']}-gate.json"
            write_json(invalid_session_gate_session_path, invalid_session_gate["session"])
            write_json(invalid_session_gate_event_path, invalid_session_gate["event"])
            write_json(invalid_session_gate_message_path, invalid_session_gate["decrypted_message"])
            command = build_nip46_session_gate_command(
                companion=COMPANION,
                session_path=invalid_session_gate_session_path,
                event_path=invalid_session_gate_event_path,
                message_path=invalid_session_gate_message_path,
                evaluated_at=invalid_session_gate["evaluated_at"],
                direction=invalid_session_gate.get("direction"),
                out_path=invalid_session_gate_path,
            )
            assert_session_gate_rejected(command, invalid_session_gate_path, invalid_session_gate_vector["expected_error"])
        connect_approval_mismatch_path = temp / "connect-approval-mismatch.json"
        command = build_nip46_connect_approval_command(
            companion=COMPANION,
            review_path=connect_review_path,
            reviewed_connect_digest="0" * 64,
            approved_at=connect["connect_approval"]["approved_at"],
            out_path=connect_approval_mismatch_path,
        )
        assert_connect_approval_rejected(
            command,
            connect_approval_mismatch_path,
            "reviewed connect digest",
        )
        auth_challenge_approval_mismatch_path = temp / "auth-challenge-approval-mismatch.json"
        command = build_nip46_auth_challenge_approval_command(
            companion=COMPANION,
            review_path=auth_challenge_review_path,
            reviewed_auth_challenge_digest="0" * 64,
            approved_at=auth_challenge["approval"]["approved_at"],
            out_path=auth_challenge_approval_mismatch_path,
        )
        assert_auth_challenge_approval_rejected(
            command,
            auth_challenge_approval_mismatch_path,
            "reviewed auth challenge digest",
        )

        for vector_path in sorted((SPECS / "vectors/nip46-connection-uris").glob("*.json")):
            vector = load_json(vector_path)
            uri_path = temp / f"{vector['name']}.txt"
            descriptor_path = temp / f"{vector['name']}.json"
            uri_path.write_text(f"{vector['uri']}\n", encoding="utf-8")
            command = build_nip46_connection_uri_command(
                companion=COMPANION,
                uri_path=uri_path,
                out_path=descriptor_path,
            )
            run(command.argv, command.cwd)
            assert_descriptor_matches(
                descriptor_path,
                vector["expected_descriptor"],
                vector["secret_probe"],
            )

        connection_token_uri_path = temp / "connection-token-response-uri.txt"
        connection_token_step_path = temp / "connection-token-response-step.json"
        connection_token_response_path = temp / "connection-token-response.json"
        connection_token_mismatch_uri_path = temp / "connection-token-response-mismatch-uri.txt"
        connection_token_mismatch_path = temp / "connection-token-response-mismatch.json"
        connection_token_uri_path.write_text(f"{connection_token_source['uri']}\n", encoding="utf-8")
        connection_token_mismatch_uri_path.write_text(
            f"{connection_token_source['uri'].replace(connection_token_source['secret_probe'], 'wrong-secret')}\n",
            encoding="utf-8",
        )
        write_json(connection_token_step_path, connection_token_response["response_step"])
        command = build_nip46_connection_token_response_command(
            companion=COMPANION,
            uri_path=connection_token_uri_path,
            step_path=connection_token_step_path,
            out_path=connection_token_response_path,
        )
        run(command.argv, command.cwd)
        assert_connection_token_response_matches(
            connection_token_response_path,
            connection_token_response["expected_response"],
            connection_token_source["secret_probe"],
        )
        command = build_nip46_connection_token_response_command(
            companion=COMPANION,
            uri_path=connection_token_mismatch_uri_path,
            step_path=connection_token_step_path,
            out_path=connection_token_mismatch_path,
        )
        assert_connection_token_response_rejected(
            command,
            connection_token_mismatch_path,
            "secret mismatch",
        )

        invalid_token_response_vectors = invalid_connection_token_response_vectors(SPECS)
        if not invalid_token_response_vectors:
            raise AssertionError("missing shared invalid NIP-46 connection token response vectors")
        for vector in invalid_token_response_vectors:
            invalid_token_response = vector["connection_token_response"]
            invalid_token_uri_path = temp / f"{vector['name']}-uri.txt"
            invalid_token_step_path = temp / f"{vector['name']}-step.json"
            invalid_token_out_path = temp / f"{vector['name']}-response.json"
            invalid_token_uri_path.write_text(f"{invalid_token_response['connection_uri']}\n", encoding="utf-8")
            write_json(invalid_token_step_path, invalid_token_response["response_step"])
            command = build_nip46_connection_token_response_command(
                companion=COMPANION,
                uri_path=invalid_token_uri_path,
                step_path=invalid_token_step_path,
                out_path=invalid_token_out_path,
            )
            assert_connection_token_response_rejected(command, invalid_token_out_path, vector["expected_error"])

        invalid_uri_vectors = invalid_connection_uri_vectors(SPECS)
        if not invalid_uri_vectors:
            raise AssertionError("missing shared invalid NIP-46 connection URI vectors")
        for vector in invalid_uri_vectors:
            uri_path = temp / f"{vector['name']}.txt"
            descriptor_path = temp / f"{vector['name']}.json"
            uri_path.write_text(f"{vector['uri']}\n", encoding="utf-8")
            command = build_nip46_connection_uri_command(
                companion=COMPANION,
                uri_path=uri_path,
                out_path=descriptor_path,
            )
            assert_connection_uri_rejected(command, descriptor_path, vector["expected_error"])

    print(
        "nSealr cross-repo companion NIP-46 decision, connect-review, "
        "connect-approval, auth-challenge review, auth-challenge rejection, "
        "session checkpoint, session gate, connection URI, and connection "
        "token response CLI verification passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
