#!/usr/bin/env python3
"""Exact final specification/source-pin checks, reusing immutable prep audit."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess
from urllib.parse import unquote,urlsplit
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
CANDIDATE='e95eaaf8e3fd76ede797f128f0cc7de43ab2bb03'
BASE='b1c90139a651895284b2624da7d12903cf16bc9d'
PREP='e2df91f57c12066d5ea2e2409123cf5127642651'
PREP_REVIEW='b04b42cd8e8f68a1b8d0f8edf314986f2b6a5891'
PREFIX='docs/restart/implementation/S03/integration/'
RESULT={'candidate':CANDIDATE,'candidate_tree':'44c0a86a240a46beb4869deb1be747187d89daa9','actual_main':BASE,
        'review_phase':'Final preimplementation specification review only',
        'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':{}}
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def body(commit,path):return git('show',commit+':'+path)
def read(commit,name):return json.loads(body(commit,PREFIX+name))
def tree(commit):
    rows={}
    for raw in git('ls-tree','-rz','--full-tree',commit).split(b'\0'):
        if raw:
            meta,path=raw.split(b'\t',1);rows[path.decode()]=tuple(meta.decode().split())
    return rows

def main():
    final=tree(CANDIDATE);base=tree(BASE);old=tree('a5f7b9f2e087c9538495a16706644f3390e6b01c')
    assert git('rev-parse',CANDIDATE+'^{tree}').decode().strip()==RESULT['candidate_tree']
    changed=sorted(p for p in set(final)|set(base) if final.get(p)!=base.get(p))
    expected=[PREFIX+n for n in ['acceptance-plan.json','brief.md','nip-reconciliation.json','source-pin-addendum.json','source-reconciliation.json']]
    assert changed==expected and all(p not in base and final[p][:2]==('100644','blob') for p in changed)
    git('diff','--check',BASE,CANDIDATE)
    source=read(CANDIDATE,'source-reconciliation.json');acceptance=read(CANDIDATE,'acceptance-plan.json');addendum=read(CANDIDATE,'source-pin-addendum.json')
    oldsource=read(PREP,'source-reconciliation.json');oldacceptance=read(PREP,'acceptance-plan.json')
    for key in ['source_changed_files','requirement_and_target_context','original_case_families','target_lock_package_inventories','original_combined_source_lock_packages','explicit_collision_resolutions']:
        assert source[key]==oldsource[key],key
    assert acceptance['preserved_original_cases']==oldacceptance['preserved_original_cases']
    assert read(CANDIDATE,'nip-reconciliation.json')==read(PREP,'nip-reconciliation.json')
    prep_path='docs/restart/implementation/reviews/S03-integration-spec/'
    prep_result=body(PREP_REVIEW,prep_path+'preparation-result.json')
    assert sha(prep_result)=='67baa7f843016863c49f733902453f9af2b714c66b9f2ae94a6156d36e359287'
    assert json.loads(prep_result)['outcome']=='BINDINGS_VERIFIED_NO_ADMISSION'
    assert sha(body(PREP_REVIEW,prep_path+'preparation-probe.py'))=='f45dd02dc405cb6a57d469140c1e2284484becf7becf6d2dd723029a19341fd9'
    rows=source['source_changed_files'];assert len(rows)==746
    for row in rows:
        entry=row['preparation_target'];expected=None if entry is None else (entry['mode'],'blob',entry['blob'])
        assert base.get(row['path'])==expected,row['path']
    plan=json.loads(body(BASE,'plan/work-items.json'));task=next(t for t in plan['tasks'] if t['id']=='S03')
    assert source['canonical_acceptance']==acceptance['canonical_acceptance']==task['acceptance']
    assert len(task['acceptance'])==5
    assert all(final[p]==info for p,info in base.items())
    RESULT['checks']['unchanged_preparation_reuse']={'source_review':PREP_REVIEW,
       'source_preparation':PREP,'all746_target_preimages_unchanged':True,
       'original810_binding_and_vendor_checksum_audit_preserved':True,
       'all20_families_and5_criteria_preserved':True,'NIP_primary_assessment_unchanged':True,
       'no_product_graph_lock_fixture_or_existing_file_change':True,
       'new_five_doc_bindings':[{'path':p,'mode':final[p][0],'blob':final[p][2],'sha256':sha(body(CANDIDATE,p))} for p in changed]}
    assert addendum['input_main']==BASE and addendum['input_tree']=='0014d51b24ea0b58650d3dee3a5a8616367e6769'
    assert len(addendum['context_bindings'])==30
    changed_context=[]
    for row in addendum['context_bindings']:
        path=row['path'];data=body(BASE,path)
        assert row['commit']==BASE and base[path]==(row['mode'],'blob',row['blob'])
        assert sha(data)==row['sha256'] and len(data)==row['bytes']
        unchanged=base[path]==old[path]
        assert unchanged==row['unchanged_from_preparation']
        assert sha(body('a5f7b9f2e087c9538495a16706644f3390e6b01c',path))==row['preparation_sha256']
        if not unchanged:changed_context.append(path)
    assert sorted(changed_context)==['scripts/test_contracts.py','scripts/verify_contracts.py']
    actual_delta={p for p in set(old)|set(base) if old.get(p)!=base.get(p)}
    delta=addendum['whole_main_delta_from_preparation'];assert len(delta)==85
    assert {row['path'] for row in delta}==actual_delta
    for row in delta:
        for key,t in [('old',old),('current',base)]:
            entry=row[key];expected=None if entry is None else (entry['mode'],entry['type'],entry['blob'])
            assert expected==t.get(row['path'])
    readonly=set(addendum['read_only_target_interfaces'])
    assert readonly=={'scripts/verify_contracts.py','scripts/test_contracts.py','scripts/check_product_gates.py','scripts/test_product_gates.py','tests/integration/run.py','protocols/contracts/v1/**'}
    manifest=addendum['historical_public_copy_manifest'];assert manifest['count']==80
    assert manifest['source_delivery_rows']==39 and manifest['original_security_review_files']==41
    assert len(manifest['files'])==80 and len({r['path'] for r in manifest['files']})==80
    source_evidence={r['path'] for r in rows if r['group']=='historical_source_evidence'}
    review='b03475ccf4a057c7771065126002f2e4e056d28d'
    security={p for p in tree(review) if p.startswith('docs/restart/implementation/reviews/S03-security/')}
    assert len(security)==41 and {r['path'] for r in manifest['files']}==source_evidence|security
    trees={}
    for row in manifest['files']:
        commit,path=row['commit'],row['path']
        assert commit==(review if path in security else '03216fba02d229bcdb5c81d0573bbe26c6f35abc')
        if commit not in trees:trees[commit]=tree(commit)
        assert trees[commit][path]==(row['mode'],'blob',row['blob']) and row['mode']=='100644'
        data=body(commit,path);assert len(data)==row['bytes'] and sha(data)==row['sha256']
        assert path not in base
    RESULT['checks']['final_source_and_scope']={'actual_main30_context_rows_verified':30,
       'changed_context_paths':changed_context,'all85_main_delta_paths_classified':True,
       'read_only_interfaces':sorted(readonly),'exact_historical_public_new_copies':80,
       'source_delivery_copies':39,'original_security_review_copies':41,'all_copy_modes_blobs_sizes_hashes_verified':True,
       'canonical_task_dependencies_preserved':task['depends_on'],
       'coordinator_source_and_implementation_admission_gates_not_waived':True}
    capture_dir=Path('/home/tux/nsealr/.restart-tools/goal/a02-ci-2026-10-20/run-39412818666')
    capture_data=(capture_dir/'capture.json').read_bytes();capture=json.loads(capture_data)
    assert sha(capture_data)=='71369a06a757df909a9c963b167c190821c07b5bea97c18cc321435008344229'
    ci=addendum['actual_main_CI'];assert ci['head_sha']==BASE and ci['id']==39412818666
    assert ci['status']=='completed' and ci['conclusion']=='success' and addendum['main_CI_passed'] is True
    for row in ci['coordinator_capture']['files']:
        data=(capture_dir/row['path']).read_bytes();assert len(data)==row['size'] and sha(data)==row['sha256']
    for row in capture['files']:
        data=(capture_dir/row['path']).read_bytes();assert len(data)==row['size'] and sha(data)==row['sha256']
    run=json.loads((capture_dir/'run.json').read_bytes());jobs=json.loads((capture_dir/'jobs.json').read_bytes())
    assert run['head_sha']==BASE and run['id']==39412818666 and run['event']=='push'
    assert run['conclusion']=='success' and run['status']=='completed' and run['run_attempt']==1
    assert [(j['id'],j['name'],j['conclusion']) for j in jobs['jobs']]==[(118594507068,'verify','success')]
    with ZipFile(capture_dir/'logs.zip') as archive:
        assert set(archive.namelist())=={row['name'] for row in capture['zip_members']}
        for row in capture['zip_members']:
            data=archive.read(row['name']);assert len(data)==row['size'] and sha(data)==row['sha256']
        acceptance_log=archive.read('verify/5_Complete product acceptance.txt').decode()
        bootstrap_log=archive.read('verify/4_Bootstrap exact public product and pinned tools.txt').decode()
    assert BASE in bootstrap_log and 'All 17 retained product integration steps passed.' in acceptance_log
    assert '"failed_commands": []' in acceptance_log
    assert acceptance['implementation_admitted'] is False and addendum['implementation_admitted'] is False
    RESULT['checks']['actual_main_CI_evidence']={'run':39412818666,'head':BASE,'event':'push','attempt':1,
       'verify_job':118594507068,'actual_conclusion':'success','captured_files':capture['files'],
       'capture_sha256':sha(capture_data),'all10_decompressed_members_verified':True,
       'actual_exact_source_bootstrap_and_complete17_product_acceptance_confirmed':True,
       'no_S03_product_execution_or_implementation_admission_in_spec':True}
    links=0
    for path in changed:
        if not path.endswith('.md'):continue
        for raw in re.findall(r'\[[^\]\n]*\]\(([^\s)]+)\)',body(CANDIDATE,path).decode()):
            url=urlsplit(raw)
            if url.scheme or url.netloc or not url.path:continue
            dest=(ROOT/path).parent/unquote(url.path)
            assert dest.resolve().is_relative_to(ROOT) and dest.exists(),(path,raw)
            links+=1
    RESULT['checks']['metadata_validation']={'new_JSON_valid':4,'changed_docs_whitespace_exit':0,'relative_brief_links_resolve':links,
       'no_product_suite_run_for_doc_only_specification':True}
    coordinator=Path('/home/tux/nsealr/.restart-tools/goal/s03-preparation-checks-2026-10-20')
    checked=json.loads((coordinator/'result.json').read_bytes())
    assert checked['candidate']==CANDIDATE and checked['tree']==RESULT['candidate_tree']
    recorded=json.loads((coordinator/'commands.json').read_bytes())
    for row in recorded:
        assert row['exit_code']==0 and sha((coordinator/row['log']).read_bytes())==row['sha256']
    RESULT['checks']['coordinator_affected_checks']={'candidate':checked['candidate'],
      'result_sha256':sha((coordinator/'result.json').read_bytes()),
      'commands_sha256':sha((coordinator/'commands.json').read_bytes()),
      'three_recorded_log_hashes_verified':True,'independent_base_to_candidate_whitespace_check_also_passed':True}
    RESULT['outcome']='EXACT_SPECIFICATION_BINDINGS_VERIFIED'

try:main()
except Exception as error:
    RESULT['outcome']='PROBE_FAILED';RESULT['failure']={'type':type(error).__name__,'diagnostic':str(error)}
    raise
finally:(OUT/'probe-result.json').write_text(json.dumps(RESULT,indent=2)+'\n')
