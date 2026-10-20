#!/usr/bin/env python3
"""Independent exact-delivery audit and disposable public cold-fetch controls.

Only reviewer evidence is written in this checkout. Tampering occurs in a
temporary, freshly fetched public repository and is restored before removal.
"""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
PROOF='docs/restart/implementation/A02/post-rebase-repair/'
BASE='d931277bebbc5f43514b0e8438d65fb60603fa35'
CANDIDATE='951ed2ad1bb7c7d85a6eaa735a5286022e8fce36'
SOURCE='63ada7b48432119c932a35224978f48057e5a99c'
SCOPE='7618ea42a86a1c25790955090b2dee3350943ff8'
SPEC_REVIEW='771a35ff4dd5176dd9ee50e566320d4ab68c3844'
OLD_SOURCE='86569e073da4faec0811d67137bbb0fd4f74c7c6'
OLD_BASELINE='5cb16cbaffc6b90ca9dfbb1ce7a5388e731d1ae0'
ADOPTED_SOURCE='68508ea1eea1e07b0064fadd65b33433d72701f8'
ADOPTED_BASELINE='59653fcc15c4cbc21a39d0a0dd5548abe46165b0'
FROZEN_SOURCE='f2ef70f522af4977e15f81554a8c6eadcdbe8097'
COMMANDS=[]
RESULT={'candidate':CANDIDATE,'base':BASE,'started_utc':datetime.now(timezone.utc).isoformat(),
        'environment':{'python':platform.python_version(),'platform':platform.platform()},'checks':{}}
ENV={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
ENV.update({'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,
            'GIT_TERMINAL_PROMPT':'0','PYTHONDONTWRITEBYTECODE':'1'})

def sha(data):return hashlib.sha256(data).hexdigest()
def run(args,cwd=ROOT,expected=0,record=False):
    proc=subprocess.run(args,cwd=cwd,env=ENV,capture_output=True)
    if record:
        COMMANDS.append({'command':[str(a) for a in args],
          'cwd':'$COLD' if str(cwd).startswith('/tmp/') else str(cwd),
          'exit_code':proc.returncode,'stdout':proc.stdout.decode(errors='replace'),
          'stderr':proc.stderr.decode(errors='replace')})
    assert proc.returncode==expected,(args,proc.returncode,proc.stderr.decode(errors='replace'))
    return proc.stdout
def git(*args,repo=ROOT,expected=0,record=False):
    return run(['git',*args],cwd=repo,expected=expected,record=record)
def body(commit,path):return git('show',commit+':'+path)
def tree(commit):
    rows={}
    for row in git('ls-tree','-rz','--full-tree',commit).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);rows[path.decode()]=tuple(meta.decode().split())
    return rows
def read(path):return json.loads((ROOT/PROOF/path).read_bytes())
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module
def test_methods(data):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(data))
            if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}

