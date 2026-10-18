from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import Callable


ReadText = Callable[[Path], str]
FindModule = Callable[[str], bool]
RunCommand = Callable[[tuple[str, ...]], tuple[int, str, str]]


BOOT_CONFIG_PATHS = (
    Path("/boot/config.txt"),
    Path("/boot/firmware/config.txt"),
)
REMOTE_ACCESS_SERVICES = ("ssh", "sshd")
CHECK_HUMAN_ACTIONS = {
    "board_model": "Run the probe on the target Raspberry Pi Zero-class board.",
    "gpio_python_module": "Install the GPIO Python dependency used by the SeedSigner-compatible button HAT.",
    "spi_python_module": "Install the SPI Python dependency used by the ST7789 display HAT.",
    "camera_python_module": "Install the Pi camera Python dependency used by the OV5647/ZeroCam QR scanner.",
    "boot_camera_enabled": "Enable the Pi camera path in the boot config before hardware acceptance.",
    "boot_spi_enabled": "Enable SPI in the boot config before hardware acceptance.",
    "swap_disabled": "Disable swap before signing acceptance so RAM-only secrets cannot page to storage.",
    "wireless_absent_or_blocked": "Use a non-wireless Pi Zero or record clear Wi-Fi/Bluetooth block evidence.",
    "remote_access_disabled": "Disable SSH/remote-login services before signing acceptance.",
}


def _default_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _default_find_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _default_run_command(args: tuple[str, ...]) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            list(args),
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _check(check_id: str, status: str, expected: str, observed: str) -> dict[str, str | bool]:
    return {
        "id": check_id,
        "required": True,
        "status": status,
        "expected": expected,
        "observed": observed,
    }


def _clean_model(value: str) -> str:
    return value.replace("\x00", "").strip()


def _read_first(paths: tuple[Path, ...], read_text: ReadText) -> tuple[Path | None, str | None]:
    for path in paths:
        try:
            return path, read_text(path)
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            continue
    return None, None


def _module_check(check_id: str, module_names: tuple[str, ...], find_module: FindModule) -> dict[str, str | bool]:
    available = [name for name in module_names if find_module(name)]
    status = "pass" if available else "blocked"
    return _check(
        check_id,
        status,
        "Python module available: " + " or ".join(module_names),
        ", ".join(available) if available else "module not found",
    )


def _boot_config_check(check_id: str, marker_options: tuple[str, ...], read_text: ReadText) -> dict[str, str | bool]:
    path, value = _read_first(BOOT_CONFIG_PATHS, read_text)
    if value is None or path is None:
        return _check(check_id, "blocked", "boot config readable", "no supported boot config path found")
    normalized = value.replace(" ", "").lower()
    matched = [marker for marker in marker_options if marker.replace(" ", "").lower() in normalized]
    return _check(
        check_id,
        "pass" if matched else "fail",
        "boot config contains " + " or ".join(marker_options),
        f"{path}: " + (", ".join(matched) if matched else "required marker missing"),
    )


def _command_state(returncode: int, stdout: str, stderr: str) -> str:
    detail = (stdout or stderr).strip()
    if not detail:
        detail = f"exit {returncode}"
    return detail.splitlines()[0]


def _remote_access_check(run_command: RunCommand) -> dict[str, str | bool]:
    observations: list[str] = []
    unsafe: list[str] = []
    blocked: list[str] = []

    for service in REMOTE_ACCESS_SERVICES:
        enabled = _command_state(*run_command(("systemctl", "is-enabled", service)))
        active = _command_state(*run_command(("systemctl", "is-active", service)))
        observations.append(f"{service}: enabled={enabled}; active={active}")

        if enabled in {"enabled", "enabled-runtime", "linked", "linked-runtime", "alias"}:
            unsafe.append(f"{service} is {enabled}")
        if active == "active":
            unsafe.append(f"{service} is active")
        if (
            "No such file or directory" in enabled
            or "No such file or directory" in active
            or "System has not been booted with systemd" in enabled
            or "System has not been booted with systemd" in active
        ):
            blocked.append(f"{service} systemd state unavailable")

    if unsafe:
        status = "fail"
        observed = "; ".join(unsafe + observations)
    elif blocked:
        status = "blocked"
        observed = "; ".join(blocked + observations)
    else:
        status = "pass"
        observed = "; ".join(observations)

    return _check(
        "remote_access_disabled",
        status,
        "ssh/sshd systemd services disabled or inactive before signing",
        observed,
    )


