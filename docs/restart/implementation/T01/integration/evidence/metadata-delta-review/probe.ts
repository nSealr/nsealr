// Independent focused reading probes for metadata delta24b0b58a, not a product validator.
import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import {
  compactReportedCapabilities, parseImplementationProfile, parseLimitsManifest,
  parseReportedCapabilities, readBoundedJson, resolveReportedCapabilities,
  requireMessageFeature, intersectMethodLimits, type FullCapabilities
} from "../../../../../packages/protocol/src/capabilities.ts";

const load = (path: string) => JSON.parse(readFileSync(path, "utf8"));
const artifact = "protocols/contracts/v1/";
const cases = load(artifact + "vectors/profile-capabilities/cases-v1.json");
const local = parseImplementationProfile(load(artifact + cases.implementation_examples.pi_qr));
const full = (): FullCapabilities => {
  const { conformance_only: _, ...fields } = structuredClone(local);
  return { ...fields, format: "nsealr.capabilities.v1", form: "full" };
};
const rows: { id: string; result: string; reason?: string }[] = [];
const rejects = (id: string, operation: () => unknown) => {
  let caught: unknown;
  try { operation(); } catch (error) { caught = error; }
  assert(caught instanceof Error, `${id} unexpectedly accepted`);
  rows.push({ id, result: "REJECTED", reason: caught.message });
};
const accepts = (id: string, operation: () => unknown) => {
  operation(); rows.push({ id, result: "ACCEPTED_CONTROL" });
};

// Original-byte grammar is tested before object construction, including escaped aliases.
const original = JSON.stringify(full());
rejects("decoded-key-alias", () => parseReportedCapabilities(original.replace('"profile":"pi_qr"', '"profile":"pi_qr","\\u0070rofile":"pi_qr"')));
rejects("duplicate-nested-key", () => parseReportedCapabilities(original.replace('"name":', '"name":"prior","name":')));
for (const [id, raw] of [
  ["lone-high-surrogate", '{"x":"\\ud800"}'],
  ["lone-low-surrogate", '{"x":"\\udc00"}'],
  ["escaped-raw-control", '{"x":"\u0001"}'],
  ["number-exponent", '{"x":1e0}'],
  ["number-decimal", '{"x":1.0}'],
  ["number-negative-zero", '{"x":-0}'],
  ["number-unsafe", '{"x":9007199254740992}'],
  ["trailing-comma", '{"x":1,}'],
  ["non-rfc-whitespace", '{"x":1}\u00a0'],
  ["appended-object", '{}{}']
] as const) rejects(id, () => readBoundedJson(raw));
rejects("overlong-utf8", () => readBoundedJson(Uint8Array.from([0x22, 0xc0, 0xaf, 0x22])));
accepts("rfc-whitespace-and-surrogate-pair", () => assert.deepEqual(readBoundedJson(' \r\n\t{"x":"\\ud83d\\ude00"} '), { x: "😀" }));
accepts("utf8-label-exact128", () => {
  const value = full(); value.device.name = "😀".repeat(32);
  assert.equal(parseReportedCapabilities(JSON.stringify(value)).form, "full");
});
rejects("utf8-label129", () => {
  const value = full(); value.device.name = "😀".repeat(32) + "a";
  return parseReportedCapabilities(JSON.stringify(value));
});

