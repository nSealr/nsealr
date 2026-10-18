"""Positive and mutation controls for admitted integration-placement obligations."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from check_product_gates import ROOT,REQUIRED_STEPS,REQUIRED_COMMANDS,current_ci_plan,steps_from_source,validate_steps,validate_ci_commands
sys.path.insert(0,str(ROOT))
from tests.integration.integration_support import pinned_command

class ProductGateControls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.plan=current_ci_plan();cls.steps=steps_from_source((ROOT/'tests/integration/run.py').read_text())

 def test_1ef1b23af596b9384b11915492171412b116008e2fb776efc11ff115ae29b7b5(self):
  validate_ci_commands(self.plan)
  for mutation in ['make -C ../private ci','NSEALR_HARDWARE_ROOT=/somewhere make audit','python3 -m tests.integration.external.integration_hardware_validation']:
   with self.subTest(mutation=mutation),self.assertRaisesRegex(ValueError,'external/private/physical'):validate_ci_commands(self.plan+'\n'+mutation)

 def assert_step(self,number):
  validate_steps(self.steps)
  with self.assertRaisesRegex(ValueError,'obligation'):validate_steps([r for r in self.steps if r[0]!=number])
  with self.assertRaisesRegex(ValueError,'obligation'):validate_steps([(n,'bypassed' if n==number else name) for n,name in self.steps])

 def test_2cd5cf0b745ba6b4d567e471cfebe87ce2f4494715d86bc22f23925e25027090(self):self.assert_step(15)
 def test_5413e7d98413e95cd18caf1adef38d50182d16e899157004e1c0dd2369774d55(self):self.assert_step(10)
 def test_9a42df470476778c0cfd4aaa1fc23a9567f7e94575b46d9626b6bb8b31a74473(self):self.assert_step(17)
 def test_bae25d0a1c3821c9e3bb3487c97ffd2be0fec90a87642f45b90d93360ce04276(self):self.assert_step(9)
 def test_d4c332e9b34555a73d98d4139c68349efb53465c9b80f82837e528bcbe5f3b94(self):self.assert_step(11)
 def test_cd8aa2e857fd38ec84f82d6495d3b76bafa25f213800cde86d019df14c17056a(self):
  self.assert_step(1);validate_ci_commands(self.plan)
  with self.assertRaisesRegex(ValueError,'verify_contracts'):validate_ci_commands(self.plan.replace('scripts/verify_contracts.py','scripts/bypassed.py'))
  # Actual missing/extra/forged/hidden/nonregular consumer tamper execution is
  # retained in test_contracts.py, not emulated by a second artifact validator.

 def test_c14f9f5e3399a076c3fbe828287049ce0f33b47cc3e3c4dba31c165a3663ffb4(self):
  validate_ci_commands(self.plan);validate_steps(self.steps)
  for marker in REQUIRED_COMMANDS:
   marker='test_contracts.py' if marker=='scripts/test_contracts.py' else marker
   with self.subTest(marker=marker),self.assertRaisesRegex(ValueError,'missing product gate'):validate_ci_commands(self.plan.replace(marker,'REMOVED'))

 def test_ea7dbb867accab4e166758af8b0de49bd0f38b6ab72e490e91cc78f856d27d7e(self):
  validate_ci_commands(self.plan)
  self.assertIn('tests/integration',self.plan)
  for command in ['python3 -m tests.integration.optional.browser_extension_chromium_smoke','CHROMIUM=/installed/browser make ci']:
   with self.assertRaisesRegex(ValueError,'physical'):validate_ci_commands(self.plan+'\n'+command)

 def test_687ec755f8234a8d0084df78aa5e9381d8e5ded2aaf0963c549e8319966ca0c2(self):
  # The actual pinned executable is on the supplied bootstrap PATH, independent
  # of whether the host has globally installed pnpm.
  self.assertEqual(pinned_command(['pnpm','--version']),['pnpm','--version'])
  with tempfile.TemporaryDirectory() as tmp:
   with patch.dict(os.environ,{'PATH':tmp}):
    with self.assertRaises(FileNotFoundError):pinned_command(['pnpm','--version'])
    fake=Path(tmp)/'pnpm';fake.write_text('#!/bin/sh\nprintf "0.0.0\\n"\n');fake.chmod(0o755)
    with self.assertRaisesRegex(RuntimeError,'pinned product toolchain'):pinned_command(['pnpm','--version'])

if __name__=='__main__':unittest.main()
