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
BASE = '5c701113bc2ac2d7b596f7d3fb76574a7cff24b3'
CANDIDATE = '8b20b98f1e8962cdce8b2fa4cd3be116e7b2bd9d'
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



import re
from urllib.parse import unquote, urlparse
result=doc(P+'readiness-result.json');checks=doc(P+'readiness-checks.json');manifest=doc(P+'readiness-artifact-manifest.json')
assert sha(blob(P+'readiness-result.json'))=='82e8808c7247ba0934f64a549df473367601d5be99939f357804751dc400bcba'
assert sha(blob(P+'readiness-checks.json'))=='78f158fc6f6cc3337c1b1dc08822ea65f5753554973e5839227f2242b531c5cd'
assert sha(blob(P+'readiness-artifact-manifest.json'))=='a83dfbbccedf1a66a5ad8ce6b2f0c63ef2d3c8e0397c05b2fc3343fed7192853'
delta={p:s for s,p in (line.split('\t') for line in git('diff','--no-renames','--name-status',BASE,CANDIDATE).decode().splitlines())}
assert len(delta)==69 and collections.Counter(delta.values())=={'A':66,'M':3}
assert manifest['member_count']==len(manifest['files'])==68
assert {r['path'] for r in manifest['files']}|{P+'readiness-artifact-manifest.json'}==set(delta)
for row in manifest['files']:
    path=row['path'];assert tree(CANDIDATE)[path][0]==row['mode']
    assert len(blob(path))==row['bytes'] and sha(blob(path))==row['sha256']
modified={P+'exchange.py',P+'client-exchange.ts','plan/work-items.json'}
assert {p for p,s in delta.items() if s=='M'}==modified
unchanged={p for p,v in tree(BASE).items() if tree(CANDIDATE).get(p)==v}
assert len(tree(BASE))==8644 and len(unchanged)==8641
assert set(tree(BASE))-unchanged==modified
runtime=result['executed_product_source'];stable=checks['final_structural_source']
assert runtime=='b75db930d89a7dfbd9c28036c3d345c81aecd1ac' and stable=='618f6fe127b282a278b981ef8ed0b39ebae87e4d'
for row in result['product_delta']:
    path=row['path'];assert tree(runtime)[path]==tree(stable)[path]==tree(CANDIDATE)[path]
    assert sha(blob(path))==row['sha256']
assert len(result['product_delta'])==2
for row in result['unchanged_active_author_inputs']:
    path=row['path'];assert tree(BASE)[path]==tree(runtime)[path]==tree(CANDIDATE)[path]
    assert sha(blob(path))==row['sha256']
assert len(result['unchanged_active_author_inputs'])==10
for row in result['historical_manifests'].values():
    if isinstance(row,dict): assert sha(blob(row['path']))==row['sha256'] and tree(BASE)[row['path']]==tree(CANDIDATE)[row['path']]
pre='aca364addf102abc86b37aac5623f4018255d249'
for name in ['readiness-correction.json','readiness-correction.md','readiness-regression.py']:
    assert tree(pre)[P+name]==tree(CANDIDATE)[P+name]
review=result['root_scope_review'];assert sha(blob(review['path']))==review['sha256']
prefix='docs/restart/implementation/reviews/QP01-readiness-contract/'
for path in tree(result['root_scope_review_commit']):
    if path.startswith(prefix): assert tree(result['root_scope_review_commit'])[path]==tree(CANDIDATE)[path]