// These mutable reports can never replace the caller's exact static manifest.
for (const [id, mutate] of [
  ["operation-catalog-substitution", (v: FullCapabilities) => { v.methods[1].operation_id = "nostr.blind-sign.v1"; }],
  ["algorithm-substitution", (v: FullCapabilities) => { v.methods[1].algorithm_ids = ["nip44.v2"]; }],
  ["execution-substitution", (v: FullCapabilities) => { v.methods[1].execution_location = "se"; }],
  ["custody-substitution", (v: FullCapabilities) => { v.custody.mode = "mcu_wrapped_persistent"; }],
  ["required-se-substitution", (v: FullCapabilities) => { v.secure_element = { state: "required", configuration_id: "different" }; }],
  ["limits-id-substitution", (v: FullCapabilities) => { v.limits_id = "unbounded"; }]
] as const) rejects(id, () => { const v = full(); mutate(v); return resolveReportedCapabilities(v, local); });
rejects("wire-local-verification-field", () => {
  const v = full(); Object.assign(v.messages.nip44_v2_primitive, { verified: true });
  return parseReportedCapabilities(JSON.stringify(v));
});
accepts("resolution-clones-report", () => {
  const v = full(); const resolved = resolveReportedCapabilities(v, local);
  resolved.device.name = "mutated caller output";
  assert.notEqual(v.device.name, resolved.device.name);
  assert.notEqual(local.device.name, resolved.device.name);
});
accepts("method-reordering-preserves-semantics", () => {
  const v = full(); v.methods.reverse();
  assert.deepEqual(resolveReportedCapabilities(v, local), v);
});
rejects("reference-cannot-introduce-method", () => {
  const reference = compactReportedCapabilities(full(), local, 704);
  reference.runtime.push({ method_id: "nip44_encrypt", configuration: "configured", availability: "available", reason: null });
  return resolveReportedCapabilities(reference, local);
});
rejects("reference-cannot-carry-authority", () => {
  const reference = compactReportedCapabilities(full(), local, 704);
  return parseReportedCapabilities(JSON.stringify({ ...reference, approved: true }));
});

