#!/usr/bin/env python3
"""Bind the active artifact to immutable source/postimage and retain scope guards."""
import argparse,ast
from pathlib import Path
from rehearse import canonical,digest
from transforms import Changes


def apply(target,author,output):
    c=Changes(target)
    prior=(target/'tests/integration/check_fixture_snapshots.py').read_text()
    node=next(n for n in ast.parse(prior).body if isinstance(n,ast.AnnAssign) and n.target.id=='DEFAULT_REQUIRED_SNAPSHOT_GLOBS')
    scopes=ast.literal_eval(node.value)
    consumers={'bridge':list(scopes['companion']),'engine':list(dict.fromkeys([*scopes['firmware'],*scopes['hardware']])),'pi':list(scopes['raspberry'])}
    data=canonical(consumers);c.put('protocols/contracts/v1/consumers.json',data)
    text=(author/'tools/migration/templates/scripts/verify_contracts.py').read_text().replace('98a8df4a73a999ca3944bd9756e0be1e0e7bf221','98a8df4a71c0da19908de0e5ec39ea5fb798325a').replace('REPLACE_CONSUMERS_SHA256',digest(data))
    c.put('scripts/verify_contracts.py',text.encode())
    c.put('scripts/test_contracts.py',(author/'tools/migration/templates/scripts/test_contracts.py').read_bytes())
    prior=(target/'tests/integration/test_fixture_snapshots.py').read_text();lines=prior.splitlines(True)
    cls=next(n for n in ast.parse(prior).body if isinstance(n,ast.ClassDef) and n.name=='FixtureSnapshotTests')
    methods=[]
    for node in cls.body:
        if not isinstance(node,ast.FunctionDef) or node.name in ['test_smartcard_requires_identity_route_snapshots','test_matching_snapshot_files_pass','test_mismatched_snapshot_reports_repo_and_path','test_snapshot_without_live_specs_file_fails','test_required_snapshot_glob_reports_missing_live_specs_file']:continue
        method=''.join(lines[node.lineno-1:node.end_lineno])
        method=method.replace('DEFAULT_REQUIRED_SNAPSHOT_GLOBS','REQUIRED_CONTRACT_SCOPES')
        for before,after in [('companion','bridge'),('firmware','engine'),('hardware','engine'),('raspberry','pi')]:
            method=method.replace('REQUIRED_CONTRACT_SCOPES["'+before+'"]','REQUIRED_CONTRACT_SCOPES["'+after+'"]')
        methods.append(method)
    text='''"""Retained per-feature consumer scopes; source/tamper controls live at the artifact owner."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
REQUIRED_CONTRACT_SCOPES=json.loads((ROOT/'protocols/contracts/v1/consumers.json').read_bytes())

class FixtureScopeTests(unittest.TestCase):
'''+ '\n\n'.join(methods)+'\n\nif __name__=="__main__":unittest.main()\n'
    c.put('tests/integration/test_fixture_snapshots.py',text.encode())
    c.put('tests/integration/check_fixture_snapshots.py',b'''#!/usr/bin/env python3
"""Invoke the sole authoritative contract provenance/completeness gate."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_contracts import validate
if __name__=='__main__':
    print(validate())
''')
    path='Makefile';text=(target/path).read_text().replace('\tpython3 scripts/verify_evidence.py\n','\tpython3 scripts/verify_evidence.py\n\tpython3 scripts/verify_contracts.py\n\tpython3 -m unittest discover -s scripts -p \'test_contracts.py\'\n');c.put(path,text.encode())
    return c.apply(output,'Bind single contract artifact to immutable source and declared postimage with complete consumer guards')


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.author_repo,a.output))
