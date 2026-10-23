"""Exact final assembly review, without rerunning component experiments."""
import collections
import copy
import tomllib
import functools
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = '14d5e37065329078afe7275c7448884214ea8a9a'
CANDIDATE = '5c701113bc2ac2d7b596f7d3fb76574a7cff24b3'
P = 'docs/restart/implementation/QP01/request-engine/'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


@functools.cache
def tree(commit):
    result = {}
    for row in git('ls-tree', '-rz', '-l', commit).split(b'\0'):
        if row:
            head, path = row.split(b'\t', 1)
            mode, kind, oid, size = head.decode().split()
            result[path.decode()] = (mode, oid, int(size))
            assert kind == 'blob'
    return result


@functools.cache
def contents(oid):
    return git('cat-file', 'blob', oid)


def blob(path, commit=CANDIDATE):
    return contents(tree(commit)[path][1])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def doc(path, commit=CANDIDATE):
    return json.loads(blob(path, commit))



AUTHOR = 'e44f957bc20c79d443f6e29ac0ba8c611f4787bd'
D = P+'delivery/'
manifest, checks, descriptor = (doc(D+n) for n in ['artifact-manifest.json','checks.json','descriptor.json'])
assert sha(blob(D+'artifact-manifest.json')) == '7a8fee43491d83734811ee774e0aba91c1e97b72fe419209dec8464267831736'
assert sha(blob(D+'checks.json')) == '88bf91d477ab043b7014ec0e0ab05f652ce5aac84f14609869a2f368e99079b1'
delta={p:s for s,p in (line.split('\t') for line in git('diff','--no-renames','--name-status',BASE,CANDIDATE).decode().splitlines())}
assert len(delta)==224 and collections.Counter(delta.values())=={'A':215,'M':9}
assert manifest['member_count']==len(manifest['files'])==223
assert {r['path'] for r in manifest['files']} | {D+'artifact-manifest.json'} == set(delta)
for r in manifest['files']:
    assert tree(CANDIDATE)[r['path']][0]==r['mode']
    assert len(blob(r['path']))==r['bytes'] and sha(blob(r['path']))==r['sha256']
assert descriptor['author']['commit']==AUTHOR
assert sha(blob(P+'artifact-manifest.json'))==descriptor['author']['original_manifest']['sha256']
original=doc(P+'artifact-manifest.json',AUTHOR)
assert original['member_count']==len(original['files'])==171
for r in original['files']:
    assert tree(AUTHOR)[r['path']][0]==r['mode']
    assert len(blob(r['path'],AUTHOR))==r['bytes'] and sha(blob(r['path'],AUTHOR))==r['sha256']
author_delta=git('diff','--name-only',BASE,AUTHOR).decode().splitlines()
assert len(author_delta)==172
assert set(author_delta)=={r['path'] for r in original['files']}|{P+'artifact-manifest.json'}
for path in author_delta:
    if path!='plan/work-items.json': assert tree(AUTHOR)[path]==tree(CANDIDATE)[path]
selections=[]
for s in descriptor['review_selections']:
    source,prefix=s['source_commit'],s['prefix'].rstrip('/')
    assert git('rev-parse',source+'^{tree}').decode().strip()==s['source_tree']
    assert git('rev-parse',source+':'+prefix).decode().strip()==s['prefix_tree']
    assert git('rev-parse',CANDIDATE+':'+prefix).decode().strip()==s['prefix_tree']
    paths=[p for p in tree(source) if p.startswith(prefix+'/')]
    assert len(paths)==s['file_count']
    for path in paths: assert tree(source)[path]==tree(CANDIDATE)[path]
    selections.append({'source':source,'files':len(paths),'prefix_tree':s['prefix_tree']})
review_prefix='docs/restart/implementation/reviews/QP01-request-engine/'
bm=doc(review_prefix+'artifact-manifest.json')
assert bm['candidate']==AUTHOR and bm['member_count']==len(bm['files'])==37
assert {r['path'] for r in bm['files']}|{review_prefix+'artifact-manifest.json'}=={p for p in tree(CANDIDATE) if p.startswith(review_prefix)}
for r in bm['files']:
    assert tree(CANDIDATE)[r['path']][0]==r['mode']
    assert sha(blob(r['path']))==r['sha256'] and len(blob(r['path']))==r['bytes']
correspondence=doc(P+'source-correspondence.json')
assert len(correspondence['current_active_inputs'])==12
for r in correspondence['current_active_inputs']:
    for source in [AUTHOR,'ab0b040e83038e03bc47ceed640a093490c79ef1']:
        assert tree(source)[r['path']]==tree(CANDIDATE)[r['path']]
    assert sha(blob(r['path']))==r['sha256']
old_graph,new_graph=doc('plan/work-items.json',AUTHOR),doc('plan/work-items.json')
normalized=copy.deepcopy(new_graph)
a,b=({t['id']:t for t in g['tasks']} for g in [old_graph,normalized])
assert len(a)==len(b)==47 and set(a)==set(b)
for field in ['current_checkpoint','result_artifacts']: b['QP01'][field]=copy.deepcopy(a['QP01'][field])
assert normalized==old_graph
assert (json.dumps(normalized,indent=2)+'\n').encode()==blob('plan/work-items.json',AUTHOR)
q=next(t for t in new_graph['tasks'] if t['id']=='QP01')
old_artifacts={r['path']:r for r in a['QP01']['result_artifacts']}
current_artifacts={r['path']:r for r in q['result_artifacts']}
assert len(current_artifacts)==len(q['result_artifacts'])==133
assert set(old_artifacts)<=set(current_artifacts)
reconciled=[p for p,r in old_artifacts.items() if current_artifacts[p]!=r]
assert reconciled==['docs/restart/implementation/QP01/README.md']
for path in reconciled:
    assert old_artifacts[path]['sha256']==sha(blob(path,AUTHOR))
    assert dict(current_artifacts[path],sha256=old_artifacts[path]['sha256'])==old_artifacts[path]
