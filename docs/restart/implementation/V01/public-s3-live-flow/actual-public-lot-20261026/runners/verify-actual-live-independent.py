from pathlib import Path
import json,hashlib,importlib.util
p=Path(__file__).resolve().parent
source=Path("/home/tux/nsealr/firmware/docs/restart/implementation/S03/oracle.py")
assert hashlib.sha256(source.read_bytes()).hexdigest()=="f69bd3446fd4dce92106d29a0dfb13bf9fbdf447cbfdcae1b2dcf9e6c0f1cda5"
spec=importlib.util.spec_from_file_location("independent_s03",source); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
saved=json.loads((p/"physical-approve-120/result.json").read_text());request=saved["request"];response=saved["response"];event=response["result"]["event"]
expected="f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9"
assert response["request_id"]==request["request_id"] and response["ok"] is True and event["pubkey"]==expected
assert request["params"]["event_template"]=={"kind":1,"created_at":1710000000,"content":"S3 public physical approval","tags":[]}
for field,value in request["params"]["event_template"].items():assert event[field]==value
value=mod.template(json.dumps(request["params"]["event_template"],ensure_ascii=False,separators=(",",":")).encode())
digest=hashlib.sha256(mod.canonical(value,expected)).digest();assert digest.hex()==event["id"]
assert mod.reference().schnorr_verify(digest,bytes.fromhex(expected),bytes.fromhex(event["sig"]))
print(json.dumps({"independent_BIP340":True,"expected_public_key":expected,"event_id":event["id"],"oracle_wrapper_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"upstream_reference":"hash verified internally by existing oracle.reference()","scope":"Actual live result, separately wire-matched by product decoder; independent BIP340, no deterministic golden-byte comparison"}))
