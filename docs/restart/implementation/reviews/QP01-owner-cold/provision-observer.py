"""Record actual Cargo stdout while invoking the unmodified finite producer."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys

source, evidence = map(Path, sys.argv[1:3])
path = source / 'docs/restart/implementation/QP01/request-engine/exchange.py'
spec = importlib.util.spec_from_file_location('reviewed_exchange', path)
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)
actual_run = subprocess.run
calls = []


def observe(*args, **kwargs):
    result = actual_run(*args, **kwargs)
    argv = args[0]
    if argv[:2] == ['cargo', 'build']:
        name = 'cargo-' + str(len(calls) + 1) + '.stdout.jsonl'
        raw = result.stdout.encode('utf-8')
        (evidence / name).write_bytes(raw)
        calls.append({'argv': argv, 'cwd': str(kwargs['cwd']), 'exit': result.returncode,
                      'raw_stdout': name, 'raw_stdout_sha256': hashlib.sha256(raw).hexdigest()})
    return result


producer.subprocess.run = observe
try:
    identities = producer.provision()
finally:
    producer.subprocess.run = actual_run
    (evidence / 'cargo-calls.json').write_text(json.dumps(calls, indent=2) + '\n')
(evidence / 'identities.json').write_text(json.dumps(identities, indent=2) + '\n')
print(json.dumps({'reviewer_provision': identities, 'actual_build_commands': len(calls)}))
