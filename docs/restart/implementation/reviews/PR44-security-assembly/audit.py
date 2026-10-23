"""Exact final assembly review, without rerunning component experiments."""
import collections
import sys
import functools
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = '994a8b682ed6cd52bb46608b90794c02d2a9d3cb'
CANDIDATE = sys.argv[1]
PREVIOUS = '1be80c8114583627a8eef1952a0cd939f40b84ec'
PREPARATION = '660d73caf2dda71999dac901e65c0e042bfdf37f'
PI_SOURCE = '69a090254738cbf6368b37c2ebb820a99bf83ea4'
P = 'docs/restart/implementation/QH01/rust-qr-delivery/'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


@functools.cache
def tree(commit):
    result = {}
    for row in git('ls-tree', '-rz', '-l', commit).split(b'\0'):
        if row:
            head, path = row.split(b'\t', 1)
            mode, kind, oid, size = head.decode().split()
            result[path.decode()] = (mode, oid, int(size))
            assert kind == 'blob'
    return result


@functools.cache
def contents(oid):
    return git('cat-file', 'blob', oid)


def blob(path, commit=CANDIDATE):
    return contents(tree(commit)[path][1])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def doc(path, commit=CANDIDATE):
    return json.loads(blob(path, commit))


# Additional frozen sources are the complete admitted component diffs and
# the two distinct review prefixes; no inferred selection from the delivery.
DEPS = '1d10e7a1c2986a5d244807624377e22ad562a110'
GATE = '87918b96b7498de6b4bddf5da52566e11916e4b9'
DEP_REVIEW = '21f65fcd541bd856844ea70d6db0eabcae18dee3'
GATE_REVIEW = 'd13f4f8df64baec65d81d3ee9e8a0c46e267ad6c'
COMBINED = 'd250d1302fb88487e14b6883463386fe66aa7fc7'

def changed_paths(a, b):
    return git('diff','--no-renames','--name-only',a,b).decode().splitlines()

new_allowed = {}
for ref, prefix in [(DEPS,None),(GATE,None),
                    (DEP_REVIEW,'docs/restart/implementation/reviews/R00-ctutils-remediation/'),
                    (GATE_REVIEW,'docs/restart/implementation/reviews/R00-audit-data/')]:
    selected = changed_paths(PREVIOUS, ref) if prefix is None else [p for p in tree(ref) if p.startswith(prefix)]
    for path in selected:
        assert path not in new_allowed
        new_allowed[path] = ref
assert len(new_allowed) == 201
inventory = doc(P+'copy-inventory.json')
previous_inventory = doc(P+'copy-inventory.json', PREVIOUS)
assert inventory['exact_copy_count'] == len(inventory['copies']) == 796
assert len(inventory['source_groups']) == 23
assert inventory['source_groups'][:17] == previous_inventory['source_groups']
old_copies = {x['destination_path']:x for x in previous_inventory['copies']}
copies = {x['destination_path']:x for x in inventory['copies']}
assert len(old_copies) == 595 and len(copies) == 796
assert set(copies) == set(old_copies) | set(new_allowed)
assert not set(old_copies) & set(new_allowed)
for path, item in copies.items():
    ref = old_copies[path]['source_commit'] if path in old_copies else new_allowed[path]
    assert item['source_commit'] == ref and item['source_path'] == path
    assert tree(ref)[path] == tree(CANDIDATE)[path] == (item['mode'],item['blob'],item['bytes'])
    assert sha(blob(path)) == item['sha256']
    if path in old_copies:
        assert tree(PREVIOUS)[path] == tree(CANDIDATE)[path]
    if path in tree(BASE):
        before = item['base_file']
        assert before['commit'] == BASE
        assert tree(BASE)[path] == (before['mode'],before['blob'],before['bytes'])
        assert sha(blob(path,BASE)) == before['sha256']
