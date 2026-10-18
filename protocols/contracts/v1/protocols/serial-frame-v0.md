# Serial Frame v0

The first serial frame is designed for USB CDC, UART, and host-side firmware
simulators. It frames one JSON request or response envelope as one ASCII line.

## Format

```text
nsealr1f:<type>:<base64url-json>:<checksum>\n
```

- Prefix: `nsealr1f:`.
- Type: `request`, `response`, or `error`.
- Payload: unpadded base64url of UTF-8 JSON.
- Checksum: first 16 lowercase hexadecimal characters of SHA-256 over
  `<type>:<base64url-json>`.
- Terminator: one newline byte.

## Decoding

1. Require the `nsealr1f:` prefix.
2. Split the remaining frame into exactly `type`, `payload`, and `checksum`.
3. Require a supported type: `request`, `response`, or `error`.
4. Require unpadded base64url payload characters.
5. Recompute and compare the checksum before JSON parsing.
6. Decode payload as UTF-8 JSON.
7. Validate decoded JSON against the relevant request or response schema.
8. Enforce the nSealr v0 implementation safety profile before review or
   signing.

Frames larger than `max_serial_frame_bytes` are rejected in v0. Payloads remain
unpadded base64url. Unknown frame types are rejected before decoded JSON is
handled as a request, response, or error payload.

## Security Notes

The checksum only detects accidental framing or transport corruption. It is not
authentication, authorization, or a substitute for event-id and Schnorr
verification.
