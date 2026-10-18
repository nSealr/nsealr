import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import * as ts from "typescript";
import { packageDirName, publicPackages, root, sourceManifest } from "./package_set.mjs";

const docPath = join(root, "docs", "bridge", "api.md");

function usage() {
  return "usage: node tools/bridge/check_api_docs.mjs [--write]";
}

function readSource(path) {
  return ts.createSourceFile(path, readFileSync(path, "utf-8"), ts.ScriptTarget.Latest, true);
}

function hasExportModifier(statement) {
  return Boolean(statement.modifiers?.some((modifier) => modifier.kind === ts.SyntaxKind.ExportKeyword));
}

function resolveSourceModule(fromPath, specifier) {
  if (!specifier.startsWith(".")) {
    return undefined;
  }
  const candidate = resolve(dirname(fromPath), specifier.replace(/\.js$/, ".ts"));
  if (existsSync(candidate)) {
    return candidate;
  }
  throw new Error(`cannot resolve export ${specifier} from ${fromPath}`);
}

function collectBindingNames(name, symbols) {
  if (ts.isIdentifier(name)) {
    symbols.add(name.text);
    return;
  }
  if (ts.isObjectBindingPattern(name) || ts.isArrayBindingPattern(name)) {
    for (const element of name.elements) {
      if (ts.isBindingElement(element)) {
        collectBindingNames(element.name, symbols);
      }
    }
  }
}

function collectExports(entryPath, seen = new Set()) {
  if (seen.has(entryPath)) {
    return new Set();
  }
  seen.add(entryPath);

  const source = readSource(entryPath);
  const symbols = new Set();
  const namespaces = new Map();
  for (const statement of source.statements) {
    if (ts.isImportDeclaration(statement) && ts.isStringLiteral(statement.moduleSpecifier) &&
        statement.importClause?.namedBindings && ts.isNamespaceImport(statement.importClause.namedBindings)) {
      const specifier = statement.moduleSpecifier.text;
      if (specifier.startsWith("@nsealr/")) {
        const parts = specifier.split("/");
        const packageName = parts.slice(0, 2).join("/");
        const subpath = parts.length > 2 ? `./${parts.slice(2).join("/")}` : ".";
        const target = sourceManifest(packageName).exports[subpath];
        if (!target?.import) throw new Error(`unmapped namespace ${specifier}`);
        namespaces.set(statement.importClause.namedBindings.name.text,
          sourcePathForDistImport(packageName, target.import));
      }
    }
  }

  for (const statement of source.statements) {
    if (ts.isExportDeclaration(statement)) {
      if (statement.exportClause && ts.isNamedExports(statement.exportClause)) {
        for (const element of statement.exportClause.elements) {
          const name = element.name.text;
          symbols.add(name);
          const namespace = namespaces.get(element.propertyName?.text ?? name);
          if (namespace) for (const symbol of collectExports(namespace, new Set())) symbols.add(`${name}.${symbol}`);
        }
      } else if (statement.moduleSpecifier && ts.isStringLiteral(statement.moduleSpecifier)) {
        const resolvedPath = resolveSourceModule(entryPath, statement.moduleSpecifier.text);
        if (resolvedPath) {
          for (const symbol of collectExports(resolvedPath, seen)) {
            symbols.add(symbol);
          }
        }
      }
      continue;
    }

    if (!hasExportModifier(statement)) {
      continue;
    }

    if (
      ts.isFunctionDeclaration(statement) ||
      ts.isClassDeclaration(statement) ||
      ts.isInterfaceDeclaration(statement) ||
      ts.isTypeAliasDeclaration(statement) ||
      ts.isEnumDeclaration(statement)
    ) {
      if (statement.name) {
        symbols.add(statement.name.text);
      }
      continue;
    }

    if (ts.isVariableStatement(statement)) {
      for (const declaration of statement.declarationList.declarations) {
        collectBindingNames(declaration.name, symbols);
      }
    }
  }

  return symbols;
}

