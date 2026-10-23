"""Distinct read-only check of the footer correction and full existing CI log."""
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import types

ROOT = Path(__file__).resolve().parents[5]
SOURCE = 'afc686e81632fc5d51cdb12c940d0b253df0388c'
OLD = '9d39469209afc8e35535cf8ba58dbe668a3f3224'
PREFIX = 'docs/restart/implementation/QP01/host-coordinator/cold-delivery/'

def blob(head, path):
    return subprocess.check_output(['git', 'show', head + ':' + path], cwd=ROOT)

def sha(data):
    return hashlib.sha256(data).hexdigest()

source = blob(SOURCE, PREFIX + 'verify-cold-capture.py')
old = blob(OLD, PREFIX + 'verify-cold-capture.py')
assert sha(source) == '7d5a1669ee2ff366ef34b710e8e8b3bdf25531d6e72ca3fc35442acc653f354d'
assert sha(old) == 'a5d0ab2d279bc944888f42b5b2b77c15e81f85bef6ce5ab59391662367d43e7a'
old_ast, new_ast = ast.parse(old), ast.parse(source)
assert [ast.dump(n) for n in ast.walk(old_ast) if isinstance(n, ast.Assert)] == [ast.dump(n) for n in ast.walk(new_ast) if isinstance(n, ast.Assert)]
old_first = next(n for n in old_ast.body if isinstance(n, ast.FunctionDef) and n.name == 'verify_first')
new_first = next(n for n in new_ast.body if isinstance(n, ast.FunctionDef) and n.name == 'verify_first')
assert ast.dump(old_first) == ast.dump(new_first)

raw = gzip.decompress(blob(SOURCE, PREFIX + 'full-validation/make-ci.log.gz'))
correspondence = json.loads(blob(SOURCE, PREFIX + 'full-validation/source-correspondence.json'))
command = json.loads(blob(SOURCE, PREFIX + 'full-validation/command.json'))
assert len(raw) == correspondence['raw_combined_log_bytes'] == 492016
assert sha(raw) == correspondence['raw_combined_log_sha256'] == '2de2df5f9efa5f99c2fdf87e1387d2a85ab08529fb77bcf3c5fd6bd231157fd8'
assert command['source'] == correspondence['executed_source'] == OLD
assert command['exit_code'] == correspondence['make_ci_exit_code'] == 0
assert command['before_source_clean'] is True and command['after_source_status'] == ''
module = types.ModuleType('reviewed_cold_capture')
exec(compile(source, SOURCE + ':' + PREFIX + 'verify-cold-capture.py', 'exec'), module.__dict__)
positive = module.verify_product(raw, SOURCE, str(ROOT))
assert positive['run'] is None and positive['proof_role'] == 'local_makeci_source_addon_no_GitHub_claim'
assert positive['generic_completed_capture_checker_remains_separately_mandatory'] is True

controls = []
def reject(name, changed):
    assert changed != raw
    try:
        module.verify_product(changed, SOURCE, str(ROOT))
    except (AssertionError, KeyError):
        controls.append({'control': name, 'rejected': True})
    else:
        raise AssertionError('Accepted changed receipt: ' + name)

needle = b'Ran 194 tests in '
assert raw.count(needle) == 1
reject('missing one Pi test', raw.replace(needle, b'Ran 193 tests in '))
needle = b'advisories ok, bans ok, licenses ok, sources ok'
assert raw.count(needle) == 3
reject('missing third successful fresh audit', raw.replace(needle, b'changed audit summary', 1))
needle = b'actual_unsettled_child_timeout_no_early_reuse_then_fresh": true'
assert raw.count(needle) == 1
reject('original no early reuse proof false', raw.replace(needle, needle[:-4] + b'false'))
changed, count = re.subn(rb'(?m)^(nsealr-pi-engine-fixture\s+)[0-9.]+(%\s+[0-9.]+%\s+ok)$', rb'\g<1>99.00\2', raw)
assert count == 1
reject('fixture coverage below original100 floor', changed)
root_digest = sha(blob(SOURCE, 'Cargo.toml')).encode()
assert 0 < raw.count(root_digest) < 20
reject('foreign retained native source binding', raw.replace(root_digest, b'0' * 64))

print(json.dumps({
    'verdict': 'PASS_DISTINCT_FINAL_CHECKER_SOURCE_AND_LOCAL_COMBINED_LOG_ONLY',
    'candidate': SOURCE,
    'checker_sha256': sha(source),
    'all_assert_ASTs_unchanged': True,
    'verify_first_AST_unchanged': True,
    'source_qualified_first_scope_review': 'b930b68b',
    'command': command,
    'positive': positive,
    'whole_log_negative_controls': controls,
    'limits': 'No product rerun and no hosted/PR/main receipt. afc metadata manifest has an independently reported ignored-pycache error pending correction; this review admits only the checker source and actual local combined trace. Final corrected packet, distinct product review, generic hosted verifier, protected integration and actual-main cold checks remain required.'
}, indent=2))
