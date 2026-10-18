import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
CANDIDATE='9e023ccef300ddeb738c377fe68b130a94123477'
EVIDENCE='dc4709e833d0e92a38ec6f4788c8586d7999b30f'
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def blob(commit,path): return git('show',f'{commit}:{path}')
def sha(data): return hashlib.sha256(data).hexdigest()
manifest=json.loads(blob(EVIDENCE,'docs/restart/S01/evidence/f02-results.json'))
assert manifest['source_candidate']==CANDIDATE
assert all(p.startswith('docs/restart/S01/evidence/') for p in git('diff','--name-only',CANDIDATE,EVIDENCE).decode().splitlines())
assert not git('diff','--name-only','da2869792af862e62022744585e5a4681c422838',CANDIDATE,'--','tests/fixtures/specs/vectors')
for artifact in manifest['artifacts']: assert sha(blob(EVIDENCE,artifact['path']))==artifact['sha256'],artifact
gates=[]
for item in manifest['validation']:
    record=json.loads(blob(EVIDENCE,item['manifest']))
    assert record['candidate_commit']==CANDIDATE and record['exit_code']==0
    assert sha(blob(EVIDENCE,item['manifest'].replace('.json','.log')))==record['log_sha256']
    gates.append({'manifest':item['manifest'],'command':record['command'],'log_sha256':record['log_sha256'],'exit_code':0,'classification':'author execution, independently hash-verified; not reviewer execution'})
sources=json.loads(blob(EVIDENCE,'docs/restart/S01/evidence/f01-node-sources.json'))
for source in sources['sources']:
    data=urllib.request.urlopen(source['url'],timeout=20).read()
    assert len(data)==source['bytes'] and sha(data)==source['sha256']
record={'source_candidate':CANDIDATE,'author_evidence_commit':EVIDENCE,'brief_sha256':sha(blob(CANDIDATE,'docs/restart/S01/brief.md')),'evidence_only_successor':True,'fixture_bytes_unchanged_since_da286979':True,'author_artifacts_hash_verified':manifest['artifacts'],'final_gates':gates,'node_source_hashes_verified':sources['sources']}
(HERE/'author-evidence-assessment.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'source_candidate':CANDIDATE,'artifacts_verified':len(manifest['artifacts']),'final_gate_records_verified':len(gates),'node_sources_verified':len(sources['sources'])}))
