#!/usr/bin/env python3
"""Actual repaired-main-only source check, separate from pending closure gates."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile

OUT=Path(__file__).resolve().parent
CANDIDATE='b1c90139a651895284b2624da7d12903cf16bc9d'
TREE='0014d51b24ea0b58650d3dee3a5a8616367e6769'
OLD=['86569e073da4faec0811d67137bbb0fd4f74c7c6','5cb16cbaffc6b90ca9dfbb1ce7a5388e731d1ae0']
ANCHORS=['68508ea1eea1e07b0064fadd65b33433d72701f8','59653fcc15c4cbc21a39d0a0dd5548abe46165b0','f2ef70f522af4977e15f81554a8c6eadcdbe8097']
ENV={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
ENV.update({'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,'GIT_TERMINAL_PROMPT':'0','PYTHONDONTWRITEBYTECODE':'1'})
COMMANDS=[]
RESULT={'product_candidate':CANDIDATE,'tree':TREE,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope':'Read-only exact repaired-main Git reachability, immutable contract and frozen evidence validation; no task/source-closure or final metadata verdict',
        'python':platform.python_version(),'corrected_main_CI_capture':'Pending independent completed actual capture; not inferred here'}

def run(args,cwd,expected=0):
    p=subprocess.run(args,cwd=cwd,env=ENV,capture_output=True)
    COMMANDS.append({'command':[str(x) for x in args],'cwd':'$TEMPORARY_REPOSITORY' if (Path(cwd)/'.git').is_dir() else '$TEMPORARY_PARENT',
      'exit_code':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')})
    assert p.returncode==expected,(args,p.returncode)
    return p.stdout

try:
    with tempfile.TemporaryDirectory(prefix='a02-source-closure-cold-') as directory:
        root=Path(directory);repo=root/'product'
        run(['git','-c','init.templateDir=','init','-q','--initial-branch=intake',str(repo)],root)
        def git(*args,expected=0):return run(['git',*args],repo,expected)
        git('fetch','--no-tags','--no-write-fetch-head','https://github.com/nSealr/nsealr.git',CANDIDATE+':refs/heads/candidate')
        git('checkout','-q','candidate')
        assert git('rev-parse','HEAD').decode().strip()==CANDIDATE
        assert git('rev-parse','HEAD^{tree}').decode().strip()==TREE
        assert git('for-each-ref','--format=%(refname)')==b'refs/heads/candidate\n'
        assert not git('remote') and not git('status','--porcelain')
        for path in ['objects/info/alternates','objects/info/http-alternates','shallow','info/grafts']:
            assert not (repo/'.git'/path).exists()
        assert not any(p.is_symlink() or (p.is_file() and p.stat().st_nlink!=1) for p in (repo/'.git/objects').rglob('*'))
        for old in OLD:git('cat-file','-e',old+'^{commit}',expected=128)
        for anchor in ANCHORS:
            git('cat-file','-e',anchor+'^{commit}')
            git('merge-base','--is-ancestor',anchor,CANDIDATE)
        objects=set(git('cat-file','--batch-all-objects','--batch-check=%(objectname)').splitlines())
        reachable={row.split(b' ',1)[0] for row in git('rev-list','--objects',CANDIDATE).splitlines()}
        assert objects==reachable
        git('fsck','--full','--strict','--no-reflogs')
        contracts=json.loads(run([sys.executable,'-B','scripts/verify_contracts.py'],repo))
        evidence=json.loads(run([sys.executable,'-B','scripts/verify_evidence.py'],repo))
        assert contracts['files']==251 and evidence['closed_files']==1508
        manifest=(repo/'protocols/contracts/v1/manifest.json').read_bytes()
        assert json.loads(manifest)['initial_import_commit']==OLD[0]
        assert hashlib.sha256(manifest).hexdigest()=='16bf215c6f65a5c616c30971cb860351272633ff6a8c75edc8246eab61f8bbeb'
        assert not git('status','--porcelain')
        RESULT.update({'source_checks':'PASS','all_fetched_objects_reachable':len(objects),'only_ref':'refs/heads/candidate',
          'old_objects_absent':OLD,'permanent_ancestors':ANCHORS,'no_extra_refs_remotes_alternates_grafts_shallow_hardlinks':True,
          'strict_fsck':'PASS','contract_checker':contracts,'frozen_evidence_checker':evidence,
          'literal_historical_manifest_preserved':True,'source_clean_after':True})
except Exception as error:
    RESULT['source_checks']='FAIL';RESULT['failure']={'type':type(error).__name__,'diagnostic':str(error)}
    raise
finally:
    RESULT['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (OUT/'cold-main-result.json').write_text(json.dumps(RESULT,indent=2)+'\n')
    (OUT/'cold-main-commands.json').write_text(json.dumps(COMMANDS,indent=2)+'\n')
