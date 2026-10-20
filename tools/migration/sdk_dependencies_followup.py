#!/usr/bin/env python3
"""Declare every external runtime dependency; reject transitive-hoisting reliance."""
import argparse,json,tempfile
from pathlib import Path
from admission import Recorder
from rehearse import canonical
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--environment',type=Path,required=True);a=p.parse_args();a.output.mkdir(mode=0o700);c=Changes(a.target);env=json.loads(a.environment.read_bytes());rec=Recorder(a.output/'lock-generation')
 sdk=json.loads((a.target/'packages/sdk/package.json').read_bytes());sdk['dependencies']['@noble/ciphers']='2.1.1';c.put('packages/sdk/package.json',canonical(sdk))
 c.put('tools/bridge/bundle_sdk.mjs',(a.author_repo/'tools/migration/templates/tools/bridge/bundle_sdk.mjs').read_bytes())
 with tempfile.TemporaryDirectory(dir=a.output,prefix='lock-metadata-') as tmp:
  scratch=Path(tmp);paths=['package.json','pnpm-workspace.yaml','pnpm-lock.yaml']+[p.relative_to(a.target).as_posix() for root in ['packages','apps/bridge'] for p in (a.target/root).glob('*/package.json')]
  for path in paths:
   dest=scratch/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(c.updates[path][0] if path in c.updates else (a.target/path).read_bytes())
  rec.run('declare-sdk-direct-runtime-dependencies',['pnpm','install','--lockfile-only','--ignore-scripts'],scratch,env=env)
  lock=(scratch/'pnpm-lock.yaml').read_bytes();before=(a.target/'pnpm-lock.yaml').read_bytes()
  if lock.split(b'\npackages:\n',1)[1]!=before.split(b'\npackages:\n',1)[1]:raise ValueError('external dependency resolution changed')
  c.put('pnpm-lock.yaml',lock)
 print(c.apply(a.output/'transformation','Declare all SDK external runtime dependencies and reject transitive-hoisting assumptions'))
