"""Static delta/source/proof inspection only; no imports of product code."""
import ast
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).parent
HEAD = 'f8adb7dd0b8cfb22f0b7d7c7cf5c7ad65104d683'
BASE = '5b32621d24bf06fe523f28f83ac51ebce6d870fc'
FIX = 'eaf0265543ff9d79f1495ed59993e2e058f29835'
CHECKER = 'docs/restart/implementation/QP01/host-coordinator/cold-delivery/verify-cold-capture.py'
CONTROL = 'docs/restart/implementation/reviews/QH01-python-rgb-composition/test_capture_extension.py'
OLD = 'docs/restart/implementation/reviews/QH01-python-rgb-composition-integration/'
PACK = OLD + 'full-gate-correction/'
ORACLE = 'docs/restart/implementation/QH01/manual-port/python-rgb-composition/proof/normal-ci/full-gate-build-oracle.json'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def raw(ref, path):
    return git('show', ref + ':' + path)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tree(ref, prefix=''):
    rows = git('ls-tree', '-rz', '--full-tree', ref, *(['--', prefix] if prefix else [])).split(b'\0')
    result = {}
    for row in filter(None, rows):
        meta, path = row.split(b'\t', 1); mode, kind, oid = meta.decode().split()
        result[path.decode()] = (mode, kind, oid)
    assert result
    return result


