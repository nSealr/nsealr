from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
root=Path('/home/tux/nsealr/.restart-tools/goal/qp01-host-owner-first-gate')
runtime=root.parent/'qp01-host-owner-first-gate-runtime'
name=sys.argv[1];argv=sys.argv[2:]
p=root/'docs/restart/implementation/QP01/host-coordinator/first-gate/correction'/name
p.mkdir(exist_ok=False)
env=json.load(open(runtime/'environment.json')); env['PYTHONPATH']=str(root/'apps/pi/app')
inputs=json.load(open(root/'docs/restart/implementation/QP01/host-coordinator/first-gate/correction/inputs.json'))
for row in inputs['source_bindings']:
 assert hashlib.sha256((root/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
for row in inputs['runtime_binaries'].values():
 assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
start=time.monotonic()
record={'source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True).strip(),'git_status_before':subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True),'argv':argv,'cwd':str(root),'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'environment':env,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'timeout':'NONE: unknown cleanup retains owner/session, no watchdog'}
(p/'command.json').write_text(json.dumps(record,indent=2)+'\n')
with (p/'stdout.log').open('wb') as out,(p/'stderr.log').open('wb') as err:
 child=subprocess.Popen(argv,cwd=root,env=env,stdout=out,stderr=err)
 (runtime/'active.json').write_text(json.dumps({'pid':child.pid,'output':str(p),'command':argv})+'\n')
 code=child.wait()
record.update(exit=code,duration_seconds=time.monotonic()-start,outputs={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['stdout.log','stderr.log']})
(p/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
(runtime/'active.json').unlink()
print(json.dumps({'name':name,'exit':code,'duration':record['duration_seconds']}))
print((p/'stdout.log').read_text()[-5000:]);print((p/'stderr.log').read_text()[-2500:])
sys.exit(code)
