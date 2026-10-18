#!/usr/bin/env python3
"""Verify source provenance and complete consumer scopes for one contract artifact."""
import fnmatch
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
ARTIFACT=ROOT/'protocols/contracts/v1'
ORIGIN='45f8b6ff1123f3f55be4ce457fd1008e91043cc2'
INITIAL_IMPORT='86569e073da4faec0811d67137bbb0fd4f74c7c6'
# This immutable migration postimage binds the active reviewed data, independently
# of working-tree digests. A later contract change needs a declared/reviewed
# source transition and a new baseline; merely editing manifest.json is invalid.
BASELINE='98a8df4a71c0da19908de0e5ec39ea5fb798325a'
DATA_DIRS=('protocols','schemas','vectors','examples')
CONSUMERS_SHA256='REPLACE_CONSUMERS_SHA256'


def sha(data):return hashlib.sha256(data).hexdigest()


def git(repository,*args):
    return subprocess.check_output(['git','-C',str(repository),*args],stderr=subprocess.DEVNULL)


def committed(repository,commit,path):
    return git(repository,'show',commit+':protocols/contracts/v1/'+path)


def inventory(artifact):
    if artifact.is_symlink() or not artifact.is_dir():raise ValueError('nonregular artifact root')
    actual=set()
    for directory in DATA_DIRS:
        root=artifact/directory
        if not root.is_dir() or root.is_symlink():raise ValueError('missing/nonregular contract directory')
        for path in root.rglob('*'):
            if path.is_symlink() or (not path.is_file() and not path.is_dir()):raise ValueError('nonregular contract entry')
            if path.is_file():actual.add(path.relative_to(artifact).as_posix())
    return actual


def check_consumers(artifact,paths):
    path=artifact/'consumers.json'
    if path.is_symlink() or not path.is_file():raise ValueError('consumer scopes are required and regular')
    if sha(path.read_bytes())!=CONSUMERS_SHA256:raise ValueError('consumer scope changed without declared review')
    consumers=json.loads(path.read_bytes())
    if set(consumers)!={'bridge','engine','pi'}:raise ValueError('missing/unknown consumer')
    for name,patterns in consumers.items():
        if not patterns or len(patterns)!=len(set(patterns)):raise ValueError('empty/duplicate consumer scope')
        for pattern in patterns:
            if not any(fnmatch.fnmatchcase(path,pattern) for path in paths):
                raise ValueError('consumer scope matches no contract: '+name+': '+pattern)
    return consumers


def validate(artifact=ARTIFACT,repository=ROOT):
    actual=inventory(artifact)
    manifest_path=artifact/'manifest.json'
    if not manifest_path.is_file() or manifest_path.is_symlink():raise ValueError('contract manifest is required; old snapshots are not accepted')
    manifest_bytes=manifest_path.read_bytes()
    try:manifest=json.loads(manifest_bytes)
    except ValueError as error:raise ValueError('malformed contract manifest') from error
    if not isinstance(manifest,dict):raise ValueError('contract manifest must be an object')
    if manifest.get('artifact_format')!=1 or manifest.get('artifact_id')!='nsealr-contracts-v1':raise ValueError('unsupported contract artifact identity')
    if manifest.get('source_commit')!=ORIGIN or manifest.get('initial_import_commit')!=INITIAL_IMPORT:raise ValueError('contract source pin changed without migration review')
    if manifest_bytes!=committed(repository,BASELINE,'manifest.json'):raise ValueError('contract manifest differs from immutable reviewed baseline')
    records=manifest['files'];paths=[row['path'] for row in records]
    if len(paths)!=len(set(paths)):raise ValueError('duplicate contract path')
    if actual!=set(paths):raise ValueError('contract inventory missing/extra file, including hidden files')
    for row in records:
        path=row['path']
        if path.startswith('/') or '..' in path.split('/') or '\\' in path:raise ValueError('unsafe contract path')
        data=(artifact/path).read_bytes()
        if sha(data)!=row['sha256']:raise ValueError('contract byte tamper: '+path)
        for commit,expected in [(INITIAL_IMPORT,row['original_sha256']),(BASELINE,row['sha256'])]:
            tree=git(repository,'ls-tree','-z',commit,'--','protocols/contracts/v1/'+path)
            if not tree.startswith((b'100644 blob ',b'100755 blob ')):raise ValueError('nonregular committed contract')
            if sha(committed(repository,commit,path))!=expected:raise ValueError('contract committed source/postimage mismatch')
    consumers=check_consumers(artifact,actual)
    for forbidden in ['tests/fixtures/specs','apps/pi/tests/fixtures/specs','packages/fixtures/fixtures']:
        path=repository/forbidden
        if path.exists() or path.is_symlink():raise ValueError('stale duplicate contract snapshot: '+forbidden)
    if (artifact/'vectors/smartcard').exists():raise ValueError('retired card contract present')
    return {'artifact':'nsealr-contracts-v1','files':len(records),'source_commit':ORIGIN,'consumers':sorted(consumers)}


if __name__=='__main__':
    try:print(json.dumps(validate(),sort_keys=True))
    except (ValueError,OSError,KeyError,TypeError,subprocess.CalledProcessError) as error:
        print('ERROR:',error);raise SystemExit(1)
