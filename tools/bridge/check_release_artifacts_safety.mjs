#!/usr/bin/env node
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { root } from "./package_set.mjs";

function expectRejectedArgs(args, expectedPattern, label) {
  const result = spawnSync(process.execPath, ["scripts/prepare_release_artifacts.mjs", ...args], {
    cwd: root,
    encoding: "utf-8"
  });
  assert.notEqual(result.status, 0, `${label} must be rejected before release artifact cleanup`);
  assert.match(
    `${result.stdout}\n${result.stderr}`,
    expectedPattern,
    `${label} must fail with the expected release output safety guard`
  );
}

function expectRejectedOutput(path) {
  expectRejectedArgs(
    ["--out", path],
    /release artifact output directory must be a child of release-artifacts\//u,
    path
  );
}

for (const path of [".", "packages", "release-artifacts", "release-artifacts/.."]) {
  expectRejectedOutput(path);
}

expectRejectedArgs(["--out"], /--out requires a directory/u, "missing release output directory");
expectRejectedArgs(
  ["--out", "release-artifacts/packages", "--out", "release-artifacts/other"],
  /--out must be specified only once/u,
  "duplicated release output directory"
);
expectRejectedArgs(["--unknown"], /unsupported release artifact option/u, "unknown release artifact option");

console.log("companion release artifact output safety check passed");
