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
CANDIDATE = 'e44f957bc20c79d443f6e29ac0ba8c611f4787bd'
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



result = doc(P+'result.json')
manifest = doc(P+'artifact-manifest.json')
assert sha(blob(P+'artifact-manifest.json')) == '4975636e98dc091fdf785e650ea6bf4aaad049896cc4ad8c62ecd88e26e664b5'
assert sha(blob(P+'result.json')) == 'd90dc0f899b950ff7693f7eaaf6beab6144f24c956c43ff6eaeb2e7505af3067'
delta = {p:s for s,p in (line.split('\t') for line in git('diff','--no-renames','--name-status',BASE,CANDIDATE).decode().splitlines())}
assert len(delta)==172 and collections.Counter(delta.values())=={'A':166,'M':6}
assert manifest['member_count']==len(manifest['files'])==171
assert {r['path'] for r in manifest['files']} | {P+'artifact-manifest.json'} == set(delta)
for row in manifest['files']:
    assert tree(CANDIDATE)[row['path']][0]==row['mode']
    assert len(blob(row['path']))==row['bytes'] and sha(blob(row['path']))==row['sha256']
assert {p for p,s in delta.items() if s=='M'} == {'Cargo.toml','Cargo.lock','Makefile','ci/ratchet.json','scripts/check_product_gates.py','plan/work-items.json'}
for path,status in delta.items():
    if status=='A':
        assert path.startswith((P,'crates/nsealr-pi-engine-fixture/','docs/restart/implementation/reviews/QP01-request-engine-contract/')) or path in ['apps/pi/app/nsealr_vault/engine_adapter.py','apps/pi/tests/test_engine_adapter.py']

correspondence=doc(P+'source-correspondence.json')
executed=result['executed_product_source']
structural=result['final_structural_source']
assert executed=='ab0b040e83038e03bc47ceed640a093490c79ef1'
assert structural=='f75ff2235721793ba88fc84cefd9a36a912e54cb'
assert len(correspondence['current_active_inputs'])==12
for row in correspondence['current_active_inputs']:
    assert tree(executed)[row['path']]==tree(structural)[row['path']]==tree(CANDIDATE)[row['path']]
    assert sha(blob(row['path']))==row['sha256']
for row in correspondence['unchanged_source_bindings']:
    actual=git('rev-parse',CANDIDATE+':'+row['path']).decode().strip()
    assert actual==row['git_object']==git('rev-parse',BASE+':'+row['path']).decode().strip()
for path in tree(BASE):
    if path.startswith('apps/pi/'):
        assert tree(BASE)[path]==tree(CANDIDATE)[path]

old_graph,new_graph=doc('plan/work-items.json',BASE),doc('plan/work-items.json')
normalized=copy.deepcopy(new_graph)
a,b=({t['id']:t for t in g['tasks']} for g in [old_graph,normalized])
assert set(a)==set(b) and len(a)==47
changed=[]
for before,after in zip(a['R00']['result_artifacts'],b['R00']['result_artifacts']):
    assert before['path']==after['path']
    if before!=after:
        path=before['path'];assert path in ['Cargo.lock','Makefile','scripts/check_product_gates.py']
        assert before['sha256']==sha(blob(path,BASE)) and after['sha256']==sha(blob(path))
        restored=dict(after,sha256=before['sha256']);assert restored==before
        after['sha256']=before['sha256'];changed.append(path)
assert set(changed)=={'Cargo.lock','Makefile','scripts/check_product_gates.py'}
assert normalized==old_graph
assert len(correspondence['R00_current_artifact_reconciliation'])==3
for row in correspondence['R00_current_artifact_reconciliation']:
    assert row['preimage_graph_source']==BASE and row['postimage_source_commit']==executed
    assert sha(blob(row['path'],BASE))==row['preimage_sha256']
    assert sha(blob(row['path']))==row['postimage_sha256']

old_lock=tomllib.loads(blob('Cargo.lock',BASE).decode())
new_lock=tomllib.loads(blob('Cargo.lock').decode())
fixture=[r for r in new_lock['package'] if r['name']=='nsealr-pi-engine-fixture']
assert len(fixture)==1 and fixture[0]['version']=='0.0.0' and 'source' not in fixture[0]
assert fixture[0]['dependencies']==['nsealr-core']
new_lock['package']=[r for r in new_lock['package'] if r['name']!='nsealr-pi-engine-fixture']
assert new_lock==old_lock
old_workspace=tomllib.loads(blob('Cargo.toml',BASE).decode())
new_workspace=tomllib.loads(blob('Cargo.toml').decode())
new_workspace['workspace']['members'].remove('crates/nsealr-pi-engine-fixture')
assert old_workspace==new_workspace
crate=tomllib.loads(blob('crates/nsealr-pi-engine-fixture/Cargo.toml').decode())
assert crate['package']['publish'] is False
assert set(crate['dependencies'])=={'nsealr-core'}
edge=crate['dependencies']['nsealr-core']
assert edge['version']=='=0.0.0' and edge['default-features'] is False
assert blob('deny.toml')==blob('deny.toml',BASE)
old_floor,new_floor=doc('ci/ratchet.json',BASE),doc('ci/ratchet.json')
assert new_floor['coverage']['floors'].pop('nsealr-pi-engine-fixture')==100.0
assert new_floor==old_floor

