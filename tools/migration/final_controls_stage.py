#!/usr/bin/env python3
"""Declare consolidated structure ownership and enforce post-suite source identity."""
import argparse
from pathlib import Path
from transforms import Changes

VERIFY='''#!/usr/bin/env python3
"""Check this product repository, independent of the checkout directory name."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REQUIRED_FILES=('README.md','LICENSE','Makefile','.pre-commit-config.yaml',
 'docs/architecture.md','docs/testing.md','docs/roadmap.md','docs/audit-checklist.md',
 '.github/workflows/ci.yml','plan/work-items.json','plan/evidence-index.json',
 'protocols/contracts/v1/manifest.json','apps/desktop-simulator/Cargo.lock',
 'apps/desktop-simulator/rust-toolchain.toml','pnpm-lock.yaml','packages/sdk/package.json')
REQUIRED_DIRS=('crates','apps/bridge','apps/pi','ci','boards','docs','scripts','tests/integration','tools/bridge')

def validate(root=ROOT):
 errors=[]
 for name in REQUIRED_FILES:
  path=root/name
  if not path.is_file() or path.is_symlink():errors.append('missing/nonregular required file: '+name)
  elif not path.read_text().strip():errors.append('empty required file: '+name)
 for name in REQUIRED_DIRS:
  path=root/name
  if not path.is_dir() or path.is_symlink():errors.append('missing/nonregular required directory: '+name)
 if (root/'LICENSE').is_file() and 'MIT License' not in (root/'LICENSE').read_text():errors.append('product license must retain MIT notice')
 if (root/'README.md').is_file() and '## License' not in (root/'README.md').read_text():errors.append('README.md must include a License section')
 return errors

if __name__=='__main__':
 errors=validate()
 for error in errors:print('ERROR:',error)
 if not errors:print('nSealr consolidated product structure passed')
 raise SystemExit(bool(errors))
'''
TEST='''"""Actual checkout-shape positives and malformed ownership negatives."""
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
'''
RUN_TEST='''

class SuiteSourceCorrespondenceTests(unittest.TestCase):
    def exercise(self,mutate):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'nsealr';source.mkdir()
            (source/'tracked.txt').write_text('original')
            recipe='test:\\n\\t'+('echo changed >> tracked.txt' if mutate else 'true')+'\\ncargo-test:\\n\\ttrue\\n'
            (source/'Makefile').write_text(recipe)
            subprocess.run(['git','init','-q',str(source)],check=True)
            subprocess.run(['git','-C',str(source),'add','.'],check=True)
            subprocess.run(['git','-C',str(source),'-c','user.name=Test','-c','user.email=test@invalid.example','commit','-qm','fixture'],check=True)
            commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
            for name,data in [('environment.json',dict(os.environ)),('source-commits.json',{'nsealr':commit}),('source-state.json',{'nsealr':{'status':'','diff_sha256':__import__('hashlib').sha256(b'').hexdigest()}})]:
                (root/name).write_text(json.dumps(data))
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('run.py')),str(root),'--smoke'],capture_output=True,text=True)
            record=json.loads((root/'evidence/smoke/result.json').read_text())
            self.assertEqual(result.returncode,1 if mutate else 0)
            self.assertEqual(record['all_passed'],not mutate)
            self.assertEqual(record['source_changed_after'],['nsealr'] if mutate else [])
    def test_successful_command_that_changes_source_fails_acceptance(self):self.exercise(True)
    def test_successful_command_preserving_source_passes(self):self.exercise(False)
'''

def apply(target,output):
 c=Changes(target);c.put('scripts/verify_repo.py',VERIFY.encode());c.put('scripts/test_verify_repo.py',TEST.encode())
 path='Makefile';s=(target/path).read_text().replace("\tpython3 -m unittest discover -s scripts -p 'test_validate_restart_plan.py'", "\tpython3 -m unittest discover -s scripts -p 'test_validate_restart_plan.py'\n\tpython3 -m unittest discover -s scripts -p 'test_verify_repo.py'");c.put(path,s.encode())
 path='tools/baseline/run.py';s=(target/path).read_text().replace("    write_json(directory/'source-after.json', statuses(root, inputs))", "    after = statuses(root, inputs)\n    write_json(directory/'source-after.json', after)\n    changed = [name for name in inputs if after[name] != before[name] or hashlib.sha256(subprocess.check_output(['git','diff','--binary'],cwd=root/name)).hexdigest() != expected[name]['diff_sha256']]\n    for name in inputs:\n        if subprocess.check_output(['git','rev-parse','HEAD'],cwd=root/name,text=True).strip() != inputs[name] and name not in changed:\n            changed.append(name)")
 s=s.replace("'all_passed':not failed", "'source_changed_after':changed, 'all_passed':not failed and not changed").replace("return int(bool(failed))", "return int(bool(failed or changed))");c.put(path,s.encode())
 path='tools/baseline/test_bootstrap.py';s=(target/path).read_text().replace("\n\nif __name__ == '__main__':",RUN_TEST+"\n\nif __name__ == '__main__':");c.put(path,s.encode())
 return c.apply(output,'Require actual consolidated source structure and unchanged source after complete suite execution')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output))
