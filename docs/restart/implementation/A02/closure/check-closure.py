#!/usr/bin/env python3
"""Exercise the actual A02 closure; temporarily withhold one new proof, then restore."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'tools/migration'))
from admission import Recorder
from rehearse import canonical, write_private


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='absent private runtime destination')
    args = parser.parse_args()
    recorder = Recorder(args.destination.absolute())
    # Reuse the already verified pinned tools; preserve HOME and source files.
    tools = Path('/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final')
    env = json.loads((tools / 'environment.json').read_bytes())
    write_private(recorder.root / 'explicit-environment.json', canonical(env))
    plan = json.loads((ROOT / 'plan/work-items.json').read_bytes())
    a02 = next(t for t in plan['tasks'] if t['id'] == 'A02')
    assert a02['status'] == 'integrated' and a02['review_verdict'] == 'pass'
    assert a02['candidate_commits'] == {'nSealr/nsealr': 'b1c90139a651895284b2624da7d12903cf16bc9d'}
    proof = ROOT / 'docs/restart/implementation/A02/closure/evidence/CI/run-39412818666/capture.json'
    original = proof.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    assert digest == '71369a06a757df909a9c963b167c190821c07b5bea97c18cc321435008344229'
    recorder.run('actual-A02-closure-positive', [sys.executable, '-B', 'scripts/validate_restart_plan.py'], ROOT, env=env)
    recorder.run('new-closure-with-unchanged-historical-index-positive', [sys.executable, '-B', 'scripts/verify_evidence.py'], ROOT, env=env)
    held = recorder.root / 'held-underlying-proof.json'
    assert not held.exists()
    proof.rename(held)
    try:
        recorder.run('missing-actual-underlying-main-CI-proof-REJECTS', [sys.executable, '-B', 'scripts/validate_restart_plan.py'], ROOT, expected=1, env=env)
    finally:
        held.rename(proof)
    assert proof.read_bytes() == original and hashlib.sha256(proof.read_bytes()).hexdigest() == digest
    recorder.run('exact-proof-restoration-closure-positive', [sys.executable, '-B', 'scripts/validate_restart_plan.py'], ROOT, env=env)
    recorder.run('affected-make-docs-test', ['make', 'docs', 'test'], ROOT, env=env)
    recorder.run('all47-other46-closed7-frozen1508-scope', [sys.executable, '-B', 'docs/restart/implementation/A02/closure/check-scope.py', '--expect-closed'], ROOT, env=env)
    recorder.run('changed-current-docs-and-plan-whitespace', ['git', 'diff', '--check', 'b1c90139a651895284b2624da7d12903cf16bc9d', '--', 'plan/work-items.json', 'docs/restart/README.md', 'docs/restart/implementation/handoff.md'], ROOT, env=env)
    summary = {'source_product': 'b1c90139a651895284b2624da7d12903cf16bc9d',
               'actual_A02_closure_positive': True, 'historical_index_unchanged_with_new_closed_A02': True,
               'actual_missing_underlying_proof_rejected_exit': 1,
               'withheld_path': str(proof.relative_to(ROOT)), 'restored_bytes_sha256': digest,
               'exact_proof_restoration_positive': True, 'affected_make_docs_test_passed': True,
               'all47_criteria_dependencies_other46_closed7_frozen1508_scope_passed': True,
               'changed_current_docs_plan_whitespace_passed': True,
               'no_product_full_suite_migration48_or_replay_rerun': True,
               'commands_sha256': hashlib.sha256((recorder.root / 'commands.json').read_bytes()).hexdigest(),
               'limits': 'Actual local closure-metadata controls only; distinct final root review, protected PR/main checks and normal integration remain required.'}
    write_private(recorder.root / 'summary.json', canonical(summary))
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
