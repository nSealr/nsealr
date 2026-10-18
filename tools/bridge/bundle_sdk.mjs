#!/usr/bin/env node
// Bundle owned runtime code and relocate declarations; third-party packages keep
// their own distribution and license notices as exact external dependencies.
import assert from "node:assert/strict";
import { cpSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { build } from "esbuild";
import { root, sourceManifest } from "./package_set.mjs";

const owned = ["browser-provider", "client", "core", "framing", "nip46", "policy", "protocol", "qr", "review"];
const sdkRoot = join(root, "packages/sdk");
const out = join(sdkRoot, "dist");
const reports = [];
for (const [entry, platform] of [["index", "browser"], ["browser", "browser"], ["node", "node"]]) {
  const result = await build({ absWorkingDir: root, entryPoints: [join(sdkRoot, `src/${entry}.ts`)],
    outfile: join(out, `${entry}.js`), bundle: true, format: "esm", platform,
    target: "es2022", external: ["@noble/*", "nostr-tools", "nostr-tools/*"],
    sourcemap: false, legalComments: "eof", metafile: true, write: true });
  for (const file of Object.keys(result.metafile.inputs)) {
    assert(!/(?:^|\/)packages\/(?:dev-signer|fixtures|smartcard)\//u.test(file), `forbidden SDK input: ${file}`);
    assert(!file.endsWith(".test.ts"), `test in SDK: ${file}`);
  }
  for (const artifact of Object.values(result.metafile.outputs)) {
    assert(!artifact.imports.some((entry) => entry.path.startsWith("@nsealr/")), "packed SDK must contain its owned runtime");
  }
  reports.push({ entry, platform, ...result.metafile });
}
for (const name of owned) {
  const destination = join(out, "internal", name);
  mkdirSync(destination, { recursive: true });
  for (const file of readdirSync(join(root, "packages", name, "dist"))) {
    if (file.endsWith(".d.ts")) cpSync(join(root, "packages", name, "dist", file), join(destination, file));
  }
}
function declarations(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? declarations(path) : entry.name.endsWith(".d.ts") ? [path] : [];
  });
}
for (const path of declarations(out)) {
  const source = readFileSync(path, "utf8");
  const relocated = source.replace(/(["'])@nsealr\/([a-z0-9-]+)([^"']*)\1/gu, (_match, quote, name, subpath) => {
    assert(owned.includes(name), `forbidden declaration dependency ${name}`);
    const manifest = sourceManifest(`@nsealr/${name}`);
    const entry = manifest.exports[subpath ? `.${subpath}` : "."];
    assert(entry?.types?.startsWith("./dist/"), `unmapped declaration export ${name}${subpath}`);
    const target = resolve(out, "internal", name, entry.types.slice("./dist/".length)).replace(/\.d\.ts$/u, ".js");
    let specifier = relative(dirname(path), target).replaceAll("\\", "/");
    if (!specifier.startsWith(".")) specifier = `./${specifier}`;
    return `${quote}${specifier}${quote}`;
  });
  assert(!relocated.includes("@nsealr/"), `unbundled declaration in ${path}`);
  writeFileSync(path, relocated);
}
mkdirSync(join(root, "build"), { recursive: true });
writeFileSync(join(root, "build/sdk-bundle-report.json"), JSON.stringify(reports, null, 2) + "\n");
console.log("SDK root/browser/Node runtime and owned declarations bundled");
