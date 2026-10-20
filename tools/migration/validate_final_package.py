#!/usr/bin/env python3
"""Check current A02 report links, case-source bindings, notice paths and public exports."""
import argparse
import ast
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from assemble import read_git
from rehearse import canonical, digest, git


def validate(author: Path, output: Path) -> None:
    author = author.resolve()
    report = author / 'docs/restart/implementation/A02'
    target = author / 'tools/migration/.runtime/rehearsal-01/repository'
    head = read_git(target, 'rev-parse', 'HEAD').decode().strip()
    mapping = json.loads((report / 'final-source-map.json').read_bytes())
    final_tree = json.loads((report / 'final-tree.json').read_bytes())
    replay = json.loads((report / 'execution/rehearsal-04/result.json').read_bytes())
    assert mapping['target_commit'] == final_tree['target_commit'] == replay['second_assembly']['target_head'] == head
    assert mapping['target_tree'] == replay['second_assembly']['target_tree']
    assert replay['recovery']['tree_and_all_objects_equal']

    reports = ['final-report.md', 'failure-removal-ledger.md', 'draft-source-notices.md', 'interoperability-handoff.md']
    checked_links = 0
    for name in reports:
        text = (report / name).read_text()
        for raw in re.findall(r'\[[^\]\n]*\]\(([^\s)]+)\)', text):
            parsed = urlsplit(raw)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resolved = ((report / name).parent / unquote(parsed.path)).resolve()
            if not resolved.is_relative_to(author) or not resolved.exists():
                raise ValueError('missing or escaping report link: ' + name)
            checked_links += 1
    ledger = (report / 'failure-removal-ledger.md').read_text()
    failures = json.loads((report / 'failure-observations.json').read_bytes())['observations']
    for row in failures:
        assert row['log'].removeprefix('execution/') in ledger, 'unexplained failed observation'
        assert digest((report / row['log']).read_bytes()) == row['log_sha256']

    checked_cases = 0
    def check(path, sha):
        nonlocal checked_cases
        assert digest((target / path).read_bytes()) == sha, 'case source changed since named execution'
        checked_cases += 1
    cases = json.loads((report / 'execution/case-reconciliation-execution-01/case-correspondence.json').read_bytes())
    for row in cases['cases']:
        after = row.get('after')
        if isinstance(after, dict) and after.get('path') and after.get('sha256'):
            owner = {'pi': 'apps/pi', 'contracts': 'protocols/contracts/v1'}.get(after['execution_group'], '')
            path = (Path(owner) / after['path']).as_posix()
            assert path == row['before'].get('target_file', path), 'case owner/path mapping differs from admitted destination'
            check(path, after['sha256'])
    for row in cases['additional_executed_controls']:
        check(row['path'], row['sha256'])
    for row in cases['private_opaque_obligations']:
        after = row.get('after')
        if after and after['status'] == 'passed':
            if 'source_file' in after:
                check(after['source_file'], after['source_sha256'])
            else:
                check(after['path'], after['sha256'])
    ts = json.loads((report / 'execution/bridge-named-execution-02/case-correspondence.json').read_bytes())
    for row in ts['case_correspondence']:
        if row.get('after_file_sha256'):
            check(row['target_file'], row['after_file_sha256'])

    notice_paths = ['apps/bridge', 'packages', 'tools/bridge', 'docs/bridge', 'apps/pi',
        'protocols/contracts/v1', 'tests/integration', 'plan/work-items.json',
        'docs/product/client-qualification.md', 'docs/product/contract.md',
        'docs/product/requirements.md', 'docs/product/event-review-contract.md', 'docs/product/threat-models.md',
        'LICENSES/companion-MIT.txt', 'packages/sdk/LICENSE', 'apps/pi/LICENSE',
        'protocols/contracts/v1/LICENSE', 'LICENSES/lab-tooling-CC0.txt']
    assert all((target / path).exists() for path in notice_paths)
    for path in ['LICENSES/companion-MIT.txt', 'apps/pi/LICENSE', 'protocols/contracts/v1/LICENSE', 'LICENSES/lab-tooling-CC0.txt']:
        row = next(r for r in mapping['public_and_selected_private_file_dispositions'] if r['final'] and r['final']['path'] == path)
        assert row['source_sha256'] == row['final']['sha256'] == digest((target / path).read_bytes())
    assert (target / 'packages/sdk/LICENSE').read_bytes() == (target / 'LICENSES/companion-MIT.txt').read_bytes()
    qualification = (target / 'docs/product/client-qualification.md').read_text()
    interoperability = (report / 'interoperability-handoff.md').read_text()
    for value in ['a79e21d90fce5465b50ef385dd368bba99ec4a0b', '0476cad1944dcc999da5eae21ea5224e27014042', '8f4d34cc16bfb4380208923d26307fab561a867d']:
        assert value in qualification and value in interoperability

    # Read excluded original references solely for in-memory exclusion checks.
    original = ast.parse(git(Path('/home/tux/nsealr/lab'), 'show',
        '3303ab17a28ed32419576627d5abb93db3999635:scripts/integration_feature_matrix.py'))
    node = next(n for n in original.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'LAB_DOCS' for t in n.targets))
    words = [n.value for n in ast.walk(node.value) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    forbidden = [s.encode() for word in words for s in (word, Path(word).name)]
    exported = [p for p in report.rglob('*') if p.is_file()]
    for path in exported:
        if any(value in path.read_bytes() for value in forbidden):
            raise ValueError('excluded private document reference in public report/evidence')
    assert not read_git(target, 'status', '--porcelain')
    result = dict(target_commit=head, target_tree=mapping['target_tree'],
        current_named_case_source_bindings_checked=checked_cases, local_report_links_checked=checked_links,
        failed_observations_explained_and_hash_verified=len(failures), notice_paths_checked=notice_paths,
        retained_license_bytes_verified=True, pinned_interoperability_source_identity_verified=True,
        public_report_and_evidence_files_privacy_checked=len(exported), excluded_private_references_found=False,
        final_map_replay_and_restored_candidate_equal=True, target_clean=True,
        scope='Author package validation only; final independent review, coordinator adoption and actual main CI remain pending.')
    output.write_bytes(canonical(result))
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--author-repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    validate(args.author_repo, args.output)
