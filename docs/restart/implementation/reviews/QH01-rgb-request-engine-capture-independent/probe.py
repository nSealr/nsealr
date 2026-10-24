"""Independent pure retained-log/source-object controls; no product execution."""
import argparse,ast,base64,copy,hashlib,importlib.util,json,re,subprocess
from functools import cache
from pathlib import Path
from unittest.mock import patch
p=argparse.ArgumentParser();p.add_argument('--log',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
HEAD='355bdef1c4c543029e1b15e76b5010fb67f0ee94'
CHECKER='docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py'
raw=a.log.read_bytes();assert hashlib.sha256(raw).hexdigest()=='58172516c4426f184cf02939c9ef09be23f7ba862a42dbdfe13ef4a91d4d487c'
original_check_output=subprocess.check_output
@cache
def git_read(argv,text):
 assert argv[0]=='git' and argv[1:3]==('-C',str(a.repo)) and argv[3] in {'show','ls-tree','rev-parse'},argv
 return original_check_output(list(argv),text=text)
def safe_read(argv,**kwargs):
 assert set(kwargs)<={'text'}
 return git_read(tuple(argv),kwargs.get('text',False))
old=original_check_output(['git','-C',str(a.repo),'show','bacc8d22^:'+CHECKER]);new=(a.repo/CHECKER).read_bytes()
assert hashlib.sha256(old).hexdigest()=='4b66f6242f2fed02eb2da923396d2ecf9b4f697c55edd6068a920003e4eef36f'
assert hashlib.sha256(new).hexdigest()=='e64bf1cc45c13b7b41ca6e1c0640eb3da94d30dbb220422c764d0e6d9c12bc26'
x,y=ast.parse(old),ast.parse(new);helpers=[n for n in y.body if isinstance(n,ast.FunctionDef) and n.name=='verify_qh01_request_engine'];assert len(helpers)==1;y.body.remove(helpers[0]);removed=0
for n in ast.walk(y):
 if isinstance(n,ast.FunctionDef) and n.name=='verify_product':
  for item in list(n.body):
   if isinstance(item,ast.Expr) and isinstance(item.value,ast.Call) and isinstance(item.value.func,ast.Attribute) and item.value.func.attr=='update' and any(isinstance(c,ast.Call) and isinstance(c.func,ast.Name) and c.func.id=='verify_qh01_request_engine' for c in ast.walk(item)):
    n.body.remove(item);removed+=1
assert removed==1 and ast.dump(x,include_attributes=False)==ast.dump(y,include_attributes=False)
spec=importlib.util.spec_from_file_location('independent_qh01_checker',a.repo/CHECKER);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
lines=[re.sub(r'^\d{4}-\d\d-\d\dT\S+Z ?','',line) for line in raw.decode().splitlines()];objects=[];decoder=json.JSONDecoder()
for i,line in enumerate(lines):
 if line.startswith('{'):
  try:value,_=decoder.raw_decode('\n'.join(lines[i:]))
  except json.JSONDecodeError:continue
  if isinstance(value,dict):objects.append(value)
def rows(items,key):return [o[key] for o in items if key in o]
def put(items,key,path,value,index=0):
 obj=rows(items,key)[index]
 for field in path[:-1]:obj=obj[field]
 obj[path[-1]]=value
controls=[]
def negative(name,mutate,head=HEAD):
 changed=copy.deepcopy(objects);mutate(changed)
 try:m.verify_qh01_request_engine(changed,head,str(a.repo))
 except subprocess.CalledProcessError:
  assert head!=HEAD
  controls.append({'name':name,'refused':True,'reason':'source Git object absent at wrong head'})
 except (AssertionError,KeyError,TypeError,ValueError):controls.append({'name':name,'refused':True})
 else:raise AssertionError('false green: '+name)
with patch.object(m.subprocess,'check_output',side_effect=safe_read):
 workers=[o for o in objects if o.get('role')=='public RGB worker build, initialization v2, not hardware qualification'];assert len(workers)==1
 old_composition=m.verify_qh01_composition(objects,lines,workers[0],HEAD,str(a.repo))
 old_lifecycle=m.verify_qh01_lifecycle(objects)
 baseline=m.verify_qh01_request_engine(objects,HEAD,str(a.repo))
 for key,path,value,name in [
  ('qh01_request_engine_build',['v'],True,'build version boolean'),
  ('qh01_request_engine_build',['outputs','native-leaf.js','bytes'],True,'generated artifact bytes boolean'),
  ('qh01_request_engine_case',['actual','C_code'],0.0,'actual C code float'),
  ('qh01_request_engine_case',['actual','parent_pid'],True,'actual parent PID boolean'),
  ('qh01_request_engine_case',['collection','node_wait_raw'],False,'Node wait raw boolean'),
  ('qh01_request_engine_case',['collection','B3','phase','limits','AS'],268435456,'rlimit AS scalar rather than soft hard pair'),
  ('qh01_request_engine_case',['collection','B3','phase','limits','CORE'],[False,0],'rlimit pair boolean'),
  ('qh01_request_engine_case',['collection','B3','phase','limits','CPU'],[1,2,3],'rlimit triple'),
  ('qh01_request_engine_case',['native_settlement','initialization_ns'],'00','native initialization leading zero'),
  ('qh01_request_engine_case',['native_settlement','request_to_close_ns'],'18446744073709551616','native close beyond u64'),
  ('qh01_request_engine_case',['native_settlement','request_to_close_ns'],1,'native timing integer instead of canonical decimal string'),
  ('qh01_request_engine_case',['native_outcome','fds_before','0','dev'],'00','FD identity leading zero'),
  ('qh01_request_engine_case',['native_outcome','timer_clears'],True,'native timer clears boolean'),
  ('qh01_request_engine_case',['node_records',-1,'engine','code'],False,'paired Node engine code boolean'),
  ('qh01_request_engine_case',['source_before','apps/pi/app/nsealr_vault/engine_adapter.py'],'0'*64,'source before adapter mismatch'),
  ('qh01_request_engine_case',['native_preparation_after','source','pnpm-lock.yaml'],'0'*64,'source after preparation lock mismatch'),
  ('qh01_request_engine_case',['collection','B3','terminal','session_policy_verified'],False,'B3 session policy false'),
  ('qh01_request_engine_case',['native_outcome','spawn','pid'],999999,'spawn PID differs from actual C'),
 ]:negative(name,lambda o,k=key,p=path,v=value:put(o,k,p,v))
 def swap_results(o):
  targets=[r for r in o if 'qh01_request_engine_result' in r];targets[0]['qh01_request_engine_result'],targets[1]['qh01_request_engine_result']=targets[1]['qh01_request_engine_result'],targets[0]['qh01_request_engine_result']
 negative('two independent result records swapped',swap_results)
 negative('source HEAD changed to prior accepted main',lambda o:None,'6b0a57aebd7a3b1fa567312417f92e5336db4f18')
assert len(controls)==20
native=next(o for o in objects if o.get('role')=='public fixture build, not hardware qualification')
result={'scope':'Independent bounded checker review; only pure log parsing and allowlisted read-only Git subprocesses','source_head':HEAD,'checker_sha256':hashlib.sha256(new).hexdigest(),'original_log_sha256':hashlib.sha256(raw).hexdigest(),'all_prior_AST_unchanged_after_one_helper_and_one_call_removed':True,'positive':baseline,'retained_old_composition':old_composition,'retained_old_lifecycle':old_lifecycle,'additional_negative_controls':controls,'cached_git_queries':git_read.cache_info()._asdict(),'worker_sha256_dynamic':workers[0]['sha256'],'native_sha256_dynamic':native['sha256'],'new_product_compiler_actor_audit_CI_processes':0}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'positive':True,'additional_negative_controls':len(controls),'all_other_AST_equal':True,'new_product_processes':0}))