def main():
    assert git('rev-parse', 'HEAD').decode().strip() == HEAD
    before, after = tree(BASE), tree(HEAD)
    changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
    assert {p for p in changed if p in before} == {CHECKER, CONTROL, 'plan/work-items.json'}
    assert len(changed) == 31
    for p in [CHECKER, CONTROL]:
        assert after[p] == tree(FIX)[p]
    original = tree('10abbd91cd2444e596c1633cea70df21053206d9', OLD)
    assert len(original) == 14 and all(after[p] == row for p, row in original.items())
    oracle = json.loads(raw(HEAD, ORACLE))
    assert raw(HEAD, ORACLE) == raw('2db4fc8595869ed0bdb48d754ba447554d96b425', ORACLE)
    assert len(oracle['source_references']) == 26
    for p, row in oracle['source_references'].items():
        assert raw(HEAD, p) == raw(BASE, p) == raw(oracle['author_source'], p)
        assert sha(raw(HEAD, p)) == row['sha256']
    runner = ast.parse(raw(HEAD, 'tests/integration/run.py'))
    step_node = next(n for n in runner.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PRODUCT_STEPS' for t in n.targets))
    steps = ast.literal_eval(step_node.value); assert len(steps) == 17
    callsites = []
    for entry in oracle['post_case_callsites']:
        position = entry['integration_position']; original_number, module = steps[position - 1]
        assert (original_number, module) == (entry['original_recipe'], entry['module'])
        path = 'tests/integration/' + module + '.py'; module_ast = ast.parse(raw(HEAD, path))
        main_ast = next(n for n in module_ast.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        calls = [n for n in ast.walk(module_ast) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'build_pnpm_workspace']
        assert len(calls) == 1 and calls[0].lineno == entry['call_line']
        assert any(isinstance(n, ast.Expr) and n.value is calls[0] for n in main_ast.body)
        assert len(calls[0].args) == 1 and isinstance(calls[0].args[0], ast.Name) and calls[0].args[0].id == 'COMPANION'
        assert any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'COMPANION' for t in n.targets)
                   and isinstance(n.value, ast.Name) and n.value.id == 'ROOT' for n in module_ast.body)
        callsites.append({'position': position, 'path': path, 'line': calls[0].lineno})
    assert [c['position'] for c in callsites] == [*range(3, 16), 17]
    for entry in oracle['integration_steps_without_build']:
        assert tuple(steps[entry['integration_position'] - 1]) == (entry['original_recipe'], entry['module'])
        module_ast = ast.parse(raw(HEAD, 'tests/integration/' + entry['module'] + '.py'))
        assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'build_pnpm_workspace' for n in ast.walk(module_ast))
    current = ast.parse(raw(HEAD, CHECKER))
    current.body = [n for n in current.body if not isinstance(n, ast.FunctionDef) or n.name != 'verify_qh01_composition']
    for node in current.body:
        if isinstance(node, ast.Import):
            node.names = [n for n in node.names if n.name not in ['ast', 'base64']]
    product = next(n for n in current.body if isinstance(n, ast.FunctionDef) and n.name == 'verify_product')
    extra = [n for n in product.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and n.value.args
             and isinstance(n.value.args[0], ast.Call) and isinstance(n.value.args[0].func, ast.Name)
             and n.value.args[0].func.id == 'verify_qh01_composition']
    assert len(extra) == 1; product.body.remove(extra[0])
    legacy = ast.parse(raw('da8c06aa30a460c1849a1f96f62862259640bf19', CHECKER))
    assert ast.dump(current, include_attributes=False) == ast.dump(legacy, include_attributes=False)
    manifest = json.loads(raw(HEAD, PACK + 'artifact-manifest.json'))
    assert len(manifest['members']) == manifest['member_count'] == 15
    for row in manifest['members']:
        data = raw(HEAD, row['path'])
        assert (len(data), sha(data), after[row['path']][0], after[row['path']][2]) == (row['bytes'], row['sha256'], row['mode'], row['git_blob'])
    graphs = [json.loads(raw(ref, 'plan/work-items.json')) for ref in [BASE, HEAD]]
    tasks = [{t['id']: t for t in g.pop('tasks')} for g in graphs]
    assert graphs[0] == graphs[1] and len(tasks[0]) == len(tasks[1]) == 47
    for name, a in tasks[0].items():
        b = tasks[1][name]; fields = {k for k in a.keys() | b.keys() if a.get(k) != b.get(k)}
        assert not fields or (name in ['QH01', 'QP01'] and fields <= {'current_checkpoint', 'result_artifacts'})
        for row in b.get('result_artifacts', []):
            if row not in a.get('result_artifacts', []): assert sha(raw(HEAD, row['path'])) == row['sha256']
    archive = raw(HEAD, PACK + 'evidence.tar.gz')
    with tarfile.open(fileobj=io.BytesIO(archive)) as t:
        members = t.getmembers(); assert len(members) == 98 and all(m.isfile() for m in members)
        names = [m.name for m in members]; assert len(set(names)) == 98
        archived = json.load(t.extractfile('archive-manifest.json'))['members']
        assert len(archived) == 97 and {m['path'] for m in archived} == set(names) - {'archive-manifest.json'}
        for row in archived:
            data = t.extractfile(row['path']).read(); assert (len(data), sha(data)) == (row['bytes'], row['sha256'])
        mapping = {'actual-build-positions.json': 'actual-build-positions.json', 'early-controls.json': 'capture-fixed-early-controls-01.json',
                   'full-command.json': 'gate/commands.json', 'full-controls.json': 'capture-fixed-full-controls-01.json',
                   'full-result.json': 'result.json', 'original-red-receipt.json': 'capture-original-01-receipt.json',
                   'original-red.stderr.log': 'capture-original-01.stderr', 'source-aware-green.json': 'capture-fixed-full-01.stdout'}
        for outer, inner in mapping.items(): assert raw(HEAD, PACK + outer) == t.extractfile(inner).read()
        log = t.extractfile('gate/00-product-ci.log').read()
        assert len(log) == 751120 and sha(log) == '21965321b2537b213549f04e4fdcf266a8932877963ab297d903a68fea96c244'
        # Parse only the one source-binding record, without importing/running the checker.
        cases = [json.loads(line)['qh01_composition_case'] for line in log.decode().splitlines() if line.startswith('{"qh01_composition_case":')]
        assert len(cases) == 1 and len(cases[0]['source_before']) == 60
        assert cases[0]['source_before'] == cases[0]['source_after']
        for path, expected in cases[0]['source_before'].items():
            assert raw(HEAD, path) == raw(BASE, path) and sha(raw(HEAD, path)) == expected
        (OUT / '.runtime').mkdir(exist_ok=True); (OUT / '.runtime/original-full.log').write_bytes(log)
    result = {'role': 'Static source/AST/manifest/archive review; no product or checker execution', 'candidate': HEAD,
              'tree': git('rev-parse', HEAD + '^{tree}').decode().strip(), 'product_source': BASE, 'checker_source': FIX,
              'changed_existing_paths': [CHECKER, CONTROL, 'plan/work-items.json'], 'changed_total': len(changed),
              'original10ab_review14_files_exact': True, 'oracle26_source_bindings_exact': True,
              'source_derived_direct_main_callsites': callsites, 'zero_build_positions': [1, 2, 16],
              'legacy_f129_whole_AST_restored': True, 'formal47_other45_and_other_graph_fields_exact': True,
              'manifest_members_plus_self': [15, 1], 'archive_members_plus_self': [97, 1], 'selected_raw_copies_exact': mapping,
              'archive_sha256': sha(archive), 'log_bytes': len(log), 'log_sha256': sha(log), 'runtime60_postimages_exact5b': True,
              'checker_sha256': sha(raw(HEAD, CHECKER)), 'control_sha256': sha(raw(HEAD, CONTROL))}
    (OUT / 'checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'static_delta': 'PASS', 'oracle_sources': 26, 'direct_later_build_calls': 14, 'archive_members': 98}))


if __name__ == '__main__':
    main()
