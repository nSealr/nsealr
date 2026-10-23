"""One-time evidence inspection of Cargo1.95 cache3/schema2; not the audit gate."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
cache = HERE / '.runtime/cargo'
inputs = json.loads((HERE / 'input-locks.json').read_text())
packages = {}
for graph in inputs['graphs']:
    for row in graph['registry_entries']:
        assert row['source'] == 'registry+https://github.com/rust-lang/crates.io-index'
        key = (row['name'], row['version'])
        if key in packages:
            assert packages[key] == row
        packages[key] = row
indices = list((cache / 'registry/index').iterdir())
assert len(indices) == 1 and indices[0].name.startswith('index.crates.io-')
index = indices[0]
records, raw_records = [], []
for (name, version), expected in sorted(packages.items()):
    lower = name.lower()
    relative = ('1/' + lower if len(lower) == 1 else '2/' + lower if len(lower) == 2
                else '3/' + lower[0] + '/' + lower if len(lower) == 3
                else lower[:2] + '/' + lower[2:4] + '/' + lower)
    path = index / '.cache' / relative
    data = path.read_bytes()
    # Format examined at Cargo rust-1.95.0 registry/index/cache.rs, lines85/95-193.
    assert data[:5] == b'\x03\x02\x00\x00\x00'
    parts = data[5:].split(b'\0')
    assert parts[-1] == b'' and (len(parts) - 2) % 2 == 0
    matches = [parts[i + 1] for i in range(1, len(parts) - 1, 2) if parts[i].decode() == version]
    assert len(matches) == 1
    raw = matches[0]
    record = json.loads(raw)
    assert record['name'] == name and record['vers'] == version
    assert record['cksum'] == expected['checksum']
    assert type(record['yanked']) is bool and record['yanked'] is False
    raw_records.append(raw)
    records.append({'name': name, 'version': version, 'checksum': record['cksum'], 'yanked': record['yanked'],
                    'sparse_url': 'https://index.crates.io/' + relative, 'cache_version': 3, 'schema_version': 2,
                    'index_file_version': parts[0].decode(), 'cache_path': str(path.relative_to(HERE)),
                    'cache_sha256': hashlib.sha256(data).hexdigest(), 'record_sha256': hashlib.sha256(raw).hexdigest()})
dbs = [p for p in (cache / 'advisory-dbs').iterdir() if p.is_dir()]
assert len(dbs) == 1
db = dbs[0]
git = lambda *args: subprocess.check_output(['git', '-C', str(db), *args]).decode().strip()
assert git('status', '--porcelain') == ''
advisory = db / 'crates/ctutils/RUSTSEC-2026-0385.md'
result = {'schema_version': 1, 'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'role': 'Evidence inspection only; production gate exclusively uses standard Cargo/cargo-deny',
          'lock_registry_counts': [len(g['registry_entries']) for g in inputs['graphs']],
          'union_count': len(records), 'all_locked_versions_found_checksum_equal_and_not_yanked': True,
          'fetch_receipts': ['03-fetch-index-root.command.json', '04-fetch-index-host.command.json'],
          'format_source': 'https://raw.githubusercontent.com/rust-lang/cargo/rust-1.95.0/src/cargo/sources/registry/index/cache.rs',
          'index_format_source': 'https://doc.rust-lang.org/cargo/reference/registry-index.html',
          'registry_records': records,
          'advisory_database': {'origin': git('remote', 'get-url', 'origin'), 'commit': git('rev-parse', 'HEAD'),
                               'commit_timestamp': git('show', '-s', '--format=%cI', 'HEAD'), 'clean': True,
                               'path': str(db.relative_to(HERE)), 'known_advisory_path': str(advisory.relative_to(db)),
                               'known_advisory_sha256': hashlib.sha256(advisory.read_bytes()).hexdigest()},
          'passed': True}
(HERE / 'registry-records.jsonl').write_bytes(b'\n'.join(raw_records) + b'\n')
(HERE / 'data-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'lock_counts': result['lock_registry_counts'], 'union': len(records),
                  'advisory_db_commit': result['advisory_database']['commit']}))
