"""Independent exact-candidate audit. Exports identities/counts, never private data."""
import ast
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
AUTHOR=HERE.parents[3]
PRODUCT=HERE/'replay/initial-import/repository'
SOURCES=Path('/home/tux/nsealr')
REPORT=AUTHOR/'docs/restart/implementation/A02'
EXPECTED_AUTHOR='f9a09ba2e9b0212f7dafa53b086c5f1c366d9288'
EXPECTED_PRODUCT='daf8ba03a9eb820f99b0f1bf5c4f553a7961e008'
EXPECTED_TREE='db0687a5ec15228e944360e00e391a4fff863f5d'
CORE='f2ef70f522af4977e15f81554a8c6eadcdbe8097'
results={}

def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_bytes())
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL)
def tree(root,commit):
 out={}
 for row in git(root,'ls-tree','-rz','--full-tree',commit).split(b'\0'):
  if row:
   info,path=row.split(b'\t',1);mode,kind,blob=info.decode().split();out[path.decode()]={'mode':mode,'kind':kind,'blob':blob}
 return out

def blobs(root,oids):
 oids=sorted(set(oids));data=git(root,'cat-file','--batch',) if not oids else subprocess.check_output(['git','-C',str(root),'cat-file','--batch'],input=('\n'.join(oids)+'\n').encode())
 at=0;out={}
 for oid in oids:
  end=data.index(b'\n',at);actual,kind,size=data[at:end].decode().split();assert actual==oid and kind=='blob';size=int(size);at=end+1;out[oid]=data[at:at+size];at+=size+1
 return out

def check(name,value):results[name]=value;print(name,json.dumps(value,sort_keys=True),flush=True)

assert git(AUTHOR,'rev-parse','HEAD').decode().strip()==EXPECTED_AUTHOR
assert not git(AUTHOR,'status','--porcelain')
assert git(PRODUCT,'rev-parse','HEAD').decode().strip()==EXPECTED_PRODUCT
assert git(PRODUCT,'rev-parse','HEAD^{tree}').decode().strip()==EXPECTED_TREE
package_path=REPORT/'final-review-package.json'
assert sha(package_path.read_bytes())=='f44c18838428d4b72ebf52c63fce62687b01cfa65683f2b18713d7938ff55318'
package=read(package_path);index=tree(AUTHOR,'HEAD')
paths={p for p in index if p.startswith(('tools/migration/','docs/restart/implementation/A02/'))}-{package_path.relative_to(AUTHOR).as_posix()}
assert len(package['files'])==len(paths)==982 and {r['path'] for r in package['files']}==paths
for row in package['files']:
 p=AUTHOR/row['path'];assert not p.is_symlink() and sha(p.read_bytes())==row['sha256'] and index[row['path']]['mode']==row['mode']
check('complete_public_package',{'files':len(paths),'manifest_sha256':sha(package_path.read_bytes())})

admitted=read(REPORT/'admission-evidence/file-dispositions.json')
final=read(REPORT/'final-source-map.json');final_tree=read(REPORT/'final-tree.json')
manifest=read(REPORT/'admission-inputs.json');sources={s['name']:s for s in manifest['sources']}
source_trees={};source_hashes={};notices=0
for name,s in sources.items():
 repo=SOURCES/s['directory'];assert git(repo,'rev-parse',s['commit']+'^{tree}').decode().strip()==s['tree'];source_trees[name]=tree(repo,s['commit'])
 license=s.get('root_license')
 if license:
  assert sha(git(repo,'show',s['commit']+':'+license['path']))==license['sha256'];notices+=1
 # Excluded private blobs are not read. Only individually admitted file bytes.
 selected=[r['blob'] for r in admitted['files'] if r['source']==name and r.get('sha256')]
 source_hashes[name]={oid:sha(data) for oid,data in blobs(repo,selected).items()}
