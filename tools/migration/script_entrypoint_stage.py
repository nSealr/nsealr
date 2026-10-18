#!/usr/bin/env python3
"""Use explicit package script invocation where pnpm reserves the command name."""
import argparse
from pathlib import Path
from transforms import Changes

def apply(target,output):
 c=Changes(target)
 for path in ['Makefile','scripts/check_product_gates.py','docs/bridge/testing.md']:
  old=(target/path).read_text();new=old.replace('pnpm ci','pnpm run ci')
  if old==new:raise ValueError('expected CI entrypoint absent: '+path)
  c.put(path,new.encode())
 return c.apply(output,'Invoke the complete Bridge package CI script explicitly through pnpm run')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output))