def static():
    before=tree(BASE);after=tree(CANDIDATE)
    git('merge-base','--is-ancestor',CANDIDATE,'HEAD')
    head_tree=tree('HEAD')
    review_prefix=OUT.relative_to(ROOT).as_posix()+'/'
    assert all(p.startswith(review_prefix) for p in set(head_tree)|set(after)
               if head_tree.get(p)!=after.get(p))
    assert git('rev-parse',CANDIDATE+'^{tree}').decode().strip()=='0014d51b24ea0b58650d3dee3a5a8616367e6769'
    changed=sorted(p for p in before if after.get(p)!=before[p])
    added=sorted(set(after)-set(before))
    assert changed==['docs/restart/README.md','docs/restart/implementation/handoff.md','scripts/test_contracts.py','scripts/verify_contracts.py']
    assert all(p.startswith(PROOF) and after[p][:2]==('100644','blob') for p in added)
    assert not set(before)-set(after)
    for name in ['brief.md','source-audit.json']:
        assert body(CANDIDATE,PROOF+name)==body(SCOPE,PROOF+name)
    source_tree=tree(SOURCE)
    tail=[p for p in set(source_tree)|set(after) if source_tree.get(p)!=after.get(p)]
    assert all(p.startswith(PROOF) for p in tail)
    for item in read('result.json')['source_postimages']:
        path=item['path'];assert sha(body(CANDIDATE,path))==item['sha256']
        assert body(CANDIDATE,path)==body(SOURCE,path)
    RESULT['checks']['exact_diff']={'modified_existing':changed,'added_scoped_files':len(added),
       'proof_only_tail_files':len(tail),'no_deletions':True,'all_new_modes':'100644'}
    inventory=[{'path':p,'mode':after[p][0],'blob':after[p][2],
                'bytes':len((ROOT/p).read_bytes()),'sha256':sha((ROOT/p).read_bytes())}
               for p in sorted(changed+added)]
    (OUT/'candidate-inventory.json').write_text(json.dumps({'candidate':CANDIDATE,'files':inventory},indent=2)+'\n')
    oldtest=test_methods(body(BASE,'scripts/test_contracts.py'))
    newtest=test_methods(body(CANDIDATE,'scripts/test_contracts.py'))
    assert len(oldtest)==20 and len(newtest)==24
    assert all(newtest[name]==v for name,v in oldtest.items())
    RESULT['checks']['test_bodies']={'original_unchanged':20,'total':24,'added':sorted(set(newtest)-set(oldtest))}
    for path in ['plan/work-items.json','plan/evidence-index.json']:
        assert before[path]==after[path]
    plan=json.loads(body(CANDIDATE,'plan/work-items.json'))
    index=json.loads(body(CANDIDATE,'plan/evidence-index.json'))
    assert len(plan['tasks'])==47 and len(plan['resources'])==16 and len(plan['release_paths'])==5
    closed=[t for t in plan['tasks'] if t.get('status') in {'verified','integrated'}]
    assert len(closed)==7 and next(t for t in plan['tasks'] if t['id']=='A02')['status'] not in {'verified','integrated'}
    frozen=index['artifacts'];assert len(frozen)==1508
    for row in frozen:
        assert before[row['path']]==after[row['path']]
        assert sha((ROOT/row['path']).read_bytes())==row['sha256']
    contract=lambda t:{p:v for p,v in t.items() if p.startswith('protocols/contracts/v1/')}
    assert contract(before)==contract(after)
    RESULT['checks']['unchanged_invariants']={'whole_plan_sha256':sha(body(CANDIDATE,'plan/work-items.json')),
       'tasks':47,'resources':16,'release_paths':5,'closed_tasks':[t['id'] for t in closed],
       'frozen_files_bytes_and_git_modes':len(frozen),'whole_v1_contract_entries':len(contract(after)),
       'whole_evidence_index_unchanged':True,'A02_unclosed':True}
    mappings=[]
    for old,new in [(OLD_SOURCE,ADOPTED_SOURCE),(OLD_BASELINE,ADOPTED_BASELINE)]:
        oldtree=git('rev-parse',old+'^{tree}');newtree=git('rev-parse',new+'^{tree}')
        assert oldtree==newtree
        git('merge-base','--is-ancestor',new,BASE)
        mappings.append({'historical':old,'adopted':new,'identical_whole_tree':newtree.decode().strip(),'already_main_ancestor':True})
    RESULT['checks']['anchor_tree_equalities']=mappings
    admission=ROOT/PROOF/'scope-admission.json'
    assert sha(admission.read_bytes())=='974c1517c86dc308af0fa05f0f936f42a4c3fe32785eea415987109e9d6c71d9'
    for row in read('spec-review-copy.json')['files']:
        data=body(row['source_commit'],row['source_path'])
        assert row['source_commit']==SPEC_REVIEW and sha(data)==row['sha256']
        assert data==(ROOT/row['path']).read_bytes()
        assert after[row['path']]==(row['mode'],'blob',row['blob'])
    copies=read('local-proof-copy.json')['copies']
    author=Path('/home/tux/nsealr/.restart-tools/goal/a02-contract-repair')
    for row in copies:
        dest=ROOT/PROOF/row['copied_path'];data=dest.read_bytes()
        assert len(data)==row['bytes'] and sha(data)==row['sha256']
        assert data==(author/row['source_path']).read_bytes()
        assert after[PROOF+row['copied_path']][0]==row['mode']
    failed=read('failed-main-CI/copy-inventory.json')
    for row in failed['files']:
        data=(ROOT/PROOF/'failed-main-CI'/row['copied_path']).read_bytes()
        assert len(data)==row['bytes'] and sha(data)==row['sha256']
        assert data==Path(row['source_path']).read_bytes()
    with ZipFile(ROOT/PROOF/'failed-main-CI/logs.zip') as archive:
        assert set(archive.namelist())=={r['path'] for r in failed['zip_members']}
        for row in failed['zip_members']:
            data=archive.read(row['path']);assert len(data)==row['bytes'] and sha(data)==row['sha256']
    command_files=list((ROOT/PROOF).rglob('commands.json'));records=0
    for path in command_files:
        for row in json.loads(path.read_bytes()):
            records+=1
            if 'log' in row:
                assert sha((path.parent/row['log']).read_bytes())==row['sha256']
            if 'environment_sha256' in row:
                assert sha((path.parent/'environment.json').read_bytes())==row['environment_sha256']
    red=read('cold-main-red/summary.json');green=read('cold-candidate-green/summary.json')
    assert red['source_main']==BASE and red['checker_exit']==1 and red['underlying_git_show_exit']==128
    red_commands=read('cold-main-red/commands.json')
    green_commands=read('cold-candidate-green/commands.json')
    assert any(BASE+':refs/heads/cold-main' in r['command'] for r in red_commands)
    assert any(SOURCE+':refs/heads/candidate' in r['command'] for r in green_commands)
    assert green['commands_sha256']==sha((ROOT/PROOF/'cold-candidate-green/commands.json').read_bytes())
    assert green['checker_sha256']==sha(body(CANDIDATE,'scripts/verify_contracts.py'))
    assert green['probe_sha256']==sha((ROOT/PROOF/'cold-candidate-probe.py').read_bytes())
    assert all(r['exit_code']==0 for r in read('integration-checks/commands.json'))
    integration=(ROOT/PROOF/'integration-checks/01-all-17-retained-product-integration.log').read_text()
    steps=[int(n) for n in re.findall(r'^\[(\d+)/17 original \d+\]',integration,re.M)]
    assert steps==list(range(1,18))
    assert integration.endswith('All 17 retained product integration steps passed. External hardware and optional physical resources are separate.\n')
    RESULT['checks']['author_evidence_bindings']={'spec_review_files':4,'admission_sha256':sha(admission.read_bytes()),
      'selected_local_proof_copies':len(copies),'failed_public_CI_files':4,'decompressed_zip_members':len(failed['zip_members']),
      'command_record_files':len(command_files),'bound_command_records':records,'integration_steps':steps,
      'cold_RED_checked':True,'cold_GREEN_source':SOURCE,'cold_GREEN_observation':green}
    executable=read('runtime-dependency-audit/source-inventory.json')
    assert len(executable)==364 and len({row['path'] for row in executable})==364
    for row in executable:assert sha((ROOT/row['path']).read_bytes())==row['sha256']
    RESULT['checks']['runtime_audit_inventory']={'actual_current_file_hashes_verified':len(executable)}
    with ZipFile(ROOT/PROOF/'failed-main-CI/logs.zip') as archive:
        failed_acceptance=archive.read('verify/5_Complete product acceptance.txt').decode()
    make_errors=re.findall(r'make: \*\*\* \[([^\]]+)\] Error (\d+)',failed_acceptance)
    assert make_errors==[('Makefile:17: test','1'),('Makefile:93: integration','1')]
    assert 'show\', \'5cb16cbaffc6b90ca9dfbb1ce7a5388e731d1ae0:protocols/contracts/v1/manifest.json' in failed_acceptance
    assert 'exit status 128' in failed_acceptance
    assert '[1/17 original 1]' in failed_acceptance and '[2/17 original 2]' not in failed_acceptance
    RESULT['checks']['failed_main_log_diagnosis']={'run':39408038674,'actual_make_failures':make_errors,
       'same_baseline_lookup_exit_128_in_root_test_and_integration_step1':True,
       'remaining_integration_steps_unexecuted_in_failed_hosted_run':16,
       'now_author_integration_17_bound_to_exact_log':True}
    # Bounded token/private-key scan plus human inspection; not a general security audit.
    patterns={'credential_token':rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|xox[baprs]-[A-Za-z0-9-]{20,})',
              'private_key_block':rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
              'private_agent_session':rb'/(?:\.codex|\.ssh)/(?:sessions|id_rsa|id_ed25519)',
              'unmasked_bearer':rb'(?i)authorization:\s*bearer\s+[A-Za-z0-9._-]{20,}'}
    inputs=[(p,(ROOT/p).read_bytes()) for p in changed+added if not p.endswith('.zip')]
    with ZipFile(ROOT/PROOF/'failed-main-CI/logs.zip') as archive:
        inputs.extend(('failed-main-CI/logs.zip!'+name,archive.read(name)) for name in archive.namelist())
    privacy=[{'path':p,'category':name} for p,data in inputs for name,regex in patterns.items() if re.search(regex,data)]
    assert not privacy,privacy
    assert not any(any(part in {'.git','.runtime','node_modules','__pycache__','vendor'} for part in Path(p).parts) for p in added)
    RESULT['checks']['bounded_public_proof_scan']={'candidate_text_and_decompressed_members':len(inputs),
      'categories':sorted(patterns),'findings':privacy,'no_runtime_objects_caches_or_private_sessions':True,
      'limits':'Public CI ZIP deliberately retained; selected command logs and source inventories are not private Git history. Bounded scan is supplemented by source/diff inspection.'}
    linkcount=0
    for path in [ROOT/'docs/restart/README.md',ROOT/'docs/restart/implementation/handoff.md',ROOT/PROOF/'README.md']:
        for raw in re.findall(r'\[[^\]\n]*\]\(([^\s)]+)\)',path.read_text()):
            url=urlsplit(raw)
            if url.scheme or url.netloc or not url.path:continue
            target=(path.parent/unquote(url.path)).resolve()
            assert target.is_relative_to(ROOT) and target.exists(),(path,raw)
            linkcount+=1
    nonlogs=[p for p in changed+added if not p.endswith('.log')]
    whitespace=subprocess.run(['git','diff','--check',BASE,CANDIDATE],cwd=ROOT,capture_output=True)
    (OUT/'candidate-whitespace.log').write_bytes(whitespace.stdout+whitespace.stderr)
    run(['git','diff','--check',BASE,CANDIDATE,'--',*nonlogs])
    warnings={}
    for path in re.findall(rb'^(.*?):\d+: trailing whitespace\.$',whitespace.stdout,re.M):
        key=path.decode();warnings[key]=warnings.get(key,0)+1
    RESULT['checks']['navigation_and_whitespace']={'local_links_resolve':linkcount,
      'all_raw_diff_exit':whitespace.returncode,'all_raw_diff_log_sha256':sha(whitespace.stdout+whitespace.stderr),
      'warning_lines':sum(warnings.values()),'raw_log_files':warnings,
      'all_nonlog_source_diff_exit':0,'author_earlier_two_log_snapshot_preserved':True}

