"""Finite review command recorder; no timeout can kill an unsettled owner."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

review = Path(__file__).resolve().parent
runtime = review / '.runtime'
source = runtime / 'source'
name, *argv = sys.argv[1:]
evidence = review / name
evidence.mkdir(exist_ok=False)
env = json.loads((runtime / 'environment.json').read_text())
if (review / 'provision-01/identities.json').exists():
    env.update(json.loads((review / 'provision-01/identities.json').read_text()))
record = {'candidate': '9d39469209afc8e35535cf8ba58dbe668a3f3224',
          'candidate_tree': 'ae40e5a3f6b0c8d13238f2477a9f643ee5eda466',
          'argv': argv, 'cwd': str(source), 'environment': env,
          'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'recorder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'timeout': 'none; actual unsettled-owner cleanup may retain this session'}
(evidence / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
start = time.monotonic()
with (evidence / 'stdout.log').open('wb') as out, (evidence / 'stderr.log').open('wb') as err:
    child = subprocess.Popen(argv, cwd=source, env=env, stdout=out, stderr=err)
    (runtime / 'active.json').write_text(json.dumps({'pid': child.pid, 'command': argv, 'output': str(evidence)}) + '\n')
    code = child.wait()
record.update(exit=code, duration_seconds=time.monotonic() - start,
              outputs={n: hashlib.sha256((evidence / n).read_bytes()).hexdigest() for n in ['stdout.log', 'stderr.log']})
(evidence / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
(runtime / 'active.json').unlink()
print(json.dumps({'name': name, 'exit': code, 'seconds': record['duration_seconds']}))
if code:
    print((evidence / 'stderr.log').read_text()[-2500:])
sys.exit(code)
