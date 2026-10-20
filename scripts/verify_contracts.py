#!/usr/bin/env python3
"""Verify one reviewed format2 contract tree and its historical provenance."""
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / 'protocols/contracts/v1'
ORIGIN = '45f8b6ff1123f3f55be4ce457fd1008e91043cc2'
INITIAL_IMPORT = '86569e073da4faec0811d67137bbb0fd4f74c7c6'
# Permanent adopted authorities. INITIAL_IMPORT is historical metadata, never
# a required runtime object after normal rebase.
SOURCE_POSTIMAGE = '68508ea1eea1e07b0064fadd65b33433d72701f8'
BASELINE = '59653fcc15c4cbc21a39d0a0dd5548abe46165b0'
# Selected A: only the final independently reviewed artifact subtree literal
# belongs here, outside that subtree. Interim unbound source MUST fail closed.
# Never derive trust from HEAD, a manifest, an environment variable or a ref.
ARTIFACT_TREE_OID = 'b629e75d18190ded2403ffabe965b595a9bcf6a6'
DATA_DIRS = ('protocols', 'schemas', 'vectors', 'examples')
TOP_KEYS = {'artifact_format', 'artifact_id', 'source_commit', 'initial_import_commit',
            'consumer_coverage', 'generation', 'retirement', 'wire_versions', 'files'}
ROW_KEYS = {'path', 'disposition', 'original', 'baseline', 'current', 'adaptation'}
MODES = {'100644', '100755'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(repository, *args):
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(repository), *args],
                                   stderr=subprocess.DEVNULL)


def committed(repository, commit, path):
    return git(repository, 'show', commit + ':protocols/contracts/v1/' + path)


def require_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError('missing/unknown ' + label + ' fields')


def nonempty(value):
    return isinstance(value, str) and len(value) > 0


def strict_json(data):
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise ValueError('duplicate decoded JSON key')
            result[key] = value
        return result

    def reject(_value):
        raise ValueError('noninteger/nonfinite JSON token')

    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                           parse_float=reject, parse_constant=reject)
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, str):
                item.encode('utf-8')
            elif isinstance(item, dict):
                pending.extend(item.keys())
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
        return value
    except (UnicodeError, RecursionError) as error:
        raise ValueError('invalid JSON Unicode/nesting') from error


def safe_path(path, data_only=False):
    if (not isinstance(path, str) or not path or '\\' in path
            or any(ord(char) < 32 or ord(char) == 127 for char in path)
            or any(part in ('', '.', '..') for part in path.split('/'))):
        raise ValueError('unsafe contract path')
    if data_only and (len(path.split('/')) < 2 or path.split('/')[0] not in DATA_DIRS):
        raise ValueError('contract data path outside DATA_DIRS')
    return path


def tree_entries(repository, oid):
    if not isinstance(oid, str) or re.fullmatch('[0-9a-f]{40}', oid) is None:
        raise ValueError('literal immutable Git OID required')
    if git(repository, 'cat-file', '-t', oid).strip() != b'tree':
        raise ValueError('artifact/source subtree must be a Git tree')
    result = {}
    for entry in git(repository, 'ls-tree', '-r', '-t', '-z', oid).split(b'\0'):
        if not entry:
            continue
        head, raw_path = entry.split(b'\t', 1)
        mode, kind, blob = head.decode('ascii').split()
        path = safe_path(raw_path.decode('utf-8'))
        if (mode, kind) != ('040000', 'tree') and (mode not in MODES or kind != 'blob'):
            raise ValueError('nonregular committed contract entry')
        if path in result:
            raise ValueError('duplicate committed path')
        result[path] = (mode, kind, blob)
    return result


def anchor_entries(repository, commit):
    if not isinstance(commit, str) or re.fullmatch('[0-9a-f]{40}', commit) is None:
        raise ValueError('permanent source/postimage commit required')
    if git(repository, 'cat-file', '-t', commit).strip() != b'commit':
        raise ValueError('permanent source/postimage commit required')
    return tree_entries(repository, git(repository, 'rev-parse', commit + ':protocols/contracts/v1').decode().strip())


