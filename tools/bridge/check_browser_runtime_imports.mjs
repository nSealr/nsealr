#!/usr/bin/env node
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import * as ts from "typescript";
import { packageDirName, root, sourceManifest } from "./package_set.mjs";

const browserRuntimeEntrypoints = [
  "apps/browser-extension/src/nsealr-background-entrypoint.ts",
  "apps/browser-extension/src/nsealr-content-script-entrypoint.ts",
  "apps/browser-extension/src/nsealr-popup-entrypoint.ts",
  "apps/browser-extension/src/nsealr-page-script-entrypoint.ts",
  "packages/browser-provider/src/index.ts",
  "packages/framing/src/index.ts",
  "packages/sdk/src/browser.ts"
].map((path) => join(root, path));

const nodeBuiltinSpecifiers = new Set([
  "assert",
  "buffer",
  "child_process",
  "crypto",
  "events",
  "fs",
  "net",
  "os",
  "path",
  "stream",
  "url",
  "util",
  "zlib"
]);

const visited = new Set();

function relativePath(path) {
  return relative(root, path);
}

function exportedSubpaths(packageName) {
  const manifest = sourceManifest(packageName);
  const exports = manifest.exports;
  if (!exports || typeof exports !== "object") return new Set([""]);
  return new Set(Object.keys(exports).map((subpath) => (subpath === "." ? "" : subpath.slice(1))));
}

function nsealrPackageName(specifier) {
  if (!specifier.startsWith("@nsealr/")) return undefined;
  const [scope, name] = specifier.split("/");
  return `${scope}/${name}`;
}

function resolveRelative(fromFile, specifier) {
  const candidate = resolve(dirname(fromFile), specifier.replace(/\.js$/u, ".ts"));
  if (existsSync(candidate)) return candidate;
  const indexCandidate = join(candidate, "index.ts");
  if (existsSync(indexCandidate)) return indexCandidate;
  throw new Error(`cannot resolve browser runtime import ${specifier} from ${relativePath(fromFile)}`);
}

function resolveNsealrPackage(fromFile, specifier) {
  const packageName = nsealrPackageName(specifier);
  assert(packageName !== undefined, "internal error: expected @nsealr package import");
  const subpath = specifier.slice(packageName.length);
  const reviewedSubpaths = exportedSubpaths(packageName);
  assert(
    reviewedSubpaths.has(subpath),
    `${relativePath(fromFile)} imports unreviewed browser runtime subpath ${specifier}`
  );
  assert(
    packageName !== "@nsealr/client" || subpath !== "",
    `${relativePath(fromFile)} must import @nsealr/client/browser instead of the Node-capable root entrypoint`
  );
  const sourceSubpath = subpath === "" ? "index" : subpath.slice(1);
  return join(root, "packages", packageDirName(packageName), "src", `${sourceSubpath}.ts`);
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

function assertBrowserRuntimeSource(path, source) {
  assert(
    !/\bBuffer\b/u.test(source),
    `${relativePath(path)} must not use Node Buffer in browser runtime code`
  );
  assert(
    !/\bprocess\b/u.test(source),
    `${relativePath(path)} must not use Node process in browser runtime code`
  );
}

function visitSourceFile(path) {
  assert(
    !isAbsolute(relative(root, path)) && !relative(root, path).startsWith(".."),
    `browser runtime source escapes companion root: ${path}`
  );
  if (visited.has(path)) return;
  visited.add(path);

  const sourceText = readFileSync(path, "utf-8");
  assertBrowserRuntimeSource(path, sourceText);
  const source = ts.createSourceFile(path, sourceText, ts.ScriptTarget.Latest, true);

  function visit(node) {
    const specifier = moduleSpecifierText(node);
    if (specifier !== undefined) {
      assert(
        !specifier.startsWith("node:") && !nodeBuiltinSpecifiers.has(specifier),
        `${relativePath(path)} must not import Node builtin ${specifier} in browser runtime code`
      );
      if (specifier.startsWith(".")) {
        visitSourceFile(resolveRelative(path, specifier));
      } else if (specifier.startsWith("@nsealr/")) {
        visitSourceFile(resolveNsealrPackage(path, specifier));
      }
    }
    ts.forEachChild(node, visit);
  }

  visit(source);
}

for (const entrypoint of browserRuntimeEntrypoints) {
  visitSourceFile(entrypoint);
}

console.log(`companion browser runtime import hygiene passed (${visited.size} source files)`);