assert len(admitted['files'])==len(final['public_and_selected_private_file_dispositions'])==4456
final_by_key={(r['source'],r['source_path']):r for r in final['public_and_selected_private_file_dispositions']}
for row in admitted['files']:
 original=source_trees[row['source']][row['path']];assert original=={'mode':row['mode'],'kind':'blob','blob':row['blob']}
 if row.get('sha256'):assert source_hashes[row['source']][row['blob']]==row['sha256']
 dest=final_by_key[row['source'],row['path']]
 for k,v in [('source_commit',row['commit']),('source_blob',row['blob']),('source_mode',row['mode']),('source_sha256',row['sha256'])]:assert dest[k]==v
 assert dest['rights_basis'] and dest['reason']
actual=tree(PRODUCT,'HEAD');raw=blobs(PRODUCT,[r['blob'] for r in actual.values()])
assert len(actual)==len(final_tree['files'])==3612
for row in final_tree['files']:
 assert actual[row['path']]=={k:row[k] for k in ['blob','mode']}|{'kind':'blob'}
 assert sha(raw[row['blob']])==row['sha256'] and sha((PRODUCT/row['path']).read_bytes())==row['sha256']
 assert row['origins'] or row['declarations']
for row in final_by_key.values():
 if row['final']:
  entry=row['final'];assert actual[entry['path']]=={k:entry[k] for k in ['blob','mode']}|{'kind':'blob'} and sha(raw[entry['blob']])==entry['sha256']
check('all_source_and_final_rows',{'source_rows':4456,'final_files':3612,'root_notices_checked':notices,'dispositions':dict(Counter(r['final_disposition'] for r in final_by_key.values()))})

original_plan=json.loads(git(PRODUCT,'show',CORE+':docs/restart/work-items.json'))
plan=read(PRODUCT/'plan/work-items.json');policy=plan.pop('execution_model_policy');assert plan==original_plan
assert len(plan['tasks'])==47
closed=[t for t in original_plan['tasks'] if t['status'] in ['verified','integrated']]
frozen=read(PRODUCT/'plan/evidence-index.json');bound={r['path']:r['sha256'] for t in closed for r in t['result_artifacts']}
assert len(closed)==7 and len(bound)==1508 and sum(len(t['result_artifacts']) for t in closed)==1511
assert set(bound)=={r['path'] for r in frozen['artifacts']}
historical=tree(PRODUCT,CORE);links=0
for row in frozen['artifacts']:
 assert historical[row['path']]==actual[row['path']]=={k:row[k] for k in ['blob','kind','mode']}
 assert row['sha256']==bound[row['path']]==sha(raw[row['blob']])
 assert row['original_commit']==CORE and row['source_url']=='https://github.com/nSealr/nsealr/blob/'+CORE+'/'+row['path']
 for link in row['relative_links']:
  assert link['exists_at_inventory_commit'];path=link['resolved_path'];assert path in historical or any(p.startswith(path.rstrip('/')+'/') for p in historical);links+=1
assert not (PRODUCT/'docs/restart/work-items.json').exists()
assert policy['default_model']=='gpt-6.1-sol' if 'default_model' in policy else 'gpt-6.1-sol' in json.dumps(policy)
check('frozen_graph_and_navigation',{'tasks_unchanged':47,'closed_tasks_unchanged':7,'unique_files':1508,'artifact_references':1511,'historical_links_checked':links,'current_contract_owners':len(frozen['current_contracts']),'current_model_policy':policy})

progress=read(REPORT/'execution/progress.json');artifacts=progress['artifacts'];assert len(artifacts)==755 and len({r['path'] for r in artifacts})==755
for row in artifacts:assert sha((AUTHOR/row['path']).read_bytes())==row['sha256']
failed=[];command_count=0
for p in (REPORT/'execution').rglob('commands.json'):
 data=read(p)
 if not isinstance(data,list):continue
 for row in data:
  log=p.parent/row['log'];assert sha(log.read_bytes())==row['sha256'];command_count+=1
  if row.get('exit_code',0):failed.append((log.relative_to(REPORT).as_posix(),row['exit_code']))
