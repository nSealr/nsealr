from __future__ import annotations

import unittest
from pathlib import Path

from scripts.integration_companion_serial_frame_cli import (
    build_create_request_command,
    build_unwrap_response_command,
    build_wrap_request_command,
)


class IntegrationCompanionSerialFrameCliTests(unittest.TestCase):
    def test_create_request_command_uses_companion_request_cli(self) -> None:
        command = build_create_request_command(
            companion=Path("/repos/companion"),
            method="get-signing-status",
            request_id="req-lab-signing-status",
            out=Path("/tmp/request.json"),
        )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "request", "get-signing-status"])
        self.assertIn("--request-id", command.argv)
        self.assertIn("req-lab-signing-status", command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(Path("/tmp/request.json")), command.argv)

    def test_wrap_request_command_uses_companion_serial_frame_cli(self) -> None:
        command = build_wrap_request_command(
            companion=Path("/repos/companion"),
            request=Path("/tmp/request.json"),
            out=Path("/tmp/request.frame"),
        )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "serial-frame", "wrap-request"])
        self.assertIn("--request", command.argv)
        self.assertIn(str(Path("/tmp/request.json")), command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(Path("/tmp/request.frame")), command.argv)

    def test_unwrap_response_command_uses_companion_serial_frame_cli(self) -> None:
        command = build_unwrap_response_command(
            companion=Path("/repos/companion"),
            request=Path("/tmp/request.json"),
            response_frame=Path("/tmp/response.frame"),
            out=Path("/tmp/response.json"),
        )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "serial-frame", "unwrap-response"])
        self.assertIn("--request", command.argv)
        self.assertIn(str(Path("/tmp/request.json")), command.argv)
        self.assertIn("--response-frame", command.argv)
        self.assertIn(str(Path("/tmp/response.frame")), command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(Path("/tmp/response.json")), command.argv)


if __name__ == "__main__":
    unittest.main()
