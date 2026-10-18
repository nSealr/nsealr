#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { readdirSync, rmSync, statSync } from "node:fs";
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
  "smartcard",
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

function runTsc(packageDir) {
  const sourceDir = join(root, "packages", packageDir, "src");
  const outDir = join(root, "packages", packageDir, "dist");
  if (!statSync(sourceDir).isDirectory()) {
    throw new Error(`missing source directory for ${packageDir}`);
  }
  rmSync(outDir, { recursive: true, force: true });
  const sourceFiles = collectSources(sourceDir).map((path) => relative(root, path));
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
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

for (const packageDir of packageOrder) {
  runTsc(packageDir);
}

console.log("nSealr package build artifacts generated");
