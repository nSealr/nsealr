#!/usr/bin/env node
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";
import { build } from "esbuild";
import {
  assertCompanionPackageRegistry, assertPublicPackageTarball, packageFilename,
  packageManagerCommand, publicPackages, root, run, sourceManifest
} from "./package_set.mjs";

assertCompanionPackageRegistry();
assert.deepEqual(publicPackages, ["@nsealr/sdk"]);
const packageManager = packageManagerCommand();
const packDir = mkdtempSync(join(tmpdir(), "nsealr-sdk-pack-"));
const consumerDir = mkdtempSync(join(tmpdir(), "nsealr-sdk-consumer-"));
const manifest = sourceManifest("@nsealr/sdk");
run(packageManager.command, [...packageManager.prefixArgs, "--filter", "@nsealr/sdk", "pack", "--pack-destination", packDir], { env: packageManager.env });
const tarball = join(packDir, packageFilename(manifest));
assertPublicPackageTarball("@nsealr/sdk", tarball, manifest);
assert(Object.keys(manifest.dependencies).every((name) => !name.startsWith("@nsealr/")), "tarball must not need unpublished packages");
writeFileSync(join(consumerDir, "package.json"), JSON.stringify({name:"isolated-sdk-consumer",version:"0.0.0",private:true,type:"module",dependencies:{"@nsealr/sdk":`file:${tarball}`}},null,2));
run("npm", ["install", "--ignore-scripts", "--no-audit", "--fund=false"], { cwd:consumerDir,env:process.env });
const artifact = join(root,"protocols/contracts/v1");
for (const name of ["request-kind-1-basic", "response-kind-1-basic"]) {
  writeFileSync(join(consumerDir, `${name}.json`), readFileSync(join(artifact,`examples/${name}.json`)));
}
writeFileSync(join(consumerDir,"node.mjs"), `
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import * as root from "@nsealr/sdk";
import * as browser from "@nsealr/sdk/browser";
import * as node from "@nsealr/sdk/node";
const request=JSON.parse(readFileSync(new URL("request-kind-1-basic.json",import.meta.url)));
const response=JSON.parse(readFileSync(new URL("response-kind-1-basic.json",import.meta.url)));
for (const sdk of [root,browser,node]) {
  assert.equal(sdk.protocol.validateRequest(request).ok,true);
  assert.equal(sdk.core.computeEventId(response.result.event),response.result.event.id);
  assert.equal(sdk.core.verifySignedEventResponse(request,response).ok,true);
  assert.deepEqual(sdk.qr.decodeQrEnvelope(sdk.qr.encodeQrEnvelope(request)),request);
  assert.equal("smartcard" in sdk,false);
  assert.equal("devSignRequest" in sdk,false);
}
assert.equal(typeof node.client.parseLocalGrantStore,"function");
assert.equal(typeof node.nip46.decideNip46BridgeAction,"function");
assert.equal("parseLocalGrantStore" in root.client,false);
assert.equal("parseLocalGrantStore" in browser.client,false);
await assert.rejects(import("@nsealr/core"),{code:"ERR_MODULE_NOT_FOUND"});
await assert.rejects(import("@nsealr/sdk/dist/internal/core/index.js"),{code:"ERR_PACKAGE_PATH_NOT_EXPORTED"});
console.log("isolated packed root/browser/Node behavior and hidden-import negatives passed");
`);
run("node",["node.mjs"],{cwd:consumerDir});
writeFileSync(join(consumerDir,"browser-entry.mjs"), `
import * as sdk from "@nsealr/sdk/browser";
import request from "./request-kind-1-basic.json";
import response from "./response-kind-1-basic.json";
const provider=sdk.browserProvider.createNip07Provider({
 client:{surface:"browser_extension",origin:"https://example.com",app_name:"Packed SDK",instance_id:"packed-sdk"},
 backend:{getPublicKey:async()=>response.result.event.pubkey,signEventRequest:async()=>response},
 nextRequestId:()=>request.request_id
});
globalThis.packedSdkResult=(async()=>({
 pubkey:await provider.getPublicKey(),event:await provider.signEvent(request.params.event_template),
 valid:sdk.core.verifySignedEventResponse(request,response).ok
}))();
`);
const bundle = await build({absWorkingDir:consumerDir,entryPoints:["browser-entry.mjs"],bundle:true,format:"iife",platform:"browser",target:"es2022",write:false,metafile:true});
assert(!Object.values(bundle.metafile.outputs).some((output)=>output.imports.some((item)=>item.external)),"browser consumer bundle has no unresolved external imports");
writeFileSync(join(consumerDir,"browser-bundle.js"),bundle.outputFiles[0].text);
writeFileSync(join(consumerDir,"browser-run.mjs"),`
import assert from "node:assert/strict";
import vm from "node:vm";
import {readFileSync} from "node:fs";
import {webcrypto} from "node:crypto";
const context=vm.createContext({TextEncoder,TextDecoder,Uint8Array,ArrayBuffer,AbortController,crypto:webcrypto,setTimeout,clearTimeout,console});
vm.runInContext(readFileSync("browser-bundle.js","utf8"),context);
const result=await context.packedSdkResult;
const expected=JSON.parse(readFileSync("response-kind-1-basic.json","utf8")).result.event;
assert.equal(result.valid,true);assert.equal(result.pubkey,expected.pubkey);assert.equal(result.event.id,expected.id);
console.log("packed browser bundle executes without Node module globals; real browser qualification remains separate");
`);
run("node",["browser-run.mjs"],{cwd:consumerDir});
writeFileSync(join(consumerDir,"consumer.ts"),`
import * as sdk from "@nsealr/sdk";
import * as browser from "@nsealr/sdk/browser";
import * as node from "@nsealr/sdk/node";
const identity:sdk.client.LocalClientIdentity={surface:"browser_extension",origin:"https://example.com",app_name:"Types"};
const request: sdk.core.SignEventRequest={version:1,request_id:"types",method:"sign_event",params:{event_template:{created_at:1,kind:1,tags:[],content:"types"}}};
const provider:browser.browserProvider.Nip07Provider=browser.browserProvider.createNip07Provider({client:identity,backend:{getPublicKey:async()=>"1".repeat(64),signEventRequest:async()=>{throw new Error("no signer");}},nextRequestId:()=>request.request_id});
void provider;void node.client.parseLocalGrantStore;void node.nip46.decideNip46BridgeAction;
`);
const tsc=join(root,"node_modules/typescript/bin/tsc");
run("node",[tsc,"--ignoreConfig","--strict","--target","ES2022","--module","NodeNext","--moduleResolution","NodeNext","--noEmit","consumer.ts"],{cwd:consumerDir});
console.log("single packed SDK runtime/browser/type acceptance passed");
