# @nsealr/framing

Checksum-protected serial frame helpers for USB CDC and UART experiments.

## Purpose

- Encode and decode nSealr serial line frames.
- Enforce shared serial-frame byte limits.
- Reject checksum mismatches and malformed payloads deterministically.
- Stay browser-runtime safe for future WebSerial/WebUSB experiments while
  remaining outside the `@nsealr/sdk/browser` facade until that access surface
  is reviewed.

## Example

```ts nsealr-readme-example
import assert from "node:assert/strict";
import { decodeSerialFrame, encodeSerialFrame } from "@nsealr/framing";

const frame = encodeSerialFrame({
  type: "request",
  payload: {
    version: 1,
    request_id: "readme-frame",
    method: "get_public_key"
  }
});

assert.deepEqual(decodeSerialFrame(frame), {
  type: "request",
  payload: {
    version: 1,
    request_id: "readme-frame",
    method: "get_public_key"
  }
});
```

## Boundary

This package only frames bytes for transport. It does not open devices, select
routes, store keys, or sign events.

Decoded serial payload JSON rejects duplicate object members, escaped aliases,
trailing data and more than 32 nested containers. The existing 1,024-byte serial
frame limit remains; checksum validation does not replace payload validation.
