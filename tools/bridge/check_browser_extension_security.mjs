#!/usr/bin/env node
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";
import * as ts from "typescript";
import { root } from "./package_set.mjs";

const auditedRoots = [
  "apps/browser-extension/src",
  "packages/browser-provider/src",
  "packages/sdk/src"
].map((path) => join(root, path));

const bannedPackagePrefixes = [
  "@nsealr/dev-signer",
  "@noble/",
  "nostr-tools",
  "secp256k1"
];

const bannedRuntimeApiPatterns = [
  /\bbrowser\.storage\b/u,
  /\bchrome\.storage\b/u,
  /\blocalStorage\b/u,
  /\bsessionStorage\b/u,
  /\bindexedDB\b/u
];

const bannedSigningCodePatterns = [
  /\bfinalizeEvent\b/u,
  /\bgenerateSecretKey\b/u,
  /\bsignSchnorr\b/u,
  /\bschnorr\.sign\b/u,
  /\bsecp256k1\.sign\b/u,
  /\bnsecEncode\b/u
];

function collectSourceFiles(directory) {
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectSourceFiles(path));
      continue;
    }
    if (entry.isFile() && entry.name.endsWith(".ts") && !entry.name.endsWith(".test.ts")) {
      files.push(path);
    }
  }
  return files.sort();
}

function relativePath(path) {
  return relative(root, path);
}

function moduleSpecifierText(node) {
  if (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) {
    return node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)
      ? node.moduleSpecifier.text
      : undefined;
  }
  if (
    ts.isCallExpression(node) &&
    node.expression.kind === ts.SyntaxKind.ImportKeyword &&
    node.arguments.length === 1 &&
    ts.isStringLiteral(node.arguments[0])
  ) {
    return node.arguments[0].text;
  }
  if (ts.isImportTypeNode(node) && ts.isLiteralTypeNode(node.argument) && ts.isStringLiteral(node.argument.literal)) {
    return node.argument.literal.text;
  }
  return undefined;
}

function assertNoBannedImports(path, sourceText) {
  const source = ts.createSourceFile(path, sourceText, ts.ScriptTarget.Latest, true);
  function visit(node) {
    const specifier = moduleSpecifierText(node);
    if (specifier !== undefined) {
      for (const bannedPrefix of bannedPackagePrefixes) {
        assert(
          !specifier.startsWith(bannedPrefix),
          `${relativePath(path)} must not import signing/key-custody package ${specifier}`
        );
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
}

function assertNoPattern(path, sourceText, patterns, message) {
  for (const pattern of patterns) {
    assert(!pattern.test(sourceText), `${relativePath(path)} ${message}: ${pattern}`);
  }
}

function assertPackageManifest(path) {
  const manifest = JSON.parse(readFileSync(path, "utf-8"));
  const dependencies = {
    ...(manifest.dependencies ?? {}),
    ...(manifest.devDependencies ?? {})
  };
  for (const dependency of Object.keys(dependencies)) {
    for (const bannedPrefix of bannedPackagePrefixes) {
      assert(
        !dependency.startsWith(bannedPrefix),
        `${relativePath(path)} must not depend on signing/key-custody package ${dependency}`
      );
    }
  }
}

for (const manifest of [
  "apps/browser-extension/package.json",
  "packages/browser-provider/package.json",
  "packages/sdk/package.json"
].map((path) => join(root, path))) {
  assertPackageManifest(manifest);
}

for (const sourcePath of auditedRoots.flatMap(collectSourceFiles)) {
  const sourceText = readFileSync(sourcePath, "utf-8");
  assertNoBannedImports(sourcePath, sourceText);
  assertNoPattern(sourcePath, sourceText, bannedRuntimeApiPatterns, "must not use browser storage before reviewed storage policy");
  assertNoPattern(sourcePath, sourceText, bannedSigningCodePatterns, "must not implement browser-side signing or key generation");
}

console.log("companion browser extension security audit passed");
