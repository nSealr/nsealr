"""Inspect already-collected independent and original author evidence; no rerun."""
import base64
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
RUN = HERE / '.runtime/cancel-preG-01'
PACK = ROOT / 'docs/restart/implementation/QH01/manual-port/python-rgb-composition/proof/lifecycle-cases'


def read(path):
    return json.loads(path.read_bytes())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    preflight = read(HERE / 'preflight.json'); command = read(RUN / 'command.json'); case = RUN / 'composition'
    result = read(case / 'result.json'); collection = read(case / 'collection.json'); ready = read(case / 'worker-ready.json')
    settled = read(case / 'owner-settled.json')['observation']; rows = read(case / 'node-records.json')
    o = collection['B3']; p = o['phase']; t = o['terminal']; wait = t['worker_wait']
    ids = [result[k] for k in ['parent_pid', 'node_pid', 'owner_pid', 'worker_pid']]
    assert len(set(ids)) == 4 and all(type(pid) is int and pid > 1 for pid in ids)
    assert command['invoker_pid'] == result['parent_pid'] and command['exit_code'] == command['invoker_wait_raw'] == 0
    assert command['after_actual_collection_ECHILD'] is True and command['source_after'] == command['reuse_source_after'] == ''
    assert command['outer_watchdog'] is None and command['argv'][-2:] == ['--case', 'fixture_cancel_B3_verified_preG']
    assert result['result'] == 'PASS_HOST_COMPOSITION_LIFECYCLE_CASE' and result['physical_claim'] is False
    assert result['worker_sha256'] == preflight['actual_worker_producer']['sha256'] == p['exe_sha256']
    assert p == ready['observation']['phase'] and ready['observation']['state'] == 'verified-worker-ready'
    assert p['owner_pid'] == p['ppid'] == result['owner_pid'] == o['owner_pid'] == t['owner_pid']
    assert p['worker_pid'] == p['sid'] == p['pgid'] == t['worker_pid'] == result['worker_pid']
    assert p['limits'] == {'AS': [268435456, 268435456], 'CPU': [1, 2], 'CORE': [0, 0]}
    assert p['G_bytes'] == p['image_bytes_sent'] == 0 and [f['fd'] for f in p['fds']] == [0, 1, 2]
    identities = {(f['dev'], f['ino']) for f in p['fds']}
    assert len(identities) == 3 and identities.isdisjoint({(f['dev'], f['ino']) for f in o['pipe_identities']})
    for f in p['fds']:
        assert str(int(f['dev'])) == f['dev'] and str(int(f['ino'])) == f['ino'] and f['target'] == 'pipe:[' + f['ino'] + ']'
    proc_status = dict(line.split(':', 1) for line in ready['proc_status'].splitlines() if ':' in line)
    assert int(proc_status['Pid']) == result['worker_pid'] and int(proc_status['PPid']) == result['owner_pid']
    assert o['state'] == settled['state'] == 'settled' and o['closed'] is settled['closed'] is True
    assert o['taken'] is settled['taken'] is False and o['fault'] is o['transport_error'] is None
    assert o['owner_exit_code'] == 2 and o['owner_wait_raw'] == 512
    assert (wait['exit_code'], wait['raw_status']) in [(71, 18176), (-9, 9)] and wait['collector_pid'] == result['owner_pid']
    assert t['outcome'] == 'cancelled' and t['cancel_observed'] is True and t['ownership'] == 'settled'
    assert t['session_policy_verified'] is True and t['final_worker_eligible'] is False
    assert all(v is True for v in t['worker_io'].values())
    assert o['commands'] == ['P', 'X'] and t['G_bytes'] == t['image_bytes_sent'] == t['result_bytes'] == o['output_bytes'] == 0
    assert t['stdout_observed'] == t['stdout_retained'] == t['stderr_observed'] == t['stderr_retained'] == 0
    assert t['input_bytes_received'] == 172800 and t['input_sha256'] == '64d9be602c821c31c0dfd6e952199a328325acdbf9a7e1b3494921942a11055f'
    assert o['EOF'] == [1, 2, 4, 5] and o['parent_owned_fds'] == [] and o['ready_hex'] == '52'
    timing = {k: int(v) for k, v in t['timing'].items()}
    assert timing['cleanup_deadline_ns'] - timing['invalidated_ns'] == 4000000000
    assert timing['begin_ns'] <= timing['invalidated_ns'] <= timing['settled_ns'] <= timing['final_admission_ns'] < timing['cleanup_deadline_ns']
    assert [json.loads(line) for line in base64.b64decode(o['status_wire_base64'], validate=True).splitlines()] == [p, t]
    assert collection['node_wait_raw'] == 0 and collection['node_pid'] == result['node_pid']
    assert collection['node_EOF'] == ['stderr', 'stdout'] and collection['node_observed'] == {'stdout': 923, 'stderr': 0}
    assert collection['runtime_strong_reference'] is True and collection['parent_fd_before'] == collection['parent_fd_after'] == [0, 1, 2]
    assert read(case / 'cancel-refusals.json') == {'take_result_refused': True, 'reservation_before_close_refused': True, 'caller_released_bytes': 0}
    assert (case / 'parent-reply.jsonl').read_bytes() == b'{"v":1,"event":"cancelled"}\n'
    assert [r['event'] for r in rows] == ['present', 'close', 'result'] and all(type(r['v']) is int and r['v'] == 1 for r in rows)
    assert rows[0]['timer_args'] == [100] and rows[0]['clock'] == 99 and len(rows[0]['frame']) == 259
    final = rows[-1]; life = final['lifecycle']
    assert final['timer_args'] == [100] and final['clear_calls'] == 1 and final['deadline_fires'] == 0 and final['clock_steps'] == [0, 99, 100]
    assert life == {'case': 'fixture_cancel_B3_verified_preG', 'opens': 1, 'scans': 0, 'closes': 1, 'abort_observed': True,
                    'underlying_settled': True, 'late_scan_bytes': 0, 'late_scan_sha256': None, 'pending_retry_error': None}
    wire = (case / 'native-response.bin').read_bytes(); assert base64.b64decode(final['native_response_base64'], validate=True) == wire
    assert int.from_bytes(wire[:4], 'little') == len(wire) - 4
    service = read(case / 'service-response.json'); assert json.loads(wire[4:]) == service
    assert service['ok'] is False and service['request_id'] == 'qh01.composition' and service['error']['code'] == 'signer_transport_failed' and 'result' not in service
    assert not (case / 'decoded.envelope').exists() and not (case / 'decoded.json').exists() and not (case / 'attention.json').exists()
    assert not (RUN / 'stderr.log').read_bytes() and not (case / 'node.stderr').read_bytes()
    assert all(not Path('/proc/' + str(pid)).exists() for pid in ids)
    for path, digest in preflight['runtime_source60'].items(): assert sha((ROOT / path).read_bytes()) == digest
    reuse = Path(preflight['same_root_for_bridge_and_packages'])
    for path, digest in preflight['prepared_generated62'].items(): assert sha((reuse / path).read_bytes()) == digest
    assert sha(Path(preflight['actual_worker_producer']['worker']).read_bytes()) == result['worker_sha256']
    original = []
    with tarfile.open(PACK / 'early.tar.gz') as archive:
        for name in ['scan_null_after_settlement', 'scan_pending_timeout_after_settlement', 'fixture_cancel_B3_verified_preG']:
            get = lambda f: json.load(archive.extractfile(name + '/' + f))
            c, rs = get('collection.json'), get('node-records.json'); observation = c['B3']
            assert c['node_wait_raw'] == 0 and c['node_EOF'] == ['stderr', 'stdout'] and c['parent_fd_before'] == c['parent_fd_after'] == [0, 1, 2]
            assert observation['closed'] is True and observation['EOF'] == [1, 2, 4, 5] and observation['parent_owned_fds'] == []
            if name.startswith('scan_'):
                assert observation['owner_wait_raw'] == observation['terminal']['worker_wait']['raw_status'] == 0 and observation['taken'] is True
                assert archive.extractfile(name + '/decoded.envelope').read() == (ROOT / 'docs/restart/implementation/QH01/native-qr-probe/expected/request-kind-1-basic.envelope').read_bytes()
            if name == 'scan_pending_timeout_after_settlement':
                assert [r['event'] for r in rs] == ['present', 'scan_pending', 'timeout', 'close', 'result']
                assert rs[2]['closes'] == 0 and rs[2]['underlying_settled'] is False and rs[2]['abort_observed'] is True
                assert rs[2]['pending_retry_error'] == 'runtime_unavailable' and rs[2]['native_response_base64'] == rs[-1]['native_response_base64']
                assert rs[-1]['lifecycle']['closes'] == 1 and rs[-1]['lifecycle']['underlying_settled'] is True and rs[-1]['lifecycle']['late_scan_bytes'] == 611
            if name == 'scan_null_after_settlement': assert rs[1]['frame'] is None and rs[-1]['lifecycle']['closes'] == 1
            original.append({'case': name, 'events': [r['event'] for r in rs], 'O_raw': observation['owner_wait_raw'], 'W_wait': observation['terminal']['worker_wait']})
    consumer = ROOT.parent / 'qh01-python-rgb-lifecycle-runtime-2026-10-24/root-consumer'
    receipt, controls = read(consumer / 'receipt.json'), read(consumer / 'current-default-controls.json')
    assert receipt['exit_code'] == 0 and receipt['log_sha256'] == controls['log_sha256'] == preflight['normal_log_sha256']
    assert controls['source_head'] == preflight['normal_source'] and len(controls['negative_controls']) == 27 and all(r['rejected'] for r in controls['negative_controls'])
    assert controls['checker_sha256'] == sha((ROOT / 'docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py').read_bytes())
    (HERE / 'reused-consumer').mkdir(exist_ok=True)
    for source, target in [('receipt.json', 'receipt.json'), ('current-default-controls.json', 'controls.json')]:
        (HERE / 'reused-consumer' / target).write_bytes((consumer / source).read_bytes())
    verified = {'role': 'Post-run read-only receipt verification, no new execution', 'candidate': preflight['candidate'],
                'wrapper_source': command['wrapper_source'], 'invoker_wait_raw': command['invoker_wait_raw'], 'exit_code': command['exit_code'],
                'elapsed_seconds_bookkeeping_only': command['elapsed_seconds_bookkeeping_only'], 'PIDs': dict(zip(['Python', 'Node', 'O', 'W'], ids)),
                'O_exit_raw': [o['owner_exit_code'], o['owner_wait_raw']], 'W_wait': wait, 'actual_wait_then_ECHILD': True,
                'current_worker_sha256': result['worker_sha256'], 'session_limits_FD_identity_checked': True,
                'O_received_RGB': t['input_bytes_received'], 'G_bytes': 0, 'W_image_bytes': 0, 'result_API_bytes': 0,
                'closed_settled_receipt_precedes_reply_in_frozen_source': True, 'cancel_reply_bytes': 28,
                'service_error': service['error']['code'], 'node_records': 3, 'node_stdout_bytes': 923,
                'timer_argument_clear_fires': [100, 1, 0], 'scan_close_counts': [0, 1], 'EOF_FDs_restored': True,
                'four_collected_PIDs_absent_after_known_wait': True, 'post_run_inputs_unchanged': True,
                'original_author_case_receipts_verified': original, 'root_default_consumer_reused_not_rerun': {'source': controls['source_head'], 'log_sha256': controls['log_sha256'], 'controls': 27},
                'negative_cases_automatically_in_normal_CI': False, 'new_build_install_positive_or_full_gate': 0}
    (HERE / 'verification.json').write_text(json.dumps(verified, indent=2) + '\n')
    print(json.dumps({'evidence': 'PASS', 'PIDs': verified['PIDs'], 'O_raw': 512, 'W_raw': wait['raw_status'], 'bytes_to_W': 0, 'API_bytes': 0}))


if __name__ == '__main__':
    main()
