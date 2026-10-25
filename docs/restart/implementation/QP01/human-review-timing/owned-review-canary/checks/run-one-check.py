"""Run the sole explicitly admitted compile-only argv, preserving its first result."""
import json,subprocess,hashlib,datetime,os,time
from pathlib import Path
W=Path('/home/tux/nsealr/.restart-tools/goal/qp01-owned-review-canary');P=W/'docs/restart/implementation/QP01/human-review-timing/owned-review-canary';R=Path('/home/tux/nsealr/.restart-tools/goal/qp01-owned-review-canary-runtime-01');freeze_path=P/'freeze.json';f=json.loads(freeze_path.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as x:
  for b in iter(lambda:x.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(W),*a]).decode().strip()
assert not git('status','--porcelain')
assert sha(W/f['literal_source']['path'])==f['literal_source']['sha256']
assert sha(Path(f['environment']['source']))==f['environment']['sha256']
assert not Path(f['execution']['new_target_directory']).exists()
with (R/'attempt-01.guard').open('x') as g:g.write('Exactly one compiler invocation permitted; never retry.\n')
C=P/'checks';C.mkdir();command={'schema_version':1,'candidate':git('rev-parse','HEAD'),'tree':git('rev-parse','HEAD^{tree}'),'frozen_receipt_sha256':sha(freeze_path),'prepared_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cwd':str(W),'argv':f['execution']['argv'],'environment':f['environment']['values'],'attempt':1,'command_kind':'compile-only cargo check; existing build scripts only; no example/test/product execution'};(C/'command.json').write_text(json.dumps(command,indent=2)+'\n');t=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (C/'stdout.log').open('wb') as out,(C/'stderr.log').open('wb') as err:
 r=subprocess.run(f['execution']['argv'],cwd=W,env=f['environment']['values'],stdout=out,stderr=err)
end=datetime.datetime.now(datetime.timezone.utc).isoformat();unchanged={p:sha(W/p)==v['sha256'] for p,v in f['unchanged_inputs'].items()};source_same=sha(W/f['literal_source']['path'])==f['literal_source']['sha256'];result={'schema_version':1,'id':'HRT-C01','status':'PASS_COMPILE_ONLY' if r.returncode==0 else 'RED_COMPILE_STOP_NO_RETRY','candidate':command['candidate'],'candidate_tree':command['tree'],'start_utc':start,'end_utc':end,'elapsed_seconds':round(time.monotonic()-t,6),'argv':f['execution']['argv'],'cwd':str(W),'compiler_invocations':1,'exit_code':r.returncode,'command_sha256':sha(C/'command.json'),'stdout':{'path':'checks/stdout.log','bytes':(C/'stdout.log').stat().st_size,'sha256':sha(C/'stdout.log')},'stderr':{'path':'checks/stderr.log','bytes':(C/'stderr.log').stat().st_size,'sha256':sha(C/'stderr.log')},'literal_source_unchanged':source_same,'unchanged_input_hashes':unchanged,'source_changes_after_launch':git('diff','--name-only','HEAD','--','crates','Cargo.lock','Cargo.toml','vendor','.cargo','rust-toolchain.toml'),'executed_example':False,'executed_tests_or_actors':False,'bootstrap_or_network_fetch':False,'limitations':['Typecheck only: no runtime operation, response/signing or asynchronous/gesture/human waiting proof','No v2 transition, API/provider, policy, caller deadline, ABI, ARM/Pi/physical or interoperability qualification','Existing synchronous host fixture5s/100ticks/O8shared4 budgets and every task/release state unchanged'],'failure_policy_observed':'First result preserved; no source correction/retry permitted'};(C/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'candidate':result['candidate'],'status':result['status'],'exit_code':r.returncode,'elapsed_seconds':result['elapsed_seconds'],'stderr_bytes':result['stderr']['bytes'],'all_inputs_unchanged':all(unchanged.values()) and source_same}),flush=True)
