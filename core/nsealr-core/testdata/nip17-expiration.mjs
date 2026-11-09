// Independent public-fixture NIP44/NIP01/BIP340 construction; no Rust outputs.
// Usage: node nip17-expiration.mjs NODE_MODULES OUTPUT_JSON
import assert from 'node:assert/strict';
import {createHash, createHmac} from 'node:crypto';
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
import {writeFileSync} from 'node:fs';
const req = createRequire(resolve(process.argv[2], 'package.json'));
const {nip44, getPublicKey, verifyEvent} = req('nostr-tools');
const {schnorr} = createRequire(req.resolve('nostr-tools'))('@noble/curves/secp256k1.js');
const keys = [16,17,18].map(n => {const key = new Uint8Array(32); key[31] = n; return key;});
const pubs = keys.map(getPublicKey), rows = [];
const id = e => createHash('sha256').update(JSON.stringify([0,e.pubkey,e.created_at,e.kind,e.tags,e.content])).digest('hex');
function sign(e, key) {
  e = {...e, pubkey:getPublicKey(key)}; e.id = id(e);
  e.sig = Buffer.from(schnorr.sign(Buffer.from(e.id,'hex'), key, new Uint8Array(32))).toString('hex');
  assert(verifyEvent(JSON.parse(JSON.stringify(e)))); return e;
}
let sequence = 0;
function encrypt(text, key) {
  const nonce = createHmac('sha256','nsealr public expiration fixture').update(String(sequence++)).digest();
  return nip44.v2.encrypt(text, nip44.v2.utils.getConversationKey(key,pubs[1]), nonce);
}
const forms = [
  ['missing', [['expiration']]], ['empty', [['expiration','']]],
  ['expired', [['expiration','0']]], ['future', [['expiration','9999999999']]],
  ['not-number', [['expiration','tomorrow']]], ['negative', [['expiration','-1']]],
  ['duplicate', [['expiration','0'],['expiration','9999999999']]],
  ['extra-field', [['expiration','0','extra']]],
  ['escaped-name', [['expiration','0']]],
];
function row(layer, label, tags) {
  const rumor = {pubkey:pubs[0],created_at:1730000000,kind:14,tags:[['p',pubs[1]],...(layer==='rumor'?tags:[])],content:'Private public-fixture text'};
  rumor.id=id(rumor);
  let rumorText=JSON.stringify(rumor);
  if(layer==='rumor'&&label==='escaped-name')rumorText=rumorText.replace('"expiration"','"\\u0065xpiration"');
  const seal=sign({created_at:1729900000,kind:13,tags:layer==='seal'?tags:[],content:encrypt(rumorText,keys[0])},keys[0]);
  let sealText=JSON.stringify(seal);
  if(layer==='seal'&&label==='escaped-name')sealText=sealText.replace('"expiration"','"\\u0065xpiration"');
  const wrap=sign({created_at:1729890000,kind:1059,tags:[['p',pubs[1]],...(layer==='outer'?tags:[])],content:encrypt(sealText,keys[2])},keys[2]);
  let raw=JSON.stringify(wrap);
  if(layer==='outer'&&label==='escaped-name')raw=raw.replace('"expiration"','"\\u0065xpiration"');
  assert(verifyEvent(JSON.parse(raw)));
  const decodedSeal=JSON.parse(nip44.v2.decrypt(wrap.content,nip44.v2.utils.getConversationKey(keys[1],pubs[2])));
  assert(verifyEvent(decodedSeal));
  const decodedRumor=JSON.parse(nip44.v2.decrypt(decodedSeal.content,nip44.v2.utils.getConversationKey(keys[1],pubs[0])));
  assert.equal(id(decodedRumor),decodedRumor.id);assert.deepEqual(decodedRumor,rumor);
  rows.push({name:`${layer}-${label}`,accept:layer==='none',local_secret:Buffer.from(keys[1]).toString('hex'),gift_wrap:raw});
}
row('none','unexpired-control',[]);
for(const layer of ['outer','rumor','seal'])for(const [label,tags] of forms)row(layer,label,tags);
writeFileSync(process.argv[3],JSON.stringify({public_fixture_only:true,oracle:'nostr-tools2.23.3 NIP44 + Noble deterministic BIP340 + Node canonical JSON/SHA256',policy:'All expiration identifiers unsupported until qualified complete time policy; malformed and future forms also refuse',cases:rows},null,2)+'\n');
console.log(JSON.stringify({cases:rows.length,accepts:rows.filter(x=>x.accept).length,refuses:rows.filter(x=>!x.accept).length}));
