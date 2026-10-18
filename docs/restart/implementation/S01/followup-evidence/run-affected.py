#!/usr/bin/env python3
"""Run affected gates against the fresh, default-bootstrap source tuple."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root/'firmware/tools/baseline'))
from bootstrap import Recorder, write_json

env = json.loads((root/'environment.json').read_text())
inputs = json.loads((root/'source-commits.json').read_text())
expected = json.loads((root/'source-state.json').read_text())


def states():
    result = {}
    for name, commit in inputs.items():
        source = root/('firmware' if name == 'nsealr' else name)
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
        assert actual == commit, (name, actual, commit)
        result[name] = {'status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=source, text=True),
                        'diff_sha256': hashlib.sha256(subprocess.check_output(['git', 'diff', '--binary'], cwd=source)).hexdigest()}
    return result


before = states()
assert before == expected, 'undeclared source change before affected gates'
recorder = Recorder(root/'evidence/affected', env)
write_json(recorder.directory/'source-before.json', before)
for label, argv, directory in (
    ('core-ci', ['make', '-k', 'ci'], 'firmware'),
    ('lab-ci', ['make', '-k', 'ci'], 'lab'),
    ('fixture-parity', ['python3', 'scripts/check_fixture_snapshots.py'], 'lab'),
    ('v1-discovery', ['python3', str(root/'firmware/docs/restart/implementation/S01/check-auth-negative-inventory.py'), str(root/'lab'), str(root/'specs')], 'firmware'),
    ('full-integration', ['make', 'integration'], 'lab'),
):
    recorder.run(label, argv, root/directory, required=False)
after = states()
write_json(recorder.directory/'source-after.json', after)
assert all(after[name]['diff_sha256'] == before[name]['diff_sha256'] for name in inputs), 'tracked source changed during gates'
failed = [row['label'] for row in recorder.results if row['exit_code']]
write_json(recorder.directory/'result.json', {'candidate': inputs['nsealr'], 'inputs': inputs,
           'all_passed': not failed, 'failed_commands': failed,
           'scope': 'Fresh default bootstrap; affected core/lab CI, fixture parity, v1 discovery and full integration. Other component suites reconcile to preserved prior evidence.'})
raise SystemExit(bool(failed))
