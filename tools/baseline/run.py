#!/usr/bin/env python3
"""Execute every baseline suite and retain failures; never turn known failures green."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from bootstrap import Recorder, sha256, write_json


def statuses(root: Path, inputs: dict) -> dict:
    return {name: subprocess.check_output(['git', 'status', '--porcelain'], cwd=root/('firmware' if name == 'nsealr' else name), text=True) for name in inputs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--smoke', action='store_true', help='replay smoke only; does not claim full suite acceptance')
    args = parser.parse_args()
    root = args.destination.resolve()
    env = json.loads((root/'environment.json').read_text())
    inputs = json.loads((root/'source-commits.json').read_text())
    for name, expected in inputs.items():
        source = root/('firmware' if name == 'nsealr' else name)
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
        if actual != expected:
            raise ValueError(f'{name}: source pin drift: {actual} != {expected}')
    directory = root/'evidence'/('smoke' if args.smoke else 'suites')
    recorder = Recorder(directory, env)
    before = statuses(root, inputs)
    if any(before.values()):
        raise ValueError(f'source checkouts must be clean before baseline: {before}')
    write_json(directory/'source-before.json', before)
    if args.smoke:
        recorder.run('core-smoke', ['make', 'test', 'cargo-test'], root/'firmware', required=False)
        if 'lab' in inputs:
            recorder.run('fixture-snapshots', ['python3', 'scripts/check_fixture_snapshots.py'], root/'lab', required=False)
            recorder.run('integration-helper-tests', ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_integration_support.py'], root/'lab', required=False)
    else:
        # -k executes remaining independent targets after a failure while
        # retaining make's failing status, including stale API checks.
        for name in ('firmware', 'specs', 'companion', 'raspberry', 'smartcard', 'hardware', 'website', 'lab'):
            if (root/name).exists():
                recorder.run(f'{name}-ci', ['make', '-k', 'ci'], root/name, required=False)
        if 'lab' in inputs:
            # One uninterrupted invocation of the complete existing recipe.
            # No command-line PYTHON/VENV overrides leak through recursive make.
            recorder.run('full-integration', ['make', 'integration'], root/'lab', required=False)
    write_json(directory/'source-after.json', statuses(root, inputs))
    skipped = [
        {'gate': 'NSEALR_LIVE_E2E relay test', 'reason': 'not enabled in this offline software baseline; Docker/relay run requires separate evidence'},
        {'gate': 'interactive Chromium/Firefox session', 'reason': 'package/DOM/native-messaging checks do not exercise an installed browser session'},
        {'gate': 'real hardware approval/signing, GPIO/camera/display and card/USB', 'reason': 'no identified sample/operator; simulator and safe probe are software evidence only'},
        {'gate': 'manufacturing, provisioning, secure-element custody and physical entropy', 'reason': 'outside R00 software baseline; no production keys or irreversible operations'},
    ]
    write_json(directory/'skips.json', skipped)
    failed = [r['label'] for r in recorder.results if r['exit_code']]
    write_json(directory/'result.json', {'input_commits':inputs, 'mode':'smoke' if args.smoke else 'full', 'failed_commands':failed, 'commands_sha256':sha256(directory/'commands.json'), 'all_passed':not failed})
    print(json.dumps({'failed_commands': failed, 'evidence': str(directory)}))
    return int(bool(failed))


if __name__ == '__main__':
    raise SystemExit(main())
