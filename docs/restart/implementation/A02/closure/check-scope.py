#!/usr/bin/env python3
"""Check the bounded A02 metadata diff without changing source or the graph."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[5]
BASE = 'b1c90139a651895284b2624da7d12903cf16bc9d'
SCOPE = 'docs/restart/implementation/A02/closure/'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def task_fragments(text):
    position = re.search(r'^  "tasks": \[', text, re.M).end()
    decoder = json.JSONDecoder(); result = {}
    while True:
        while text[position].isspace() or text[position] == ',':
            position += 1
        if text[position] == ']':
            return result
        value, end = decoder.raw_decode(text, position)
        result[value['id']] = text[position:end]
        position = end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expect-closed', action='store_true')
    args = parser.parse_args()
    old_bytes = git('show', BASE + ':plan/work-items.json')
    current_bytes = (ROOT / 'plan/work-items.json').read_bytes()
    old, current = json.loads(old_bytes), json.loads(current_bytes)
    before, after = task_fragments(old_bytes.decode()), task_fragments(current_bytes.decode())
    assert set(before) == set(after) and len(before) == 47
    assert all(before[k] == after[k] for k in before if k != 'A02')
    old_tasks = {t['id']: t for t in old['tasks']}
    tasks = {t['id']: t for t in current['tasks']}
    for key in tasks:
        assert tasks[key]['acceptance'] == old_tasks[key]['acceptance']
        assert tasks[key]['depends_on'] == old_tasks[key]['depends_on']
    a02 = tasks['A02']; original = old_tasks['A02']
    allowed_task = {'status', 'candidate_commits', 'reviewer', 'review_verdict',
                    'result_artifacts', 'current_checkpoint', 'reviewed_candidate_commits',
                    'reviewed_input_commits', 'result_manifest', 'integration'}
    assert {k: v for k, v in a02.items() if k not in allowed_task} == {
        k: v for k, v in original.items() if k not in allowed_task}
    assert a02['input_commits'] == original['input_commits']
    allowed_global = {'tasks', 'revision', 'as_of', 'execution_model_policy', 'adoption_reconciliation'}
    assert {k: v for k, v in current.items() if k not in allowed_global} == {
        k: v for k, v in old.items() if k not in allowed_global}
    policy_old = copy.deepcopy(old['execution_model_policy'])
    policy_new = copy.deepcopy(current['execution_model_policy'])
    policy_old.pop('integration'); policy_new.pop('integration')
    assert policy_old == policy_new
    allowed_adoption = {'initial_adoption', 'closure_integration', 'closure_recorded_utc'}
    assert {k: v for k, v in current['adoption_reconciliation'].items() if k not in allowed_adoption} == {
        k: v for k, v in old['adoption_reconciliation'].items() if k not in allowed_adoption}
    closed = [t['id'] for t in old['tasks'] if t['status'] in {'integrated', 'verified'}]
    assert len(closed) == 7 and all(tasks[k] == old_tasks[k] for k in closed)
    index_path = ROOT / 'plan/evidence-index.json'
    assert index_path.read_bytes() == git('show', BASE + ':plan/evidence-index.json')
    index = json.loads(index_path.read_bytes())
    assert index['source_commit'] == 'f2ef70f522af4977e15f81554a8c6eadcdbe8097'
    assert len(index['artifacts']) == 1508
    for row in index['artifacts']:
        path = ROOT / row['path']
        assert path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == row['sha256']
        assert ('100755' if stat.S_IMODE(path.stat().st_mode) & 0o111 else '100644') == row['mode']
    allowed_existing = {'plan/work-items.json', 'docs/restart/README.md',
                        'docs/restart/implementation/handoff.md'}
    names = git('diff', '--name-only', BASE).decode().splitlines()
    names += git('ls-files', '--others', '--exclude-standard').decode().splitlines()
    assert all(p.startswith(SCOPE) or p in allowed_existing for p in names)
    assert git('diff', BASE, '--', 'protocols/contracts/v1', 'Cargo.lock', 'ci', '.github') == b''
    for path in (ROOT / SCOPE).rglob('*'):
        assert not path.is_symlink()
    if args.expect_closed:
        assert a02['status'] == 'integrated'
        assert a02['candidate_commits'] == a02['reviewed_candidate_commits'] == {'nSealr/nsealr': BASE}
        assert a02['reviewed_input_commits'] == original['input_commits']
        assert a02['review_verdict'] == 'pass' and a02['reviewer'] != a02['assignee']
        assert current['revision'] == old['revision'] + 1
    print(json.dumps({'scope_only': True, 'tasks': 47, 'all_criteria_dependencies_unchanged': True,
                      'other46_serialized_records_unchanged': True, 'original_closed7': closed,
                      'frozen1508_hashes_modes_and_index_preserved': True,
                      'resources': len(current['resources']), 'release_paths': len(current['release_paths']),
                      'expected_closed_A02': args.expect_closed, 'historical_index_sha256': sha(index_path.read_bytes())},
                     sort_keys=True))


if __name__ == '__main__':
    main()
