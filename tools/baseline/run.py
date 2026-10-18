#!/usr/bin/env python3
"""Execute every baseline suite and retain failures; never turn known failures green."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from bootstrap import Recorder, sha256, write_json


def statuses(root: Path, inputs: dict) -> dict:
    return {name: subprocess.check_output(['git', 'status', '--porcelain'], cwd=root/name, text=True) for name in inputs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--smoke', action='store_true', help='replay smoke only; does not claim full suite acceptance')
    args = parser.parse_args()
    root = args.destination.resolve()
    env = json.loads((root/'environment.json').read_text())
    inputs = json.loads((root/'source-commits.json').read_text())
    for name, expected in inputs.items():
        source = root/name
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
        if actual != expected:
            raise ValueError(f'{name}: source pin drift: {actual} != {expected}')
    directory = root/'evidence'/('smoke' if args.smoke else 'suites')
    recorder = Recorder(directory, env)
    before = statuses(root, inputs)
    expected = json.loads((root/'source-state.json').read_text())
    for name in inputs:
        source = root/name
        diff = hashlib.sha256(subprocess.check_output(['git','diff','--binary'],cwd=source)).hexdigest()
        if before[name] != expected[name]['status'] or diff != expected[name]['diff_sha256']:
            raise ValueError(f'{name}: undeclared source delta before baseline')
    write_json(directory/'source-before.json', before)
    if args.smoke:
        recorder.run('product-smoke', ['make', 'test', 'cargo-test'], root/'nsealr', required=False)
    else:
        # One complete product entrypoint; -k preserves independent failures.
        recorder.run('product-ci', ['make', '-k', 'ci'], root/'nsealr', required=False)
    after = statuses(root, inputs)
    write_json(directory/'source-after.json', after)
    changed = [name for name in inputs if after[name] != before[name] or hashlib.sha256(subprocess.check_output(['git','diff','--binary'],cwd=root/name)).hexdigest() != expected[name]['diff_sha256']]
    for name in inputs:
        if subprocess.check_output(['git','rev-parse','HEAD'],cwd=root/name,text=True).strip() != inputs[name] and name not in changed:
            changed.append(name)
    skipped = [
        {'gate': 'NSEALR_LIVE_E2E relay test', 'reason': 'not enabled in this offline software baseline; Docker/relay run requires separate evidence'},
        {'gate': 'interactive Chromium/Firefox session', 'reason': 'package/DOM/native-messaging checks do not exercise an installed browser session'},
        {'gate': 'real hardware approval/signing, GPIO/camera/display and USB', 'reason': 'no identified sample/operator; simulator and safe probe are software evidence only'},
        {'gate': 'manufacturing, provisioning, secure-element custody and physical entropy', 'reason': 'outside software acceptance; no production keys or irreversible operations'},
    ]
    write_json(directory/'skips.json', skipped)
    failed = [r['label'] for r in recorder.results if r['exit_code']]
    write_json(directory/'result.json', {'input_commits':inputs, 'mode':'smoke' if args.smoke else 'full', 'failed_commands':failed, 'commands_sha256':sha256(directory/'commands.json'), 'source_changed_after':changed, 'all_passed':not failed and not changed})
    print(json.dumps({'failed_commands': failed, 'evidence': str(directory)}))
    return int(bool(failed or changed))


if __name__ == '__main__':
    raise SystemExit(main())
