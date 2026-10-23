from pathlib import Path
import subprocess,time,json,hashlib,sys
root=Path(__file__).resolve().parents[5]
here=Path(__file__).resolve().parent
out=here/'standard-node';out.mkdir(exist_ok=False)
env=json.loads((here/'environment.json').read_text())
argv=['node','--import','tsx/esm','docs/restart/implementation/QP01/request-engine/client-exchange.ts']
start=time.time()
with (out/'stdout.log').open('wb') as stdout,(out/'stderr.log').open('wb') as stderr:
 result=subprocess.run(argv,cwd=root,env=env,stdout=stdout,stderr=stderr)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt={'candidate':'8b20b98f1e8962cdce8b2fa4cd3be116e7b2bd9d','tree':'05e9848ebe9633fdb62c018fb565a579b1ee64d6','cwd':str(root),'argv':argv,'start_unix':start,'duration_seconds':time.time()-start,'exit':result.returncode,'environment_sha256':sha(here/'environment.json'),'outputs':{name:sha(out/name) for name in ['stdout.log','stderr.log']}}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt));print((out/'stderr.log').read_text()[-2500:]);sys.exit(result.returncode)
