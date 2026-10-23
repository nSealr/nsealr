"""Exact final assembly review, without rerunning component experiments."""
import collections
import functools
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = '994a8b682ed6cd52bb46608b90794c02d2a9d3cb'
CANDIDATE = '1be80c8114583627a8eef1952a0cd939f40b84ec'
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


delta = dict((path, status) for status, path in
             (row.split('\t') for row in git('diff', '--no-renames', '--name-status', BASE, CANDIDATE).decode().splitlines()))
assert len(delta) == 620 and collections.Counter(delta.values()) == {'A': 615, 'M': 5}
manifest = doc(P + 'artifact-manifest.json')
assert manifest['member_count'] == len(manifest['members']) == 619
assert len({x['path'] for x in manifest['members']}) == 619
assert set(delta) == {x['path'] for x in manifest['members']} | {P + 'artifact-manifest.json'}
for x in manifest['members']:
    mode, oid, size = tree(CANDIDATE)[x['path']]
    assert (mode, oid, size) == (x['mode'], x['blob'], x['bytes'])
    assert delta[x['path']] == x['change'] and sha(contents(oid)) == x['sha256']
scope = doc(P + 'source-scope.json')
assert {p for p, status in delta.items() if status == 'M'} == set(scope['existing_paths_allowed_now'])

inventory = doc(P + 'copy-inventory.json')
assert len(inventory['copies']) == inventory['exact_copy_count'] == 595
assert len(inventory['source_groups']) == 17
assert len({x['destination_path'] for x in inventory['copies']}) == 595
dispositions = collections.Counter(x['base_disposition'] for x in inventory['copies'])
assert dispositions == {'absent_new_exact_copy': 593, 'existing_overwritten_exact_accepted_postimage': 2}
for x in inventory['copies']:
    source = tree(x['source_commit'])[x['source_path']]
    current = tree(CANDIDATE)[x['destination_path']]
    assert current == source == (x['mode'], x['blob'], x['bytes'])
    assert sha(contents(current[1])) == x['sha256']
    assert x['source_path'] == x['destination_path']
    if x['destination_path'] in tree(BASE):
        before = x['base_file']
        assert before['commit'] == BASE
        assert tree(BASE)[x['destination_path']] == (before['mode'], before['blob'], before['bytes'])
        assert sha(blob(x['destination_path'], BASE)) == before['sha256']
        assert x['tested_source'] == PI_SOURCE
        assert tree(PI_SOURCE)[x['destination_path']] == current
    else:
        assert x['base_disposition'] == 'absent_new_exact_copy'
covered = []
for group in inventory['source_groups']:
    assert git('rev-parse', group['source_commit'] + '^{tree}').decode().strip() == group['source_tree']
    selected = set(group['paths']) if 'paths' in group else {
        p for p in tree(group['source_commit']) if p.startswith(group['prefix'].rstrip('/') + '/')}
    assert len(selected) == group['count']
    matching = [x['destination_path'] for x in inventory['copies']
                if x['source_commit'] == group['source_commit'] and x['source_path'] in selected]
    assert set(matching) == selected
    covered.extend(matching)
assert collections.Counter(covered) == collections.Counter(x['destination_path'] for x in inventory['copies'])
old_inventory = doc(P + 'copy-inventory.json', PREPARATION)
assert len(old_inventory['copies']) == 562
for x in old_inventory['copies']:
    assert tree(PREPARATION)[x['destination_path']] == tree(CANDIDATE)[x['destination_path']]
git('diff', '--quiet', PI_SOURCE, CANDIDATE, '--', 'apps/pi')

correspondence = doc(P + 'source-correspondence.json')
inner_count = 0
for record in correspondence['current_manifests']:
    assert sha(blob(record['path'])) == record['sha256']
    inner = doc(record['path'])[record['member_field']]
    assert len(inner) == record['members_checked']
    for item in inner:
        data = blob(item['path'])
        assert len(data) == item['bytes'] and sha(data) == item['sha256']
        if 'mode' in item:
            assert tree(CANDIDATE)[item['path']][0] == item['mode']
    inner_count += len(inner)
