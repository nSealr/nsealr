"""Real-candidate tamper/refusal probes; always restore exact original bytes."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
PRODUCT=HERE/'replay/initial-import/repository'
RESTORED=HERE/'replay/candidate-recovery/restored'
PYTHON='/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/python/bin/python3'

def module(name):
 spec=importlib.util.spec_from_file_location(name,PRODUCT/'scripts'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
contracts=module('verify_contracts');evidence=module('verify_evidence');rows=[]

def exercise(label,path,changed,validate,message):
 old=path.read_bytes()
 try:
  path.write_bytes(changed)
  try:validate()
  except (ValueError,KeyError) as error:
   assert message in str(error),(label,str(error));rows.append({'probe':label,'refused':True,'diagnostic':str(error)})
  else:raise AssertionError('tampered candidate passed: '+label)
 finally:path.write_bytes(old)
 validate()

artifact=PRODUCT/'protocols/contracts/v1'
contracts.validate();evidence.validate(PRODUCT)
path=artifact/'vectors/.review-extra'
try:
 path.write_text('purpose-written hidden addition')
 try:contracts.validate()
 except ValueError as e:assert 'inventory' in str(e);rows.append({'probe':'actual hidden contract addition','refused':True,'diagnostic':str(e)})
 else:raise AssertionError('hidden artifact admitted')
finally:path.unlink()
contracts.validate()
vector=artifact/'vectors/events/kind-1-basic.json';manifest=artifact/'manifest.json';vold=vector.read_bytes();mold=manifest.read_bytes()
try:
 vector.write_bytes(vold+b' ');data=json.loads(mold)
 import hashlib
 next(r for r in data['files'] if r['path']=='vectors/events/kind-1-basic.json')['sha256']=hashlib.sha256(vector.read_bytes()).hexdigest()
 manifest.write_text(json.dumps(data))
 try:contracts.validate()
 except ValueError as e:assert 'immutable reviewed baseline' in str(e);rows.append({'probe':'actual fixture mutation plus forged matching manifest digest','refused':True,'diagnostic':str(e)})
 else:raise AssertionError('self-attributed fixture admitted')
finally:vector.write_bytes(vold);manifest.write_bytes(mold)
contracts.validate()
extra=PRODUCT/'tests/fixtures/specs'
try:
 extra.mkdir(parents=True)
 try:contracts.validate()
 except ValueError as e:assert 'stale duplicate' in str(e);rows.append({'probe':'actual reintroduced stale snapshot root','refused':True,'diagnostic':str(e)})
 else:raise AssertionError('stale snapshot passed')
finally:
 extra.rmdir();extra.parent.rmdir()
contracts.validate()
frozen=json.loads((PRODUCT/'plan/evidence-index.json').read_bytes())
file=PRODUCT/frozen['artifacts'][0]['path']
exercise('actual frozen bytes with unchanged digest',file,file.read_bytes()+b'changed',lambda:evidence.validate(PRODUCT),'frozen evidence bytes changed')
index=PRODUCT/'plan/evidence-index.json'
x=json.loads(index.read_bytes());x['artifacts'].pop();exercise('actual missing historical closure row',index,json.dumps(x).encode(),lambda:evidence.validate(PRODUCT),'closure')
x=json.loads(index.read_bytes());x['artifacts'][0]['blob']='0'*40;exercise('actual forged historical blob',index,json.dumps(x).encode(),lambda:evidence.validate(PRODUCT),'historical blob')
x=json.loads(index.read_bytes());x['artifacts'][0]['original_commit']='0'*40;exercise('actual forged historical origin',index,json.dumps(x).encode(),lambda:evidence.validate(PRODUCT),'alias/source')
current=PRODUCT/'docs/product/contract.md';exercise('actual current contract edit claiming original review',current,current.read_bytes()+b'new requirement',lambda:evidence.validate(PRODUCT),'falsely attributed')
oldgraph=PRODUCT/'docs/restart/work-items.json'
try:
 oldgraph.write_text('{}')
 try:evidence.validate(PRODUCT)
 except ValueError as e:assert 'second live task graph' in str(e);rows.append({'probe':'actual duplicate live task graph','refused':True,'diagnostic':str(e)})
 else:raise AssertionError('duplicate graph passed')
finally:oldgraph.unlink()
evidence.validate(PRODUCT)
locations=[]
for checkout in [PRODUCT,RESTORED]:
 result=subprocess.run([PYTHON,'-B',str(checkout/'scripts/verify_contracts.py')],cwd='/tmp',capture_output=True,text=True);assert result.returncode==0,result.stderr
 locations.append(json.loads(result.stdout))
assert locations[0]==locations[1]
result={'tamper_controls':rows,'all_exact_restores_passed':True,'different_checkout_paths_from_unrelated_cwd':locations,'product_clean':not subprocess.check_output(['git','-C',str(PRODUCT),'status','--porcelain'])}
assert result['product_clean']
(HERE/'negative-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
