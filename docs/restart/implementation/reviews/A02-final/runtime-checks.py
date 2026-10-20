"""Targeted source-behavior review using verified existing pinned tools/caches."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
PRODUCT=HERE/'replay/initial-import/repository'
COLD=Path('/home/tux/nsealr/.restart-tools/goal/a02/tools/migration/.runtime/cold-product-03')
AUTHOR=HERE.parents[3]
env=dict(os.environ,**json.loads((AUTHOR/'docs/restart/implementation/A02/execution/cold-product-03/environment.json').read_bytes()))
env['npm_config_offline']='true'
env['PYTHONDONTWRITEBYTECODE']='1'
commands=[('pinned-runtime-identities',['bash','-c','python3 --version && node --version && npm --version && pnpm --version && rustc --version && cargo --version'],PRODUCT),
 ('frozen-offline-js-install',['pnpm','install','--frozen-lockfile','--offline'],PRODUCT),
 ('build-packed-sdk-inputs',['pnpm','run','build'],PRODUCT),
 ('active-contract-route-and-s01-tests',['pnpm','exec','vitest','run','--maxWorkers=4','apps/bridge/cli/src/index.test.ts','packages/client/src/local-service-client.test.ts','packages/client/src/service.test.ts','packages/policy/src/policy.test.ts','packages/fixtures/src/fixtures.test.ts','packages/nip46/src/session-manager.test.ts','packages/nip46/src/session-security.test.ts'],PRODUCT),
 ('isolated-sdk-tarball-node-browser-types',['node','tools/bridge/pack_smoke.mjs'],PRODUCT),
 ('production-boundaries-and-negatives',['pnpm','run','product-boundaries:check'],PRODUCT),
 ('current-guides-and-negatives',['pnpm','run','current-guides:check'],PRODUCT),
 ('embedded-workspace-metadata',['cargo','metadata','--locked','--offline','--format-version','1','--no-deps'],PRODUCT),
 ('host-workspace-metadata',['cargo','metadata','--locked','--offline','--format-version','1','--no-deps'],PRODUCT/'apps/desktop-simulator')]
rows=[]
(HERE/'runtime-reuse.json').write_text(json.dumps({'source_environment_file':'docs/restart/implementation/A02/execution/cold-product-03/environment.json','mode':'Explicit reuse of pinned tools and existing package caches; no cold-bootstrap claim','explicit_environment':{key:env[key] for key in [*json.loads((AUTHOR/'docs/restart/implementation/A02/execution/cold-product-03/environment.json').read_bytes()),'npm_config_offline']},'npm_network_disabled':True},indent=2)+'\n')
for label,argv,cwd in commands:
 log=HERE/(label+'.log');started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with log.open('wb') as f:r=subprocess.run(argv,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 rows.append({'label':label,'argv':argv,'cwd':str(cwd),'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':r.returncode,'log':log.name,'sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
 (HERE/'runtime-commands.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(label,r.returncode,log.read_text()[-450:] if 'metadata' not in label else 'metadata JSON saved',flush=True)
 if r.returncode:sys.exit(r.returncode)
