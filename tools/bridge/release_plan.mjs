#!/usr/bin/env node
import { createHash } from "node:crypto";
import {
  assertCompanionPackageRegistry,
  packageDirName,
  packageFilename,
  publicPackages,
  sourceManifest
} from "./package_set.mjs";

export const RELEASE_PLAN_FORMAT = "nsealr-companion-package-release-plan-v0";
export const RELEASE_PLAN_DIGEST_INPUT_FORMAT = "nsealr-companion-package-release-plan-digest-v0";
export const RELEASE_PLAN_REVIEW_FORMAT = "nsealr-companion-package-release-plan-review-v0";

function sha256Json(value) {
  return createHash("sha256")
    .update(JSON.stringify(value))
    .digest("hex");
}

export function buildCompanionPackageReleasePlan() {
  assertCompanionPackageRegistry();
  const packages = publicPackages.map((packageName) => {
    const manifest = sourceManifest(packageName);
    return {
      name: manifest.name,
      version: manifest.version,
      directory: `packages/${packageDirName(packageName)}`,
      tarball: packageFilename(manifest),
      files: manifest.files,
      publish_config: manifest.publishConfig,
      license: manifest.license,
      private: false
    };
  });
  const versions = [...new Set(packages.map((entry) => entry.version))];
  if (versions.length !== 1) {
    throw new Error("companion package release plan requires one synchronized version");
  }
  return Object.freeze({
    format: RELEASE_PLAN_FORMAT,
    version: versions[0],
    package_manager: "pnpm@10.33.4",
    package_count: packages.length,
    packages,
    required_local_gates: Object.freeze([
      "make ci",
      "make integration in ../lab",
      "make release-artifacts"
    ]),
    requires_trusted_publishing: true,
    requires_npm_provenance: true,
    local_npm_publish_allowed: false,
    workflow_publish_allowed: false,
    includes_private_packages: false,
    stores_production_secrets: false,
    contains_secret_material: false
  });
}

export function companionPackageReleasePlanDigest(plan) {
  return sha256Json({
    format: RELEASE_PLAN_DIGEST_INPUT_FORMAT,
    plan
  });
}

export function buildCompanionPackageReleasePlanReview() {
  const plan = buildCompanionPackageReleasePlan();
  return Object.freeze({
    format: RELEASE_PLAN_REVIEW_FORMAT,
    release_plan_digest: companionPackageReleasePlanDigest(plan),
    release_plan: plan,
    requires_user_review: true,
    requires_trusted_publishing: true,
    requires_npm_provenance: true,
    local_npm_publish_allowed: false,
    workflow_publish_allowed: false,
    includes_private_packages: false,
    stores_production_secrets: false,
    contains_secret_material: false
  });
}

export function companionPackageReleasePlanJson() {
  return `${JSON.stringify(buildCompanionPackageReleasePlan(), null, 2)}\n`;
}

export function companionPackageReleasePlanReviewJson() {
  return `${JSON.stringify(buildCompanionPackageReleasePlanReview(), null, 2)}\n`;
}

function main(args) {
  const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
  if (normalizedArgs.length === 0) {
    process.stdout.write(companionPackageReleasePlanJson());
    return;
  }
  if (normalizedArgs.length === 1 && normalizedArgs[0] === "--review") {
    process.stdout.write(companionPackageReleasePlanReviewJson());
    return;
  }
  throw new Error("usage: release_plan.mjs [--review]");
}

if (import.meta.url === `file://${process.argv[1]}`) {
  try {
    main(process.argv.slice(2));
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(1);
  }
}
