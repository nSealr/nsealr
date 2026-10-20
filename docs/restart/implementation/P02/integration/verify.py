#!/usr/bin/env python3
"""Verify selective documentary source/copy/context/case correspondence.

No client fetch, package install, browser, hardware, pilot or old helper runs.
"""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import re
import subprocess
from urllib.parse import unquote,urlsplit

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
BASE='b1c90139a651895284b2624da7d12903cf16bc9d'
SOURCE='8525ce01ad02466b78654e31c672774c99d256da'
SOURCE_BASE='f2ef70f522af4977e15f81554a8c6eadcdbe8097'
RESULT={'task':'P02','scope':'Current-layout documentary integration source/copy/correspondence checks only',
        'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':BASE,'checks':{}}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def body(commit,path):return git('show',commit+':'+path)
def tree(commit):
    rows={}
    for raw in git('ls-tree','-rz','--full-tree',commit).split(b'\0'):
        if raw:
            meta,path=raw.split(b'\t',1);rows[path.decode()]=tuple(meta.decode().split())
    return rows
def local(path):return (ROOT/path).read_bytes()

def main():
    mapping=json.loads(local('docs/restart/implementation/P02/integration/source-map.json'))
    base=tree(BASE);source=tree(SOURCE)
    selected=git('diff','--name-only',SOURCE_BASE,SOURCE).decode().splitlines()
    copies=mapping['historical_exact_copies']
    assert len(copies)==17 and {r['source_path'] for r in copies}==set(selected)
    bysource={r['source_path']:r for r in copies}
    for row in copies:
        assert source[row['source_path']]==(row['mode'],'blob',row['blob'])
        original=body(row['source_commit'],row['source_path']);copied=local(row['destination'])
        assert original==copied and len(copied)==row['bytes'] and sha(copied)==row['sha256']
        assert body(row['original_review_or_candidate'],row['source_path'])==original
        assert row['destination'] not in base
    # Resolve the complete paired review manifests through explicit source-role map.
    paired=0
    for name in ['P02-final','P02-spec']:
        source_path='docs/restart/implementation/reviews/'+name+'/review-artifacts.json'
        manifest=json.loads(local(bysource[source_path]['destination']))
        for item in manifest['candidate_files']+manifest['files']:
            row=bysource[item['path']];copied=local(row['destination'])
            assert len(copied)==item['bytes'] and sha(copied)==item['sha256']
            if 'blob' in item:assert row['blob']==item['blob']
            paired+=1
    oldplan=json.loads(body(SOURCE_BASE,'docs/restart/work-items.json'))
    plan=json.loads(body(BASE,'plan/work-items.json'))
    assert local('plan/work-items.json')==body(BASE,'plan/work-items.json')
    before={t['id']:t for t in oldplan['tasks']};current={t['id']:t for t in plan['tasks']}
    assert len(before)==len(current)==47 and set(before)==set(current)
    assert all(before[t]['acceptance']==current[t]['acceptance'] and before[t]['depends_on']==current[t]['depends_on'] for t in before)
    assert oldplan['resources']==plan['resources'] and oldplan['release_paths']==plan['release_paths']
    assert mapping['canonical_five_criteria']==current['P02']['acceptance']
    assert len(current['P02']['acceptance'])==5 and current['P02']['status']=='running'
    assert not current['P02'].get('result_artifacts') and not current['P02'].get('review_verdict')
    # The current historical evidence verifier owns declared link relocations.
    spec=importlib.util.spec_from_file_location('evidence_links',ROOT/'scripts/verify_evidence.py')
    links=importlib.util.module_from_spec(spec);spec.loader.exec_module(links)
    contexts=mapping['current_context'];assert len(contexts)==11
    classifications=[]
    for row in contexts:
        historical=row['historical_source'];old=body(historical['commit'],historical['path'])
        assert sha(old)==historical['sha256'] and len(old)==historical['bytes']
        now=body(row['current_commit'],row['current_path'])
        assert row['current_commit']==BASE and base[row['current_path']]==(row['mode'],'blob',row['blob'])
        assert len(now)==row['bytes'] and sha(now)==row['sha256'] and local(row['current_path'])==now
        if row['current_path'] in ['docs/product/client-qualification.md','docs/restart/architecture.md']:
            assert links.relocated(old.decode(),historical['path'],row['current_path']).encode()==now
        classifications.append({'historical':historical['path'],'current':row['current_path'],
             'byte_identical':old==now,'classification':row['classification']})
    register=json.loads(local(bysource['docs/restart/implementation/P02/source-register.json']['destination']))
    assert mapping['selected_clients_unchanged']==register['clients']
    assert mapping['selected_browsers_unchanged']==register['browser_candidates']
    bridge=next(row for row in register['source_files'] if row['id']=='G-B-manifest')
    assert sha(body(BASE,'apps/bridge/browser-extension/src/manifest.ts'))==bridge['sha256']
    active={row['path']:row for row in mapping['active_documents']}
    assert set(active)=={'docs/product/compatibility-plan.md','docs/product/research-protocols.md'}
    for path,row in active.items():
        assert path not in base and sha(local(path))==row['working_target_sha256']
        assert sha(body(row['source_commit'],row['source_path']))==row['source_sha256']
    oldcompat=body(SOURCE,'docs/restart/implementation/P02/compatibility-plan.md').decode()
    compat=local('docs/product/compatibility-plan.md').decode()
    cases=lambda text:{re.match(r'\| (P02-[A-Z]\d\d)\b',line)[1]:line for line in text.splitlines() if re.match(r'\| P02-[A-Z]\d\d\b',line)}
    original_cases=cases(oldcompat);new_cases=cases(compat)
    assert len(original_cases)==31 and original_cases==new_cases
    owners=set()
    for line in new_cases.values():owners.update(re.findall(r'\b[A-Z]{1,3}\d\dS?\b',line.split('|')[-2]))
    assert owners<=set(current),sorted(owners-set(current))
    oldresearch=body(SOURCE,'docs/restart/implementation/P02/research-protocols.md').decode()
    research=local('docs/product/research-protocols.md').decode()
    # All four complete procedures and surrounding consent/record/interpretation
    # obligations are preserved; only the introductory provenance paragraph differs.
    assert oldresearch[oldresearch.index('These are manual procedures'):]==research[research.index('These are manual procedures'):]
    issues=json.loads(local('docs/restart/implementation/P02/integration/source-issues.json'))
    snapshot=mapping['source_issue_snapshot']
    assert sha(local(snapshot['path']))==snapshot['sha256']
    assert [r['selected_public_record']['number'] for r in issues]==[26,27]
    assert all(r['selected_public_record']['state']=='open' for r in issues)
    assert all(sha(r['selected_public_record']['body'].encode())==r['selected_body_sha256'] for r in issues)
    navigation=['docs/product/compatibility-plan.md','docs/product/research-protocols.md',
      'docs/restart/implementation/P02/integration/README.md','docs/restart/implementation/P02/historical/README.md']
    resolved=[]
    for path in navigation:
        for raw in re.findall(r'\[[^\]\n]*\]\(([^\s)]+)\)',local(path).decode()):
            url=urlsplit(raw)
            if url.scheme or url.netloc or not url.path:continue
            destination=((ROOT/path).parent/unquote(url.path)).resolve()
            assert destination.is_relative_to(ROOT) and destination.exists(),(path,raw)
            resolved.append({'from':path,'to':destination.relative_to(ROOT).as_posix()})
    modified=git('diff','--name-only',BASE).decode().splitlines()
    untracked=git('ls-files','--others','--exclude-standard').decode().splitlines()
    paths=set(modified+untracked)
    allowed=lambda p:p in active or p.startswith('docs/restart/implementation/P02/')
    assert all(allowed(p) for p in paths),sorted(p for p in paths if not allowed(p))
    assert not set(base)&set(modified), 'existing base file changed'
    RESULT['checks']={'exact_historical_copies':17,'paired_manifest_dependencies_resolved':paired,
       'current_context_classifications':classifications,'canonical_criteria_preserved':5,
       'all47_criteria_dependencies_and16resources5releases_preserved':True,
       'original_client_source_package_lock_and_browser_inputs_preserved':True,
       'Bridge_manifest_equals_original_registered_companion_body':True,
       'all31_scenario_rows_and_owner_obligations_byte_exact':True,
       'all_four_research_procedures_and_consent_record_limits_byte_exact_after_provenance_intro':True,
       'current_local_navigation_links':resolved,'no_existing_base_file_changed':True,
       'only_new_active_plans_and_scoped_P02_proof':True,
       'no_runtime_human_or_task_closure_claim':True}
    RESULT['outcome']='DOCUMENTARY_SOURCE_COPY_CONTEXT_CORRESPONDENCE_PASS'

try:main()
except Exception as error:
    RESULT['outcome']='CHECK_FAILED';RESULT['failure']={'type':type(error).__name__,'diagnostic':str(error)}
    raise
finally:(OUT/'verification.json').write_text(json.dumps(RESULT,indent=2)+'\n')
