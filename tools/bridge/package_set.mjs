import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const root = dirname(fileURLToPath(new URL("../package.json", import.meta.url)));

const packagesRoot = join(root, "packages");

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf-8"));
}

export function packageDirName(packageName) {
  return packageName.replace("@nsealr/", "");
}

export function workspacePackageEntries() {
  return readdirSync(packagesRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => ({
      dir: entry.name,
      manifest: readJson(join(packagesRoot, entry.name, "package.json"))
    }))
    .sort((left, right) => left.dir.localeCompare(right.dir));
}

export const workspacePackages = workspacePackageEntries();

export const publicPackages = workspacePackages
  .filter(({ manifest }) => manifest.publishConfig?.access === "public")
  .map(({ manifest }) => manifest.name)
  .sort();

export const privatePackages = workspacePackages
  .filter(({ manifest }) => manifest.private === true)
  .map(({ manifest }) => manifest.name)
  .sort();

export function packageExportSubpaths(packageName) {
  const manifest = sourceManifest(packageName);
  const exports = manifest.exports;
  if (!exports || typeof exports !== "object") {
    return [""];
  }
  return Object.keys(exports)
    .map((subpath) => {
      if (subpath === ".") return "";
      if (subpath.startsWith("./")) return subpath.slice(1);
      throw new Error(`${packageName} export subpath ${subpath} is unsupported`);
    })
    .sort();
}

export function packageExportSpecifiers(packageName) {
  return packageExportSubpaths(packageName).map((subpath) => `${packageName}${subpath}`);
}

export const publicPackageExportSpecifiers = publicPackages
  .flatMap((packageName) => packageExportSpecifiers(packageName))
  .sort();

export function packageManagerCommand() {
  const packageManager = readJson(join(root, "package.json")).packageManager;
  assert.match(packageManager, /^pnpm@\d+\.\d+\.\d+$/u, "root packageManager must pin pnpm");
  const env = { ...process.env };
  for (const key of Object.keys(env)) {
    if (key.startsWith("npm_config_")) {
      delete env[key];
    }
  }
  return { command: "npm", prefixArgs: ["exec", "--yes", `--package=${packageManager}`, "--", "pnpm"], env };
}

export function run(command, args, options = {}) {
  const result = spawnSync(command, args, { cwd: root, stdio: "inherit", ...options });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

export function capture(command, args, options = {}) {
  const result = spawnSync(command, args, { cwd: root, encoding: "utf-8", ...options });
  if (result.status !== 0) {
    process.stderr.write(result.stderr);
    process.exit(result.status ?? 1);
  }
  return result.stdout;
}

export function sourceManifest(packageName) {
  return readJson(join(root, "packages", packageDirName(packageName), "package.json"));
}

export function packageFilename(manifest) {
  return `${manifest.name.replace("@", "").replace("/", "-")}-${manifest.version}.tgz`;
}

export function fileIntegrity(path) {
  const data = readFileSync(path);
  return {
    bytes: data.byteLength,
    sha256: createHash("sha256").update(data).digest("hex")
  };
}

export function assertNoWorkspaceProtocols(value, path = "package.json") {
  if (typeof value === "string") {
    assert(!value.startsWith("workspace:"), `${path} must not contain workspace protocol dependencies`);
    return;
  }
  if (Array.isArray(value)) {
    for (const [index, item] of value.entries()) {
      assertNoWorkspaceProtocols(item, `${path}[${index}]`);
    }
    return;
  }
  if (value && typeof value === "object") {
    for (const [key, item] of Object.entries(value)) {
      assertNoWorkspaceProtocols(item, `${path}.${key}`);
    }
  }
}

function packageReferenceEntries(value, path = "package.json") {
  if (typeof value === "string") {
    return value.startsWith("@nsealr/") ? [{ path, packageName: value.split("/").slice(0, 2).join("/") }] : [];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => packageReferenceEntries(item, `${path}[${index}]`));
  }
  if (value && typeof value === "object") {
    return Object.entries(value).flatMap(([key, item]) => {
      if (key.startsWith("@nsealr/")) {
        return [{ path: `${path}.${key}`, packageName: key.split("/").slice(0, 2).join("/") }];
      }
      return packageReferenceEntries(item, `${path}.${key}`);
    });
  }
  return [];
}

