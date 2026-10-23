"""Fixed RGB experiment proof correspondence, not another decoder campaign."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = '5fa5ec3afd0cf1f343743fe347b61728a242b15c'
NEW = '9220db123eb7ab9c02ef0d407dc6fc8fa3927bf2'
EXECUTED = '5b69e1655c461624218b6df0e3d112b3dc726114'
P = 'docs/restart/implementation/QH01/rgb-input/'
OLD = 'docs/restart/implementation/QH01/rust-qr-worker/'
AUTHOR = Path('/home/tux/nsealr/.restart-tools/goal/qh01-linux-worker-experiment')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def blob(path, commit=NEW):
    return git('show', f'{commit}:{path}')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def doc(path):
    return json.loads(blob(path))


manifest = doc(P + 'artifact-manifest.json')
assert len(manifest['artifacts']) == manifest['member_count'] == 67
paths = {x.decode() for x in git('ls-tree', '-rz', '--name-only', NEW, '--', P).split(b'\0') if x}
assert len({x['path'] for x in manifest['artifacts']}) == 67
assert paths == {x['path'] for x in manifest['artifacts']} | {P + 'artifact-manifest.json'}
for x in manifest['artifacts']:
    data = blob(x['path'])
    assert sha(data) == x['sha256'] and len(data) == x['bytes']
    assert git('ls-tree', NEW, '--', x['path']).decode().split()[0] == x['mode'] == '100644'
delta = [x.split('\t') for x in git('diff', '--name-status', BASE, NEW).decode().splitlines()]
assert len(delta) == 68 and all(status == 'A' and path in paths for status, path in delta)
result = doc(P + 'result.json')
for name in ('brief.md', 'expectations.json', 'parameters.json', 'source-decision.json'):
    assert blob(P + name) == blob(P + name, '7d8d705ec8792e7f13f3d71cda9b1fce6541b214')
for name in ('Cargo.toml', 'Cargo.lock'):
    assert blob(P + name) == blob(OLD + name, BASE)
params = doc(P + 'parameters.json')
old_params = json.loads(blob(OLD + 'parameters.json', BASE))
assert params['baseline'] == old_params['baseline'] and params['core_bytes'] == old_params['core_bytes'] == 0
for path, digest in result['source_hashes'].items():
    assert blob(path) == blob(path, EXECUTED) and sha(blob(path)) == digest
decision = doc(P + 'source-decision.json')
for path, digest in decision['old_bindings'].items():
    assert sha(blob(path, BASE)) == digest and blob(path) == blob(path, BASE)
cache = doc(P + 'cache-source.json')
registry = json.loads(blob(OLD + 'dependency-register.json', BASE))
assert cache['exact_archive_rows'] == registry['packages'] and len(cache['exact_archive_rows']) == 11
for row in cache['exact_archive_rows']:
    archives = list((Path(cache['new_cache']) / 'registry/cache').glob('*/' + row['name'] + '-' + row['version'] + '.crate'))
    assert len(archives) == 1
    data = archives[0].read_bytes()
    assert sha(data) == row['archive_sha256'] and len(data) == row['archive_bytes']
old_result = json.loads(blob(OLD + 'result.json', BASE))
assert sha((AUTHOR / old_result['binary']['ignored_local_path']).read_bytes()) == old_result['binary']['sha256']
binary = AUTHOR / result['binary']['path']
assert sha(binary.read_bytes()) == result['binary']['sha256'] and binary.stat().st_size == result['binary']['bytes'] == 669072

metamorphism = result['metamorphism']
original = blob(metamorphism['source_path'], metamorphism['source_commit'])
assert sha(original) == metamorphism['source_sha256'] and len(original) == 172800
tinted = bytearray()
counts = {'black': 0, 'white': 0}
for i in range(0, len(original), 3):
    pixel = original[i:i+3]
    assert pixel in (b'\0\0\0', b'\xff\xff\xff')
    dark = pixel == b'\0\0\0'
    counts['black' if dark else 'white'] += 1
    tinted.extend((0, 16, 0) if dark else (240, 255, 255))
assert counts == metamorphism['source_pixel_counts'] == {'black': 34569, 'white': 23031}
assert sha(tinted) == metamorphism['derived_sha256'] == '47929068f16631b1a6624b95fed8fde8db3f2b50483e89a24529e0fee8ae210c'
assert len(tinted) == metamorphism['derived_bytes'] == 172800
for directory in ('build-evidence',):
    for name in ('unit-command.json', 'candidate-command.json'):
        command = doc(P + directory + '/' + name)
        assert command['source_commit'] == EXECUTED and command['exit_code'] == 0
        for path, digest in command['source_hashes'].items():
            assert sha(blob(path, EXECUTED)) == digest
for run in result['actual_runs']:
    command = doc(run['directory'] + '/command.json')
    assert command['exit_code'] == 0 and command['source_commit'] == EXECUTED
    assert sha(blob(run['directory'] + '/command.json')) == run['command_sha256']
    assert sha(blob(run['directory'] + '/summary.json')) == run['summary_sha256']
    for path, digest in command['source_hashes'].items():
        assert sha(blob(path, EXECUTED)) == digest
for case in result['stable_cases']:
    assert sha(blob(case['trace'])) == case['trace_sha256'] and case['passed']
assert len(result['stable_cases']) == 6

Path(__file__).with_name('validation.json').write_text(json.dumps({
    'candidate': NEW, 'tree': git('rev-parse', NEW + '^{tree}').decode().strip(),
    'reviewer': '/root', 'verdict': 'PASS_RGB_EXPERIMENT_SOURCE_AND_PROOF_CORRESPONDENCE_ONLY',
    'checked': {'manifest_members': 67, 'new_paths': 68, 'precode_files_exact': 4,
                'executed_source_files': 4, 'Cargo_manifest_lock_equal_base': True,
                'baseline13_CORE_equal': True, 'unchanged_locked_archives': 11,
                'old_author_ELF_unchanged': True, 'new_author_ELF_bytes': 669072,
                'in_memory_tint_source_and_derived_hashes_exact': True,
                'unit_and_candidate_build_receipts': 2, 'image_command_summary_bindings': 2,
                'final_trace_bindings': 6},
    'new_build_or_decoder_executions': 0,
    'scope': 'The tint was recomputed only as a source-data/hash check and was not written or decoded. A02 separately executed unit/build/six-case review. No camera, all-input decoder bound, final cap/framing/route, secret isolation, target or physical/task acceptance.'
}, indent=2) + '\n')
print('PASS RGB packet:67 members/68 new paths,11 archives,original and derived input hashes,old ELF unchanged,six trace bindings. No build or decoder run.')
