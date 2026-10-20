#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess
OWN=pathlib.Path(__file__).resolve().parent
ROOT=OWN.parents[4]
BASE='3cbd818a0bcd4016eb8983dad7605cb57280d913'
MAIN='f2ef70f522af4977e15f81554a8c6eadcdbe8097'
audit=json.loads((ROOT/'docs/restart/implementation/S03/source-audit.json').read_text())
rows=[]
for item in audit['input_files']:
    path=item['path']
    base=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
    current=subprocess.check_output(['git','show',MAIN+':'+path],cwd=ROOT)
    assert hashlib.sha256(base).hexdigest()==item['sha256'],path
    rows.append({'path':path,'accepted_input_sha256':item['sha256'],'frozen_main_sha256':hashlib.sha256(current).hexdigest(),'identical':base==current})
assert len(rows)==43 and sum(x['identical'] for x in rows)==41
assert {x['path'] for x in rows if not x['identical']}=={'docs/restart/README.md','docs/restart/work-items.json'}
result={'base':BASE,'frozen_main':MAIN,'files':rows,'identical':41,'changed':2}
(OWN/'evidence/main-reconciliation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'audited':len(rows),'identical':41,'changed':[x['path'] for x in rows if not x['identical']]}))
