#!/usr/bin/env python3
"""Reproduce T01-PROV-01 using only existing public synthetic fixtures.

Run with python -B from this reviewed repository. Only disposable fixture Git
repositories change; neither production constants nor working product files do.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'scripts'))
from test_contracts import ArtifactProvenanceTests

case = ArtifactProvenanceTests()
case.setUp()
try:
    target = case.artifact / 'LICENSE'
    target.chmod(0o755)
    with case.trust_current_tree():
        approved = case.check()
        approved_entry = case.git('ls-tree', case.tree, '--', 'LICENSE').decode()
        # The helper pins another actual fixture subtree; read that literal.
        import verify_contracts
        approved_oid = verify_contracts.ARTIFACT_TREE_OID
        approved_entry = case.git('ls-tree', approved_oid, '--', 'LICENSE').decode()
        target.chmod(0o645)
        observed = case.check()
        diff = case.git('diff', '--summary').decode()
        case.git('add', 'protocols/contracts/v1/LICENSE')
        staged = case.git('ls-files', '--stage', 'protocols/contracts/v1/LICENSE').decode()
        changed_tree = case.git('write-tree').decode().strip()
        assert approved_entry.startswith('100755 blob ')
        assert 'mode change 100755 => 100644' in diff
        assert staged.startswith('100644 ')
        assert observed == approved
        print(json.dumps({
            'finding': 'T01-PROV-01',
            'question': 'Does working regular mode equal the literal approved Git mode?',
            'approved_fixture_subtree': approved_oid,
            'approved_entry': approved_entry,
            'first_valid_result': approved,
            'after_chmod_0645_result': observed,
            'after_chmod_stat_mode': oct(target.stat().st_mode & 0o777),
            'actual_git_diff_summary': diff,
            'actual_git_index_after_add': staged,
            'changed_repository_tree': changed_tree,
            'observed_defect': 'Checker accepts 100755 while Git reports/stages 100644',
            'production_pin_changed': False,
            'production_files_changed': False,
            'scope': 'Public synthetic fixture only; not current artifact acceptance'
        }, indent=2))
finally:
    case.doCleanups()
