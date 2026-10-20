#!/usr/bin/env python3
"""Decode three exact normative preimages; no product/runtime execution."""
import base64, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
C='6324aaa9f71b55c57b076f4d402e8056e8f63488'
B='503719d5c607bdbcd1da30a89b0c3c6f5983c01b'
def body(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def sha(d):return hashlib.sha256(d).hexdigest()
spec=json.loads(body(C,'docs/restart/implementation/T01/integration/source-reconciliation.json'))
outputs={'field-7bc474eb9fd65cd1f1cdfd09.txt','field-b69c96b873204e5c324385c0.txt','field-275b00adc2cdd30c17c95c67.txt'}
observations=[]
for row in spec['SSOT_projection_reconciliation']:
 mapping=row['mapping']
 if mapping['output'] not in outputs:continue
 path='protocols/contracts/v1/'+mapping['artifact_path'];raw=body(B,path);source=json.loads(raw)
 projected=source
 for part in mapping['pointer']:projected=projected[part]
 assert isinstance(projected,str) and sha(projected.encode())==row['current_projected_sha256']
 if mapping['pointer']==['qr_envelope']:
  assert projected.startswith('nsealr1:');encoded=projected.split(':',1)[1]
 elif mapping['pointer']==['frame']:
  assert projected.startswith('nsealr1f:request:');encoded=projected.split(':')[2]
 else:encoded=projected
 decoded=base64.urlsafe_b64decode(encoded+'='*((-len(encoded))%4));request=json.loads(decoded)
 assert request['version']==1 and request['method']=='sign_event'
 assert row['potential_wire_status_cutover_collision'] is False and 'T01_semantic_transition' not in row
 observations.append(dict(mapping=mapping,source_commit=B,source_path=path,source_sha256=sha(raw),projected_bytes=len(projected.encode()),projected_sha256=sha(projected.encode()),encoded_payload=encoded,decoded_request=request,classification=row['required_disposition'],collision_flag=False))
assert len(observations)==3
result=dict(candidate=C,scope='Exact primary fixture decoding; no predicted future runtime result is labelled an executed failure',finding='T01-SPEC-CURRENT-01',observations=observations)
(OUT/'finding-reproduction.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(candidate=C,controls=len(observations),all_decoded_device_versions=[x['decoded_request']['version'] for x in observations],all_current_collision_flags=[x['collision_flag'] for x in observations]),sort_keys=True))
