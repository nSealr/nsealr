"""Check names, actual outcomes and source hashes without asserting semantic equality."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--author',type=Path,required=True);p.add_argument('--product',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
base=a.author/'docs/restart/implementation/A02'
read=lambda p:json.loads(p.read_bytes())
sha=lambda b:hashlib.sha256(b).hexdigest()
ts=read(base/'execution/bridge-named-execution-02/case-correspondence.json');raw=read(base/'execution/bridge-named-execution-02/cases.json')
executed={};skipped=[]
for suite in raw['testResults']:
 for case in suite['assertionResults']:
  name=' > '.join([*case['ancestorTitles'],case['title']])
  if case['status']=='passed':
   matches=[r['target_file'] for r in ts['case_correspondence'] if r['target_file'] and suite['name'].endswith('/'+r['target_file'])];assert matches
   key=(matches[0],name);assert key not in executed;executed[key]=case
  else:skipped.append(case)
assert len(executed)==691 and len(skipped)==1 and len(ts['case_correspondence'])==716
mapped=set();retired=0;bindings=0
for row in ts['case_correspondence']:
 if row['after_status']=='deliberately-retired':assert row['treatment']=='retire-smartcard';retired+=1;continue
 assert row['after_status']=='passed';key=(row['target_file'],row['after_case']);assert key in executed and key not in mapped;mapped.add(key)
 assert sha((a.product/row['target_file']).read_bytes())==row['after_file_sha256'];bindings+=1
assert mapped==set(executed) and retired==25
other=read(base/'execution/case-reconciliation-execution-01/case-correspondence.json');log=(base/'execution/cold-product-03/evidence/suites/00-product-ci.log').read_text()
rust=[r for r in other['cases'] if r['disposition'].startswith('retained Rust')];assert len(rust)==263
for row in rust:assert row['after']['status']=='passed' and row['before']['case_id']==row['after']['case_id'] and row['after']['case_id'] in log
for row in other['cases']:
 after=row.get('after')
 if isinstance(after,dict) and after.get('path') and after.get('sha256'):
  owner={'pi':'apps/pi','contracts':'protocols/contracts/v1'}.get(after['execution_group'],'');target=Path(owner)/after['path']
  assert sha((a.product/target).read_bytes())==after['sha256'];bindings+=1
for row in other['private_opaque_obligations']:
 after=row.get('after')
 if after and after['status']=='passed':
  assert row['before']['case_identity_sha256'] in log
  path=after.get('source_file',after.get('path'));digest=after.get('source_sha256',after.get('sha256'));assert sha((a.product/path).read_bytes())==digest;bindings+=1
 else:assert row['before']['treatment']=='retire-obsolete-private-taxonomy'
expected={'pi':150,'contracts':90,'helpers':115,'root-controls':67,'bootstrap':8};named={}
for group,count in expected.items():
 data=read(base/f'execution/named-python-execution-01/{group}.json');assert data['successful'] and data['tests_run']==len(data['rows'])==count
 assert len({r['case_id'] for r in data['rows']})==count
 assert all(r['status']=='passed' for r in data['rows']);named[group]=count
result={'typescript':dict(ts['counts'],treatment_counts=dict(Counter(r['treatment'] for r in ts['case_correspondence']))),'rust_original_named_cases_in_complete_log':263,'python_named_execution':named,'private_replacements':21,'private_retirements':4,'current_case_file_hash_bindings':bindings,'disposition_counts':dict(Counter(r['disposition'] for r in other['cases'])),'semantic_limit':'These checks establish complete correspondence/outcomes/source identity. The distinct reviewer also inspected actual assertion/fixture transformations; names or totals alone do not establish assertion equivalence.'}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
