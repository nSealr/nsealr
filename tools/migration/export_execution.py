#!/usr/bin/env python3
"""Export explicit public execution records and exact ordered patches, never runtime repos."""
import argparse,ast,json,shutil
from pathlib import Path
from rehearse import canonical,digest,git


def export(author):
 runtime=author/'tools/migration/.runtime';target=runtime/'rehearsal-01/repository';destination=author/'docs/restart/implementation/A02/execution';patches=author/'tools/migration/patches'
 # Inspect protected originals in memory only; never emit excluded path literals.
 original=git(Path('/home/tux/nsealr/lab'),'show','3303ab17a28ed32419576627d5abb93db3999635:scripts/integration_feature_matrix.py')
 tree=ast.parse(original);node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='LAB_DOCS' for t in n.targets));literals=[n.value for n in ast.walk(node.value) if isinstance(n,ast.Constant) and isinstance(n.value,str)];forbidden=[s.encode() for item in literals for s in (item,Path(item).name)]
 def safe_write(path,data):
  if any(value in data for value in forbidden):raise ValueError('excluded private reference in proposed public output')
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
 for directory in sorted(runtime.iterdir()):
  if not directory.is_dir() or not any(directory.name.startswith(p) for p in ['bridge-','sdk-package-execution-','integration-layout-execution-','product-boundaries-execution-','current-product-execution-','product-ci-execution-']):continue
  if not (directory/'commands.json').is_file():continue
  for path in directory.iterdir():
   if path.is_file() and path.suffix in ['.json','.log']:safe_write(destination/directory.name/path.name,path.read_bytes())
 series=json.loads((patches/'series.json').read_bytes());last=json.loads((patches/series[-1]['record']).read_bytes())['target_commit'];candidates={}
 for directory in (runtime/'rehearsal-01').iterdir():
  if not directory.is_dir() or directory.name=='repository':continue
  for path in directory.rglob('result.json'):
   data=json.loads(path.read_bytes())
   if isinstance(data,dict) and all(key in data for key in ['source_commit','target_commit','patch_sha256','changes']):
    if data['source_commit'] in candidates:raise ValueError('ambiguous transformation chain')
    candidates[data['source_commit']]=(path,data)
 head=git(target,'rev-parse','HEAD').decode().strip()
 while last!=head:
  path,record=candidates[last];patch=(path.parent/'change.patch').read_bytes();assert digest(patch)==record['patch_sha256'];number=len(series)+1;stem=f'{number:02d}-'+path.parent.name
  if any(row['patch']==stem+'.patch' for row in series):raise ValueError('duplicate patch filename')
  safe_write(patches/(stem+'.patch'),patch);safe_write(patches/(stem+'.json'),path.read_bytes());series.append(dict(patch=stem+'.patch',record=stem+'.json',sha256=digest(patch)));last=record['target_commit']
 safe_write(patches/'series.json',canonical(series))
 source=Path('/home/tux/nsealr/.restart-tools/goal/ci-actions-source/result.json');expected='e098f77abc6a12d4e490202711febdabea1528bc6c0801e15210061563b42dfe'
 if digest(source.read_bytes())!=expected:raise ValueError('independent official action record changed')
 safe_write(destination/'official-actions-source.json',source.read_bytes())
 progress=json.loads((destination/'progress.json').read_bytes());progress['target_head']=head;progress['phase']='Bridge package, seventeen product integrations and twenty-one replacement guardrails executed; final cold complete suite, replay/restoration and distinct review pending';progress['pending']='Complete consolidated cold bootstrap/CI and current-candidate Rust reproduction; external hardware; final case inventories; byte-exact accepted review additions; second assembly/all-object audit/restore and distinct final review.'
 progress['runtime_validation'].update(bridge_runnable_before=716,bridge_runnable_after=691,bridge_retired_card_cases=25,bridge_explicit_named_replacements=5,inherited_live_relay_skip=1,selected_integration_helper_cases=115,optional_browser_serial_helper_cases=13,packed_sdk_node_browser_types='PASS; actual tarball installed outside workspace',uninterrupted_product_integration_steps=17,admitted_replacement_obligations_executed=21)
 progress['source_tooling_commits']=git(author,'rev-list','--reverse','5ad571a..HEAD').decode().splitlines();progress['validation']['current_bootstrap_controls']=6;progress['validation']['historical_overlay_cases']='Seven former multi-repository overlay cases retire from active bootstrap; exact original overlay application was executed before migration, current artifact tamper controls and public-only selected fetch controls replace the active mechanisms. Full per-case ledger is pending.'
 progress['post_adoption_coordinator_reconciliation']='P02 reviewed delivery8525ce01 and coordinator89a7af0, S03 isolated implementation, S04 assigned, B01 preparation only. No branch contents implicitly imported; final graph reconciliation is coordinator-owned after migration. Private workspace recovery receipt advanced to aa4b286; earlier bundles remain dated proofs and need a final metadata refresh.'
 progress['artifacts']=[dict(path=p.relative_to(author).as_posix(),sha256=digest(p.read_bytes())) for p in sorted(destination.rglob('*')) if p.is_file() and p.name!='progress.json']
 safe_write(destination/'progress.json',canonical(progress))
 print(json.dumps({'target_head':head,'patches':len(series),'public_execution_artifacts':len(progress['artifacts'])}))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--author-repo',type=Path,required=True);a=p.parse_args();export(a.author_repo)
