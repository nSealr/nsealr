from pathlib import Path
import subprocess,json,hashlib,os
source=Path.cwd();base='1620ab19d3fbcaf3438a76a5817d266babe30511';candidate='e83c49d97efcbec4fb54c11609c0d2d21e687719';approved='b629e75d18190ded2403ffabe965b595a9bcf6a6'
directory=source/'target/t01-runtime/actual-rebase-final-delivery-03';assert not directory.exists();directory.mkdir(mode=0o700)
rewrite=directory/'rewrite';cold=directory/'cold'
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
init(rewrite)
run(rewrite,'fetch','--no-tags','--no-write-fetch-head',str(source),base+':refs/heads/main')
run(rewrite,'fetch','--no-tags','--no-write-fetch-head',str(source),candidate+':refs/heads/author')
run(rewrite,'checkout','-q','author')
before=run(rewrite,'rev-parse','HEAD:protocols/contracts/v1')
assert before==approved
run(rewrite,'-c','user.name=T01 rebase rehearsal','-c','user.email=t01-rebase@example.invalid','-c','commit.gpgSign=false','rebase','main')
rebased=run(rewrite,'rev-parse','HEAD');assert rebased!=candidate
after=run(rewrite,'rev-parse','HEAD:protocols/contracts/v1');assert after==approved
tree=run(rewrite,'rev-parse','HEAD^{tree}');assert tree==run(source,'rev-parse',candidate+'^{tree}')
init(cold)
run(cold,'fetch','--no-tags','--no-write-fetch-head',str(rewrite),rebased+':refs/heads/main')
run(cold,'checkout','-q','main')
assert run(cold,'for-each-ref','--format=%(refname)')=='refs/heads/main'
assert run(cold,'remote')==''
for name in ['objects/info/alternates','shallow','info/grafts']:
    assert not (cold/'.git'/name).exists(),name
absent=['86569e073da4faec0811d67137bbb0fd4f74c7c6','5cb16c',candidate,'ae34085dd6017eaf2539cf0b570bfb49daace824','21137d6177d1fe62b29f29cf59707bd7988527c3','104f5e369244dcdc3afe87bb91074067c6ad8ac7']
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
verifier=cold/'scripts/verify_contracts.py';original=verifier.read_bytes()
for field,value in [('ARTIFACT_TREE_OID','0'*40),('SOURCE_POSTIMAGE','0'*40),('BASELINE','0'*40),('SOURCE_POSTIMAGE','59653fcc15c4cbc21a39d0a0dd5548abe46165b0')]:
    text=original.decode();lines=text.splitlines();matched=[i for i,line in enumerate(lines) if line.startswith(field+' = ')];assert len(matched)==1
    lines[matched[0]]=field+' = '+repr(value);verifier.write_text('\n'.join(lines)+'\n');check('wrong-or-missing-'+field,1);verifier.write_bytes(original)
artifact=cold/'protocols/contracts/v1';path=artifact/'examples/request-kind-1-basic.json';data=path.read_bytes();path.write_bytes(data+b' ');check('artifact-byte-tamper',1);path.write_bytes(data)
extra=artifact/'.t01-undeclared-hidden';assert not extra.exists();extra.write_text('test-only hidden extra\n');check('hidden-extra',1);extra.unlink()
license=artifact/'LICENSE';mode=license.stat().st_mode;license.chmod(mode^0o100);check('metadata-owner-execution-mode-tamper',1);license.chmod(mode)
restored=json.loads(check('exact-restoration',0));assert restored==valid
assert run(cold,'status','--porcelain')==''
assert run(source,'rev-parse','HEAD')==candidate
print(json.dumps({'state':'LOCAL_ACTUAL_PRODUCT_REBASE_REHEARSAL_NOT_PROTECTED_ADOPTION','source_candidate':candidate,'accepted_main_base':base,'rebased_candidate':rebased,'whole_tree_equal_before_after':tree,'approved_artifact_tree':approved,'all_absent_commits':absent,'all_absent_cat_file_exit':128,'permanent_685_596_ancestors':True,'artifact_reachable_from_cold_main':True,'only_cold_ref':'refs/heads/main','remote_alternate_shallow_graft_present':False,'historical_initial_import_metadata_preserved':manifest['initial_import_commit'],'positive_then_negatives_then_restore':True,'cold_clean':True,'source_branch_unchanged':True},sort_keys=True))
