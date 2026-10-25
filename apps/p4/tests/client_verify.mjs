// Uses unchanged product client/QR/core source. No external-client admission.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {handleLocalServiceRequest,clientIdForIdentity} from "../../../packages/client/src/service.ts";
import {decodeQrEnvelope,encodeQrEnvelope} from "../../../packages/qr/src/qr.ts";
const request=JSON.parse(readFileSync(process.argv[2],"utf8"));
const frame=readFileSync(process.argv[3],"utf8");
const response=decodeQrEnvelope(frame);
const expected="4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";
assert.equal(response.result.event.pubkey,expected);
const client={surface:"cli",origin:"cli:p4-public-test",instance_id:"p4-optical"};
const grants=[{client_id:clientIdForIdentity(client),origin:client.origin,surface:client.surface,allowed_operations:["verify_signer_response"]}];
function verify(candidate) {
 const result=handleLocalServiceRequest({version:1,request_id:"p4-client-verification",operation:"verify_signer_response",params:{client,request,response:candidate}},{grants});
 assert.equal(result.ok,true);return result.result.validation.valid;
}
assert.equal(verify(response),true);
const cases=[];
for(const kind of ["correlation","template","event-id","signature"]) {
 const changed=structuredClone(response);
 if(kind==="correlation")changed.request_id+=".wrong";
 if(kind==="template")changed.result.event.content+=" tampered";
 if(kind==="event-id")changed.result.event.id="0".repeat(64);
 if(kind==="signature")changed.result.event.sig=(changed.result.event.sig[0]==="0"?"1":"0")+changed.result.event.sig.slice(1);
 assert.equal(verify(changed),false);cases.push(kind);
}
assert.deepEqual(decodeQrEnvelope(encodeQrEnvelope(request)),request);
console.log(JSON.stringify({scope:"unchanged actual product QR/client/core verifier; host public fixture only",ok:true,response_frame_bytes:frame.length,expected_identity:expected,negative_refusals:cases,external_clients_qualified:0,physical_results:0},null,2));
