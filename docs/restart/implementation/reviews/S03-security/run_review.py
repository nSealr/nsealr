#!/usr/bin/env python3
"""Reproduce isolated security checks without changing product source or author evidence."""
import datetime, hashlib, json, os, pathlib, platform, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[5]
OWN=pathlib.Path(__file__).resolve().parent
EVIDENCE=OWN/'evidence'
CANDIDATE='2d7d465a291c4d4a1324d90595fc45a2fdbefca5'
commands=json.loads((EVIDENCE/'commands.json').read_text()) if (EVIDENCE/'commands.json').exists() else []
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(name,argv,extra=None):
    env=os.environ.copy();env['CARGO_TARGET_DIR']=str(OWN/'build')
    env.update(extra or {})
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=subprocess.run(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=EVIDENCE/(name+'.log');log.write_bytes(p.stdout)
    commands.append(dict(name=name,argv=argv,cwd=str(ROOT),candidate=CANDIDATE,started_utc=started,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=p.returncode,log=str(log.relative_to(ROOT)),log_sha256=sha(log),env_override={'CARGO_TARGET_DIR':env['CARGO_TARGET_DIR'],**(extra or {})}))
    (EVIDENCE/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    print(name,p.returncode,flush=True)
    if p.returncode: print(p.stdout.decode(errors='replace')[-5000:]);sys.exit(p.returncode)
    return p.stdout

def audit():
    manifest=json.loads((ROOT/'docs/restart/implementation/S03/evidence/artifact-manifest.json').read_text())
    checked=[]
    for a in manifest['artifacts']:
        p=ROOT/a['path'];assert sha(p)==a['sha256'] and p.stat().st_size==a['bytes'], a['path'];checked.append(a['path'])
    result=json.loads((ROOT/'docs/restart/implementation/S03/acceptance-result.json').read_text())
    lock=__import__('tomllib').loads((ROOT/'Cargo.lock').read_text())
    count=0; packages=[]
    for p in lock['package']:
        if not p.get('source','').startswith('registry+'): continue
        directory=ROOT/'vendor'/p['name']
        if not directory.exists(): directory=ROOT/'vendor'/(p['name']+'-'+p['version'])
        m=json.loads((directory/'.cargo-checksum.json').read_text())
        assert m['package']==p['checksum'],p['name']
        for rel,digest in m['files'].items(): assert sha(directory/rel)==digest,(p['name'],rel);count+=1
        packages.append({'name':p['name'],'version':p['version'],'package_checksum':p['checksum'],'files':len(m['files'])})
    spec=json.loads(subprocess.check_output(['git','show','68b4374f93487fef3b559e9a401bc231a7c7bdfe:docs/restart/implementation/reviews/S03-spec.json'],cwd=ROOT))
    for a in spec['bindings']:assert sha(ROOT/a['path'])==a['sha256'],a['path']
    diff=subprocess.check_output(['git','diff','--name-only','271bb88cf8a3efef71a01f2130897ab098e537a5',CANDIDATE],cwd=ROOT).decode().splitlines()
    assert all(x.startswith('docs/restart/implementation/S03/') for x in diff)
    for rel in ['crates/nsealr-core/src/session/source_backup.rs','crates/nsealr-core/src/board_profile_tests.rs']:
        base=subprocess.check_output(['git','show','3cbd818a0bcd4016eb8983dad7605cb57280d913:'+rel],cwd=ROOT)
        assert base.replace(b'render_review_page',b'render_preview_page')==(ROOT/rel).read_bytes()
    out={'candidate':CANDIDATE,'source':'271bb88cf8a3efef71a01f2130897ab098e537a5','manifest_files_verified':len(checked),'accepted_spec_bindings_verified':3,'narrow_scope_substitutions_verified':2,'lock_vendor_packages':packages,'vendor_files_verified':count,'final_commit_docs_only':diff}
    (EVIDENCE/'integrity.json').write_text(json.dumps(out,indent=2)+'\n')
    print('integrity',len(checked),count,flush=True)

if __name__=='__main__':
    changed=subprocess.check_output(['git','diff','--name-only',CANDIDATE],cwd=ROOT).decode().splitlines()
    assert all(p.startswith('docs/restart/implementation/reviews/S03-security/') for p in changed),changed
    audit()
    run('input-main-reconciliation',['python3',str(OWN/'audit_inputs.py')],{'PYTHONDONTWRITEBYTECODE':'1'})
    run('environment',['rustc','-Vv'])
    run('runtime-features',['cargo','tree','--locked','--offline','-p','nsealr-core','--no-default-features','-e','features,no-dev'])
    run('author-affected',['cargo','test','--locked','--offline','-p','nsealr-core','s03_','--','--nocapture'],{'S03_OBSERVED':str(EVIDENCE/'observed-events.json')})
    run('author-public-contract',['cargo','test','--locked','--offline','-p','nsealr-core','--doc'])
    run('oracle-actual-rerun',['python3','docs/restart/implementation/S03/oracle.py','--check','--fixtures','docs/restart/implementation/S03/vectors.json','--observed',str(EVIDENCE/'observed-events.json')],{'PYTHONDONTWRITEBYTECODE':'1'})
    run('no-std-target',['cargo','build','--locked','--offline','-p','nsealr-core','--release','--target','riscv32imafc-unknown-none-elf'])
    manifest=str(OWN/'probe/Cargo.toml')
    run('probe-lock',['cargo','generate-lockfile','--offline','--manifest-path',manifest])
    run('independent-lifecycle',['cargo','test','--locked','--offline','--manifest-path',manifest,'--','--nocapture'])
    run('independent-build',['cargo','build','--locked','--offline','--manifest-path',manifest])
    run('independent-adversarial',['python3',str(OWN/'adversarial.py')],{'PYTHONDONTWRITEBYTECODE':'1'})

    run('shipping-surface',['python3',str(OWN/'audit_shipping.py')],{'PYTHONDONTWRITEBYTECODE':'1'})
