"""Read-only assertions over this review's one six-case campaign; no worker run."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SOURCE = ROOT / 'docs/restart/implementation/QH01/rgb-input'
load = lambda p: json.loads(p.read_text())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
expected = load(SOURCE / 'expectations.json')['cases']
summary = load(HERE / 'stable-6/summary.json')
context = load(HERE / 'stable-6/environment.json')
binary = load(HERE / 'binary-context.json')
command = load(HERE / 'campaign-command.json')
preflight = load(HERE / 'source-validation.json')
assert command['exit_code'] == 0
assert summary['passed'] and not summary['not_exercised']
assert [c['id'] for c in summary['cases']] == [c['id'] for c in expected]
assert expected[0]['id'] == 'tinted-response-get-public-key'
assert context['binary_path'] == binary['binary_path'] == command['binary_path']
assert context['binary_sha256'] == binary['binary_sha256'] == digest(Path(binary['binary_path']))
assert context['controller_sha256'] == digest(SOURCE / 'controller.py') == command['controller_sha256']
assert context['executable_sha256'] == binary['python']['sha256'] == digest(Path(binary['python']['path']))
assert context['threads'] == summary['actual_final_threads'] == 1
assert context['uid'] == context['euid'] == 1000 and int(context['CapEff'], 16) == 0
assert not binary['setuid_setgid_bits']
for key in ['all_created_PIDs_collected', 'FDs_equal_initial', 'parent_identity_unchanged', 'parent_limits_unchanged']:
    assert summary[key]
rows = []
for generation, case in enumerate(expected, 1):
    name = case['id']
    trace_path = HERE / 'stable-6' / (name + '.json')
    r = load(trace_path)
    out_path = HERE / 'stable-6' / (name + '.stdout.bin')
    err_path = HERE / 'stable-6' / (name + '.stderr.bin')
    out, err = out_path.read_bytes(), err_path.read_bytes()
    pid = r['pid']
    assert r['passed'] and all(r['checks'].values()) and 'harness_error' not in r
    assert r['argv'] == [binary['binary_path']]
    assert r['input_sha256'] == case['image_sha256']
    assert r['input_in_memory'] == (generation == 1)
    assert r['owner_generation'] == generation and not r['owner_quarantined']
    assert r['actual_status_acquired'] and r['parent_FDs_restored'] and r['callbacks_settled']
    assert r['second_refusals'] == ['live-child', 'status-before-IO-settlement']
    assert r['signals'] == []
    assert r['control_bytes'] == 1 and r['image_bytes'] == 172800
    assert r['identity_checks_before_writes'] == 44
    assert r['kernel_identity'] == {'pid': pid, 'sid': pid, 'pgid': pid}
    assert pid > 1 and pid != context['parent_pid'] and pid != context['parent_pgid']
    assert r['bootstrap_VmSize_bytes'] < 268435456
    for key, value in {'0': [1, 2], '4': [0, 0], '9': [268435456, 268435456]}.items():
        assert r['policy'][key]['requested'] == r['policy'][key]['readback'] == value
    ev = r['events']
    names = [e['event'] for e in ev]
    assert names == ['spawn-begin', 'spawn-return', 'kernel-session-established', 'policy-readback-before-G', 'G-sent', 'first-image-write', 'actual-wait', 'settled']
    assert ev[2]['pid'] == ev[2]['sid'] == ev[2]['pgid'] == pid
    assert all(a['t'] <= b['t'] for a, b in zip(ev, ev[1:]))
    assert ev[-1]['known'] and ev[-1]['t'] <= r['admission_elapsed_seconds'] < 8
    assert r['duration_seconds'] >= r['admission_elapsed_seconds']
    assert r['max_write_chunk'] == 4096 and r['max_read_chunk'] <= 4096
    assert r['stdout_observed'] == r['stdout_retained'] == len(out) <= 512
    assert r['stderr_observed'] == r['stderr_retained'] == len(err) <= 512
    if case['expected'] == 'exact':
        original = ROOT / case['expected_path']
        assert out == original.read_bytes() and digest(out_path) == case['expected_sha256']
        assert err == ('status=decoded grids=1 bytes=' + str(len(out)) + '\n').encode()
        exitcode = 0
        assert r['eligible']
    elif case['expected'] == 'output-overflow':
        assert not out and err == b'status=output_overflow retained=512 limit=512 refused_chunk=1\n'
        exitcode = 42
        assert not r['eligible']
    else:
        assert case['expected'] == 'no-qr'
        assert not out and err == b'status=no_qr grids=0\n'
        exitcode = 20
        assert not r['eligible']
    assert r['owner_wait']['pid'] == pid
    assert r['owner_wait']['exitcode'] == exitcode
    assert r['owner_wait']['raw_status'] == ev[-2]['status'] == exitcode * 256
    assert not Path('/proc', str(pid)).exists()
    rows.append({'id': name, 'pid': pid, 'owner_generation': generation, 'input_in_memory': r['input_in_memory'],
                 'input_sha256': r['input_sha256'], 'output_bytes': len(out), 'stdout_sha256': digest(out_path),
                 'stderr_bytes': len(err), 'stderr_sha256': digest(err_path), 'exitcode': exitcode,
                 'trace_sha256': digest(trace_path), 'initial_kernel_identity': r['initial_kernel_identity'],
                 'established_kernel_identity': r['kernel_identity'], 'admission_elapsed_seconds': r['admission_elapsed_seconds'],
                 'actual_wait_raw_status': r['owner_wait']['raw_status'], 'PID_absent_at_check': True,
                 'checks_independently_asserted': True})
assert len(set(summary['owned_PIDs'])) == 6
assert summary['owned_PIDs'] == [r['pid'] for r in rows]
assert not Path('/proc', str(command['controller_pid'])).exists()
input_rows = []
for row in preflight['source_hashes']:
    assert digest(ROOT / row['path']) == row['sha256']
    input_rows.append(dict(row, unchanged_after=True))
for row in preflight['toolchain_files'] + preflight['config_bindings']:
    assert digest(Path(row['path'])) == row['sha256']
changed = subprocess.run(['git', 'diff', '--name-only', preflight['candidate_commit'], '--'], cwd=ROOT, capture_output=True, check=True)
assert changed.stdout == b''
image_files = sorted(str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p.suffix.lower() in ['.rgb', '.png', '.jpg', '.jpeg'])
archive_images = load(HERE / 'postprocess-observation.json')['allowed_preexisting_archive_images']
assert image_files == sorted(row['path'] for row in archive_images)
for row in archive_images:
    assert digest(HERE / row['path']) == row['sha256']
new_image_files = []
proof = {'schema_version': 1, 'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'role': 'Post-run assertions over six recorded traces; no additional worker/build/corpus campaign',
         'campaign_count': 1, 'cases': rows, 'all_six_passed': True,
         'controller_PID_absent_at_check': True, 'all_six_owned_PIDs_absent_at_check': True,
         'source_hashes_after': input_rows, 'toolchain_and_workspace_config_unchanged': True,
         'tracked_diff_from_candidate_before_review_staging': [], 'new_saved_image_files_under_review': new_image_files,
         'preexisting_images_extracted_by_Cargo': archive_images,
         'baseline13_plus_CORE0_unchanged': True, 'all_parent_identity_FD_limit_checks_pass': True,
         'initial_inherited_SID_PGID_not_used_as_ready': True,
         'all_session_policy_G_image_wait_settlement_admission_orders_asserted': True,
         'owned_reuse_generations': [1, 2, 3, 4, 5, 6],
         'binary_binding_scope': 'Hash-bound built ELF path is passed to unchanged posix_spawn; each actual trace argv and context match. No /proc/exe or syscall trace claim.',
         'final_clock_scope': 'Logical admission sampled after status/IO settlement, not a hard real-time return guarantee.',
         'writer_cap_scope': 'Actual stderr retained512/refused_chunk1 and zero stdout agree with unchanged reviewed fixed-array writer source; no RSS/allocation bound inferred.',
         'passed': True}
(HERE / 'runtime-validation.json').write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps({'passed': True, 'cases': len(rows), 'source_inputs_unchanged': len(input_rows), 'old_campaigns_rerun': 0}))
