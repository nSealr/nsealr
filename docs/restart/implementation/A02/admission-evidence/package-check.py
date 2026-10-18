from pathlib import Path
import ast,hashlib,json,subprocess
root=Path.cwd(); base=root/'docs/restart/implementation/A02'; rt=root/'tools/migration/.runtime'; digest=lambda b:hashlib.sha256(b).hexdigest()
original=subprocess.check_output(['git','-C','/home/tux/nsealr/lab','show','3303ab17a28ed32419576627d5abb93db3999635:scripts/integration_feature_matrix.py'])
tree=ast.parse(original);assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='LAB_DOCS' for t in n.targets));private_refs=[n.value for n in ast.walk(assignment.value) if isinstance(n,ast.Constant) and isinstance(n.value,str)]; assert len(private_refs)==3
forbidden={x.encode() for p in private_refs for x in [p,Path(p).name]}
private_cases=json.loads((rt/'public-records-04-private-cases.json').read_bytes()); forbidden_cases={r['case_id'].encode() for r in private_cases}; forbidden_case_paths={r['path'].encode() for r in private_cases}
paths=[p for p in base.rglob('*') if p.is_file()]+[p for p in (root/'tools/migration').glob('*') if p.is_file()]
leaks=[(str(p.relative_to(root)),digest(s)) for p in paths for s in forbidden|forbidden_cases|forbidden_case_paths if s in p.read_bytes()]
if leaks:
 (rt/'package-leaks-private.json').write_text(json.dumps(leaks)); raise RuntimeError('excluded private string found; details protected')
for name in ['brief.md','input-notes.json','source-observations.json','preparation-validation.json']:
 assert (base/name).read_bytes()==subprocess.check_output(['git','show','709f09183e7d54937a8562151dd5ac1fbeefc615:docs/restart/implementation/A02/'+name])
for name in ['file-dispositions.json','case-dispositions.json','closed-evidence.json','before-gates.json']:
 assert (base/'admission-evidence'/name).read_bytes()==(rt/'public-records-04'/name).read_bytes()
for p in base.rglob('*.json'):json.loads(p.read_bytes())
assert subprocess.check_output(['git','-C','/home/tux/nsealr/firmware','rev-parse','HEAD']).decode().strip()=='f2ef70f522af4977e15f81554a8c6eadcdbe8097'
assert not subprocess.check_output(['git','-C','/home/tux/nsealr/firmware','status','--porcelain'])
for d in ['plan-01','admission-execution-05','admission-execution-06','admission-execution-07','admission-execution-08','core-python-cases-01']:
 q=base/'admission-evidence'/d
 for r in json.loads((q/'commands.json').read_bytes()):assert digest((q/r['log']).read_bytes())==r['sha256'] and r['exit_code']==0
files=json.loads((base/'admission-evidence/file-dispositions.json').read_bytes())['files']; pubmap={(r['source'],r['path']):r for r in files}; obligations=json.loads((base/'private-case-obligations.json').read_bytes())
for row in obligations['cases']:
 for binding in row.get('existing_source_bindings',[]):
  if 'path' in binding:
   actual=pubmap[(binding['source'],binding['path'])];assert actual['commit']==binding['commit'] and actual['sha256']==binding['sha256']
assert len({r['case_identity_sha256'] for r in private_cases})==25
result=dict(excluded_private_names_and_case_ids_absent=True,scanned_public_files=len(paths),original_four_spec_files_unchanged=True,generated_review_records_copied_exactly=True,all_public_json_parse=True,copied_command_log_hashes_and_success_verified=True,obligation_existing_source_bindings_match_map=True,canonical_frozen_f2_clean=True,import_executed=False)
print(json.dumps(result,indent=2,sort_keys=True))
