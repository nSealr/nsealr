#!/usr/bin/env python3
"""Admitted A02 isolated source intake; never fetch private histories or add remotes."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import subprocess

from admission import Recorder, protected_destination, public_refs
from rehearse import Source, PreflightError, canonical, decode_json, digest, git, safe_path, write_private

PACKAGE = '732f742422cb26e7f215613f56a6c90acc6f73dc'
DECISION = '0a8bb620fa635bf1d1721c707957563df456fc9c'
DECISION_PATH = 'docs/restart/implementation/reviews/A02-admission-coordinator.json'
DECISION_SHA256 = '1eaa60c798501ed016d8016d78b019c0119a8649f4bbaaea1e8df9979512d7da'
MANIFEST_PATH = 'docs/restart/implementation/A02/admission-inputs.json'
MAP_PATH = 'docs/restart/implementation/A02/admission-evidence/file-dispositions.json'
PRIVACY_PATH = 'docs/restart/implementation/A02/privacy-evidence/summary.json'


def git_environment() -> dict:
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT='0', GIT_AUTHOR_NAME='nSealr migration rehearsal',
               GIT_AUTHOR_EMAIL='migration-rehearsal@nsealr.invalid',
               GIT_COMMITTER_NAME='nSealr migration rehearsal',
               GIT_COMMITTER_EMAIL='migration-rehearsal@nsealr.invalid',
               GIT_AUTHOR_DATE='2026-10-18T18:55:00+00:00',
               GIT_COMMITTER_DATE='2026-10-18T18:55:00+00:00')
    return env


def read_git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, env=git_environment())
    if result.returncode:
        raise PreflightError('target Git read failed: ' + args[0])
    return result.stdout


def reachable(repo: Path, commit: str) -> set[str]:
    return {row.split()[0] for row in read_git(repo, 'rev-list', '--objects', commit).decode().splitlines()}


def commits(repo: Path, commit: str) -> set[str]:
    return set(read_git(repo, 'rev-list', commit).decode().splitlines())


def audit(repo: Path, base_objects: set[str], base_commits: set[str], added_commits: list[str], base_head: str) -> dict:
    control = repo / '.git'
    if not control.is_dir() or control.is_symlink():
        raise PreflightError('target must have its own ordinary .git directory')
    if any((control / name).exists() for name in ('objects/info/alternates', 'objects/info/http-alternates', 'shallow', 'info/grafts')):
        raise PreflightError('target has alternate, shallow or graft history')
    for path in (control / 'objects').rglob('*'):
        if path.is_symlink() or (path.is_file() and path.stat().st_nlink != 1):
            raise PreflightError('target object is linked to another store')
    keys = set(read_git(repo, 'config', '--local', '--name-only', '--list').decode().splitlines())
    if not keys <= {'core.repositoryformatversion', 'core.filemode', 'core.bare', 'core.logallrefupdates'}:
        raise PreflightError('unexpected target config or remote/push configuration')
    expected_head = added_commits[-1] if added_commits else base_head
    refs = read_git(repo, 'for-each-ref', '--format=%(refname) %(objectname)').decode().splitlines()
    if refs != ['refs/heads/rehearsal ' + expected_head] or read_git(repo, 'rev-parse', 'HEAD').decode().strip() != expected_head:
        raise PreflightError('unselected target refs or HEAD')
    if commits(repo, expected_head) != base_commits | set(added_commits):
        raise PreflightError('target contains unselected commit ancestry')
    previous = base_head
    for commit in added_commits:
        if read_git(repo, 'show', '-s', '--format=%P', commit).decode().strip() != previous:
            raise PreflightError('new commit is not the declared linear transformation')
        previous = commit
    allowed = reachable(repo, expected_head)
    if not base_objects <= allowed:
        raise PreflightError('original public ancestry objects missing')
    all_objects = set(read_git(repo, 'cat-file', '--batch-all-objects', '--batch-check=%(objectname)').decode().splitlines())
    if all_objects != allowed:
        raise PreflightError('target object store contains unselected/unreachable objects')
    if not added_commits and allowed != base_objects:
        raise PreflightError('initial intake differs from exact public ancestry')
    return dict(head=expected_head, reachable_commits=len(base_commits)+len(added_commits),
                all_objects=len(all_objects), all_objects_reachable_and_allowed=True,
                no_other_refs_remotes_alternates_or_hardlinks=True)


def intake(source: Path, commit: str, target: Path, recorder: Recorder) -> tuple[set[str], set[str]]:
    if target.exists() or target.is_symlink():
        raise PreflightError('target destination must be absent')
    base_objects, base_commits = reachable(source, commit), commits(source, commit)
    env = git_environment()
    recorder.run('empty-target-init', ['git', '-c', 'init.templateDir=', 'init', '--initial-branch=rehearsal', str(target)], recorder.root, env=env)
    # Git transport fetch sends selected ancestry; local clone/hardlink optimizations are never used.
    recorder.run('exact-public-ancestry-fetch', ['git', '-C', str(target), 'fetch', '--no-tags', '--no-write-fetch-head',
                 str(source), commit + ':refs/heads/rehearsal'], recorder.root, env=env)
    audit(target, base_objects, base_commits, [], commit)
    recorder.run('checkout-public-source', ['git', '-C', str(target), 'checkout', '--force', 'rehearsal'], recorder.root, env=env)
    return base_objects, base_commits


def tree(repo: Path, commit: str) -> dict:
    result = {}
    for row in read_git(repo, 'ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if not row:
            continue
        metadata, path = row.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split()
        if kind != 'blob' or mode not in {'100644', '100755'}:
            raise PreflightError('nonregular target source entry')
        result[safe_path(path.decode())] = {'mode': mode, 'blob': blob}
    return result


def import_selected(source_root: Path, manifest_path: Path, privacy_root: Path, output: Path) -> dict:
    core_repo = source_root / 'firmware'
    manifest_bytes = git(core_repo, 'show', PACKAGE + ':' + MANIFEST_PATH)
    if manifest_path.read_bytes() != manifest_bytes:
        raise PreflightError('manifest differs from exact admitted package')
    decision_bytes = git(core_repo, 'show', DECISION + ':' + DECISION_PATH)
    decision = decode_json(decision_bytes)
    if (digest(decision_bytes) != DECISION_SHA256 or decision['candidate_commit'] != PACKAGE
            or decision['import_authorized'] is not True):
        raise PreflightError('coordinator admission does not bind this package')
    manifest = decode_json(manifest_bytes)
    entries = {r['name']: r for r in manifest['sources']}
    file_map = decode_json(git(core_repo, 'show', PACKAGE + ':' + MAP_PATH))
    privacy = decode_json(git(core_repo, 'show', PACKAGE + ':' + PRIVACY_PATH))
    sanitized = {row['source_path']: row for row in privacy['files']}
    output = protected_destination(output, source_root, manifest)
    previous_umask = os.umask(0o077)
    try:
        recorder = Recorder(output)
        public_refs(manifest, source_root, output / 'public-refs-before')
        target = output / 'repository'
        base = entries['nsealr']
        base_objects, base_commits = intake(core_repo, base['commit'], target, recorder)
        expected = tree(target, base['commit'])
        rows = []
        with ExitStack() as stack:
            sources = {}
            for name in ('nsealr', 'companion', 'specs', 'raspberry', 'lab'):
                source = Source(source_root, entries[name]); sources[name] = source; stack.callback(source.close)
            for row in file_map['files']:
                if row['action'] not in {'retain', 'transform'}:
                    continue
                source = sources[row['source']]
                path = row['path']; data = source.blob(path)
                if digest(data) != row['sha256'] or source.files[path]['blob'] != row['blob'] or source.files[path]['mode'] != row['mode']:
                    raise PreflightError('selected original source identity drift')
                initial_path = path if row['source'] == 'nsealr' else row['destination']
                treatment = 'exact original source'
                if row['source'] == 'lab' and path in sanitized:
                    approved = sanitized[path]
                    if digest(data) != approved['before_sha256']:
                        raise PreflightError('privacy exception original source drift')
                    data = (privacy_root / Path(path).name).read_bytes()
                    if digest(data) != approved['after_sha256']:
                        raise PreflightError('privacy exception postimage drift')
                    treatment = 'approved pre-import seven-literal privacy exception across two files'
                target_path = target / safe_path(initial_path)
                if row['source'] == 'nsealr':
                    if target_path.read_bytes() != data:
                        raise PreflightError('core initial bytes changed')
                else:
                    if initial_path in expected or target_path.exists() or target_path.is_symlink():
                        raise PreflightError('unlisted import collision')
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_bytes(data); target_path.chmod(0o755 if row['mode']=='100755' else 0o644)
                blob = subprocess.check_output(
                    ['git', 'hash-object', '--stdin'], input=data, env=git_environment()).decode().strip()
                expected[initial_path] = {'mode': row['mode'], 'blob': blob}
                rows.append({key: row[key] for key in ('source', 'commit', 'path', 'blob', 'mode', 'sha256')} |
                            {'initial_target_path': initial_path, 'planned_final_path': row['destination'],
                             'initial_blob': blob, 'initial_sha256': digest(data), 'copy': treatment})
            recorder.run('stage-selected-import', ['git', '-C', str(target), 'add', '--all'], output, env=git_environment())
            recorder.run('commit-selected-import', ['git', '-C', str(target), '-c', 'commit.gpgsign=false', 'commit',
                         '-m', 'Import selected licensed Bridge, Pi, contracts and integration source'], output, env=git_environment())
            imported = read_git(target, 'rev-parse', 'HEAD').decode().strip()
            if tree(target, imported) != expected:
                raise PreflightError('initial imported tree differs from exact selected-source map')
            # Re-read each selected source after the copy; source worktrees are never copied.
            for row in rows:
                source = sources[row['source']]
                if digest(git(source.repo, 'show', source.commit + ':' + row['path'])) != row['sha256']:
                    raise PreflightError('selected source changed across import')
        audit_result = audit(target, base_objects, base_commits, [imported], base['commit'])
        recorder.run('import-fsck', ['git', '-C', str(target), 'fsck', '--full', '--strict'], output, env=git_environment())
        public_refs(manifest, source_root, output / 'public-refs-after')
        record = dict(admitted_package=PACKAGE, coordinator_decision=DECISION, source_core=base['commit'],
                      initial_commit=imported, initial_tree=read_git(target, 'rev-parse', 'HEAD^{tree}').decode().strip(),
                      exact_initial_tree_verified=True, selected_source_before_after_verified=True,
                      public_ref_checks='Exact pinned mains before and after import', object_audit=audit_result,
                      files=rows, phase='Initial source only; no migrated behavior/plan authority acceptance yet',
                      unchanged_core='Full original f2 tree retained, including old fixture copies; later declared atomic transformation moves graph/live consumers and removes copies.',
                      source_tags='Exact public evidence/release ref observations retained in public-refs-before/after; review tags are not product releases.')
        write_private(output / 'import-map.json', canonical(record))
        write_private(output / 'summary.json', canonical({key:value for key,value in record.items() if key!='files'}))
        return record
    finally:
        os.umask(previous_umask)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--privacy-root', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    result = import_selected(args.source_root, args.manifest, args.privacy_root, args.destination)
    print(canonical({key:value for key,value in result.items() if key!='files'}).decode(), end='')
