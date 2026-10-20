#!/usr/bin/env python3
"""Apply the three admitted S01 patches to exact selected source before adaptation."""
import argparse
from pathlib import Path
import subprocess
from admission import Recorder
from assemble import git_environment,read_git
from rehearse import canonical,decode_json,digest,write_private
from transforms import Changes


def apply(target:Path,output:Path):
    recorder=Recorder(output);scratch=output/'selected-source';scratch.mkdir()
    mapping={'scripts/check_fixture_snapshots.py':'tests/integration/check_fixture_snapshots.py',
             'tests/test_fixture_snapshots.py':'tests/integration/test_fixture_snapshots.py',
             'scripts/integration_companion_nip46_cli.py':'tests/integration/integration_companion_nip46_cli.py',
             'tests/test_integration_companion_nip46_cli.py':'tests/integration/test_integration_companion_nip46_cli.py'}
    for old,new in mapping.items():
        p=scratch/old;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((target/new).read_bytes())
    recorder.run('isolated-overlay-worktree',['git','-c','init.templateDir=','init',str(scratch)],output,env=git_environment())
    patches=['tools/baseline/overlays/lab-provenance.patch','docs/restart/implementation/S01/lab-metadata-v1.patch','tools/baseline/overlays/lab-provenance-followup.patch']
    for i,path in enumerate(patches):
        recorder.run(str(i)+'-check',['git','-C',str(scratch),'apply','--check',str(target/path)],output,env=git_environment())
        recorder.run(str(i)+'-apply',['git','-C',str(scratch),'apply',str(target/path)],output,env=git_environment())
    expected={'scripts/check_fixture_snapshots.py':'cb8286e0b91410400dd6f039a4c6dbfce961c8a2b9160250927ef7d0b5d953df',
              'tests/test_fixture_snapshots.py':'db8186c61ad27267e93bc0e2d69be9cad36a2029850f921bad5c544e3c827e7b',
              'scripts/integration_companion_nip46_cli.py':'0f304dc3cb8513e11eab4e58922ceebe4329455edb40d080278aff3e44218fb0',
              'tests/test_integration_companion_nip46_cli.py':'39f9baa22f7ce205bd20646f2e608c6e1a57782a63287408e4d876a5ccae25e5'}
    change=Changes(target)
    for old,new in mapping.items():
        data=(scratch/old).read_bytes()
        if digest(data)!=expected[old]:raise ValueError('corrected S01 patch postimage mismatch')
        change.put(new,data)
    return change.apply(output/'declared-transform','Apply exact reviewed S01 provenance and metadata corrections')


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output))
