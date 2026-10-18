# NIP-46 Session Lifecycle v0

This contract defines the first nSealr checkpoint between reviewed NIP-46
`connect` metadata and a future encrypted relay session.

It is intentionally not an active session format. A
`nsealr-nip46-session-lifecycle-v0` object records only that a specific
connect review digest was approved, which client and remote signer pubkeys are
involved, which relay URLs are expected later, which requested permissions were
reviewed, and which approved permissions remain in scope.

These are nSealr v0 implementation-safety limits for pre-production companion
work. They are not NIP-46 protocol limits and must not be used to claim full
Nostr Connect support.

## Required Fields

| Field | Rule |
| --- | --- |
| `name` | Stable vector name matching the fixture filename. |
| `format` | Exactly `nsealr-nip46-session-lifecycle-v0`. |
| `phase` | Exactly `approved_pending_ack`. |
| `client_pubkey` | Lowercase 32-byte x-only client public key hex. |
| `remote_signer_pubkey` | Lowercase 32-byte x-only remote signer public key hex. |
| `relays` | Non-empty normalized unique `wss://` relay URL list. |
| `connect_digest` | Lowercase 32-byte digest matching the source connect review. |
| `approved_at` | Safe non-negative integer timestamp. |
| `expires_at` | Safe non-negative integer timestamp greater than `approved_at`. |
| `requested_permissions` | Reviewed permissions copied from the connect intent. |
| `approved_permissions` | Approved subset of the requested permissions. |
| `secret_present` | Boolean copied from the connect review. It records presence only. |
| `scope` | Human-readable statement of this checkpoint's disabled side effects. |

The checkpoint also carries explicit false side-effect flags. These flags make
the boundary machine-checkable and prevent future code from silently treating a
reviewed approval artifact as an active session.

Specs fixtures may wrap a session object with
`format: nsealr-nip46-session-lifecycle-vector-v0` and
`source_connect_review_vector` metadata so conformance tests can prove the
session binds back to the reviewed connect vector. That source path is fixture
metadata, not a field of the runtime session object.

## Required Safety Boundary

- It must not contain secret values, NIP-44 keys, private keys, mnemonics,
  `nsec` values, seeds, or passphrases.
- It must keep `acknowledges_connect: false`.
- It must keep `derives_nip44_key: false`.
- It must keep `opens_relay: false`.
- It must keep `creates_grants: false`.
- It must keep `dispatches_signer: false`.
- It must keep `stores_production_secrets: false`.
- It must keep `persists_session_state: false`.

The only v0 phase is `approved_pending_ack`. Full relay I/O, NIP-44
encryption/decryption, connect acknowledgement, signer dispatch, grant storage,
and persisted session state require later vectors and downstream implementation
work before they can be treated as supported behavior.

## Permission Rule

`requested_permissions` preserves the reviewed request from the connect intent.
`approved_permissions` is the narrower permission set the device/user approved.
Every approved permission must match at least one requested permission. Broad
requested `sign_event` metadata can be reviewed, but approved `sign_event`
permissions must remain kind-scoped before they can route to any signer.
