#!/usr/bin/env python3
"""Verify actual protected delivery/CI chain and exact repaired-source inputs."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
CAPTURES=Path('/home/tux/nsealr/.restart-tools/goal/a02-ci-2026-10-20')
PRODUCT='b1c90139a651895284b2624da7d12903cf16bc9d'
ADOPTION='a5f7b9f2e087c9538495a16706644f3390e6b01c'
ADOPTED='d931277bebbc5f43514b0e8438d65fb60603fa35'
REPAIR='951ed2ad1bb7c7d85a6eaa735a5286022e8fce36'
RESULT={'product_candidate':PRODUCT,'tree':'0014d51b24ea0b58650d3dee3a5a8616367e6769',
        'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':{}}
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def body(commit,path):return git('show',commit+':'+path)
def tree(commit):return git('rev-parse',commit+'^{tree}').decode().strip()
def capture_file(path):
    data=path.read_bytes()
    return {'path':str(path.relative_to(CAPTURES)),'bytes':len(data),'sha256':sha(data)}

def main():
    runs=[]
    for rid,head,event,conclusion in [(39406783194,ADOPTION,'pull_request','success'),
           (39408038674,ADOPTED,'push','failure'),(39411242641,REPAIR,'pull_request','success'),
           (39412818666,PRODUCT,'push','success')]:
        folder=CAPTURES/('run-'+str(rid));capture=json.loads((folder/'capture.json').read_bytes())
        run=json.loads((folder/'run.json').read_bytes());jobs=json.loads((folder/'jobs.json').read_bytes())
        assert run['id']==rid and run['head_sha']==head and run['event']==event
        assert run['status']=='completed' and run['conclusion']==conclusion and run['run_attempt']==1
        assert capture['head_sha']==head and capture['conclusion']==conclusion
        assert len(jobs['jobs'])==1 and jobs['jobs'][0]['conclusion']==conclusion
        for row in capture['files']:
            data=(folder/row['path']).read_bytes()
            assert len(data)==row['size'] and sha(data)==row['sha256']
        with ZipFile(folder/'logs.zip') as archive:
            assert set(archive.namelist())=={r['name'] for r in capture['zip_members']}
            for row in capture['zip_members']:
                data=archive.read(row['name']);assert len(data)==row['size'] and sha(data)==row['sha256']
            bootstrap=archive.read('verify/4_Bootstrap exact public product and pinned tools.txt').decode()
            accepted=archive.read('verify/5_Complete product acceptance.txt').decode()
        if conclusion=='success':
            assert 'All 17 retained product integration steps passed.' in accepted
            assert '"failed_commands": []' in accepted
        else:
            assert '5cb16cbaffc6b90ca9dfbb1ce7a5388e731d1ae0:protocols/contracts/v1/manifest.json' in accepted
            assert 'exit status 128' in accepted
        if event=='push':assert head in bootstrap
        runs.append({'id':rid,'head':head,'event':event,'conclusion':conclusion,'attempt':1,
          'verify_job':jobs['jobs'][0]['id'],'full_actual_API_and_log_members_verified':len(capture['zip_members']),
          'files':[capture_file(folder/n) for n in ['capture.json','run.json','jobs.json','logs.zip']]})
    assert runs[-1]['files'][0]['sha256']=='71369a06a757df909a9c963b167c190821c07b5bea97c18cc321435008344229'
    protected=[];synthetic_bindings=[]
    for number,head,main,admission_name in [(31,ADOPTION,ADOPTED,'protected-merge-admission.json'),
                       (32,REPAIR,PRODUCT,'repair-protected-merge-admission.json')]:
        admission=json.loads((CAPTURES/admission_name).read_bytes())
        request=json.loads((CAPTURES/f'merge-pr{number}-request.json').read_bytes())
        response=json.loads((CAPTURES/f'merge-pr{number}-response.json').read_bytes())
        if 'stdout' in response:
            assert response['exit_code']==0 and response['force_or_admin_bypass'] is False
            response=json.loads(response['stdout'])
        assert request=={'sha':head,'merge_method':'rebase'}
        assert response['merged'] is True and response['sha']==main
        assert admission['head']==head and tree(head)==tree(main)==admission['tree']
        synthetic=admission['tested_synthetic_merge']
        api_command=['gh','api','repos/nSealr/nsealr/git/commits/'+synthetic,
                     '--jq','{sha:.sha,tree:.tree.sha,parents:[.parents[].sha]}']
        api_bytes=subprocess.check_output(api_command,cwd=ROOT)
        api=json.loads(api_bytes)
        assert api['sha']==synthetic and api['tree']==tree(head)
        assert api['parents']==[admission['base'],head]
        synthetic_bindings.append({'command':api_command,'exit_code':0,'response_sha256':sha(api_bytes),'response':api})
        protection=admission['branch_protection']
        assert protection['enforce_admins']['enabled'] and not protection['allow_force_pushes']['enabled']
        assert protection['required_status_checks']['strict']
        assert protection['required_status_checks']['checks']==[{'context':'verify','app_id':15368}]
        protected.append({'PR':number,'reviewed_head':head,'actual_main':main,'identical_tree':tree(main),
           'tested_synthetic_merge':synthetic,'synthetic_tree_equals_reviewed_head':True,
           'request_method':'ordinary rebase','required_verify_app':15368,'enforced_admins_no_force_push':True,
           'files':[capture_file(CAPTURES/n) for n in [admission_name,f'merge-pr{number}-request.json',f'merge-pr{number}-response.json']]})
    original='daf8ba03a9eb820f99b0f1bf5c4f553a7961e008'
    stable=['Cargo.toml','Cargo.lock','.cargo/config.toml','rust-toolchain.toml',
       'apps/desktop-simulator/Cargo.toml','apps/desktop-simulator/Cargo.lock',
       'apps/desktop-simulator/.cargo/config.toml','apps/desktop-simulator/rust-toolchain.toml',
       'Makefile','ci/ratchet.json','ci/repro_build.sh','protocols/contracts/v1/manifest.json',
       'protocols/contracts/v1/consumers.json','docs/product/client-qualification.md']
    for path in stable:assert body(PRODUCT,path)==body(original,path)
    destinations=['apps/bridge','packages','tools/bridge','docs/bridge','protocols/contracts/v1','apps/pi','tests/integration','plan/work-items.json']
    for path in destinations:assert git('ls-tree',PRODUCT,'--',path)
    source='docs/restart/implementation/A02/'
    for path in [source+'draft-source-notices.md',source+'interoperability-handoff.md']:
        assert body(PRODUCT,path)==body('bb033619b5346302833d717eb501bfa4e3653a1b',path)
    admission=json.loads((CAPTURES/'a02-closure-admission.json').read_bytes())
    assert admission['product_input_main']==PRODUCT and admission['product_input_tree']==tree(PRODUCT)
    assert admission['actual_main_CI']['conclusion']=='success'
    assert 'exact missing full public adoption/repair/source-closure review artifact closure with copy manifest' in admission['writable_scope']
    RESULT['checks']={'actual_CI_chain':runs,'actual_normal_protected_merges':protected,
       'stable_workspace_toolchain_fixture_interop_paths':stable,
       'draft_notice_destinations_present':destinations,'drafts_and_interop_handoff_unchanged':True,
       'bounded_closure_admission':capture_file(CAPTURES/'a02-closure-admission.json'),
       'full_paired_review_artifact_copy_requirement_is_admitted':True,
       'source_criteria_verdict_not_replaced_by_future_metadata_review':True}
    (OUT/'synthetic-merge-bindings.json').write_text(json.dumps(synthetic_bindings,indent=2)+'\n')
    RESULT['outcome']='ACTUAL_DELIVERY_AND_CURRENT_INPUT_BINDINGS_VERIFIED'

try:main()
except Exception as error:
    RESULT['outcome']='PROBE_FAILED';RESULT['failure']={'type':type(error).__name__,'diagnostic':str(error)}
    raise
finally:(OUT/'delivery-result.json').write_text(json.dumps(RESULT,indent=2)+'\n')
