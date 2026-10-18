# Signing Response Protocol v0

Every response echoes the request version and request id.

The echoed `request_id` must use the same nSealr v0 request-id profile as
requests; hosts must reject malformed response ids before interpreting result
payloads.

## Successful Capabilities Response

```json
{
  "version": 1,
  "request_id": "req-capabilities-esp32-s3-scaffold",
  "ok": true,
  "result": {
    "capabilities": {
      "device": {
        "name": "nSealr ESP32-S3 USB Signer Scaffold",
        "firmware": "nsealr-esp32-s3-usb-signer",
        "hardware": "esp32-s3-devkitc-1"
      },
      "protocols": ["nsealr.signing.v0", "nsealr.serial-frame.v0"],
      "methods": ["get_capabilities", "get_signing_status", "get_public_key", "sign_event"],
      "transports": ["usb-serial-jtag"],
      "signing_enabled": false,
      "requires_physical_approval": true
    }
  }
}
```

`signing_enabled: false` means the device may advertise the future signing
method while still rejecting `sign_event` until storage, trusted review, and
physical approval gates are implemented.

## Successful Signing Status Response

```json
{
  "version": 1,
  "request_id": "req-signing-status-esp32-s3-scaffold",
  "ok": true,
  "result": {
    "signing_status": {
      "signing_enabled": false,
      "missing_gates": [
        "runtime_signing_feature",
        "trusted_review_display",
        "physical_approval_controls",
        "unicode_review_rendering",
        "key_provisioning",
        "source_public_key_proof",
        "secure_boot",
        "flash_encryption",
        "debug_lock",
        "companion_signed_output_verification"
      ],
      "development_accepted_gates": [
        "parser_limits",
        "trusted_review_display",
        "physical_approval_controls",
        "approval_digest_binding"
      ]
    }
  }
}
```

`missing_gates` names the runtime readiness gates that still block real
`sign_event` for that device profile. The ESP32-S3 scaffold omits
`parser_limits` and `approval_digest_binding` because those host-core gates are
already implemented and tested, but it must keep `signing_enabled: false` until
the remaining gates are satisfied and the signing feature is intentionally
enabled. `unicode_review_rendering` stays missing while the current display
path uses development `U+XXXX` fallback instead of a production-accepted
Unicode review policy. A device must not return `signing_enabled: true` while
`missing_gates` is non-empty; hosts must reject that contradictory status
instead of treating it as signing-ready. Conversely, a device that returns
`signing_enabled: false` must report at least one `missing_gates` entry so the
disabled state has a deterministic reason. `missing_gates` and
`development_accepted_gates` must not contain duplicate entries.

`development_accepted_gates` names gates with deterministic implementation
coverage or manual development evidence in the current scaffold. It is not a
production security claim. A gate may appear in both `development_accepted_gates`
and `missing_gates` when the current board has development acceptance evidence
but production acceptance, provisioning, or hardening is still incomplete.

## Production Signing-Enabled Contract

A device is *production signing-enabled* only when every runtime readiness gate in the
canonical gate set is satisfied. Concretely:

- `get_signing_status` returns `signing_enabled: true` with an **empty** `missing_gates`
  array. `signing_enabled: true` together with a non-empty `missing_gates` is a
  contradiction and hosts must reject it.
- `get_capabilities` returns `signing_enabled: true` and keeps
  `requires_physical_approval: true`; no nSealr signer may enable signing without physical
  approval.
- `sign_event` returns a verified signed event (see *Successful Event Signing Response*)
  instead of the `signing_disabled` error.

`development_accepted_gates` stays informational (development evidence) and is never the
production-ready signal; the authoritative signal is `signing_enabled: true` with an empty
`missing_gates`. The canonical enabled fixtures are
`examples/response-get-capabilities-esp32-s3-enabled.json` and
`examples/response-get-signing-status-esp32-s3-enabled.json`, contrasted with the matching
`*-esp32-s3-scaffold` disabled fixtures.

## Successful Public Key Response

```json
{
  "version": 1,
  "request_id": "req-pubkey-1",
  "ok": true,
  "result": {
    "public_key": "<64 lowercase hex chars>"
  }
}
```

## Successful Event Signing Response

```json
{
  "version": 1,
  "request_id": "req-kind-1-basic",
  "ok": true,
  "result": {
    "event": {
      "id": "<64 lowercase hex chars>",
      "pubkey": "<64 lowercase hex chars>",
      "created_at": 1710000000,
      "kind": 1,
      "tags": [],
      "content": "nSealr fixture: basic kind 1 event.",
      "sig": "<128 lowercase hex chars>"
    }
  }
}
```

The companion must verify:

- response `request_id` matches the request;
- signed event shape remains inside the nSealr v0 implementation limit
  profile, including integer safety plus content and tag resource limits;
- signed event fields match the requested template;
- event id matches NIP-01 canonical serialization;
- signature verifies against event id and public key.

## Error Response

```json
{
  "version": 1,
  "request_id": "req-kind-1-basic",
  "ok": false,
  "error": {
    "code": "user_rejected",
    "message": "User rejected the signing request.",
    "retryable": true
  }
}
```

Error responses must not include `result`.

Scaffolded devices that advertise `sign_event` for forward compatibility but
have not implemented trusted review, physical approval, and signing yet must
return an explicit protocol error:

```json
{
  "version": 1,
  "request_id": "req-kind-1-basic",
  "ok": false,
  "error": {
    "code": "signing_disabled",
    "message": "Signing is disabled until trusted review and physical approval are implemented.",
    "retryable": false
  }
}
```
