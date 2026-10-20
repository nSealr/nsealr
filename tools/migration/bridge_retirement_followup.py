#!/usr/bin/env python3
"""Preserve exact JSON semantics and assert the active route rejection stage."""
import argparse,re
from pathlib import Path
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=Changes(a.target)
 path='apps/bridge/cli/src/index.ts';text=(a.target/path).read_text();text=re.sub(r'JSON.stringify\(actual\) !== JSON.stringify\(([A-Za-z0-9_.]+)\)',r'!isDeepStrictEqual(actual, \1)',text);c.put(path,text.encode())
 path='packages/policy/src/policy.test.ts';text=(a.target/path).read_text().replace('.toThrow(/route type/u);','.toThrow(/signer_route.type/u);');c.put(path,text.encode())
 path='packages/client/src/service.test.ts';text=(a.target/path).read_text().replace('expect(result).toMatchObject({ ok: false, error: { code: "invalid_service_request" } });','expect(result).toMatchObject({ ok: false, error: { code: "route_selection_failed", message: "route selection route_type is unknown" } });');c.put(path,text.encode())
 path='apps/bridge/browser-extension/src/route-config.test.ts';text=(a.target/path).read_text().replace('route_type: "smartcard"\n    })).toThrow(/not browser-dispatchable/u);','route_type: "smartcard"\n    })).toThrow(/route_type is unknown/u);');c.put(path,text.encode())
 print(c.apply(a.output,'Preserve exact JSON value semantics and reject retired routes at their active boundary'))
