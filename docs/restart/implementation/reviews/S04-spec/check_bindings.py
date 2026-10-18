#!/usr/bin/env python3
"""Read-only exact-object/requirement checks. Not a custody or prose-presence test."""
import datetime,hashlib,json,pathlib,subprocess,sys
OWN=pathlib.Path(__file__).resolve().parent
ROOT=OWN.parents[4]
CANDIDATE='d4713e134e24b4f5b6a33cbe83a67b91c19449c3'
CANDIDATE_TREE='f156ad286c17249d166f14cc7bfd2b31c3f83be7'
BASE='f2ef70f522af4977e15f81554a8c6eadcdbe8097'
REPOS={'core':ROOT,'s03_context':ROOT,'h01':pathlib.Path('/home/tux/nsealr/hardware'),'h01_review':pathlib.Path('/home/tux/nsealr/hardware'),'hardware_main':pathlib.Path('/home/tux/nsealr/hardware'),'sdk':pathlib.Path('/home/tux/nsealr/board-sdk')}
HASHES={'brief.md':'86a15bd3ab06189fb7cad3065a18b883d58bc0387cc02c8896b334f7128d198b','source-audit.json':'d3112561d36e1a19f2070d2b7023da89dea60b3ec9f27fe23675e00e3df3762c','acceptance-plan.json':'2068876b3997748f59f0a9cd67acc8c50fd9bf594475da29625e8484e717abef'}
def git(repo,*argv):return subprocess.check_output(['git','-C',str(repo),*argv])
def sha(data):return hashlib.sha256(data).hexdigest()
assert git(ROOT,'rev-parse',CANDIDATE+'^{tree}').decode().strip()==CANDIDATE_TREE
prefix='docs/restart/implementation/S04/'
assert set(git(ROOT,'diff','--name-only',BASE,CANDIDATE).decode().splitlines())=={prefix+x for x in HASHES}
for name,digest in HASHES.items():
 data=git(ROOT,'show',CANDIDATE+':'+prefix+name)
 assert sha(data)==digest and data==(ROOT/prefix/name).read_bytes(),name
audit=json.loads((ROOT/prefix/'source-audit.json').read_text())
plan=json.loads((ROOT/prefix/'acceptance-plan.json').read_text())
rows=[];trees=[];refs=set()
for repo in audit['repository_inputs']:
 loc=REPOS[repo['id']]
 tree=git(loc,'rev-parse',repo['commit']+'^{tree}').decode().strip();assert tree==repo['tree'],repo['id']
 trees.append({'id':repo['id'],'commit':repo['commit'],'tree':tree})
 for f in repo['files']:
  entry=git(loc,'ls-tree',repo['commit'],'--',f['path']).decode().strip();meta,path=entry.split('\t');mode,typ,blob=meta.split()
  assert (mode,typ,blob,path)==(f['mode'],'blob',f['git_blob'],f['path']),f
  data=git(loc,'cat-file','blob',blob);assert len(data)==f['bytes'] and sha(data)==f['sha256'],f
  rows.append({'repository':repo['id'],**f});refs.add(repo['id']+':'+f['path'])
for observation in audit['observations']:
 assert set(observation['sources'])<=refs,observation['id']
assert len(rows)==40 and len(trees)==6
register=json.loads(git(REPOS['h01'],'show','6f95cc298c5a8108d5c0bdaedfd53e7b81b130ed:docs/restart/H01/manual-register.json'))
by_id={x['id']:x for x in register['documents']}
inherited=[]
for entry in audit['inherited_vendor_register']['documents']:
 for key,value in entry.items():assert by_id[entry['id']][key]==value,(entry['id'],key)
 inherited.append(entry['id'])
assert len(inherited)==18
(OWN/'inherited-register.json').write_text(json.dumps({'frozen_h01':'6f95cc298c5a8108d5c0bdaedfd53e7b81b130ed','records_checked':inherited,'status':'All 18 copied document record fields exactly match frozen H01.','limits':'Correspondence only. No fresh manufacturer document retrieval, advisory applicability determination or part admission. Later research must reread exact primary sources and refresh current advisories.'},indent=2)+'\n')
ledger=json.loads(git(ROOT,'show',BASE+':docs/restart/work-items.json'))
task=next(t for t in ledger['tasks'] if t['id']=='S04')
assert task['depends_on']==plan['parent_dependency_ids']==['P01']
assert task['acceptance']==[x['exact_parent_acceptance'] for x in plan['criterion_mapping']]
assert len(task['acceptance'])==7
r=subprocess.run(['python3','scripts/validate_restart_plan.py'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(OWN/'plan-validation.log').write_bytes(r.stdout);assert r.returncode==0
r2=subprocess.run(['git','diff','--check',BASE,CANDIDATE],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(OWN/'candidate-diff-check.log').write_bytes(r2.stdout);assert r2.returncode==0
result={'candidate':CANDIDATE,'candidate_tree':CANDIDATE_TREE,'base':BASE,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'preparation_sha256':HASHES,'trees':trees,'files':rows,'seven_criteria_unchanged':task['acceptance'],'dependency_unchanged':task['depends_on'],'observation_references_bound':True,'candidate_scope_exactly_three_files':True,'structural_validation':{'argv':['python3','scripts/validate_restart_plan.py'],'exit_code':r.returncode,'log':'plan-validation.log'},'diff_check':{'argv':['git','diff','--check',BASE,CANDIDATE],'exit_code':r2.returncode,'log':'candidate-diff-check.log'},'limits':'Git correspondence and unchanged requirement check only. No custody protocol, manufacturer command, model runner or physical behavior executed.'}
(OWN/'bindings.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: exact candidate/tree/three SHA256 files; 40 blob/mode/length/SHA256 bindings; six trees; 18 inherited records; seven unchanged S04 criteria; unchanged P01 dependency; structural validator and candidate diff check.')
