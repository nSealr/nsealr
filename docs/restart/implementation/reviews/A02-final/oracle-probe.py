"""Execute the unchanged independent Pi/libsecp oracle against public fixtures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
PRODUCT=HERE/'replay/initial-import/repository'
p=PRODUCT/'apps/pi/app/nsealr_vault/crypto.py'
spec=importlib.util.spec_from_file_location('independent_review_pi_crypto',p);crypto=importlib.util.module_from_spec(spec);spec.loader.exec_module(crypto)
artifact=PRODUCT/'protocols/contracts/v1'
key=json.loads((artifact/'vectors/keys/test-key-1.json').read_bytes())
rows=[]
for name in ['kind-1-basic','kind-1-tags']:
 vector=json.loads((artifact/f'vectors/events/{name}.json').read_bytes())
 event=vector['signed_event']
 assert crypto.canonical_event_serialization(event)==vector['canonical_serialization']
 assert crypto.event_id(event)==vector['event_id']
 assert crypto.verify_schnorr_signature(event['pubkey'],event['id'],event['sig'])
 signed=crypto.sign_event(vector['event_template'],key['secret_key'])
 assert signed['id']==vector['event_id'] and signed['pubkey']==key['public_key']
 assert crypto.verify_schnorr_signature(signed['pubkey'],signed['id'],signed['sig'])
 changed=dict(event,content=event['content']+' purpose-written mutation')
 assert crypto.event_id(changed)!=event['id']
 assert not crypto.verify_schnorr_signature(event['pubkey'],crypto.event_id(changed),event['sig'])
 rows.append({'fixture':name,'independent_serialization_id_pubkey_and_schnorr_checked':True,'changed_event_signature_rejected':True})
result={'python_executable':sys.executable,'python_sha256':hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),'crypto_path':p.relative_to(PRODUCT).as_posix(),'crypto_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'cases':rows,'scope':'Public fixture identities only; no production-key or physical/device approval claim.'}
(HERE/'oracle-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
