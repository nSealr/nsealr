#!/usr/bin/env node
import { mkdtempSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  assertCompanionPackageRegistry,
  assertPublicPackageTarball,
  packageFilename,
  packageManagerCommand,
  publicPackageExportSpecifiers,
  publicPackages,
  run,
  sourceManifest
} from "./package_set.mjs";

assertCompanionPackageRegistry();

function cleanNpmConsumerEnv() {
  const env = { ...process.env, npm_config_loglevel: "error" };
  for (const key of Object.keys(env)) {
    if (key.startsWith("npm_config_") && key !== "npm_config_loglevel") {
      delete env[key];
    }
  }
  return env;
}

const packageManager = packageManagerCommand();
const packDir = mkdtempSync(join(tmpdir(), "nsealr-pack-"));
const consumerDir = mkdtempSync(join(tmpdir(), "nsealr-pack-consumer-"));
const tarballs = new Map();

for (const packageName of publicPackages) {
  const expectedManifest = sourceManifest(packageName);
  run(packageManager.command, [
    ...packageManager.prefixArgs,
    "--filter",
    packageName,
    "pack",
    "--pack-destination",
    packDir
  ], { env: packageManager.env });
  const tarball = join(packDir, packageFilename(expectedManifest));
  tarballs.set(packageName, tarball);
  assertPublicPackageTarball(packageName, tarball, expectedManifest);
}

writeFileSync(join(consumerDir, "package.json"), JSON.stringify({
  name: "nsealr-packed-consumer-smoke",
  version: "0.0.0",
  private: true,
  type: "module",
  dependencies: Object.fromEntries(publicPackages.map((packageName) => [packageName, `file:${tarballs.get(packageName)}`]))
}, null, 2));

writeFileSync(join(consumerDir, "index.mjs"), `
import assert from "node:assert/strict";

const packages = ${JSON.stringify(publicPackages, null, 2)};
const packageExports = ${JSON.stringify(publicPackageExportSpecifiers, null, 2)};
for (const specifier of packageExports) {
  const module = await import(specifier);
  assert(Object.keys(module).length > 0, specifier + " must import from packed tarball");
}
assert(packageExports.length >= packages.length, "packed smoke must cover every public package root and subpath export");

const { computeEventId } = await import("@nsealr/core");
const { validateRequest } = await import("@nsealr/protocol");
const { parseLocalClientIdentity } = await import("@nsealr/client/client-identity");

assert.equal(validateRequest({
  version: 1,
  request_id: "packed-consumer-get-public-key",
  method: "get_public_key"
}).ok, true);
assert.equal(computeEventId({
  pubkey: "0".repeat(64),
  created_at: 1,
  kind: 1,
  tags: [],
  content: "packed consumer smoke"
}).length, 64);
assert.equal(parseLocalClientIdentity({
  surface: "browser_extension",
  origin: "https://example.com",
  app_name: "Packed Consumer Smoke",
  instance_id: "packed-consumer-smoke"
}).origin, "https://example.com");

console.log("nSealr packed package smoke passed");
`);

run("npm", ["install", "--ignore-scripts", "--no-audit", "--fund=false"], { cwd: consumerDir, env: cleanNpmConsumerEnv() });
run("node", ["index.mjs"], { cwd: consumerDir });
