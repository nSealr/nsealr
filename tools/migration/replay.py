#!/usr/bin/env python3
"""Replay the admitted import and exact declared patches; restore the resulting Git bundle."""
import argparse,json,subprocess
from pathlib import Path
from admission import Recorder
from assemble import audit,commits,git_environment,import_selected,read_git,reachable,tree
from rehearse import canonical,digest,safe_path,write_private


def replay_patches(target,patches,output):
 rec=Recorder(output);series=json.loads((patches/'series.json').read_bytes());applied=[]
 for item in series:
  patch=patches/safe_path(item['patch']);record=json.loads((patches/safe_path(item['record'])).read_bytes())
  if digest(patch.read_bytes())!=item['sha256'] or item['sha256']!=record['patch_sha256']:raise ValueError('patch hash mismatch')
  if read_git(target,'status','--porcelain') or read_git(target,'rev-parse','HEAD').decode().strip()!=record['source_commit']:raise ValueError('replay source/cleanliness mismatch')
  before=tree(target,record['source_commit']);names=set()
  for row in record['changes']:
   path=safe_path(row['path'])
   if path in names:raise ValueError('duplicate declaration')
   names.add(path);entry=before.get(path);data=(target/path).read_bytes() if entry else None
   if (digest(data) if data is not None else None)!=row['before_sha256'] or (entry['mode'] if entry else None)!=row['before_mode']:raise ValueError('declared preimage mismatch')
  rec.run('apply-'+str(len(applied)+1),['git','-C',str(target),'apply','--index','--whitespace=nowarn',str(patch)],output,env=git_environment())
  changed=set(read_git(target,'diff','--cached','--name-only','--no-renames','-z').decode().strip('\0').split('\0'))
  if changed!=names:raise ValueError('patch changes undeclared paths')
  staged=read_git(target,'write-tree').decode().strip()
  if staged!=record['target_tree']:raise ValueError('replay staged tree differs')
  after=tree(target,staged)
  for row in record['changes']:
   path=row['path'];entry=after.get(path);data=(target/path).read_bytes() if entry else None
   if (digest(data) if data is not None else None)!=row['after_sha256'] or (entry['mode'] if entry else None)!=row['after_mode']:raise ValueError('declared postimage mismatch')
  rec.run('commit-'+str(len(applied)+1),['git','-C',str(target),'-c','commit.gpgsign=false','commit','-m',record['stage']],output,env=git_environment())
  actual=read_git(target,'rev-parse','HEAD').decode().strip()
  if actual!=record['target_commit']:raise ValueError('replay commit differs')
  applied.append(actual)
 result=dict(patches=len(applied),target_head=applied[-1],target_tree=read_git(target,'rev-parse','HEAD^{tree}').decode().strip(),every_declared_preimage_postimage_mode_patch_tree_and_commit_equal=True,commits=applied)
 write_private(output/'result.json',canonical(result));return result


def restore(target,base,added,output):
 rec=Recorder(output);env=git_environment();bundle=output/'candidate.bundle';restored=output/'restored'
 original=audit(target,reachable(target,base),commits(target,base),added,base)
 rec.run('candidate-bundle',['git','-C',str(target),'bundle','create',str(bundle),'refs/heads/rehearsal'],output,env=env)
 rec.run('bundle-verify',['git','-C',str(target),'bundle','verify',str(bundle)],output,env=env)
 rec.run('empty-restore',['git','-c','init.templateDir=','init','--initial-branch=rehearsal',str(restored)],output,env=env)
 rec.run('restore-selected-branch',['git','-C',str(restored),'fetch','--no-tags','--no-write-fetch-head',str(bundle),'refs/heads/rehearsal:refs/heads/rehearsal'],output,env=env)
 rec.run('restore-checkout',['git','-C',str(restored),'checkout','--force','rehearsal'],output,env=env)
 rec.run('restore-fsck',['git','-C',str(restored),'fsck','--full','--strict'],output,env=env)
 restored_audit=audit(restored,reachable(target,base),commits(target,base),added,base)
 if original!=restored_audit or tree(target,'HEAD')!=tree(restored,'HEAD') or reachable(target,'HEAD')!=reachable(restored,'HEAD'):raise ValueError('restored tree/object identity differs')
 result=dict(bundle_sha256=digest(bundle.read_bytes()),bundle_bytes=bundle.stat().st_size,source_audit=original,restored_audit=restored_audit,tree_and_all_objects_equal=True,no_private_or_unselected_object_import=True)
 write_private(output/'result.json',canonical(result));return result


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--privacy-root',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--expected-target',type=Path,required=True);a=p.parse_args()
 root=a.destination.resolve();root.mkdir(mode=0o700);author=a.author_repo.resolve()
 imported=import_selected(a.source_root.resolve(),author/'docs/restart/implementation/A02/admission-inputs.json',a.privacy_root.resolve(),root/'initial-import')
 target=root/'initial-import/repository';result=replay_patches(target,author/'tools/migration/patches',root/'patch-execution')
 expected=a.expected_target.resolve()
 if read_git(expected,'rev-parse','HEAD').decode().strip()!=result['target_head'] or tree(expected,'HEAD')!=tree(target,'HEAD'):raise ValueError('second source assembly differs from first')
 recovery=restore(target,imported['source_core'],[imported['initial_commit']]+result['commits'],root/'candidate-recovery')
 write_private(root/'result.json',canonical(dict(second_assembly=result,recovery=recovery,first_and_second_commit_and_tree_equal=True)))
 print(json.dumps({'second_head':result['target_head'],'patches':result['patches'],'recovery':recovery['restored_audit']}))

if __name__=='__main__':main()
