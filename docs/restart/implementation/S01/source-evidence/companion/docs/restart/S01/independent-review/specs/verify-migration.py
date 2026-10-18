import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
BRIDGE=HERE.parents[4]
SPECS=Path('/home/tux/nsealr/.restart-tools/goal/specs-s01')
PRODUCT='b0022f3dd8b1c2b1bb553c0e5f84e81fb312396a'
EVIDENCE='062f250268bfde76162b3820acbef33200e253fc'
BRIDGE_PRODUCT='9e023ccef300ddeb738c377fe68b130a94123477'
def git(repo,*argv):return subprocess.check_output(['git',*argv],cwd=repo)
def blob(repo,commit,path):return git(repo,'show',f'{commit}:{path}')
def sha(data):return hashlib.sha256(data).hexdigest()
manifest=json.loads(blob(SPECS,PRODUCT,'docs/evidence/S01/fixture-migration.json'))
assert len(manifest['changes'])==22
source_paths={c['source_path'] for c in manifest['changes']}
actual=set(git(BRIDGE,'diff','--no-renames','--name-only',manifest['source_companion_base'],BRIDGE_PRODUCT,'--','tests/fixtures/specs/vectors').decode().splitlines())
assert source_paths==actual
dest_paths={c['destination_path'] for c in manifest['changes']}
actual_dest=set(git(SPECS,'diff','--no-renames','--name-only',manifest['input_specs_commit'],PRODUCT,'--','vectors').decode().splitlines())
assert dest_paths==actual_dest
for c in manifest['changes']:
    if c['before_sha256'] is not None:
        assert sha(blob(SPECS,manifest['input_specs_commit'],c['destination_path']))==c['before_sha256']
        assert sha(blob(BRIDGE,manifest['source_companion_base'],c['source_path']))==c['before_sha256']
    if c['after_sha256'] is not None:
        left=blob(SPECS,PRODUCT,c['destination_path']);right=blob(BRIDGE,BRIDGE_PRODUCT,c['source_path'])
        assert left==right and sha(left)==c['after_sha256']
    else:
        assert not git(SPECS,'ls-tree',PRODUCT,'--',c['destination_path'])
        assert not git(BRIDGE,'ls-tree',BRIDGE_PRODUCT,'--',c['source_path'])
assert all(p.startswith('docs/evidence/S01/') for p in git(SPECS,'diff','--name-only',PRODUCT,EVIDENCE).decode().splitlines())
gate=json.loads(blob(SPECS,EVIDENCE,'docs/evidence/S01/boolean-timestamp-final-ci.json'))
assert gate['candidate']==PRODUCT and gate['exit_code']==0 and gate['tests']==92
assert sha(blob(SPECS,EVIDENCE,gate['log']))==gate['sha256']
record={'specs_source_candidate':PRODUCT,'specs_evidence_commit':EVIDENCE,'bridge_source_candidate':BRIDGE_PRODUCT,'migration_manifest_sha256':sha(blob(SPECS,PRODUCT,'docs/evidence/S01/fixture-migration.json')),'exact_changes_verified':manifest['changes'],'extra_or_missing_fixture_changes':[],'author_final_ci':gate,'author_final_ci_classification':'author execution, independently hash-verified','source_unchanged_in_evidence_successor':True}
(HERE/'migration-assessment.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'exact_fixture_changes_verified':len(manifest['changes']),'author_exact_source_ci_verified':True,'source_unchanged_in_evidence_successor':True}))
