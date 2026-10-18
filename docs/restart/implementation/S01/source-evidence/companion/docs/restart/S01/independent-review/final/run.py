#!/usr/bin/env python3
"""Preserve new-candidate evidence without overwriting the original failed review."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CANDIDATE = '9e023ccef300ddeb738c377fe68b130a94123477'
TOOLS = Path('/home/tux/nsealr/.restart-tools/goal/s01/.tmp/tools')
ENV = dict(os.environ)
ENV.update({'PATH': str(TOOLS / 'node-v24.22.0-linux-x64/bin') + ':' + str(TOOLS / 'pnpm/node_modules/.bin') + ':' + ENV['PATH'], 'CI': 'true', 'npm_config_loglevel': 'error', 'npm_config_store_dir': str(ROOT / '.tmp/pnpm-store'), 'PYTHONDONTWRITEBYTECODE': '1'})
def cmd(*argv):
    return subprocess.check_output(argv, cwd=ROOT, env=ENV, text=True).strip()
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
name, *argv = sys.argv[1:]
assert name and argv
changed = cmd('git', 'diff', '--name-only', CANDIDATE).splitlines()
assert all(p.startswith('docs/restart/S01/independent-review/') for p in changed), changed
record = {
    'reviewer': '/root/independent_bridge_review', 'source_candidate': CANDIDATE,
    'checkout_head': cmd('git', 'rev-parse', 'HEAD'), 'command': argv, 'cwd': str(ROOT),
    'started_utc': now(), 'dirty_status': cmd('git', 'status', '--short'),
    'environment': {'platform': platform.platform(), 'python': platform.python_version(), 'node': cmd('node', '--version'), 'npm': cmd('npm', '--version'), 'pnpm': cmd('pnpm', '--version'), 'CI': ENV['CI'], 'npm_config_store_dir': ENV['npm_config_store_dir'], 'lockfile_sha256': sha(ROOT / 'pnpm-lock.yaml')},
    'brief_sha256': sha(ROOT / 'docs/restart/S01/brief.md'),
    'source_sha256': {p: sha(ROOT / p) for p in ['packages/transport/src/transport.ts', 'packages/nip46/src/nip46.ts', 'tests/fixtures/specs/vectors/invalid/relay-step-response-unsupported-result.json']},
    'original_finding_commit': '67804a5d1995504a69d2fe49618da8e263ec3d89',
}
log = HERE / f'{name}.log'
with log.open('w') as output:
    result = subprocess.run(argv, cwd=ROOT, env=ENV, stdout=output, stderr=subprocess.STDOUT, timeout=240)
record.update({'finished_utc': now(), 'exit_code': result.returncode, 'log_sha256': sha(log)})
(HERE / f'{name}.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'command': argv, 'exit_code': result.returncode, 'log_sha256': record['log_sha256']}))
sys.exit(result.returncode)
