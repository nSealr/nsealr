#!/usr/bin/env python3
"""Verify author evidence bytes and exact product/brief identity via Git objects."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CANDIDATE = 'd385ddb0c775a1e863e9db0ee9ae38fee5f19057'
EVIDENCE = '143e6fb260431dc9cb97a72d6c019e3c6c5c6bf1'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)
def sha(data):
    return hashlib.sha256(data).hexdigest()
def blob(commit, path):
    return git('show', f'{commit}:{path}')

manifest = json.loads(blob(EVIDENCE, 'docs/restart/S01/evidence/candidate-results.json'))
assert manifest['source_candidate'] == CANDIDATE
paths = git('diff', '--name-only', CANDIDATE, EVIDENCE).decode().splitlines()
assert all(p.startswith('docs/restart/S01/evidence/') for p in paths), paths
artifacts = []
for artifact in manifest['artifacts']:
    actual = sha(blob(EVIDENCE, artifact['path']))
    assert actual == artifact['sha256'], artifact
    artifacts.append({**artifact, 'hash_verified': True})
gates = []
for name in ['final-ci', 'live-relay', 'targeted']:
    record = json.loads(blob(EVIDENCE, f'docs/restart/S01/evidence/{name}.json'))
    assert record['candidate_commit'] == CANDIDATE
    assert record['exit_code'] == 0
    assert sha(blob(EVIDENCE, f'docs/restart/S01/evidence/{name}.log')) == record['log_sha256']
    gates.append({'name': name, 'command': record['command'], 'candidate': record['candidate_commit'], 'exit_code': record['exit_code'], 'log_sha256': record['log_sha256'], 'classification': 'author execution, independently inspected and hash-verified; not a reviewer rerun'})
dependency = {}
for file in ['abstract-relay', 'pool']:
    dependency[file] = sha((ROOT / f'node_modules/nostr-tools/lib/esm/{file}.js').read_bytes())
    assert dependency[file] == manifest['default_adapter_source'][file.replace('-', '_') + '_sha256']
protocols = []
for name, expected in [('46.md', 'e5a3c818eb3bc410541104198d4ebdce6b1720a2da00cb8e71d38ec0b72f01c1'), ('01.md', 'b229fa210af54e4a821c0c483fba88d7dcd2b7a6f26c010b4548039919da266e'), ('44.md', 'b5f89374e4e1dbdee7881e8573b4313b6a89430a9c8d518471599ae0660cf0e2')]:
    url = f'https://raw.githubusercontent.com/nostr-protocol/nips/37db639582d857e12468dcccd99b2c7f1d657da9/{name}'
    data = urllib.request.urlopen(url, timeout=20).read()
    actual = sha(data)
    assert actual == expected, name
    protocols.append({'url': url, 'sha256': actual, 'hash_verified': True})
record = {
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_candidate': CANDIDATE,
    'evidence_commit': EVIDENCE,
    'brief_sha256': sha(blob(CANDIDATE, 'docs/restart/S01/brief.md')),
    'product_unchanged_in_evidence_commit': True,
    'author_artifacts': artifacts,
    'author_final_gates': gates,
    'installed_dependency_sha256': dependency,
    'pinned_protocols': protocols,
    'limits': 'Hash agreement proves byte identity, not correctness. Review scope and independent behavioral evidence are recorded separately. Docker execution remains author evidence; reviewer loopback experiment uses real local WebSocket I/O without Docker.'
}
(HERE / 'author-evidence-assessment.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'author_artifacts_verified': len(artifacts), 'exact_source_final_gates_verified': len(gates), 'pinned_protocol_hashes_verified': len(protocols), 'installed_dependency_hashes_verified': len(dependency)}))
