#!/usr/bin/env python3
"""Read-only preparation audit; no product test, cold fetch or CI rerun."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

C = '7618ea42a86a1c25790955090b2dee3350943ff8'
MAIN = 'd931277bebbc5f43514b0e8438d65fb60603fa35'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CAPTURE = Path('/home/tux/nsealr/.restart-tools/goal/a02-ci-2026-10-20/run-39408038674')
PREFIX = 'docs/restart/implementation/A02/post-rebase-repair/'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def sha(body):
    return hashlib.sha256(body).hexdigest()


def source(commit, path):
    return git('show', commit + ':' + path)


def main():
    audit = json.loads(source(C, PREFIX + 'source-audit.json'))
    assert git('rev-parse', C + '^').decode().strip() == MAIN
    assert git('rev-parse', MAIN + '^{tree}').decode().strip() == audit['input_tree']
    assert sorted(git('diff', '--name-status', MAIN, C).decode().splitlines()) == sorted(
        ['A\t' + PREFIX + 'brief.md', 'A\t' + PREFIX + 'source-audit.json'])
    subprocess.run(['git', '-C', str(ROOT), 'diff', '--check', MAIN, C], check=True)
    bindings = []
    for row in audit['inputs']:
        body = source(row['source_commit'], row['path'])
        assert len(body) == row['bytes'] and sha(body) == row['sha256']
        bindings.append(row)
    pairs = []
    for row in audit['exact_rebased_anchors']:
        old, new = row['historical_commit'], row['adopted_ancestor']
        assert git('rev-parse', old + '^{tree}') == git('rev-parse', new + '^{tree}')
        assert git('rev-parse', new + '^{tree}').decode().strip() == row['exact_whole_tree']
        before = git('ls-tree', '-r', '-z', old, '--', 'protocols/contracts/v1')
        after = git('ls-tree', '-r', '-z', new, '--', 'protocols/contracts/v1')
        assert before == after and sha(after) == row['artifact_tree_inventory_sha256']
        assert len([x for x in after.split(b'\0') if x]) == row['artifact_rows']
        codes = [subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', c, MAIN]).returncode for c in [old, new]]
        assert codes == [1, 0]
        pairs.append(dict(row, actual_old_new_ancestor_exit_codes=codes))
    capture = json.loads((CAPTURE / 'capture.json').read_text())
    for row in capture['files']:
        body = (CAPTURE / row['path']).read_bytes()
        assert len(body) == row['size'] and sha(body) == row['sha256']
    run = json.loads((CAPTURE / 'run.json').read_text())
    jobs = json.loads((CAPTURE / 'jobs.json').read_text())
    assert run['head_sha'] == MAIN and run['id'] == 39408038674 and run['conclusion'] == 'failure'
    failed_steps = [s['name'] for job in jobs['jobs'] for s in job['steps'] if s['conclusion'] == 'failure']
    assert failed_steps == ['Complete product acceptance']
    assert sha((CAPTURE / 'logs.zip').read_bytes()) == audit['failed_main_CI']['capture_logs_zip_sha256']
    with zipfile.ZipFile(CAPTURE / 'logs.zip') as z:
        for row in capture['zip_members']:
            body = z.read(row['name'])
            assert len(body) == row['size'] and sha(body) == row['sha256']
        lines = z.read('verify/5_Complete product acceptance.txt').decode().splitlines()
    errors = [line for line in lines if re.search(r'make: \*\*\* \[Makefile:', line)]
    assert len(errors) == 2 and ': test]' in errors[0] and ': integration]' in errors[1]
    baseline = '5cb16cbaffc6b90ca9dfbb1ce7a5388e731d1ae0'
    assert any('ERROR: Command' in line and baseline in line and '128' in line for line in lines)
    assert any('CalledProcessError: Command' in line and baseline in line and '128' in line for line in lines)
    assert any('[1/17 original 1] check_fixture_snapshots' in line for line in lines)
    assert not any('[2/17 ' in line for line in lines)
    manifest = json.loads(source(MAIN, 'protocols/contracts/v1/manifest.json'))
    assert manifest['initial_import_commit'] == audit['exact_rebased_anchors'][0]['historical_commit']
    result = {'schema_version': 1, 'candidate_commit': C, 'input_main': MAIN,
              'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'spec_bindings': [{'path': PREFIX + name, 'sha256': sha(source(C, PREFIX + name))}
                                for name in ['brief.md', 'source-audit.json']],
              'input_file_bindings_verified': bindings, 'whole_tree_and_artifact_inventory_pairs': pairs,
              'capture_files': capture['files'], 'zip_members_verified': capture['zip_members'],
              'failed_job_steps': failed_steps, 'failing_make_targets': errors,
              'observed_root_cause': 'Unresolvable old BASELINE Git object; integration step1 repeats the same lookup failure.',
              'initial_import_failure_is_source_inference': 'Current loop also dereferences old INITIAL_IMPORT; it is not an ancestor of fetched main. The failing baseline guard prevents reaching it in this log.',
              'remaining_integration_steps_unexecuted': 16, 'other_terminal_make_failure_observed': False,
              'whitespace_exit_code': 0, 'result': 'PASS_preimplementation_identity_and_diagnosis_only',
              'not_run': ['No product tests, cold fetch/RED reproduction, implementation or CI rerun',
                          'No merge, task closure, source reset or physical qualification']}
    (HERE / 'probe-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'result': result['result'], 'tree_pairs': len(pairs), 'input_bindings': len(bindings),
                      'failed_make_targets': 2, 'zip_members_verified': len(capture['zip_members'])}))


if __name__ == '__main__':
    main()
