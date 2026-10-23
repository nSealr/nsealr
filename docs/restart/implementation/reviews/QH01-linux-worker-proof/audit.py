"""Check the frozen author's proof packet; does not execute its worker."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
PREFIX = 'docs/restart/implementation/QH01/linux-worker-experiment/'
CANDIDATE = '31df3027a6e0903d8efa183dd3d4f964ebdf3949'
BASE = 'a94c24e7306c255725dfd080a1b91c38e5d4211e'
OUT = Path(__file__).with_name('validation.json')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def blob(commit, path):
    return git('show', f'{commit}:{path}')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def doc(path):
    return json.loads(blob(CANDIDATE, path))


manifest = doc(PREFIX + 'artifact-manifest.json')
paths = {p.decode() for p in git('ls-tree', '-rz', '--name-only', CANDIDATE, '--', PREFIX).split(b'\0') if p}
members = manifest['artifacts']
assert manifest['member_count'] == len(members) == 150
assert len({m['path'] for m in members}) == 150
assert paths == {m['path'] for m in members} | {PREFIX + 'artifact-manifest.json'}
for item in members:
    data = blob(CANDIDATE, item['path'])
    mode = git('ls-tree', CANDIDATE, '--', item['path']).decode().split()[0]
    assert mode == item['mode'] == '100644'
    assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
changes = [row.split('\t', 1) for row in git('diff', '--name-status', BASE, CANDIDATE).decode().splitlines()]
assert len(changes) == 141
assert sum(status == 'A' for status, _ in changes) == 135
assert sum(status == 'M' for status, _ in changes) == 6
assert all(status in ('A', 'M') and path in paths for status, path in changes)

for name in ('expectations.json', 'parameters.json'):
    assert blob(CANDIDATE, PREFIX + name) == blob('78372015d42efcdf84f3e9996dac5ee7439996a5', PREFIX + name)
assert blob(CANDIDATE, PREFIX + 'strategy-amendment.json') == blob('72dd25ad3df99cf2b154c23c5b7c57829d1ed950', PREFIX + 'strategy-amendment.json')
copies = doc(PREFIX + 'historical-copy-inventory.json')['copies']
assert len(copies) == 5
for copy in copies:
    original = blob(copy['source_commit'], copy['source_path'])
    assert blob(CANDIDATE, copy['target_path']) == original
    assert len(original) == copy['bytes'] and sha(original) == copy['sha256']
    assert git('rev-parse', f"{copy['source_commit']}:{copy['source_path']}").decode().strip() == copy['source_blob']
old = 'edd7ac5fc0cb1688643dedd0c91fd797fa41f076'
old_focus = [p.decode() for p in git('ls-tree', '-rz', '--name-only', old, '--', PREFIX + 'focused-01/').split(b'\0') if p]
assert len(old_focus) == 8
for path in old_focus:
    assert blob(CANDIDATE, path) == blob(old, path)

result = doc(PREFIX + 'result.json')
assert len(result['all_runs']) == 5 and len(result['case_mapping']) == 22
for run in result['all_runs']:
    directory = run['directory'] + '/'
    command = doc(directory + 'command.json')
    summary = doc(directory + 'summary.json')
    assert sha(blob(CANDIDATE, directory + 'command.json')) == run['command_sha256']
    assert sha(blob(CANDIDATE, directory + 'summary.json')) == run['summary_sha256']
    assert command['source_commit'] == run['source_commit']
    assert command['exit_code'] == run['exit_code']
    assert command['source_sha256'] == run['source_sha256'] == sha(blob(run['source_commit'], PREFIX + 'experiment.py'))
    assert len(summary['results']) == run['rows_recorded']
    assert sum(row['disposition'] == 'PASS' for row in summary['results']) == run['rows_pass']
stable = doc(PREFIX + 'stable-01/summary.json')
expected = doc(PREFIX + 'expectations.json')['cases']
extra = doc(PREFIX + 'strategy-amendment.json')['extra_case']
assert set(stable['requested_cases']) == {c['id'] for c in expected} | {extra['id']}
assert len(stable['actual_owned_PIDs']) == 16 and all(row['disposition'] == 'PASS' for row in stable['results'])
for binding in result['case_mapping']:
    trace = doc(binding['trace_path'])
    assert sha(blob(CANDIDATE, binding['trace_path'])) == binding['trace_sha256']
    assert trace['id'] == binding['id'] and trace['disposition'] == binding['disposition']
    assert trace['eligible'] == binding['eligible'] and trace['image_bytes_sent'] == binding['image_bytes_sent']
    assert trace['actual_QR_decode'] is False
    assert all(trace['checks'].values())
    if trace['spawned']:
        assert trace['retained']['stdout'] <= 512 and trace['retained']['stderr'] <= 512
    else:
        assert trace['image_bytes_sent'] == trace['control_bytes_sent'] == 0
        assert trace['owner_wait'] is None and not trace['parent_signals']
env = doc(PREFIX + 'stable-01/environment.json')
for binding in env['source_bindings'].values():
    source = blob(binding.get('commit', CANDIDATE), binding['path'])
    assert sha(source) == binding['sha256']
for binding in env['stdlib_sources'].values():
    assert sha(Path(binding['path']).read_bytes()) == binding['sha256']
assert sha(Path(env['executable_realpath']).read_bytes()) == env['executable_sha256']
assert blob(CANDIDATE, 'plan/work-items.json') == blob('994a8b682ed6cd52bb46608b90794c02d2a9d3cb', 'plan/work-items.json')

OUT.write_text(json.dumps({
    'schema_version': 1,
    'candidate': CANDIDATE,
    'tree': git('rev-parse', CANDIDATE + '^{tree}').decode().strip(),
    'reviewer': '/root',
    'scope': 'Git provenance, manifest, immutable history and recorded trace correspondence only; no worker execution or code/runtime approval',
    'verdict': 'PASS_PACKET_CORRESPONDENCE_ONLY_RUNTIME_REVIEW_SEPARATE',
    'checked': {'manifest_members': 150, 'owned_paths': 151, 'changes_from_readmission': {'A': 135, 'M': 6}, 'original_focused_files': 8,
                'historical_metadata_copies': 5, 'command_summary_source_bindings': 5,
                'stable_recorded_rows': 22, 'recorded_owned_children': 16,
                'frozen_expectations_parameters_amendment_exact': True,
                'R00_public_fixture_stdlib_executable_hashes_exact': True,
                'plan_byte_identical_to_actual_main': True},
    'independent_worker_executions': 0,
    'verifier_corrections': [
        'First metadata-only invocation failed at scope assertion: it incorrectly expected all 151 final paths to be additions against a94, which already contains 16 original experiment paths. Actual git diff is 135 additions and six modifications, all inside the owned prefix; ten prior files remain unchanged. Manifest membership remains independently checked at 150 plus itself.',
        'Second metadata-only invocation reached trace checks and failed KeyError retained: six no-spawn refusal traces intentionally have no stream-retention fields. Inspected every affected trace; validate zero control/image bytes, no status and no signals on this branch. Spawned traces retain the <=512 stream checks. No product code, threshold or case changed.'
    ],
    'limitations': ['Author 22 PASS rows are recorded historical observations, not independent acceptance.',
                    'Known blocking independent code finding QH-WORKER-RUNTIME-01 prevents adoption; see distinct runtime review.']
}, indent=2) + '\n')
print('PASS packet correspondence: 150 members; 151 owned paths; immutable history exact; 22 recorded rows. No worker executed; runtime adoption blocked separately.')
