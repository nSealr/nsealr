"""Finite source/proof correspondence review; no timing or physical claims."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tomllib

BASE = '1be80c8114583627a8eef1952a0cd939f40b84ec'
CANDIDATE = '1d10e7a1c2986a5d244807624377e22ad562a110'
TESTED = 'f089a20098523f07193f15cf472bdf1b973b7318'
PREFIX = Path('docs/restart/implementation/R00/ctutils-remediation')
OUT = Path(__file__).parent / 'validation.json'


def git(*args):
    return subprocess.check_output(['git', *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_at(ref, path):
    return git('show', f'{ref}:{path}')


def record(row, ref=None):
    data = read_at(ref, row['path']) if ref else Path(row['path']).read_bytes()
    assert sha(data) == row['sha256'], row['path']
    if 'bytes' in row:
        assert len(data) == row['bytes'], row['path']
    if 'blob' in row:
        actual = git('rev-parse', f'{ref or CANDIDATE}:{row["path"]}').decode().strip()
        assert actual == row['blob'], row['path']
    if 'mode' in row:
        mode = git('ls-tree', ref or CANDIDATE, '--', row['path']).decode().split()[0]
        assert mode == row['mode'], row['path']


manifest = json.loads((PREFIX / 'artifact-manifest.json').read_bytes())
assert len(manifest['files']) == 80
for item in manifest['files']:
    record(item)
listed = {r['path'] for r in manifest['files']}
tracked = set(git('ls-tree', '-r', '--name-only', CANDIDATE, '--', str(PREFIX)).decode().splitlines())
assert tracked == listed | {str(PREFIX / 'artifact-manifest.json')}

bindings = json.loads((PREFIX / 'source-bindings.json').read_bytes())
for item in bindings['product_postimages']:
    record(item, item['commit'])
    record(item, CANDIDATE)
for item in bindings['proof_inputs']:
    record(item, CANDIDATE)
    assert read_at(BASE, item['path']) == read_at(CANDIDATE, item['path'])

changes = git('diff', '--name-only', BASE, CANDIDATE).decode().splitlines()
product = [p for p in changes if not p.startswith(str(PREFIX) + '/')]
assert len(product) == 12
assert all(p in ['Cargo.lock', 'apps/desktop-simulator/Cargo.lock'] or p.startswith('vendor/ctutils/') for p in product)
unchanged_counts = {}
for path in ['Cargo.lock', 'apps/desktop-simulator/Cargo.lock']:
    before = tomllib.loads(read_at(BASE, path).decode())
    after = tomllib.loads(read_at(CANDIDATE, path).decode())
    b = [r for r in before['package'] if r['name'] != 'ctutils']
    a = [r for r in after['package'] if r['name'] != 'ctutils']
    assert b == a
    unchanged_counts[path] = len(a)
    old = next(r for r in before['package'] if r['name'] == 'ctutils')
    new = next(r for r in after['package'] if r['name'] == 'ctutils')
    assert old['version'] == '0.4.3' and new['version'] == '0.4.4'
    assert {k:v for k,v in old.items() if k not in ['version','checksum']} == {k:v for k,v in new.items() if k not in ['version','checksum']}
    before['package'] = b
    after['package'] = a
    assert before == after
    assert read_at(TESTED, path) == read_at(CANDIDATE, path)

archive = PREFIX / 'sources/ctutils-0.4.4.crate'
archive_sha = sha(archive.read_bytes())
assert archive_sha == '12218662ccac37d9714f2191252553d67585b97df8c839cbe49e0bde278dc865'
checksums = json.loads(Path('vendor/ctutils/.cargo-checksum.json').read_bytes())
assert checksums['package'] == archive_sha
archive_files = {}
with tarfile.open(archive, 'r:gz') as package:
    for member in package.getmembers():
        if member.isfile():
            name = member.name.removeprefix('ctutils-0.4.4/')
            assert not name.startswith('/') and '..' not in Path(name).parts
            body = package.extractfile(member).read()
            assert Path('vendor/ctutils', name).read_bytes() == body
            assert checksums['files'][name] == sha(body)
            archive_files[name] = sha(body)
assert set(checksums['files']) == set(archive_files)
vendor_files = set(git('ls-tree','-r','--name-only',CANDIDATE,'--','vendor/ctutils').decode().splitlines())
assert vendor_files == {'vendor/ctutils/' + n for n in archive_files} | {'vendor/ctutils/.cargo-checksum.json'}
assert json.loads(Path('vendor/ctutils/.cargo_vcs_info.json').read_bytes())['git']['sha1'] == 'a993c0ba50db6510d8db15a6219572de65115438'
index = [json.loads(line) for line in (PREFIX / 'sources/registry-ctutils.jsonl').read_text().splitlines()]
registry_record = next(r for r in index if r['vers'] == '0.4.4')
assert registry_record['cksum'] == archive_sha and registry_record['yanked'] is False

non_vendor = git('ls-tree','-r','--name-only',BASE,'--','vendor').decode().splitlines()
non_vendor = [p for p in non_vendor if not p.startswith('vendor/ctutils/')]
assert len(non_vendor) == 1892
def vendor_entries(ref):
    rows = git('ls-tree','-r',ref,'--','vendor').decode().splitlines()
    return {row.split('\t',1)[1]:row.split('\t',1)[0] for row in rows}
old_vendor, new_vendor = vendor_entries(BASE), vendor_entries(CANDIDATE)
for path in non_vendor:
    assert old_vendor[path] == new_vendor[path], path
for path in ['vendor/ctutils/LICENSE-APACHE','vendor/ctutils/LICENSE-MIT']:
    assert read_at(BASE,path) == read_at(CANDIDATE,path)
old_meta = tomllib.loads(read_at(BASE,'vendor/ctutils/Cargo.toml').decode())
new_meta = tomllib.loads(read_at(CANDIDATE,'vendor/ctutils/Cargo.toml').decode())
for key in ['dependencies','features']:
    assert old_meta[key] == new_meta[key]
for key in ['edition','rust-version','license']:
    assert old_meta['package'][key] == new_meta['package'][key]

command_results = []
environment_sha = sha((PREFIX / 'environment.json').read_bytes())
for group in ['compatibility','rust-gates']:
    for item in json.loads((PREFIX / group / 'commands.json').read_bytes()):
        assert item['source_commit'] == TESTED and item['exit'] == 0
        assert item['environment_sha256'] == environment_sha
        for stream in ['stdout','stderr']:
            logfile = PREFIX / group / (item['id'] + '.' + stream + '.log')
            assert sha(logfile.read_bytes()) == item[stream + '_sha256']
        command_results.append({'id':item['id'],'exit':item['exit']})
assert len(command_results) == 16
result = {
    'status':'PASS_exact_official_dependency_patch_and_source_bound_compatibility_only',
    'candidate':CANDIDATE,'tested_source':TESTED,'manifest_members':len(listed),
    'exact_product_paths':product,'unchanged_other_package_records':unchanged_counts,
    'official_archive_files':len(archive_files),'archive_sha256':archive_sha,
    'non_ctutils_vendor_files_unchanged':len(non_vendor),
    'product_bindings_verified':len(bindings['product_postimages']),
    'unchanged_proof_inputs':len(bindings['proof_inputs']),
    'source_bound_compatibility_commands':command_results,
    'runtime':'Separate independent upstream unit build/run receipt; no full suite repeated here.',
    'limitations':['No all-target constant-time, physical, provider or key-custody qualification.',
                   'Audit-data gate has separate distinct review; actual CI/main adoption pending.'],
    'reader_observations':['A diagnostic reader assumed resolution receipts carried source_commit; actual receipt variants inspected; semantic binding checks apply to compatibility/rust-gates records only. No product/test changes.',
                           'Earlier output truncation recovered using bounded selections; complete manifests and source bindings verified directly.']
}
OUT.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status','manifest_members','unchanged_other_package_records','official_archive_files','non_ctutils_vendor_files_unchanged']}))
