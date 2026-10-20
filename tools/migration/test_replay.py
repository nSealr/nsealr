"""Real Git patch tampering and declared-change boundary negatives."""
import json,subprocess,tempfile,unittest
from pathlib import Path
from assemble import git_environment
from rehearse import canonical,digest
from replay import replay_patches
from transforms import Changes

class ReplayControls(unittest.TestCase):
 def fixture(self,root):
  repo=root/'source';repo.mkdir();env=git_environment()
  def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],env=env,stderr=subprocess.DEVNULL)
  git('init','-q');(repo/'a').write_text('before');git('add','.');git('commit','-qm','base');before=git('rev-parse','HEAD').decode().strip()
  change=Changes(repo);change.put('a',b'after');change.put('b',b'explicit addition');patch=root/'patch';change.apply(patch,'declared synthetic transformation');record=json.loads((patch/'result.json').read_bytes());(patch/'series.json').write_bytes(canonical([{'patch':'change.patch','record':'result.json','sha256':record['patch_sha256']}]))
  git('reset','--hard',before);return repo,patch,record
 def exercise(self,mutation,expected):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);repo,patch,record=self.fixture(root);mutation(repo,patch,record)
   with self.assertRaisesRegex(ValueError,expected):replay_patches(repo,patch,root/'execution')
 def test_unapproved_patch_bytes_rejected(self):
  self.exercise(lambda r,p,d:(p/'change.patch').write_bytes((p/'change.patch').read_bytes()+b'\n'),'patch hash mismatch')
 def test_dirty_preimage_rejected_before_patch(self):
  self.exercise(lambda r,p,d:(r/'a').write_text('unapproved source'),'source/cleanliness')
 def test_patch_with_undeclared_added_path_rejected(self):
  def mutate(r,p,d):d['changes']=[x for x in d['changes'] if x['path']=='a'];(p/'result.json').write_bytes(canonical(d))
  self.exercise(mutate,'undeclared paths')
 def test_forged_postimage_rejected(self):
  def mutate(r,p,d):d['changes'][0]['after_sha256']='0'*64;(p/'result.json').write_bytes(canonical(d))
  self.exercise(mutate,'postimage mismatch')
 def test_declared_commit_identity_cannot_be_forged(self):
  def mutate(r,p,d):d['target_commit']='0'*40;(p/'result.json').write_bytes(canonical(d))
  self.exercise(mutate,'commit differs')

if __name__=='__main__':unittest.main()