export function assertNoPrivatePackageReferences(value, path = "package.json") {
  const privatePackageSet = new Set(privatePackages);
  for (const reference of packageReferenceEntries(value, path)) {
    assert(
      !privatePackageSet.has(reference.packageName),
      `${reference.path} must not reference private/test-only package ${reference.packageName}`
    );
  }
}

function workspaceDependencyEntries(manifest, sections) {
  return sections.flatMap((section) => {
    const dependencies = manifest[section];
    if (!dependencies || typeof dependencies !== "object") return [];
    return Object.entries(dependencies).map(([name, version]) => ({ section, name, version }));
  });
}

export function assertCompanionPackageRegistry() {
  const rootManifest = readJson(join(root, "package.json"));
  const packageNames = new Set(workspacePackages.map(({ manifest }) => manifest.name));
  const publicPackageSet = new Set(publicPackages);

  assert(!publicPackageSet.has("@nsealr/dev-signer"), "@nsealr/dev-signer must stay private");
  assert(privatePackages.includes("@nsealr/dev-signer"), "@nsealr/dev-signer must be registered as private");

  for (const { dir, manifest } of workspacePackages) {
    const expectedName = `@nsealr/${dir}`;
    assert.equal(manifest.name, expectedName, `packages/${dir}/package.json name must match its directory`);
    assert.equal(manifest.version, rootManifest.version, `${manifest.name} must use the synchronized root version`);

    if (manifest.private === true) {
      assert.equal(manifest.publishConfig, undefined, `${manifest.name} must not publish while private`);
    } else {
      assert.deepEqual(
        manifest.publishConfig,
        { access: "public", provenance: true },
        `${manifest.name} must declare public npm provenance`
      );
    }

    if (publicPackageSet.has(manifest.name)) {
      assertNoPrivatePackageReferences(manifest, `${manifest.name} package manifest`);
      for (const dependency of workspaceDependencyEntries(manifest, ["dependencies", "peerDependencies", "optionalDependencies"])) {
        if (!dependency.name.startsWith("@nsealr/")) continue;
        assert(
          packageNames.has(dependency.name),
          `${manifest.name} ${dependency.section}.${dependency.name} must reference a workspace package`
        );
        assert(
          publicPackageSet.has(dependency.name),
          `${manifest.name} production ${dependency.section}.${dependency.name} must be public, not private/test-only`
        );
        assert.equal(
          dependency.version,
          "workspace:*",
          `${manifest.name} ${dependency.section}.${dependency.name} must use workspace:* before packing`
        );
      }
    }
  }
}

export function assertPublicPackageTarball(packageName, tarball, expectedManifest) {
  const contents = capture("tar", ["-tzf", tarball]);
  assert(contents.includes("package/package.json\n"), `${packageName} tarball must include package.json`);
  assert(contents.includes("package/README.md\n"), `${packageName} tarball must include README.md`);
  assert(contents.includes("package/dist/index.js\n"), `${packageName} tarball must include dist/index.js`);
  assert(contents.includes("package/dist/index.d.ts\n"), `${packageName} tarball must include dist/index.d.ts`);
  assert(!contents.includes("package/src/"), `${packageName} tarball must not include source or tests`);

  const manifest = JSON.parse(capture("tar", ["-xOf", tarball, "package/package.json"]));
  assert.equal(manifest.name, packageName);
  assert.equal(manifest.version, expectedManifest.version);
  assert.equal(manifest.private, undefined, `${packageName} public tarball must not be private`);
  assertNoWorkspaceProtocols(manifest);
  assertNoPrivatePackageReferences(manifest, `${packageName} packed manifest`);
}
