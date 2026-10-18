#!/usr/bin/env python3
"""Export explicit public after-state evidence, excluding source/bundle/cache trees."""
import argparse,ast,json
from pathlib import Path
from assemble import read_git
from rehearse import canonical,digest,git

def export(author,replay):
 runtime=author/'tools/migration/.runtime';destination=author/'docs/restart/implementation/A02/execution'
 original=ast.parse(git(Path('/home/tux/nsealr/lab'),'show','3303ab17a28ed32419576627d5abb93db3999635:scripts/integration_feature_matrix.py'))
 node=next(n for n in original.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='LAB_DOCS' for t in n.targets));words=[n.value for n in ast.walk(node.value) if isinstance(n,ast.Constant) and isinstance(n.value,str)];forbidden=[s.encode() for value in words for s in (value,Path(value).name)]
 def copy(source,path):
  data=source.read_bytes()
  if any(value in data for value in forbidden):raise ValueError('excluded private reference in proposed public evidence')
  target=destination/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 for name in ['final-pre-cold-execution-01','external-hardware-execution-01','named-python-execution-01','source-replay-execution-01','source-replay-execution-02','final-source-execution-01','case-reconciliation-execution-01','case-reconciliation-execution-02']:
  directory=runtime/name
  if not directory.exists():continue
  for file in directory.iterdir():
   if file.is_file() and file.suffix in ['.json','.log']:copy(file,Path(name)/file.name)
 for number in [1,2,3]:
  outer=runtime/f'cold-product-execution-{number:02d}'
  if outer.exists():
   for file in outer.iterdir():
    if file.is_file():copy(file,Path(outer.name)/file.name)
  cold=runtime/f'cold-product-{number:02d}'
  if cold.exists():
   for file in cold.iterdir():
    if file.is_file() and file.suffix=='.json':copy(file,Path(cold.name)/file.name)
   for file in (cold/'evidence').rglob('*'):
    if file.is_file():copy(file,Path(cold.name)/file.relative_to(cold))
 # Explicit source-replay records only; never recurse into repository, restored
 # object stores, recovery capture directories or private full ref inventories.
 for name in ['rehearsal-02',replay]:
  base=runtime/name
  if not base.exists():continue
  for relative in ['result.json','patch-execution','candidate-recovery','candidate-recovery-02','initial-import/public-refs-before','initial-import/public-refs-after']:
   path=base/relative
   files=[path] if path.is_file() else list(path.iterdir()) if path.is_dir() else []
   for file in files:
    if file.is_file() and file.suffix in ['.json','.log']:copy(file,Path(name)/file.relative_to(base))
 for relative in ['final-navigation','final-navigation/recovery','final-controls','script-entrypoint','repro-navigation','s01-overlays']:
  base=runtime/'rehearsal-01'/relative
  if base.exists():
   for file in base.iterdir():
    if file.is_file() and file.suffix in ['.json','.log']:copy(file,Path('declared-transformation-execution')/relative/file.name)
 copy(runtime/'workspace-recovery-04/summary.json',Path('workspace-recovery-04-summary.json'))
 progress=json.loads((destination/'progress.json').read_bytes());progress['artifacts']=[dict(path=p.relative_to(author).as_posix(),sha256=digest(p.read_bytes())) for p in sorted(destination.rglob('*')) if p.is_file() and p.name!='progress.json'];progress['phase']='Actual migration execution evidence; see final-report for exact candidate acceptance and remaining coordinator review/adoption gates.';progress['pending']='Distinct final review and coordinator integration/main CI; no archival, registry publication or physical qualification claimed.';progress['target_head']=read_git(runtime/'rehearsal-01/repository','rev-parse','HEAD').decode().strip();progress['validation']['current_bootstrap_controls']=8;progress['source_tooling_commits']=read_git(author,'rev-list','--reverse','5ad571a..HEAD').decode().splitlines();(destination/'progress.json').write_bytes(canonical(progress))
 print(json.dumps({'exported_artifacts':len(progress['artifacts']),'target_head':progress['target_head']}))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--replay',required=True);a=p.parse_args();export(a.author_repo,a.replay)
