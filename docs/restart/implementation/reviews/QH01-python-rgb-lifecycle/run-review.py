"""ONE real pre-G cancellation replay; retain exact unknown invoker, never kill."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
R00 = ROOT.parent / 'r00/tools/baseline/.work/final'
OUT = HERE / '.runtime/cancel-preG-01'
PREFIX = 'docs/restart/implementation/QH01/manual-port/python-rgb-composition/'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


preflight = json.loads((HERE / 'preflight.json').read_bytes())
assert preflight['candidate'] == '858eaf19a1f2b104112edb9842a479c035db301f'
assert not OUT.exists(), 'No overwrite/retry of the single admitted real replay'
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)
reuse = Path(preflight['same_root_for_bridge_and_packages'])
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=reuse)
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=reuse).decode().strip() == preflight['candidate']
for path, expected in preflight['runtime_source60'].items():
    assert sha(ROOT / path) == sha(reuse / path) == expected
for path, expected in preflight['prepared_generated62'].items():
    assert sha(reuse / path) == expected
for link in preflight['module_identity_links']:
    assert str(Path(link['path']).resolve()) == link['resolved']
for tool in preflight['tools'].values():
    assert sha(tool['path']) == tool['sha256']
worker = preflight['actual_worker_producer']
assert sha(worker['worker']) == worker['sha256']
assert sys.version_info[:3] == (3, 12, 15)
assert Path(sys.executable).resolve() == Path(preflight['tools']['python']['path']).resolve()
OUT.mkdir(parents=True)
environment = json.loads((R00 / 'environment.json').read_bytes())
assert isinstance(environment, dict) and all(isinstance(v, str) for v in environment.values())
for key, name in [('TMPDIR', 'tmp'), ('XDG_CACHE_HOME', 'cache'), ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data')]:
    (OUT / name).mkdir(); environment[key] = str(OUT / name)
environment['PYTHONDONTWRITEBYTECODE'] = '1'
argv = [preflight['tools']['python']['path'], '-B', str(ROOT / (PREFIX + 'run-composition.py')),
        '--output', str(OUT / 'composition'), '--worker', worker['worker'], '--sha256', worker['sha256'],
        '--node', preflight['tools']['node']['path'], '--bridge', str(reuse / 'apps/bridge/service/dist'),
        '--reuse', str(reuse), '--case', 'fixture_cancel_B3_verified_preG']
source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
command = {'role': 'ONE independent actual pre-G cancellation; no build/install/positive/full gate',
           'candidate': preflight['candidate'], 'wrapper_source': source,
           'wrapper_sha256': sha(__file__), 'preflight_sha256': sha(HERE / 'preflight.json'),
           'argv': argv, 'cwd': str(ROOT), 'environment': environment, 'python_version': sys.version,
           'node_version_by_exact_binary_and_original_normal_trace': '24.22.0',
           'host': platform.uname()._asdict(), 'started_utc': datetime.now(timezone.utc).isoformat(),
           'source_before': '', 'reuse_source_before': '', 'outer_watchdog': None}
write(OUT / 'command.json', command)
start = time.monotonic()
with (OUT / 'stdout.log').open('xb') as stdout, (OUT / 'stderr.log').open('xb') as stderr:
    process = subprocess.Popen(argv, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                               stdout=stdout, stderr=stderr, close_fds=True)
    command['invoker_pid'] = process.pid
    try:
        status = Path(f'/proc/{process.pid}/status').read_text().splitlines()
        command['actual_invoker_initial_status'] = [line for line in status if line.split(':')[0] in ['Name', 'State', 'Pid', 'PPid', 'Threads']]
        write(OUT / 'command.json', command)
    except BaseException:
        pass  # After spawn, fallible bookkeeping must not bypass collection.
    while True:
        try:
            pid, raw, _usage = os.wait4(process.pid, 0)
            assert pid == process.pid and (os.WIFEXITED(raw) or os.WIFSIGNALED(raw))
            break
        except InterruptedError:
            continue
        except BaseException:
            try:
                write(OUT / 'attention.json', {'reason': 'invoker status unavailable; exact handle retained', 'pid': process.pid})
                print('RETAINED UNKNOWN INVOKER; notify root; do not restart or kill', flush=True)
            except BaseException:
                pass
            while True:
                time.sleep(1)
    process.returncode = os.waitstatus_to_exitcode(raw)
command.update(invoker_wait_raw=raw, exit_code=process.returncode,
               elapsed_seconds_bookkeeping_only=time.monotonic() - start, completed_utc=datetime.now(timezone.utc).isoformat(),
               source_after=subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).decode(),
               reuse_source_after=subprocess.check_output(['git', 'status', '--porcelain'], cwd=reuse).decode())
try:
    os.wait4(process.pid, os.WNOHANG)
except ChildProcessError:
    command['after_actual_collection_ECHILD'] = True
else:
    raise RuntimeError('collected invoker unexpectedly waitable')
write(OUT / 'command.json', command)
print(json.dumps({'exit_code': process.returncode, 'actual_raw_wait': raw, 'invoker_pid': process.pid,
                  'elapsed_seconds': command['elapsed_seconds_bookkeeping_only'], 'output': str(OUT)}))
sys.exit(process.returncode)