old_graph,new_graph=doc('plan/work-items.json',BASE),doc('plan/work-items.json')
normalized=copy.deepcopy(new_graph)
a,b=({t['id']:t for t in g['tasks']} for g in [old_graph,normalized])
assert len(a)==len(b)==47 and set(a)==set(b)
for key in ['current_checkpoint','result_artifacts']: b['QP01'][key]=copy.deepcopy(a['QP01'][key])
assert normalized==old_graph and (json.dumps(normalized,indent=2)+'\n').encode()==blob('plan/work-items.json',BASE)
q=next(t for t in new_graph['tasks'] if t['id']=='QP01')
old_rows={r['path']:r for r in a['QP01']['result_artifacts']};new_rows={r['path']:r for r in q['result_artifacts']}
assert len(old_rows)==133 and len(new_rows)==140 and set(old_rows)<=set(new_rows)
assert all(new_rows[p]==r for p,r in old_rows.items())
for row in new_rows.values(): assert sha(blob(row['path']))==row['sha256']
variants=collections.Counter();output_paths=set()
for entry in result['command_receipts']+checks['final_gates']:
    path=entry['path'];assert sha(blob(path))==entry['sha256'];receipt=doc(path)
    if 'outputs' in receipt:
        variants['ordinary']+=1
        assert receipt['source']==entry['source'] if 'source' in entry else receipt['source']==stable
        assert receipt['argv']==entry['argv'] and receipt['exit']==entry['exit_code']
        assert git('rev-parse',receipt['source']+'^{tree}').decode().strip()==receipt['tree']
        for name,digest in receipt['outputs'].items():
            output=str(Path(path).parent/name);assert sha(blob(output))==digest;output_paths.add(output)
    else:
        variants['precode_missing_interface_RED']+=1
        assert receipt['source_commit']=='61796c7f8bfd134c8e9fea83ab9462a9d1a1b7dd' and receipt['exit_code']==entry['exit_code']==1
        for stream in ['stdout','stderr']:
            output=str(Path(path).parent/(stream+'.log'));assert sha(blob(output))==receipt[stream+'_sha256'];output_paths.add(output)
assert variants=={'ordinary':16,'precode_missing_interface_RED':1}
assert len(result['command_receipts'])==12 and len(checks['final_gates'])==5
expected=[['make','product-gates'],['make','docs'],['python3','scripts/validate_restart_plan.py'],['python3','scripts/verify_evidence.py'],['python3','scripts/verify_contracts.py']]
for row,argv in zip(checks['final_gates'],expected):
    receipt=doc(row['path']);assert receipt['source']==stable and receipt['exit']==0 and receipt['argv']==argv
assert all(tree(CANDIDATE)[p]==v for p,v in tree(stable).items())
tail=set(tree(CANDIDATE))-set(tree(stable));assert len(tail)==17
expected_tail={P+'readiness-checks.json',P+'readiness-artifact-manifest.json'}
for row in checks['final_gates']:
    expected_tail.add(row['path']);receipt=doc(row['path'])
    expected_tail.update(str(Path(row['path']).parent/name) for name in receipt['outputs'])
assert tail==expected_tail and len(checks['stable_input_bindings'])==13
for row in checks['stable_input_bindings']:assert sha(blob(row['path']))==row['sha256']
bridge=result['Bridge_build_and_reuse'];assert len(bridge['source_closure'])==18
for row in bridge['source_closure']:
    assert git('rev-parse',CANDIDATE+':'+row['path']).decode().strip()==row['git_object']==git('rev-parse',BASE+':'+row['path']).decode().strip()
for key in ['actual_fresh_package_build','offline_install','cache_copy_observation','reused_prior_full_Bridge_receipt','consumed_direct_Bridge_source']:
    row=bridge[key];assert sha(blob(row['path']))==row['sha256']
resolution=json.loads(bridge['resolution_command']['stdout']);assert bridge['resolution_command']['exit_code']==0
assert {r['name']:r['url'] for r in resolution}=={r['name']:r['url'] for r in bridge['actual_three_top_level_package_imports']}
for row in bridge['actual_three_top_level_package_imports']:
    disk=Path(unquote(urlparse(row['url']).path));assert disk.is_relative_to('/home/tux/nsealr/.restart-tools/goal/qp01-request-engine-correction')
    assert sha(disk.read_bytes())==row['sha256']
