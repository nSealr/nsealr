#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, realpathSync, rmSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { packageManagerCommand, root } from "./package_set.mjs";

const packageOrder = [
  "core",
  "policy",
  "protocol",
  "review",
  "framing",
  "nip46",
  "qr",
  "client",
  "fixtures",
  "dev-signer",
  "transport",
  "browser-provider",
  "sdk"
];

function collectSources(directory) {
  const entries = readdirSync(directory, { withFileTypes: true });
  const sources = [];
  for (const entry of entries) {
    const fullPath = join(directory, entry.name);
    if (entry.isDirectory()) {
      sources.push(...collectSources(fullPath));
    } else if (entry.isFile() && entry.name.endsWith(".ts") && !entry.name.endsWith(".test.ts")) {
      sources.push(fullPath);
    }
  }
  return sources.sort();
}

function hashes(paths) {
  return Object.fromEntries(paths.map((path) => [path, createHash("sha256").update(readFileSync(join(root, path))).digest("hex")]));
}

function runTsc(sourceDir, outDir, recordBridge = false) {
  if (!statSync(sourceDir).isDirectory()) {
    throw new Error(`missing source directory ${relative(root, sourceDir)}`);
  }
  rmSync(outDir, { recursive: true, force: true });
  const sourceFiles = collectSources(sourceDir).map((path) => relative(root, path));
  const before = recordBridge ? hashes(sourceFiles) : undefined;
  const packageManager = packageManagerCommand();
  const args = [
    ...packageManager.prefixArgs,
    "exec",
    "tsc",
    "--ignoreConfig",
    "--target",
    "ES2022",
    "--module",
    "NodeNext",
    "--moduleResolution",
    "NodeNext",
    "--strict",
    "--esModuleInterop",
    "--forceConsistentCasingInFileNames",
    "--skipLibCheck",
    "--resolveJsonModule",
    "--types",
    "node",
    "--declaration",
    "--rootDir",
    relative(root, sourceDir),
    "--outDir",
    relative(root, outDir),
    ...sourceFiles
  ];
  const result = spawnSync(packageManager.command, args, { cwd: root, env: packageManager.env, stdio: "inherit" });
  if (recordBridge) {
    const after = hashes(sourceFiles);
    const outputFiles = sourceFiles.flatMap((path) => [".js", ".d.ts"].map((suffix) =>
      relative(root, join(outDir, relative(sourceDir, join(root, path)).replace(/\.ts$/u, suffix)))));
    const compiler = realpathSync(join(root, "node_modules/typescript/bin/tsc"));
    console.log("\n" + JSON.stringify({ bridge_service_build: {
      v: 1, role: "current_checkout_compiler_artifacts_only", argv: [packageManager.command, ...args], cwd: root,
      compiler: { path: compiler, version: JSON.parse(readFileSync(join(root, "node_modules/typescript/package.json"), "utf8")).version,
        sha256: createHash("sha256").update(readFileSync(compiler)).digest("hex") },
      status: result.status, signal: result.signal,
      error: result.error ? { name: result.error.name, message: result.error.message } : null,
      source_before: before, source_after: after, outputs: result.status === 0 ? hashes(outputFiles) : {}
    } }));
    if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error("Bridge source changed during compilation");
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

for (const packageDir of packageOrder) {
  runTsc(join(root, "packages", packageDir, "src"), join(root, "packages", packageDir, "dist"));
}
runTsc(join(root, "apps/bridge/service/src"), join(root, "apps/bridge/service/dist"), true);

await import("./bundle_sdk.mjs");
console.log("nSealr package build artifacts generated");
