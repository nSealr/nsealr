import base64, hashlib, json
from pathlib import Path
from unittest.mock import patch
from nsealr_vault.qr import decode_qr_envelope, decode_animated_qr_envelope_frames
from nsealr_vault.signer import sign_request

def framing(raw):
 payload=base64.urlsafe_b64encode(raw).decode().rstrip('=');digest=hashlib.sha256(raw).hexdigest()
 chunks=[payload[i:i+256] for i in range(0,len(payload),256)];frames=[]
 for i,chunk in enumerate(chunks,1):
  text=f'nsealr1a:{digest}:{i}/{len(chunks)}:{chunk}'
  frames.append(text+':'+hashlib.sha256(text.encode()).hexdigest()[:16])
 return 'nsealr1:'+payload,frames
rows=[]
def reject(name,raw,which=('static','animated')):
 static,animated=framing(raw)
 for transport,decoder,value in [('static',decode_qr_envelope,static),('animated',decode_animated_qr_envelope_frames,animated)]:
  if transport not in which:continue
  invoked=False
  try:
   request=decoder(value);invoked=True
   raise AssertionError('Original bytes unexpectedly reached signer boundary')
  except ValueError as exc:
   rows.append({'case':name,'transport':transport,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'result':'REJECTED_BEFORE_SIGNER','reason':str(exc),'signer_invoked':invoked})
original=json.loads(Path('docs/restart/implementation/T01/integration/pi-consumer/raw-ingress-gap/observation.json').read_text())
for row in original['rows']:
 assert row['actual_reference_response_ok'] is True
 reject(row['case'],row['original_json'].encode())
valid=b'{"version":2,"request_id":"root-ingress","method":"get_capabilities"}'
reject('BOM',b'\xef\xbb\xbf'+valid)
reject('escaped-duplicate-version',valid.replace(b'"version":2',b'"version":2,"\\u0076ersion":2'))
reject('trailing-document',valid+b'{}')
deep_raw=b'['*2047+b'0'+b']'*2047
deep_decoded=decode_animated_qr_envelope_frames(framing(deep_raw)[1]);assert isinstance(deep_decoded,list)
with patch('nsealr_vault.signer.sign_event') as signer,patch('nsealr_vault.signer.xonly_pubkey_from_secret') as key:
 response=sign_request(deep_decoded,'not-a-key',approved=True)
 assert response['ok'] is False and response['error']['code']=='invalid_request'
 signer.assert_not_called();key.assert_not_called()
rows.append({'case':'deep-valid-JSON-nonobject-signing-refusal','transport':'animated','bytes':len(deep_raw),'result':'invalid_request','crypto_and_key_invocations':0})
reject('static-cap-plus-one',valid+b' '*(705-len(valid)),('static',))
reject('animated-cap-plus-one',valid+b' '*(4097-len(valid)),('animated',))
for transport,cap,decoder,index in [('static',704,decode_qr_envelope,0),('animated',4096,decode_animated_qr_envelope_frames,1)]:
 raw=valid+b' '*(cap-len(valid));actual=decoder(framing(raw)[index]);assert actual==json.loads(valid)
 with patch('nsealr_vault.signer.sign_event') as signer,patch('nsealr_vault.signer.xonly_pubkey_from_secret') as key:
  response=sign_request(actual,'not-a-key',approved=False)
  assert response['ok'] is True and response['result']['capabilities']['profile']=='pi_qr'
  signer.assert_not_called();key.assert_not_called()
 rows.append({'case':'exact-original-byte-cap','transport':transport,'bytes':cap,'result':'PRESERVED_AND_DISCOVERY_WITHOUT_KEY'})
for method in ('unknown',[],{}):
 with patch('nsealr_vault.signer.sign_event') as signer,patch('nsealr_vault.signer.xonly_pubkey_from_secret') as key:
  response=sign_request({'version':2,'request_id':'root-method','method':method},'not-a-key',approved=False)
  assert response['ok'] is False and response['error']['code']==('unsupported_method' if isinstance(method,str) else 'invalid_request')
  signer.assert_not_called();key.assert_not_called()
 rows.append({'case':'closed-malformed-method','method':method,'result':response['error']['code']})
for kind in (4,13,14,1059,10050,22242):
 request={'version':2,'request_id':'root-offline','method':'sign_event','params':{'event_template':{'created_at':0,'kind':kind,'tags':[],'content':''}}}
 with patch('nsealr_vault.signer.sign_event') as signer,patch('nsealr_vault.signer.xonly_pubkey_from_secret') as key:
  response=sign_request(request,'not-a-key',approved=True)
  assert response['ok'] is False and response['error']['code']=='invalid_request'
  signer.assert_not_called();key.assert_not_called()
 rows.append({'case':'offline-workflow-refusal','kind':kind,'result':response['error']['code']})
assert len(rows)==26
print(json.dumps({'candidate':'793b4d4e800f3e18c1a625b074c0293dc5d974ab','observations':len(rows),'status':'PASS_SCOPED_CONTROLS','rows':rows},indent=2))
