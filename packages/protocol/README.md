# @nsealr/protocol

Shared nSealr request, response, capability, signing-status, and resource-limit
validation, plus small browser-safe encoding helpers for transport envelopes.

## Purpose

- Validate nSealr v0 request and response shapes.
- Centralize host-side copies of constrained-signer implementation limits.
- Reject unsafe `sign_event` templates before transport or signer routing.
- Validate capability and signing-status diagnostics.
- Share deterministic JSON-to-UTF-8 and unpadded base64url helpers used by QR
  and serial framing packages without relying on Node runtime globals.

## Example

```ts nsealr-readme-example
import assert from "node:assert/strict";
import { validateRequest } from "@nsealr/protocol";

const validation = validateRequest({
  version: 1,
  request_id: "readme-get-public-key",
  method: "get_public_key"
});

assert.equal(validation.ok, true);
```

## Boundary

These limits are nSealr v0 safety limits, not Nostr protocol limits. This
package does not perform signing and must be used before any companion access
surface contacts a signer route. Its encoding helpers are low-level transport
primitives; callers should prefer `@nsealr/qr` or `@nsealr/framing` for complete
envelope formats.


`parseStrictJson(text, maxBytes)` checks raw UTF-8 byte length, JSON syntax,
duplicate object members (including escaped aliases), trailing data and a maximum
nesting depth of 32 containers. `maxBytes` is an integer in 1..1,048,576. It returns
JSON values without performing protocol schema validation; callers must still
validate their request or response shape.
