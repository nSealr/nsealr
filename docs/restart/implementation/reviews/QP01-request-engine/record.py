from pathlib import Path
import json,subprocess,time,sys,hashlib
root=Path('/home/tux/nsealr/.restart-tools/goal/qh01-linux-worker-experiment')
review=root/'docs/restart/implementation/reviews/QP01-request-engine'
env=json.loads((review/'environment.json').read_text())
name=sys.argv[1]; argv=sys.argv[2:]; out=review/'commands'/name;out.mkdir(parents=True,exist_ok=False)
start=time.time()
with (out/'stdout.log').open('wb') as stdout,(out/'stderr.log').open('wb') as stderr:
 result=subprocess.run(argv,cwd=root,env=env,stdout=stdout,stderr=stderr)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d={'candidate':'e44f957bc20c79d443f6e29ac0ba8c611f4787bd','review_checkout_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'argv':argv,'cwd':str(root),'start_unix':start,'duration_seconds':time.time()-start,'exit':result.returncode,'environment_sha256':sha(review/'environment.json'),'outputs':{n:sha(out/n) for n in ['stdout.log','stderr.log']}}
(out/'receipt.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({'name':name,'exit':result.returncode,'seconds':d['duration_seconds']}))
print((out/'stderr.log').read_text()[-1600:])
sys.exit(result.returncode)
