# NIP-46 Active Session v0

This contract defines the nSealr active NIP-46 relay session that begins where
`nsealr-nip46-session-lifecycle-v0` (the `approved_pending_ack` checkpoint) ends.

Unlike the checkpoint, this format records an ACTIVE session: connect has been
acknowledged, a NIP-44 conversation key has been derived (in memory), a relay is
open, and session state is persisted. It never persists secret material.

## Phases

| `phase` | Meaning | `opens_relay` | `derives_nip44_key` | `dispatches_signer` |
| --- | --- | --- | --- | --- |
| `connect_ack` | Remote signer acknowledged connect; relay open; NIP-44 derived; not yet dispatching | true | true | false |
| `session_active` | Session live; sign requests may be dispatched | true | true | true |
| `session_closed` | Relay closed; session terminated | false | false | false |

`acknowledges_connect` is true in every phase. `persists_session_state` is true.

## Required Fields

| Field | Rule |
| --- | --- |
| `name` | Stable vector name matching the fixture filename. |
| `format` | Exactly `nsealr-nip46-session-active-v0`. |
| `phase` | One of `connect_ack`, `session_active`, `session_closed`. |
| `client_pubkey` / `remote_signer_pubkey` | Lowercase 32-byte x-only hex. |
| `relays` | Non-empty normalized unique `wss://` relay URL list. |
| `connect_digest` | Lowercase 32-byte digest matching the source checkpoint. |
| `approved_permissions` | Kind-scoped approved permission subset. |
| `nip44` | Session encryption-mode descriptor `{ event_kind: 24133, payload_encrypted: true, version: 2 }`. See "NIP-44 Envelope" below. |
| `persists_session_state` | Exactly `true`. |
| `persisted_state` | `{ fields: [...], contains_secret_material: false }`. |
| `acknowledges_connect` / `derives_nip44_key` / `opens_relay` / `dispatches_signer` | Booleans fixed per phase — see the phase table above. |
| `creates_grants` | Boolean (free; T2 sessions create no grants). |
| `secret_value_stored` / `contains_secret_material` / `stores_production_secrets` | Always `false`. |
| `secret_present` | Boolean copied from the source connect review. See "secret_present" below. |
| `scope` | Non-empty string that MUST mention `NIP-44`, `relay`, `persist`, and `secret material`. |

## Required Safety Boundary

- It must not contain secret values, NIP-44 keys, private keys, mnemonics,
  `nsec` values, seeds, or passphrases.
- `secret_value_stored`, `contains_secret_material`, and
  `stores_production_secrets` must be `false`.
- `persisted_state.fields` must not include any secret field name
  (`secret`, `shared_secret`, `session_secret`, `nip44_key`, ...).
- Phase side-effect flags must match the phase table above exactly.

## NIP-44 Envelope

The `nip44` field is a **session-level descriptor only**: it records that this
session encrypts its NIP-46 traffic as NIP-44 v2 payloads carried in kind-24133
events. It deliberately does **not** re-specify the relay-event structure (the
single `p` tag, the encrypted `content`, id/signature) — that envelope is already
the separate, frozen contract `nsealr-nip46-relay-event-envelope-v0` (see
`vectors/nip46-relay-events/`). Downstream consumers (T2 companion, T6) validate
individual relay events against that contract; this session format only declares
the mode, to avoid duplicating envelope validation in two places.

## secret_present

`secret_present` is copied verbatim from the source connect review and records
**only** whether the original NIP-46 connect carried a secret token. It is an
audit-trail bit, not a storage statement: it never implies the secret is held by
the session. The secretless invariant is enforced independently
(`secret_value_stored`, `contains_secret_material`, `stores_production_secrets`
are always false; `persisted_state.fields` carries no secret field name).

## Source Binding

A fixture wraps the session with `format: nsealr-nip46-session-active-vector-v0`
and `source_session_vector` pointing under `vectors/nip46-sessions/`. The active
session's `client_pubkey`, `remote_signer_pubkey`, `connect_digest`, `relays`, and
`secret_present` must match that source `approved_pending_ack` checkpoint, proving
continuity.

## Schema vs validators

`schemas/nip46-session-active-v0.schema.json` is a **coarse structural gate**. The
authoritative rules are the `verify_specs.py` checks (and the companion
`parseNip46SessionActive`): per-phase flag values, the `scope` substrings, the
secret-field exclusion in `persisted_state.fields`, relay normalization/uniqueness,
and source binding are enforced there, not all in the schema.
