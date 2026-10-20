from pathlib import Path
import subprocess,json,hashlib,os
source=Path('/home/tux/nsealr/firmware');base='d41a37e25cd0a86d3a47294f8d0ba24913128a21';candidate='0985af3a3e2aab335eaaeac09a3b3f1fd0bd1ebf';approved='b629e75d18190ded2403ffabe965b595a9bcf6a6'
rewrite=source;rebased=candidate;cold=Path('/home/tux/nsealr/.restart-tools/goal/a02-ci-2026-10-20/qh01-delivery/actual-main-cold')
assert not cold.exists()
def run(repo,*args,expect=0):
    command=['git','--no-replace-objects','-C',str(repo),*args]
    result=subprocess.run(command,capture_output=True,text=True)
    print(json.dumps({'argv':command,'exit_code':result.returncode}),flush=True)
    if result.stdout:print(result.stdout,end='',flush=True)
    if result.stderr:print(result.stderr,end='',flush=True)
    assert result.returncode==expect,(command,result.returncode,expect)
    return result.stdout.strip()
def init(repo):
    result=subprocess.run(['git','-c','init.templateDir=','init','-q','--initial-branch=intake',str(repo)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
tree=run(source,'rev-parse','HEAD^{tree}');assert tree=='0100f32f63682312440f32c2ca3b0f9f6aa0f0c3'
init(cold)
run(cold,'fetch','--no-tags','--no-write-fetch-head',str(rewrite),rebased+':refs/heads/main')
run(cold,'checkout','-q','main')
assert run(cold,'for-each-ref','--format=%(refname)')=='refs/heads/main'
assert run(cold,'remote')==''
for name in ['objects/info/alternates','shallow','info/grafts']:
    assert not (cold/'.git'/name).exists(),name
absent=['86569e073da4faec0811d67137bbb0fd4f74c7c6','5cb16c','e83c49d97efcbec4fb54c11609c0d2d21e687719','ae34085dd6017eaf2539cf0b570bfb49daace824','21137d6177d1fe62b29f29cf59707bd7988527c3','104f5e369244dcdc3afe87bb91074067c6ad8ac7']
# Resolve the historical rehearsal spelling against the author's existing object database only.
absent[1]=run(source,'rev-parse',absent[1]+'^{commit}')
for oid in absent:run(cold,'cat-file','-e',oid+'^{commit}',expect=128)
for anchor in ['68508ea1eea1e07b0064fadd65b33433d72701f8','59653fcc15c4cbc21a39d0a0dd5548abe46165b0']:
    run(cold,'merge-base','--is-ancestor',anchor,'main')
assert run(cold,'cat-file','-t',approved)=='tree'
reachable=subprocess.check_output(['git','--no-replace-objects','-C',str(cold),'rev-list','--objects','main'],text=True)
assert approved in {line.split()[0] for line in reachable.splitlines()}
manifest=json.loads((cold/'protocols/contracts/v1/manifest.json').read_text());assert manifest['initial_import_commit']==absent[0] and manifest['artifact_format']==2
def check(name,expected):
    result=subprocess.run(['python3','scripts/verify_contracts.py'],cwd=cold,capture_output=True,text=True)
    print(json.dumps({'control':name,'argv':['python3','scripts/verify_contracts.py'],'cwd':str(cold),'exit_code':result.returncode}),flush=True)
    print(result.stdout,end='',flush=True);print(result.stderr,end='',flush=True)
    assert result.returncode==expected,(name,result.returncode)
    return result.stdout
valid=json.loads(check('cold-rebased-main-valid',0));assert valid['files']==255 and valid['records']==266 and valid['retired']==11 and valid['artifact_tree']==approved and valid['consumers']==['bridge','engine','pi']
assert run(cold,'status','--porcelain')==''
assert run(source,'rev-parse','HEAD')==candidate
print(json.dumps({'state':'ACTUAL_MANUAL_QR_MAIN_ONLY_POSITIVE_SOURCE_CHECK_NOT_FULLCI_OR_DEVICE_QUALIFICATION','actual_main':candidate,'previous_accepted_main':base,'tree':tree,'source_guard_result':valid,'old_objects_absent':absent,'permanent_anchors_actual_ancestors':True,'only_ref':'refs/heads/main','remote_alternate_shallow_graft_present':False,'clean':True,'prior_negative_controls':'Source-identical verify_contracts.py/artifact/provenance source; retain T01 original9control proof939da2, not rerun or relabelled here.'},sort_keys=True))
