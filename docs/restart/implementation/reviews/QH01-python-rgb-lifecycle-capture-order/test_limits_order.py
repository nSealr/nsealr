"""One pure source-corresponding follow-up; reuse unchanged earlier controls.

Usage: python3 -B test_limits_order.py ORIGINAL_LOG REPOSITORY OUTPUT.json
Only the existing one-line qh01 JSON namespaces are needed by this block.
"""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def main():
    log, repo, output = sys.argv[1:]
    raw = Path(log).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == 'e3b31f6f629f45eefeb0e2374c98958a850425738b63347f7e1ec48c82cf8eac'
    objects = [json.loads(line) for line in raw.decode().splitlines() if line.startswith('{"qh01_')]
    source = Path(repo) / 'docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py'
    spec = importlib.util.spec_from_file_location('limits_order_capture', source)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    positive = checker.verify_qh01_lifecycle(objects)
    rows = copy.deepcopy(objects)
    b = next(o['qh01_lifecycle_case'] for o in rows if 'qh01_lifecycle_case' in o)['collection']['B3']
    p, t = b['phase'], b['terminal']
    assert list(p['limits']) == ['AS', 'CPU', 'CORE']
    p['limits'] = {key: p['limits'][key] for key in ['CPU', 'AS', 'CORE']}
    b['status_wire_base64'] = base64.b64encode(b''.join((json.dumps(row, separators=(',', ':')) + '\n').encode('ascii') for row in [p, t])).decode('ascii')
    try:
        checker.verify_qh01_lifecycle(rows)
    except AssertionError:
        pass
    else:
        raise AssertionError('accepted reordered limits with coherent canonical wire')
    result = {'role': 'Pure limits-order follow-up on original f7 log; previous46 controls retain original source identities',
              'log_sha256': hashlib.sha256(raw).hexdigest(), 'checker_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'control_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'positive': positive,
              'negative_controls': [{'name': 'reordered limits with consistent canonical status', 'rejected': True}],
              'new_product_processes': 0}
    with Path(output).open('x') as target:
        json.dump(result, target, indent=2)
        target.write('\n')
    print(json.dumps({'positive': True, 'additional_negative_controls': 1, 'output': output}))


if __name__ == '__main__':
    main()