def _acceptance_blockers(checks: list[dict[str, str | bool]]) -> list[str]:
    return [str(check["id"]) for check in checks if check["status"] != "pass"]


def _human_actions_required(checks: list[dict[str, str | bool]]) -> list[str]:
    actions: list[str] = []
    for check_id in _acceptance_blockers(checks):
        action = CHECK_HUMAN_ACTIONS.get(check_id, f"Resolve failed hardware-probe check: {check_id}.")
        if action not in actions:
            actions.append(action)
    return actions


def run_seed_signer_compatibility_probe(
    *,
    read_text: ReadText = _default_read_text,
    find_module: FindModule = _default_find_module,
    run_command: RunCommand = _default_run_command,
) -> dict[str, object]:
    """Build a non-destructive SeedSigner-compatible Raspberry probe report."""

    checks: list[dict[str, str | bool]] = []

    try:
        model = _clean_model(read_text(Path("/proc/device-tree/model")))
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        model = ""
    model_lower = model.lower()
    if not model:
        checks.append(
            _check("board_model", "blocked", "Raspberry Pi Zero-class board model", "board model not readable")
        )
    elif "raspberry pi zero" in model_lower:
        checks.append(_check("board_model", "pass", "Raspberry Pi Zero-class board model", model))
    else:
        checks.append(_check("board_model", "fail", "Raspberry Pi Zero-class board model", model))

    checks.append(_module_check("gpio_python_module", ("RPi.GPIO",), find_module))
    checks.append(_module_check("spi_python_module", ("spidev",), find_module))
    checks.append(_module_check("camera_python_module", ("picamera", "picamera2"), find_module))
    checks.append(_boot_config_check("boot_camera_enabled", ("start_x=1", "camera_auto_detect=1"), read_text))
    checks.append(_boot_config_check("boot_spi_enabled", ("dtparam=spi=on",), read_text))

    try:
        swaps = read_text(Path("/proc/swaps")).strip().splitlines()
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        checks.append(_check("swap_disabled", "blocked", "no active swap entries", "/proc/swaps not readable"))
    else:
        active_swaps = [line for line in swaps[1:] if line.strip()]
        checks.append(
            _check(
                "swap_disabled",
                "pass" if not active_swaps else "fail",
                "no active swap entries",
                "no active swap entries" if not active_swaps else "; ".join(active_swaps),
            )
        )

    if "raspberry pi zero" in model_lower and "zero w" not in model_lower and "zero 2" not in model_lower:
        wireless_status = "pass"
        wireless_observed = "Pi Zero non-wireless target model"
    elif model:
        wireless_status = "blocked"
        wireless_observed = "wireless mitigation evidence required for this board model"
    else:
        wireless_status = "blocked"
        wireless_observed = "board model not readable"
    checks.append(
        _check(
            "wireless_absent_or_blocked",
            wireless_status,
            "wireless absent or blocked before signing",
            wireless_observed,
        )
    )
    checks.append(_remote_access_check(run_command))

    ready = all(check["status"] == "pass" for check in checks)
    return {
        "format": "nsealr-raspberry-seedsigner-compatibility-probe-v0",
        "target": "raspberry-pi-zero-seedsigner-compatible-qr-vault",
        "ready_for_hardware_acceptance": ready,
        "production_signing_enabled": False,
        "persistent_secret_present": False,
        "tropic01_used": False,
        "checks": checks,
        "acceptance_blockers": _acceptance_blockers(checks),
        "human_actions_required": _human_actions_required(checks),
        "limitations": [
            "This is a non-destructive development probe, not a completed hardware acceptance report.",
            "A passing probe does not prove QR scan quality, trusted display readability, GPIO approval UX, or production security.",
            "The Raspberry/Pi stateless QR vault remains RAM-only and must not add persistent secret storage or TROPIC01.",
        ],
    }
