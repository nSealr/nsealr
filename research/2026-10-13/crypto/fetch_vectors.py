#!/usr/bin/env python3
"""Fetch exact external NIP44 test data; never follows a moving branch."""
import hashlib,json,pathlib,urllib.request
root=pathlib.Path(__file__).resolve().parent
bip=root/'sources/bitcoin/bips/bip-0340/test-vectors.csv'
if hashlib.sha256(bip.read_bytes()).hexdigest()!='34c9d1d9c3a88d524bc80778540dc43f8306ec249a7485293063c376db851c2d': raise SystemExit('BIP340 fixture checksum mismatch')
url='https://raw.githubusercontent.com/paulmillr/nip44/671a1f04bcfacaf125b0db68adc45bc9ce0e763b/nip44.vectors.json'
expected='269ed0f69e4c192512cc779e78c555090cebc7c785b609e338a62afc3ce25040'
path=root/'sources/paulmillr/nip44/nip44.vectors.json'
if path.exists():
 data=path.read_bytes()
else:
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'nsealr-public-crypto-probe'}),timeout=30) as response: data=response.read()
if hashlib.sha256(data).hexdigest()!=expected: raise SystemExit('NIP44 fixture checksum mismatch')
path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
x=json.loads(data)['v2']
a='// Generated from hash-verified public test vectors; do not commit this generated file.\n'
a+='const NIP44_VALID: &[(&str,&str,&str)] = &[\n'+''.join('('+','.join(json.dumps(v[k]) for k in ('sec1','pub2','conversation_key'))+'),\n' for v in x['valid']['get_conversation_key'])+'];\n'
a+='const NIP44_INVALID: &[(&str,&str)] = &[\n'+''.join('('+','.join(json.dumps(v[k]) for k in ('sec1','pub2'))+'),\n' for v in x['invalid']['get_conversation_key'])+'];\n'
(root/'tests/nip44_data.rs').write_text(a)
print('NIP44 fixture SHA256 verified; generated 35 valid and 8 invalid conversation-key cases')
