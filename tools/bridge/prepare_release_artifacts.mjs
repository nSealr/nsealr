#!/usr/bin/env node
import assert from "node:assert/strict";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { basename, isAbsolute, join, relative, resolve } from "node:path";
import {
  assertCompanionPackageRegistry,
  assertPublicPackageTarball,
  fileIntegrity,
  packageFilename,
  packageManagerCommand,
  publicPackages,
  root,
  run,
  sourceManifest
} from "./package_set.mjs";
import {
  buildCompanionPackageReleasePlan,
  companionPackageReleasePlanDigest
} from "./release_plan.mjs";

function outputDirectoryFromArgs(args) {
  let outDir;
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--out") {
      if (outDir !== undefined) throw new Error("--out must be specified only once");
      const value = args[index + 1];
      if (!value || value.startsWith("--")) throw new Error("--out requires a directory");
      outDir = resolve(root, value);
      index += 1;
    } else {
      throw new Error(`unsupported release artifact option: ${arg}`);
    }
  }
  return outDir ?? resolve(root, "release-artifacts/packages");
}

function assertSafeReleaseOutputDirectory(outDir) {
  const releaseRoot = resolve(root, "release-artifacts");
  const relativePath = relative(releaseRoot, outDir);
  if (relativePath === "" || relativePath.startsWith("..") || isAbsolute(relativePath)) {
    throw new Error("release artifact output directory must be a child of release-artifacts/");
  }
}

const outDir = outputDirectoryFromArgs(process.argv.slice(2));
assertSafeReleaseOutputDirectory(outDir);
assertCompanionPackageRegistry();
const releasePlan = buildCompanionPackageReleasePlan();
const releasePlanDigest = companionPackageReleasePlanDigest(releasePlan);
rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });

const packageManager = packageManagerCommand();
const artifacts = [];

assert.deepEqual(releasePlan.packages.map((entry) => entry.name), publicPackages);

for (const plannedPackage of releasePlan.packages) {
  const packageName = plannedPackage.name;
  const expectedManifest = sourceManifest(packageName);
  assert.equal(plannedPackage.version, expectedManifest.version);
  assert.equal(plannedPackage.tarball, packageFilename(expectedManifest));
  run(packageManager.command, [
    ...packageManager.prefixArgs,
    "--filter",
    packageName,
    "pack",
    "--pack-destination",
    outDir
  ], { env: packageManager.env });
  const tarball = join(outDir, packageFilename(expectedManifest));
  assertPublicPackageTarball(packageName, tarball, expectedManifest);
  artifacts.push({
    name: packageName,
    version: expectedManifest.version,
    file: basename(tarball),
    ...fileIntegrity(tarball)
  });
}

writeFileSync(join(outDir, "manifest.json"), `${JSON.stringify({
  format: "nsealr-companion-release-artifacts-v0",
  release_plan_format: releasePlan.format,
  release_plan_digest: releasePlanDigest,
  version: releasePlan.version,
  package_count: artifacts.length,
  packages: artifacts
}, null, 2)}\n`, "utf8");

console.log(`nSealr package release artifacts prepared in ${outDir}`);
