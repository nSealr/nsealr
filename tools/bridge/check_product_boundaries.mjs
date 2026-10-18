#!/usr/bin/env node
// Product-source claim and validator ownership checks complement runtime tests.
import assert from "node:assert/strict";
import {readFileSync, readdirSync} from "node:fs";
import {join, relative} from "node:path";
import {pathToFileURL} from "node:url";
import * as ts from "typescript";
import {root} from "./package_set.mjs";

export function checkProductionSource(path, text) {
  if (path.endsWith(".test.ts") || path.startsWith("packages/dev-signer/") || path.startsWith("packages/fixtures/")) return;
  const source = ts.createSourceFile(path,text,ts.ScriptTarget.Latest,true);
  const keyName = (node) => ts.isIdentifier(node) || ts.isStringLiteral(node) ? node.text :
    ts.isComputedPropertyName(node) && ts.isStringLiteral(node.expression) ? node.expression.text : undefined;
  function visit(node) {
    if ((ts.isFunctionDeclaration(node) || ts.isVariableDeclaration(node)) && node.name &&
        ["validateRequest","validateResponse"].includes(keyName(node.name))) {
      assert.equal(path,"packages/protocol/src/protocol.ts",`${path}: shared validator has a different owner`);
    }
    if (ts.isPropertyAssignment(node) && keyName(node.name)==="stores_production_secrets") {
      assert.equal(node.initializer.kind,ts.SyntaxKind.FalseKeyword,`${path}: production signing-secret custody claim is forbidden`);
    }
    ts.forEachChild(node,visit);
  }
  visit(source);
}
export function checkFeatureClaims(text) {
  for (const sentence of text.split(/[.\n]/u)) {
    if (/\bTROPIC01\b/iu.test(sentence) && /stateless|QR\s+vault/iu.test(sentence)) {
      assert(/\b(?:not|never|unsupported|forbidden|reject\w*|exclud\w*)\b/iu.test(sentence),
        "stateless QR vault cannot claim TROPIC01 custody");
    }
  }
}
export function checkFeatureData(matrix) {
  for (const name of ["raspberry_qr_vault","esp32_qr_vault"]) {
    assert.equal(matrix.solutions[name].features.persistent_secret_custody.current,"forbidden");
    assert.equal(matrix.solutions[name].features.persistent_secret_custody.target,"forbidden");
    assert(!Object.keys(matrix.solutions[name].features).some((key)=>/tropic01/iu.test(key)),"no TROPIC01 feature in stateless QR profile");
  }
}
export function checkCurrentOwnerLinks(text) {
  for (const match of text.matchAll(/https:\/\/github\.com\/nSealr\/([^\s/#)]+)([^\s)]*)/gu)) {
    assert(!["firmware","raspberry","vault","companion","specs","lab","smartcard"].includes(match[1]),"stale public repository alias in current navigation");
    if (/\/apps\/pi(?:\/|$)/u.test(match[2])) assert.equal(match[1],"nsealr","Pi component must link to its current public owner");
  }
}
export function sourceFiles(directory) {
 return readdirSync(directory,{withFileTypes:true}).flatMap((entry)=>{
  const path=join(directory,entry.name);
  if (entry.isDirectory()) return ["src"].includes(entry.name) || !["node_modules","dist","target",".tmp"].includes(entry.name) ? sourceFiles(path) : [];
  return entry.isFile() && path.endsWith(".ts") ? [path] : [];
 });
}
export function main() {
 for(const directory of ["packages","apps/bridge"]) for(const path of sourceFiles(join(root,directory))) {
  checkProductionSource(relative(root,path),readFileSync(path,"utf8"));
 }
 checkFeatureData(JSON.parse(readFileSync(join(root,"protocols/contracts/v1/vectors/features/signer-feature-matrix-v0.json"),"utf8")));
 console.log("production source custody, validator ownership and stateless feature boundaries passed");
}
if (import.meta.url===pathToFileURL(process.argv[1]).href) main();