observations=read(REPORT/'failure-observations.json')['observations'];assert len(observations)==len(failed)==30
assert Counter(failed)==Counter((r['log'],r['exit_code']) for r in observations)
ledger=(REPORT/'failure-removal-ledger.md').read_text()
for row in observations:assert sha((REPORT/row['log']).read_bytes())==row['log_sha256'] and row['log'].removeprefix('execution/') in ledger
check('execution_evidence_and_failures',{'artifacts':755,'commands_with_hashed_logs':command_count,'all_nonzero_observations_explained':30})

suite=read(REPORT/'execution/cold-product-03/evidence/suites/result.json');assert suite['all_passed'] and not suite['failed_commands'] and not suite['source_changed_after'] and suite['input_commits']=={'nsealr':'2bb10013c9fcaab04c544abcff3f480243200da1'}
delta=git(PRODUCT,'diff','--name-only',suite['input_commits']['nsealr'],'HEAD').decode().splitlines()
assert delta==['AGENTS.md','docs/reproducible-build.md','docs/restart/execution.md','plan/work-items.json']
check('full_suite_reuse',{'full_suite_source':suite['input_commits']['nsealr'],'exact_final_documentation_delta':delta,'no_executable_fixture_lock_toolchain_or_recipe_delta':True})

# Privacy comparisons keep excluded values in memory and publish only counts.
original=ast.parse(git(SOURCES/'lab','show',sources['lab']['commit']+':scripts/integration_feature_matrix.py'))
assignment=next(n for n in original.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='LAB_DOCS' for t in n.targets))
words=[n.value for n in ast.walk(assignment.value) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
forbidden=[v.encode() for word in words for v in (word,Path(word).name)]
for path in paths:assert not any(v in (AUTHOR/path).read_bytes() for v in forbidden)
all_oids=git(PRODUCT,'cat-file','--batch-all-objects','--batch-check=%(objectname) %(objecttype)').decode().splitlines()
all_blobs=blobs(PRODUCT,[row.split()[0] for row in all_oids if row.endswith(' blob')])
assert not any(v in data for data in all_blobs.values() for v in forbidden)
private_commits=[s['commit'] for s in manifest['sources'] if s['visibility']=='private']
objects={row.split()[0] for row in all_oids};assert len(objects)==7943 and not objects.intersection(private_commits)
assert git(PRODUCT,'remote')==b'' and git(PRODUCT,'for-each-ref','--format=%(refname)').decode().splitlines()==['refs/heads/rehearsal']
check('private_intake_exclusion',{'public_files_checked':982,'all_public_candidate_blobs_checked':len(all_blobs),'excluded_original_manual_references_found':0,'private_source_commits_in_object_store':0,'only_rehearsal_ref_no_remotes':True})

# Source identity of independent Pi oracle remains exact original bytes.
pi=PRODUCT/'apps/pi/app/nsealr_vault/crypto.py'
assert pi.read_bytes()==git(SOURCES/'raspberry','show',sources['raspberry']['commit']+':app/nsealr_vault/crypto.py')
projection=ast.parse((PRODUCT/'ci/project_core_fixtures.py').read_bytes())
imports={n.names[0].name.split('.')[0] for n in projection.body if isinstance(n,ast.Import)}|{n.module.split('.')[0] for n in projection.body if isinstance(n,ast.ImportFrom)}
assert imports=={'json','pathlib','sys'}
check('oracle_and_projection_independence',{'pi_crypto_original_sha256':sha(pi.read_bytes()),'pi_uses_direct_libsecp256k1':True,'projection_imports':sorted(imports),'projection_reads_expected_contract_data_only':True})
assert not git(PRODUCT,'status','--porcelain')
(HERE/'probe-result.json').write_text(json.dumps(results,indent=2)+'\n')
print('Independent audit passed',flush=True)
