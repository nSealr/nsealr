#!/usr/bin/env python3
"""Independent public-scalar fixtures, cross-language checks, and exact migration."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import secp256k1

HERE = Path(__file__).resolve().parent
COMPANION = HERE.parents[4]
SPECS = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location('reviewed_verify_specs', SPECS / 'scripts/verify_specs.py')
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
def sign(event, scalar):
    # Independent canonical construction and signing: no DUT event_id helper.
    key = secp256k1.PrivateKey(scalar.to_bytes(32, 'big'), raw=True)
    event = dict(event, pubkey=key.pubkey.serialize()[1:].hex())
    raw = json.dumps([0,event['pubkey'],event['created_at'],event['kind'],event['tags'],event['content']], ensure_ascii=False, separators=(',', ':')).encode()
    event['id'] = hashlib.sha256(raw).hexdigest()
    event['sig'] = key.schnorr_sign(bytes.fromhex(event['id']), '', raw=True).hex()
    return event
inner = sign({'created_at':1700000000, 'kind':1, 'tags':[['t','review']], 'content':'independent review'}, 3)
outer = sign({'created_at':1700000000, 'kind':24133, 'tags':[['p','79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798']], 'content':'metadata fixture, not encrypted traffic'}, 2)
user = inner['pubkey']; assert user != outer['pubkey']
base = {'format':'nsealr-nip46-relay-response-step-v1', 'direction':'remote_signer_to_client', 'event':outer, 'decrypted_message':{'id':'independent-review','result':json.dumps(inner,separators=(',',':'))}, 'expected_user_pubkey':user}
cases = []
def case(name, step, expected):
    cases.append({'name':name, 'step':step, 'expected':expected})
case('valid distinct signed user', copy.deepcopy(base), True)
step=copy.deepcopy(base); step.pop('expected_user_pubkey'); case('unbound distinct signed user',step,True)
step=copy.deepcopy(base); step['expected_user_pubkey']=outer['pubkey']; case('expected user mismatch',step,False)
for field in ['id','sig']:
    step=copy.deepcopy(base); event=dict(inner); event[field]='0'*len(event[field]); step['decrypted_message']['result']=json.dumps(event);case('invalid inner '+field,step,False)
for field in ['id','sig']:
    step=copy.deepcopy(base); step['event'][field]='0'*len(step['event'][field]);case('invalid outer '+field,step,False)
step=copy.deepcopy(base); step['event']=sign(dict(outer,created_at=True),2);case('signed boolean outer timestamp',step,False)
step=copy.deepcopy(base); step['decrypted_message']['result']=json.dumps(sign(dict(inner,created_at=True),3));case('signed boolean inner timestamp',step,False)
for value, name in [(user,'public key'),('1'*64,'digit-only metadata key')]:
    step=copy.deepcopy(base);step['decrypted_message']['result']=value;step.pop('expected_user_pubkey');case(name,step,True)
for value in [None, 2, 'A'*64, 'bad']:
    step=copy.deepcopy(base);step['expected_user_pubkey']=value;case('invalid expected user '+repr(value),step,False)
for value,name in [('ack','ack'),('pong','pong'),('null','relay no change'),('["wss://one.example/","wss://two.example/"]','relay list')]:
    step=copy.deepcopy(base);step['decrypted_message']['result']=value;case(name,step,True)
step=copy.deepcopy(base);step['decrypted_message']={'id':'independent-review','result':'auth_url','error':'https://signer.example/auth'};case('auth challenge',step,True)
step=copy.deepcopy(base);step['decrypted_message']={'id':'independent-review','error':'cancelled'};case('error response',step,True)
for value,name in [('{"pub\\u006bey":"'+user+'",'+base['decrypted_message']['result'][1:],'escaped duplicate'),(base['decrypted_message']['result']+' null','trailing token'),('NaN','nonfinite literal'),('['*33+'null'+']'*33,'too deep'),('"'+'é'*512+'"','too many UTF-8 bytes')]:
    step=copy.deepcopy(base);step['decrypted_message']['result']=value;case(name,step,False)
json_cases=[]
for depth in range(32):
    json_cases.append({'raw':'['*depth+'{"a":0,"\\u0061":1}'+']'*depth,'expected':False})
    json_cases.append({'raw':'['*depth+'{"a":0,"b":1}'+']'*depth,'expected':True})
json_cases += [
    {'raw':'['*33+'0'+']'*33,'expected':False},
    {'raw':json.dumps('é'*511,ensure_ascii=False),'expected':True},
    {'raw':json.dumps('é'*511,ensure_ascii=False)+' ','expected':False},
    {'raw':'{"x":"\\\" [{] ","y":0}','expected':True},
    {'raw':'{"😀":0,"\\ud83d\\ude00":1}','expected':False},
    {'raw':'null true','expected':False}, {'raw':'NaN','expected':False}, {'raw':'Infinity','expected':False},
]
peer=json.loads(subprocess.check_output(['node',str(HERE/'evaluate.mjs')],input=json.dumps({'cases':cases,'json':json_cases}),text=True,cwd=COMPANION))
failed=[]
for index,c in enumerate(cases):
    errors=[]
    result=v.expected_nip46_relay_response_step('review-case',c['step'],errors)
    accepted=result is not None and not errors
    other=peer['cases'][index]
    passed=accepted == c['expected'] == other['ok'] and (not accepted or v.exact_json_equal(result,other['value']))
    print(json.dumps({'name':c['name'],'expected':c['expected'],'python_accepted':accepted,'typescript_accepted':other['ok'],'pass':passed,'python_errors':errors}))
    if not passed: failed.append(c['name'])
    if accepted:
        assert all(result[k] is False for k in ['decrypts_content','opens_relay','creates_grants','acknowledges_connect','dispatches_signer','stores_production_secrets','persists_session_state'])
for index,c in enumerate(json_cases):
    try: result=v.strict_nip46_result_json(c['raw']); accepted=True
    except (ValueError,UnicodeError,RecursionError): accepted=False;result=None
    other=peer['json'][index]
    if accepted != c['expected'] or other['ok'] != c['expected'] or (accepted and not v.exact_json_equal(result,other['value'])): failed.append('strict-json-'+str(index))
assert v.exact_json_equal({'a':False,'b':[1,2]},{'b':[1,2],'a':False})
for wrong in [{'a':0,'b':[1,2]},{'a':False,'b':[2,1]},{'a':False},{'a':False,'b':[1,2],'extra':0}]: assert not v.exact_json_equal({'a':False,'b':[1,2]},wrong)
print(json.dumps({'metadata_cases':len(cases),'strict_json_cases':len(json_cases),'failed':failed}))
assert not failed, failed
