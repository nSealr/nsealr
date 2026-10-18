# QR Envelope v0

The first QR envelope is intentionally simple.

## Format

```text
nsealr1:<base64url-json>
nsealr1a:<payload-sha256-hex>:<index>/<total>:<base64url-json-chunk>:<frame-checksum-hex16>
```

- Static prefix: `nsealr1:`.
- Animated frame prefix: `nsealr1a:`.
- Static payload: unpadded base64url of UTF-8 JSON.
- Animated payload: the same unpadded base64url JSON split across ordered
  frame chunks.
- Compression: none in v0.

## Decoding

1. Require the `nsealr1:` prefix.
2. Decode unpadded base64url payload.
3. Parse UTF-8 JSON.
4. Validate the decoded object against the relevant request or response schema.
5. Enforce the nSealr v0 implementation safety profile before review or
   signing.

Static QR payloads whose decoded JSON exceeds
`max_static_qr_decoded_json_bytes` are rejected in v0. The base64url payload is
unpadded; padded payloads are rejected.

Encoders must apply the same decoded JSON byte limit before emitting a static
QR envelope. v0 does not silently produce oversized static QR payloads; larger
valid requests or responses must use the animated frame set.

Animated QR frames use the `nsealr1a:` prefix and are decoded as a complete
frame set:

1. Require at least one frame.
2. Require every frame to use the same 32-byte lowercase hex decoded JSON
   SHA-256 digest and the same total frame count.
3. Require `index` to be one-based, unique, contiguous, and no greater than the
   declared total.
4. Require every chunk to be unpadded base64url, non-empty, and no longer than
   `max_animated_qr_frame_payload_chars`.
5. Verify each frame checksum, computed as the first 16 lowercase hex
   characters of SHA-256 over
   `nsealr1a:<digest>:<index>/<total>:<chunk>`.
6. Concatenate chunks by index, decode the resulting unpadded base64url payload,
   require decoded JSON bytes no larger than
   `max_animated_qr_decoded_json_bytes`, and require the decoded-byte SHA-256 to
   match the frame digest.
7. Parse UTF-8 JSON and validate the decoded object against the relevant
   request or response schema.

`max_animated_qr_frame_count` bounds total memory and scan time. Animated QR is
for v0 payloads that are valid after schema validation but do not fit the
static QR decoded-JSON byte limit, especially signed responses. It is not a way
to bypass request, event, tag, content, or response validation.

## Security Notes

The QR envelope provides transport framing, not trust. The signer must still
parse the request, compute the event id, render review where possible, require
approval, and sign only after approval.
