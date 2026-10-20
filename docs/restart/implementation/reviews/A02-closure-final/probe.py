from pathlib import Path
import datetime,hashlib,json,os,re,subprocess,sys,zipfile
p=Path(sys.argv[1]).resolve(); out=Path(__file__).resolve().parent
base='b1c90139a651895284b2624da7d12903cf16bc9d'; candidate='bbccf25897bda8121244c0138d129ae9683177e8'; prefix='docs/restart/implementation/A02/closure/'
def git(*a):return subprocess.check_output(['git','-C',str(p),*a])
def sha(b):return hashlib.sha256(b).hexdigest()
def load(path):return json.loads((p/path).read_text())
assert git('rev-parse','HEAD').decode().strip()==candidate
changed=git('diff','--name-status',base,candidate).decode().splitlines()
existing={'plan/work-items.json','docs/restart/README.md','docs/restart/implementation/handoff.md'}
assert {line.split('\t')[1] for line in changed if line.startswith('M\t')}==existing
assert all(line.startswith('M\t') or (line.startswith('A\t') and line.split('\t')[1].startswith(prefix)) for line in changed)
old=json.loads(git('show',base+':plan/work-items.json')); new=load('plan/work-items.json')
assert [t['id'] for t,o in zip(new['tasks'],old['tasks']) if t!=o]==['A02']
for t,o in zip(new['tasks'],old['tasks']):assert t['id']==o['id'] and t['acceptance']==o['acceptance'] and t['depends_on']==o['depends_on']
x=json.loads(json.dumps(old)); y=json.loads(json.dumps(new));x.pop('tasks');y.pop('tasks');assert y['revision']==x['revision']+1;x.pop('revision');y.pop('revision');x['execution_model_policy'].pop('integration');y['execution_model_policy'].pop('integration');x['adoption_reconciliation'].pop('initial_adoption');y['adoption_reconciliation'].pop('initial_adoption');assert x==y
assert (p/'plan/evidence-index.json').read_bytes()==git('show',base+':plan/evidence-index.json')
a=next(t for t in new['tasks'] if t['id']=='A02');r=load(a['result_manifest']);sr=load(prefix+'evidence/source-review/review.json')
assert a['candidate_commits']==r['candidate_commits']==sr['candidate_commits']=={'nSealr/nsealr':base}
assert a['input_commits']==r['input_commits']==sr['input_commits'] and a['acceptance']==r['acceptance']==sr['acceptance']
assert a['reviewed_candidate_commits']==a['candidate_commits'] and a['reviewed_input_commits']==a['input_commits']
assert a['assignee']==r['review']['assignee']=='/root/a02_sol' and a['reviewer']==r['review']['reviewer']==sr['reviewer']=='/root/b01_final_review'
assert a['review_verdict']==r['review']['verdict']=='pass' and sr['verdict']=='PASS_A02_source_criteria_only'
assert [z['index'] for z in r['acceptance_results']]==list(range(5)) and all(z['outcome']=='pass' for z in r['acceptance_results'])
artifact_names={z['path'] for z in a['result_artifacts']};assert len(artifact_names)==len(a['result_artifacts'])
for z in a['result_artifacts']:
 f=p/z['path'];assert f.is_file() and not f.is_symlink() and sha(f.read_bytes())==z['sha256'];assert z['path'].startswith(('docs/restart/implementation/A02/','docs/restart/implementation/reviews/A02-final/','tools/migration/patches/'))
for z in r['acceptance_results']:assert z['evidence_paths'] and all(n in artifact_names and n!=a['result_manifest'] for n in z['evidence_paths'])
manifest=load(prefix+'artifact-manifest.json'); actual={str(f.relative_to(p)) for f in (p/prefix).rglob('*') if f.is_file()};assert actual=={z['path'] for z in manifest['files']}|{prefix+'artifact-manifest.json'}
assert manifest['plan_sha256']==sha((p/'plan/work-items.json').read_bytes())
for z in manifest['files']:
 b=(p/z['path']).read_bytes();assert len(b)==z['bytes'] and sha(b)==z['sha256']
inv=load(prefix+'copy-inventory.json'); git_copies=0
for z in inv['copies']:
 b=(p/z['copied_path']).read_bytes();assert len(b)==z['bytes'] and sha(b)==z['sha256'];s=z['source']
 if 'commit' in s:assert b==git('show',s['commit']+':'+s['path']);git_copies+=1
