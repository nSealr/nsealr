#!/usr/bin/env python3
"""Exact-object adoption audit. No candidate or source checkout mutation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
CANDIDATE = "3fd7291c31128a5c3b32f68ae34e00e2e74911f5"
BASE = "7b5553685dac56029a4379be12054154b6b5e0b5"
TESTED = "f4c35c1c455528501c91747eb503dc78b4050f9d"
S01 = "docs/restart/implementation/S01/"


def git(*args, repo=ROOT):
    return subprocess.check_output(["git", *args], cwd=repo)


def blob(path, commit=CANDIDATE, repo=ROOT):
    return git("show", f"{commit}:{path}", repo=repo)


def doc(path, commit=CANDIDATE):
    return json.loads(blob(path, commit))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def oid(commit, path):
    return git("rev-parse", f"{commit}:{path}").decode().strip()


def main():
    before = doc("docs/restart/work-items.json", BASE)
    after = doc("docs/restart/work-items.json")
    assert before['revision'] == 11 and after['revision'] == 12
    assert {k:v for k,v in before.items() if k not in ('revision','tasks')} == {k:v for k,v in after.items() if k not in ('revision','tasks')}
    b = {t['id']:t for t in before['tasks']}
    a = {t['id']:t for t in after['tasks']}
    assert set(b) == set(a) and len(a) == 47
    allowed = {'S01': {'status','reviewer','review_verdict','candidate_commits','input_commits','reviewed_candidate_commits','reviewed_input_commits','result_manifest','result_artifacts'},
               'H01': {'status','assignee','assignment_record','github_issue','input_commits'}, 'T01': {'github_issue'}}
    changes = {}
    for task in a:
        keys = {k for k in set(a[task]) | set(b[task]) if a[task].get(k) != b[task].get(k)}
        assert keys == allowed.get(task, set()), (task, keys)
        if keys:
            changes[task] = sorted(keys)
    assert a['S01']['status'] == 'verified' and 'integration' not in a['S01']
    result = doc(S01 + 'result.json')
    for key in ('input_commits','candidate_commits','acceptance'):
        assert result[key] == a['S01'][key]
    assert result['review'] == {'assignee':a['S01']['assignee'],'reviewer':a['S01']['reviewer'],'verdict':a['S01']['review_verdict']}
    assert [r['index'] for r in result['acceptance_results']] == list(range(5))
    indexed = {r['path']:r['sha256'] for r in a['S01']['result_artifacts']}
    assert len(indexed) == len(a['S01']['result_artifacts']) == 388
    for path, expected in indexed.items():
        assert path.startswith('docs/restart/implementation/') and digest(blob(path)) == expected
    for row in result['acceptance_results']:
        assert row['outcome'] == 'pass' and row['proof_kind'] == 'executed_test'
        assert row['evidence_paths'] and all(p in indexed for p in row['evidence_paths'])
    copies = doc(S01 + 'source-evidence-index.json')['files']
    assert len(copies) == len({r['path'] for r in copies}) == 151
    for row in copies:
        repo = Path('/home/tux/nsealr') / row['repository'].split('/')[1]
        source = blob(row['source_path'], row['commit'], repo)
        assert source == blob(row['path']) and digest(source) == row['sha256'] and len(source) == row['bytes']
        header, path = git('ls-tree', row['commit'], '--', row['source_path'], repo=repo).decode().rstrip('\n').split('\t')
        mode, kind, source_oid = header.split()
        assert path == row['source_path'] and kind == 'blob' and mode == row['mode'] and source_oid == row['source_blob']
        assert git('ls-tree', CANDIDATE, '--', row['path']).decode().split()[0] == mode
        assert row['source_url'] == f"https://github.com/{row['repository']}/blob/{row['commit']}/{row['source_path']}"
    selected_paths = set(git('ls-tree','-r','--name-only',CANDIDATE,'--',S01+'source-evidence').decode().splitlines())
    assert selected_paths == {r['path'] for r in copies} | {S01+'source-evidence/NOTICE.md'}
    objects = {}
    for line in git('ls-tree', TESTED).decode().splitlines():
        header, path = line.split('\t')
        if path not in ('docs','tools'):
            objects[path] = oid(TESTED,path)
            assert oid(CANDIDATE,path) == objects[path]
    assert len(objects) == 20
    assert oid(CANDIDATE,'tools/baseline') == oid(TESTED,'tools/baseline')
    assert oid(CANDIDATE,'tools/cad') == oid(BASE,'tools/cad')
    for row in doc(S01+'adoption-correspondence.json')['product_and_tool_bindings']:
        assert oid(CANDIDATE,row['path']) == row['object'] == oid(row.get('equal_commit',TESTED),row['path'])
    preserved = {}
    for original, prefix in ((TESTED,S01),('30ae87dd31c3c292b22f4758d4fad9fea63a7b37','docs/restart/implementation/reviews/S01-integration/'),
                             ('a3dec9063b81a981176b48b00e5f59d8b6f4288e','docs/restart/implementation/reviews/S01-provenance/')):
        paths = git('ls-tree','-r','--name-only',original,'--',prefix).decode().splitlines()
        assert all(blob(path) == blob(path,original) for path in paths)
        preserved[prefix] = len(paths)
    for index, count in (('artifacts.json',75),('provenance-followup-artifacts.json',131)):
        entries = doc(S01+index)
        assert len(entries) == count and all(digest(blob(r['path'])) == r['sha256'] for r in entries)
    approval = S01+'integration-spec-review.json'
    assert blob(approval) == blob(approval,BASE) == blob(approval,'8993f773f3bb69d7e6aece69ca8308a8f6310101')
    audit = dict(candidate=CANDIDATE,base=BASE,tested=TESTED,recorded_at=datetime.now(timezone.utc).isoformat(),
        passed=True,source_copy_bindings_verified=151,copied_bytes=sum(r['bytes'] for r in copies),
        result_artifacts_verified=388,acceptance_indices=[0,1,2,3,4],graph_revision=[11,12],
        allowed_task_field_changes=changes,all_47_contracts_preserved=True,all_other_global_policy_fields_preserved=True,
        product_top_level_objects=objects,baseline_tree=oid(CANDIDATE,'tools/baseline'),cad_tree=oid(CANDIDATE,'tools/cad'),
        preserved_source_and_review_file_counts=preserved,original_75_and_followup_131_indexes_verified=True,
        skipped_original_approval_exactly_preserved=True,
        legal_notice_sha256=digest(blob(S01+'source-evidence/NOTICE.md')),
        candidate_metadata_bindings={p:digest(blob(p)) for p in ('docs/restart/work-items.json',S01+'result.json',S01+'adoption-correspondence.json',S01+'source-evidence-index.json')})
    (HERE/'audit-result.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit,indent=2))


if __name__ == '__main__':
    main()
