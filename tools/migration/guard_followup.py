#!/usr/bin/env python3
"""Reject explicit production custody claims without rejecting validated projection."""
import argparse
from pathlib import Path
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=Changes(a.target)
 for name in ['check_product_boundaries.mjs','check_current_guides.mjs','test_product_boundaries.mjs','test_current_guides.mjs']:c.put('tools/bridge/'+name,(a.author_repo/'tools/migration/templates/tools/bridge'/name).read_bytes())
 print(c.apply(a.output,'Keep explicit custody-claim rejection and validated secretless metadata projection distinct'))
