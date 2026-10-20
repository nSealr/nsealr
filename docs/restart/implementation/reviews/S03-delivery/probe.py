#!/usr/bin/env python3
"""Exact root-envelope/metadata review; immutable S03 source is not re-executed."""
import datetime,hashlib,json,re,subprocess,zipfile
from pathlib import Path
from urllib.parse import unquote,urlsplit
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
C='30702d4158cfc9a08d4a98a78a2e8158a86ba7ac';P='363a49441e0c5edaee514d43fc0034d95193c64f'
B='2295fb9d6d00219c648c9cde75af5c8cf089db06';S='c358229777d2582964a4f326ce8d15709841a395'
SOURCE_BASE='b1c90139a651895284b2624da7d12903cf16bc9d';R='23d76b2c15d8dd41627f58c7b2018e06d40e821c'
D='docs/restart/implementation/S03/delivery/';PYTHON='/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/python/bin/python3'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def body(c,p):return git('show',c+':'+p)
def sha(d):return hashlib.sha256(d).hexdigest()
def read(p):return (ROOT/p).read_bytes()
def load(p):return json.loads(read(p))
def tree(c):
 result={}
 for row in git('ls-tree','-rz',c).split(b'\0'):
  if row:
   entry,path=row.decode().split('\t');result[path]=tuple(entry.split())
 return result
ct,pt,st=tree(C),tree(P),tree(S)
assert git('rev-parse','HEAD').decode().strip()==C
assert git('rev-parse',C+'^{tree}').decode().strip()=='bd0fab419ea9be3e633645a4cc195392c1fe5832'
assert git('rev-parse',B+'^{tree}').decode().strip()==git('rev-parse','4ecfcd0b106b7979e2e3359e2b320bf60c2c1cec^{tree}').decode().strip()=='6e83ae7aa7652a9dd6fb64a000efa3bf330252c3'
assert subprocess.run(['git','merge-base','--is-ancestor',B,C],cwd=ROOT).returncode==0
source_paths=git('diff','--name-only',SOURCE_BASE,S).decode().splitlines();assert len(source_paths)==922
assert set(git('diff','--name-only',B,P).decode().splitlines())==set(source_paths)
assert all(ct[p]==pt[p]==st[p] for p in source_paths)
delta=[r.split('\t') for r in git('diff','--name-status',P,C).decode().splitlines()]
assert len(delta)==45 and {p for s,p in delta if s=='M'}=={'AGENTS.md','docs/restart/README.md','docs/restart/implementation/handoff.md','plan/work-items.json'}
delivery_paths={p for p in ct if p.startswith(D)};assert len(delivery_paths)==41
assert {p for s,p in delta if s=='A'}==delivery_paths
copies=load(D+'review-copy-map.json')['copies'];assert len(copies)==31
rt=tree(R);review_root='docs/restart/implementation/reviews/S03-current-final/'
assert {r['source_path'] for r in copies}=={p for p in rt if p.startswith(review_root)}
for row in copies:
 assert row['source_commit']==R and ct[row['destination']]==rt[row['source_path']]==(row['mode'],'blob',row['blob'])
 raw=read(row['destination']);assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
review=load(D+'review/review.json');assert review['candidate_commit']==S and review['reviewer']=='/root/b01_final_review' and review['implementation_author']=='/root/a02_sol'
assert len(review['artifacts'])==30
assert {str(Path(r['destination']).relative_to(D+'review')) for r in copies}=={r['path'] for r in review['artifacts']}|{'review.json'}
for row in review['artifacts']:
 raw=read(D+'review/'+row['path']);assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
a=json.loads(body(P,'plan/work-items.json'));b=load('plan/work-items.json')
at,bt=({t['id']:t for t in g['tasks']} for g in (a,b));assert len(bt)==47 and at.keys()==bt.keys()
assert all(at[k]==bt[k] for k in at if k!='S03')
assert all(at[k]['acceptance']==bt[k]['acceptance'] and at[k]['depends_on']==bt[k]['depends_on'] for k in at)
assert a['revision']==16 and b['revision']==17
assert dict(b,tasks=a['tasks'],resources=a['resources'],revision=a['revision'])==a
changed_resources={k for k in a['resources'] if a['resources'][k]!=b['resources'][k]};assert changed_resources=={'accessible_kit','pi_kit','p4_kit','se_bench'}
for key in changed_resources:
 before,after=a['resources'][key],b['resources'][key]
 assert before['status']==after['status']=='unknown' and before['owner_role']==after['owner_role']
 assert after['maintainer_report']['actual_sample_or_operation_verified'] is False
 assert {k:v for k,v in after.items() if k not in ['next_action','maintainer_report']}=={k:v for k,v in before.items() if k!='next_action'}
