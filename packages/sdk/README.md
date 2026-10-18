# @nsealr/sdk

Platform-neutral facade over curated nSealr companion packages.

Browser runtime code should import `@nsealr/sdk/browser`, which exposes only
the browser-safe provider, local-service client, and pure core/policy/protocol/
QR/review helpers.

## Boundary

- Export curated package namespaces for app, browser-extension, and companion
  integrations.
- Export a browser-safe `./browser` subpath so extension and web callers do not
  import the broader SDK root by accident.
- Keep `@nsealr/dev-signer` out of the public SDK surface.
- Keep Node-only fixture loading and host transport adapters in their own
  packages instead of importing them through this facade.
- Store no production keys, mnemonics, passphrases, grants, or browser-side
  signing material.

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
