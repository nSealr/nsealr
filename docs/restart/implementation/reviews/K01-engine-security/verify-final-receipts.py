#!/usr/bin/env python3
"""Read-only audit of the fixed K01 package; not a product acceptance gate."""
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

repo = Path('/home/tux/nsealr/.restart-tools/goal/k01-current-implementation')
candidate = '1aa144e9410c014cf55cf0694e24ef1fcddcf729'
base = '7f00138902526a63dc590ad4cd09dc40ab9b9700'
runtime = 'bf51d414f9dfc5f23c863dff51c3128dffa2dcad'
tests = '4bab1c86c0145a44bc5fefdd2f38d80e3336bcfb'
prefix = 'docs/restart/implementation/K01/'
evidence = repo / prefix / 'evidence'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=repo)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def tree(commit):
    result = {}
    for row in git('ls-tree', '-rz', commit).split(b'\0'):
        if row:
            metadata, name = row.split(b'\t', 1)
            mode, kind, blob = metadata.decode().split()
            result[name.decode()] = (mode, kind, blob)
    return result


def binding(row, commit=candidate):
    mode, kind, blob = trees.setdefault(commit, tree(commit))[row['path']]
    data = git('show', commit + ':' + row['path'])
    assert kind == 'blob'
    assert (mode, blob, len(data), digest(data)) == (
        row['mode'], row['blob'], row['bytes'], row['sha256'])
    if commit == candidate:
        assert (repo / row['path']).read_bytes() == data


assert git('rev-parse', 'HEAD').decode().strip() == candidate
assert git('status', '--porcelain') == b''
trees = {candidate: tree(candidate), base: tree(base)}
manifest = load(evidence / 'artifact-manifest.json')
assert len(manifest['members']) == manifest['member_count'] == 304
assert len({x['path'] for x in manifest['members']}) == 304
for row in manifest['members']:
    binding(row)
result = load(evidence / 'result.json')
assert digest((evidence / 'artifact-manifest.json').read_bytes()) == result['artifact_manifest']['sha256']
environment_path = 'docs/restart/implementation/R00/evidence/final/environment.json'
environment_hash = digest((repo / environment_path).read_bytes())
assert environment_hash == '5b0f773e07fc90aa4a2b7d62c102bbc7b824b6bab135002ee0a01ad90a0ef001'
assert git('show', candidate + ':' + environment_path) == (repo / environment_path).read_bytes()
scope = load(evidence / 'source-scope.json')
for row in scope['product_bindings']:
    binding(row)
    binding(row, row['commit'])
for row in scope['original_six_preparation_bindings']:
    binding(row)
    binding(row, row['commit'])
for row in scope['read_only_git_inputs']:
    for commit in (candidate, base):
        assert git('rev-parse', commit + ':' + row['path']).decode().strip() == row['unchanged_git_object']
changed = sorted(p for p in trees[candidate].keys() | trees[base].keys()
                 if trees[candidate].get(p) != trees[base].get(p))
core = set(scope['changed_runtime_paths'])
assert set(p for p in changed if p.startswith('crates/')) == core
assert all(p in core or p.startswith(prefix) or
           p.startswith('docs/restart/implementation/reviews/K01-specification/') for p in changed)
assert all(p.startswith(prefix) for p in git('diff', '--name-only', tests, candidate).decode().splitlines())
assert [p for p in git('diff', '--name-only', runtime, tests).decode().splitlines()
        if p.startswith('crates/')] == ['crates/nsealr-core/src/authorization/tests.rs']
assert git('show', candidate + ':' + prefix + 'evidence/semantic-matrix.json') == git(
    'show', '3a609e78f2e04e93feb31a053ee7dbd257177ac3:' + prefix + 'evidence/semantic-matrix.json')

command_rows = []
for name in ('stable-ci-03/command.json', 'proof-final-core/commands.json',
             'independent-final/commands.json', 'checker-controls-01/command.json',
             'final-metadata-checks/commands.json', 'review-proof-addendum-01/command.json',
             'content-role-red/command.json'):
    receipt_path = evidence / name
    receipt = load(receipt_path)
    assert receipt['environment_sha256'] == environment_hash
    commands = receipt.get('commands', [receipt])
    for index, command in enumerate(commands):
        for stream in ('stdout', 'stderr'):
            filename = f'{index}-{stream}.log' if 'commands' in receipt else f'{stream}.log'
            assert digest((receipt_path.parent / filename).read_bytes()) == command[stream + '_sha256']
        for path, expected in command.get('input_sha256', {}).items():
            assert digest((repo / path).read_bytes()) == expected
        command_rows.append({'receipt': name, 'index': index, 'argv': command['argv'],
                             'exit': command['exit']})
        assert command['exit'] == (101 if name.startswith('content-role-red/') else 0)