covered = []
for group in inventory['source_groups']:
    assert git('rev-parse',group['source_commit']+'^{tree}').decode().strip() == group['source_tree']
    selected = set(group['paths']) if 'paths' in group else {p for p in tree(group['source_commit']) if p.startswith(group['prefix'].rstrip('/')+'/')}
    assert len(selected) == group['count']
    rows = [x['destination_path'] for x in inventory['copies'] if x['source_commit'] == group['source_commit'] and x['source_path'] in selected]
    assert set(rows) == selected
    covered.extend(rows)
assert collections.Counter(covered) == collections.Counter(copies.keys())

delta = {path:status for status,path in (line.split('\t') for line in git('diff','--no-renames','--name-status',BASE,CANDIDATE).decode().splitlines())}
manifest = doc(P+'artifact-manifest.json')
assert manifest['member_count'] == len(manifest['members'])
assert len({x['path'] for x in manifest['members']}) == len(manifest['members'])
assert set(delta) == {x['path'] for x in manifest['members']} | {P+'artifact-manifest.json'}
for x in manifest['members']:
    assert tree(CANDIDATE)[x['path']] == (x['mode'],x['blob'],x['bytes'])
    assert delta[x['path']] == x['change'] and sha(blob(x['path'])) == x['sha256']
non_copy = set(delta)-set(copies)
assert all(p.startswith(P) or p in {'docs/restart/README.md','docs/restart/implementation/handoff.md','plan/work-items.json'} for p in non_copy)
allowed_changed_old_wrapper = {P+n for n in ['artifact-manifest.json','README.md','copy-inventory.json','source-scope.json','source-correspondence.json','result.json']}
for path in tree(PREVIOUS):
    if path.startswith(P) and path not in allowed_changed_old_wrapper:
        assert tree(PREVIOUS)[path] == tree(CANDIDATE)[path],path
scope = doc(P+'source-scope.json')
assert {p for p,s in delta.items() if s=='M'} == set(scope['existing_paths_allowed_now'])
git('diff','--quiet',PI_SOURCE,CANDIDATE,'--','apps/pi')

old_graph,new_graph = doc('plan/work-items.json',PREVIOUS),doc('plan/work-items.json')
assert {k:v for k,v in old_graph.items() if k!='tasks'} == {k:v for k,v in new_graph.items() if k!='tasks'}
a,b = ({t['id']:t for t in graph['tasks']} for graph in [old_graph,new_graph])
assert set(a)==set(b) and len(b)==47
for name,before in a.items():
    fields = {k for k in set(before)|set(b[name]) if before.get(k)!=b[name].get(k)}
    assert fields <= {'current_checkpoint','result_artifacts'} if name in ['R00','QH01'] else not fields
for name in ['R00','QH01']:
    artifacts = b[name]['result_artifacts']
    assert len({x['path'] for x in artifacts}) == len(artifacts)
    for item in artifacts:
        assert sha(blob(item['path'])) == item['sha256']

corr = doc(P+'source-correspondence.json')
security = doc(P+'security-fix-correspondence.json')
inner_members = 0
manifests_by_path = {}
for row in corr['current_manifests']+security['new_current_manifests']:
    if row['path'] in manifests_by_path:
        previous = manifests_by_path[row['path']]
        for key in ['sha256','member_field','members_checked']:
            assert previous[key] == row[key]
    manifests_by_path[row['path']] = row
for row in manifests_by_path.values():
    assert sha(blob(row['path'])) == row['sha256']
    members = doc(row['path'])[row['member_field']]
    assert len(members)==row['members_checked']
    for x in members:
        assert len(blob(x['path']))==x['bytes'] and sha(blob(x['path']))==x['sha256']
        if 'mode' in x:
            assert tree(CANDIDATE)[x['path']][0]==x['mode']
    inner_members += len(members)
for row in corr['unchanged_existing_input_bindings']:
    assert blob(row['path'])==blob(row['path'],BASE)
    assert sha(blob(row['path']))==row['sha256']
