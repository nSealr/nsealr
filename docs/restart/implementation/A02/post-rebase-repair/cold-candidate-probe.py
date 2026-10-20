#!/usr/bin/env python3
"""Record an ordinary cold Git fetch of only the public committed repair."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'tools/migration'))
from admission import Recorder
from rehearse import canonical, write_private

OLD = ('86569e073da4faec0811d67137bbb0fd4f74c7c6',
       '5cb16cbaffc6b90ca9dfbb1ce7a5388e731d1ae0')
ANCHORS = ('68508ea1eea1e07b0064fadd65b33433d72701f8',
           '59653fcc15c4cbc21a39d0a0dd5548abe46165b0',
           'f2ef70f522af4977e15f81554a8c6eadcdbe8097')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', help='exact public repair commit')
    parser.add_argument('output', type=Path, help='absent private runtime destination')
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}', args.candidate):
        parser.error('candidate must be an exact SHA-1 commit')
    output = args.output.absolute()
    recorder = Recorder(output)
    # Keep HOME intact and exclude ambient Git object/config override variables.
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    repo = output / 'candidate'
    recorder.run('absent-destination-init', ['git', '-c', 'init.templateDir=', 'init',
                 '--initial-branch=intake', str(repo)], output, env=env)
    recorder.run('public-exact-candidate-only-fetch', ['git', 'fetch', '--no-tags',
                 '--no-write-fetch-head', 'https://github.com/nSealr/nsealr.git',
                 args.candidate + ':refs/heads/candidate'], repo, env=env)
    recorder.run('candidate-checkout', ['git', 'checkout', 'candidate'], repo, env=env)
    actual = recorder.run('actual-head-tree', ['git', 'rev-parse', 'HEAD', 'HEAD^{tree}'], repo, env=env).decode().splitlines()
    assert actual[0] == args.candidate
    refs = recorder.run('only-selected-ref', ['git', 'for-each-ref', '--format=%(refname) %(objectname)'], repo, env=env).decode().splitlines()
    assert refs == ['refs/heads/candidate ' + args.candidate]
    assert recorder.run('no-configured-remotes', ['git', 'remote'], repo, env=env) == b''
    assert recorder.run('clean-source-before', ['git', 'status', '--porcelain'], repo, env=env) == b''
    for oid in OLD:
        recorder.run('historical-' + oid[:7] + '-absent', ['git', 'cat-file', '-e', oid + '^{commit}'], repo, expected=128, env=env)
    for oid in ANCHORS:
        recorder.run('permanent-' + oid[:7] + '-present', ['git', 'cat-file', '-e', oid + '^{commit}'], repo, env=env)
        recorder.run('permanent-' + oid[:7] + '-ancestor', ['git', 'merge-base', '--is-ancestor', oid, args.candidate], repo, env=env)
    gitdir = repo / '.git'
    for name in ('objects/info/alternates', 'objects/info/http-alternates', 'shallow', 'info/grafts'):
        assert not (gitdir / name).exists()
    paths = list(gitdir.rglob('*'))
    assert all(not p.is_symlink() for p in paths)
    assert all(p.stat().st_nlink == 1 for p in paths if p.is_file())
    all_objects = set(recorder.run('all-fetched-object-identities', ['git', 'cat-file', '--batch-all-objects', '--batch-check=%(objectname)'], repo, env=env).decode().splitlines())
    reachable = {line.split()[0] for line in recorder.run('only-candidate-reachable-objects', ['git', 'rev-list', '--objects', args.candidate], repo, env=env).decode().splitlines()}
    assert all_objects == reachable
    recorder.run('strict-object-integrity', ['git', 'fsck', '--full', '--strict'], repo, env=env)
    manifest = (repo / 'protocols/contracts/v1/manifest.json').read_bytes()
    assert hashlib.sha256(manifest).hexdigest() == '16bf215c6f65a5c616c30971cb860351272633ff6a8c75edc8246eab61f8bbeb'
    assert json.loads(manifest)['initial_import_commit'] == OLD[0]
    checker = repo / 'scripts/verify_contracts.py'
    constants = {n.targets[0].id: n.value.value for n in ast.parse(checker.read_bytes()).body
                 if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                 and isinstance(n.value, ast.Constant)}
    assert constants['INITIAL_IMPORT'] == OLD[0]
    assert constants['SOURCE_POSTIMAGE'] == ANCHORS[0]
    assert constants['BASELINE'] == ANCHORS[1]
    recorder.run('corrected-actual-artifact-checker-GREEN', [sys.executable, '-B', 'scripts/verify_contracts.py'], repo, env=env)
    recorder.run('remaining-historical-evidence-anchor-GREEN', [sys.executable, '-B', 'scripts/verify_evidence.py'], repo, env=env)
    assert recorder.run('clean-source-after', ['git', 'status', '--porcelain'], repo, env=env) == b''
    summary = {'candidate': actual[0], 'tree': actual[1], 'origin': 'https://github.com/nSealr/nsealr.git',
               'only_ref': refs[0], 'all_objects_reachable_from_only_candidate': True,
               'fetched_objects': len(all_objects), 'old_intermediate_commits_absent': list(OLD),
               'permanent_ancestors_present': list(ANCHORS), 'no_shared_hardlinked_objects_alternates_or_extra_refs': True,
               'literal_historical_manifest_identity_preserved': True, 'manifest_sha256': hashlib.sha256(manifest).hexdigest(),
               'checker_sha256': hashlib.sha256(checker.read_bytes()).hexdigest(),
               'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'actual_contract_gate_passed': True, 'actual_frozen_evidence_gate_passed': True,
               'commands_sha256': hashlib.sha256((output / 'commands.json').read_bytes()).hexdigest(),
               'limits': 'Cold source/immutable data validation only; no full product suite rerun, protected PR/main CI, task closure or physical qualification claimed.'}
    write_private(output / 'summary.json', canonical(summary))
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
