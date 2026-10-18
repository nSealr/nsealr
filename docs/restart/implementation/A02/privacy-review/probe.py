import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/home/tux/nsealr/.restart-tools/goal/a02-admission-review-private')
AUTHOR = Path('/home/tux/nsealr/.restart-tools/goal/a02/tools/migration/.runtime/privacy-01')
REPO = Path('/home/tux/nsealr/lab')
COMMIT = '3303ab17a28ed32419576627d5abb93db3999635'
PYTHON = Path('/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/python/bin/python3')
SOURCE = ('scripts/integration_feature_matrix.py', 'tests/test_integration_feature_matrix.py')
sha = lambda data: hashlib.sha256(data).hexdigest()
summary = json.loads((AUTHOR / 'summary.json').read_text())
assert summary['source_commit'] == COMMIT
assert sha(PYTHON.resolve().read_bytes()) == 'eaaa308032c4aa063df5880c4c293cd458b4629d503fbc2c03ec163d71f7f790'
rows = {r['source_path']: r for r in summary['files']}
before = {p: subprocess.check_output(['git', '-C', str(REPO), 'show', COMMIT + ':' + p]) for p in SOURCE}
after = {p: (AUTHOR / Path(p).name).read_bytes() for p in SOURCE}

def paths(data):
    assignment = next(n for n in ast.parse(data).body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'LAB_DOCS' for t in n.targets))
    return [n.value for n in ast.walk(assignment.value)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]

old_paths, new_paths = paths(before[SOURCE[0]]), paths(after[SOURCE[0]])
assert len(old_paths) == len(new_paths) == len(set(old_paths)) == len(set(new_paths)) == 3
assert new_paths == [f'docs/historical-feature-contract-{i:02d}.md' for i in range(1, 4)]
mapping = dict(zip(old_paths, new_paths))

class Normalize(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value in mapping:
            node.value = mapping[node.value]
        return node

def mask(data, literals):
    offsets = [0]
    for line in data.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    spans = [(offsets[n.lineno - 1] + n.col_offset,
              offsets[n.end_lineno - 1] + n.end_col_offset)
             for n in ast.walk(ast.parse(data))
             if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in literals]
    masked = data
    for start, end in sorted(spans, reverse=True):
        masked = masked[:start] + b'<approved-literal>' + masked[end:]
    return masked, len(spans)

results = []
for index, path in enumerate(SOURCE):
    assert sha(before[path]) == rows[path]['before_sha256']
    assert sha(after[path]) == rows[path]['after_sha256']
    expected = Normalize().visit(copy.deepcopy(ast.parse(before[path])))
    assert ast.dump(expected) == ast.dump(ast.parse(after[path]))
    left, count = mask(before[path], set(old_paths))
    right, after_count = mask(after[path], set(new_paths))
    assert left == right and count == after_count == (3 if index == 0 else 4)
    assert not any(s.encode() in after[path] for s in old_paths)
    assert not any(Path(s).name.encode() in after[path] for s in old_paths)
    results.append({'source_path': path, 'before_sha256': sha(before[path]),
                    'after_sha256': sha(after[path]), 'literal_spans': count,
                    'all_nonliteral_bytes_identical': True, 'ast_equivalent_under_explicit_renaming': True})

public_tool = subprocess.check_output(['git', '-C', '/home/tux/nsealr/firmware', 'show',
                                     '325448c126ba1bc9f95a8a4ed593b6105a331986:tools/migration/sanitize_lab_paths.py'])
assert not any(s.encode() in public_tool or Path(s).name.encode() in public_tool for s in old_paths)
assert sha((AUTHOR / 'private-full.patch').read_bytes()) == summary['private_patch_sha256']
commands = []
for label, files in [('before', before), ('after', after)]:
    directory = ROOT / label
    assert not directory.exists()
    directory.mkdir(mode=0o700)
    for name, data in files.items():
        dest = directory / name
        dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        dest.write_bytes(data)
        dest.chmod(0o600)
    command = [str(PYTHON), '-B', '-m', 'unittest', 'discover', '-s', 'tests',
               '-p', 'test_integration_feature_matrix.py', '-v']
    run = subprocess.run(command, cwd=directory, capture_output=True)
    log = run.stdout + run.stderr
    (ROOT / (label + '-tests.log')).write_bytes(log)
    (ROOT / (label + '-tests.log')).chmod(0o600)
    commands.append({'label': label, 'command': command, 'exit_code': run.returncode,
                     'log_sha256': sha(log), 'five_original_cases_passed': run.returncode == 0 and b'Ran 5 tests' in log})
    assert run.returncode == 0 and b'Ran 5 tests' in log
result = {'reviewer': '/root', 'scope': 'Two-file pre-import privacy exception only; no migration admission',
          'source_commit': COMMIT, 'tooling_candidate': '325448c126ba1bc9f95a8a4ed593b6105a331986',
          'files': results, 'private_patch_sha256': summary['private_patch_sha256'],
          'public_tool_omits_excluded_strings': True, 'commands': commands,
          'limits': 'External document addresses intentionally change. Runtime migration and later functional assertion adaptation remain separately unaccepted. No target repository/history assembled.'}
(ROOT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
(ROOT / 'result.json').chmod(0o600)
print('PASS: 7 exact literal-only spans, nonliteral bytes and normalized AST verified; original/sanitized five-case suites pass in separate private directories; public tool omits originals')
