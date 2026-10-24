"""Pure controls on a retained log: LOG SOURCE_HEAD REPOSITORY RESULT.

No product execution, compiler, network or actor. Source queries address immutable
Git objects and are cached without changing the returned bytes.
"""
from functools import cache
from pathlib import Path
from unittest.mock import patch
import base64
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys


def main():
    log, head, repo, output = sys.argv[1:]
    source = Path(repo) / 'docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py'
    spec = importlib.util.spec_from_file_location('qh01_engine_capture', source)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    raw = Path(log).read_bytes()
    lines = [re.sub(r'^\d{4}-\d\d-\d\dT\S+Z ?', '', s) for s in raw.decode().splitlines()]
    decoder, objects = json.JSONDecoder(), []
    for i, line in enumerate(lines):
        if line.startswith('{'):
            try:
                value, _ = decoder.raw_decode('\n'.join(lines[i:]))
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                objects.append(value)
    def all_rows(rows, key):
        return [row[key] for row in rows if key in row]
    def engine(rows, index=0):
        return all_rows(rows, 'qh01_request_engine_case')[index]
    def build(rows):
        return all_rows(rows, 'qh01_request_engine_build')[0]
    def replace(rows, path, value, index=0):
        item = engine(rows, index)
        for key in path[:-1]:
            item = item[key]
        item[path[-1]] = value
    actual_check_output = subprocess.check_output
    @cache
    def fixed_git_read(argv, text):
        return actual_check_output(list(argv), text=text)
    def read(argv, **kwargs):
        assert set(kwargs) <= {'text'}
        return fixed_git_read(tuple(argv), kwargs.get('text', False))
    controls = []
    def reject(name, change):
        rows = copy.deepcopy(objects)
        change(rows)
        try:
            checker.verify_qh01_request_engine(rows, head, repo)
        except (AssertionError, KeyError, ValueError, TypeError):
            controls.append({'name': name, 'rejected': True})
        else:
            raise AssertionError('checker accepted mutated evidence: ' + name)
    with patch.object(checker.subprocess, 'check_output', side_effect=read):
        workers = [o for o in objects if o.get('role') == 'public RGB worker build, initialization v2, not hardware qualification']
        assert len(workers) == 1
        legacy_composition = checker.verify_qh01_composition(objects, lines, workers[0], head, repo)
        legacy_lifecycle = checker.verify_qh01_lifecycle(objects)
        positive = checker.verify_qh01_request_engine(objects, head, repo)
        for key in ['qh01_request_engine_build_command', 'qh01_request_engine_build',
                    'qh01_request_engine_command', 'qh01_request_engine_result', 'qh01_request_engine_case']:
            reject('missing ' + key, lambda rows, k=key: rows.__setitem__(slice(None), [r for r in rows if k not in r]))
            reject('duplicate ' + key, lambda rows, k=key: rows.append(copy.deepcopy(next(r for r in rows if k in r))))
        reject('compiler exits nonzero', lambda r: build(r).__setitem__('status', 1))
        reject('compiler status boolean', lambda r: build(r).__setitem__('status', False))
        reject('compiler strict option removed', lambda r: build(r)['argv'].remove('--strict'))
        reject('compiler from another checkout', lambda r: build(r).__setitem__('cwd', '/old/worktree'))
        reject('compiler entry differs from joined Bridge build', lambda r: build(r)['compiler'].__setitem__('sha256', '0' * 64))
        reject('stale preparation source', lambda r: build(r)['source_after'].__setitem__('package.json', '0' * 64))
        reject('missing declaration artifact', lambda r: build(r)['outputs'].pop('native-leaf.d.ts'))
        reject('wrong module context', lambda r: build(r)['package_context'].__setitem__('value', {'type': 'commonjs'}))
        reject('wrong preparation receipt', lambda r: build(r).__setitem__('receipt', '/old/preparation.json'))
        reject('build failure also reported', lambda r: r.append({'qh01_request_engine_build_failure': {}}))
        reject('case failure also reported', lambda r: r.append({'qh01_request_engine_failure': {}}))
        reject('case order reversed', lambda r: r.reverse())
        for path, value, name in [
            (['source_after', 'Cargo.lock'], '0' * 64, 'stale real engine source'),
            (['native_preparation_after', 'compiler_sha256'], '0' * 64, 'compiler changed after preparation'),
            (['native_initialization', 'module_sha256'], '0' * 64, 'unbound helper module'),
            (['native_initialization', 'library_sha256'], '0' * 64, 'unbound native library'),
            (['native_settlement', 'code'], True, 'C code boolean'),
            (['native_settlement', 'signal'], 'SIGKILL', 'C signal'),
            (['native_settlement', 'sent'], False, 'request not sent'),
            (['native_settlement', 'readiness_hex'], '', 'missing actual readiness'),
            (['native_settlement', 'overflow'], True, 'native stdout overflow'),
            (['native_settlement', 'stderr_bytes'], 0, 'missing native observation stderr'),
            (['native_outcome', 'collected'], 0, 'C uncollected'),
            (['native_outcome', 'capability_calls'], 2, 'reused signing capability'),
            (['native_outcome', 'timer_args'], [4999], 'native timeout changed'),
            (['native_outcome', 'children_after'], '999999', 'child remains'),
            (['native_outcome', 'response_sha256'], '0' * 64, 'response artifact mismatch'),
            (['native_observation', 'synthetic_complete_review', 30, 'body'], 'skip decision', 'review page changed'),
            (['collection', 'B3', 'terminal', 'G_bytes'], True, 'B3 G boolean'),
            (['collection', 'B3', 'terminal', 'worker_wait', 'raw_status'], 9, 'worker not collected successfully'),
            (['collection', 'B3', 'phase', 'fds', 0, 'target'], '/tmp/fake', 'worker FD not actual pipe'),
            (['collection', 'B3', 'terminal', 'timing', 'settled_ns'], '00', 'noncanonical timing'),
            (['collection', 'B3', 'status_wire_base64'], 'e30K', 'status wire not source rows'),
            (['node_records', -1, 'engine', 'fd_restored'], False, 'Node FD restoration false'),
            (['service_response', 'result', 'signer_response', 'result', 'event', 'sig'], '0' * 128, 'wrong complete event signature'),
        ]:
            reject(name, lambda rows, p=path, v=value: replace(rows, p, v))
        reject('native FD identity unrestored', lambda r: engine(r)['native_outcome']['fds_after'].pop('0'))
        reject('refusal sends input', lambda r: replace(r, ['native_settlement', 'sent'], True, 1))
        reject('refusal emits output', lambda r: replace(r, ['native_settlement', 'stdout_bytes'], 611, 1))
        reject('refusal has observation', lambda r: replace(r, ['native_observation'], engine(r)['native_observation'], 1))
        reject('refusal expected SHA not inverted', lambda r: replace(r, ['native_initialization', 'child_expected_sha256'], engine(r, 1)['native_initialization']['library_sha256'], 1))
        def duplicate_json(rows):
            c = engine(rows)
            w = base64.b64decode(c['native_response_base64'])
            changed = b'{"version":1,' + w[5:]
            c['native_response_base64'] = base64.b64encode(len(changed).to_bytes(4, 'little') + changed).decode()
            c['node_records'][-1]['native_response_base64'] = c['native_response_base64']
        reject('duplicate field in native JSON', duplicate_json)
    result = {'role': 'Pure capture-checker controls; no product replay or hosted CI claim',
              'source_head': head, 'checker_commit': actual_check_output(['git', '-C', repo, 'rev-parse', 'HEAD'], text=True).strip(),
              'checker_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'control_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'log_bytes': len(raw), 'log_sha256': hashlib.sha256(raw).hexdigest(),
              'legacy_composition': legacy_composition, 'legacy_lifecycle': legacy_lifecycle,
              'positive': positive, 'negative_controls': controls,
              'cached_immutable_git_queries': fixed_git_read.cache_info()._asdict(), 'new_product_processes': 0}
    with Path(output).open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'positive': True, 'negative_controls': len(controls), 'output': output}))


if __name__ == '__main__':
    main()