assert inner_count == 538
assert len(correspondence['unchanged_existing_input_bindings']) == 14
for record in correspondence['unchanged_existing_input_bindings']:
    assert blob(record['path']) == blob(record['path'], BASE)
    assert sha(blob(record['path'])) == record['sha256']

old_graph = doc('plan/work-items.json', BASE)
new_graph = doc('plan/work-items.json')
assert {k:v for k,v in old_graph.items() if k != 'tasks'} == {k:v for k,v in new_graph.items() if k != 'tasks'}
old_tasks = {x['id']: x for x in old_graph['tasks']}
new_tasks = {x['id']: x for x in new_graph['tasks']}
assert set(old_tasks) == set(new_tasks) and len(new_tasks) == 47
for task, before in old_tasks.items():
    after = new_tasks[task]
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    assert changed <= {'current_checkpoint', 'result_artifacts'} if task in ('QH01', 'QP01') else not changed
for task in ('QH01', 'QP01'):
    artifacts = new_tasks[task]['result_artifacts']
    assert len({x['path'] for x in artifacts}) == len(artifacts)
    for item in artifacts:
        assert sha(blob(item['path'])) == item['sha256']

final = doc(P + 'final-checks.json')
for field, hash_field in (('metadata_commands', 'metadata_command_sha256'), ('metadata_context', 'metadata_context_sha256')):
    assert sha(blob(final[field])) == final[hash_field]
commands = doc(final['metadata_commands'])
assert [x['argv'] for x in commands] == [['make','docs'], ['python3','scripts/validate_restart_plan.py'],
                                       ['python3','scripts/verify_evidence.py'], ['python3','scripts/verify_contracts.py']]
assert [x['exit_code'] for x in commands] == [0, 0, 0, 0]
for command in commands:
    log = str(Path(final['metadata_commands']).parent / command['log'])
    assert sha(blob(log)) == command['sha256']
context = doc(final['metadata_context'])
assert len(context['stable_inputs']) == 17
for record in context['stable_inputs']:
    assert sha(blob(record['path'])) == record['sha256']
assert sha(blob(context['environment_source'])) == context['environment_sha256']
for record in final['preserved_preparation_receipts']:
    assert blob(record['path']) == blob(record['path'], PREPARATION)
    assert sha(blob(record['path'])) == record['sha256']
assert len(final['preserved_preparation_receipts']) == 8
for path, digest in final['current_wrapper_bindings'].items():
    assert sha(blob(P + path)) == digest

Path(__file__).with_name('validation.json').write_text(json.dumps({
    'candidate': CANDIDATE, 'tree': git('rev-parse', CANDIDATE + '^{tree}').decode().strip(),
    'base': BASE, 'reviewer': '/root', 'verdict': 'PASS_FINAL_ASSEMBLY_SOURCE_AND_METADATA_ONLY',
    'checked': {'manifest_members': 619, 'changed_paths': 620, 'added': 615, 'modified': 5,
                'exact_source_postimages': 595, 'new_exact_sources': 593, 'accepted_existing_Pi_postimages': 2,
                'source_groups': 17, 'prior_copies_unchanged': 562, 'current_inner_members': 538,
                'original_inputs_equal_base': 14, 'other_full_task_records_unchanged': 45,
                'all47_states_and_acceptance_dependencies_resources_releases_unchanged': True,
                'entire_apps_pi_equal_tested69a': True, 'final_metadata_gate_receipts': 4,
                'current_stable_gate_inputs': 17, 'preserved_preparation_receipts': 8},
    'new_component_runtime_build_crypto_install_runs': 0,
    'reader_observation': 'An initial display filter compared the disposition with an assumed label and printed an oversized inventory; the tool truncated it. It was not treated as fully read. Actual category counts were inspected, only the two intended rows were recovered with an asserted output bound, and every595 source row is verified programmatically here.',
    'integration': 'Not integrated. Exact candidate review only; protected PR/actual tested merge and resulting-main gates remain mandatory.',
    'limits': 'Accepted source-specific experiments and narrow probe correction only; no task, target, physical, final decoder, camera/color, framing/profile, route or secrets-isolation acceptance.'
}, indent=2) + '\n')
print('PASS final assembly:595 source postimages/619 members/620 paths;538 inner members;47 task sets and45 other records unchanged;17 gate inputs and8 historical receipts exact. No component tests rerun.')
