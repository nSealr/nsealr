#!/usr/bin/env python3
"""Shared helpers for integrated integration scripts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Mapping


DEP0205_SUPPRESSION = "--disable-warning=DEP0205"
PNPM_VERSION = "10.33.4"
PINNED_PNPM_COMMAND = ["pnpm"]


def _node_options_with_dep0205_suppressed(existing: str | None) -> str:
    parts = existing.split() if existing else []
    if DEP0205_SUPPRESSION not in parts:
        parts.append(DEP0205_SUPPRESSION)
    return " ".join(parts)


def pinned_command(command: list[str]) -> list[str]:
    if command and command[0] == "pnpm":
        version = subprocess.run(["pnpm", "--version"], check=True, capture_output=True, text=True)
        if version.stdout.strip() != PNPM_VERSION:
            raise RuntimeError("pnpm version differs from the pinned product toolchain")
        return [*PINNED_PNPM_COMMAND, *command[1:]]
    return command


def env_for_command(command: list[str], base_env: Mapping[str, str] | None = None) -> dict[str, str] | None:
    env = None if base_env is None else dict(base_env)
    if (
        len(command) >= 2 and command[:2] == ["pnpm", "nsealr"]
    ) or (
        len(command) >= 3 and command[:3] == ["pnpm", "--silent", "nsealr"]
    ):
        env = dict(os.environ if base_env is None else base_env)
        env["NODE_OPTIONS"] = _node_options_with_dep0205_suppressed(env.get("NODE_OPTIONS"))
    return env


def run_command(
    command: list[str],
    cwd: Path,
    *,
    capture_output: bool = False,
    input: str | None = None,
    base_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            pinned_command(command),
            cwd=cwd,
            check=True,
            capture_output=capture_output,
            input=input,
            text=True,
            env=env_for_command(command, base_env=base_env),
        )
    except subprocess.CalledProcessError as error:
        if capture_output:
            if error.stdout:
                print(error.stdout, end="", file=sys.stdout)
            if error.stderr:
                print(error.stderr, end="", file=sys.stderr)
        raise


def install_pnpm_workspace(cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["CI"] = "true"
    return run_command(["pnpm", "install", "--frozen-lockfile"], cwd, base_env=env)


def build_pnpm_workspace(cwd: Path) -> subprocess.CompletedProcess[str]:
    return run_command(["pnpm", "build"], cwd)
