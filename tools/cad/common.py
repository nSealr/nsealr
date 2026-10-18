"""Small evidence helpers. No global KiCad configuration or environment dump."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def runtime():
    return Path(os.environ['CAD_TOOLS_ROOT']).resolve()

def output():
    return Path(os.environ['CAD_QUAL_ROOT']).resolve()

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + '\n')

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def environment(base):
    # Keep ordinary host launch variables, but never inherit an unrelated IPC token.
    env = dict(os.environ)
    env.pop('KICAD_API_TOKEN', None)
    env.update(KICAD_CONFIG_HOME=str(base/'config'),
               KICAD_DOCUMENTS_HOME=str(base/'documents'),
               XDG_CACHE_HOME=str(base/'cache'), XDG_RUNTIME_DIR=str(base/'runtime'),
               TMPDIR=str(base/'runtime'), LIBGL_ALWAYS_SOFTWARE='1',
               KIPILOT_ENABLE_MUTATIONS='false', PYTHONDONTWRITEBYTECODE='1')
    return env

def run(name, argv, *, env=None, expected=0, timeout=180, out=None):
    out = out or output()
    logdir = out/'logs'
    logdir.mkdir(exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    start = now()
    argv = list(map(str, argv))
    try:
        p = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=timeout)
        code, stdout, stderr = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        code = 'timeout'
        stdout = exc.stdout or b''
        stderr = exc.stderr or b''
        if isinstance(stdout, bytes): stdout = stdout.decode(errors='replace')
        if isinstance(stderr, bytes): stderr = stderr.decode(errors='replace')
    stem = f'{stamp}-{name}'
    (logdir/f'{stem}.stdout').write_text(stdout)
    (logdir/f'{stem}.stderr').write_text(stderr)
    row = {'start_utc':start, 'end_utc':now(), 'name':name, 'argv':argv,
           'returncode':code, 'expected':expected,
           'stdout':f'logs/{stem}.stdout', 'stderr':f'logs/{stem}.stderr'}
    with (out/'commands.jsonl').open('a') as f:
        f.write(json.dumps(row)+'\n')
    print(name, code, flush=True)
    if expected is not None:
        require(code == expected, f'{name}: return {code}, expected {expected}; see {stem}')
    return stdout