for role,ref in [('ctutils',DEP_REVIEW),('audit_data',GATE_REVIEW)]:
    x=security['component_reviews'][role]
    assert x['commit']==ref and sha(blob(x['path']))==x['sha256']
    review=doc(x['path'])
    assert review['findings']==[] and review['verdict']==x['verdict']
    assert blob(x['path'])==blob(x['path'],ref)
# These are exactly the dependency and gate/control postimages actually exercised
# together, including the control module inside the audit-data proof prefix.
rows=security['exact_implementation_and_test_bindings']
assert len(rows)==16
for x in rows:
    assert tree(COMBINED)[x['path']]==tree(CANDIDATE)[x['path']]

checks = doc(P+'security-fix-checks.json')
structural = checks['structural_source_commit']
assert structural == '6148330d4a66a57f189ef3d931a909c08c9bc934'
assert git('rev-parse',structural+'^{tree}').decode().strip() == checks['structural_source_tree']
git('merge-base','--is-ancestor',structural,CANDIDATE)
for field,hash_field in [('metadata_commands','metadata_commands_sha256'),('metadata_context','metadata_context_sha256'),('format_receipt','format_receipt_sha256')]:
    assert sha(blob(checks[field])) == checks[hash_field]
commands = doc(checks['metadata_commands'])
assert [r['argv'] for r in commands] == [['make','docs'],['python3','scripts/validate_restart_plan.py'],['python3','scripts/verify_evidence.py'],['python3','scripts/verify_contracts.py']]
assert [r['exit_code'] for r in commands] == checks['metadata_exits'] == [0,0,0,0]
for command in commands:
    log = str(Path(checks['metadata_commands']).parent/command['log'])
    assert sha(blob(log)) == command['sha256']
context = doc(checks['metadata_context'])
assert context['source_commit_before_receipts'] == structural
assert context['source_tree_before_receipts'] == checks['structural_source_tree']
assert context['clean_tracked_source_before_execution'] is True
assert sha(blob(context['environment_source'])) == context['environment_sha256']
assert len(context['stable_inputs']) == checks['stable_input_count'] == 40
for row in context['stable_inputs']:
    assert blob(row['path'],structural) == blob(row['path'])
    assert sha(blob(row['path'])) == row['sha256']
for name,digest in checks['current_wrapper_bindings'].items():
    assert sha(blob(P+name)) == digest
assert checks['frozen_closed_files'] == 1508
assert checks['outer_changed_paths_vs994'] == len(delta) == 832
assert checks['outer_manifest_members_expected'] == len(manifest['members']) == 831
assert checks['full_diff_check_exit'] == 2
assert checks['explicit_assembly_authored_scope_check_exit'] == 0

result = {'status':'PASS_source_and_assembly_correspondence_only_final_structural_receipts_separate',
          'candidate':CANDIDATE,'tree':git('rev-parse',CANDIDATE+'^{tree}').decode().strip(),
          'outer_members':len(manifest['members']),'changed_paths':len(delta),
          'exact_postimages':len(copies),'preserved_prior_postimages':len(old_copies),
          'additional_frozen_postimages':len(new_allowed),'source_groups':len(inventory['source_groups']),
          'inner_manifest_members':inner_members,'combined_tested_postimages':len(rows),
          'distinct_inner_manifests':len(manifests_by_path),
          'four_required_structural_gates_exit':[r['exit_code'] for r in commands],
          'stable_structural_input_hashes_verified':len(context['stable_inputs']),
          'current_wrapper_hashes_verified':len(checks['current_wrapper_bindings']),
          'other45_full_task_records_unchanged':True,'all47_status_criteria_dependencies_resources_and_release_sets_unchanged':True,
          'complete_apps_pi_equals_tested69a':True,
          'historical_wrapper_files_preserved_except_explicit_current_six':True,
          'new_product_or_component_tests':0,
          'verifier_observation':'First source audit checked overlapping manifest lists twice and reported886 occurrences. Lists share three entries; metadata inspected, entries deduplicated by path with hash/field/count equality,712 unique members. Original first receipt retained. Product/tests/thresholds unchanged.'}
(Path(__file__).parent/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
