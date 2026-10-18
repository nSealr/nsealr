#!/usr/bin/env python3
"""Record a reviewer command without changing product source or author worktree."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TOOLS = Path('/home/tux/nsealr/.restart-tools/goal/s01/.tmp/tools')
ENV = dict(os.environ)
ENV.update({
    'PATH': str(TOOLS / 'node-v24.22.0-linux-x64/bin') + ':' + str(TOOLS / 'pnpm/node_modules/.bin') + ':' + ENV['PATH'],
    'CI': 'true',
    'npm_config_loglevel': 'error',
    'npm_config_store_dir': str(ROOT / '.tmp/pnpm-store'),
})
def command(*args):
    return subprocess.check_output(args, cwd=ROOT, env=ENV, text=True).strip()
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

name, *argv = sys.argv[1:]
assert name and argv
product_changes = command('git', 'diff', '--name-only', 'd385ddb0c775a1e863e9db0ee9ae38fee5f19057')
assert not any(not p.startswith('docs/restart/S01/independent-review/') for p in product_changes.splitlines()), product_changes
record = {
    'reviewer': '/root/independent_bridge_review',
    'source_candidate': 'd385ddb0c775a1e863e9db0ee9ae38fee5f19057',
    'checkout_head': command('git', 'rev-parse', 'HEAD'),
    'command': argv,
    'cwd': str(ROOT),
    'started_utc': now(),
    'dirty_status': command('git', 'status', '--short'),
    'environment': {'platform': platform.platform(), 'python': platform.python_version(), 'node': command('node', '--version'), 'npm': command('npm', '--version'), 'pnpm': command('pnpm', '--version'), 'CI': ENV['CI'], 'npm_config_store_dir': ENV['npm_config_store_dir'], 'lockfile_sha256': sha(ROOT / 'pnpm-lock.yaml')},
    'transport': 'Node/pnpm executables read from author tool directory; isolated dependency install used an independently copied pnpm store with --offline --frozen-lockfile. All workspace packages rebuilt in reviewer worktree; no author dist or node_modules resolution.',
    'node_archive_sha256': sha(TOOLS / 'node-v24.22.0-linux-x64.tar.xz'),
    'brief_sha256': sha(ROOT / 'docs/restart/S01/brief.md'),
    'source_sha256': {p: sha(ROOT / p) for p in ['packages/nip46/src/session-manager.ts', 'packages/nip46/src/session-protocol.ts', 'packages/nip46/src/nip46.ts', 'packages/nip46/src/relay-pool-adapter.ts', 'packages/protocol/src/encoding.ts', 'packages/framing/src/serial.ts', 'packages/transport/src/transport.ts', 'apps/cli/src/index.ts']},
}
log = HERE / f'{name}.log'
with log.open('w') as output:
    result = subprocess.run(argv, cwd=ROOT, env=ENV, stdout=output, stderr=subprocess.STDOUT, timeout=240)
record.update({'finished_utc': now(), 'exit_code': result.returncode, 'log_sha256': sha(log)})
(HERE / f'{name}.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'command': argv, 'exit_code': result.returncode, 'log_sha256': record['log_sha256']}))
sys.exit(result.returncode)
