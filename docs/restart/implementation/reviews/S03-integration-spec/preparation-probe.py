#!/usr/bin/env python3
"""Read-only pre-admission S03 source/spec bindings; no product execution."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import subprocess
import tomllib
import urllib.request

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
PREP='e2df91f57c12066d5ea2e2409123cf5127642651'
PREFIX='docs/restart/implementation/S03/integration/'
SOURCE='03216fba02d229bcdb5c81d0573bbe26c6f35abc'
SOURCE_BASE='3cbd818a0bcd4016eb8983dad7605cb57280d913'
TARGET='a5f7b9f2e087c9538495a16706644f3390e6b01c'
RESULT={'preparation':PREP,'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'READ_ONLY_PREPARATION_NO_ADMISSION','implementation_admitted':False,
        'actual_corrected_main_and_final_specification_verdict':'PENDING','checks':{}}
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
def content(commit,path):return git('show',commit+':'+path)
def read(name):return json.loads(content(PREP,PREFIX+name))
def tree(commit):
    result={}
    for row in git('ls-tree','-rz','--full-tree',commit).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);result[path.decode()]=tuple(meta.decode().split())
    return result
TREES={}
CONTENT={}
def verify(row):
    commit,path=row['commit'],row['path']
    if commit not in TREES:TREES[commit]=tree(commit)
    assert TREES[commit][path]==(row['mode'],'blob',row['blob'])
    if row['blob'] not in CONTENT:CONTENT[row['blob']]=git('cat-file','blob',row['blob'])
    data=CONTENT[row['blob']]
    assert len(data)==row['bytes'] and sha(data)==row['sha256'],path

def main():
    source=read('source-reconciliation.json');acceptance=read('acceptance-plan.json')
    rows=source['source_changed_files']
    actual={}
    diff=git('diff','--name-status','--no-renames',SOURCE_BASE,SOURCE).decode().splitlines()
    for line in diff:
        status,path=line.split('\t');actual[path]=status
    assert len(rows)==746 and {r['path']:r['status_from_original_base'] for r in rows}==actual
    n=0;groups={};collisions=[]
    base_tree=tree(SOURCE_BASE);target_tree=tree(TARGET)
    for row in rows:
        groups[row['group']]=groups.get(row['group'],0)+1
        for name in ['source_base','reviewed_source','preparation_target']:
            if row[name] is not None:verify(row[name]);n+=1
        assert row['reviewed_source']['commit']==SOURCE
        if row['group']=='product_source':
            changed=base_tree.get(row['path'])!=target_tree.get(row['path'])
            assert changed==row['target_changed_from_source_base']
            if changed:collisions.append(row['path'])
        if row['group']=='vendor':assert row['path'] not in target_tree
    assert groups=={'product_source':21,'historical_source_evidence':39,'vendor':686},groups
    assert set(collisions)=={r['path'] for r in source['explicit_collision_resolutions']}
    assert len(collisions)==14
    context=source['requirement_and_target_context'];assert len(context)==30
    for row in context:verify(row);n+=1
    old_plan=json.loads(content(SOURCE,'docs/restart/implementation/S03/acceptance-plan.json'))
    cases=old_plan['cases'];new=acceptance['preserved_original_cases']
    assert len(cases)==len(new)==20
    for old,current in zip(cases,new):
        assert old['id']==current['id'] and old['test_name']==current['test_name']
        for field in ['arrange','actions','expected']:
            assert current['original_'+field]==old[field],(old['id'],field)
        assert current['requirements']==old['requirements']
    plan=json.loads(content(TARGET,'plan/work-items.json'))
    task=next(t for t in plan['tasks'] if t['id']=='S03')
    assert acceptance['canonical_acceptance']==source['canonical_acceptance']==task['acceptance']
    projection=json.loads(content(TARGET,'ci/core-test-projections.json'));assert len(projection)==170
    RESULT['checks']['Git_bindings']={'all_source_changes':len(rows),'groups':groups,
      'verified_source_context_bindings':n,'unique_blob_hashes':len(CONTENT),'actual_collision_paths':collisions,
      'all_new_vendor_files_absent_from_target':686,'unchanged_canonical_criteria':len(task['acceptance']),
      'original20_families_arrange_actions_expected_requirements_preserved':True,'existing_projection_rows':len(projection)}
    locks={p:tomllib.loads(content(TARGET,p).decode())['package'] for p in ['Cargo.lock','apps/desktop-simulator/Cargo.lock']}
    key=lambda p:(p['name'],p['version'],p.get('source'),p.get('checksum'))
    current={key(p) for packages in locks.values() for p in packages}
    oldlock=tomllib.loads(content(SOURCE,'Cargo.lock').decode())['package'];old={key(p) for p in oldlock}
    recorded={key(p) for p in source['original_combined_source_lock_packages']}
    assert old==recorded and current<=old and len(current)==26 and len(old)==47
    for path,packages in locks.items():assert {key(p) for p in packages}=={key(p) for p in source['target_lock_package_inventories'][path]}
    additional=sorted((p[0],p[1]) for p in old-current)
    assert additional==[tuple(x) for x in source['observed_lock_relationship']['additional_reviewed_name_versions']]
    source_tree=tree(SOURCE)
    for name,version in additional:
        package=next(p for p in oldlock if p['name']==name and p['version']==version)
        prefix='vendor/'+name+'/'
        checksum=json.loads(content(SOURCE,prefix+'.cargo-checksum.json'))
        assert checksum['package']==package['checksum']
        vendor_files={p[len(prefix):] for p in source_tree if p.startswith(prefix)}-{'.cargo-checksum.json'}
        assert vendor_files==set(checksum['files'])
        for path,digest in checksum['files'].items():assert sha(content(SOURCE,prefix+path))==digest
    RESULT['checks']['lock_package_identities']={'current_union':26,'reviewed_combined':47,'additional':additional,
       'current_versions_sources_checksums_preserved_in_reviewed_combined':True,
       'all21_new_vendor_package_and_every_per_file_checksum_matches':True}
    original_review='b03475ccf4a057c7771065126002f2e4e056d28d'
    report=json.loads(content(original_review,'docs/restart/implementation/reviews/S03-security/report.json'))
    assert report['candidate_commit']=='2d7d465a291c4d4a1324d90595fc45a2fdbefca5'
    difference=git('diff','--name-only',report['candidate_commit'],SOURCE,'--','crates','apps','Cargo.lock','vendor').decode().splitlines()
    assert difference==['crates/nsealr-core/src/review/qr_flow.rs']
    comments='95cd3fc79d885c58bdabe71498d2509b6ff4370e'
    assert git('diff',comments,SOURCE,'--','crates','apps','Cargo.lock','vendor')==b''
    RESULT['checks']['historical_review_reuse']={'original_review':original_review,
      'original_review_candidate':report['candidate_commit'],'bounded_verdict':report['verdict'],
      'source_product_difference_from_original_review':difference,
      'all_source_product_bytes_equal_comment_review_candidate':comments,
      'review_not_rebound_to_future_integrated_bytes':True}
    current='b1c90139a651895284b2624da7d12903cf16bc9d'
    current_tree=tree(current)
    assert git('rev-parse',current+'^{tree}').decode().strip()=='0014d51b24ea0b58650d3dee3a5a8616367e6769'
    changed_context=[row['path'] for row in context if target_tree[row['path']]!=current_tree[row['path']]]
    assert set(changed_context)=={'scripts/verify_contracts.py','scripts/test_contracts.py'}
    changed_product=[row['path'] for row in rows if row['group']=='product_source'
                     and target_tree.get(row['path'])!=current_tree.get(row['path'])]
    assert not changed_product
    changed_since_target=sorted(p for p in set(target_tree)|set(current_tree)
                               if target_tree.get(p)!=current_tree.get(p))
    outside_proof=[p for p in changed_since_target if not p.startswith('docs/restart/implementation/A02/post-rebase-repair/')]
    assert outside_proof==['docs/restart/README.md','docs/restart/implementation/handoff.md','scripts/test_contracts.py','scripts/verify_contracts.py']
    RESULT['checks']['new_actual_main_provisional_read_only_classification']={
       'commit':current,'tree':'0014d51b24ea0b58650d3dee3a5a8616367e6769',
       'source_of_main_and_CI_state':'Coordinator reports protected PR32 merge; actual corrected-main CI39412818666 still in_progress, no PASS inferred.',
       'changed_preparation_context_paths':changed_context,'changed21_product_preimages':changed_product,
       'all_full_tree_changes_outside_admitted_repair_proof':outside_proof,
       'final_five_doc_addendum_candidate_and_actual_successful_main_CI':'PENDING'}
    nip=read('nip-reconciliation.json');pins=nip['official_Git_tree_comparison']['pins']
    official={}
    for commit,row in pins.items():
        commit_request=urllib.request.Request('https://api.github.com/repos/nostr-protocol/nips/git/commits/'+commit,
                         headers={'User-Agent':'nsealr-independent-spec-review'})
        actual_commit=json.load(urllib.request.urlopen(commit_request,timeout=30))
        assert actual_commit['sha']==commit and actual_commit['tree']['sha']==row['tree']
        assert actual_commit['committer']['date']==row['commit_date']
        url='https://api.github.com/repos/nostr-protocol/nips/git/trees/'+row['tree']
        request=urllib.request.Request(url,headers={'User-Agent':'nsealr-independent-spec-review'})
        data=json.load(urllib.request.urlopen(request,timeout=30))
        assert data['sha']==row['tree']
        official[commit]={entry['path']:entry['sha'] for entry in data['tree']}
    compared=[]
    first,second=list(pins)
    for row in nip['official_Git_tree_comparison']['files']:
        a,b=official[first][row['path']],official[second][row['path']]
        assert (a,b)==(row['first_blob'],row['second_blob']) and (a==b)==row['identical']
        compared.append({'path':row['path'],'first_blob':a,'second_blob':b,'identical':a==b})
    bodies={}
    for row in nip['read_changed_document']:
        data=urllib.request.urlopen(row['source_url'],timeout=30).read()
        assert len(data)==row['bytes'] and sha(data)==row['sha256']
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==official[row['commit']][row['path']]
        bodies[row['commit']]=data
    patch=''.join(difflib.unified_diff(bodies[second].decode().splitlines(keepends=True),
                                    bodies[first].decode().splitlines(keepends=True),fromfile=second+'/01.md',tofile=first+'/01.md'))
    changed=[x for x in patch.splitlines() if x[:1] in {'+','-'} and not x.startswith(('+++','---'))]
    semantic=[line for line in changed if line[1:].strip()]
    assert len(semantic)==1 and semantic[0].startswith('+If any of these lists is empty,')
    delta={'unified_diff_sha256':sha(patch.encode()),
           'added_lines':len([line for line in changed if line.startswith('+')]),
           'removed_lines':len([line for line in changed if line.startswith('-')]),
           'nonblank_added_line_sha256':sha(semantic[0][1:].encode()),
           'semantic_assessment':'An empty list in a relay subscription filter matches no event and is distinct from an absent attribute.'}
    (OUT/'nip01-independent-comparison.json').write_text(json.dumps(delta,indent=2)+'\n')
    RESULT['checks']['official_primary_NIP_comparison']={'source':'Official nostr-protocol/nips GitHub trees and raw immutable bodies',
      'pins':list(pins),'exact_blob_comparisons':compared,'changed_document_body_hashes_verified':True,
      'actual_complete_delta':delta,'relevance':'Relay REQ empty-list matching; no event serialization/parser/signature delta. Prior narrower S03 grammar retained; no global client-qualification baseline change.'}
    RESULT['outcome']='BINDINGS_VERIFIED_NO_ADMISSION'

try:main()
except Exception as error:
    RESULT['outcome']='PROBE_FAILED';RESULT['error']={'type':type(error).__name__,'diagnostic':str(error)}
    raise
finally:
    (OUT/'preparation-result.json').write_text(json.dumps(RESULT,indent=2)+'\n')
