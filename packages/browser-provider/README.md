# @nsealr/browser-provider

NIP-07 provider adapter for future nSealr browser-extension packaging.

## Purpose

- Expose `getPublicKey` and `signEvent` behavior over an injected companion
  backend.
- Bind every call to explicit client identity.
- Convert event templates into nSealr signer requests.
- Provide a local-service backend adapter for authorized account-route
  selection, signer-request dispatch, and deterministic signer-unavailable
  responses when no signer route dispatcher is configured.
- Provide a browser native-messaging local-service client adapter over an
  explicit `sendNativeMessage` function and shared native host name while
  relying on `@nsealr/client` for response validation, request-id correlation,
  deterministic response timeout, and request cancellation.
- Import the local-service client boundary through the reviewed
  `@nsealr/client/browser` runtime subpath, not the Node-capable client root.
- Verify signed responses before returning them to `window.nostr` callers.

## Example

```ts nsealr-readme-example
import assert from "node:assert/strict";
import {
  NATIVE_HOST_NAME,
  createBrowserNativeMessagingLocalServiceClient,
  createNip07Provider
} from "@nsealr/browser-provider";

const publicKey = "3".repeat(64);
const service = createBrowserNativeMessagingLocalServiceClient({
  sendNativeMessage: (hostName, message) => {
    assert.equal(hostName, NATIVE_HOST_NAME);
    return {
      version: 1,
      request_id: message.request_id,
      ok: true,
      result: {
        service: {
          protocol: "nsealr-local-service-v0",
          name: "nsealr-companion-service",
          operations: [
            "service_status",
            "request_pairing",
            "select_account_route",
            "validate_signer_request",
            "dispatch_signer_request",
            "verify_signer_response"
          ],
          requires_pairing: true,
          stores_production_secrets: false
        }
      }
    };
  }
});
const provider = createNip07Provider({
  client: {
    surface: "browser_extension",
    origin: "https://example.com",
    app_name: "Example client"
  },
  backend: {
    getPublicKey: async () => publicKey,
    signEventRequest: async (request) => ({
      version: 1,
      request_id: request.request_id,
      ok: false,
      error: {
        code: "signing_disabled",
        message: "No signer connected",
        retryable: false
      }
    })
  },
  nextRequestId: () => "readme-provider-sign"
});

assert.equal((await service.serviceStatus("readme-native-status")).ok, true);
assert.equal(await provider.getPublicKey(), publicKey);
await assert.rejects(
  provider.signEvent({
    created_at: 1_710_000_000,
    kind: 1,
    tags: [],
    content: "provider request"
  }),
  /No signer connected/u
);
```

## Boundary

This package is not a browser extension by itself. It stores no browser-side
production keys, implements no local signing, persists no grants, and does not
implement NIP-04, NIP-44, relay sessions, signer transport drivers, extension
packaging, or native-host installation.
Timeout and cancellation are deliberately delegated to `@nsealr/client` so this
package stays a browser API adapter instead of a second local-service client
implementation.