# Bound real final execution; do not execute a second native campaign.
record=next(r for r in result['command_receipts'] if '/readiness-stable-pi-03/' in r['path']);receipt=doc(record['path'])
text='\n'.join(blob(str(Path(record['path']).parent/name)).decode() for name in receipt['outputs'])
objects=[];decoder=json.JSONDecoder()
for match in re.finditer(r'^\{',text,re.M):
    try: value,_=decoder.raw_decode(text[match.start():])
    except json.JSONDecodeError: continue
    if isinstance(value,dict):objects.append(value)
ready=[v for v in objects if v.get('scope')=='readiness_controls'];client=[v for v in objects if v.get('scope')=='actual client + public-fixture host adapter only']
assert len(ready)==len(client)==1
x,y=ready[0],client[0];assert x['readiness_controls']==5 and x['request_bytes_sent']==x['native_reports']==0 and x['children']==x['collected']==5
assert y['positive']==2 and y['valid_shape_verifier_negatives']==y['post_native_currentness_negatives']==5 and y['children']==y['collected']==14 and y['actual_unsettled_child_timeout_no_early_reuse_then_fresh'] is True
assert receipt['source']==runtime and receipt['exit']==0 and receipt['argv']==['make','-o','bridge-ci','pi-ci']
assert re.search(r'Ran 189 tests in .+s',text)
full=checks['whitespace']['full'];authored=checks['whitespace']['authored_only']
assert full['exit_code']==2 and authored['exit_code']==0
f=subprocess.run(['git','diff','--check',BASE,CANDIDATE],cwd=ROOT,capture_output=True)
assert f.returncode==2 and f.stdout.decode()==full['stdout'] and f.stderr.decode()==full['stderr']
assert authored['argv'][:4]==['git','diff','--check',BASE]
w=subprocess.run(['git','diff','--check',BASE,CANDIDATE,*authored['argv'][4:]],cwd=ROOT,capture_output=True)
assert w.returncode==0 and not w.stdout and not w.stderr
out={'verdict':'PASS_readiness_source_provenance_and_graph_only_B01_SEPARATE','candidate':CANDIDATE,'tree':git('rev-parse',CANDIDATE+'^{tree}').decode().strip(),'base':BASE,'delta':dict(collections.Counter(delta.values())),'changed_paths':69,'manifest_members':68,'unchanged_base_postimages':8641,'only_modified_base_paths':sorted(modified),'runtime_source':runtime,'runtime_code_postimages_exact':2,'unchanged_active_author_inputs':10,'all47_formal_and46other_task_records_unchanged':True,'current_QP01_artifacts':140,'all133_original_artifact_rows_exact':True,'receipt_variants':dict(variants),'hash_bound_output_paths':len(output_paths),'all_five_final_gates_exit0_at_stable_source':True,'all_stable_source_postimages_exact':len(tree(stable)),'tail_files':17,'stable_explicit_inputs':13,'Bridge_source_closure_bindings':18,'actual_consumed_entrypoints_disk_SHA_verified':3,'compiled_output_aggregate_inventories':'13 informational inventory summaries not independently recomputed here; explicit entry hashes/build receipts and full unchanged source closure checked. B01 independently verifies consumed closure/runtime.','actual_default_provisioning_run':{'Pi':189,'readiness':x,'client':{k:v for k,v in y.items() if k!='reports'},'Bridge_prerequisite':'source-identical reuse via explicit -o, not fresh Bridge/full hostedCI'},'full_raw_whitespace':2,'author_whitespace_scope':0,'new_runtime_or_builds_by_root':0,'findings':[],'reader_note':'Recovered necessary structured Bridge/receipt fields after an overlarge initial result selection was truncated; did not assume that entire output was read. Both receipt variants inspected before verification.','limits':['Provenance/graph only; independent B01 affected semantic/runtime review required, then full protected PR and actual-main gates.','Only explicit public-fixture trusted-host engineering; no production custody/provider/entropy, camera/UI/ARM/P4/physical/target/reproducibility/task/release qualification.']}
(Path(__file__).parent/'validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['limits','actual_default_provisioning_run']}))
