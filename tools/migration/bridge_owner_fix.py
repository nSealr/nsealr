#!/usr/bin/env python3
"""Align Bridge owner and solution inventories with the admitted contract artifact."""
import argparse
from pathlib import Path
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=Changes(a.target)
 path='apps/bridge/service/src/drivers.test.ts';c.put(path,(a.target/path).read_text().replace('repository: "firmware"','repository: "nsealr"').encode())
 path='packages/fixtures/src/fixtures.ts';c.put(path,(a.target/path).read_text().replace('  "smartcard",\n','').encode())
 print(c.apply(a.output,'Align Bridge owner assertions and active solution discovery with the single artifact'))
