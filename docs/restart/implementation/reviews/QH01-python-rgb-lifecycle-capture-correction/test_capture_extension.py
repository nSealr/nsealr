"""Pure controls on one original pi-ci log, without product replay.

Usage: python3 -B test_capture_extension.py LOG SOURCE_HEAD REPO OUTPUT.json
The existing positive source/build block must pass before the new block is tested.
"""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys


def main():
    log, head, repo, output = sys.argv[1:]
    source = Path(repo) / 'docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py'
    spec = importlib.util.spec_from_file_location('lifecycle_capture', source)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    raw = Path(log).read_bytes()
    lines = [re.sub(r'^\d{4}-\d\d-\d\dT\S+Z ?', '', line) for line in raw.decode().splitlines()]
    objects = []
    decoder = json.JSONDecoder()
    for i, line in enumerate(lines):
        if line.startswith('{'):
            try:
                value, _ = decoder.raw_decode('\n'.join(lines[i:]))
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                objects.append(value)
    workers = [o for o in objects if o.get('role') == 'public RGB worker build, initialization v2, not hardware qualification']
    assert len(workers) == 1
    positive = checker.verify_qh01_composition(objects, lines, workers[0], head, repo)
    lifecycle = checker.verify_qh01_lifecycle(objects)
    controls = []

    def reject(name, change):
        rows = copy.deepcopy(objects)
        change(rows)
        try:
            checker.verify_qh01_lifecycle(rows)
        except (AssertionError, KeyError, ValueError, TypeError):
            controls.append({'name': name, 'rejected': True})
        else:
            raise AssertionError('checker accepted mutated evidence: ' + name)

    def case(rows, index=0):
        return [o['qh01_lifecycle_case'] for o in rows if 'qh01_lifecycle_case' in o][index]

    def actual(rows, key, value, index=0):
        c = case(rows, index)
        c['actual'][key] = value
        next(o['qh01_lifecycle_result'] for o in rows if 'qh01_lifecycle_result' in o and o['qh01_lifecycle_result']['case'] == c['id'])[key] = value

    def terminal(rows, key, value, index=0):
        c = case(rows, index)
        b = c['collection']['B3']
        b['terminal'][key] = value
        # Keep the actual status-wire cross-binding intact, testing semantics.
        b['status_wire_base64'] = base64.b64encode(b''.join((json.dumps(o, separators=(',', ':')) + '\n').encode('ascii') for o in [b['phase'], b['terminal']])).decode('ascii')

    def phase(rows, key, value):
        b = case(rows)['collection']['B3']
        b['phase'][key] = value
        terminal(rows, 'outcome', b['terminal']['outcome'])

    def status(rows, transform):
        b = case(rows)['collection']['B3']
        b['status_wire_base64'] = base64.b64encode(transform(base64.b64decode(b['status_wire_base64']))).decode('ascii')

    def cancel_stderr(rows):
        terminal(rows, 'stderr_observed', 1, 2)
        terminal(rows, 'stderr_retained', 1, 2)
        terminal(rows, 'worker_stderr_base64', base64.b64encode(b'x').decode('ascii'), 2)

    for key in ['qh01_lifecycle_command', 'qh01_lifecycle_result', 'qh01_lifecycle_case']:
        reject('missing ' + key, lambda rows, key=key: rows.__setitem__(slice(None), [r for r in rows if key not in r]))
        reject('duplicate ' + key, lambda rows, key=key: rows.append(copy.deepcopy(next(r for r in rows if key in r))))
    def reorder(rows):
        indices = [i for i, o in enumerate(rows) if 'qh01_lifecycle_case' in o]
        rows[indices[0]], rows[indices[1]] = rows[indices[1]], rows[indices[0]]
    reject('case order reversed', reorder)
    reject('reported lifecycle failure', lambda rows: rows.append({'qh01_lifecycle_failure': {'v': 1}}))
    reject('stale source', lambda rows: case(rows)['source_after'].__setitem__(next(iter(case(rows)['source_after'])), '0' * 64))
    reject('foreign generated dependency', lambda rows: case(rows)['generated_before'].__setitem__(next(iter(case(rows)['generated_before'])), '0' * 64))
    reject('changed worker', lambda rows: case(rows)['worker_initialization'].__setitem__('sha256', '0' * 64))
    reject('unbound original result', lambda rows: case(rows)['actual'].__setitem__('presented_bytes', 258))
    reject('PID bool', lambda rows: actual(rows, 'parent_pid', True))
    reject('null scan releases bytes', lambda rows: actual(rows, 'scanned_bytes', 611))
    reject('cancel claims released request', lambda rows: actual(rows, 'caller_released_bytes', 259, 2))
    reject('timeout claims successful scan', lambda rows: case(rows, 1)['frames'].__setitem__('scanned', copy.deepcopy(case(rows, 1)['frames']['late_scan'])))
    reject('missing late response', lambda rows: case(rows, 1)['frames'].__setitem__('late_scan', None))
    reject('missing cancel refusal', lambda rows: case(rows, 2)['cancel_refusals'].__setitem__('take_result_refused', False))
    reject('missing actual Node wait', lambda rows: case(rows)['collection'].__setitem__('node_wait_raw', None))
    reject('missing Node EOF', lambda rows: case(rows)['collection']['node_EOF'].pop())
    reject('unrestored parent FD', lambda rows: case(rows)['collection']['parent_fd_after'].append(9))
    reject('O wait not collected', lambda rows: case(rows)['collection']['B3'].__setitem__('owner_wait_raw', None))
    reject('W collector is parent', lambda rows: terminal(rows, 'worker_wait', {**case(rows)['collection']['B3']['terminal']['worker_wait'], 'collector_pid': case(rows)['actual']['parent_pid']}))
    reject('cancel sends G', lambda rows: terminal(rows, 'G_bytes', 1, 2))
    reject('cancel gives W image', lambda rows: terminal(rows, 'image_bytes_sent', 172800, 2))
    reject('G bool', lambda rows: terminal(rows, 'G_bytes', True))
    reject('worker stderr hidden', lambda rows: terminal(rows, 'stderr_observed', 1))
    reject('status wire unbound', lambda rows: case(rows)['collection']['B3'].__setitem__('status_wire_base64', base64.b64encode(b'{}\n').decode('ascii')))
    reject('late B3 admission', lambda rows: case(rows)['collection']['B3']['terminal']['timing'].__setitem__('final_admission_ns', str(int(case(rows)['collection']['B3']['terminal']['timing']['begin_ns']) + 8000000000)))
    reject('timer changed', lambda rows: case(rows)['node_records'][-1].__setitem__('timer_args', [101]))
    reject('timeout closes before settlement', lambda rows: case(rows, 1)['node_records'][2].__setitem__('closes', 1))
    reject('timeout claims underlying settled early', lambda rows: case(rows, 1)['node_records'][2].__setitem__('underlying_settled', True))
    reject('timeout admits retry before settlement', lambda rows: case(rows, 1)['node_records'][2].__setitem__('pending_retry_error', None))
    reject('timeout final missing close', lambda rows: case(rows, 1)['node_records'][-1]['lifecycle'].__setitem__('closes', 0))
    reject('deadline not cleared', lambda rows: case(rows)['node_records'][-1].__setitem__('clear_calls', 0))
    reject('Node stdout count mismatch', lambda rows: case(rows)['collection']['node_observed'].__setitem__('stdout', 1))
    reject('native LE32 corrupt', lambda rows: case(rows).__setitem__('native_response_base64', base64.b64encode(b'\x01\x00\x00\x00{}').decode('ascii')))
    reject('service ok bool replaced by zero', lambda rows: case(rows)['service_response'].__setitem__('ok', 0))
    reject('status exceeds4096 with otherwise unchanged records', lambda rows: status(rows, lambda raw: b' ' * 4096 + raw))
    reject('noncompact status', lambda rows: status(rows, lambda raw: b' ' + raw))
    reject('duplicate status JSON key', lambda rows: status(rows, lambda raw: raw.replace(b'{"v":1,', b'{"v":1,"v":1,', 1)))
    reject('extra status record', lambda rows: status(rows, lambda raw: raw + b'{}\n'))
    reject('extra phase key with consistent wire', lambda rows: phase(rows, 'extra', 1))
    reject('nonpipe phase target with consistent wire', lambda rows: phase(rows, 'fds', [{**fd, 'target': '/tmp/foreign'} if i == 0 else fd for i, fd in enumerate(case(rows)['collection']['B3']['phase']['fds'])]))
    reject('noncanonical pipe decimal with consistent wire', lambda rows: phase(rows, 'fds', [{**fd, 'dev': '015'} if i == 0 else fd for i, fd in enumerate(case(rows)['collection']['B3']['phase']['fds'])]))
    reject('preG stderr with coherent count and wire', cancel_stderr)
    result = {'role': 'Pure lifecycle capture controls on one original normal pi-ci log; no product replay or full/hosted CI claim',
              'source_head': head, 'checker_commit': subprocess.check_output(['git', '-C', repo, 'rev-parse', 'HEAD'], text=True).strip(),
              'checker_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'control_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'log_bytes': len(raw), 'log_sha256': hashlib.sha256(raw).hexdigest(),
              'positive': positive, 'lifecycle': lifecycle, 'negative_controls': controls, 'new_product_processes': 0}
    with Path(output).open('x') as target:
        json.dump(result, target, indent=2)
        target.write('\n')
    print(json.dumps({'positive': True, 'lifecycle_cases': 3, 'negative_controls': len(controls), 'output': output}))


if __name__ == '__main__':
    main()
