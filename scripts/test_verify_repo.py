"""Actual checkout-shape positives and malformed ownership negatives."""
from pathlib import Path
import tempfile,unittest
from verify_repo import REQUIRED_FILES,REQUIRED_DIRS,validate

class ProductStructureTests(unittest.TestCase):
 def fixture(self,root):
  for name in REQUIRED_DIRS:(root/name).mkdir(parents=True,exist_ok=True)
  for name in REQUIRED_FILES:
   path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('present')
  (root/'LICENSE').write_text('MIT License');(root/'README.md').write_text('## License')
 def test_arbitrary_checkout_name_accepted(self):
  with tempfile.TemporaryDirectory(prefix='unrelated-checkout-') as tmp:
   root=Path(tmp);self.fixture(root);self.assertEqual(validate(root),[])
 def test_required_file_replaced_by_directory_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.fixture(root);p=root/'plan/work-items.json';p.unlink();p.mkdir();self.assertTrue(validate(root))
 def test_missing_consolidated_consumers_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.fixture(root);(root/'apps/pi').rmdir();self.assertTrue(validate(root))
 def test_wrong_product_license_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.fixture(root);(root/'LICENSE').write_text('CERN Open Hardware Licence');self.assertTrue(validate(root))
 def test_required_symlink_alias_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.fixture(root);p=root/'plan/work-items.json';p.unlink();p.symlink_to(root/'LICENSE');self.assertTrue(validate(root))