// Both multiplicative and additive overflow fail before an allocator/write exists here.
rejects("retained-capacity-below-pending", () => {
  const limits = structuredClone(cases.limits_manifest);
  limits.methods[0].retained_bytes = 703;
  return parseLimitsManifest(limits);
});
rejects("retained-sum-overflow", () => {
  const limits = structuredClone(cases.limits_manifest);
  Object.assign(limits.methods[0], { request_json_bytes: Number.MAX_SAFE_INTEGER, response_json_bytes: 1, retained_bytes: Number.MAX_SAFE_INTEGER, queued_operations: 1 });
  return parseLimitsManifest(limits);
});
rejects("transport-retention-overflow", () => {
  const limits = structuredClone(cases.limits_manifest);
  Object.assign(limits.transports[0], { reassembly_bytes: Number.MAX_SAFE_INTEGER, retained_bytes: Number.MAX_SAFE_INTEGER, queued_frames: 1 });
  return parseLimitsManifest(limits);
});
rejects("message-dimensions-on-sign-event", () => {
  const limits = structuredClone(cases.limits_manifest);
  limits.methods[2].plaintext_bytes = 1;
  return parseLimitsManifest(limits);
});
rejects("primitive-does-not-admit-workflow", () => {
  const messages = full().messages;
  Object.assign(messages.nip44_v2_primitive, { support: "supported", configuration: "configured", availability: "available", reason: null });
  return requireMessageFeature(messages, "nip17_59_one_to_one_text_v1", "a.named.workflow");
});
// Additional controls for the actual refactor and direct limits intersection.
const baselineControls = rows.length;
for (const [id, raw] of [
  ["utf8-bom", Uint8Array.from([0xef, 0xbb, 0xbf, 0x7b, 0x7d])],
  ["string-bom", "\ufeff{}"],
  ["alias-inside-array", '[{"x":1,"\\u0078":2}]'],
  ["unicode-key-invalid", '{"\\ud800":0}'],
  ["json-infinity", '{"x":Infinity}'],
  ["json-nan", '{"x":NaN}'],
  ["leading-zero", '{"x":01}'],
  ["negative-integer", '{"x":-1}'],
  ["invalid-escape", '{"x":"\\v"}'],
  ["members33", JSON.stringify(Object.fromEntries(Array.from({length:33},(_,i)=>[`k${i}`,i])))],
  ["utf8-key129", JSON.stringify({["😀".repeat(32)+"x"]:0})],
  ["depth9", "[".repeat(9)+"0"+"]".repeat(9)],
  ["bytes8193", " ".repeat(8191)+"{}"]
] as const) rejects(id, () => readBoundedJson(raw));
accepts("members32", () => assert.equal(Object.keys(readBoundedJson(JSON.stringify(Object.fromEntries(Array.from({length:32},(_,i)=>[`k${i}`,i])))) as object).length,32));
accepts("utf8-key128", () => assert.deepEqual(readBoundedJson(JSON.stringify({["😀".repeat(32)]:0})),{["😀".repeat(32)]:0}));
accepts("depth8", () => assert.deepEqual(readBoundedJson("[".repeat(8)+"0"+"]".repeat(8)),[[[[[[[[0]]]]]]]]));
accepts("bytes8192", () => assert.deepEqual(readBoundedJson(" ".repeat(8190)+"{}"),{}));
accepts("nested-strings-delimiters-and-literals", () => {
  const value={a:[{b:'comma, colon: brace} bracket] quote" slash\\',c:[true,false,null,0,Number.MAX_SAFE_INTEGER]}],d:"é😀"};
  assert.deepEqual(readBoundedJson(JSON.stringify(value)),value);
});
for (const [id,bytes,depth] of [["byte-bound-zero",0,8],["byte-bound-over",8193,8],["byte-bound-fraction",1.5,8],["depth-bound-zero",8192,0],["depth-bound-over",8192,9],["depth-bound-fraction",8192,1.5]] as const) {
  rejects(id,()=>readBoundedJson("{}",bytes,depth));
}
rejects("raw-input-nonbytes",()=>readBoundedJson({byteLength:0} as any));
const localLimits=parseLimitsManifest(cases.limits_manifest).methods.find(m=>m.method_id==="sign_event")!;
const peerLimits={...localLimits,content_utf8_bytes:256,deadline_ms:50};
for (const [id,which,change] of [
  ["local-retention-invalid","local",{retained_bytes:1}],
  ["peer-retention-invalid","peer",{retained_bytes:1}],
  ["local-negative-budget","local",{request_json_bytes:-1}],
  ["peer-overflow","peer",{request_json_bytes:Number.MAX_SAFE_INTEGER,pending_requests:2,retained_bytes:Number.MAX_SAFE_INTEGER}],
  ["peer-method-scope-mismatch","peer",{method_id:"get_public_key"}],
  ["local-missing-budget","local",{deadline_ms:undefined}]
] as const) rejects(id,()=>intersectMethodLimits(which==="local"?{...localLimits,...change} as any:localLimits,which==="peer"?{...peerLimits,...change} as any:peerLimits));
rejects("both-foreign-dimension",()=>intersectMethodLimits({...localLimits,foreign_unit:1} as any,{...peerLimits,foreign_unit:1} as any));
accepts("valid-intersection-bounds-and-clone",()=>{
  const before=JSON.stringify([localLimits,peerLimits]);
  const value=intersectMethodLimits(localLimits,peerLimits);
  for(const [key,number] of Object.entries(value))if(typeof number==="number")assert(number<=Number((localLimits as any)[key])&&number<=Number((peerLimits as any)[key]));
  assert.notEqual(value,localLimits);assert.notEqual(value,peerLimits);
  assert.equal(JSON.stringify([localLimits,peerLimits]),before);
  assert.equal(value.queued_operations,0);assert.equal(value.cached_responses,0);
});
const output = { candidate: "24b0b58a6ee085d8176a801a7bad5595d39965b7", scope: "Metadata helper execution only; no transport/signing/consent or final T01 verdict", count: rows.length, baseline_controls: baselineControls, delta_controls: rows.length-baselineControls, rows };
writeFileSync(new URL("./probe-result.json", import.meta.url), JSON.stringify(output, null, 2) + "\n");
console.log(JSON.stringify({ candidate: output.candidate, count: rows.length, expected_rejections: rows.filter(r => r.result === "REJECTED").length, positive_controls: rows.filter(r => r.result === "ACCEPTED_CONTROL").length, status: "PASS_COMPONENT_PROBES_ONLY" }));