imports=doc(P+'import-bindings.json')
assert imports['count']==len(imports['files'])==30 and imports['runtime_or_ELF_copies']==0
authorized={}
for name in ['brief.md','expectations.json','source-bindings.json']:
    authorized[P+name]='2beee74cb7ca88d67adf73d774b4a64cded70190'
review_prefix='docs/restart/implementation/reviews/QP01-request-engine-contract/'
for name in ['report.md','review.json','validation.json']:
    authorized[review_prefix+name]='20adacc072d79f0ca5c9a37e454ad8af40ea1792'
for name in ['nonce-adjudication.json','nonce-amendment-review.json']:
    authorized[review_prefix+name]='f57013b7892f5266154808ae176c9c549782c121'
investigation='5740407eeac6a4716be21616695d8f34939b6147'
for path in tree(investigation):
    if path.startswith(P+'nonce-contract/'):
        authorized[path]=investigation
assert len(authorized)==30 and {r['path'] for r in imports['files']}==set(authorized)
for row in imports['files']:
    assert row['source_commit']==authorized[row['path']]
    assert tree(row['source_commit'])[row['path']]==tree(CANDIDATE)[row['path']]
    assert len(blob(row['path']))==row['bytes'] and sha(blob(row['path']))==row['sha256']
    assert tree(executed)[row['path']]==tree(CANDIDATE)[row['path']]

output_paths=set();variants=collections.Counter()
for record in result['command_receipts']:
    path=P+record['receipt'];assert sha(blob(path))==record['sha256']
    receipt=doc(path)
    assert (receipt['source'],receipt['argv'],receipt['exit'])==(record['source'],record['argv'],record['exit'])
    assert git('rev-parse',receipt['source']+'^{tree}').decode().strip()==receipt['tree']
    if 'outputs' in receipt:
        variants['ordinary_with_output_hashes']+=1
        for filename,digest in receipt['outputs'].items():
            log=str(Path(path).parent/filename);assert sha(blob(log))==digest;output_paths.add(log)
    else:
        variants['initial_precode_RED_without_output_map']+=1
        assert record['receipt']=='evidence/red-01/receipt.json' and receipt['exit']==1
        test='apps/pi/tests/test_engine_adapter.py'
        assert sha(blob(test,receipt['source']))==receipt['test_sha256']
        assert 'apps/pi/app/nsealr_vault/engine_adapter.py' not in tree(receipt['source'])
assert len(result['command_receipts'])==35 and variants=={'ordinary_with_output_hashes':34,'initial_precode_RED_without_output_map':1}
expected_structural={'final-01-docs':['make','docs'], 'final-02-plan':['python3','scripts/validate_restart_plan.py'], 'final-03-frozen':['python3','scripts/verify_evidence.py'], 'final-04-contracts':['python3','scripts/verify_contracts.py']}
for directory,argv in expected_structural.items():
    receipt=doc(P+'evidence/'+directory+'/receipt.json')
    assert receipt['source']==structural and receipt['exit']==0 and receipt['argv']==argv
cases=doc(P+'case-results.json');expectations=doc(P+'expectations.json')
assert len(cases['cases'])==len(expectations['cases'])==23
assert [r['id'] for r in cases['cases']]==[r['id'] for r in expectations['cases']]
assert all(r['status']=='PASS_scoped_host_controls' for r in cases['cases'])
assert sha(blob(P+'case-results.json'))==result['case_results_sha256']
assert result['format_check']['full_exit']==2 and result['format_check']['authored_only_exit']==0
out={'status':'PASS_candidate_provenance_and_graph_only_COMPONENT_REVIEW_PENDING','candidate':CANDIDATE,'tree':git('rev-parse',CANDIDATE+'^{tree}').decode().strip(),'manifest_members':171,'changed_paths':172,'changes':dict(collections.Counter(delta.values())),'exact_imports':30,'runtime_source':executed,'structural_source':structural,'runtime_and_structural_input_postimages_identical':12,'unchanged_prior_source_bindings':len(correspondence['unchanged_source_bindings']),'exact_receipts':35,'receipt_variants':dict(variants),'receipt_bound_output_paths':len(output_paths),'all_raw_manifest_role_files_hashed':71,'all47formal_and46other_full_task_records_unchanged':True,'only_R00_three_current_hashes_updated':changed,'only_new_workspace_package':'nsealr-pi-engine-fixture0.0.0 local core edge; no other package record changed','coverage_change':'Only new member100 floor; all previous values/checker unchanged','case_ledger':'23 scoped statuses/IDs checked for integrity; B01 independently assesses semantic/runtime coverage','full_source_whitespace':2,'explicit_authored_scope':0,'new_product_runtime_or_signature_runs':0,'reader_note':'Inspected both receipt variants before checking them; initial RED has test/source binding but no output-map, original raw logs remain outer-manifest-bound. Nonce and other raw sources retained unchanged.','limits':['Not code/runtime adoption; independent component review and actual protected PR/resulting-main gates required.','Fixture-only host component, no camera/ARM/physical/provider/custody/profile qualification; no new cdylib reproducibility claim.']}
(Path(__file__).parent/'validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
