"""Mutation tests of the existing source checker; never runs product processes."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def main():
    if sys.flags.optimize:
        raise RuntimeError("control harness requires assertions enabled")
    checker, log, head, repo, output = sys.argv[1:]
    checker, log, output = Path(checker).resolve(), Path(log).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = checker.read_bytes()
    raw = log.read_bytes()
    spec = importlib.util.spec_from_file_location("capture_checker", checker)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    positive = module.verify_product(raw, head, repo)
    lines = raw.decode().splitlines(keepends=True)
    parsed = {}
    for index, line in enumerate(lines):
        if line.startswith('{'):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                parsed[index] = value
    owner_rows = {i: value['python_owner_case'] for i, value in parsed.items()
                  if 'python_owner_case' in value}
    assert len(owner_rows) == 70
    plans = [
        ("missing positive release", "normal259_release_once", "released", None, "remove"),
        ("duplicate collected helper", "FG7_wrong-owner", "rejected-collected", None, "duplicate"),
        ("foreign worker ELF", "cancel_preG", "settled", ['observation', 'phase', 'exe_sha256'], '0' * 64),
        ("foreign wait collector", "cancel_preG", "settled", ['observation', 'terminal', 'worker_wait', 'collector_pid'], -1),
        ("positive before collection", "normal259_release_once", "released", ['observation', 'owner_wait_raw'], None),
        ("negative releases bytes", "cancel_preP", "settled", ['caller_released_bytes'], 1),
        ("early wall invalidation", "wall8_preG", "settled", ['observation', 'terminal', 'timing', 'invalidated_ns'], "early-wall"),
        ("helper claims worker", "FG7_status-missing", "rejected-collected", ['actual_W_count'], 1),
        ("boolean owner wait", "unused_Q", "settled", ['observation', 'owner_wait_raw'], False),
        ("unexpected pre-G success", "cancel_preG", "settled", ['observation', 'terminal', 'worker_wait', 'exit_code'], 0),
        ("missing pure relation", "unused-with-phase", "rejected", None, "remove"),
        ("synthetic PID claimed real", "phase-before-P", "rejected", ['role'], "actual_O_W_lifecycle"),
    ]
    results = []
    for name, case, event, path, value in plans:
        selected = [i for i, r in owner_rows.items() if (r['id'], r['event']) == (case, event)]
        assert len(selected) == 1
        index = selected[0]
        modified = list(lines)
        if path is None:
            if value == 'remove':
                modified.pop(index)
            else:
                modified.append(lines[index])
        else:
            changed = copy.deepcopy(parsed[index])
            target = changed['python_owner_case']
            if value == 'early-wall':
                value = str(int(target['observation']['terminal']['timing']['begin_ns']) + 7999999999)
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            modified[index] = json.dumps(changed) + '\n'
        altered = ''.join(modified).encode()
        try:
            module.verify_product(altered, head, repo)
        except AssertionError:
            results.append({'name': name, 'rejected': True, 'selector': [case, event],
                            'field': path, 'value': value,
                            'original_line_sha256': hashlib.sha256(lines[index].encode()).hexdigest()})
        else:
            raise RuntimeError('accepted mutation: ' + name)
    for name, altered in [
        ('old Pi194 count', raw.replace(b'Ran 211 tests in ', b'Ran 194 tests in ', 1)),
        ('missing original FG0 final', ''.join(line for i, line in enumerate(lines)
            if not (parsed.get(i, {}).get('case') == 'FG0_startup_unused'
                    and parsed[i].get('pass') is True)).encode()),
    ]:
        assert altered != raw
        try:
            module.verify_product(altered, head, repo)
        except AssertionError:
            results.append({'name': name, 'rejected': True})
        else:
            raise RuntimeError('accepted mutation: ' + name)
    probe = '''import importlib.util,json,sys
spec=importlib.util.spec_from_file_location("optimized_checker",sys.argv[1])
m=importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
except RuntimeError as error:
    if str(error)!="capture checker requires assertions enabled": raise
    print(json.dumps({"optimization":sys.flags.optimize,"rejected":True}))
else:
    raise RuntimeError("optimized checker accepted")
'''
    optimized = subprocess.run([sys.executable, '-O', '-B', '-c', probe, str(checker)],
                               capture_output=True, text=True, check=True)
    assert json.loads(optimized.stdout) == {'optimization': 1, 'rejected': True}
    assert optimized.stderr == ''
    assert checker.read_bytes() == source and log.read_bytes() == raw
    record = {'role': 'Verifier tests only; altered logs are synthetic, no product reruns or hosted claim',
              'argv': sys.argv, 'python': sys.version,
              'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_head': head, 'checker_sha256': hashlib.sha256(source).hexdigest(),
              'original_log_sha256': hashlib.sha256(raw).hexdigest(),
              'original_log_path': str(log), 'positive': positive,
              'mutations': results, 'optimized_mode_refused': True,
              'original_log_and_checker_unchanged': True}
    (output / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'positive': True, 'mutations_rejected': len(results),
                      'optimized_mode_refused': True, 'product_reruns': 0}))


if __name__ == '__main__':
    main()
