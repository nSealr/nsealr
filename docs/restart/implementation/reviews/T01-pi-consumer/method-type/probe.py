import json
from unittest.mock import patch
from nsealr_vault.signer import sign_request
rows=[]
for method in ('unknown', [], {}):
 with patch('nsealr_vault.signer.sign_event') as signer, patch('nsealr_vault.signer.xonly_pubkey_from_secret') as key:
  try:
   response=sign_request({'version':2,'request_id':'review-method-type','method':method},'not-a-key',approved=False)
   row={'method':method,'response':response,'closed_error':response.get('ok') is False}
  except Exception as exc:
   row={'method':method,'exception':type(exc).__name__,'message':str(exc),'closed_error':False}
  row['signer_called']=signer.called;row['key_called']=key.called;rows.append(row)
print(json.dumps({'rows':rows,'all_closed_errors':all(r['closed_error'] and not r['signer_called'] and not r['key_called'] for r in rows)},indent=2))
raise SystemExit(0 if all(r['closed_error'] and not r['signer_called'] and not r['key_called'] for r in rows) else 1)
