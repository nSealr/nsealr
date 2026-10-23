"""Affected proof correspondence; never executes the experiment or decoder."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
NEW = '06d213fd46e654bfe2ac43e4a88963a346d35973'
OLD = '31df3027a6e0903d8efa183dd3d4f964ebdf3949'
P = 'docs/restart/implementation/QH01/linux-worker-experiment/'
D = P + 'deadline-correction/'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def blob(path, commit=NEW):
    return git('show', f'{commit}:{path}')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def doc(path):
    return json.loads(blob(path))


members = doc(P + 'artifact-manifest.json')['artifacts']
assert len(members) == doc(P + 'artifact-manifest.json')['member_count'] == 263
paths = {v.decode() for v in git('ls-tree', '-rz', '--name-only', NEW, '--', P).split(b'\0') if v}
assert len({m['path'] for m in members}) == 263
assert paths == {m['path'] for m in members} | {P + 'artifact-manifest.json'}
for m in members:
    data = blob(m['path'])
    assert sha(data) == m['sha256'] and len(data) == m['bytes'], m['path']
    assert git('ls-tree', NEW, '--', m['path']).decode().split()[0] == m['mode'] == '100644'
delta = [row.split('\t') for row in git('diff', '--name-status', OLD, NEW).decode().splitlines()]
assert sum(s == 'A' for s, _ in delta) == 113 and sum(s == 'M' for s, _ in delta) == 5
assert all(s in ('A', 'M') and p in paths for s, p in delta)
modified = {p for s, p in delta if s == 'M'}
oldpaths = {v.decode() for v in git('ls-tree', '-rz', '--name-only', OLD, '--', P).split(b'\0') if v}
assert len(oldpaths) == 151
for path in oldpaths - modified:
    assert blob(path) == blob(path, OLD), path
rawpaths = {p for p in oldpaths if '/focused-' in p or '/stable-01/' in p}
assert len(rawpaths) == 136
assert not (rawpaths & modified)
assert blob(D + 'expectation.json') == blob(D + 'expectation.json', 'a080e5a459f98b881f767bda064afcf7431d6cbf')
assert blob(D + 'regression.py') == blob(D + 'regression.py', 'cb123e89bf0325181147f41e948eb30fca95bb7e')
for inv, count in (('before-entry-inventory.json', 5), ('review-copy-inventory.json', 4)):
    copies = doc(D + inv)['copies']
    assert len(copies) == count
    for copy in copies:
        source = blob(copy['source_path'], copy['source_commit'])
        assert blob(copy['target_path']) == source
        assert sha(source) == copy['sha256'] and len(source) == copy['bytes']

result = doc(P + 'result.json')
assert len(result['all_runs']) == 9
for run in result['all_runs'][5:]:
    command_path = run['directory'] + '/command.json'
    command = doc(command_path)
    assert sha(blob(command_path)) == run['command_sha256']
    assert sha(blob(run['summary_path'])) == run['summary_sha256']
    assert command['source_commit'] == run['source_commit'] and command['exit_code'] == run['exit_code']
    hash_key = 'harness_sha256' if run['probe_sha256'] is not None else 'source_sha256'
    assert command[hash_key] == run['source_sha256'] == sha(blob(P + 'experiment.py', run['source_commit']))
    if run['probe_sha256'] is not None:
        assert command['probe_sha256'] == run['probe_sha256'] == sha(blob(D + 'regression.py', run['source_commit']))
assert blob(P + 'experiment.py') == blob(P + 'experiment.py', '0d29f42eda4a59c93c98ef361af6bf81c4eef028')
assert blob('plan/work-items.json') == blob('plan/work-items.json', '994a8b682ed6cd52bb46608b90794c02d2a9d3cb')
assert result['execution_totals']['actual_QR_decodes'] == result['execution_totals']['crypto_key_operations'] == 0
for name, expected, eligible, status in (('red', False, True, 1), ('green', True, False, 0)):
    receipt = doc(D + name + '/regression.json')
    command = doc(D + name + '/command.json')
    assert receipt['passed'] is expected and receipt['observed_eligible'] is eligible and command['exit_code'] == status
    assert receipt['clock_replaced'] is False and receipt['record_mutated_by_probe'] is False
    assert receipt['budget_seconds'] == 8.0 and receipt['actual_pause_seconds'] >= 8.25
    assert receipt['checks']['actual_child_collected_and_IO_settled']
for row in result['case_mapping']:
    assert sha(blob(row['trace_path'])) == row['trace_sha256']
    assert doc(row['trace_path'])['disposition'] == row['disposition'] == 'PASS'
assert len(result['case_mapping']) == 22

Path(__file__).with_name('validation.json').write_text(json.dumps({
    'candidate': NEW, 'tree': git('rev-parse', NEW + '^{tree}').decode().strip(),
    'verdict': 'PASS_AFFECTED_PACKET_PROVENANCE_ONLY', 'reviewer': '/root',
    'checked': {'manifest_members': 263, 'owned_paths': 264, 'added': 113, 'modified': 5,
                'unchanged_prior_paths': 146, 'immutable_prior_run_files': 136,
                'entry_snapshots': 5, 'review_copies': 4, 'new_command_source_summary_bindings': 4,
                'final_recorded_trace_bindings': 22, 'precommitted_expectation_and_probe_exact': True,
                'unchanged_plan_and_original_inputs': True},
    'retained_prior_review': '23d6fb3ba52e84bf160807d238a71c4d01b7e408',
    'runtime_executions_by_this_review': 0,
    'verifier_correction': 'Initial metadata run failed KeyError harness_sha256 on the focused command: all four receipt schemas were then inspected. RED/GREEN probe commands bind harness_sha256 and probe_sha256; focused/stable direct harness commands bind source_sha256. The explicit discriminator is the already recorded non-null probe hash. Both branches still compare the exact executed Git source bytes. No source, case, threshold or historical runtime observation changed.',
    'scope_limit': 'Author RED/GREEN and final22 are checked as recorded source-bound evidence. A02 owns independent affected code review and runtime; no adoption or QR/target/physical/task completion follows.'
}, indent=2) + '\n')
print('PASS: 263 manifest members; 136 prior run files immutable; RED/GREEN and final22 bindings exact. Provenance only; no runtime executed.')
