#!/usr/bin/env python3
"""Finite read-only metadata/copy review, with one restored proof-removal control."""
import datetime, hashlib, json, subprocess, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
C='4ecfcd0b106b7979e2e3359e2b320bf60c2c1cec'
B='1db465e0371814f47ea17d297d5cb8d848e1680e'
R='4893abd86ffc0e481a44b72f91aab0be34c3bdeb'
P='docs/restart/implementation/P02/closure/'
PYTHON='/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/python/bin/python3'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def body(c,p):return git('show',c+':'+p)
def sha(d):return hashlib.sha256(d).hexdigest()
def read(p):return (ROOT/p).read_bytes()
def load(p):return json.loads(read(p))
def identity(c,p):
 mode,kind,blob=git('ls-tree',c,'--',p).decode().split('\t')[0].split();raw=body(c,p)
 assert kind=='blob';return dict(mode=mode,blob=blob,bytes=len(raw),sha256=sha(raw))
assert git('rev-parse','HEAD').decode().strip()==C
assert git('rev-parse',C+'^{tree}').decode().strip()=='6e83ae7aa7652a9dd6fb64a000efa3bf330252c3'
delta=[r.split('\t') for r in git('diff','--name-status',B,C).decode().splitlines()]
assert len(delta)==26 and [(s,p) for s,p in delta if s=='M']==[('M','plan/work-items.json')]
assert len([1 for s,p in delta if s=='A' and p.startswith(P)])==25
original=[r.split('\t') for r in git('diff','--name-status','503719d5c607bdbcd1da30a89b0c3c6f5983c01b',B).decode().splitlines()]
assert len(original)==48 and all(identity(B,p)==identity(C,p) for _,p in original)
a=json.loads(body(B,'plan/work-items.json'));b=load('plan/work-items.json')
at,bt=({t['id']:t for t in g['tasks']} for g in (a,b))
assert len(bt)==47 and at.keys()==bt.keys()
assert all(at[k]==bt[k] for k in at if k!='P02')
assert all(at[k]['acceptance']==bt[k]['acceptance'] and at[k]['depends_on']==bt[k]['depends_on'] for k in at)
assert a['revision']==15 and b['revision']==16
normalized=dict(b,tasks=a['tasks'],revision=a['revision']);assert normalized==a
assert len(b['resources'])==16 and len(b['release_paths'])==5
assert body(B,'plan/evidence-index.json')==read('plan/evidence-index.json')
t=bt['P02']; result=load(P+'result.json')
assert load(P+'prior-task.json')==at['P02']
assert t['status']=='integrated' and t['assignee']=='/root/b01_final_review' and t['reviewer']=='/root' and t['review_verdict']=='pass'
assert t['candidate_commits']==t['reviewed_candidate_commits']==result['candidate_commits']=={'nSealr/nsealr':'268d2c52456f107cf369b54316c29ef35be10751'}
assert t['input_commits']==t['reviewed_input_commits']==result['input_commits']=={'nSealr/nsealr':'b1c90139a651895284b2624da7d12903cf16bc9d'}
assert result['acceptance']==t['acceptance'] and len(result['acceptance_results'])==5
assert all(r['index']==i and r['outcome']=='pass' and r['proof_kind']=='document' for i,r in enumerate(result['acceptance_results']))
assert t['result_manifest']==P+'result.json' and len(t['result_artifacts'])==71
all_delivery_changes=[row.split('\t') for row in git('diff','--name-status','503719d5c607bdbcd1da30a89b0c3c6f5983c01b',C).decode().splitlines()]
assert {r['path'] for r in t['result_artifacts']}=={path for status,path in all_delivery_changes if status=='A' and path.startswith('docs/restart/implementation/P02/')}
for row in t['result_artifacts']:
 assert row['path'].startswith('docs/restart/implementation/P02/') and not row['path'].startswith('docs/product/')
 assert sha(read(row['path']))==row['sha256'],row['path']
