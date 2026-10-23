"""Independent read-only verifier checks on immutable, existing runtime evidence.

No product execution, network, CI observation, or historical evidence change.
"""
import collections
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
SOURCE = '9d39469209afc8e35535cf8ba58dbe668a3f3224'
PREFIX = 'docs/restart/implementation/QP01/host-coordinator/'
CHECKER = ROOT / (PREFIX + 'cold-delivery/verify-cold-capture.py')
EXPECTED_CHECKER_SHA = 'a5d0ab2d279bc944888f42b5b2b77c15e81f85bef6ce5ab59391662367d43e7a'
assert hashlib.sha256(CHECKER.read_bytes()).hexdigest() == EXPECTED_CHECKER_SHA
spec = importlib.util.spec_from_file_location('cold_capture', CHECKER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

matrix = subprocess.check_output(['git', 'show', '92913a83e9645d95d17fb323c517123265a43ccd:' + PREFIX + 'first-gate/correction/stable-matrix-01/stdout.log'], cwd=ROOT)
assert hashlib.sha256(matrix).hexdigest() == '5679976f68f81a026d3ecde6ba2d5a9942c9f5ffe36a46d4bbfb931842e5e5a0'
prior = [json.loads(line) for line in matrix.splitlines() if line.startswith(b'{')]
case_rows = [o for o in prior if 'case' in o]
assert len(case_rows) == 62
assert collections.Counter(o['case'] for o in case_rows) == module.EXPECTED_CASE_ROW_COUNTS
final_rows = [o for o in case_rows if 'pass' in o]
assert len(final_rows) == 39 and all(o['pass'] is True for o in final_rows)
assert {o['case'] for o in final_rows} == module.EXPECTED_FIRST_CASES

raw = gzip.decompress((ROOT / (PREFIX + 'cold-delivery/early-smoke/early-pi-fixed.stdout.log.gz')).read_bytes())
text = raw.decode()
objects = []
offset = 0
decoder = json.JSONDecoder()
for line in text.splitlines(keepends=True):
    if line.startswith('{'):
        try:
            value, _ = decoder.raw_decode(text, offset)
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(value, dict):
                objects.append(value)
    offset += len(line)
base = next(o for o in objects if o.get('role') == 'public fixture build, not hardware qualification')
positive = module.verify_first(objects, base, SOURCE, str(ROOT))
assert positive['first_owner_cases'] == 39

results = []
def reject(name, mutate):
    changed = copy.deepcopy(objects)
    mutate(changed)
    try:
        module.verify_first(changed, base, SOURCE, str(ROOT))
    except (AssertionError, KeyError):
        results.append({'control': name, 'rejected': True})
    else:
        raise AssertionError('Verifier accepted mutation: ' + name)

def select(rows, key):
    return next(o[key] for o in rows if key in o)

def duplicate(rows, final):
    row = next(o for o in rows if 'case' in o and ('pass' in o) == final)
    rows.append(copy.deepcopy(row))

reject('duplicate final true', lambda r: duplicate(r, True))
reject('duplicate intermediate telemetry', lambda r: duplicate(r, False))
reject('false final result', lambda r: next(o for o in r if o.get('pass') is True and 'case' in o).__setitem__('pass', False))
reject('foreign worker ELF', lambda r: select(r, 'owner_phase').__setitem__('exe_sha256', '0' * 64))
reject('wrong actual W collector', lambda r: next(o['owner_settlement']['terminal']['worker_wait'] for o in r if 'owner_settlement' in o and not o['owner_settlement']['synthetic_no_W_helper'] and o['owner_settlement']['terminal']['worker_pid'] is not None).__setitem__('collector_pid', 0))
reject('timer callback already aborted', lambda r: select(r, 'synchronous_deadline_guard').__setitem__('signal_aborted', True))
reject('foreign decoded response oracle', lambda r: next(o['owner_settlement']['terminal'] for o in r if 'owner_settlement' in o and not o['owner_settlement']['synthetic_no_W_helper'] and o['owner_settlement']['terminal']['outcome'] == 'decoded').__setitem__('result_sha256', '0' * 64))

result = {
    'verdict': 'PASS_DISTINCT_FIRST_SCOPE_VERIFIER_ONLY',
    'candidate': SOURCE,
    'checker_sha256': EXPECTED_CHECKER_SHA,
    'original_929_case_catalogue': {'final_unique_true': 39, 'intermediate_rows': 23, 'case_tagged_rows': 62},
    'actual_reused_early_log_sha256': hashlib.sha256(raw).hexdigest(),
    'positive': positive,
    'negative_controls': results,
    'limits': 'Read-only replay of the proposed verifier on existing actual source-bound early evidence. No new product run or completed hosted CI claim; full combined verifier and unchanged mandatory generic checker remain required on final delivery.'
}
print(json.dumps(result, indent=2))