def inventory(artifact):
    if artifact.is_symlink() or not artifact.is_dir() or any(p.is_symlink() for p in artifact.parents):
        raise ValueError('nonregular artifact root/parent')
    result = {}
    for path in artifact.rglob('*'):
        mode = path.lstat().st_mode
        relative = safe_path(path.relative_to(artifact).as_posix())
        if stat.S_ISDIR(mode):
            result[relative] = ('040000', None)
        elif stat.S_ISREG(mode):
            result[relative] = ('100755' if mode & stat.S_IXUSR else '100644', path.read_bytes())
        else:
            raise ValueError('nonregular contract entry')
    return result


def digest(value, nullable=False):
    if value is None and nullable:
        return
    require_keys(value, {'mode', 'sha256'}, 'digest')
    if (not isinstance(value['mode'], str) or value['mode'] not in MODES
            or not isinstance(value['sha256'], str) or re.fullmatch('[0-9a-f]{64}', value['sha256']) is None):
        raise ValueError('invalid mode/hash digest')


def header(value, version):
    require_keys(value, TOP_KEYS, 'manifest')
    if type(value['artifact_format']) is not int or value['artifact_format'] != version or value['artifact_id'] != 'nsealr-contracts-v1':
        raise ValueError('unsupported contract artifact identity')
    if value['source_commit'] != ORIGIN or value['initial_import_commit'] != INITIAL_IMPORT:
        raise ValueError('historical contract source pin changed')
    require_keys(value['consumer_coverage'], {'python', 'rust', 'typescript'}, 'consumer coverage')
    if not all(nonempty(v) for v in value['consumer_coverage'].values()) or not all(nonempty(value[k]) for k in ('generation', 'retirement', 'wire_versions')):
        raise ValueError('empty manifest declaration')
    if not isinstance(value['files'], list) or not value['files']:
        raise ValueError('empty/invalid manifest inventory')


def check_consumers(data, paths):
    consumers = strict_json(data)
    require_keys(consumers, {'bridge', 'engine', 'pi'}, 'consumer')
    for name, patterns in consumers.items():
        if not isinstance(patterns, list) or not patterns or not all(nonempty(p) for p in patterns):
            raise ValueError('empty/invalid consumer scope')
        if len(patterns) != len(set(patterns)):
            raise ValueError('duplicate consumer pattern')
        for pattern in patterns:
            safe_path(pattern, data_only=True)
            if not any(fnmatch.fnmatchcase(path, pattern) for path in paths):
                raise ValueError('consumer scope matches no active contract: ' + name + ': ' + pattern)
    return consumers