function packageRoot(packageName) {
  return join(root, "packages", packageDirName(packageName));
}

function entrypointForPackage(packageName) {
  return join(packageRoot(packageName), "src", "index.ts");
}

function sourcePathForDistImport(packageName, importPath) {
  const filename = importPath.replace("./dist/", "").replace(/\.js$/, ".ts");
  return join(packageRoot(packageName), "src", filename);
}

function collectSubpathExports(packageName) {
  const manifest = sourceManifest(packageName);
  const exports = manifest.exports;
  if (!exports || typeof exports !== "object") {
    return [];
  }
  const subpaths = [];
  for (const [subpath, target] of Object.entries(exports)) {
    if (subpath === "." || !target || typeof target !== "object") {
      continue;
    }
    const importPath = target.import;
    if (typeof importPath !== "string") {
      continue;
    }
    const sourcePath = sourcePathForDistImport(packageName, importPath);
    subpaths.push({
      subpath,
      importName: `${packageName}${subpath.slice(1)}`,
      exports: [...collectExports(sourcePath)].sort()
    });
  }
  return subpaths.sort((left, right) => left.subpath.localeCompare(right.subpath));
}

function renderApiDocs() {
  const lines = [
    "# Public API Surface",
    "",
    "This file is generated from the public package entrypoints by",
    "`tools/bridge/check_api_docs.mjs`. It documents the pre-release package surface",
    "that consumers may import after the package gates pass.",
    "",
    "Regenerate and verify it with:",
    "",
    "```sh",
    "pnpm api-docs:update",
    "pnpm api-docs:check",
    "```",
    "",
    "The packages are still pre-release. Breaking changes are allowed before the",
    "first public npm publication, but every exported symbol must remain visible",
    "here so API drift is reviewed deliberately.",
    ""
  ];

  for (const packageName of publicPackages) {
    const manifest = sourceManifest(packageName);
    if (typeof manifest.description !== "string" || manifest.description.length === 0) {
      throw new Error(`${packageName} must declare a package description`);
    }
    const symbols = [...collectExports(entrypointForPackage(packageName))].sort();
    if (symbols.length === 0) {
      throw new Error(`${packageName} has no public exports`);
    }

    lines.push(`## ${packageName}`);
    lines.push("");
    lines.push(manifest.description);
    lines.push("");
    lines.push(`Source entrypoint: \`packages/${packageDirName(packageName)}/src/index.ts\``);
    lines.push("");
    lines.push("Exports:");
    for (const symbol of symbols) {
      lines.push(`- \`${symbol}\``);
    }

    const subpaths = collectSubpathExports(packageName);
    if (subpaths.length > 0) {
      lines.push("");
      lines.push("Additional package subpaths:");
      for (const subpath of subpaths) {
        lines.push(`- \`${subpath.importName}\`: ${subpath.exports.map((symbol) => `\`${symbol}\``).join(", ")}`);
      }
    }
    lines.push("");
  }

  return `${lines.join("\n").trimEnd()}\n`;
}

function main() {
  const args = process.argv.slice(2);
  const shouldWrite = args.includes("--write");
  const stdout = args.includes("--stdout");
  const unknownArgs = args.filter((arg) => arg !== "--write" && arg !== "--stdout");
  if (unknownArgs.length > 0) {
    console.error(usage());
    process.exit(2);
  }

  const expected = renderApiDocs();
  if (stdout) { process.stdout.write(expected); return; }
  if (shouldWrite) {
    writeFileSync(docPath, expected);
    console.log(`wrote ${docPath}`);
    return;
  }

  if (!existsSync(docPath)) {
    console.error("docs/api.md is missing; run pnpm api-docs:update");
    process.exit(1);
  }

  const actual = readFileSync(docPath, "utf-8");
  if (actual !== expected) {
    console.error("docs/api.md is out of date; run pnpm api-docs:update");
    process.exit(1);
  }

  console.log("companion API docs are up to date");
}

main();
