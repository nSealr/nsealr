#!/usr/bin/env node
import assert from "node:assert/strict";
import {join} from "node:path";
import {checkProductionSource,checkFeatureClaims,checkFeatureData,checkCurrentOwnerLinks} from "./check_product_boundaries.mjs";
import {checkSourceText} from "./check_public_imports.mjs";
import {assertNoPrivatePackageReferences,root} from "./package_set.mjs";
const executed=[];
function check(identity, callback) {callback();executed.push(identity);console.log(`PASS ${identity}`);}
check("17279524b14390ef046f228aca1bca86cdb53bf1086206cdc9f390d4758de0dd",()=>{
 for (const text of ["function validateRequest(x) { return true; }","export const validateResponse = () => true;"]) assert.throws(()=>checkProductionSource("apps/bridge/service/src/mutation.ts",text),/different owner/u);
 checkProductionSource("apps/bridge/service/src/example.ts",'import {validateRequest} from "@nsealr/protocol"; validateRequest(input);');
 checkProductionSource("packages/protocol/src/protocol.ts","export function validateRequest(x) { return x; }");
});
const importCases=()=>{
 for (const text of ['import {devSignRequest} from "@nsealr/dev-signer";','export * from "@nsealr/dev-signer";','await import("@nsealr/dev-signer");']) assert.throws(()=>checkSourceText("@nsealr/sdk",join(root,"packages/sdk/src"),join(root,"packages/sdk/src/mutation.ts"),text),/non-public|test-only/u);
 assert.throws(()=>assertNoPrivatePackageReferences({dependencies:{"@nsealr/dev-signer":"0.1.0"}}),/private/u);
 checkSourceText("@nsealr/sdk",join(root,"packages/sdk/src"),join(root,"packages/sdk/src/positive.ts"),'export * from "@nsealr/protocol";');
 checkSourceText("@nsealr/dev-signer",join(root,"packages/dev-signer/src"),join(root,"packages/dev-signer/src/positive.ts"),'import {validateRequest} from "@nsealr/protocol";');
 assertNoPrivatePackageReferences({dependencies:{"nostr-tools":"2.23.3"}});
};
for(const id of ["22395efa9f7fff63f3c5a16df222bb3e1fb5db59d6a170ff8614cf66b0c9fe1e","5c005c269d5192537af02c9176bb32723fc32fcef71c0fe86cd3da7c831b1bfd"])check(id,importCases);
check("b9cee4b876e69c9af01cc704d96612e0c37037ed0ffd4cdca693f159d4e7fe34",()=>{
 for(const key of ["stores_production_secrets",'"stores_production_secrets"','["stores_production_secrets"]']) assert.throws(()=>checkProductionSource("apps/bridge/service/src/mutation.ts",`const state={${key}:true};`),/custody/u);
 checkProductionSource("apps/bridge/service/src/positive.ts","const state={stores_production_secrets:false,clientTransportSecret: new Uint8Array(32)};");
 checkProductionSource("apps/bridge/service/src/rejection.test.ts","const mutation={stores_production_secrets:true};");
});
check("6c1bc0ee0023c497e9030f98c0f04507fc23f98e6c1efb69dec1422f6af205f0",()=>{
 for(const url of ["https://github.com/nSealr/raspberry","https://github.com/nSealr/board-sdk/tree/main/apps/pi"])assert.throws(()=>checkCurrentOwnerLinks(url),/alias|owner/u);
 checkCurrentOwnerLinks("https://github.com/nSealr/nsealr/tree/main/apps/pi");
});
for(const id of ["592cff524db06bc8f42bb806609350cd0f87df15621236b9fccd9f2626a7ea08","cd29a3bff1f2024239a136fafc7112e671dbde856cb27716c7f4f72e571bce6d","f04c62a5f9ba82470e652915b34c879021182aa4b2a9143e4b78c398b614cf12"])check(id,()=>{
 assert.throws(()=>checkFeatureClaims("The stateless QR vault includes TROPIC01 key wrapping."),/cannot claim/u);
 for(const text of ["Rejection of stateless QR vault TROPIC01 usage.","The stateless QR vault must not add TROPIC01."]) checkFeatureClaims(text);
 const matrix={solutions:Object.fromEntries(["raspberry_qr_vault","esp32_qr_vault"].map(name=>[name,{features:{persistent_secret_custody:{current:"forbidden",target:"forbidden"}}}]))};
 checkFeatureData(matrix);matrix.solutions.raspberry_qr_vault.features.persistent_secret_custody.current="implemented";assert.throws(()=>checkFeatureData(matrix));
});
console.log(`${executed.length} admitted source/privacy/capability replacement obligations passed; recipe and CLI obligations are separate gates`);
