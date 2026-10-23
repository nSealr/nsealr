from __future__ import annotations

import importlib.util
import re
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
    # Deliberately a small unconditional text subset, not a firmware evaluator.
    values: dict[str, set[str]] = {"start_x": set(), "camera_auto_detect": set(), "dtparam": set()}
    expected = "supported unconditional boot setting " + " or ".join(marker_options)
    for number, raw in enumerate(value.split("\n"), 1):
        line = raw.strip(" \t\r")
        if not line or line.startswith("#"):
            continue
        # Official pages describe80/98-character entry limits. Do not infer
        # truncated firmware meaning from a longer or non-ASCII entry.
        if len(raw) > 80 or not line.isascii():
            return _check(check_id, "blocked", expected, f"{path}:{number}: unsupported boot entry")
        if line == "[all]":
            continue
        camera = re.fullmatch(r"(start_x|camera_auto_detect)[ \t]*=[ \t]*([01])", line)
        spi = re.fullmatch(r"dtparam[ \t]*=[ \t]*spi[ \t]*=[ \t]*(on|off)", line)
        if camera:
            values[camera[1]].add(camera[2])
        elif spi:
            values["dtparam"].add("spi=" + spi[1])
        else:
            # Includes, filters, overlay scope, multi-parameter forms and other
            # directives require resolution this read-only probe does not have.
            return _check(check_id, "blocked", expected, f"{path}:{number}: unresolved boot syntax")
    options = [marker.split("=", 1) for marker in marker_options]
    if any(len(values[key]) > 1 for key, _setting in options):
        return _check(check_id, "blocked", expected, f"{path}: conflicting target directives")
    matched = [marker for marker, (key, setting) in zip(marker_options, options) if setting in values[key]]
    return _check(
        check_id,
        "pass" if matched else "fail",
        expected,
        f"{path}: " + (", ".join(matched) if matched else "required supported setting missing or off"),
    )


def _command_state(returncode: int, stdout: str, stderr: str, *, enabled: bool) -> tuple[str, str]:
    # Keep every response field; a first-line token or a nonzero exit alone
    # cannot establish that a queried service is disabled/inactive.
    detail = f"exit={returncode!r}, stdout={stdout!r}, stderr={stderr!r}"
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        return "blocked", detail
    unsafe = {"enabled", "enabled-runtime", "linked", "linked-runtime", "alias"} if enabled else {
        "active", "reloading", "refreshing", "activating", "deactivating"
    }
    if any(line.strip(" \t\r") in unsafe for line in stdout.split("\n")):
        return "fail", detail
    state = stdout.strip(" \t\r\n")
    safe_states = {"disabled", "masked", "masked-runtime"} if enabled else {"inactive"}
    safe_exit = 1 if enabled else 3
    if type(returncode) is int and returncode == safe_exit and state in safe_states and not stderr.strip(" \t\r\n"):
        return "pass", detail
    return "blocked", detail


def _remote_access_check(run_command: RunCommand) -> dict[str, str | bool]:
    observations: list[str] = []
    statuses: list[str] = []
    for service in REMOTE_ACCESS_SERVICES:
        enabled_status, enabled = _command_state(*run_command(("systemctl", "is-enabled", service)), enabled=True)
        active_status, active = _command_state(*run_command(("systemctl", "is-active", service)), enabled=False)
        statuses.extend((enabled_status, active_status))
        observations.append(f"{service}: is-enabled ({enabled}); is-active ({active})")
    status = "fail" if "fail" in statuses else "blocked" if "blocked" in statuses else "pass"
    return _check(
        "remote_access_disabled",
        status,
        "queried ssh/sshd units explicitly disabled or masked AND inactive",
        "; ".join(observations),
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
            "Boot checks cover only a supported unconditional file-text subset, not current loaded configuration, SPI, sensor or display operation.",
            "Remote checks cover only the ssh/sshd systemd service queries, not sockets, other SSH implementations or all remote-access paths.",
            "The Raspberry/Pi stateless QR vault remains RAM-only and must not add persistent secret storage or TROPIC01.",
        ],
    }