reuse = load(evidence / 'independent-reuse.json')
for row in reuse['same_compared_inputs']:
    assert digest((repo / row['path']).read_bytes()) == row['sha256']
checker = load(evidence / 'checker-controls-01/controls/result.json')
assert checker['controls'] == len(checker['rows']) == 30 and checker['all_rejected'] is True
for row in checker['rows']:
    assert row['exit'] == 1
    stem = evidence / 'checker-controls-01/controls' / row['id']
    for kind, suffix in (('input', '.input.json'), ('stdout', '.stdout.log'), ('stderr', '.stderr.log')):
        assert digest(Path(str(stem) + suffix).read_bytes()) == row[kind + '_sha256']
    error = Path(str(stem) + '.stderr.log').read_text()
    assert 'ModuleNotFoundError' not in error and 'FileNotFoundError' not in error

aux = load(evidence / 'auxiliary-prefix-observed.json')
assert len(aux) == 198 and Counter(x['written_prefix'] for x in aux) == Counter({i: 6 for i in range(33)})
for n in range(33):
    assert {x['reported_result'] for x in aux if x['written_prefix'] == n} == {
        'Err(Unavailable)', 'Err(Interrupted)', 'Err(Health)', 'Err(Provider)', f'Ok({min(n,31)})', 'Ok(33)'}
for row in aux:
    assert row['direct_full_destination_wipe'] is True and row['state'] == 'Spent'
    assert row['actual_engine_calls'] == row['engine_provider_calls'] == 1
    assert row['retry_provider_calls'] == row['sign_calls'] == 0 and row['output'] is False
identity = load(evidence / 'identity-operation-observed.json')
assert len(identity) == 9
assert {(x['scalar'], x['fresh_operation']) for x in identity} == {
    (s, n) for s in ('1', '3', 'n-3') for n in range(1,4)}
assert len({x['test_only_original_nsec'] for x in identity}) == 3
assert all(x['provider_calls'] == x['sign_calls'] == 1 and x['state'] == 'Spent' for x in identity)
matrix = load(evidence / 'semantic-matrix-observed.json')
assert len(matrix) == len({x['id'] for x in matrix}) == 70
positive = [x for x in matrix if x['approval_calls'] == 1]
negative = [x for x in matrix if x['approval_calls'] == 0]
assert len(positive) == len(negative) == 35
assert all(x['entropy_calls'] == x['sign_calls'] == 0 and x['output'] is False for x in matrix)
assert all(x['contiguous_data_and_separate_decision'] is True for x in positive)
assert all(x['layer'] in ('parser', 'semantic', 'review') for x in negative)
coverage = {}
for name in ('stable-ci-03/core-coverage.json', 'stable-ci-03/host-coverage.json',
             'proof-final-core/core-coverage.json'):
    coverage[name] = load(evidence / name)['data'][0]['totals']['lines']
assert coverage['stable-ci-03/core-coverage.json']['percent'] == 100
assert coverage['proof-final-core/core-coverage.json']['percent'] == 100
assert coverage['stable-ci-03/host-coverage.json']['percent'] >= 76.70

print(json.dumps({'candidate': candidate, 'tree': git('rev-parse', candidate+'^{tree}').decode().strip(),
 'manifest_verified': 304, 'original_preparation_verified': 6, 'read_only_git_objects_verified': 14,
 'product_bindings_verified': 4, 'total_changed_paths': len(changed), 'out_of_scope': [],
 'final_tail_only_task_proof': True, 'runtime_after_bf51_only_test_change': True,
 'same_compared_input_rows_verified': len(reuse['same_compared_inputs']),
 'environment': {'path': environment_path, 'sha256': environment_hash,
                 'scope': 'Existing bootstrap environment map plus command-specific overrides; not a physical resource inventory.'},
 'command_log_pairs_verified': len(command_rows), 'commands': command_rows,
 'checker_control_originals_verified': 30, 'prefix_records_verified': 198,
 'original_identity_operations_verified': 9, 'matrix_complete_review_records': 35,
 'matrix_zero_effect_rejections': 35, 'coverage': coverage,
 'limits': 'Read-only source/artifact/receipt correspondence; source review determines assertion meaning. No new product tests, target execution, physical qualification, final verdict or CI adoption.'}, indent=2))
