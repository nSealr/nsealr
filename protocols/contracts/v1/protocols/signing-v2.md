# Device signing contract v2

The device JSON contract is `nsealr.signing.v2`, numeric `version: 2`.
The containing `contracts/v1` directory identifies the artifact inventory.
It does not select the wire revision. The internal consuming authorization
domain remains `nsealr.authorization.v1`. External Nostr serialization and
cryptographic domains are unchanged.

Requests have exactly `version`, `request_id`, `method`, and, for `sign_event`
only, `params`. IDs are 1–128 ASCII characters from `[A-Za-z0-9._:-]`.
`get_capabilities` and `get_public_key` have no params. `sign_event` has exactly
`params.event_template` with `created_at`, `kind`, `tags`, `content`; supplied
`id`, `pubkey`, `sig` and unknown members reject. Timestamps are unsigned decimal integer tokens at most 9007199254740991;
kinds are unsigned decimal integer tokens in 0–65535, preserving S03 grammar. Decoded duplicate object keys,
invalid UTF8/Unicode scalars, BOM, trailing data and unsupported methods reject.
Numeric 1, unknown revisions and `get_signing_status` reject without fallback.
The versioned request/response JSON Schemas supplement original-byte parsing.

Successful responses have exactly `version`, `request_id`, `ok: true`, `result`.
The result has exactly one of `capabilities`, `public_key`, `event`. Error
responses have `ok: false`, `error` and no result. Their error record is exactly
`code`, `message`, `retryable`. A capabilities result is the strict full or
reference record in [profile-capabilities-v1.md](profile-capabilities-v1.md).
A signed event retains the independent Nostr canonicalization/ID/BIP340
verification rules. Host verification binds the expected request ID, account
public key, complete event template and independent signature verification.
A reported capability, selected route or host review acknowledgement never
approves signing. Production remains `signing_disabled`/`SigningUnavailable`;
the fixture backend remains private and test-only.

The existing serial-frame v0 and QR-envelope v0 byte grammars remain unchanged.
Their Base64URL, SHA256/truncated SHA256 checksums, frame counts and original
decoded-byte ceilings apply to the new JSON payload. The QR prefix `nsealr1:`
does not mean JSON numeric version 1. Encoded payloads, frame checksums,
request-bound diagnostic digests and paired transcripts change together.
Independent Nostr event/canonical/signature bytes and key/import/backup vectors
do not change. A larger metadata descriptor cannot increase an adapter's
capacity: emit a complete representable reference or report discovery unavailable.

Finite local operation limits remain no greater than the existing implementation
limits: Bridge request JSON 704 bytes, content 512 UTF8 bytes, 16 tags, 8 fields
per tag, 64 UTF8 bytes per field and 4096 aggregate tag bytes. Other engines may
declare different finite limits within their existing actual ceilings. The
effective route intersects all applicable method/transport constraints before
any operation write. Original JSON whitespace counts toward the raw byte limit.
