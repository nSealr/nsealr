from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.integration_companion_nip46_cli import (
    build_nip46_auth_challenge_approval_command,
    build_nip46_auth_challenge_review_command,
    build_nip46_connect_approval_command,
    build_nip46_connect_review_command,
    build_nip46_connection_token_response_command,
    build_nip46_connection_uri_command,
    build_nip46_decide_command,
    build_nip46_policy_file_command,
    build_nip46_session_checkpoint_command,
    assert_auth_challenge_vector_inventory,
    invalid_auth_challenge_relay_step_vectors,
    invalid_connection_token_response_vectors,
    invalid_connection_uri_vectors,
    invalid_policy_file_vectors,
)


class IntegrationCompanionNip46CliTests(unittest.TestCase):
    def test_nip46_decide_command_uses_companion_cli_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_nip46_decide_command(
                companion=Path("/repos/companion"),
                message_path=temp / "message.json",
                permissions="sign_event:1",
                out_path=temp / "decision.json",
            )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "nip46", "decide"])
        self.assertIn("--message", command.argv)
        self.assertIn("--permissions", command.argv)
        self.assertIn("sign_event:1", command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(temp / "decision.json"), command.argv)

    def test_nip46_decide_command_can_use_policy_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_nip46_policy_file_command(
                companion=Path("/repos/companion"),
                message_path=temp / "message.json",
                policy_path=temp / "policy.json",
                out_path=temp / "decision.json",
            )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "nip46", "decide"])
        self.assertIn("--policy-file", command.argv)
        self.assertIn(str(temp / "policy.json"), command.argv)
        self.assertNotIn("--permissions", command.argv)

    def test_nip46_connect_review_command_uses_companion_cli_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_nip46_connect_review_command(
                companion=Path("/repos/companion"),
                message_path=temp / "connect-message.json",
                out_path=temp / "connect-review.json",
            )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "nip46", "review-connect"])
        self.assertIn("--message", command.argv)
        self.assertIn(str(temp / "connect-message.json"), command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(temp / "connect-review.json"), command.argv)

    def test_nip46_connect_approval_command_uses_digest_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_nip46_connect_approval_command(
                companion=Path("/repos/companion"),
                review_path=temp / "connect-review.json",
                reviewed_connect_digest="a" * 64,
                approved_at=1900000001,
                out_path=temp / "connect-approval.json",
            )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "nip46", "approve-connect"])
        self.assertIn("--review", command.argv)
        self.assertIn(str(temp / "connect-review.json"), command.argv)
        self.assertIn("--reviewed-connect-digest", command.argv)
        self.assertIn("a" * 64, command.argv)
        self.assertIn("--approved-at", command.argv)
        self.assertIn("1900000001", command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(temp / "connect-approval.json"), command.argv)

    def test_nip46_auth_challenge_review_command_uses_file_backed_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_nip46_auth_challenge_review_command(
                companion=Path("/repos/companion"),
                step_path=temp / "auth-challenge-step.json",
                out_path=temp / "auth-challenge-review.json",
            )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "nip46", "review-auth-challenge"])
        self.assertIn("--step", command.argv)
        self.assertIn(str(temp / "auth-challenge-step.json"), command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(temp / "auth-challenge-review.json"), command.argv)

    def test_nip46_auth_challenge_approval_command_uses_digest_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_nip46_auth_challenge_approval_command(
                companion=Path("/repos/companion"),
                review_path=temp / "auth-challenge-review.json",
                reviewed_auth_challenge_digest="b" * 64,
                approved_at=1900000200,
                out_path=temp / "auth-challenge-approval.json",
            )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "nip46", "approve-auth-challenge"])
        self.assertIn("--review", command.argv)
        self.assertIn(str(temp / "auth-challenge-review.json"), command.argv)
        self.assertIn("--reviewed-auth-challenge-digest", command.argv)
        self.assertIn("b" * 64, command.argv)
        self.assertIn("--approved-at", command.argv)
        self.assertIn("1900000200", command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(temp / "auth-challenge-approval.json"), command.argv)

    def test_nip46_session_checkpoint_command_uses_reviewed_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_nip46_session_checkpoint_command(
                companion=Path("/repos/companion"),
                review_path=temp / "connect-review.json",
                approval_path=temp / "connect-approval.json",
                name="checkpoint-1",
                client_pubkey="b" * 64,
                relays=["wss://relay1.example.com/", "wss://relay2.example.com/"],
                policy_path=temp / "policy.json",
                expires_at=1900003601,
                out_path=temp / "session.json",
            )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "nip46", "create-session-checkpoint"])
        self.assertIn("--review", command.argv)
        self.assertIn(str(temp / "connect-review.json"), command.argv)
        self.assertIn("--approval", command.argv)
        self.assertIn(str(temp / "connect-approval.json"), command.argv)
        self.assertIn("--client-pubkey", command.argv)
        self.assertIn("b" * 64, command.argv)
        self.assertIn("--relays", command.argv)
        self.assertIn("wss://relay1.example.com/,wss://relay2.example.com/", command.argv)
        self.assertIn("--policy-file", command.argv)
        self.assertIn(str(temp / "policy.json"), command.argv)
        self.assertIn("--expires-at", command.argv)
        self.assertIn("1900003601", command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(temp / "session.json"), command.argv)

    def test_nip46_connection_uri_command_uses_file_backed_cli_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_nip46_connection_uri_command(
                companion=Path("/repos/companion"),
                uri_path=temp / "token.txt",
                out_path=temp / "descriptor.json",
            )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "nip46", "parse-connection-uri"])
        self.assertIn("--uri-file", command.argv)
        self.assertIn(str(temp / "token.txt"), command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(temp / "descriptor.json"), command.argv)
        self.assertNotIn("--uri", command.argv)

    def test_nip46_connection_token_response_command_uses_file_backed_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_nip46_connection_token_response_command(
                companion=Path("/repos/companion"),
                uri_path=temp / "token.txt",
                step_path=temp / "response-step.json",
                out_path=temp / "response.json",
            )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "nip46", "verify-connection-token-response"])
        self.assertIn("--uri-file", command.argv)
        self.assertIn(str(temp / "token.txt"), command.argv)
        self.assertIn("--step", command.argv)
        self.assertIn(str(temp / "response-step.json"), command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(temp / "response.json"), command.argv)

    def test_invalid_connection_uri_vectors_are_discovered_by_category(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-invalid-") as temp_dir:
            specs = Path(temp_dir)
            invalid = specs / "vectors/invalid"
            invalid.mkdir(parents=True)
            invalid.joinpath("connection.json").write_text(
                """
{
  "name": "connection",
  "category": "nip46-connection-uri",
  "uri": "nostrconnect://bad"
}
""".lstrip(),
                encoding="utf-8",
            )
            invalid.joinpath("payload.json").write_text(
                """
{
  "name": "payload",
  "category": "nip46"
}
""".lstrip(),
                encoding="utf-8",
            )

            vectors = invalid_connection_uri_vectors(specs)

        self.assertEqual([vector["name"] for vector in vectors], ["connection"])

    def test_invalid_connection_token_response_vectors_are_discovered_by_category(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-invalid-token-response-") as temp_dir:
            specs = Path(temp_dir)
            invalid = specs / "vectors/invalid"
            invalid.mkdir(parents=True)
            invalid.joinpath("token-response.json").write_text(
                """
{
  "name": "token-response",
  "category": "nip46-connection-token-response",
  "connection_token_response": {
    "connection_uri": "nostrconnect://bad",
    "response_step": {}
  }
}
""".lstrip(),
                encoding="utf-8",
            )
            invalid.joinpath("connection.json").write_text(
                """
{
  "name": "connection",
  "category": "nip46-connection-uri",
  "uri": "nostrconnect://bad"
}
""".lstrip(),
                encoding="utf-8",
            )

            vectors = invalid_connection_token_response_vectors(specs)

        self.assertEqual([vector["name"] for vector in vectors], ["token-response"])

    def test_invalid_auth_challenge_relay_step_vectors_are_discovered_by_category(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-invalid-auth-challenge-") as temp_dir:
            specs = Path(temp_dir)
            invalid = specs / "vectors/invalid"
            invalid.mkdir(parents=True)
            invalid.joinpath("auth-challenge.json").write_text(
                """
{
  "name": "auth-challenge",
  "category": "nip46-relay-step",
  "relay_step": {
    "format": "nsealr-nip46-relay-response-step-v1",
    "decrypted_message": {
      "result": "auth_url"
    }
  }
}
""".lstrip(),
                encoding="utf-8",
            )
            invalid.joinpath("public-key.json").write_text(
                """
{
  "name": "public-key",
  "category": "nip46-relay-step",
  "relay_step": {
    "format": "nsealr-nip46-relay-response-step-v1",
    "decrypted_message": {
      "result": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    }
  }
}
""".lstrip(),
                encoding="utf-8",
            )

            vectors = invalid_auth_challenge_relay_step_vectors(specs)

        self.assertEqual([vector["name"] for vector in vectors], ["auth-challenge"])

    def test_auth_negative_inventory_requires_each_case_and_rejects_extras(self) -> None:
        names = (
            "relay-step-response-auth-url-with-credentials.json",
            "relay-step-response-auth-url-with-fragment.json",
            "relay-step-response-auth-url-wrong-scheme.json",
        )
        with tempfile.TemporaryDirectory(prefix="nsealr-auth-inventory-") as directory:
            specs = Path(directory)
            invalid = specs / "vectors/invalid"
            invalid.mkdir(parents=True)
            originals = {}
            for name in names:
                vector = {"name": name.removesuffix(".json"), "category": "nip46-relay-step",
                          "relay_step": {"format": "nsealr-nip46-relay-response-step-v1",
                                         "decrypted_message": {"result": "auth_url"}}}
                originals[name] = json.dumps(vector)
                (invalid / name).write_text(originals[name])
            # Malformed and unrelated vectors must not be selected as auth negatives.
            (invalid / "malformed.json").write_text(json.dumps({"category": "nip46-relay-step", "relay_step": None}))
            unrelated = json.loads(originals[names[0]])
            unrelated["category"] = "other"
            (invalid / "wrong-category.json").write_text(json.dumps(unrelated))
            vectors = invalid_auth_challenge_relay_step_vectors(specs)
            self.assertEqual(len(vectors), 3)
            assert_auth_challenge_vector_inventory(specs, vectors)
            for name in names:
                with self.subTest(missing=name):
                    (invalid / name).unlink()
                    with self.assertRaises(AssertionError):
                        assert_auth_challenge_vector_inventory(specs, invalid_auth_challenge_relay_step_vectors(specs))
                    (invalid / name).write_text(originals[name])
                with self.subTest(stale_version=name):
                    stale = json.loads(originals[name])
                    stale["relay_step"]["format"] = "nsealr-nip46-relay-response-step-v0"
                    (invalid / name).write_text(json.dumps(stale))
                    with self.assertRaises(AssertionError):
                        assert_auth_challenge_vector_inventory(specs, invalid_auth_challenge_relay_step_vectors(specs))
                    (invalid / name).write_text(originals[name])
            extra = json.loads(originals[names[0]])
            extra["name"] = "unexpected-extra"
            (invalid / "extra.json").write_text(json.dumps(extra))
            with self.assertRaises(AssertionError):
                assert_auth_challenge_vector_inventory(specs, invalid_auth_challenge_relay_step_vectors(specs))
            (invalid / "extra.json").unlink()
            vectors = invalid_auth_challenge_relay_step_vectors(specs)
            for omitted in range(3):
                with self.subTest(selected_case_omitted=omitted), self.assertRaises(AssertionError):
                    assert_auth_challenge_vector_inventory(specs, vectors[:omitted] + vectors[omitted + 1:])
            assert_auth_challenge_vector_inventory(specs, vectors)

    def test_invalid_policy_file_vectors_are_discovered_by_category(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-nip46-invalid-policy-") as temp_dir:
            specs = Path(temp_dir)
            invalid = specs / "vectors/invalid"
            invalid.mkdir(parents=True)
            invalid.joinpath("policy.json").write_text(
                """
{
  "name": "policy",
  "category": "nip46-policy-file",
  "policy_file": {
    "format": "nsealr-nip46-policy-v0",
    "approved_permissions": []
  }
}
""".lstrip(),
                encoding="utf-8",
            )
            invalid.joinpath("payload.json").write_text(
                """
{
  "name": "payload",
  "category": "nip46"
}
""".lstrip(),
                encoding="utf-8",
            )

            vectors = invalid_policy_file_vectors(specs)

        self.assertEqual([vector["name"] for vector in vectors], ["policy"])


if __name__ == "__main__":
    unittest.main()
