#!/usr/bin/env python3
"""Validate the shared signer feature matrix against lab taxonomy docs."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORG = ROOT.parent
FEATURE_MATRIX = ORG / "specs/vectors/features/signer-feature-matrix-v0.json"
LAB_DOCS = (
    ROOT / "docs/historical-feature-contract-01.md",
    ROOT / "docs/historical-feature-contract-02.md",
    ROOT / "docs/historical-feature-contract-03.md",
)

EXPECTED_SIGNER_FAMILIES = {
    "raspberry_qr_vault": {
        "label": "nSealr Vault — Pi edition",
        "repository": "raspberry",
    },
    "esp32_qr_vault": {
        "label": "nSealr Vault — ESP32 edition",
        "repository": "firmware",
    },
    "esp32_usb_nip46": {
        "label": "nSealr Key",
        "repository": "firmware",
    },
    "smartcard": {
        "label": "nSealr Card",
        "repository": "smartcard",
    },
    "custom_hardware_wallet": {
        "label": "nSealr One",
        "repository": "hardware",
    },
}


def load_feature_matrix(path: Path = FEATURE_MATRIX) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_feature_matrix(path: Path, matrix: dict) -> None:
    if matrix.get("format") != "nsealr-signer-feature-matrix-v0":
        raise ValueError(f"{path}: feature matrix format drift")
    if matrix.get("name") != "signer-feature-matrix-v0":
        raise ValueError(f"{path}: feature matrix name drift")

    solutions = matrix.get("solutions")
    if not isinstance(solutions, dict):
        raise ValueError(f"{path}: solutions must be an object")
    if set(solutions) != set(EXPECTED_SIGNER_FAMILIES):
        raise ValueError(
            f"{path}: first-class signer family drift: "
            f"observed {sorted(solutions)}, expected {sorted(EXPECTED_SIGNER_FAMILIES)}"
        )

    for solution_id, expected in EXPECTED_SIGNER_FAMILIES.items():
        solution = solutions[solution_id]
        if solution.get("label") != expected["label"]:
            raise ValueError(
                f"{path}: label drift for {solution_id}: "
                f"{solution.get('label')!r} != {expected['label']!r}"
            )
        if solution.get("repository") != expected["repository"]:
            raise ValueError(
                f"{path}: repository owner drift for {solution_id}: "
                f"{solution.get('repository')!r} != {expected['repository']!r}"
            )
        if not isinstance(solution.get("product_goal"), str) or not solution["product_goal"]:
            raise ValueError(f"{path}: product_goal missing for {solution_id}")
        if not isinstance(solution.get("features"), dict):
            raise ValueError(f"{path}: features missing for {solution_id}")


def validate_feature_matrix_docs(paths: tuple[Path, ...] | list[Path] = LAB_DOCS) -> None:
    required_patterns = (
        (r"Feature\s+Conformance", "Feature Conformance"),
        (r"vectors/features/signer-feature-matrix-v0\.json", "vectors/features/signer-feature-matrix-v0.json"),
        (r"same\s+behavior", "same behavior"),
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        missing = [label for pattern, label in required_patterns if not re.search(pattern, text)]
        if missing:
            raise ValueError(f"{path}: missing feature matrix contract reference: {', '.join(missing)}")


def main() -> int:
    if not FEATURE_MATRIX.exists():
        raise FileNotFoundError(f"missing sibling specs feature matrix: {FEATURE_MATRIX}")
    validate_feature_matrix(FEATURE_MATRIX, load_feature_matrix(FEATURE_MATRIX))
    validate_feature_matrix_docs()
    print("nSealr cross-repo feature matrix validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
