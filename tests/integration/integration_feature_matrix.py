#!/usr/bin/env python3
"""Validate the shared signer feature matrix against current component ownership."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FEATURE_MATRIX = ROOT / "protocols/contracts/v1/vectors/features/signer-feature-matrix-v0.json"
# Existing conformance component identifiers; these are requirements and software
# fixtures, not proof that a board/driver/production custody profile is qualified.
EXPECTED_SIGNER_FAMILIES = {
    "raspberry_qr_vault": {"label": "nSealr Vault — Pi edition", "repository": "nsealr"},
    "esp32_qr_vault": {"label": "nSealr Vault — ESP32 edition", "repository": "nsealr"},
    "esp32_usb_nip46": {"label": "nSealr Key", "repository": "nsealr"},
    "custom_hardware_wallet": {"label": "nSealr One", "repository": "nsealr"},
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


def main() -> int:
    if not FEATURE_MATRIX.exists():
        raise FileNotFoundError(f"missing authoritative feature matrix: {FEATURE_MATRIX}")
    validate_feature_matrix(FEATURE_MATRIX, load_feature_matrix(FEATURE_MATRIX))
    print("nSealr integrated feature matrix validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
