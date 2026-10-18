#!/usr/bin/env node
import assert from "node:assert/strict";
import { join } from "node:path";
import { build } from "esbuild";
import { root } from "./package_set.mjs";

const entryPoints = [
  "apps/browser-extension/src/nsealr-background-entrypoint.ts",
  "apps/browser-extension/src/nsealr-content-script-entrypoint.ts",
  "apps/browser-extension/src/nsealr-popup-entrypoint.ts",
  "apps/browser-extension/src/nsealr-page-script-entrypoint.ts"
].map((path) => join(root, path));

const result = await build({
  absWorkingDir: root,
  bundle: true,
  entryNames: "[name]",
  entryPoints,
  format: "iife",
  logLevel: "silent",
  metafile: true,
  outdir: "browser-runtime-bundle-smoke",
  platform: "browser",
  sourcemap: false,
  target: "es2022",
  treeShaking: true,
  write: false
});

const nodeBufferReference = /(?:\bBuffer\s*(?:\.|\[)|new\s+Buffer\b|typeof\s+Buffer|globalThis\.Buffer)/u;
const nodeProcessReference = /(?:\bprocess\s*(?:\.|\[)|typeof\s+process|globalThis\.process)/u;

assert.equal(result.outputFiles?.length, entryPoints.length, "browser runtime bundle smoke must produce one output per packaged entrypoint");

for (const output of result.outputFiles ?? []) {
  assert(
    !nodeBufferReference.test(output.text),
    `${output.path} must not contain Node Buffer references after browser bundling`
  );
  assert(
    !nodeProcessReference.test(output.text),
    `${output.path} must not contain Node process references after browser bundling`
  );
  assert(
    !/node:/u.test(output.text),
    `${output.path} must not contain Node builtin specifiers after browser bundling`
  );
}

console.log(`companion browser runtime bundle smoke passed (${entryPoints.length} entrypoints)`);
