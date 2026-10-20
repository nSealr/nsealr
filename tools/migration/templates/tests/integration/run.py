#!/usr/bin/env python3
"""Execute every retained product integration obligation in one invocation."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
# Original recipe numbers are provenance identifiers, not task state.
PRODUCT_STEPS = (
    (1, "check_fixture_snapshots"),
    (2, "integration_feature_matrix"),
    (3, "integration_companion_fixtures"),
    (4, "integration_companion_policy_cli"),
    (5, "integration_companion_nip46_cli"),
    (6, "integration_companion_serial_frame_cli"),
    (7, "integration_companion_service_context"),
    (8, "integration_companion_route_identity"),
    (9, "integration_companion_sdk_browser"),
    (10, "integration_browser_extension_package_plan"),
    (11, "integration_browser_extension_package_build"),
    (12, "integration_browser_extension_origin_permission_cli"),
    (13, "integration_browser_extension_origin_review_control"),
    (14, "integration_browser_extension_origin_approval_control"),
    (15, "integration_browser_native_messaging_manifest"),
    (17, "integration_raspberry_hardware_probe"),
    (19, "integration_vault_companion"),
)


def main():
    for count, (original, module) in enumerate(PRODUCT_STEPS, 1):
        print(f"[{count}/{len(PRODUCT_STEPS)} original {original}] {module}", flush=True)
        subprocess.run([sys.executable, "-B", "-m", "tests.integration." + module], cwd=ROOT, check=True)
    print("All 17 retained product integration steps passed. External hardware and optional physical resources are separate.", flush=True)


if __name__ == "__main__":
    main()