def cold():
    with tempfile.TemporaryDirectory(prefix='a02-independent-cold-') as directory:
        repo=Path(directory)/'repository'
        run(['git','-c','init.templateDir=','init','-q','--initial-branch=intake',str(repo)],cwd=Path(directory),record=True)
        git('fetch','--no-tags','--no-write-fetch-head','https://github.com/nSealr/nsealr.git',CANDIDATE+':refs/heads/candidate',repo=repo,record=True)
        git('checkout','-q','candidate',repo=repo,record=True)
        assert git('rev-parse','HEAD',repo=repo).decode().strip()==CANDIDATE
        assert git('rev-parse','HEAD^{tree}',repo=repo).decode().strip()=='0014d51b24ea0b58650d3dee3a5a8616367e6769'
        assert git('for-each-ref','--format=%(refname)',repo=repo)==b'refs/heads/candidate\n'
        assert not git('remote',repo=repo)
        for path in ['objects/info/alternates','objects/info/http-alternates','shallow','info/grafts']:
            assert not (repo/'.git'/path).exists()
        assert not any(p.is_symlink() or (p.is_file() and p.stat().st_nlink!=1) for p in (repo/'.git/objects').rglob('*'))
        for old in [OLD_SOURCE,OLD_BASELINE]:git('cat-file','-e',old+'^{commit}',repo=repo,expected=128,record=True)
        for new in [ADOPTED_SOURCE,ADOPTED_BASELINE,FROZEN_SOURCE]:
            git('cat-file','-e',new+'^{commit}',repo=repo,record=True)
            git('merge-base','--is-ancestor',new,CANDIDATE,repo=repo,record=True)
        objects=set(git('cat-file','--batch-all-objects','--batch-check=%(objectname)',repo=repo).splitlines())
        reachable={r.split(b' ',1)[0] for r in git('rev-list','--objects',CANDIDATE,repo=repo).splitlines()}
        assert objects==reachable
        git('fsck','--full','--strict','--no-reflogs',repo=repo,record=True)
        git('status','--porcelain',repo=repo,record=True)
        run([sys.executable,'-B','scripts/verify_contracts.py'],cwd=repo,record=True)
        run([sys.executable,'-B','scripts/verify_evidence.py'],cwd=repo,record=True)
        module=load(repo/'scripts/verify_contracts.py','cold_verifier')
        artifact=repo/'protocols/contracts/v1';manifest=artifact/'manifest.json';original=manifest.read_bytes()
        metadata=json.loads(original)
        assert metadata['initial_import_commit']==OLD_SOURCE
        assert original==(ROOT/'protocols/contracts/v1/manifest.json').read_bytes()
        controls=[]
        def rejects(label,expected):
            try:module.validate(artifact,repo)
            except (ValueError,subprocess.CalledProcessError) as error:
                assert isinstance(error,expected),(label,type(error))
                controls.append({'control':label,'outcome':'rejected','exception':type(error).__name__,
                                 'diagnostic':str(error) if isinstance(error,ValueError) else 'Git lookup failed; exit '+str(error.returncode)})
            else:raise AssertionError('tamper accepted: '+label)
        try:
            metadata['initial_import_commit']=ADOPTED_SOURCE
            manifest.write_text(json.dumps(metadata))
            rejects('adopted ID cannot replace literal historical identity',ValueError)
            manifest.write_bytes(original)
            metadata=json.loads(original);metadata['files'][0]['sha256']='0'*64
            manifest.write_text(json.dumps(metadata))
            rejects('forged current manifest cannot replace immutable reviewed baseline',ValueError)
            manifest.write_bytes(original)
            for name in ['SOURCE_POSTIMAGE','BASELINE']:
                value=getattr(module,name);setattr(module,name,'0'*40)
                try:rejects('missing '+name,subprocess.CalledProcessError)
                finally:setattr(module,name,value)
            value=module.SOURCE_POSTIMAGE;module.SOURCE_POSTIMAGE=FROZEN_SOURCE
            try:rejects('present wrong source tree',ValueError)
            finally:module.SOURCE_POSTIMAGE=value
            value=module.BASELINE;module.BASELINE=ADOPTED_SOURCE
            try:rejects('present wrong postimage without reviewed manifest',subprocess.CalledProcessError)
            finally:module.BASELINE=value
        finally:manifest.write_bytes(original)
        assert module.validate(artifact,repo)['files']==len(metadata['files'])
        assert not git('status','--porcelain',repo=repo,record=True)
        RESULT['checks']['independent_final_public_cold_fetch']={'source':CANDIDATE,
          'tree':'0014d51b24ea0b58650d3dee3a5a8616367e6769','only_ref':'refs/heads/candidate',
          'all_objects_reachable':len(objects),'old_objects_absent':[OLD_SOURCE,OLD_BASELINE],
          'permanent_ancestors':[ADOPTED_SOURCE,ADOPTED_BASELINE,FROZEN_SOURCE],
          'no_remotes_alternates_shallow_grafts_hardlinks':True,'strict_fsck':True,
          'actual_contract_and_1508_evidence_checkers':'PASS','manifest_sha256':sha(original),
          'negative_controls':controls,'restored_clean':True}

try:
    static();cold();RESULT['outcome']='PASS'
except Exception as error:
    RESULT['outcome']='FAIL';RESULT['failure']={'type':type(error).__name__,'diagnostic':str(error)}
    raise
finally:
    RESULT['ended_utc']=datetime.now(timezone.utc).isoformat()
    (OUT/'probe-result.json').write_text(json.dumps(RESULT,indent=2)+'\n')
    (OUT/'cold-commands.json').write_text(json.dumps(COMMANDS,indent=2)+'\n')
