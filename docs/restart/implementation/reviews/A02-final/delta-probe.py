"""Review only the final current report/index correction above full substantive review."""
import hashlib
import json
from pathlib import Path
import subprocess
OLD='f9a09ba2e9b0212f7dafa53b086c5f1c366d9288'
INTERMEDIATE='c9958ec9cf2a6f04ee210d40de4c8f84bb57ef64'
NEW='bb033619b5346302833d717eb501bfa4e3653a1b'
BASE='docs/restart/implementation/A02/'
REPORT=BASE+'final-report.md';PROGRESS=BASE+'execution/progress.json';PACKAGE=BASE+'final-review-package.json'
HERE=Path(__file__).resolve().parent
sha=lambda data:hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args])
def show(commit,path):return git('show',commit+':'+path)
def read(commit,path):return json.loads(show(commit,path))
assert git('rev-parse','HEAD').decode().strip()==NEW
assert git('diff','--name-only',OLD,NEW).decode().splitlines()==[PROGRESS,REPORT,PACKAGE]
assert show(OLD,REPORT).replace(b'is still pending; do not claim its completion from this draft.',b'is complete and bound by `acceptance-receipt.json`; independent final review\nand coordinator adoption remain pending.')==show(NEW,REPORT)
oldsha=sha(show(OLD,REPORT));newsha=sha(show(NEW,REPORT))
assert show(OLD,PROGRESS).count(oldsha.encode())==1
assert show(OLD,PROGRESS).replace(oldsha.encode(),newsha.encode())==show(NEW,PROGRESS)
assert sha(show(NEW,PACKAGE))=='38b2fb69ef3f1e8a2414d168b005d6f674e2eabebe84d252f2239494cea0917e'
old=read(OLD,PACKAGE);new=read(NEW,PACKAGE)
oldrows={r['path']:r for r in old['files']};newrows={r['path']:r for r in new['files']}
assert len(oldrows)==len(newrows)==982 and set(oldrows)==set(newrows)
assert {p for p in oldrows if oldrows[p]!=newrows[p]}=={REPORT,PROGRESS}
for row in new['files']:
 assert sha(show(NEW,row['path']))==row['sha256']
 assert git('ls-tree',NEW,'--',row['path']).decode().split()[0]==row['mode']
artifacts=read(NEW,PROGRESS)['artifacts'];assert len(artifacts)==755
for row in artifacts:assert sha(show(NEW,row['path']))==row['sha256']
assert new['product_commit']==old['product_commit']=='daf8ba03a9eb820f99b0f1bf5c4f553a7961e008'
assert new['product_tree']==old['product_tree']=='db0687a5ec15228e944360e00e391a4fff863f5d'
for key in ['source_core','selected_hardware','full_suite_source','recovery','patch_count']:
 assert old[key]==new[key]
intermediate=next(r for r in read(INTERMEDIATE,PROGRESS)['artifacts'] if r['path']==REPORT)
assert intermediate['sha256']!=sha(show(INTERMEDIATE,REPORT))
result={'full_substantive_review_author':OLD,'intermediate_corrected_author':INTERMEDIATE,'final_exact_author':NEW,'exact_changed_files':[PROGRESS,REPORT,PACKAGE],'current_package_manifest_sha256':sha(show(NEW,PACKAGE)),'complete_package_members_checked':982,'unchanged_other_payload_members':980,'current_artifact_index_hashes_checked':755,'final_report_sha256':newsha,'final_progress_sha256':sha(show(NEW,PROGRESS)),'product_and_all_execution_source_logs_results_unchanged':True,'findings_F01_F02':'Both corrected; intermediate stale-index observation preserved, no execution evidence rewritten.','full_source_suite_replay_reused_after_bounded_documentation_delta':True}
(HERE/'delta-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