for r in current_artifacts.values(): assert sha(blob(r['path']))==r['sha256']
component=q['current_checkpoint']['request_aware_fixture_component']
assert component['criteria_completed']==0 and component['assembly_runtime_executions']==0
assert component['author']==AUTHOR
assert component['implementation_runtime_review']['findings']==[]
for key in ['result','delivery_descriptor','provenance_review','implementation_runtime_review']:
    r=component[key]; assert sha(blob(r['path']))==r['sha256']
assert component['scope']==descriptor['scope'] and component['limits']==descriptor['limits']
assert len(descriptor['authored_input_paths'])==6
stable=checks['source_commit']
assert stable=='eed7eb306749d33044cd3a3cbc33d314b3b50fd4'
assert git('rev-parse',stable+'^{tree}').decode().strip()==checks['source_tree']=='ac9a871defc0f72e36cb261987f17fd225ea3efe'
assert all(tree(CANDIDATE)[p]==v for p,v in tree(stable).items())
tail={p for p in tree(CANDIDATE) if p not in tree(stable)}
expected_tail={D+n for n in ['01-docs.json','02-plan.json','03-evidence.json','04-contracts.json','checks.json','artifact-manifest.json']}
assert tail==expected_tail
assert checks['current_plan_sha256']==sha(blob('plan/work-items.json'))
assert checks['descriptor_sha256']==sha(blob(D+'descriptor.json'))
assert len(checks['stable_input_bindings'])==checks['stable_input_count']==24
for r in checks['stable_input_bindings']:
    assert tree(CANDIDATE)[r['path']][0]==r['mode'] and sha(blob(r['path']))==r['sha256']
expected_argv=[['make','docs'],['python3','scripts/validate_restart_plan.py'],['python3','scripts/verify_evidence.py'],['python3','scripts/verify_contracts.py']]
assert len(checks['structural_receipts'])==4
for entry,argv in zip(checks['structural_receipts'],expected_argv):
    assert entry['argv']==argv and entry['exit_code']==0
    assert sha(blob(entry['path']))==entry['sha256']
    r=doc(entry['path']); c=r['context']
    assert r['argv']==argv and r['exit_code']==0
    assert c['source_commit']==stable and c['source_tree']==checks['source_tree']
    assert c['plan_sha256']==checks['current_plan_sha256'] and c['descriptor_sha256']==checks['descriptor_sha256']
    assert c['source_state_before_first_gate']=='clean tracked and untracked state'
    assert sha(blob(c['environment']['path']))==c['environment']['sha256']
    for stream in ['stdout','stderr']:
        raw=r[stream].encode(); assert len(raw)==r[stream+'_bytes'] and sha(raw)==r[stream+'_sha256']
    assert r['elapsed_seconds']>=0 and r['finished_utc']>=r['started_utc']
full=checks['whitespace']['full_stable_source']
f=subprocess.run(full['argv'],cwd=ROOT,capture_output=True)
assert f.returncode==full['exit_code']==2
assert f.stdout.decode()==full['stdout'] and f.stderr.decode()==full['stderr']
authored=checks['whitespace']['authored_delivery_scope']
assert len(authored['paths'])==12
w=subprocess.run(['git','diff','--check',BASE,CANDIDATE,'--',*authored['paths']],cwd=ROOT,capture_output=True)
assert w.returncode==0 and not w.stdout and not w.stderr
out={'verdict':'PASS_final_delivery_source_and_metadata_only','findings':[],'candidate':CANDIDATE,'tree':git('rev-parse',CANDIDATE+'^{tree}').decode().strip(),'base':BASE,'changed_paths':len(delta),'delta':dict(collections.Counter(delta.values())),'outer_manifest_members':223,'author_manifest_members_validated_at_author':171,'current_exact_author_postimages_excluding_plan':171,'review_selections':selections,'B01_inner_manifest_members':37,'active_runtime_inputs_unchanged':12,'graph':'Only QP01 current_checkpoint/result_artifacts; all46 other full records and all47 formal/resource/release sets unchanged. R00 remains author-exact. Restoring those two fields reconstructs author graph bytes.','current_QP01_artifacts':133,'old_QP01_artifact_paths_preserved':len(old_artifacts),'old_QP01_artifact_rows_exact':len(old_artifacts)-len(reconciled),'current_navigation_artifact_hash_reconciled':reconciled,'stable_source_tracked_files_unchanged':len(tree(stable)),'appended_receipt_manifest_tail':6,'stable_input_bindings_verified':24,'structural_receipts':4,'structural_exits':[0,0,0,0],'full_historical_whitespace':2,'delivery_authored_scope_whitespace':0,'new_product_runtime_build_or_feed_runs':0,'review_scope':'Final assembly only; exact component semantics/runtime remain independently reviewed at025b. No second runtime campaign.','limits':descriptor['limits'],'reader_note':'Reviewed full bounded navigation diffs and delivery README; inspected inline structural receipt and both exact original/current manifest scopes before verification. Large checkpoint read was truncated; relevant changed fields were recovered using key selection and complete graph comparison.'}
(Path(__file__).parent/'validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['limits','review_selections']}))