source_review=load(result['source_approval']['path'])
assert source_review['candidate']==result['candidate_commits']['nSealr/nsealr'] and source_review['reviewer']=='/root' and source_review['author']=='/root/b01_final_review'
assert sha(read(result['source_approval']['path']))==result['source_approval']['sha256']
copies=load(P+'review-copy-map.json')['copies'];assert len(copies)==11
for row in copies:
 source=identity(R,row['source_path']);assert all(row[k]==v for k,v in source.items());assert source==identity(C,row['destination'])
paired=load(P+'delivery-review/review.json');assert len(paired['artifacts'])==10
assert {Path(r['destination']).name for r in copies}=={r['path'] for r in paired['artifacts']}|{'review.json'}
for r in paired['artifacts']:
 raw=read(P+'delivery-review/'+r['path']);assert len(raw)==r['bytes'] and sha(raw)==r['sha256']
ci=P+'base-main-CI/';capture=load(ci+'capture.json');run=load(ci+'run.json');jobs=load(ci+'jobs.json')
assert sha(read(ci+'capture.json'))==result['actual_base_main_CI']['capture_sha256']
assert run['id']==39420363820 and run['head_sha']=='503719d5c607bdbcd1da30a89b0c3c6f5983c01b' and run['event']=='push' and run['status']=='completed' and run['conclusion']=='success'
assert any(j['id']==118619497395 and j['conclusion']=='success' for j in jobs['jobs'])
for r in capture['files']:
 raw=read(ci+r['path']);assert sha(raw)==r['sha256'] and len(raw)==r['size']
with zipfile.ZipFile(ROOT/ci/'logs.zip') as z:
 assert set(z.namelist())=={r['name'] for r in capture['zip_members']}
 for r in capture['zip_members']:
  raw=z.read(r['name']);assert sha(raw)==r['sha256'] and len(raw)==r['size']
for row in load(P+'controls/commands.json'):
 assert row['exit_code']==row['expected_exit_code'] and sha(read(P+'controls/'+row['log']))==row['sha256']
commands=[]
def validate(name,expected):
 argv=[PYTHON,'-B','scripts/validate_restart_plan.py'];r=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (OUT/(name+'.log')).write_bytes(r.stdout);commands.append(dict(argv=argv,name=name,exit_code=r.returncode,expected=expected,log=name+'.log',sha256=sha(r.stdout)))
 assert r.returncode==expected,r.stdout.decode();return r.stdout.decode()
validate('positive',0)
path=ROOT/'docs/restart/implementation/P02/integration/target-bindings.json';raw=path.read_bytes();mode=path.stat().st_mode
try:
 path.unlink();diagnostic=validate('missing-underlying-binding',1)
 assert all('P02: acceptance '+str(i)+' needs hashed underlying evidence' in diagnostic for i in range(5))
finally:
 path.write_bytes(raw);path.chmod(mode)
validate('restored',0);assert identity(C,str(path.relative_to(ROOT)))['sha256']==sha(path.read_bytes())
full=subprocess.run(['git','diff','--check',B,C],capture_output=True,cwd=ROOT)
nonlog=subprocess.run(['git','diff','--check',B,C,'--','.',':(exclude)*.log'],capture_output=True,cwd=ROOT)
assert full.returncode==2 and nonlog.returncode==0
assert full.stdout.decode()==load(P+'whitespace.json')['whole_staged_diagnostic']
result=dict(candidate=C,tree=git('rev-parse',C+'^{tree}').decode().strip(),scope='Exact root closure metadata only; original plan acceptance remains root369 on268, no content self-approval',status='PASS_metadata_checks',changed_paths=26,added_closure_files=25,existing_graph_only=True,previous48_paths_identical=True,all47_criteria_dependencies_unchanged=True,other46_records_unchanged=True,resources=16,release_paths=5,scoped_hashed_artifacts=71,paired_delivery_review_files=11,actual_base_main_CI=39420363820,CI_zip_members=len(capture['zip_members']),controls=commands,whitespace=dict(full_exit=2,nonlog_exit=0),observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(OUT/'probe-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,sort_keys=True))
