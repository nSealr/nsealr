"""Bounded Git/AST/archive inspection, no product imports or product execution."""
import ast
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).parent
CANDIDATE = '5b32621d24bf06fe523f28f83ac51ebce6d870fc'
BASE = 'b6d07a4aff913249a06bf1e7ea31cb6265ea0cc0'
EXECUTED = '8a80b256455deb8b9ae3a4e6115c13a3e64d328b'
P = 'docs/restart/implementation/QH01/manual-port/python-rgb-composition/'
R = 'docs/restart/implementation/reviews/QH01-python-rgb-composition/'
EXCHANGE = 'docs/restart/implementation/QP01/request-engine/exchange.py'
CHECKER = 'docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def blob(ref, path):
    return git('show', ref + ':' + path)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def tree(ref, prefix=''):
    rows = git('ls-tree', '-rz', '--full-tree', ref, *(['--', prefix] if prefix else [])).split(b'\0')
    result = {}
    for row in filter(None, rows):
        info, path = row.split(b'\t', 1)
        mode, kind, oid = info.decode().split()
        result[path.decode()] = {'mode': mode, 'kind': kind, 'git_blob': oid}
    assert result
    return result


def dump(node):
    return ast.dump(node, include_attributes=False)


def function(module, name):
    return next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == name)