def validate(artifact=ARTIFACT, repository=ROOT):
    if ARTIFACT_TREE_OID is None:
        raise ValueError('reviewed artifact subtree OID is unbound; final stable pin required')
    approved = tree_entries(repository, ARTIFACT_TREE_OID)
    original = anchor_entries(repository, SOURCE_POSTIMAGE)
    baseline = anchor_entries(repository, BASELINE)
    blobs = {}

    def body(entry):
        mode, kind, oid = entry
        if mode not in MODES or kind != 'blob':
            raise ValueError('expected regular committed file')
        if oid not in blobs:
            blobs[oid] = git(repository, 'cat-file', 'blob', oid)
        return blobs[oid]

    def binding(entries, path):
        if path not in entries:
            return None
        return {'mode': entries[path][0], 'sha256': sha(body(entries[path]))}

    actual = inventory(artifact)
    if set(actual) != set(approved):
        raise ValueError('artifact tree missing/extra entry, including hidden metadata/directories')
    for path, entry in approved.items():
        mode, data = actual[path]
        if mode != entry[0] or (data is not None and data != body(entry)):
            raise ValueError('contract byte/mode tamper: ' + path)
    for directory in DATA_DIRS:
        if directory not in approved or approved[directory][0] != '040000':
            raise ValueError('missing contract data directory')
    if not {'manifest.json', 'consumers.json'} <= set(approved):
        raise ValueError('manifest and consumer scopes are required')
    manifest = strict_json(body(approved['manifest.json']))
    header(manifest, 2)
    old_manifest = strict_json(body(baseline['manifest.json']))
    header(old_manifest, 1)
    old_rows = {}
    for row in old_manifest['files']:
        require_keys(row, {'path', 'sha256', 'original_sha256', 'adaptation'}, 'historical row')
        path = safe_path(row['path'], data_only=True)
        if path in old_rows:
            raise ValueError('duplicate historical path')
        old_rows[path] = row
        for entries, field in ((original, 'original_sha256'), (baseline, 'sha256')):
            found = binding(entries, path)
            if found is None or found['sha256'] != row[field]:
                raise ValueError('historical committed source/postimage mismatch')
    data_paths = lambda entries: {p for p, row in entries.items() if row[1] == 'blob' and p.split('/')[0] in DATA_DIRS}
    if set(old_rows) != data_paths(baseline):
        raise ValueError('historical baseline inventory mismatch')
    if 'adaptation.json' in baseline and binding(approved, 'adaptation.json') != binding(baseline, 'adaptation.json'):
        raise ValueError('historical A02 adaptation changed')
    paths, inherited, active = set(), set(), set()
    for row in manifest['files']:
        require_keys(row, ROW_KEYS, 'format2 row')
        path = safe_path(row['path'], data_only=True)
        if path in paths:
            raise ValueError('duplicate contract path')
        paths.add(path)
        disposition = row['disposition']
        if disposition not in ('maintained', 'modified_t01', 'authored_t01', 'retired_t01'):
            raise ValueError('unknown provenance disposition')
        for key in ('original', 'baseline', 'current'):
            digest(row[key], nullable=True)
        if row['adaptation'] is not None and not nonempty(row['adaptation']):
            raise ValueError('invalid adaptation declaration')
        if disposition == 'authored_t01':
            if row['original'] is not None or row['baseline'] is not None or path in original or path in baseline:
                raise ValueError('authored path fabricates historical provenance')
        else:
            inherited.add(path)
            if path not in old_rows or row['original'] != binding(original, path) or row['baseline'] != binding(baseline, path):
                raise ValueError('wrong original/baseline provenance')
        if disposition == 'maintained':
            if row['current'] != row['baseline'] or row['adaptation'] != old_rows[path]['adaptation']:
                raise ValueError('maintained row changed baseline/adaptation')
        elif not nonempty(row['adaptation']):
            raise ValueError('T01 change needs declared adaptation')
        if disposition == 'modified_t01' and row['current'] == row['baseline']:
            raise ValueError('modified row did not change')
        if disposition == 'retired_t01':
            if row['current'] is not None or path in approved:
                raise ValueError('retired path remains active')
        else:
            if row['current'] is None or row['current'] != binding(approved, path):
                raise ValueError('wrong/missing current postimage')
            active.add(path)
    if inherited != set(old_rows) or active != data_paths(approved):
        raise ValueError('missing baseline tombstone or unclassified active data')
    consumers = check_consumers(body(approved['consumers.json']), active)
    for forbidden in ('tests/fixtures/specs', 'apps/pi/tests/fixtures/specs', 'packages/fixtures/fixtures'):
        path = repository / forbidden
        if path.exists() or path.is_symlink():
            raise ValueError('stale duplicate contract snapshot: ' + forbidden)
    if (artifact / 'vectors/smartcard').exists() or (artifact / 'vectors/smartcard').is_symlink():
        raise ValueError('retired card contract present')
    return {'artifact': 'nsealr-contracts-v1', 'artifact_format': 2, 'files': len(active),
            'records': len(paths), 'retired': len(paths - active), 'source_commit': ORIGIN,
            'artifact_tree': ARTIFACT_TREE_OID, 'consumers': sorted(consumers)}


if __name__ == '__main__':
    try:
        print(json.dumps(validate(), sort_keys=True))
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print('ERROR:', error)
        raise SystemExit(1)
