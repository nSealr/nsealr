from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.integration_companion_fixtures import (
    build_fixture_verify_command,
    expected_fixture_output,
)


class IntegrationCompanionFixturesTests(unittest.TestCase):
    def fixture_specs(
        self,
        *,
        nip46: int = 5,
        policy_files: int = 1,
        connection_uris: int = 2,
        connection_token_responses: int = 1,
        relay_events: int = 2,
        relay_steps: int = 2,
        auth_challenges: int = 1,
        sessions: int = 1,
        accounts: int = 6,
        policies: int = 5,
        grants: int = 2,
        policy_changes: int = 2,
        policy_decisions: int = 9,
        route_selections: int = 6,
        route_refusals: int = 1,
        access_surfaces: int = 1,
        feature_matrices: int = 1,
        custody_contracts: int = 1,
        invalid: int = 77,
    ) -> Path:
        self._temp_specs = TemporaryDirectory()
        specs = Path(self._temp_specs.name)
        for relative, count in {
            "vectors/events": 0,
            "vectors/review": 0,
            "vectors/review-screens": 0,
            "vectors/review-display-frames": 0,
            "vectors/review-detail-pages": 0,
            "vectors/review-transcripts": 0,
            "vectors/nip46": nip46,
            "vectors/nip46-policy-files": policy_files,
            "vectors/nip46-connection-uris": connection_uris,
            "vectors/nip46-connection-token-responses": connection_token_responses,
            "vectors/nip46-relay-events": relay_events,
            "vectors/nip46-relay-steps": relay_steps,
            "vectors/nip46-auth-challenges": auth_challenges,
            "vectors/nip46-sessions": sessions,
            "vectors/accounts": accounts,
            "vectors/policies": policies,
            "vectors/grants": grants,
            "vectors/policy-changes": policy_changes,
            "vectors/policy-decisions": policy_decisions,
            "vectors/route-selections": route_selections,
            "vectors/route-refusals": route_refusals,
            "vectors/access-surfaces": access_surfaces,
            "vectors/features": feature_matrices,
            "vectors/custody": custody_contracts,
            "vectors/invalid": invalid,
        }.items():
            directory = specs / relative
            directory.mkdir(parents=True)
            for index in range(count):
                (directory / f"fixture-{index}.json").write_text("{}", encoding="utf-8")
        return specs

    def tearDown(self) -> None:
        temp_specs = getattr(self, "_temp_specs", None)
        if temp_specs is not None:
            temp_specs.cleanup()

    def test_fixture_verify_command_uses_live_specs_repository(self) -> None:
        command = build_fixture_verify_command(
            companion=Path("/repos/companion"),
            specs=Path("/repos/specs"),
        )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:3], ["pnpm", "nsealr", "fixture"])
        self.assertIn("verify", command.argv)
        self.assertIn("--specs", command.argv)
        self.assertIn(str(Path("/repos/specs")), command.argv)

    def test_fixture_verify_output_includes_review_display_frames(self) -> None:
        with TemporaryDirectory() as tmp:
            specs = Path(tmp)
            for relative, names in {
                "vectors/events": ["a", "b"],
                "vectors/review": ["a", "b", "c", "d", "e"],
                "vectors/review-screens": ["a", "b"],
                "vectors/review-display-frames": ["a", "b"],
                "vectors/review-detail-pages": ["a", "b", "c"],
                "vectors/review-transcripts": ["a", "b"],
                "vectors/nip46": ["a", "b", "c", "d", "e"],
                "vectors/nip46-policy-files": ["a"],
                "vectors/nip46-connection-uris": ["a", "b"],
                "vectors/nip46-connection-token-responses": ["a"],
                "vectors/nip46-relay-events": ["a", "b"],
                "vectors/nip46-relay-steps": ["a", "b"],
                "vectors/nip46-auth-challenges": ["a"],
                "vectors/nip46-sessions": ["a"],
                "vectors/accounts": ["a", "b", "c"],
                "vectors/policies": ["a", "b", "c"],
                "vectors/grants": ["a"],
                "vectors/policy-decisions": ["a", "b", "c", "d", "e", "f"],
                "vectors/route-selections": ["a", "b"],
                "vectors/route-refusals": ["a"],
                "vectors/access-surfaces": ["a"],
                "vectors/features": ["a"],
                "vectors/custody": ["a"],
                "vectors/invalid": ["a", "b", "c"],
            }.items():
                directory = specs / relative
                directory.mkdir(parents=True)
                for name in names:
                    (directory / f"{name}.json").write_text("{}", encoding="utf-8")

            output = expected_fixture_output(specs)

        self.assertIn("2 review-screen fixtures", output)
        self.assertIn("2 review display-frame fixtures", output)
        self.assertIn("3 review detail-page fixtures", output)
        self.assertIn("5 review fixtures", output)

    def test_fixture_verify_output_includes_nip46_payloads(self) -> None:
        self.assertIn("5 NIP-46 payload fixtures", expected_fixture_output(self.fixture_specs()))

    def test_fixture_verify_output_includes_nip46_policy_files(self) -> None:
        self.assertIn("1 NIP-46 policy-file fixture", expected_fixture_output(self.fixture_specs()))

    def test_fixture_verify_output_includes_nip46_connection_uris(self) -> None:
        self.assertIn("2 NIP-46 connection URI fixtures", expected_fixture_output(self.fixture_specs()))

    def test_fixture_verify_output_includes_nip46_connection_token_responses(self) -> None:
        self.assertIn("1 NIP-46 connection token response fixture", expected_fixture_output(self.fixture_specs()))

    def test_fixture_verify_output_includes_nip46_relay_events(self) -> None:
        self.assertIn("2 NIP-46 relay event fixtures", expected_fixture_output(self.fixture_specs()))

    def test_fixture_verify_output_includes_nip46_relay_steps(self) -> None:
        self.assertIn("2 NIP-46 relay step fixtures", expected_fixture_output(self.fixture_specs()))

    def test_fixture_verify_output_includes_nip46_auth_challenges(self) -> None:
        self.assertIn("1 NIP-46 auth challenge fixture", expected_fixture_output(self.fixture_specs()))

    def test_fixture_verify_output_includes_nip46_sessions(self) -> None:
        self.assertIn("1 NIP-46 session fixture", expected_fixture_output(self.fixture_specs()))

    def test_fixture_verify_output_includes_identity_policy_contracts(self) -> None:
        output = expected_fixture_output(self.fixture_specs())

        self.assertIn("6 account descriptors", output)
        self.assertIn("5 policy profiles", output)
        self.assertIn("2 policy change vectors", output)
        self.assertIn("2 grant descriptors", output)
        self.assertIn("9 policy decision vectors", output)
        self.assertIn("6 route selection vectors", output)
        self.assertIn("1 route-refusal contract", output)
        self.assertIn("1 access-surface vector", output)

    def test_fixture_verify_output_includes_feature_matrices(self) -> None:
        self.assertIn("1 feature matrix", expected_fixture_output(self.fixture_specs()))

    def test_fixture_verify_output_includes_custody_contracts(self) -> None:
        self.assertIn("1 persistent-secret custody contract", expected_fixture_output(self.fixture_specs()))

    def test_fixture_verify_output_includes_invalid_hardening_vectors(self) -> None:
        self.assertIn("77 invalid hardening fixtures", expected_fixture_output(self.fixture_specs()))


if __name__ == "__main__":
    unittest.main()
