#!/usr/bin/env node
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { privatePackages, publicPackages } from "./package_set.mjs";
import {
  RELEASE_PLAN_FORMAT,
  RELEASE_PLAN_REVIEW_FORMAT,
  buildCompanionPackageReleasePlan,
  buildCompanionPackageReleasePlanReview,
  companionPackageReleasePlanDigest,
  companionPackageReleasePlanJson,
  companionPackageReleasePlanReviewJson
} from "./release_plan.mjs";

const releasePlan = buildCompanionPackageReleasePlan();

assert.equal(releasePlan.format, RELEASE_PLAN_FORMAT);
assert.equal(releasePlan.package_manager, "pnpm@10.33.4");
assert.equal(releasePlan.package_count, publicPackages.length);
assert.equal(releasePlan.includes_private_packages, false);
assert.equal(releasePlan.local_npm_publish_allowed, false);
assert.equal(releasePlan.workflow_publish_allowed, false);
assert.equal(releasePlan.requires_trusted_publishing, true);
assert.equal(releasePlan.requires_npm_provenance, true);
assert.equal(releasePlan.stores_production_secrets, false);
assert.equal(releasePlan.contains_secret_material, false);
assert.deepEqual(releasePlan.required_local_gates, [
  "make ci",
  "make integration in ../lab",
  "make release-artifacts"
]);

const plannedPackageNames = releasePlan.packages.map((entry) => entry.name);
assert.deepEqual(plannedPackageNames, publicPackages);
for (const privatePackageName of privatePackages) {
  assert(!plannedPackageNames.includes(privatePackageName), `${privatePackageName} must not be in the release plan`);
}
for (const entry of releasePlan.packages) {
  assert.equal(entry.version, releasePlan.version, `${entry.name} must use the synchronized release version`);
  assert.match(entry.directory, /^packages\/[a-z0-9-]+$/u, `${entry.name} directory must stay package-local`);
  assert.match(entry.tarball, /^nsealr-[a-z0-9-]+-\d+\.\d+\.\d+\.tgz$/u, `${entry.name} tarball name drifted`);
  assert.deepEqual(entry.files, ["dist", "README.md"], `${entry.name} must publish only dist and README`);
  assert.deepEqual(entry.publish_config, { access: "public", provenance: true });
  assert.equal(entry.license, "MIT");
  assert.equal(entry.private, false);
}

const digest = companionPackageReleasePlanDigest(releasePlan);
assert.match(digest, /^[0-9a-f]{64}$/u);
assert.equal(digest, companionPackageReleasePlanDigest(JSON.parse(companionPackageReleasePlanJson())));

const review = buildCompanionPackageReleasePlanReview();
assert.equal(review.format, RELEASE_PLAN_REVIEW_FORMAT);
assert.equal(review.release_plan_digest, digest);
assert.deepEqual(review.release_plan, releasePlan);
assert.equal(review.requires_user_review, true);
assert.equal(review.requires_trusted_publishing, true);
assert.equal(review.requires_npm_provenance, true);
assert.equal(review.local_npm_publish_allowed, false);
assert.equal(review.workflow_publish_allowed, false);
assert.equal(review.includes_private_packages, false);
assert.equal(review.stores_production_secrets, false);
assert.equal(review.contains_secret_material, false);
assert.deepEqual(JSON.parse(companionPackageReleasePlanReviewJson()), review);

const cliReview = spawnSync(process.execPath, ["scripts/release_plan.mjs", "--", "--review"], {
  encoding: "utf-8"
});
assert.equal(cliReview.status, 0, cliReview.stderr);
assert.deepEqual(JSON.parse(cliReview.stdout), review);

console.log(`companion package release plan passed (${publicPackages.length} public packages)`);
