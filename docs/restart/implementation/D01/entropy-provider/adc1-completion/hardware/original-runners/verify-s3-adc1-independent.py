from pathlib import Path
import json,hashlib,importlib.util
p=Path(__file__).resolve().parent
r=p.parent
source=Path("/home/tux/nsealr/firmware/docs/restart/implementation/S03/oracle.py")
spec=importlib.util.spec_from_file_location("independent_s03",source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
request=json.loads((r/"s3-probe/artifacts/entropy-adc1-completion/request.json").read_text());response=json.loads((p/"s3-adc1-actual-response.json").read_text());event=response["result"]["event"]
expected="f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9"
assert response["request_id"]==request["request_id"] and response["ok"] is True and event["pubkey"]==expected
for field,value in request["params"]["event_template"].items():assert event[field]==value
value=mod.template(json.dumps(request["params"]["event_template"],ensure_ascii=False,separators=(",",":")).encode())
digest=hashlib.sha256(mod.canonical(value,expected)).digest();assert digest.hex()==event["id"]
assert mod.reference().schnorr_verify(digest,bytes.fromhex(expected),bytes.fromhex(event["sig"]))
print(json.dumps({"independent_BIP340":True,"expected_identity":expected,"event_id":event["id"],"oracle_wrapper":str(source),"oracle_wrapper_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"signature_verification":"Actual random-aux signature verified; old deterministic golden-byte equality is not applicable"}))
