#!/usr/bin/env python3
"""Verify the single contract artifact without generating expected protocol values."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
ARTIFACT=ROOT/'protocols/contracts/v1'
ORIGIN='45f8b6ff1123f3f55be4ce457fd1008e91043cc2'
INITIAL_IMPORT='86569e073da4faec0811d67137bbb0fd4f74c7c6'
DATA_DIRS=('protocols','schemas','vectors','examples')


def sha(data):return hashlib.sha256(data).hexdigest()


def validate(artifact=ARTIFACT,repository=ROOT):
    artifact=artifact.resolve();manifest_path=artifact/'manifest.json'
    if not manifest_path.is_file() or manifest_path.is_symlink():raise ValueError('contract manifest is required; old snapshots are not accepted')
    manifest=json.loads(manifest_path.read_bytes())
    if manifest.get('artifact_format')!=1 or manifest.get('artifact_id')!='nsealr-contracts-v1':raise ValueError('unsupported contract artifact identity')
    if manifest.get('source_commit')!=ORIGIN or manifest.get('initial_import_commit')!=INITIAL_IMPORT:raise ValueError('contract source pin changed without migration review')
    records=manifest['files'];paths=[row['path'] for row in records]
    if len(paths)!=len(set(paths)):raise ValueError('duplicate contract path')
    actual=set()
    for directory in DATA_DIRS:
        root=artifact/directory
        if not root.is_dir() or root.is_symlink():raise ValueError('missing/nonregular contract directory')
        for path in root.rglob('*'):
            if path.is_symlink() or (not path.is_file() and not path.is_dir()):raise ValueError('nonregular contract entry')
            if path.is_file():actual.add(path.relative_to(artifact).as_posix())
    if actual!=set(paths):raise ValueError('contract inventory missing/extra file, including hidden files')
    for row in records:
        path=row['path']
        if path.startswith('/') or '..' in path.split('/') or '\\' in path:raise ValueError('unsafe contract path')
        data=(artifact/path).read_bytes()
        if sha(data)!=row['sha256']:raise ValueError('contract byte tamper: '+path)
        original=subprocess.check_output(['git','-C',str(repository),'show',INITIAL_IMPORT+':protocols/contracts/v1/'+path],stderr=subprocess.DEVNULL)
        if sha(original)!=row['original_sha256']:raise ValueError('contract original source attribution mismatch')
        if row['sha256']!=row['original_sha256'] and row.get('adaptation') not in {'retire-card-members-and-reconcile-current-owner','retain-policy-mismatch-with-active-policy'}:raise ValueError('undeclared contract value change')
    for forbidden in ['tests/fixtures/specs','apps/pi/tests/fixtures/specs','packages/fixtures/fixtures']:
        if (repository/forbidden).exists():raise ValueError('stale duplicate contract snapshot: '+forbidden)
    if (artifact/'vectors/smartcard').exists():raise ValueError('retired card contract present')
    return {'artifact':'nsealr-contracts-v1','files':len(records),'source_commit':ORIGIN}


if __name__=='__main__':
    try:print(json.dumps(validate(),sort_keys=True))
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as error:
        print('ERROR:',error);raise SystemExit(1)