def main():
    assert git('rev-parse', 'HEAD').decode().strip() == CANDIDATE
    current, previous = tree(CANDIDATE), tree(BASE)
    changed = {p for p in current.keys() | previous.keys() if current.get(p) != previous.get(p)}
    modified = {p for p in changed if p in previous}
    assert modified == {EXCHANGE, CHECKER, 'tools/bridge/build_packages.mjs', 'apps/pi/tests/test_engine_adapter.py',
                        P[:-1] + '-brief.md', 'docs/restart/README.md', 'plan/work-items.json'}
    assert len(changed) == 46 and len(changed - modified) == 39
    source_paths = [EXCHANGE, 'tools/bridge/build_packages.mjs', 'apps/pi/tests/test_engine_adapter.py']
    assert all(current[p] == tree(EXECUTED)[p] for p in source_paths)
    unchanged = ['apps/pi/app/nsealr_vault/qr_owner_adapter.py', 'apps/pi/app/nsealr_vault/qr_worker.py',
                 P + 'run-composition.py', P + 'bridge-child.mjs', P + 'test_attention_reporting.py',
                 'Makefile', 'tools/bridge/package_set.mjs']
    assert all(current[p] == previous[p] for p in unchanged)
    for prefix in ['apps/bridge/service', 'packages', 'crates', 'apps/pi/qr-worker']:
        assert tree(CANDIDATE, prefix) == tree(BASE, prefix)
    manifests = []
    for path, count in [(P + 'proof/normal-ci/artifact-manifest.json', 12),
                        (R + 'capture-extension/artifact-manifest.json', 9),
                        ('docs/restart/implementation/reviews/QP01-python-owner-adoption/artifact-manifest.json', 7)]:
        m = json.loads(blob(CANDIDATE, path)); assert len(m['members']) == m['member_count'] == count
        assert len({r['path'] for r in m['members']}) == count
        for r in m['members']:
            raw = blob(CANDIDATE, r['path'])
            assert (len(raw), sha(raw), current[r['path']]['mode']) == (r['bytes'], r['sha256'], r['mode'])
            if 'git_blob' in r:
                assert current[r['path']]['git_blob'] == r['git_blob']
        manifests.append({'path': path, 'sha256': sha(blob(CANDIDATE, path)), 'members': count, 'including_self': count + 1})
    imports = []
    for ref, prefix in [('1e0453fe7af476275b749fbff116899093cbeced', R),
                        ('e1dc11b05f4aac1a1fc423030f2a54c116fef656', 'docs/restart/implementation/reviews/QP01-python-owner-adoption/')]:
        original = tree(ref, prefix)
        assert all(current[p] == row for p, row in original.items())
        imports.append({'source': ref, 'prefix': prefix, 'exact_paths': len(original)})
    lifecycle = R + 'lifecycle-expectations.json'
    assert current[lifecycle] == tree('5138d835c55eccc8826a770a6113d4ca8e53f5fd')[lifecycle]
    for prefix in [P + 'proof/normal-ci/']:
        original = tree('e9e198a077022671be95a59cf50ce4056f7b225e', prefix)
        assert all(current[p] == row for p, row in original.items())
        imports.append({'source': 'e9e198a077022671be95a59cf50ce4056f7b225e', 'prefix': prefix, 'exact_paths': len(original)})
    old, new = [ast.parse(blob(ref, EXCHANGE)) for ref in [BASE, CANDIDATE]]
    for name in ['source_binding', 'build_artifact', 'provision', 'exchange', 'main']:
        assert dump(function(old, name)) == dump(function(new, name))
    a, b = function(old, 'ci'), function(new, 'ci')
    assert len(b.body) == len(a.body) + 2
    assert [dump(n) for n in a.body] == [dump(n) for n in b.body[:-2]]
    old, new = [ast.parse(blob(ref, 'apps/pi/tests/test_engine_adapter.py')) for ref in [BASE, CANDIDATE]]
    oldclass = next(n for n in old.body if isinstance(n, ast.ClassDef) and n.name == 'ProvisioningControls')
    newclass = next(n for n in new.body if isinstance(n, ast.ClassDef) and n.name == 'ProvisioningControls')
    assert [n.name for n in oldclass.body if isinstance(n, ast.FunctionDef)] == [n.name for n in newclass.body if isinstance(n, ast.FunctionDef)]
    new.body[new.body.index(newclass)] = oldclass
    assert dump(old) == dump(new)
    old, new = [ast.parse(blob(ref, CHECKER)) for ref in [BASE, CANDIDATE]]
    new.body.remove(function(new, 'verify_qh01_composition'))
    imp = next(n for n in new.body if isinstance(n, ast.Import) and any(a.name == 'base64' for a in n.names))
    imp.names = [a for a in imp.names if a.name != 'base64']
    product = function(new, 'verify_product')
    calls = [n for n in product.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
             and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == 'update'
             and n.value.args and isinstance(n.value.args[0], ast.Call)
             and isinstance(n.value.args[0].func, ast.Name) and n.value.args[0].func.id == 'verify_qh01_composition']
    assert len(calls) == 1; product.body.remove(calls[0])
    assert dump(old) == dump(new)
    builder_old, builder_new = [blob(ref, 'tools/bridge/build_packages.mjs').decode() for ref in [BASE, CANDIDATE]]
    for start, end in [('const packageOrder = [', '\n];'), ('  const args = [', '\n  ];')]:
        assert builder_old.split(start, 1)[1].split(end, 1)[0] == builder_new.split(start, 1)[1].split(end, 1)[0]
    graphs = [json.loads(blob(ref, 'plan/work-items.json')) for ref in [BASE, CANDIDATE]]
    tasks = [{t['id']: t for t in g.pop('tasks')} for g in graphs]
    assert graphs[0] == graphs[1] and len(tasks[0]) == len(tasks[1]) == 47
    changed_tasks = []
    for key, before in tasks[0].items():
        after = tasks[1][key]
        fields = [k for k in before.keys() | after.keys() if before.get(k) != after.get(k)]
        if fields:
            assert key in ['QH01', 'QP01'] and set(fields) == {'current_checkpoint', 'result_artifacts'}
            changed_tasks.append({'id': key, 'changed_fields': sorted(fields)})
        for row in after.get('result_artifacts', []):
            if row not in before.get('result_artifacts', []):
                assert sha(blob(CANDIDATE, row['path'])) == row['sha256']
    archive = P + 'proof/normal-ci/evidence.tar.gz'
    with tarfile.open(fileobj=io.BytesIO(blob(CANDIDATE, archive))) as t:
        members = t.getmembers(); assert len(members) == 91 and all(m.isfile() for m in members)
        names = [m.name for m in members]; assert len(set(names)) == 91
        am = json.load(t.extractfile('artifact-manifest.json'))
        assert len(am['members']) == 90 and {r['path'] for r in am['members']} == set(names) - {'artifact-manifest.json'}
        for row in am['members']:
            raw = t.extractfile(row['path']).read()
            assert (len(raw), sha(raw)) == (row['bytes'], row['sha256'])
        raw = t.extractfile('make-pi-ci-01.log').read()
        assert len(raw) == 496870 and sha(raw) == '63382b6d98cbe5bcb63bd23e207363f439187600bd9f13a161019330f9dc02ee'
        (OUT / '.runtime').mkdir(exist_ok=True)
        (OUT / '.runtime/original-make-pi-ci-01.log').write_bytes(raw)
        for name in ['actual-builder-record.json', 'actual-composition-case.json', 'make-pi-ci-01-command.json', 'same-run-summary.json']:
            assert t.extractfile(name).read() == blob(CANDIDATE, P + 'proof/normal-ci/' + name)
    result = {'role': 'Static Git/AST/archive inspection only; no product execution', 'candidate': CANDIDATE,
              'tree': git('rev-parse', CANDIDATE + '^{tree}').decode().strip(), 'base': BASE, 'executed_runtime_source': EXECUTED,
              'changed_paths': sorted(changed), 'modified_existing': sorted(modified), 'new_paths': len(changed - modified),
              'source_bindings': [{'path': p, **current[p], 'sha256': sha(blob(CANDIDATE, p))} for p in source_paths + [CHECKER, R + 'test_capture_extension.py']],
              'unchanged_harness_and_product_subtrees': True, 'imported_exact_packets': imports,
              'lifecycle_expectations_exact_informative_only_not_self_reviewed': True, 'manifests': manifests,
              'legacy_checker_whole_AST_restored_by_only_three_removals': True, 'original_ci_AST_prefix_and_other_functions_exact': True,
              'unchanged_test_module_after_restoring_only_two_method_ProvisioningControls': True,
              'builder_options_and_package_order_exact': True, 'graph_tasks': 47, 'changed_task_fields': changed_tasks,
              'other45_tasks_and_all_other_fields_including_formal_sets_exact': True,
              'archive': {'path': archive, 'sha256': sha(blob(CANDIDATE, archive)), 'regular_members': 91, 'manifest_members': 90,
                          'log_bytes': len(raw), 'log_sha256': sha(raw), 'same_run_outer_copies_exact': 4}}
    (OUT / 'checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'static_checks': 'PASS', 'candidate': CANDIDATE, 'changed_paths': len(changed), 'archive_members': 91}))


if __name__ == '__main__':
    main()
