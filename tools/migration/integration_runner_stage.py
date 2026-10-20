#!/usr/bin/env python3
"""Keep all seventeen product obligations and optional helper safety cases executable."""
import argparse
from pathlib import Path
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=Changes(a.target)
 path='tests/integration/test_browser_extension_chromium_smoke.py';c.put(path,(a.target/path).read_text().replace('from scripts import browser_extension_chromium_smoke as smoke','from tests.integration.optional import browser_extension_chromium_smoke as smoke').encode())
 path='tests/integration/optional/hardware_companion_serial_smoke.py';s=(a.target/path).read_text().replace('PINNED_PNPM_COMMAND, run_command','PINNED_PNPM_COMMAND, pinned_command, run_command').replace('return [*PINNED_PNPM_COMMAND]','return pinned_command(["pnpm"])').replace('[*pnpm, "install"]','[*pnpm, "install", "--frozen-lockfile"]');c.put(path,s.encode())
 path='tests/integration/test_hardware_companion_serial_smoke.py';s=(a.target/path).read_text().replace('import unittest','import unittest\nimport subprocess\nfrom unittest.mock import patch');s=s.replace('        self.assertEqual(pnpm_command(), ["npm", "exec", "--yes", "--package=pnpm@10.33.4", "--", "pnpm"])','''        with patch("tests.integration.integration_support.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess(["pnpm"], 0, stdout="10.33.4\\n")
            self.assertEqual(pnpm_command(), ["pnpm"])
            run.return_value = subprocess.CompletedProcess(["pnpm"], 0, stdout="0.0.0\\n")
            with self.assertRaisesRegex(RuntimeError, "pinned product toolchain"):
                pnpm_command()''');c.put(path,s.encode())
 c.put('tests/integration/run.py',(a.author_repo/'tools/migration/templates/tests/integration/run.py').read_bytes())
 print(c.apply(a.output,'Run all seventeen retained product integrations and preserve thirteen optional-resource helper safety cases'))
