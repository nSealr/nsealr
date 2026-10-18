# Signing Request Protocol v0

This document defines the first nSealr signer request contract. It is the
shared protocol used by companion software, QR vaults, ESP32 signers, smartcard
adapters, and future compatible implementations.

## Envelope

Every request is a JSON object:

```json
{
  "version": 1,
  "request_id": "req-kind-1-basic",
  "method": "sign_event",
  "params": {}
}
```

Fields:

- `version`: integer protocol version. v0 documents use value `1` on the wire.
- `request_id`: caller-generated identifier that must be echoed in the response.
- `method`: requested signer method.
- `params`: method-specific object. Omitted only when the method has no
  parameters.

Unknown top-level fields are invalid in v0.

Requests must also satisfy the nSealr v0 implementation safety profile in
`implementation-limits-v0.md`. Those limits are local nSealr safety bounds
for constrained signers and are not Nostr protocol limits.

## Methods

### `get_capabilities`

Returns the signer's active protocol, method, transport, and safety flags. This
is the first request a companion should send to a directly connected device.

Request:

```json
{
  "version": 1,
  "request_id": "req-capabilities-esp32-s3-scaffold",
  "method": "get_capabilities"
}
```

### `get_public_key`

Returns the signer's active x-only secp256k1 public key as lowercase hex.

Request:

```json
{
  "version": 1,
  "request_id": "req-pubkey-1",
  "method": "get_public_key"
}
```

### `get_signing_status`

Returns the signer's current real-signing readiness state. This is a
diagnostic method for companions and test harnesses; it must not be treated as
permission to sign unless `signing_enabled` is true and every required safety
gate has been satisfied.

Request:

```json
{
  "version": 1,
  "request_id": "req-signing-status-esp32-s3-scaffold",
  "method": "get_signing_status"
}
```

### `sign_event`

Signs a Nostr event template. The host must not provide `id`, `pubkey`, or
`sig` inside `event_template`.

Request:

```json
{
  "version": 1,
  "request_id": "req-kind-1-basic",
  "method": "sign_event",
  "params": {
    "event_template": {
      "created_at": 1710000000,
      "kind": 1,
      "tags": [],
      "content": "nSealr fixture: basic kind 1 event."
    }
  }
}
```

The signer must:

1. Insert its own `pubkey`.
2. Canonically serialize `[0, pubkey, created_at, kind, tags, content]`.
3. Compute the NIP-01 event id as SHA-256 of that serialization.
4. Sign the event id with BIP-340 Schnorr over secp256k1.
5. Return the complete signed event.

The signer must reject templates that contain `id`, `pubkey`, or `sig`.
It must also reject unknown `event_template` fields, unsafe `created_at` or
`kind` integers, non-array tags, non-string tag fields, oversized tag/content
payloads, and decoded request JSON larger than the v0 implementation profile.
