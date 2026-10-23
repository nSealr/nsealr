"""Source, archive and proof correspondence only; never runs the QR worker."""
import hashlib
import json
import subprocess
import tarfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
COMMIT = '5fa5ec3afd0cf1f343743fe347b61728a242b15c'
EXECUTED = '142135cd70f920e104aa01841ceeeca794256440'
P = 'docs/restart/implementation/QH01/rust-qr-worker/'
AUTHOR = Path('/home/tux/nsealr/.restart-tools/goal/qh01-linux-worker-experiment')
CACHE = AUTHOR / P / '.runtime/cargo/registry/cache'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def blob(path, commit=COMMIT):
    return git('show', f'{commit}:{path}')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def doc(path):
    return json.loads(blob(path))


m = doc(P + 'artifact-manifest.json')
assert len(m['artifacts']) == m['member_count'] == 117
paths = {x.decode() for x in git('ls-tree', '-rz', '--name-only', COMMIT, '--', P).split(b'\0') if x}
assert len({x['path'] for x in m['artifacts']}) == 117
assert paths == {x['path'] for x in m['artifacts']} | {P + 'artifact-manifest.json'}
for x in m['artifacts']:
    data = blob(x['path'])
    assert sha(data) == x['sha256'] and len(data) == x['bytes'], x['path']
    assert git('ls-tree', COMMIT, '--', x['path']).decode().split()[0] == x['mode'] == '100644'
delta = [x.split('\t') for x in git('diff', '--name-status', '06d213fd46e654bfe2ac43e4a88963a346d35973', COMMIT).decode().splitlines()]
assert len(delta) == 118 and all(status == 'A' and path in paths for status, path in delta)
for name in ('.gitignore', 'brief.md', 'expectations.json', 'parameters.json', 'source-bindings.json'):
    assert blob(P + name) == blob(P + name, '0751088f'), name
params = doc(P + 'parameters.json')
old_params = doc('docs/restart/implementation/QH01/linux-worker-experiment/parameters.json')
assert params['baseline'] == old_params['baseline']
bindings = doc(P + 'source-bindings.json')
assert len(bindings['public_assets']) == 9
for x in bindings['public_assets']:
    data = blob(x['path'], x['commit'])
    assert sha(data) == x['sha256'] and len(data) == x['bytes']
    assert data == blob(x['path'])
    assert git('rev-parse', x['commit'] + ':' + x['path']).decode().strip() == x['blob']
for x in (bindings['controller'], bindings['R00_environment']):
    assert sha(blob(x['path'], x.get('commit', COMMIT))) == x['sha256']

lock = tomllib.loads(blob(P + 'Cargo.lock').decode())
packages = doc(P + 'dependency-register.json')['packages']
locked = {(x['name'], x['version']): x for x in lock['package'] if 'source' in x}
assert len(packages) == len(locked) == 11
assert set(locked) == {(x['name'], x['version']) for x in packages}
licenses = 0
for package in packages:
    key = (package['name'], package['version'])
    entry = locked[key]
    assert entry['source'] == package['registry_source'] == 'registry+https://github.com/rust-lang/crates.io-index'
    assert entry['checksum'] == package['archive_sha256']
    stem = package['name'] + '-' + package['version']
    archives = list(CACHE.glob('*/' + stem + '.crate'))
    assert len(archives) == 1
    data = archives[0].read_bytes()
    assert len(data) == package['archive_bytes'] and sha(data) == entry['checksum']
    assert package['official_download'] == f'https://static.crates.io/crates/{package["name"]}/{stem}.crate'
    with tarfile.open(archives[0], 'r:gz') as archive:
        cargo = archive.extractfile(stem + '/Cargo.toml').read()
        assert sha(cargo) == package['Cargo_toml_sha256']
        metadata = tomllib.loads(cargo.decode())['package']
        assert metadata['license'] == package['declared_license']
        assert metadata.get('license-file') == package['license_file_field']
        for license_body in package['actual_license_bodies']:
            raw = archive.extractfile(license_body['archive_member']).read()
            assert raw == blob(license_body['path'])
            assert len(raw) == license_body['bytes'] and sha(raw) == license_body['sha256']
            licenses += 1
assert licenses == 22

result = doc(P + 'result.json')
for path, digest in result['source_hashes'].items():
    assert blob(path) == blob(path, EXECUTED) and sha(blob(path)) == digest
binary = AUTHOR / result['binary']['ignored_local_path']
assert binary.stat().st_size == result['binary']['bytes'] == 669048
assert sha(binary.read_bytes()) == result['binary']['sha256']
build = doc(P + 'build/release-command.json')
assert build['exit_code'] == 0 and build['source_commit'] == EXECUTED
for path, digest in build['source_hashes'].items():
    assert sha(blob(path, EXECUTED)) == digest
for run in result['actual_runs']:
    command_path = run['directory'] + '/command.json'
    summary_path = run['directory'] + '/summary.json'
    assert sha(blob(command_path)) == run['command_sha256']
    assert sha(blob(summary_path)) == run['summary_sha256']
    command, summary = doc(command_path), doc(summary_path)
    assert command['source_commit'] == EXECUTED and command['exit_code'] == 0
    for path, digest in command['source_hashes'].items():
        assert sha(blob(path, EXECUTED)) == digest
    assert summary['passed'] and len(summary['cases']) == run['case_count']
    assert summary['not_exercised'] == [] and summary['all_created_PIDs_collected']
    assert summary['FDs_equal_initial'] and summary['parent_identity_unchanged'] and summary['parent_limits_unchanged']
assert len(result['stable_cases']) == 5
for case in result['stable_cases']:
    assert sha(blob(case['trace_path'])) == case['trace_sha256'] and case['passed']
assert result['execution_totals']['keys_signing_operations'] == 0

Path(__file__).with_name('validation.json').write_text(json.dumps({
    'candidate': COMMIT, 'tree': git('rev-parse', COMMIT + '^{tree}').decode().strip(),
    'reviewer': '/root', 'verdict': 'PASS_SOURCE_ARCHIVE_LICENSE_COPY_AND_PACKET_CORRESPONDENCE_ONLY',
    'checked': {'manifest_members': 117, 'new_owned_paths': 118,
                'precode_files_exact': 5, 'original_public_asset_bindings': 9,
                'Cargo_locked_official_archives': 11, 'exact_license_bodies': 22,
                'executed_source_files': 4, 'author_build_binding': True,
                'author_binary_bytes': 669048, 'run_bindings': 3,
                'recorded_final_case_bindings': 5, 'unchanged_original_parameters_and_all_other_sources': True},
    'independent_builds_or_worker_executions': 0,
    'limits': 'A02 separately owns source/runtime review and an independent build/five-case campaign. This validates source-bound author observations, not product decoder selection, all-input safety, secret isolation, ARM, physical or task qualification.'
}, indent=2) + '\n')
print('PASS packet: 117 members, 118 new paths, 11 lock/archive checksums, 22 exact license bodies, 9 original assets; no build or decoder executed.')
