#!/usr/bin/env python3
"""Retain digits in owned declaration package identities such as nip46."""
import argparse
from pathlib import Path
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=Changes(a.target)
 c.put('tools/bridge/bundle_sdk.mjs',(a.author_repo/'tools/migration/templates/tools/bridge/bundle_sdk.mjs').read_bytes())
 print(c.apply(a.output,'Preserve numeric package identities in SDK declaration relocation'))
