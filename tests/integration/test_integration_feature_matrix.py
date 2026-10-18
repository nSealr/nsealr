import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.integration_feature_matrix import (
    EXPECTED_SIGNER_FAMILIES,
    validate_feature_matrix,
    validate_feature_matrix_docs,
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

    def test_lab_docs_must_reference_feature_matrix_contract(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = [
                root / "docs/historical-feature-contract-01.md",
                root / "docs/historical-feature-contract-02.md",
                root / "docs/historical-feature-contract-03.md",
            ]
            for doc in docs:
                doc.parent.mkdir(parents=True, exist_ok=True)
                doc.write_text(
                    "Feature\nConformance v0\n"
                    "vectors/features/signer-feature-matrix-v0.json\n"
                    "same behavior when present\n",
                    encoding="utf-8",
                )

            validate_feature_matrix_docs(docs)

    def test_lab_docs_reject_missing_contract_reference(self) -> None:
        with TemporaryDirectory() as tmp:
            doc = Path(tmp) / "docs/historical-feature-contract-01.md"
            doc.parent.mkdir(parents=True)
            doc.write_text("Solution Matrix\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "feature matrix contract"):
                validate_feature_matrix_docs([doc])


if __name__ == "__main__":
    unittest.main()
