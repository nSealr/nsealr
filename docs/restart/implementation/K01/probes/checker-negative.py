#!/usr/bin/env python3
"""Finite adversarial controls for the admitted offline K01 checker only."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    original = {key:(root/path).read_bytes() for key,path in {
        'fixtures':'independent-inputs.json','observed':'evidence/observed-events.json',
        'identities':'evidence/observed-identities.json','rejections':'evidence/observed-rejections.json'}.items()}
    cases = []
    def row_change(name, key, mutate):
        data = json.loads(original[key]); mutate(data)
        cases.append((name,key,json.dumps(data,ensure_ascii=True).encode()))
    for key in ['observed','identities','rejections']:
        row_change(key+'-missing',key,lambda data:data.pop())
        row_change(key+'-duplicate',key,lambda data:data.append(copy.deepcopy(data[0])))
        if key != 'identities':
            def extra(data): data[0]['id']='not-an-admitted-ID'
            row_change(key+'-extra-ID',key,extra)
    for key in ['canonical_hex','event_id','pubkey','signature']:
        def tamper(data,field=key):
            value=data[0][field];data[0][field]=('0' if value[0]!='0' else '1')+value[1:]
        row_change('actual-'+key,'observed',tamper)
    for field in ['created_at','kind','tags','content','id','pubkey','sig']:
        def tamper(data,name=field):
            event=json.loads(data[0]['signed_event_json'])
            if name in ['created_at','kind']: event[name]+=1
            elif name=='tags':event[name].append(['unknown','changed'])
            else:event[name]+='x'
            data[0]['signed_event_json']=json.dumps(event)
        row_change('serialized-'+field,'observed',tamper)
    for field in ['approval_calls','entropy_calls','sign_calls','output','layer']:
        def tamper(data,name=field):data[0][name]=True if name=='output' else 'parser' if name=='layer' else 1
        row_change('rejection-'+field,'rejections',tamper)
    row_change('rejection-bool-counter','rejections',lambda data:data[0].update(approval_calls=False))
    row_change('identity-original','identities',lambda data:data[0].update(original_scalar='0'*64))
    row_change('identity-normalized','identities',lambda data:data[2].update(normalized_backend=data[2]['original_scalar']))
    row_change('expected-auxiliary','fixtures',lambda data:data['vectors'][0].update(aux_hex='01'*32))
    cases.append(('malformed-json','observed',b'['))
    cases.append(('decoded-duplicate','observed',original['observed'].replace(b'"id":',b'"id":"fake","\\u0069d":',1)))
    rows=[]
    args.output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='k01-checker-controls-') as temporary:
        paths={key:Path(temporary)/(key+'.json') for key in original}
        for name,key,changed in cases:
            for field,data in original.items():paths[field].write_bytes(changed if field==key else data)
            argv=[sys.executable,'-B',str(root/'check_observed.py')]
            for field,path in paths.items():argv+=['--'+field,str(path)]
            p=subprocess.run(argv,capture_output=True)
            # A negative control must fail through validation, not missing tools.
            assert p.returncode==1 and p.stderr.decode().splitlines()[-1].startswith(('ValueError:', 'json.decoder.JSONDecodeError:')), (name,p.returncode,p.stderr)
            (args.output/(name+'.stdout.log')).write_bytes(p.stdout)
            (args.output/(name+'.stderr.log')).write_bytes(p.stderr)
            (args.output/(name+'.input.json')).write_bytes(changed)
            rows.append({'id':name,'mutated_file_role':key,'exit':p.returncode,
                         'input_sha256':hashlib.sha256(changed).hexdigest(),
                         'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),
                         'stderr_sha256':hashlib.sha256(p.stderr).hexdigest()})
    result={'controls':len(rows),'all_rejected':True,'original_inputs':{k:hashlib.sha256(v).hexdigest() for k,v in original.items()},'rows':rows}
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'controls':len(rows),'all_rejected':True}))


if __name__=='__main__':main()
