from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.integration.integration_vault_companion import (
    assert_display_frame_log,
    assert_review_transcript_log,
    assert_screen_review_files_equal,
    assert_session_backup_result_file,
    assert_session_import_review_file,
    build_detail_flow_command,
    build_flow_command,
    build_companion_review_detail_pages_command,
    build_review_detail_pages_command,
    build_review_commands,
    build_screen_review_commands,
    build_session_backup_source_command,
    build_session_import_review_command,
)


class IntegrationVaultCompanionTests(unittest.TestCase):
    def test_review_commands_cover_companion_preview_and_vault_review(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            temp = Path(temp_dir)
            commands = build_review_commands(
                companion=Path("/repos/companion"),
                raspberry=Path("/repos/raspberry"),
                request_path=temp / "request.qr",
                author_pubkey="1" * 64,
                companion_review_path=temp / "companion-review.json",
                vault_review_path=temp / "vault-review.json",
            )

        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0].cwd, Path("/repos/companion"))
        self.assertIn("review-request", commands[0].argv)
        self.assertIn("--request-format", commands[0].argv)
        self.assertIn("qr", commands[0].argv)
        self.assertIn("--author-pubkey", commands[0].argv)
        self.assertEqual(commands[1].cwd, Path("/repos/raspberry"))
        self.assertIn("nsealr_vault", commands[1].argv)
        self.assertIn("review", commands[1].argv)
        self.assertIn("--input-format", commands[1].argv)
        self.assertIn("qr", commands[1].argv)
        self.assertIn("--author-pubkey", commands[1].argv)

    def test_screen_review_commands_compare_companion_and_vault_approval_digest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            temp = Path(temp_dir)
            commands = build_screen_review_commands(
                companion=Path("/repos/companion"),
                raspberry=Path("/repos/raspberry"),
                request_path=temp / "request.qr",
                author_pubkey="1" * 64,
                companion_screen_review_path=temp / "companion-screen-review.json",
                vault_screen_review_path=temp / "vault-screen-review.json",
            )

        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0].cwd, Path("/repos/companion"))
        self.assertIn("review-request", commands[0].argv)
        self.assertIn("--screen-review", commands[0].argv)
        self.assertIn("--author-pubkey", commands[0].argv)
        self.assertEqual(commands[1].cwd, Path("/repos/raspberry"))
        self.assertIn("nsealr_vault", commands[1].argv)
        self.assertIn("review", commands[1].argv)
        self.assertIn("--output-format", commands[1].argv)
        self.assertIn("screen-json", commands[1].argv)
        self.assertIn("--author-pubkey", commands[1].argv)

    def test_review_detail_pages_command_exports_vault_detail_pages(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_review_detail_pages_command(
                raspberry=Path("/repos/raspberry"),
                request_path=temp / "request.qr",
                author_pubkey="1" * 64,
                detail_pages_path=temp / "review-detail-pages.json",
            )

        self.assertEqual(command.cwd, Path("/repos/raspberry"))
        self.assertIn("review", command.argv)
        self.assertIn("--output-format", command.argv)
        self.assertIn("detail-pages-json", command.argv)
        self.assertIn("--max-compact-line-chars", command.argv)
        self.assertIn("48", command.argv)
        self.assertIn("--author-pubkey", command.argv)

    def test_companion_review_detail_pages_command_exports_preview_detail_pages(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_companion_review_detail_pages_command(
                companion=Path("/repos/companion"),
                request_path=temp / "request.qr",
                author_pubkey="1" * 64,
                detail_pages_path=temp / "companion-detail-pages.json",
            )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertIn("review-request", command.argv)
        self.assertIn("--request-format", command.argv)
        self.assertIn("qr", command.argv)
        self.assertIn("--detail-pages", command.argv)
        self.assertIn("--author-pubkey", command.argv)
        self.assertIn("--max-compact-line-chars", command.argv)
        self.assertIn("48", command.argv)

    def test_flow_command_uses_hardware_style_qr_flow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_flow_command(
                raspberry=Path("/repos/raspberry"),
                mnemonic="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
                account=0,
                request_path=temp / "request.qr",
                screen_review_path=temp / "screen-review.json",
                response_path=temp / "response.qr",
                display_frame_log_path=temp / "display-frames.json",
                review_transcript_log_path=temp / "review-transcript.json",
            )

        self.assertEqual(command.cwd, Path("/repos/raspberry"))
        self.assertIn("flow", command.argv)
        self.assertIn("--mnemonic-words-stdin", command.argv)
        self.assertIn("--mnemonic-word-count", command.argv)
        self.assertIn("12", command.argv)
        self.assertNotIn("--mnemonic-stdin", command.argv)
        self.assertNotIn("--mnemonic-file", command.argv)
        self.assertNotIn("--secret-key", command.argv)
        self.assertEqual(
            command.stdin_text,
            "abandon\nabandon\nabandon\nabandon\nabandon\nabandon\nabandon\nabandon\nabandon\nabandon\nabandon\nabout\n",
        )
        self.assertIn("--account", command.argv)
        self.assertIn("0", command.argv)
        self.assertIn("--review", command.argv)
        self.assertIn(str(temp / "screen-review.json"), command.argv)
        self.assertIn("--response", command.argv)
        self.assertIn(str(temp / "response.qr"), command.argv)
        self.assertNotIn("--approve", command.argv)
        self.assertIn("--button-sequence", command.argv)
        self.assertIn("next,next,next,approve", command.argv)
        self.assertIn("--display-frame-log", command.argv)
        self.assertIn(str(temp / "display-frames.json"), command.argv)
        self.assertIn("--review-transcript-log", command.argv)
        self.assertIn(str(temp / "review-transcript.json"), command.argv)
        self.assertIn("--max-line-chars", command.argv)
        self.assertIn("64", command.argv)

    def test_detail_flow_command_uses_logical_review_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_detail_flow_command(
                raspberry=Path("/repos/raspberry"),
                mnemonic="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
                account=0,
                request_path=temp / "request.qr",
                detail_review_path=temp / "detail-review.json",
                response_path=temp / "detail-response.qr",
            )

        self.assertEqual(command.cwd, Path("/repos/raspberry"))
        self.assertIn("flow", command.argv)
        self.assertIn("--mnemonic-words-stdin", command.argv)
        self.assertIn("--mnemonic-word-count", command.argv)
        self.assertIn("12", command.argv)
        self.assertNotIn("--mnemonic-stdin", command.argv)
        self.assertNotIn("--mnemonic-file", command.argv)
        self.assertEqual(
            command.stdin_text,
            "abandon\nabandon\nabandon\nabandon\nabandon\nabandon\nabandon\nabandon\nabandon\nabandon\nabandon\nabout\n",
        )
        self.assertIn("--review-mode", command.argv)
        self.assertIn("detail", command.argv)
        self.assertIn("--button-sequence", command.argv)
        self.assertIn("next,next,next,approve", command.argv)
        self.assertIn(str(temp / "detail-review.json"), command.argv)

    def test_detail_flow_command_can_emit_animated_qr_response(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_detail_flow_command(
                raspberry=Path("/repos/raspberry"),
                mnemonic="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
                account=0,
                request_path=temp / "request.qr",
                detail_review_path=temp / "detail-review.json",
                response_path=temp / "detail-response.qra",
                output_format="qr-animated",
            )

        self.assertIn("--output-format", command.argv)
        self.assertIn("qr-animated", command.argv)
        self.assertIn(str(temp / "detail-response.qra"), command.argv)

    def test_session_import_review_command_uses_raspberry_review_import_cli(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_session_import_review_command(
                raspberry=Path("/repos/raspberry"),
                source_argument="--seedqr-stdin",
                label="SeedQR vector 1",
                source_text="00010002",
                review_path=temp / "import-review.json",
            )

        self.assertEqual(command.cwd, Path("/repos/raspberry"))
        self.assertEqual(command.argv[:3], ["/repos/raspberry/.venv/bin/python", "-m", "nsealr_vault"])
        self.assertIn("review-import", command.argv)
        self.assertIn("--seedqr-stdin", command.argv)
        self.assertIn("--label", command.argv)
        self.assertIn("SeedQR vector 1", command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(temp / "import-review.json"), command.argv)
        self.assertEqual(command.stdin_text, "00010002\n")

    def test_session_backup_source_command_uses_raspberry_backup_source_cli(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_session_backup_source_command(
                raspberry=Path("/repos/raspberry"),
                source_argument="--nsec-stdin",
                label="nsec test vector",
                source_text="nsec1example",
                result_path=temp / "backup-result.json",
            )

        self.assertEqual(command.cwd, Path("/repos/raspberry"))
        self.assertEqual(command.argv[:3], ["/repos/raspberry/.venv/bin/python", "-m", "nsealr_vault"])
        self.assertIn("backup-source", command.argv)
        self.assertIn("--nsec-stdin", command.argv)
        self.assertIn("--button-sequence", command.argv)
        self.assertIn("next,approve", command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(temp / "backup-result.json"), command.argv)
        self.assertEqual(command.stdin_text, "nsec1example\n")

    def test_session_backup_result_assertion_rejects_review_secret_leak(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            result_path = Path(temp_dir) / "backup-result.json"
            vector = {
                "review_id": "session-backup-test",
                "approval_digest": "a" * 64,
                "pages": [{"lines": ["nsec1example"]}],
                "backup_payload": {"nsec": "nsec1example"},
            }
            result_path.write_text(
                json.dumps(
                    {
                        "format": "nsealr-session-source-backup-result-v0",
                        "review": {
                            "review_id": vector["review_id"],
                            "approval_digest": vector["approval_digest"],
                            "pages": [{"lines": ["nsec1example"]}],
                        },
                        "approved": True,
                        "revealed": True,
                        "backup_payload": vector["backup_payload"],
                        "transcript": [{"revealed": True}],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(AssertionError, "session backup review leaks source material"):
                assert_session_backup_result_file(result_path, vector, ["nsec1example"])

    def test_display_frame_log_assertion_checks_titles_and_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            frame_log_path = Path(temp_dir) / "display-frames.json"
            frame_log_path.write_text(
                """
[
  {
    "title": "Event",
    "page_indicator": "Page 1/4",
    "body_lines": ["Kind 1"],
    "action_hint": "Next"
  },
  {
    "title": "Content",
    "page_indicator": "Page 2/4",
    "body_lines": ["xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    "action_hint": "Next"
  },
  {
    "title": "Tags",
    "page_indicator": "Page 3/4",
    "body_lines": ["No tags"],
    "action_hint": "Next"
  },
  {
    "title": "Decision",
    "page_indicator": "Page 4/4",
    "body_lines": ["Approve signing only if all", "pages match."],
    "action_hint": "Approve / Reject"
  }
]
""".strip()
                + "\n",
                encoding="utf-8",
            )

            assert_display_frame_log(frame_log_path)

    def test_screen_review_assertion_checks_flow_output_digest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            temp = Path(temp_dir)
            expected_path = temp / "expected-screen-review.json"
            actual_path = temp / "actual-screen-review.json"
            expected_path.write_text(
                """
{
  "format": "screen-pages",
  "request_id": "req-1",
  "approval_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "pages": []
}
""".strip()
                + "\n",
                encoding="utf-8",
            )
            actual_path.write_text(expected_path.read_text(encoding="utf-8"), encoding="utf-8")

            assert_screen_review_files_equal(actual_path, expected_path)

            actual_path.write_text(
                """
{
  "format": "screen-pages",
  "request_id": "req-1",
  "approval_digest": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "pages": []
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(AssertionError, "screen-review JSON mismatch"):
                assert_screen_review_files_equal(actual_path, expected_path)

    def test_session_import_review_assertion_checks_vector_subset_and_secret_leak(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            temp = Path(temp_dir)
            review_path = temp / "import-review.json"
            vector = {
                "review_id": "session-import-abc",
                "approval_digest": "a" * 64,
                "pages": [{"title": "Import source", "lines": ["Secret: hidden"]}],
            }
            review_path.write_text(json.dumps(vector) + "\n", encoding="utf-8")

            assert_session_import_review_file(review_path, vector, ["secret material"])

            leaking_vector = dict(vector, pages=[{"title": "Import source", "lines": ["secret material"]}])
            review_path.write_text(json.dumps(leaking_vector) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(AssertionError, "leaks source material"):
                assert_session_import_review_file(review_path, leaking_vector, ["secret material"])

    def test_review_transcript_log_assertion_checks_displayed_frames_and_buttons(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-test-plan-") as temp_dir:
            temp = Path(temp_dir)
            display_frame_log_path = temp / "display-frames.json"
            transcript_log_path = temp / "review-transcript.json"
            display_frame_log_path.write_text(
                """
[
  {
    "title": "Event",
    "page_indicator": "Page 1/2",
    "body_lines": ["Kind 1"],
    "action_hint": "Next"
  },
  {
    "title": "Decision",
    "page_indicator": "Page 2/2",
    "body_lines": ["Approve signing only if all pages match."],
    "action_hint": "Approve / Reject"
  }
]
""".strip()
                + "\n",
                encoding="utf-8",
            )
            transcript_log_path.write_text(
                """
[
  {
    "frame": {
      "title": "Event",
      "page_indicator": "Page 1/2",
      "body_lines": ["Kind 1"],
      "action_hint": "Next"
    },
    "button": "next",
    "decision": null,
    "approved_for_signing": false
  },
  {
    "frame": {
      "title": "Decision",
      "page_indicator": "Page 2/2",
      "body_lines": ["Approve signing only if all pages match."],
      "action_hint": "Approve / Reject"
    },
    "button": "approve",
    "decision": true,
    "approved_for_signing": true
  }
]
""".strip()
                + "\n",
                encoding="utf-8",
            )

            assert_review_transcript_log(transcript_log_path, display_frame_log_path, ["next", "approve"])

            transcript_log_path.write_text(
                """
[
  {
    "frame": {
      "title": "Event",
      "page_indicator": "Page 1/2",
      "body_lines": ["Kind 1"],
      "action_hint": "Next"
    },
    "button": "approve",
    "decision": true,
    "approved_for_signing": true
  }
]
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(AssertionError, "review-transcript length mismatch"):
                assert_review_transcript_log(transcript_log_path, display_frame_log_path, ["next", "approve"])


if __name__ == "__main__":
    unittest.main()
