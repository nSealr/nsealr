import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.integration.integration_feature_matrix import (
    EXPECTED_SIGNER_FAMILIES,
    validate_feature_matrix,
)


def valid_matrix() -> dict:
    return {
        "format": "nsealr-signer-feature-matrix-v0",
        "name": "signer-feature-matrix-v0",
        "solutions": {
            solution_id: {
                "label": expected["label"],
                "repository": expected["repository"],
                "product_goal": f"{expected['label']} goal",
                "features": {},
            }
            for solution_id, expected in EXPECTED_SIGNER_FAMILIES.items()
        },
    }


class FeatureMatrixIntegrationTests(unittest.TestCase):
    def test_validates_expected_signer_families_from_specs_matrix(self) -> None:
        validate_feature_matrix(Path("matrix.json"), valid_matrix())

    def test_rejects_missing_or_extra_signer_families(self) -> None:
        matrix = valid_matrix()
        matrix["solutions"].pop("esp32_qr_vault")
        matrix["solutions"]["extra_signer"] = {
            "label": "Extra",
            "repository": "extra",
            "product_goal": "Wrong",
            "features": {},
        }

        with self.assertRaisesRegex(ValueError, "first-class signer family drift"):
            validate_feature_matrix(Path("matrix.json"), matrix)

    def test_rejects_wrong_solution_repository_owner(self) -> None:
        matrix = valid_matrix()
        matrix["solutions"]["raspberry_qr_vault"]["repository"] = "vault"

        with self.assertRaisesRegex(ValueError, "repository owner drift"):
            validate_feature_matrix(Path("matrix.json"), matrix)



if __name__ == "__main__":
    unittest.main()
