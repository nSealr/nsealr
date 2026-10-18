#!/usr/bin/env python3
"""Run against an archived exact specs product in the reviewer's writable scope."""
import datetime
import fcntl
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile

HERE=Path(__file__).resolve().parent
COMPANION=HERE.parents[4]
SOURCE=Path('/home/tux/nsealr/.restart-tools/goal/specs-s01')
PRODUCT='b0022f3dd8b1c2b1bb553c0e5f84e81fb312396a'
BRIDGE='9e023ccef300ddeb738c377fe68b130a94123477'
PYTHON=Path('/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/python/bin')
TOOLS=Path('/home/tux/nsealr/.restart-tools/goal/s01/.tmp/tools')
SNAPSHOT=COMPANION/'.tmp'/f'specs-reviewed-{PRODUCT}'
ENV=dict(os.environ)
ENV.update({'PYTHONDONTWRITEBYTECODE':'1','PATH':str(PYTHON)+':'+str(TOOLS/'node-v24.22.0-linux-x64/bin')+':'+str(TOOLS/'pnpm/node_modules/.bin')+':'+ENV['PATH'],'CI':'true'})
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*argv):return subprocess.check_output(['git',*argv],cwd=SOURCE)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
with (COMPANION/'.tmp/specs-review-archive.lock').open('w') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if not SNAPSHOT.exists():
        SNAPSHOT.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(git('archive',PRODUCT))) as archive:archive.extractall(SNAPSHOT,filter='data')
sources={}
for name in ['scripts/verify_specs.py','scripts/verify_repo.py','tests/test_nip46_response_v1.py','tests/test_checkout_structure.py','requirements.txt','docs/S01-metadata-v1.md','docs/evidence/S01/fixture-migration.json']:
    data=(SNAPSHOT/name).read_bytes();assert data==git('show',f'{PRODUCT}:{name}');sources[name]=sha(data)
name,place,*argv=sys.argv[1:]
argv=[a.replace('{snapshot}',str(SNAPSHOT)).replace('{companion}',str(COMPANION)) for a in argv]
cwd=SNAPSHOT if place=='specs' else COMPANION
assert place in ['specs','companion']
record={'reviewer':'/root/independent_bridge_review','specs_source_candidate':PRODUCT,'bridge_source_candidate':BRIDGE,'archived_specs_root':str(SNAPSHOT),'command':argv,'cwd':str(cwd),'started_utc':now(),'environment':{'platform':platform.platform(),'python':subprocess.check_output([str(PYTHON/'python3'),'--version'],text=True).strip(),'PYTHONDONTWRITEBYTECODE':'1','runtime_note':'Pinned R00 Python executable and installed secp256k1 read as transport; tests run in isolated git-archive snapshot, with no author checkout writes.'},'source_sha256':sources}
log=HERE/f'{name}.log'
with log.open('w') as output:result=subprocess.run(argv,cwd=cwd,env=ENV,stdout=output,stderr=subprocess.STDOUT,timeout=240)
record.update({'finished_utc':now(),'exit_code':result.returncode,'log_sha256':sha(log.read_bytes())})
(HERE/f'{name}.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'command':argv,'exit_code':result.returncode,'log_sha256':record['log_sha256']}))
sys.exit(result.returncode)
