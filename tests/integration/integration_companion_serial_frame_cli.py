#!/usr/bin/env python3
"""Run companion serial-frame CLI helpers against live specs vectors."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from tests.integration.integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from integration_support import build_pnpm_workspace, install_pnpm_workspace, run_command


ROOT = Path(__file__).resolve().parents[2]
COMPANION = ROOT
SPECS = ROOT / "protocols/contracts/v1"
SERIAL_FRAME_PREFIX = "nsealr1f:"


@dataclass(frozen=True)
class CommandPlan:
    cwd: Path
    argv: list[str]


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return run_command(command, cwd, capture_output=True)


def build_create_request_command(*, companion: Path, method: str, request_id: str, out: Path) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "request",
            method,
            "--request-id",
            request_id,
            "--out",
            str(out),
        ],
    )


def build_wrap_request_command(*, companion: Path, request: Path, out: Path) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "serial-frame",
            "wrap-request",
            "--request",
            str(request),
            "--out",
            str(out),
        ],
    )


def build_unwrap_response_command(*, companion: Path, request: Path, response_frame: Path, out: Path) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            "pnpm",
            "nsealr",
            "serial-frame",
            "unwrap-response",
            "--request",
            str(request),
            "--response-frame",
            str(response_frame),
            "--out",
            str(out),
        ],
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _base64url_json(payload: Any) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _checksum(frame_type: str, payload_base64url: str) -> str:
    return hashlib.sha256(f"{frame_type}:{payload_base64url}".encode("utf-8")).hexdigest()[:16]


def encode_serial_frame(frame_type: str, payload: Any) -> str:
    payload_base64url = _base64url_json(payload)
    return f"{SERIAL_FRAME_PREFIX}{frame_type}:{payload_base64url}:{_checksum(frame_type, payload_base64url)}\n"


def decode_serial_frame(line: str) -> dict[str, Any]:
    normalized = line.strip()
    if not normalized.startswith(SERIAL_FRAME_PREFIX):
        raise ValueError("serial frame has unexpected prefix")
    frame_type, payload_base64url, checksum = normalized[len(SERIAL_FRAME_PREFIX) :].split(":")
    if checksum != _checksum(frame_type, payload_base64url):
        raise ValueError("serial frame checksum mismatch")
    padded = payload_base64url + ("=" * ((4 - len(payload_base64url) % 4) % 4))
    payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    return {"type": frame_type, "payload": payload}


def main() -> int:
    for repo in (COMPANION, SPECS):
        if not repo.exists():
            raise FileNotFoundError(f"missing product component: {repo}")

    request_path = SPECS / "examples/request-get-capabilities.json"
    response_path = SPECS / "examples/response-get-capabilities-esp32-s3-scaffold.json"
    request = load_json(request_path)
    response = load_json(response_path)


    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)
    with tempfile.TemporaryDirectory(prefix="nsealr-serial-frame-") as tmp:
        temp_root = Path(tmp)
        request_frame_path = temp_root / "request.frame"
        response_frame_path = temp_root / "response.frame"
        unwrapped_response_path = temp_root / "response.json"
        generated_discovery_request_path = temp_root / "discovery-request.json"
        generated_discovery_frame_path = temp_root / "discovery-request.frame"
        discovery_response_frame_path = temp_root / "discovery-response.frame"
        unwrapped_discovery_response_path = temp_root / "discovery-response.json"

        wrap = build_wrap_request_command(companion=COMPANION, request=request_path, out=request_frame_path)
        run(wrap.argv, wrap.cwd)
        wrapped_request = decode_serial_frame(request_frame_path.read_text(encoding="utf-8"))
        if wrapped_request != {"type": "request", "payload": request}:
            raise AssertionError("wrapped serial request does not match specs request")

        response_frame_path.write_text(encode_serial_frame("response", response), encoding="utf-8")
        unwrap = build_unwrap_response_command(
            companion=COMPANION,
            request=request_path,
            response_frame=response_frame_path,
            out=unwrapped_response_path,
        )
        run(unwrap.argv, unwrap.cwd)
        if load_json(unwrapped_response_path) != response:
            raise AssertionError("unwrapped serial response does not match specs response")

        # Retired status is an actual negative, with bounded wire2 discovery as
        # its replacement. No fallback from the rejected command is attempted.
        retired = build_create_request_command(companion=COMPANION, method="get-signing-status", request_id="req-lab-retired", out=generated_discovery_request_path)
        try:
            run(retired.argv, retired.cwd)
        except subprocess.CalledProcessError as error:
            if "unsupported request method" not in (error.stderr or ""):
                raise AssertionError("retired signing-status rejection drifted") from error
        else:
            raise AssertionError("retired signing-status command unexpectedly succeeded")
        if generated_discovery_request_path.exists():
            raise AssertionError("retired command wrote a request")
        create_discovery = build_create_request_command(companion=COMPANION, method="get-capabilities", request_id="req-lab-discovery", out=generated_discovery_request_path)
        run(create_discovery.argv, create_discovery.cwd)
        generated_discovery_request = load_json(generated_discovery_request_path)
        expected_discovery_request = {"version": 2, "request_id": "req-lab-discovery", "method": "get_capabilities"}
        if generated_discovery_request != expected_discovery_request:
            raise AssertionError("generated discovery request does not match expected wire2")
        wrap_discovery = build_wrap_request_command(companion=COMPANION, request=generated_discovery_request_path, out=generated_discovery_frame_path)
        run(wrap_discovery.argv, wrap_discovery.cwd)
        if decode_serial_frame(generated_discovery_frame_path.read_text(encoding="utf-8")) != {"type": "request", "payload": expected_discovery_request}:
            raise AssertionError("wrapped discovery request mismatch")
        dynamic_response = {**response, "request_id": "req-lab-discovery"}
        discovery_response_frame_path.write_text(encode_serial_frame("response", dynamic_response), encoding="utf-8")
        unwrap_discovery = build_unwrap_response_command(companion=COMPANION, request=generated_discovery_request_path, response_frame=discovery_response_frame_path, out=unwrapped_discovery_response_path)
        run(unwrap_discovery.argv, unwrap_discovery.cwd)
        if load_json(unwrapped_discovery_response_path) != dynamic_response:
            raise AssertionError("unwrapped wire2 discovery response mismatch")

    print("nSealr integrated companion serial-frame CLI verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