reuse=[]
for z in inv['historical_current_source_dependencies']:
 assert sha(git('show',z['source_commit']+':'+z['source_path']))==z['sha256']
 if z.get('reuse_current_path'):assert sha((p/z['reuse_current_path']).read_bytes())==z['sha256'];reuse.append(z['reuse_current_path'])
row=[z for z in inv['historical_current_source_dependencies'] if z['source_path']=='plan/work-items.json'];assert len(row)==1 and row[0]['reuse_current_path'] is None
caps=[]
for run,head in [('39406783194','a5f7b9f2e087c9538495a16706644f3390e6b01c'),('39411242641','951ed2ad1bb7c7d85a6eaa735a5286022e8fce36'),('39412818666',base)]:
 root=p/prefix/'evidence/CI'/('run-'+run);c=json.loads((root/'capture.json').read_text());rr=json.loads((root/'run.json').read_text());assert c['head_sha']==rr['head_sha']==head and c['conclusion']==rr['conclusion']=='success'
 for z in c['files']:assert len((root/z['path']).read_bytes())==z['size'] and sha((root/z['path']).read_bytes())==z['sha256']
 with zipfile.ZipFile(root/'logs.zip') as archive:
  assert set(archive.namelist())=={z['name'] for z in c['zip_members']}
  for z in c['zip_members']:assert sha(archive.read(z['name']))==z['sha256']
 caps.append({'run':int(run),'head':head,'conclusion':'success','zip_members':len(c['zip_members'])})
links=0
for name in ['docs/restart/README.md','docs/restart/implementation/handoff.md',prefix+'handoff.md']:
 f=p/name
 for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',f.read_text()):
  if ':' in target or target.startswith('#'):continue
  assert (f.parent/target.split('#',1)[0]).resolve().exists(),(name,target);links+=1
py=Path('/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/python/bin/python3');assert sha(py.read_bytes())=='eaaa308032c4aa063df5880c4c293cd458b4629d503fbc2c03ec163d71f7f790'
env=dict(os.environ);env['PATH']=str(py.parent)+os.pathsep+env['PATH'];env['PYTHONDONTWRITEBYTECODE']='1';commands=[]
def run(label,argv,expected=0):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();v=subprocess.run(argv,cwd=p,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);name=label+'.log';(out/name).write_bytes(v.stdout);commands.append({'command':argv,'cwd':str(p),'started_utc':start,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':v.returncode,'expected_exit':expected,'log':name,'sha256':sha(v.stdout)});(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert v.returncode==expected,(label,v.returncode);return v.stdout
run('positive-plan',[str(py),'-B','scripts/validate_restart_plan.py']);run('positive-evidence',[str(py),'-B','scripts/verify_evidence.py'])
f=p/prefix/'evidence/CI/run-39412818666/capture.json';saved=f.read_bytes()
try:
 f.unlink();run('missing-accepted-underlying-proof',[str(py),'-B','scripts/validate_restart_plan.py'],1)
finally:f.write_bytes(saved)
run('restored-plan',[str(py),'-B','scripts/validate_restart_plan.py']);run('restored-evidence',[str(py),'-B','scripts/verify_evidence.py'])
run('nonlog-whitespace',['git','diff','--check',base,candidate,'--','.',':(exclude)*.log'])
result={'candidate':candidate,'tree':git('rev-parse',candidate+'^{tree}').decode().strip(),'base':base,'outcome':'PASS_exact_metadata_checks','only_existing_paths':sorted(existing),'total_candidate_delta_paths':len(changed),'other46_records_47criteria_dependencies_resources_releases_unchanged':True,'historical_index_and_actual1508_evidence':'PASS_unchanged_real_gate','graph_artifacts_verified':len(a['result_artifacts']),'scoped_manifest_members':len(manifest['files']),'copy_rows_verified':len(inv['copies']),'Git_bound_copies_verified':git_copies,'declared_current_reuse_paths_verified':reuse,'historical_graph_current_reuse_is_null':True,'actual_capture_sets_verified':caps,'local_links':links,'missing_underlying_proof_reject_then_restore':'PASS_actual','no_mutable_product_paths_frozen':True,'no_product_change_or_task_other_thanA02':True,'not_repeated':'Historical replay/migration48/local full product suite and original source-criteria campaign','pending':'Protected PR CI,normal merge,resulting main CI','python':str(py),'python_sha256':sha(py.read_bytes())}
(out/'probe-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