assert len(b['resources'])==16 and b['release_paths']==a['release_paths'] and len(b['release_paths'])==5
assert body(P,'plan/evidence-index.json')==read('plan/evidence-index.json')
t=bt['S03'];result=load(D+'result.json');assert load(D+'prior-task.json')==at['S03']
assert t['assignee']=='/root/a02_sol' and t['reviewer']=='/root/b01_final_review' and t['review_verdict']=='pass' and t['status']=='integrated'
assert t['candidate_commits']==t['reviewed_candidate_commits']==result['candidate_commits']=={'nSealr/nsealr':S}
assert t['input_commits']==t['reviewed_input_commits']==result['input_commits']=={'nSealr/nsealr':SOURCE_BASE}
assert t['result_manifest']==D+'result.json' and result['acceptance']==t['acceptance']
assert result['review']=={'assignee':t['assignee'],'reviewer':t['reviewer'],'verdict':'pass'}
assert len(result['acceptance_results'])==5
assert all(r['index']==i and r['outcome']=='pass' and r['proof_kind']=='executed_test' for i,r in enumerate(result['acceptance_results']))
assert result['source_approval']['commit']==R and result['source_approval']['candidate']==S and sha(read(result['source_approval']['path']))==result['source_approval']['sha256']
manifest=load('docs/restart/implementation/S03/integration/evidence/artifact-manifest.json')['artifacts'];assert len(manifest)==211
expected_artifacts={r['path'] for r in manifest}|{'docs/restart/implementation/S03/integration/evidence/artifact-manifest.json'}|delivery_paths
assert len(expected_artifacts)==253 and {r['path'] for r in t['result_artifacts']}==expected_artifacts
for row in t['result_artifacts']:
 assert sha(read(row['path']))==row['sha256'],row['path']
 assert row['path'].startswith(('docs/restart/implementation/S03/','docs/restart/implementation/reviews/S03-'))
assert sum(not p.startswith('docs/restart/implementation/S03/') for p in expected_artifacts)==44
for row in load(D+'checks/commands.json'):
 assert row['exit_code']==0 and sha(read(D+'checks/'+row['log']))==row['sha256']
ci=Path('/home/tux/nsealr/.restart-tools/goal/a02-ci-2026-10-20/run-39424748193');capture=json.loads((ci/'capture.json').read_bytes());run=json.loads((ci/'run.json').read_bytes());jobs=json.loads((ci/'jobs.json').read_bytes())
assert run['head_sha']==B and run['id']==39424748193 and run['event']=='push' and run['status']=='completed' and run['conclusion']=='success'
assert any(j['id']==118634354789 and j['conclusion']=='success' for j in jobs['jobs'])
for r in capture['files']:
 raw=(ci/r['path']).read_bytes();assert len(raw)==r['size'] and sha(raw)==r['sha256']
with zipfile.ZipFile(ci/'logs.zip') as z:
 assert set(z.namelist())=={r['name'] for r in capture['zip_members']}
 for r in capture['zip_members']:
  raw=z.read(r['name']);assert len(raw)==r['size'] and sha(raw)==r['sha256']
links=[]
for p in ['docs/restart/README.md','docs/restart/implementation/handoff.md',D+'README.md']:
 for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',read(p).decode()):
  if urlsplit(target).scheme or not target.split('#')[0]:continue
  resolved=(ROOT/Path(p).parent/unquote(target.split('#')[0])).resolve()
  assert resolved.is_relative_to(ROOT) and resolved.exists(),(p,target)
  links.append(dict(source=p,target=target))
commands=[]
def validate(name,expected):
 argv=[PYTHON,'-B','scripts/validate_restart_plan.py'];r=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (OUT/(name+'.log')).write_bytes(r.stdout);commands.append(dict(argv=argv,name=name,exit_code=r.returncode,expected=expected,log=name+'.log',sha256=sha(r.stdout)))
 assert r.returncode==expected,r.stdout.decode();return r.stdout.decode()
validate('positive',0)
path=ROOT/'docs/restart/implementation/reviews/S03-security/probe/src/main.rs';raw=path.read_bytes();mode=path.stat().st_mode
try:
 path.unlink();error=validate('missing-outside-S03-proof',1)
 assert 'S03: unavailable repository artifact docs/restart/implementation/reviews/S03-security/probe/src/main.rs' in error
finally:path.write_bytes(raw);path.chmod(mode)
validate('restored',0);assert sha(path.read_bytes())==sha(body(S,str(path.relative_to(ROOT))))
whitespace=load(D+'whitespace.json');full=subprocess.run(['git','diff','--check',P,C],cwd=ROOT,capture_output=True);nonlog=subprocess.run(['git','diff','--check',P,C,'--','.',':(exclude)*.log'],cwd=ROOT,capture_output=True)
assert full.returncode==2 and full.stdout.decode()==whitespace['commands'][0]['stdout'] and nonlog.returncode==0
observation=dict(candidate=C,tree=git('rev-parse',C+'^{tree}').decode().strip(),parent=P,actual_base=B,source_candidate=S,source_review=R,source_paths_preserved=922,root_delta_paths=45,root_additions=41,root_existing_edits=4,paired_review_files=31,graph_artifact_union=253,source_manifest_members=211,outside_S03_proof_paths=44,all47criteria_dependencies_unchanged=True,other46_records_unchanged=True,resource_notes_only=sorted(changed_resources),all_resource_statuses_unchanged=True,resource_reports_not_physical_proof=True,resources=16,release_paths=5,frozen_index_unchanged=True,base_main_CI=dict(id=39424748193,head=B,conclusion='success',capture_sha256=sha((ci/'capture.json').read_bytes()),checked_files=len(capture['files'])+1,zip_members=len(capture['zip_members'])),metadata_controls=commands,local_links=len(links),whitespace=dict(root_delta_exit=2,nonlog_exit=0,preserved_raw_log_files=4),scope='Envelope/metadata only; no repeated source campaign, no S03 delivery CI or adoption claim',recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(OUT/'probe-result.json').write_text(json.dumps(observation,indent=2)+'\n');print(json.dumps(observation,sort_keys=True))
