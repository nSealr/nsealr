"""Verify the reviewed product source, retained tests and source-bound evidence."""
import ast
import collections
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = '994a8b682ed6cd52bb46608b90794c02d2a9d3cb'
CANDIDATE = '4ab6e46e3f6e332d38bb049ed4988bec9f3550cf'
EXECUTED = '69a090254738cbf6368b37c2ebb820a99bf83ea4'
P = 'docs/restart/implementation/QP01/probe-readiness/'
PRODUCT = 'apps/pi/app/nsealr_vault/hardware_probe.py'
TEST = 'apps/pi/tests/test_seed_signer_hardware.py'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def blob(path, commit=CANDIDATE):
    return git('show', f'{commit}:{path}')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def doc(path):
    return json.loads(blob(path))


manifest = doc(P + 'artifact-manifest.json')
assert len(manifest['artifacts']) == manifest['member_count'] == 21
paths = {x.decode() for x in git('ls-tree', '-rz', '--name-only', CANDIDATE, '--', P).split(b'\0') if x}
assert len({x['path'] for x in manifest['artifacts']}) == 21
assert paths == {x['path'] for x in manifest['artifacts']} | {P + 'artifact-manifest.json'}
for x in manifest['artifacts']:
    data = blob(x['path'])
    assert len(data) == x['bytes'] and sha(data) == x['sha256']
    assert git('ls-tree', CANDIDATE, '--', x['path']).decode().split()[0] == x['mode'] == '100644'
delta = [x.split('\t') for x in git('diff', '--name-status', BASE, CANDIDATE).decode().splitlines()]
assert len(delta) == 24
assert {path for status, path in delta if status == 'M'} == {PRODUCT, TEST}
assert {path for status, path in delta if status == 'A'} == paths
assert all(status in ('A', 'M') for status, _ in delta)
for path in (PRODUCT, TEST):
    assert blob(path) == blob(path, EXECUTED)
assert sha(blob(PRODUCT)) == '525734ce67618b59d8f30d2e3fcd5dd74c5e956a259f24419cd82857a7d3d0b8'
assert sha(blob(TEST)) == 'b1a07e0ea05eacd15fd9cbb3b6285fd6187e03e31d912934b1bb75154623cbe4'


def definitions(data):
    nodes = ast.walk(ast.parse(data))
    return collections.Counter(ast.dump(x, include_attributes=False) for x in nodes
                               if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))


old = definitions(blob(TEST, BASE))
new = definitions(blob(TEST))
assert sum(old.values()) == 93 and not (old - new)
for path in ('apps/pi/tests/test_vault_core.py', 'apps/pi/Makefile',
             'plan/work-items.json', 'docs/restart/implementation/R00/evidence/final/environment.json'):
    assert blob(path) == blob(path, BASE)
result = doc(P + 'result.json')
for name in ('brief.md', 'expectations.json', 'source-bindings.json'):
    assert blob(P + name) == blob(P + name, result['precode_brief_expectations_source_record'])
assert blob(TEST) == blob(TEST, result['regression_test_definitions_before_fix'])
for run in result['actual_commands']:
    directory = run['directory'] + '/'
    command = doc(directory + 'command.json')
    assert command['source_commit'] == run['source_commit']
    assert command['exit_code'] == run['exit_code']
    assert sha(blob(directory + 'command.json')) == run['command_sha256']
    assert sha(blob(directory + 'stdout.log')) == run['stdout_sha256']
    assert sha(blob(directory + 'stderr.log')) == run['stderr_sha256']
    for path, digest in command['source_hashes'].items():
        assert sha(blob(path, command['source_commit'])) == digest
    if 'environment_sha256' in command:
        assert sha(blob(command['environment_source'])) == command['environment_sha256']
    if run['role'].startswith('Actual3RED'):
        assert blob(PRODUCT, run['source_commit']) == blob(PRODUCT, BASE) and run['exit_code'] == 1
    else:
        assert command['source_commit'] == EXECUTED and run['exit_code'] == 0
independent = json.loads(Path(__file__).with_name('independent-results.json').read_text())
assert independent['all_passed'] and independent['case_count'] == 70
assert independent['product_source_sha256'] == sha(blob(PRODUCT))
Path(__file__).with_name('validation.json').write_text(json.dumps({
    'candidate': CANDIDATE, 'tree': git('rev-parse', CANDIDATE + '^{tree}').decode().strip(),
    'reviewer': '/root', 'verdict': 'PASS_SCOPED_PI_PROBE_SOURCE_TEST_AND_PROOF_CORRESPONDENCE',
    'checked': {'manifest_members': 21, 'new_evidence_paths': 22, 'modified_product_test_paths': 2,
                'original_definition_AST_nodes_retained': 93, 'original_vault_tests_makefile_plan_R00_exact': True,
                'precode_brief_expectations_bindings_exact': True, 'test_source_before_RED_exact': True,
                'RED_focused_full_CI_source_receipts': 3, 'executed_final_source_equal_candidate': True,
                'root_independent_matrix_cases': 70},
    'suite_reuse': 'Author full Pi CI on identical69a source:173 tests and unchanged verify/compile/pip/docs recipe. No full suite repeated for metadata-only finalization; integrated-candidate CI remains mandatory.',
    'limitations': 'Read-only file-text and two service-query classification, synthetic inputs only; no actual Pi/hardware/loaded-config/global remote-access or release evidence.'
}, indent=2) + '\n')
print('PASS: two source/test paths; 21 manifest members;93 original definitions; three source-bound runs; independent70-case matrix. No task or physical acceptance.')
