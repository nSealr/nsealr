#!/usr/bin/env python3
"""Optional hardware smoke for companion CLI serial exchange against ESP32.

This script is intentionally not part of ``make integration`` because it
requires an attached board. By default it uses the companion ``serial-line``
CLI path; the older pyserial frame-capture path remains available for
diagnostics.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    from scripts.integration_support import PINNED_PNPM_COMMAND, run_command
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from integration_support import PINNED_PNPM_COMMAND, run_command


ROOT = Path(__file__).resolve().parents[1]
ORG = ROOT.parent
COMPANION = ORG / "companion"
SPECS = ORG / "specs"
PREFIX = "nsealr1f:"


@dataclass(frozen=True)
class CommandPlan:
    cwd: Path
    argv: list[str]


def pnpm_command() -> list[str]:
    return [*PINNED_PNPM_COMMAND]


def build_request_command(
    *, companion: Path, method: str, request_id: str, out: Path, pnpm: Optional[list[str]] = None
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            *(pnpm or pnpm_command()),
            "nsealr",
            "request",
            method,
            "--request-id",
            request_id,
            "--out",
            str(out),
        ],
    )


def build_sign_event_request_command(
    *, companion: Path, event_template: Path, request_id: str, out: Path, pnpm: Optional[list[str]] = None
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            *(pnpm or pnpm_command()),
            "nsealr",
            "request",
            "sign-event",
            "--event-template",
            str(event_template),
            "--request-id",
            request_id,
            "--out",
            str(out),
        ],
    )


def build_wrap_request_command(
    *, companion: Path, request: Path, out: Path, pnpm: Optional[list[str]] = None
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            *(pnpm or pnpm_command()),
            "nsealr",
            "serial-frame",
            "wrap-request",
            "--request",
            str(request),
            "--out",
            str(out),
        ],
    )


def build_unwrap_response_command(
    *, companion: Path, request: Path, response_frame: Path, out: Path, pnpm: Optional[list[str]] = None
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            *(pnpm or pnpm_command()),
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


def build_serial_line_exchange_command(
    *, companion: Path, port: str, request: Path, out: Path, timeout_ms: int, pnpm: Optional[list[str]] = None
) -> CommandPlan:
    return CommandPlan(
        cwd=companion,
        argv=[
            *(pnpm or pnpm_command()),
            "nsealr",
            "serial-line",
            "exchange",
            "--port",
            port,
            "--request",
            str(request),
            "--out",
            str(out),
            "--timeout-ms",
            str(timeout_ms),
        ],
    )


def run(command: CommandPlan) -> subprocess.CompletedProcess[str]:
    return run_command(command.argv, command.cwd, capture_output=True)


def extract_first_protocol_frame(text: str) -> Optional[str]:
    for line in text.splitlines(keepends=True):
        if not line.endswith("\n"):
            continue
        if not line.startswith(PREFIX):
            continue
        if line.endswith("\r\n"):
            return line.removesuffix("\r\n") + "\n"
        return line
    return None


def read_protocol_frame(device: object, timeout: float) -> str:
    deadline = time.monotonic() + timeout
    buffer = ""
    while time.monotonic() < deadline:
        chunk = device.read(512)
        if not chunk:
            continue
        buffer += chunk.decode("utf-8", errors="replace")
        frame = extract_first_protocol_frame(buffer)
        if frame is not None:
            return frame
    raise TimeoutError("no protocol response received before timeout")


def exchange_serial_frame(*, port: str, request_frame: str, timeout: float, baudrate: int) -> str:
    try:
        import serial  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on local ESP-IDF environment
        raise RuntimeError("pyserial is required; source the local ESP-IDF export.sh before running this smoke") from exc

    with serial.Serial(port, baudrate=baudrate, timeout=0.1) as device:
        device.reset_input_buffer()
        device.write(request_frame.encode("ascii"))
        device.flush()
        return read_protocol_frame(device, timeout)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(f"{json.dumps(value, indent=2)}\n", encoding="utf-8")


def assert_expected_response(method: str, response: dict[str, Any]) -> None:
    if method == "sign-event-disabled":
        error = response.get("error")
        if response.get("ok") is not False or not isinstance(error, dict) or error.get("code") != "signing_disabled":
            raise AssertionError(f"expected signing_disabled response, got: {response!r}")
        return
    if response.get("ok") is not True:
        raise AssertionError(f"expected successful {method} response, got: {response!r}")


def run_smoke(
    *,
    port: str,
    method: str,
    request_id: str,
    timeout: float,
    baudrate: int,
    out: Optional[Path],
    exchange_mode: str = "companion-serial-line",
) -> dict[str, Any]:
    if not COMPANION.exists():
        raise FileNotFoundError(f"missing sibling repository: {COMPANION}")
    if method == "sign-event-disabled" and not SPECS.exists():
        raise FileNotFoundError(f"missing sibling repository: {SPECS}")

    pnpm = pnpm_command()
    subprocess.run([*pnpm, "install"], cwd=COMPANION, check=True)
    with tempfile.TemporaryDirectory(prefix="nsealr-companion-hw-serial-") as tmp:
        temp_root = Path(tmp)
        request_path = temp_root / "request.json"
        request_frame_path = temp_root / "request.frame"
        response_frame_path = temp_root / "response.frame"
        response_path = out if out is not None else temp_root / "response.json"

        if method == "sign-event-disabled":
            template_path = temp_root / "event-template.json"
            shared_request = load_json(SPECS / "examples" / "request-kind-1-basic.json")
            write_json(template_path, shared_request["params"]["event_template"])
            run(
                build_sign_event_request_command(
                    companion=COMPANION,
                    event_template=template_path,
                    request_id=request_id,
                    out=request_path,
                    pnpm=pnpm,
                )
            )
        else:
            run(build_request_command(companion=COMPANION, method=method, request_id=request_id, out=request_path, pnpm=pnpm))

        if exchange_mode == "companion-serial-line":
            run(
                build_serial_line_exchange_command(
                    companion=COMPANION,
                    port=port,
                    request=request_path,
                    out=response_path,
                    timeout_ms=max(1, int(timeout * 1000)),
                    pnpm=pnpm,
                )
            )
        elif exchange_mode == "pyserial-frame":
            run(build_wrap_request_command(companion=COMPANION, request=request_path, out=request_frame_path, pnpm=pnpm))
            response_frame = exchange_serial_frame(
                port=port,
                request_frame=request_frame_path.read_text(encoding="utf-8"),
                timeout=timeout,
                baudrate=baudrate,
            )
            response_frame_path.write_text(response_frame, encoding="utf-8")
            run(
                build_unwrap_response_command(
                    companion=COMPANION,
                    request=request_path,
                    response_frame=response_frame_path,
                    out=response_path,
                    pnpm=pnpm,
                )
            )
        else:
            raise ValueError(f"unsupported exchange mode: {exchange_mode}")
        response = load_json(response_path)

    assert_expected_response(method, response)
    error = response.get("error")
    return {
        "status": "passed",
        "port": port,
        "method": method,
        "exchange_mode": exchange_mode,
        "request_id": request_id,
        "response_ok": response.get("ok"),
        "response_error_code": error.get("code") if isinstance(error, dict) else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/cu.usbmodem1101")
    parser.add_argument(
        "--method",
        choices=["get-capabilities", "get-public-key", "get-signing-status", "sign-event-disabled"],
        default="get-capabilities",
    )
    parser.add_argument("--request-id", default="lab-companion-hw-serial")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument(
        "--exchange-mode",
        choices=["companion-serial-line", "pyserial-frame"],
        default="companion-serial-line",
    )
    parser.add_argument("--out", type=Path, help="Optional path for the verified response JSON")
    args = parser.parse_args()

    result = run_smoke(
        port=args.port,
        method=args.method,
        request_id=args.request_id,
        timeout=args.timeout,
        baudrate=args.baudrate,
        out=args.out,
        exchange_mode=args.exchange_mode,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
