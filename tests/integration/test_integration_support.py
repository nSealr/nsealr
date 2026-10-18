from __future__ import annotations

import io
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import ANY, patch

from tests.integration.integration_support import (
    DEP0205_SUPPRESSION,
    PINNED_PNPM_COMMAND,
    build_pnpm_workspace,
    env_for_command,
    install_pnpm_workspace,
    pinned_command,
    run_command,
)


class IntegrationSupportTests(unittest.TestCase):
    def test_companion_cli_env_suppresses_only_node_dep0205_warning(self) -> None:
        env = env_for_command(["pnpm", "nsealr", "fixture", "verify"], base_env={"PATH": "/bin"})

        self.assertIsNotNone(env)
        self.assertEqual(env["PATH"], "/bin")
        self.assertEqual(env["NODE_OPTIONS"], DEP0205_SUPPRESSION)

    def test_companion_cli_env_preserves_existing_node_options_without_duplicates(self) -> None:
        env = env_for_command(
            ["pnpm", "nsealr", "nip46", "decide"],
            base_env={"NODE_OPTIONS": f"--trace-warnings {DEP0205_SUPPRESSION}"},
        )

        self.assertIsNotNone(env)
        self.assertEqual(env["NODE_OPTIONS"], f"--trace-warnings {DEP0205_SUPPRESSION}")

    def test_non_companion_cli_commands_do_not_get_node_warning_suppression(self) -> None:
        self.assertEqual(env_for_command(["pnpm", "install"], base_env={"PATH": "/bin"}), {"PATH": "/bin"})
        self.assertEqual(env_for_command(["make", "setup"], base_env={"PATH": "/bin"}), {"PATH": "/bin"})

    def test_pnpm_commands_are_pinned_before_subprocess_execution(self) -> None:
        self.assertEqual(
            pinned_command(["pnpm", "nsealr", "fixture", "verify"]),
            [*PINNED_PNPM_COMMAND, "nsealr", "fixture", "verify"],
        )
        self.assertEqual(pinned_command(["make", "ci"]), ["make", "ci"])

    def test_pnpm_workspace_install_uses_ci_frozen_lockfile(self) -> None:
        workspace = Path("/tmp/nsealr-companion")
        completed = subprocess.CompletedProcess(args=["pnpm"], returncode=0)

        with patch("tests.integration.integration_support.run_command", return_value=completed) as run:
            result = install_pnpm_workspace(workspace)

        self.assertIs(result, completed)
        run.assert_called_once_with(["pnpm", "install", "--frozen-lockfile"], workspace, base_env=ANY)
        self.assertEqual(run.call_args.kwargs["base_env"]["CI"], "true")

    def test_pnpm_workspace_build_uses_pinned_pnpm_build(self) -> None:
        workspace = Path("/tmp/nsealr-companion")
        completed = subprocess.CompletedProcess(args=["pnpm"], returncode=0)

        with patch("tests.integration.integration_support.run_command", return_value=completed) as run:
            result = build_pnpm_workspace(workspace)

        self.assertIs(result, completed)
        run.assert_called_once_with(["pnpm", "build"], workspace)

    def test_captured_command_failures_relay_stdout_and_stderr(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(subprocess.CalledProcessError):
            run_command(
                [
                    sys.executable,
                    "-c",
                    "import sys; print('visible stdout'); print('visible stderr', file=sys.stderr); sys.exit(3)",
                ],
                Path.cwd(),
                capture_output=True,
            )

        self.assertIn("visible stdout", stdout.getvalue())
        self.assertIn("visible stderr", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
