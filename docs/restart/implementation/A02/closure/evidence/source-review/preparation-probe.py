#!/usr/bin/env python3
"""Read-only compositional A02 source-closure bindings; no verdict/graph patch."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
PREP='bdc1b6e28288314af705399a188b90e3705e9790'
PRODUCT='b1c90139a651895284b2624da7d12903cf16bc9d'
PREFIX='docs/restart/implementation/A02/closure-preparation/'
SOURCE='bb033619b5346302833d717eb501bfa4e3653a1b'
REPAIR='951ed2ad1bb7c7d85a6eaa735a5286022e8fce36'
ADOPTION='a5f7b9f2e087c9538495a16706644f3390e6b01c'
ADOPTED='d931277bebbc5f43514b0e8438d65fb60603fa35'
RESULT={'phase':'Read-only source-closure preparation; no acceptance verdict',
        'preparation':PREP,'product_candidate':PRODUCT,'candidate_tree':'0014d51b24ea0b58650d3dee3a5a8616367e6769',
        'actual_corrected_main_CI':'PENDING completed API/log capture and actual success',
        'source_acceptance':'PENDING','final_metadata_diff_review':'Separate later required gate',
        'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':{}}
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def content(commit,path):return git('show',commit+':'+path)
def sha(data):return hashlib.sha256(data).hexdigest()
def read(name):return json.loads(content(PREP,PREFIX+name))
def tree(commit):
    rows={}
    for raw in git('ls-tree','-rz','--full-tree',commit).split(b'\0'):
        if raw:
            meta,path=raw.split(b'\t',1);rows[path.decode()]=tuple(meta.decode().split())
    return rows

def main():
    assert git('rev-parse',PRODUCT+'^{tree}')==git('rev-parse',REPAIR+'^{tree}')
    assert git('rev-parse',ADOPTED+'^{tree}')==git('rev-parse',ADOPTION+'^{tree}')
    current=tree(PRODUCT);prepared=tree(PREP);old=tree(ADOPTED)
    changes=[p for p in set(old)|set(prepared) if old.get(p)!=prepared.get(p)]
    assert len(changes)==9 and all(p.startswith(PREFIX) and p not in old for p in changes)
    inventory=read('source-evidence-inventory.json');template=read('closure-template.json')
    plan=json.loads(content(PRODUCT,'plan/work-items.json'));task=next(t for t in plan['tasks'] if t['id']=='A02')
    assert task['status']=='running' and task['result_artifacts']==[]
    assert inventory['accepted_migration_input_commits']==task['input_commits']
    assert template['result_manifest_template']['input_commits']==task['input_commits']
    assert template['result_manifest_template']['acceptance']==task['acceptance']
    assert len(task['acceptance'])==5 and len(task['input_commits'])==5
    assert content(PRODUCT,'plan/work-items.json')==content(ADOPTED,'plan/work-items.json')
    assert content(PRODUCT,'plan/evidence-index.json')==content(ADOPTED,'plan/evidence-index.json')
    assert sha(content(PRODUCT,'plan/evidence-index.json'))==inventory['historical_index']['sha256']
    evidence=inventory['source_evidence'];assert len(evidence)==46
    trees={};blobs={};present=0
    for row in evidence:
        commit,path=row['source_commit'],row['source_path']
        if commit not in trees:trees[commit]=tree(commit)
        assert trees[commit][path]==(row['mode'],'blob',row['blob'])
        if row['blob'] not in blobs:blobs[row['blob']]=git('cat-file','blob',row['blob'])
        data=blobs[row['blob']]
        assert len(data)==row['bytes'] and sha(data)==row['sha256']
        target=row['proposed_future_artifact_path']
        if target in current:
            assert current[target]==trees[commit][path];present+=1
    package_path='docs/restart/implementation/A02/final-review-package.json'
    package=json.loads(content(PRODUCT,package_path))
    assert content(PRODUCT,package_path)==content(SOURCE,package_path)
    source_tree=tree(SOURCE)
    assert len(package['files'])==982
    for row in package['files']:
        path=row['path'];assert current[path]==source_tree[path]
        assert current[path][0]==row['mode'] and sha(content(PRODUCT,path))==row['sha256']
    copies=json.loads(content(PRODUCT,'docs/restart/implementation/A02/coordinator-adoption/source-review-copy.json'))
    assert len(copies['rows'])==143
    for row in copies['rows']:
        assert current[row['destination']]==(row['mode'],'blob',row['blob'])
        assert sha(content(PRODUCT,row['destination']))==row['sha256']
    for row in template['known_underlying_artifact_candidates']:
        assert sha(content(PRODUCT,row['path']))==row['sha256']
    for anchor in ['68508ea1eea1e07b0064fadd65b33433d72701f8','59653fcc15c4cbc21a39d0a0dd5548abe46165b0','f2ef70f522af4977e15f81554a8c6eadcdbe8097']:
        git('merge-base','--is-ancestor',anchor,PRODUCT)
    product=tree('daf8ba03a9eb820f99b0f1bf5c4f553a7961e008')
    old_product_changes=sorted(p for p in product if product[p]!=current.get(p))
    assert old_product_changes==['docs/restart/README.md','docs/restart/implementation/handoff.md','plan/work-items.json','scripts/test_contracts.py','scripts/verify_contracts.py']
    RESULT['checks']={'preparation_nine_added_docs_only':True,'original5_inputs':task['input_commits'],
      'unchanged_five_requirements':task['acceptance'],'original46_inventory_rows_verified':len(evidence),
      'inventory_paths_already_exact_in_repaired_main':present,'known_underlying23_hashes_verified':len(template['known_underlying_artifact_candidates']),
      'all983_author_package_bytes_and_modes_preserved':True,'all143_source_review_copy_bindings_preserved':True,
      'original_isolated_product_existing_paths_changed_only':old_product_changes,
      'PR31_and_PR32_reviewed_tree_to_actual_main_equalities':True,'permanent_ancestors_remain':True,
      'whole_plan_and_historical1508_index_unchanged':True,'no_graph_status_result_changes':True}
    RESULT['outcome']='BINDINGS_VERIFIED_NO_SOURCE_CLOSURE_VERDICT'

try:main()
except Exception as error:
    RESULT['outcome']='PROBE_FAILED';RESULT['failure']={'type':type(error).__name__,'diagnostic':str(error)}
    raise
finally:(OUT/'preparation-result.json').write_text(json.dumps(RESULT,indent=2)+'\n')
