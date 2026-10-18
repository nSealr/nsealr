#!/usr/bin/env python3
"""Check placement of the already-required product gates, not task status."""
import ast
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
REQUIRED_STEPS={1:'check_fixture_snapshots',2:'integration_feature_matrix',3:'integration_companion_fixtures',4:'integration_companion_policy_cli',5:'integration_companion_nip46_cli',6:'integration_companion_serial_frame_cli',7:'integration_companion_service_context',8:'integration_companion_route_identity',9:'integration_companion_sdk_browser',10:'integration_browser_extension_package_plan',11:'integration_browser_extension_package_build',12:'integration_browser_extension_origin_permission_cli',13:'integration_browser_extension_origin_review_control',14:'integration_browser_extension_origin_approval_control',15:'integration_browser_native_messaging_manifest',17:'integration_raspberry_hardware_probe',19:'integration_vault_companion'}
REQUIRED_COMMANDS=('scripts/verify_contracts.py','scripts/test_contracts.py','scripts/verify_evidence.py','scripts/validate_restart_plan.py','tools/baseline','cargo fmt','cargo clippy','cargo test --workspace','cargo test -p nsealr-core --features std','riscv32imafc-unknown-none-elf','apps/desktop-simulator/Cargo.toml','cargo deny check','cargo llvm-cov','ci/check_coverage_ratchet.py','ci/repro_build.sh','pnpm ci','protocols/contracts/v1','scripts/verify_specs.py','apps/pi','tests/integration','tests.integration.run')


def steps_from_source(text):
    tree=ast.parse(text)
    matches=[node for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PRODUCT_STEPS' for t in node.targets)]
    if len(matches)!=1:raise ValueError('integration recipe must declare one step sequence')
    return ast.literal_eval(matches[0].value)


def validate_steps(steps):
    if tuple(steps)!=tuple(REQUIRED_STEPS.items()):raise ValueError('missing, bypassed or extra product integration obligation')


def validate_ci_commands(text):
    for marker in REQUIRED_COMMANDS:
        # make prints unittest discovery instead of the module path.
        if marker=='scripts/test_contracts.py':marker="test_contracts.py"
        if marker not in text:raise ValueError('missing product gate: '+marker)
    if any(value in text for value in ['../','NSEALR_HARDWARE_ROOT','tests.integration.external.','tests.integration.optional.','CHROMIUM','NSEALR_LIVE_E2E=1']):
        raise ValueError('default product acceptance depends on external/private/physical resource')


def current_ci_plan():
    return subprocess.check_output(['make','--no-print-directory','-n','ci'],cwd=ROOT,text=True)


def main():
    validate_steps(steps_from_source((ROOT/'tests/integration/run.py').read_text()))
    validate_ci_commands(current_ci_plan())
    print('all retained gate placements and seventeen self-contained integration obligations present')


if __name__=='__main__':main()
