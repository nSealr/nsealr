"""Bounded source/archive/artifact checks before the ONE admitted pre-G replay."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CANDIDATE = '858eaf19a1f2b104112edb9842a479c035db301f'
BASE = 'f8adb7dd0b8cfb22f0b7d7c7cf5c7ad65104d683'
EARLY = 'f4d4d8c579dd1dddd7a8f22435ff5a2b2710a8c9'
NORMAL = '3022289131cdad899d9eea90dc5bb4c4897b6b25'
REUSE = ROOT.parent / 'qh01-python-rgb-lifecycle'
PREFIX = 'docs/restart/implementation/QH01/manual-port/python-rgb-composition/'
PACK = ROOT / (PREFIX + 'proof/lifecycle-cases')


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd)


def blob(ref, path):
    return git('show', ref + ':' + path)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def tree(ref, prefix=''):
    data = git('ls-tree', '-rz', '--full-tree', ref, *(['--', prefix] if prefix else []))
    result = {}
    for row in filter(None, data.split(b'\0')):
        meta, path = row.split(b'\t', 1); mode, kind, oid = meta.decode().split()
        result[path.decode()] = (mode, kind, oid)
    assert result
    return result


def main():
    old, current = tree(BASE), tree(CANDIDATE)
    changed = {p for p in old.keys() | current.keys() if old.get(p) != current.get(p)}
    harness = [PREFIX + 'run-composition.py', PREFIX + 'bridge-child.mjs']
    assert len(changed) == 14 and {p for p in changed if p in old} == set(harness + [PREFIX[:-1] + '-brief.md'])
    assert all(current[p] == old[p] for p in old if p not in changed)
    for p in harness:
        assert (ROOT / p).read_bytes() == blob(CANDIDATE, p) == blob(EARLY, p) == blob(NORMAL, p)
    before, after = [ast.parse(blob(ref, harness[0])) for ref in [BASE, CANDIDATE]]
    methods = []
    classes = [next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == 'Composition') for module in [before, after]]
    for name in ['__init__', 'record_node_wait', 'pump', 'attention', 'until', 'cleanup']:
        nodes = [next(n for n in c.body if isinstance(n, ast.FunctionDef) and n.name == name) for c in classes]
        assert ast.dump(nodes[0], include_attributes=False) == ast.dump(nodes[1], include_attributes=False)
        methods.append(name)
    manifest = read(PACK / 'artifact-manifest.json'); assert len(manifest['members']) == manifest['member_count'] == 13
    for row in manifest['members']:
        data = blob(CANDIDATE, row['path'])
        assert (len(data), sha(data), current[row['path']][0], current[row['path']][2]) == (row['bytes'], row['sha256'], row['mode'], row['git_blob'])
    inputs = read(PACK / 'inputs.json')
    for row in inputs['unchanged_eight_requirement_source_bindings'] + inputs['fixtures'] + inputs['current_harness']:
        data = blob(CANDIDATE, row['path']); assert sha(data) == row['sha256']
        if 'bytes' in row: assert len(data) == row['bytes']
    archives = {}
    contents = {}
    for name, count in [('early.tar.gz', 52), ('normal.tar.gz', 81)]:
        with tarfile.open(PACK / name) as archive:
            members = archive.getmembers(); assert len(members) == count + 1 and all(m.isfile() for m in members)
            data = {m.name: archive.extractfile(m).read() for m in members}; assert len(data) == count + 1
            rows = json.loads(data['artifact-manifest.json'])['members']
            assert len(rows) == count and {r['path'] for r in rows} == set(data) - {'artifact-manifest.json'}
            for row in rows: assert (len(data[row['path']]), sha(data[row['path']])) == (row['bytes'], row['sha256'])
            archives[name] = {'sha256': sha((PACK / name).read_bytes()), 'members_plus_self': [count, 1]}
            contents[name] = data
    early = contents['early.tar.gz']; cases = ['scan_null_after_settlement', 'scan_pending_timeout_after_settlement', 'fixture_cancel_B3_verified_preG']
    early_receipts = []
    for case in cases:
        command = json.loads(early[case + '-command.json']); result = json.loads(early[case + '/result.json'])
        assert command['source_commit'] == EARLY and command['wait_raw'] == command['exit_code'] == 0
        assert command['source_before'] == command['source_after'] == ''
        assert command['argv'][-2:] == ['--case', case] and result['case'] == case
        assert result['service_error'] == ('signer_transport_timeout' if case == cases[1] else 'signer_transport_failed')
        early_receipts.append({'case': case, 'command_sha256': sha(early[case + '-command.json']), 'result_sha256': sha(early[case + '/result.json'])})
    normal = contents['normal.tar.gz']; log = normal['make-pi-ci-01.log']
    assert len(log) == 494891 and sha(log) == 'aa21e0725c9656ce0375a18627a08c22d7decf7dbe575de029e97baff445382d'
    record = json.loads(normal['actual-composition-case.json']); build = json.loads(normal['actual-builder-record.json'])
    assert normal['actual-composition-case.json'] == (PACK / 'normal-actual-composition-case.json').read_bytes()
    command = json.loads(normal['make-pi-ci-01-command.json'])
    assert command['source_commit'] == NORMAL and command['exit_code'] == command['wait_raw'] == 0
    assert command['source_before'] == command['source_after'] == '' and len(record['argv']) == 15
    assert build['source_before'] == build['source_after'] and len(build['outputs']) == 10 and build['status'] == 0
    assert record['source_before'] == record['source_after'] and len(record['source_before']) == 60
    assert git('rev-parse', 'HEAD', cwd=REUSE).decode().strip() == CANDIDATE
    assert not git('status', '--porcelain', cwd=REUSE)
    for path, digest in record['source_before'].items():
        assert blob(CANDIDATE, path) == blob(NORMAL, path) == (ROOT / path).read_bytes() == (REUSE / path).read_bytes()
        assert sha(blob(CANDIDATE, path)) == digest
    assert record['generated_before'] == record['generated_after'] and len(record['generated_before']) == 62
    for path, digest in record['generated_before'].items(): assert sha((REUSE / path).read_bytes()) == digest
    assert build['outputs'] == {p: record['generated_before'][p] for p in build['outputs']}
    assert all(sha(blob(CANDIDATE, p)) == digest for p, digest in build['source_before'].items())
    packages = ['client', 'core', 'policy', 'protocol', 'qr', 'transport', 'framing']; links = []
    for name in packages:
        prefix = 'packages/' + name
        assert tree(CANDIDATE, prefix) == tree(BASE, prefix) == tree(NORMAL, prefix)
        assert (REUSE / prefix / 'package.json').read_bytes() == blob(CANDIDATE, prefix + '/package.json')
        parent = REUSE / ('packages/client/node_modules' if name == 'core' else 'apps/bridge/service/node_modules')
        link = parent / '@nsealr' / name
        assert link.resolve() == (REUSE / prefix).resolve()
        links.append({'path': str(link), 'resolved': str(link.resolve())})
    assert tree(CANDIDATE, 'vendor') == tree(NORMAL, 'vendor')
    decoder = json.JSONDecoder(); lines = log.decode().splitlines(); objects = []
    for i, line in enumerate(lines):
        if line.startswith('{'):
            try: item, _ = decoder.raw_decode('\n'.join(lines[i:]))
            except json.JSONDecodeError: continue
            if isinstance(item, dict): objects.append(item)
    workers = [o for o in objects if o.get('role') == 'public RGB worker build, initialization v2, not hardware qualification']
    assert len(workers) == 1; worker = workers[0]
    assert worker['argv'] == ['cargo', 'build', '--manifest-path', 'apps/pi/qr-worker/Cargo.toml', '--locked', '--offline', '--release', '--message-format=json']
    assert worker['CARGO_TARGET_DIR'] is None and len(worker['source']) == 6
    for path, digest in worker['source'].items(): assert sha(blob(CANDIDATE, path)) == digest and (REUSE / path).read_bytes() == blob(CANDIDATE, path)
    assert record['worker_initialization'] == {'path': worker['worker'], 'sha256': worker['sha256']}
    assert worker['sha256'] == '95f541ec0f05bf4849b71bd0507ca47eaa4a5f649696492ad48edcbc375c0df5'
    executable = Path(worker['worker']); assert executable == REUSE / 'apps/pi/qr-worker/target/release/nsealr-qr-worker'
    binary = executable.read_bytes(); assert sha(binary) == worker['sha256'] and os.access(executable, os.X_OK)
    assert binary[:6] == b'\x7fELF\x02\x01' and int.from_bytes(binary[18:20], 'little') == 62
    for row in inputs['tools'].values():
        data = Path(row['path']).read_bytes(); assert (len(data), sha(data)) == (row['bytes'], row['sha256'])
        assert data[:6] == b'\x7fELF\x02\x01' and int.from_bytes(data[18:20], 'little') == 62 and os.access(row['path'], os.X_OK)
    assert sha(Path(build['compiler']['path']).read_bytes()) == build['compiler']['sha256']
    result = {'role': 'Pre-execution source/artifact verification; no product process/build/install', 'candidate': CANDIDATE,
              'tree': git('rev-parse', CANDIDATE + '^{tree}').decode().strip(), 'base': BASE, 'early_source': EARLY, 'normal_source': NORMAL,
              'changed_paths': sorted(changed), 'unchanged_methods_AST': methods, 'all_other_base_postimages_exact': True,
              'manifest_members_plus_self': [13, 1], 'archives': archives, 'original_early_receipts': early_receipts,
              'normal_log_sha256': sha(log), 'normal_log_bytes': len(log), 'normal_actual_build': build,
              'actual_worker_producer': worker, 'worker_bytes': len(binary), 'runtime_source60': record['source_before'],
              'prepared_generated62': record['generated_before'], 'same_root_for_bridge_and_packages': str(REUSE), 'module_identity_links': links,
              'tools': inputs['tools'], 'versions_from_source_bound_normal_archive': json.loads(normal['versions.json']),
              'fixtures': inputs['fixtures'], 'case': 'fixture_cancel_B3_verified_preG',
              'expected': {'service_error': 'signer_transport_failed', 'O_exit_raw': [2, 512], 'W_exit_raw_allowed': [[71, 18176], [-9, 9]],
                           'commands': ['P', 'X'], 'G_bytes': 0, 'W_image_bytes': 0, 'API_release_bytes': 0, 'Node_exit_raw': [0, 0],
                           'reply': '{"v":1,"event":"cancelled"}\n', 'reply_bytes': 28, 'scan_count': 0, 'close_count': 1},
              'new_compiler_or_W_C_builds': 0, 'negative_cases_in_normal_ci': False}
    (HERE / 'preflight.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'preflight': 'PASS', 'source60': 60, 'generated62': 62, 'worker': worker['sha256'], 'case': result['case']}))


if __name__ == '__main__':
    main()
