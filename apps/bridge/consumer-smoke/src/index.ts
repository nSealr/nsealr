import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

type PackageManifest = {
  name?: unknown;
  publishConfig?: {
    access?: unknown;
  };
};

function readPackageManifest(path: string): PackageManifest {
  return JSON.parse(readFileSync(path, "utf-8")) as PackageManifest;
}

function workspaceRoot(): string {
  return join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
}

function collectPublicPackages(): string[] {
  const packagesRoot = join(workspaceRoot(), "packages");
  const packageNames = readdirSync(packagesRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => readPackageManifest(join(packagesRoot, entry.name, "package.json")))
    .filter((manifest) => manifest.publishConfig?.access === "public")
    .map((manifest) => {
      if (typeof manifest.name !== "string") {
        throw new Error("public package manifest must declare a name");
      }
      return manifest.name;
    })
    .sort();
  assert(packageNames.length > 0, "consumer smoke must discover public packages from manifests");
  assert(!packageNames.includes("@nsealr/dev-signer"), "consumer smoke must not import test-only dev signer");
  return packageNames;
}

const publicPackages = collectPublicPackages();

for (const packageName of publicPackages) {
  const module = await import(packageName);
  assert(Object.keys(module).length > 0, `${packageName} must expose a public entrypoint`);
}

const protocol = await import("@nsealr/protocol");
const core = await import("@nsealr/core");
const browserProvider = await import("@nsealr/browser-provider");
const clientBrowser = await import("@nsealr/client/browser");
const clientIdentity = await import("@nsealr/client/client-identity");
const sdk = await import("@nsealr/sdk");
const sdkBrowser = await import("@nsealr/sdk/browser");

assert.equal(protocol.validateRequest({
  version: 1,
  request_id: "consumer-smoke-get-public-key",
  method: "get_public_key"
}).ok, true);

assert.equal(core.computeEventId({
  pubkey: "0".repeat(64),
  created_at: 1,
  kind: 1,
  tags: [],
  content: "consumer smoke"
}).length, 64);

assert.equal(clientIdentity.parseLocalClientIdentity({
  surface: "browser_extension",
  origin: "https://example.com",
  app_name: "Package Consumer Smoke",
  instance_id: "consumer-smoke"
}).origin, "https://example.com");
assert.equal(clientBrowser.NATIVE_HOST_NAME, browserProvider.NATIVE_HOST_NAME);
assert.equal(typeof clientBrowser.LocalServiceClient, "function");

const provider = browserProvider.createNip07Provider({
  client: {
    surface: "browser_extension",
    origin: "https://example.com",
    app_name: "Package Consumer Smoke",
    instance_id: "consumer-smoke"
  },
  backend: {
    getPublicKey: async () => "1".repeat(64),
    signEventRequest: async () => {
      throw new Error("consumer smoke must not contact a signer");
    }
  }
});
assert.equal(await provider.getPublicKey(), "1".repeat(64));
assert.equal(sdk.protocol.validateRequest({
  version: 1,
  request_id: "consumer-smoke-sdk-get-public-key",
  method: "get_public_key"
}).ok, true);
assert.equal(sdk.core.computeEventId({
  pubkey: "0".repeat(64),
  created_at: 1,
  kind: 1,
  tags: [],
  content: "consumer smoke sdk"
}).length, 64);
assert.equal(sdkBrowser.client.NATIVE_HOST_NAME, browserProvider.NATIVE_HOST_NAME);
assert.equal(sdkBrowser.protocol.validateRequest({
  version: 1,
  request_id: "consumer-smoke-sdk-browser-get-public-key",
  method: "get_public_key"
}).ok, true);
assert.deepEqual(sdkBrowser.qr.decodeQrEnvelope(sdkBrowser.qr.encodeQrEnvelope({
  version: 1,
  request_id: "consumer-smoke-sdk-browser-qr",
  method: "get_public_key"
})), {
  version: 1,
  request_id: "consumer-smoke-sdk-browser-qr",
  method: "get_public_key"
});

console.log("nSealr package consumer smoke passed");
