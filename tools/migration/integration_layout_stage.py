#!/usr/bin/env python3
"""Move selected helper consumers to the single product checkout and artifact."""
import argparse,ast,json,re
from pathlib import Path
from rehearse import canonical
from transforms import Changes

def apply(target,output):
 c=Changes(target)
 for path in sorted((target/'tests/integration').rglob('*.py')):
  rel=path.relative_to(target).as_posix();s=path.read_text()
  s=s.replace('scripts.hardware_companion_serial_smoke','tests.integration.optional.hardware_companion_serial_smoke').replace('scripts.browser_extension_chromium_smoke','tests.integration.optional.browser_extension_chromium_smoke').replace('scripts.integration_hardware_validation','tests.integration.external.integration_hardware_validation')
  s=s.replace('scripts.integration_', 'tests.integration.integration_').replace('scripts.browser_integration_support','tests.integration.browser_integration_support')
  depth=3 if '/optional/' in rel or '/external/' in rel else 2
  s=s.replace('ROOT = Path(__file__).resolve().parents[1]',f'ROOT = Path(__file__).resolve().parents[{depth}]').replace('ORG = ROOT.parent\n','')
  s=s.replace('COMPANION = ORG / "companion"','COMPANION = ROOT').replace('SPECS = ORG / "specs"','SPECS = ROOT / "protocols/contracts/v1"').replace('RASPBERRY = ORG / "raspberry"','RASPBERRY = ROOT / "apps/pi"')
  s=s.replace('apps/browser-extension/','apps/bridge/browser-extension/').replace('apps/cli/','apps/bridge/cli/').replace('missing sibling repository','missing product component').replace('cross-repo','integrated')
  if rel.endswith('/external/integration_hardware_validation.py'):
   s=s.replace('import json','import json\nimport os').replace('HARDWARE = ORG / "hardware"','HARDWARE = Path(os.environ["NSEALR_HARDWARE_ROOT"]).resolve() if "NSEALR_HARDWARE_ROOT" in os.environ else None').replace('ORG / "firmware/boards/','ROOT / "boards/').replace('ORG / "hardware/pcb/reference-esp32-s3-qr-signer/requirements.json"','HARDWARE / "pcb/reference-esp32-s3-qr-signer/requirements.json" if HARDWARE else None').replace('if not HARDWARE.exists():','if HARDWARE is None or not HARDWARE.exists():').replace('missing product component: {HARDWARE}','explicit NSEALR_HARDWARE_ROOT is required for external hardware regression: {HARDWARE}')
  c.put(rel,s.encode())
 for name in ['tests/__init__.py','tests/integration/__init__.py','tests/integration/optional/__init__.py','tests/integration/external/__init__.py']:c.put(name,b'"""Selected integration helpers; optional resources are invoked explicitly."""\n')
 path='tools/bridge/check_release_artifacts_safety.mjs';c.put(path,(target/path).read_text().replace('scripts/prepare_release_artifacts.mjs','tools/bridge/prepare_release_artifacts.mjs').encode())
 path='tests/integration/integration_support.py';s=c.updates[path][0].decode().replace('PINNED_PNPM_COMMAND = ["npm", "exec", "--yes", f"--package=pnpm@{PNPM_VERSION}", "--", "pnpm"]','PINNED_PNPM_COMMAND = ["pnpm"]')
 s=s.replace('        return [*PINNED_PNPM_COMMAND, *command[1:]]','''        version = subprocess.run(["pnpm", "--version"], check=True, capture_output=True, text=True)
        if version.stdout.strip() != PNPM_VERSION:
            raise RuntimeError("pnpm version differs from the pinned product toolchain")
        return [*PINNED_PNPM_COMMAND, *command[1:]]''');c.put(path,s.encode())
 path='tests/integration/integration_feature_matrix.py';s=c.updates[path][0].decode();start=s.index('FEATURE_MATRIX =');end=s.index('\ndef load_feature_matrix',start)
 s=s[:start]+'''FEATURE_MATRIX = ROOT / "protocols/contracts/v1/vectors/features/signer-feature-matrix-v0.json"
# Existing conformance component identifiers; these are requirements and software
# fixtures, not proof that a board/driver/production custody profile is qualified.
EXPECTED_SIGNER_FAMILIES = {
    "raspberry_qr_vault": {"label": "nSealr Vault — Pi edition", "repository": "nsealr"},
    "esp32_qr_vault": {"label": "nSealr Vault — ESP32 edition", "repository": "nsealr"},
    "esp32_usb_nip46": {"label": "nSealr Key", "repository": "nsealr"},
    "custom_hardware_wallet": {"label": "nSealr One", "repository": "nsealr"},
}

'''+s[end:];start=s.index('\ndef validate_feature_matrix_docs');end=s.index('\ndef main()',start);s=s[:start]+s[end:];s=s.replace('    validate_feature_matrix_docs()\n','').replace('lab taxonomy docs','current component ownership').replace('missing sibling specs feature matrix','missing authoritative feature matrix');c.put(path,s.encode())
 path='tests/integration/test_integration_feature_matrix.py';s=c.updates[path][0].decode().replace('    validate_feature_matrix_docs,\n','');start=s.index('    def test_lab_docs_must_reference_feature_matrix_contract');end=s.index('\n\nif __name__',start);s=s[:start]+s[end:];c.put(path,s.encode())
 path='tests/integration/integration_companion_sdk_browser.py';s=c.updates[path][0].decode().replace('    print("nSealr integrated browser-safe SDK facade verification passed")','    run_command(["pnpm", "pack-smoke"], COMPANION)\n    print("nSealr integrated browser-safe SDK facade and isolated packed SDK verification passed")');c.put(path,s.encode())
 result=c.apply(output,'Move retained helper consumers to product modules artifact and explicit external or optional resources')

 return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output))
