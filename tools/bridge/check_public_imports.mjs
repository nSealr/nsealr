#!/usr/bin/env node
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import * as ts from "typescript";
import { packageDirName, packageExportSubpaths, publicPackages, root } from "./package_set.mjs";

const publicPackageSet = new Set(publicPackages);

function collectSourceFiles(directory) {
  const entries = readdirSync(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const fullPath = join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectSourceFiles(fullPath));
      continue;
    }
    if (entry.isFile() && entry.name.endsWith(".ts") && !entry.name.endsWith(".test.ts")) {
      files.push(fullPath);
    }
  }
  return files.sort();
}

const exportedSubpathsByPackage = new Map(
  publicPackages.map((packageName) => [packageName, new Set(packageExportSubpaths(packageName))])
);

function nsealrPackageName(specifier) {
  if (!specifier.startsWith("@nsealr/")) return undefined;
  const [scope, name] = specifier.split("/");
  return `${scope}/${name}`;
}

function assertInsideDirectory(path, directory, message) {
  const relativePath = relative(directory, path);
  assert(
    relativePath === "" || (!relativePath.startsWith("..") && !isAbsolute(relativePath)),
    message
  );
}

function resolvedRelativeImport(fromFile, specifier) {
  const resolved = resolve(dirname(fromFile), specifier.replace(/\.js$/u, ".ts"));
  if (existsSync(resolved) && statSync(resolved).isFile()) {
    return resolved;
  }
  throw new Error(`cannot resolve import ${specifier} from ${relative(root, fromFile)}`);
}

function assertNsealrImport(ownerPackage, fromFile, specifier) {
  const packageName = nsealrPackageName(specifier);
  assert(packageName !== undefined, "internal error: expected @nsealr package import");
  assert(
    publicPackageSet.has(packageName),
    `${relative(root, fromFile)} must not import non-public package ${packageName}`
  );

  const subpath = specifier.slice(packageName.length);
  const exportedSubpaths = exportedSubpathsByPackage.get(packageName) ?? new Set([""]);
  assert(
    exportedSubpaths.has(subpath),
    `${relative(root, fromFile)} must import ${packageName} through a reviewed export subpath, got ${specifier}`
  );

  assert(
    packageName !== "@nsealr/dev-signer",
    `${relative(root, fromFile)} must not import test-only @nsealr/dev-signer`
  );
  assert(
    packageName !== ownerPackage,
    `${relative(root, fromFile)} must use relative imports inside ${ownerPackage}, got ${specifier}`
  );
}

function assertAllowedImport(ownerPackage, packageSourceRoot, fromFile, specifier) {
  if (specifier.startsWith(".")) {
    assertInsideDirectory(
      resolvedRelativeImport(fromFile, specifier),
      packageSourceRoot,
      `${relative(root, fromFile)} relative import escapes package src: ${specifier}`
    );
    return;
  }
  if (specifier.startsWith("@nsealr/")) {
    assertNsealrImport(ownerPackage, fromFile, specifier);
  }
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

function checkSourceFile(ownerPackage, packageSourceRoot, sourcePath) {
  const source = ts.createSourceFile(
    sourcePath,
    readFileSync(sourcePath, "utf-8"),
    ts.ScriptTarget.Latest,
    true
  );

  function visit(node) {
    const specifier = moduleSpecifierText(node);
    if (specifier !== undefined) {
      assertAllowedImport(ownerPackage, packageSourceRoot, sourcePath, specifier);
    }
    ts.forEachChild(node, visit);
  }

  visit(source);
}

for (const packageName of publicPackages) {
  const packageSourceRoot = join(root, "packages", packageDirName(packageName), "src");
  for (const sourcePath of collectSourceFiles(packageSourceRoot)) {
    checkSourceFile(packageName, packageSourceRoot, sourcePath);
  }
}

console.log("companion public package import hygiene passed");
