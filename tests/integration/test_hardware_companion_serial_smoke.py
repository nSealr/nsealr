from __future__ import annotations

import unittest
from pathlib import Path

from tests.integration.optional.hardware_companion_serial_smoke import (
    assert_expected_response,
    build_request_command,
    build_serial_line_exchange_command,
    build_sign_event_request_command,
    build_unwrap_response_command,
    build_wrap_request_command,
    extract_first_protocol_frame,
    pnpm_command,
)


class HardwareCompanionSerialSmokeTests(unittest.TestCase):
    def test_commands_drive_companion_request_bound_serial_unwrap(self) -> None:
        companion = Path("/repos/companion")
        request = Path("/tmp/request.json")
        request_frame = Path("/tmp/request.frame")
        response_frame = Path("/tmp/response.frame")
        response = Path("/tmp/response.json")

        create = build_request_command(
            companion=companion,
            method="get-capabilities",
            request_id="lab-hw-capabilities",
            out=request,
            pnpm=["pnpm"],
        )
        wrap = build_wrap_request_command(companion=companion, request=request, out=request_frame, pnpm=["pnpm"])
        unwrap = build_unwrap_response_command(
            companion=companion,
            request=request,
            response_frame=response_frame,
            out=response,
            pnpm=["pnpm"],
        )

        self.assertEqual(create.argv[:4], ["pnpm", "nsealr", "request", "get-capabilities"])
        self.assertIn("lab-hw-capabilities", create.argv)
        self.assertEqual(wrap.argv[:4], ["pnpm", "nsealr", "serial-frame", "wrap-request"])
        self.assertEqual(unwrap.argv[:4], ["pnpm", "nsealr", "serial-frame", "unwrap-response"])
        self.assertIn("--request", unwrap.argv)
        self.assertIn(str(request), unwrap.argv)

    def test_sign_event_command_uses_shared_template_and_request_id(self) -> None:
        command = build_sign_event_request_command(
            companion=Path("/repos/companion"),
            event_template=Path("/tmp/template.json"),
            request_id="lab-hw-sign-event-disabled",
            out=Path("/tmp/request.json"),
            pnpm=["pnpm"],
        )

        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "request", "sign-event"])
        self.assertIn("--event-template", command.argv)
        self.assertIn(str(Path("/tmp/template.json")), command.argv)
        self.assertIn("--request-id", command.argv)
        self.assertIn("lab-hw-sign-event-disabled", command.argv)

    def test_serial_line_exchange_command_uses_companion_cli_directly(self) -> None:
        command = build_serial_line_exchange_command(
            companion=Path("/repos/companion"),
            port="/dev/cu.usbmodem1101",
            request=Path("/tmp/request.json"),
            out=Path("/tmp/response.json"),
            timeout_ms=5000,
            pnpm=["pnpm"],
        )

        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "serial-line", "exchange"])
        self.assertIn("--port", command.argv)
        self.assertIn("/dev/cu.usbmodem1101", command.argv)
        self.assertIn("--request", command.argv)
        self.assertIn(str(Path("/tmp/request.json")), command.argv)
        self.assertIn("--timeout-ms", command.argv)
        self.assertIn("5000", command.argv)

    def test_extracts_first_protocol_frame_after_device_logs(self) -> None:
        frame = "nsealr1f:response:payload:1111111111111111\n"

        self.assertEqual(extract_first_protocol_frame(f"I boot: log line\r\n{frame}tail"), frame)
        self.assertIsNone(extract_first_protocol_frame("nsealr1f:response:partial"))

    def test_pnpm_command_always_uses_pinned_runner(self) -> None:
        self.assertEqual(pnpm_command(), ["npm", "exec", "--yes", "--package=pnpm@10.33.4", "--", "pnpm"])

    def test_expected_response_accepts_disabled_sign_event_only(self) -> None:
        assert_expected_response(
            "sign-event-disabled",
            {
                "ok": False,
                "error": {
                    "code": "signing_disabled",
                    "message": "Signing disabled",
                    "retryable": False,
                },
            },
        )

        with self.assertRaisesRegex(AssertionError, "signing_disabled"):
            assert_expected_response("sign-event-disabled", {"ok": True})


if __name__ == "__main__":
    unittest.main()
