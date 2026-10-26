import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {decodeSerialFrame} from "../../client-account-binding/packages/framing/dist/index.js";
const raw=readFileSync(new URL("./operator-reject/actual-error.serial",import.meta.url),"utf8");
const request=decodeSerialFrame(readFileSync(new URL("./request.serial",import.meta.url),"utf8"));
assert.equal(request.type,"request");assert.equal(request.payload.request_id,"s3-local-reject-1");
const frame=decodeSerialFrame(raw);assert.equal(frame.type,"error");assert.deepEqual(frame.payload,{error:"rejected"});
console.log(JSON.stringify({request_id:request.payload.request_id,frame_type:frame.type,payload:frame.payload,signature_response_present:false}));
