"""Read immutable Git objects and retained proof bytes only; execute no product/checker."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
BASE = '7f584568b667c50b3171a0f3a60f5824c4bb6ef9'
HEAD = '9e903bc9d484310769db844a2ad1e0bba370723e'
PREFIX = 'docs/restart/implementation/reviews/QH01-python-rgb-lifecycle-integration/'
PACKET = PREFIX + 'local-full-qualified/'
ORIGINAL = Path('/home/tux/nsealr/.restart-tools/goal/qh01-python-rgb-lifecycle-ci-runtime-2026-10-24/root-stable-gate-02')

def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, stdout=subprocess.PIPE).stdout

def blob(ref, path):
    return git('cat-file', 'blob', ref + ':' + path)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(ref, path):
    return json.loads(blob(ref, path))

def tree(ref, path):
    return git('ls-tree', '-r', '--full-tree', ref, '--', path)

changed = git('diff', '--name-only', BASE, HEAD).decode().splitlines()
metadata = ['docs/restart/README.md', 'docs/restart/implementation/handoff.md', PREFIX + 'README.md', 'plan/work-items.json']
proof_names = ['artifact-manifest.json', 'full-oracle-controls.json', 'full-source-addon.json', 'original-full-and-source-proof.tar.gz', 'original-full-result.json', 'result.json']
assert set(changed) == set(metadata + [PACKET + p for p in proof_names])
bindings = []
for path in changed:
    before = tree(BASE, path)
    data = blob(HEAD, path)
    bindings.append({'path': path, 'base_tree_entry': before.decode().strip() or None,
                     'candidate_tree_entry': tree(HEAD, path).decode().strip(),
                     'bytes': len(data), 'sha256': sha(data)})
manifest = read(HEAD, PACKET + 'artifact-manifest.json')
assert manifest['members_count'] == len(manifest['members']) == 5
assert {r['path'] for r in manifest['members']} == {PACKET + p for p in proof_names if p != 'artifact-manifest.json'}
for row in manifest['members']:
    data = blob(HEAD, row['path'])
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
archive_path = ROOT / PACKET / 'original-full-and-source-proof.tar.gz'
archive = {}
original_bindings = []
with tarfile.open(archive_path) as tar:
    members = tar.getmembers()
    assert len(members) == len({m.name for m in members}) == 21
    for member in members:
        assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
        data = tar.extractfile(member).read()
        original = ORIGINAL / member.name
        assert original.is_file() and data == original.read_bytes()
        disk_mode = stat.S_IMODE(original.stat().st_mode)
        assert member.mode == 0o644 and disk_mode == 0o664
        archive[member.name] = data
        original_bindings.append({'member': member.name, 'bytes': len(data), 'sha256': sha(data),
                                  'archive_mode': '0644', 'original_disk_mode': '0664',
                                  'non_executable_Git_mode': '100644', 'original_bytes_exact': True})
for public, inner in [('full-source-addon.json', 'full-source-addon.json'), ('full-oracle-controls.json', 'full-oracle-controls.json'), ('original-full-result.json', 'evidence/suites/result.json')]:
    assert blob(HEAD, PACKET + public) == archive[inner]
log = archive['evidence/suites/00-product-ci.log']
log_sha = '74fdfa39543042c95e2f951a114df26e3370b7436e5f2026bf74366635e4c2b0'
assert len(log) == 854254 and sha(log) == log_sha
commands = json.loads(archive['evidence/suites/commands.json'])
assert len(commands) == 1
command = commands[0]
assert command['argv'] == ['make', '-k', 'ci'] and type(command['exit_code']) is int and command['exit_code'] == 0 and command['sha256'] == log_sha
elapsed = (datetime.datetime.fromisoformat(command['ended']) - datetime.datetime.fromisoformat(command['started'])).total_seconds()
assert elapsed == 340.588173
original_result = json.loads(archive['evidence/suites/result.json'])
assert original_result == {'input_commits': {'nsealr': BASE}, 'mode': 'full', 'failed_commands': [], 'commands_sha256': sha(archive['evidence/suites/commands.json']), 'source_changed_after': [], 'all_passed': True}
assert json.loads(archive['source-commits.json']) == {'nsealr': BASE}
assert json.loads(archive['source-state.json']) == {'nsealr': {'status': '', 'diff_sha256': sha(b'')}}
for name in ['evidence/suites/source-before.json', 'evidence/suites/source-after.json']:
    assert json.loads(archive[name]) == {'nsealr': ''}
module = ast.parse(blob(BASE, 'tests/integration/run.py'))
steps = next(ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign) and any(isinstance(v, ast.Name) and v.id == 'PRODUCT_STEPS' for v in n.targets))
assert len(steps) == 17
expected_markers = [f'[{i}/17 original {original}] {name}' for i, (original, name) in enumerate(steps, 1)]
markers = [line for line in log.decode().splitlines() if re.fullmatch(r'\[\d+/17 original \d+\] \w+', line)]
assert markers == expected_markers
assert log.rstrip().endswith(b'All 17 retained product integration steps passed. External hardware and optional physical resources are separate.')
addon = read(HEAD, PACKET + 'full-source-addon.json')
assert addon['source_head'] == BASE and addon['product_log_sha256'] == log_sha and addon['run'] is None
assert addon['proof_role'] == 'local_makeci_source_addon_no_GitHub_claim'
assert addon['generic_completed_capture_checker_remains_separately_mandatory'] is True
for name in ['source-addon', 'full-oracle-controls']:
    receipt = json.loads(archive[name + '-receipt.json'])
    invocation = json.loads(archive[name + '-command.json'])
    assert receipt['exit_code'] == 0 and receipt['new_product_processes'] == 0
    assert invocation['source'] == BASE and invocation['log_sha256'] == log_sha and invocation['product_replay'] is False
    assert archive[name + '.stderr'] == b''
controls = read(HEAD, PACKET + 'full-oracle-controls.json')
checker_path = 'docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py'
control_path = 'docs/restart/implementation/reviews/QH01-python-rgb-composition/test_capture_extension.py'
assert controls['checker_sha256'] == sha(blob(BASE, checker_path)) == '4b66f6242f2fed02eb2da923396d2ecf9b4f697c55edd6068a920003e4eef36f'
assert controls['control_source_sha256'] == sha(blob(BASE, control_path))
assert controls['source_head'] == controls['checker_commit'] == BASE
assert controls['log_sha256'] == log_sha and controls['log_bytes'] == len(log)
assert len(controls['negative_controls']) == len({r['name'] for r in controls['negative_controls']}) == 32
assert all(r['rejected'] is True for r in controls['negative_controls']) and controls['new_product_processes'] == 0
for group in [addon['native_build']['source'], addon['worker_build']['source'], addon['python_owner_source_bindings']]:
    for path, digest in group.items():
        assert sha(blob(BASE, path)) == sha(blob(HEAD, path)) == digest
assert len(addon['audit_commands']) == 6 and addon['three_complete_fresh_audits'] is True
text = log.decode()
for value in addon['audit_commands']:
    assert text.splitlines().count(value) == 1
assert text.splitlines().count('advisories ok, bans ok, licenses ok, sources ok') == 3
coverage = {}
for line in text.splitlines():
    match = re.fullmatch(r'(desktop-simulator|nsealr-core|nsealr-pi-engine-fixture)\s+(\d+\.\d+)%\s+(\d+\.\d+)%\s+ok', line)
    if match:
        coverage[match[1]] = [float(match[2]), float(match[3])]
assert coverage == {'desktop-simulator': [77.69, 76.7], 'nsealr-core': [100.0, 100.0], 'nsealr-pi-engine-fixture': [100.0, 100.0]}
a = read(BASE, 'plan/work-items.json'); b = read(HEAD, 'plan/work-items.json')
assert len(a['tasks']) == len(b['tasks']) == 47
assert {k:v for k,v in a.items() if k != 'tasks'} == {k:v for k,v in b.items() if k != 'tasks'}
changed_tasks = []
for old, new in zip(a['tasks'], b['tasks']):
    assert old['id'] == new['id']
    if old != new:
        changed_tasks.append(old['id'])
        allowed = {'current_checkpoint'} | ({'result_artifacts'} if old['id'] == 'QH01' else set())
        assert {k:v for k,v in old.items() if k not in allowed} == {k:v for k,v in new.items() if k not in allowed}
        if old['id'] == 'QH01':
            assert new['result_artifacts'][:-1] == old['result_artifacts']
            assert new['result_artifacts'][-1] == {'path': PACKET + 'artifact-manifest.json', 'sha256': sha(blob(HEAD, PACKET + 'artifact-manifest.json'))}
assert changed_tasks == ['R00', 'QH01']
red_prefix = PREFIX + 'local-full-security-red'
assert tree(BASE, red_prefix) == tree(HEAD, red_prefix)
with tarfile.open(ROOT / red_prefix / 'original-full-and-scoped-proof.tar.gz') as tar:
    assert len(tar.getmembers()) == 13
    failed_result = json.loads(tar.extractfile('evidence/suites/result.json').read())
    assert failed_result['input_commits'] == {'nsealr':'5e17f9a957137c7d856f12bc08f5f795d3f858d8'} and failed_result['all_passed'] is False
for path in [checker_path, control_path, 'Makefile', 'ci/ratchet.json', 'deny.toml', 'scripts/audit_rust.py', 'tools/baseline/run.py']:
    assert tree(BASE, path) == tree(HEAD, path)
result = {'candidate': HEAD, 'candidate_tree': git('rev-parse', HEAD + '^{tree}').decode().strip(),
          'compared_source': BASE, 'verdict': 'PASS_BOUNDED_DOCUMENTARY_TAIL_AND_ORIGINAL_LOCAL_FULL_PROOF_BINDING_ONLY',
          'changed_paths': bindings, 'metadata_paths': len(metadata), 'proof_paths': len(proof_names),
          'manifest_members': 5, 'archive_original_members': original_bindings,
          'archive_mode_note': 'Canonical archive0644 vs actual retained disk0664; both map to non-executable Git100644. Byte identity is exact; full POSIX-mode identity is not claimed.',
          'original_log_bytes': len(log), 'original_log_sha256': log_sha, 'elapsed_seconds': elapsed,
          'original_product_command_exit': 0, 'original_source_clean_before_after': True,
          'source_derived_original17_markers_exact': expected_markers,
          'source_addon_and32_controls': 'Original receipts/source/log-bound; not re-executed by reviewer',
          'current_fresh_audit_graphs': 3, 'fresh_audit_limit': 'Existing temporary fresh-data acquisition; no retained DB snapshot or discovery-snapshot identity inferred',
          'coverage_measured_and_floors': coverage, 'formal47_unchanged': True, 'other45_task_records_exact': True,
          'changed_task_evidence_only': changed_tasks, 'historical_failed5e17_archive13_and_prefix_exact': True,
          'all_runtime_vendor_and_gate_files_exact_to_executed_source': True,
          'reviewer_product_build_test_audit_checker_or_hosted_replays': 0}
(OUT / 'checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'candidate': HEAD, 'paths': len(changed), 'archive_originals': 21, 'formal_tasks':47, 'verdict':result['verdict']}))
