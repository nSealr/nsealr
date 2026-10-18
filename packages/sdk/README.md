# @nsealr/sdk

The sole public nSealr TypeScript package. The root and `@nsealr/sdk/browser`
expose browser-safe provider, local-service client and core/policy/protocol/QR/
review namespaces. `@nsealr/sdk/node` additionally exposes the host client,
framing and NIP-46 namespaces. Owned runtime and declarations are included in
this package; consumers do not install internal workspace packages.

The SDK stores no user identity/signing keys. Device review and approval remain
signer responsibilities. The Node NIP-46 runtime owns a bounded, in-memory
client transport key; it does not persist that key or confer signing approval.
Smartcard APIs are retired. `@nsealr/dev-signer` and fixture loaders stay private
and outside the packed production graph. Real browser, relay and attached-device
qualification remains separate from deterministic package tests.

```ts nsealr-readme-example
import assert from "node:assert/strict";
import { browserProvider, client, protocol } from "@nsealr/sdk";

const identity = client.parseLocalClientIdentity({
  surface: "browser_extension",
  origin: "https://example.com",
  app_name: "README SDK Example",
  instance_id: "readme-sdk"
});

const provider = browserProvider.createNip07Provider({
  client: identity,
  backend: {
    getPublicKey: async () => "1".repeat(64),
    signEventRequest: async () => {
      throw new Error("README example does not dispatch signer I/O");
    }
  },
  nextRequestId: () => "readme-sdk-sign"
});

assert.equal(await provider.getPublicKey(), "1".repeat(64));
assert.equal(protocol.validateRequest({
  version: 1,
  request_id: "readme-sdk-request",
  method: "get_public_key"
}).ok, true);
```

```ts nsealr-readme-example
import assert from "node:assert/strict";
import { browserProvider, client, protocol, qr } from "@nsealr/sdk/browser";

const identity = client.parseLocalClientIdentity({
  surface: "browser_extension",
  origin: "https://example.com",
  app_name: "README SDK Browser Example",
  instance_id: "readme-sdk-browser"
});

assert.equal(browserProvider.NATIVE_HOST_NAME, client.NATIVE_HOST_NAME);
assert.equal(protocol.validateRequest({
  version: 1,
  request_id: "readme-sdk-browser-request",
  method: "get_public_key"
}).ok, true);
assert.equal(identity.origin, "https://example.com");
assert.deepEqual(qr.decodeQrEnvelope(qr.encodeQrEnvelope({
  version: 1,
  request_id: "readme-sdk-browser-qr",
  method: "get_public_key"
})), {
  version: 1,
  request_id: "readme-sdk-browser-qr",
  method: "get_public_key"
});
```
