# @nsealr/qr

Static and animated QR envelope helpers for nSealr requests and responses.

## Purpose

- Encode and decode v0 `nsealr1:` static QR envelopes.
- Encode and decode v0 `nsealr1a:` animated QR frame sets.
- Enforce shared QR byte limits, frame digests, frame checksums, and malformed
  payload rejection before JSON parsing.
- Stay browser-runtime safe so `@nsealr/sdk/browser` can expose the same QR
  helpers without Node `Buffer` or builtin module dependencies.

## Example

```ts nsealr-readme-example
import assert from "node:assert/strict";
import { decodeQrEnvelope, encodeQrEnvelope } from "@nsealr/qr";

const request = {
  version: 1,
  request_id: "readme-qr",
  method: "get_public_key"
};

assert.deepEqual(decodeQrEnvelope(encodeQrEnvelope(request)), request);
```

## Boundary

This package transports already-validated payloads. It does not store secrets,
perform signing, compress payloads, use fountain codes, or define signer policy.
