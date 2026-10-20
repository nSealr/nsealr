#!/usr/bin/env python3
"""Read-only, exact-candidate documentary review; writes only reviewer output."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
BASE = 'b1c90139a651895284b2624da7d12903cf16bc9d'
CANDIDATE = '268d2c52456f107cf369b54316c29ef35be10751'
SOURCE = '8525ce01ad02466b78654e31c672774c99d256da'
PREFIX = 'docs/restart/implementation/P02/integration/'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def body(commit, path):
    return git('show', commit + ':' + path)

def read(path):
    return (ROOT / path).read_bytes()

def load(path):
    return json.loads(read(path))

def binding(row, commit, path):
    mode, kind, blob = git('ls-tree', commit, '--', path).decode().split('\t')[0].split()
    raw = body(commit, path)
    assert (mode, kind, blob) == (row['mode'], 'blob', row['blob']), path
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], path
    return raw

assert git('rev-parse', 'HEAD').decode().strip() == CANDIDATE
assert git('rev-parse', CANDIDATE + '^{tree}').decode().strip() == 'e0080af94384c89bb0efc7c609ee8840d9422fcf'
changes = [line.split('\t') for line in git('diff', '--name-status', BASE, CANDIDATE).decode().splitlines()]
assert len(changes) == 32 and all(status == 'A' for status, _ in changes)
assert all(path.startswith('docs/restart/implementation/P02/') or path in
           ['docs/product/compatibility-plan.md', 'docs/product/research-protocols.md'] for _, path in changes)
mapping = load(PREFIX + 'source-map.json')
copies = mapping['historical_exact_copies']
assert len(copies) == 17
by_source = {row['source_path']: row for row in copies}
for row in copies:
    raw = binding(row, row['source_commit'], row['source_path'])
    assert raw == read(row['destination']) == body(row['original_review_or_candidate'], row['source_path'])
    assert body(CANDIDATE, row['destination']) == raw
    assert git('ls-tree', CANDIDATE, '--', row['destination']).decode().split()[0] == row['mode']
paired = 0
for name in ['P02-final', 'P02-spec']:
    manifest = load(by_source['docs/restart/implementation/reviews/' + name + '/review-artifacts.json']['destination'])
    for item in manifest['candidate_files'] + manifest['files']:
        copied = read(by_source[item['path']]['destination'])
        assert sha(copied) == item['sha256'] and len(copied) == item['bytes']
        paired += 1
assert paired == 22
for row in mapping['current_context']:
    raw = binding(row, row['current_commit'], row['current_path'])
    assert row['current_commit'] == BASE and raw == read(row['current_path'])
    old = row['historical_source']
    assert sha(body(old['commit'], old['path'])) == old['sha256']
assert len(mapping['current_context']) == 11
targets = load(PREFIX + 'target-bindings.json')
rows = targets['product_documents'] + targets['scoped_source_records']
assert len(rows) == 29
for row in rows:
    assert binding(row, row['commit'], row['path']) == read(row['path'])
result = load(PREFIX + 'result.json')
assert not result['task_complete'] and not result['graph_status_changed'] and result['parent_criteria_closed'] == 0
for row in result['artifacts']:
    assert sha(read(row['path'])) == row['sha256'] and len(read(row['path'])) == row['bytes']
assert len(result['artifacts']) == 29
plan = json.loads(body(BASE, 'plan/work-items.json'))
p02 = next(row for row in plan['tasks'] if row['id'] == 'P02')
assert mapping['canonical_five_criteria'] == p02['acceptance']
assert [row['criterion'] for row in result['all5_criteria_preserved']] == p02['acceptance']
old = body(SOURCE, 'docs/restart/implementation/P02/compatibility-plan.md').decode()
new = read('docs/product/compatibility-plan.md').decode()
cases = lambda text: [line for line in text.splitlines() if re.match(r'\| P02-[A-Z]\d\d\b', line)]
assert len(cases(new)) == 31 and cases(old) == cases(new)
old = body(SOURCE, 'docs/restart/implementation/P02/research-protocols.md').decode()
new = read('docs/product/research-protocols.md').decode()
assert old[old.index('These are manual procedures'):] == new[new.index('These are manual procedures'):]
assert len(re.findall(r'^## Script [A-D]', new, re.M)) == 4
links = 0
for path in ['docs/product/compatibility-plan.md', 'docs/product/research-protocols.md', PREFIX + 'README.md',
             'docs/restart/implementation/P02/historical/README.md']:
    for raw in re.findall(r'\[[^\]\n]*\]\(([^\s)]+)\)', read(path).decode()):
        url = urlsplit(raw)
        if url.scheme or url.netloc or not url.path:
            continue
        target = ((ROOT / path).parent / unquote(url.path)).resolve()
        assert target.is_relative_to(ROOT) and target.exists(), (path, raw)
        links += 1
for row in load(PREFIX + 'commands.json')['records']:
    assert row['exit_code'] == 0 and sha(read(PREFIX + row['log'])) == row['sha256']
assert body(BASE, 'plan/work-items.json') == read('plan/work-items.json')
for path in ['plan/evidence-index.json', 'scripts/verify_contracts.py', 'scripts/validate_restart_plan.py']:
    assert body(BASE, path) == read(path)
output = {'candidate': CANDIDATE, 'base': BASE, 'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'outcome': 'PASS_documentary_current_layout_only', 'added_paths': 32,
          'historical_copies': 17, 'paired_manifest_dependencies': paired, 'current_contexts': 11,
          'immutable_postimage_bindings': 29, 'author_receipt_bindings': 29,
          'unchanged_scenarios': 31, 'unchanged_full_procedures': 4, 'resolved_current_links': links,
          'graph_and_frozen_index_unchanged': True, 'runtime_human_hardware_or_release_evidence': False}
(OUT / 'probe-result.json').write_text(json.dumps(output, indent=2) + '\n')
print(json.dumps(output))
