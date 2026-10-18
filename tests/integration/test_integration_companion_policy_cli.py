from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.integration_companion_policy_cli import build_policy_review_command, policy_change_vectors


class IntegrationCompanionPolicyCliTests(unittest.TestCase):
    def test_policy_review_command_uses_companion_cli_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-policy-cli-plan-") as temp_dir:
            temp = Path(temp_dir)
            command = build_policy_review_command(
                companion=Path("/repos/companion"),
                proposal_path=temp / "proposal.json",
                account_path=Path("/repos/specs/vectors/accounts/esp32-usb-device-slot-0.json"),
                current_policy_path=Path("/repos/specs/vectors/policies/manual-only-persistent-device.json"),
                proposed_policy_path=Path("/repos/specs/vectors/policies/scoped-automation-daily-use.json"),
                grant_paths=[Path("/repos/specs/vectors/grants/esp32-usb-kind-1-session.json")],
                out_path=temp / "review.json",
            )

        self.assertEqual(command.cwd, Path("/repos/companion"))
        self.assertEqual(command.argv[:4], ["pnpm", "nsealr", "policy", "review-change"])
        self.assertIn("--proposal", command.argv)
        self.assertIn(str(temp / "proposal.json"), command.argv)
        self.assertIn("--out", command.argv)
        self.assertIn(str(temp / "review.json"), command.argv)
        self.assertIn("--account", command.argv)
        self.assertIn("/repos/specs/vectors/accounts/esp32-usb-device-slot-0.json", command.argv)
        self.assertIn("--current-policy", command.argv)
        self.assertIn("/repos/specs/vectors/policies/manual-only-persistent-device.json", command.argv)
        self.assertIn("--proposed-policy", command.argv)
        self.assertIn("/repos/specs/vectors/policies/scoped-automation-daily-use.json", command.argv)
        self.assertIn("--grant", command.argv)
        self.assertIn("/repos/specs/vectors/grants/esp32-usb-kind-1-session.json", command.argv)

    def test_policy_change_vectors_are_discovered_from_specs_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nsealr-policy-vectors-") as temp_dir:
            specs = Path(temp_dir)
            vectors = specs / "vectors" / "policy-changes"
            vectors.mkdir(parents=True)
            vectors.joinpath("b.json").write_text('{"name":"b"}\n', encoding="utf-8")
            vectors.joinpath("a.json").write_text('{"name":"a"}\n', encoding="utf-8")

            discovered = policy_change_vectors(specs)

        self.assertEqual([vector["name"] for vector in discovered], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
