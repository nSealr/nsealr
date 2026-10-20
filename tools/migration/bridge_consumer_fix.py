#!/usr/bin/env python3
"""Repair moved extension sources and order-independent contract object checks."""
import argparse
from pathlib import Path
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=Changes(a.target)
 for path in sorted((a.target/'apps/bridge/browser-extension/src').glob('*.ts')):
  text=path.read_text().replace('apps/browser-extension/','apps/bridge/browser-extension/')
  text=text.replace('new URL("../../..", import.meta.url)','new URL("../../../..", import.meta.url)')
  # These extension fixtures are valid route controls. Wrong-owner negatives in
  # policy/client suites intentionally retain their obsolete owner values.
  text=text.replace('repository: "firmware"','repository: "nsealr"')
  c.put(path.relative_to(a.target).as_posix(),text.encode())
 path='packages/fixtures/src/fixtures.ts';text=(a.target/path).read_text();text='import { isDeepStrictEqual } from "node:util";\n'+text
 text=text.replace('JSON.stringify(fixture.safety) !== JSON.stringify(ROUTE_REFUSAL_SAFETY)','!isDeepStrictEqual(fixture.safety, ROUTE_REFUSAL_SAFETY)');c.put(path,text.encode())
 print(c.apply(a.output,'Repair extension build paths and retain exact semantic safety checks independent of JSON object order'))
