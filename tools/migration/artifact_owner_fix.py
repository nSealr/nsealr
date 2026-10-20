#!/usr/bin/env python3
"""Reconcile exact owner assertions exposed by independent contract execution."""
import argparse
from pathlib import Path
from transforms import Changes


def apply(target,output):
    c=Changes(target)
    path='protocols/contracts/v1/scripts/verify_specs.py';text=(target/path).read_text()
    for old in ['hardware','firmware']:
        text=text.replace('vector.get("repository") != "'+old+'"','vector.get("repository") != "nsealr"').replace('repository must be '+old,'repository must be nsealr')
    c.put(path,text.encode())
    path='protocols/contracts/v1/tests/test_verify_specs.py';text=(target/path).read_text().replace('"repository": {"const": "firmware"}','"repository": {"const": "nsealr"}')
    text=text.replace('len(account_route_semantics), 6','len(account_route_semantics), 5').replace('len(route_selection_semantics), 6','len(route_selection_semantics), 5').replace('len(policy_schema["allOf"]), 3','len(policy_schema["allOf"]), 2')
    c.put(path,text.encode())
    path='apps/pi/tests/test_vault_core.py';text=(target/path).read_text().replace('self.assertEqual(route["repository"], "raspberry")','self.assertEqual(route["repository"], "nsealr")');c.put(path,text.encode())
    return c.apply(output,'Reconcile retained owner assertions with integrated source and card retirement')


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output))
