#!/usr/bin/env python3
"""Independent exact-delivery checks. Does not import, replay, merge or close A02."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import unquote

C = 'a5f7b9f2e087c9538495a16706644f3390e6b01c'
B = 'daf8ba03a9eb820f99b0f1bf5c4f553a7961e008'
A = 'bb033619b5346302833d717eb501bfa4e3653a1b'
R = '0b55449aeea6b296805b786fd4822fc625ba74dd'
S = '81a9a12140c1ace260f9ed280146b7d663e11ac9'
SR = '100edeb734994108a49a2214addc38d029c4d558'
AD = 'b507e00dbbc7992841836cc769a27d8efdbac75a'
F = 'f2ef70f522af4977e15f81554a8c6eadcdbe8097'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
P = 'docs/restart/implementation/A02/coordinator-adoption/'


def git(*args, repo=ROOT):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(c, p, repo=ROOT):
    return git('show', c + ':' + p, repo=repo)


def js(c, p):
    return json.loads(read(c, p))


def tree(c, repo=ROOT):
    result = {}
    for line in git('ls-tree', '-rz', c, repo=repo).split(b'\0'):
        if line:
            h, p = line.split(b'\t', 1)
            result[p.decode()] = tuple(h.decode().split())
    return result


def bodies(ids):
    ids = sorted(set(ids))
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', '--batch'],
                                  input=('\n'.join(ids) + '\n').encode())
    result, pos = {}, 0
    for oid in ids:
        e = raw.index(b'\n', pos)
        got, kind, size = raw[pos:e].decode().split()
        assert got == oid and kind == 'blob'
        start = e + 1
        pos = start + int(size)
        result[oid] = raw[start:pos]
        assert raw[pos:pos + 1] == b'\n'
        pos += 1
    assert pos == len(raw)
    return result


def fragments(text):
    pos = re.search(r'"tasks"\s*:\s*\[', text).end()
    out, decoder = {}, json.JSONDecoder()
    while True:
        while text[pos].isspace() or text[pos] == ',':
            pos += 1
        if text[pos] == ']':
            return out
        obj, end = decoder.raw_decode(text, pos)
        out[obj['id']] = text[pos:end]
        pos = end


def main():
    bt, ct = tree(B), tree(C)
    assert git('rev-parse', C + '^').decode().strip() == B
    assert git('rev-parse', C + '^{tree}').decode().strip() == 'e67b1337eaea5cfe3242fe4d83845881764ea5f0'
    receipt = js(C, P + 'receipt.json')
    admission = js(AD, 'docs/restart/implementation/resume-2026-10-20/a02-adoption-acceptance.json')
    assert receipt['author_commit'] == A and receipt['reviewed_product_commit'] == B
    assert receipt['reviewed_scope_commit'] == S and receipt['admission_commit'] == AD
    assert js(R, 'docs/restart/implementation/reviews/A02-final/review.json')['candidate_commit'] == A
    assert js(R, 'docs/restart/implementation/reviews/A02-final/review.json')['verdict'] == 'pass_final_rehearsal_review'
    for name in ['source_review', 'scope_review']:
        row = admission[name]
        assert sha(read(row['commit'], row['path'])) == row['sha256']

    inventories = ['payload-copy.json', 'source-review-copy.json', 'scope-review-copy.json', 'scope-copy.json']
    expected_counts = [983, 143, 5, 3]
    copied, source_checks = {}, []
    all_rows = []
    for name, count in zip(inventories, expected_counts):
        inv = js(C, P + name)
        assert len(inv['rows']) == inv['total'] == count
        all_rows.extend(inv['rows'])
    blob_data = bodies([row['blob'] for row in all_rows])
    source_trees = {c: tree(c) for c in [A, R, SR, S, AD]}
    for row in all_rows:
        src, dst, commit = row['source_path'], row['destination'], row['source_commit']
        assert dst not in copied
        assert ct[dst] == source_trees[commit][src] == (row['mode'], 'blob', row['blob'])
        body = blob_data[row['blob']]
        assert len(body) == row['bytes'] and sha(body) == row['sha256']
        if dst in bt:
            assert bt[dst] == ct[dst] and row['before']['blob'] == bt[dst][2]
            assert row['before']['mode'] == bt[dst][0]
        else:
            assert row['before'] is None
        copied[dst] = row
    assert len(copied) == 1134
    payload = js(S, 'docs/restart/implementation/resume-2026-10-20/a02-adoption-payload.json')
    for row in payload['rows']:
        delivered = copied[row['path']]
        assert delivered['source_commit'] == A and delivered['source_path'] == row['path']
        assert all(delivered[k] == row[k] for k in ['mode', 'blob', 'sha256', 'bytes'])
        if row['before']:
            assert delivered['before'] == dict({k: row['before'][k] for k in ['mode', 'blob']}, kind='blob')
            assert row['before']['sha256'] == row['sha256'] and row['before']['bytes'] == row['bytes']
        else:
            assert delivered['before'] is None
    prefixes = [(A, ('docs/restart/implementation/A02/', 'tools/migration/'), inventories[0]),
                (R, ('docs/restart/implementation/reviews/A02-final/',), inventories[1]),
                (SR, ('docs/restart/implementation/reviews/A02-adoption-scope/',), inventories[2])]
    for commit, prefix, inv_name in prefixes:
        expected = {p for p in source_trees[commit] if p.startswith(prefix)}
        assert expected == {r['source_path'] for r in js(C, P + inv_name)['rows']}
    review_manifest = js(C, 'docs/restart/implementation/reviews/A02-final/review-artifacts.json')
    for row in review_manifest['files']:
        assert sha(read(C, row['path'])) == row['sha256']
    index = js(C, P + 'artifacts.json')
    indexed = {row['path'] for row in index['artifacts']}
    actual_records = {p for p in ct if p.startswith(P)}
    assert indexed | {P + 'artifacts.json'} == actual_records and len(indexed) == 38
    for row in index['artifacts']:
        b = read(C, row['path'])
        assert sha(b) == row['sha256'] and len(b) == row['bytes']
    modified = {p for p in bt if ct.get(p) != bt[p]}
    added = set(ct) - set(bt)
    metadata = {'docs/restart/README.md', 'docs/restart/implementation/handoff.md', 'plan/work-items.json'}
    assert modified == metadata and not set(bt) - set(ct)
    assert added == (set(copied) - set(bt)) | (actual_records - set(copied))
    assert len(added) == 1092 and len(ct) == 4704
    for path in added:
        parts = PurePosixPath(path).parts
        assert not {'..', '.git', '.runtime', '__pycache__', 'node_modules'}.intersection(parts)
        assert not path.endswith(('.bundle', '.pdf', '.zip', '.pyc'))
        assert ct[path][0] in ['100644', '100755'] and ct[path][1] == 'blob'
    for row in receipt['only_existing_source_mutations']:
        assert sha(read(B, row['path'])) == row['before_sha256']
        assert sha(read(C, row['path'])) == row['after_sha256']

    frozen = js(C, 'docs/restart/implementation/A02/admission-evidence/closed-evidence.json')['artifacts']
    ft = tree(F)
    frozen_bodies = bodies([r['blob'] for r in frozen])
    assert len(frozen) == 1508
    for row in frozen:
        p = row['path']
        assert ct[p] == bt[p] == ft[p] == (row['mode'], 'blob', row['blob'])
        assert sha(frozen_bodies[row['blob']]) == row['sha256']
    old_text, new_text = read(B, 'plan/work-items.json').decode(), read(C, 'plan/work-items.json').decode()
    old, new = json.loads(old_text), json.loads(new_text)
    ot, nt = {t['id']: t for t in old['tasks']}, {t['id']: t for t in new['tasks']}
    changed = {key for key in ot if ot[key] != nt[key]}
    seven = {'A02', 'S03', 'T01', 'P02', 'H01', 'S04', 'B01'}
    assert len(ot) == len(nt) == 47 and changed == seven
    allowed = {'status', 'assignee', 'candidate_commits', 'current_checkpoint', 'input_commits',
               'input_reconciliation', 'assignment_record', 'github_issue', 'blocker'}
    task_deltas = {}
    for key in ot:
        fields = {k for k in set(ot[key]) | set(nt[key]) if ot[key].get(k) != nt[key].get(k)}
        assert fields <= allowed
        assert ot[key]['acceptance'] == nt[key]['acceptance'] and ot[key]['depends_on'] == nt[key]['depends_on']
        if fields:
            task_deltas[key] = sorted(fields)
    of, nf = fragments(old_text), fragments(new_text)
    assert all(of[key] == nf[key] for key in ot if key not in seven)
    assert old['resources'] == new['resources'] and len(new['resources']) == 16
    assert old['release_paths'] == new['release_paths'] and len(new['release_paths']) == 5
    assert {k for k in old if old[k] != new[k]} == {'as_of', 'revision', 'tasks'}
    assert set(new) - set(old) == {'adoption_reconciliation'} and new['revision'] == 14
    assert nt['A02']['status'] == 'running' and nt['A02']['current_checkpoint']['parent_criteria_closed'] == 0
    assert nt['S04']['status'] == 'blocked' and nt['S04']['assignee'] is None
    assert not nt['S04']['current_checkpoint']['active_author'] and nt['S04']['current_checkpoint']['no_alternate_model_retry']
    assert 'docs/restart/work-items.json' not in ct
    roots = {'nSealr/nsealr': ROOT, 'nSealr/hardware': Path('/home/tux/nsealr/hardware'),
             'nSealr/board-sdk': Path('/home/tux/nsealr/.restart-tools/goal/b01-final-review')}
    checkpoints = js(C, P + 'checkpoint-source-bindings.json')['tasks']
    assert set(checkpoints) == seven
    for name, rows in checkpoints.items():
        assert nt[name]['current_checkpoint']['artifacts'] == rows
        for row in rows:
            root = roots[row['repository']]
            body = read(row['commit'], row['path'], repo=root)
            entry = git('ls-tree', row['commit'], '--', row['path'], repo=root).decode().split('\t')[0].split()
            assert entry == [row['mode'], 'blob', row['blob']] and sha(body) == row['sha256']
            assert row['url'] == 'https://github.com/' + row['repository'] + '/blob/' + row['commit'] + '/' + row['path']
            source_checks.append({'task': name, 'commit': row['commit'], 'path': row['path'], 'sha256': sha(body)})
    assert len(source_checks) == 18
    links = []
    for path in ['docs/restart/README.md', 'docs/restart/implementation/handoff.md', P + 'handoff.md']:
        text = read(C, path).decode()
        for target in re.findall(r'(?<!!)\[[^\]]*\]\(([^)]+)\)', text):
            target = target.split('#')[0].split('?')[0]
            if not target or re.match(r'[a-zA-Z]+:', target):
                continue
            full = (ROOT / path).parent / unquote(target)
            assert full.resolve().is_relative_to(ROOT) and full.exists(), (path, target)
            links.append({'source': path, 'target': target})
    author_commands = []
    for folder in ['materialization', 'validation-01', 'validation-02', 'validation-03']:
        for row in js(C, P + folder + '/commands.json'):
            assert sha(read(C, P + folder + '/' + row['log'])) == row['sha256']
            author_commands.append({'folder': folder, 'command': row['command'], 'exit_code': row['exit_code']})
    full = subprocess.run(['git', '-C', str(ROOT), 'diff', '--check', B, C], capture_output=True)
    (HERE / 'candidate-whitespace.log').write_bytes(full.stdout + full.stderr)
    nonlog = subprocess.run(['git', '-C', str(ROOT), 'diff', '--check', B, C, '--', '.', ':(exclude)*.log'], capture_output=True)
    assert full.returncode == 2 and nonlog.returncode == 0
    warnings = {line.split(':', 1)[0] for line in full.stdout.decode().splitlines() if line.startswith('docs/') and ': ' in line}
    historical_warnings = set(js(C, P + 'whitespace-observation.json')['affected_files'])
    assert warnings == historical_warnings | {P + 'validation-03/00-complete-staged-whitespace-observation.log'}
    result = {'schema_version': 1, 'candidate_commit': C, 'candidate_tree': git('rev-parse', C + '^{tree}').decode().strip(),
              'base_product': B, 'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'python': sys.version.split()[0], 'copied_files_exact': len(copied), 'copy_counts': dict(zip(inventories, expected_counts)),
              'payload_preimages_unchanged': 73, 'payload_additions': 910, 'payload_replacements': 0,
              'coordinator_index_members': 38, 'all_coordinator_files_including_index': 39,
              'actual_candidate_files': len(ct), 'added_files': len(added), 'modified_existing': sorted(modified),
              'all_copied_source_mode_blob_bytes_sha256_verified': True,
              'frozen_files_verified': len(frozen), 'other_40_task_serialized_fragments_unchanged': True,
              'criteria_and_dependencies_unchanged': 47, 'closed_records_unchanged': ['R00', 'P01', 'S01', 'S02', 'E01', 'A01', 'O01'],
              'task_metadata_deltas': task_deltas, 'resources_unchanged': 16, 'release_records_unchanged': 5,
              'source_checkpoint_bindings': source_checks, 'current_local_links': links,
              'author_commands_hash_verified': author_commands, 'raw_whitespace_exit': full.returncode,
              'non_log_whitespace_exit': nonlog.returncode, 'preserved_log_warning_files': sorted(warnings),
              'historical_staged_log_warning_files': sorted(historical_warnings),
              'final_additional_warning_is_preserved_whitespace_check_log_itself': True,
              'task_closed': False, 'future_ci_claimed': False, 'result': 'PASS_exact_materialized_delivery_identity_and_invariants'}
    (HERE / 'probe-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['result', 'copied_files_exact', 'actual_candidate_files', 'added_files', 'frozen_files_verified']}))


if __name__ == '__main__':
    main()
