# @nsealr/nip46

NIP-46 metadata helpers and a bounded client session manager for nSealr Bridge.

## Purpose

- Convert already-decrypted `get_public_key` and `sign_event` payloads into
  nSealr requests, and deterministic local `ping` / `switch_relays`
  responses.
- Parse `connect` messages into review intents, deterministic review pages, and
  digest-bound local approval artifacts.
- Parse `bunker://` and `nostrconnect://` connection URIs into descriptor-only
  metadata without echoing shared secrets.
- Verify already decrypted `nostrconnect://` token responses against the
  original local token secret without echoing or storing that secret.
- Parse NIP-46 `kind:24133` relay event envelopes into sender/recipient/content
  metadata without decrypting NIP-44 content or opening relay connections.
- Evaluate metadata-only relay request and response steps after a future
  NIP-44 layer has supplied plaintext, returning deterministic bridge decisions
  or response-shape metadata. Public-key and signed-event response results identify the user separately
  from the relay transport author and can be bound to an explicit expected user, and signed-event response results must have
  a valid NIP-01 event id and BIP-340 signature before later session code can
  accept them. Connect ack and switch-relays responses remain metadata-only,
  and auth challenge responses expose only safe http(s) URL metadata without
  credentials or fragments for later UI, without relay I/O, signer dispatch,
  grant creation, URL opening, or session persistence. Signed relay-event envelopes
  are NIP-01 id checked and BIP-340 verified.
- Render auth challenge URL metadata into deterministic review pages and
  digest-bound approval artifacts without opening the URL, acknowledging
  `connect`, creating grants, opening relays, dispatching signers, storing
  secrets, or persisting session state.
- Parse reviewed-but-not-active NIP-46 session lifecycle checkpoints that bind
  client/signer pubkeys, relays, connect digest, approval time, expiry, and an
  approved permission subset while keeping NIP-44 derivation, `connect`
  acknowledgement, relay I/O, grant creation, signer dispatch, secret storage,
  and session persistence disabled.
- Create the same reviewed-but-not-active checkpoint from a canonical connect
  review, matching connect approval artifact, explicit client pubkey, relay
  list, expiry, and approved permission subset without acknowledging `connect`
  or starting a relay session.
- Evaluate pending-session request gates for `approved_pending_ack` checkpoints,
  binding relay sender/recipient metadata and decrypted request permissions
  while returning deterministic `connect_ack_pending` errors instead of signer
  dispatch.
- Parse read-only nSealr policy files used by the CLI and tests.
- Keep requested-permission parsing separate from approved-permission parsing
  so broad `sign_event` can be reviewed as metadata but cannot authorize a
  signer route.
- Enforce permission checks before signer routing.

## Example

```ts nsealr-readme-example
import assert from "node:assert/strict";
import { decideNip46BridgeAction } from "@nsealr/nip46";

const eventTemplate = {
  created_at: 1_710_000_000,
  kind: 1,
  tags: [],
  content: "NIP-46 bridge input"
};
const decision = decideNip46BridgeAction({
  id: "readme-nip46",
  method: "sign_event",
  params: [JSON.stringify(eventTemplate)]
}, [{
  method: "sign_event",
  parameter: "1",
  event_kind: 1
}]);

assert.equal(decision.type, "signer_request");
```

## Boundary

Connection URI parsing is intentionally non-committal: it validates official
NIP-46 token shape, relays, client metadata, and requested permissions, but it
returns only `secret_present` instead of the secret value.

Connection token response verification is also non-committal. It checks that a
decrypted `nostrconnect://` response returned the expected local token secret,
then returns only secretless metadata: client pubkey binding, discovered remote
signer pubkey, relays, requested permissions, and false side-effect flags. It
does not open relays, derive NIP-44 keys, acknowledge `connect`, create grants,
dispatch signers, store secrets, or persist session state.

Connect approval is also non-committal. The approval artifact proves that a
specific connect review digest was manually confirmed, but it still records
`acknowledges_connect: false`, `creates_grants: false`, `opens_relay: false`,
and `persists_session_state: false`.

Relay event envelope parsing is also non-committal. It validates the event kind,
sender pubkey, exactly one recipient `p` tag, opaque encrypted content, and
tag arrays made only of strings. When signed fields are present, it verifies the
NIP-01 event id and BIP-340 relay event signature. It does not decrypt NIP-44
content, open relays, persist grants, acknowledge `connect`, or reach signer
I/O. Those layers remain blocked on separate policy and session gates.

Relay step evaluation starts from an envelope and an already decrypted message.
Request steps reuse the same request validation, permission checks, and bridge
decision logic as local decrypted payload handling, including local
`switch_relays` `null` no-change responses that do not open or switch relay
transports. Response steps shape-check NIP-46 response messages and signed-event
result payloads, verify signed-event result ids/signatures, and optionally bind
public-key/signed-event result pubkeys to `expected_user_pubkey`. The v1 response
step reports `result_pubkey` and `result_pubkey_bound_to_expected_user`; equality
with the transport author is neither required nor an account-selection proof. Connect ack
responses are accepted only as `result: "ack"` metadata and do not activate a
session. Switch-relays responses are accepted only as normalized relay-list or
`null` no-change metadata and do not switch transports. Auth challenge
responses are accepted only as `result: "auth_url"` plus a safe http(s) URL
without credentials or fragments in `error`; the package returns that URL as
metadata and does not open it. Relay steps still do not decrypt NIP-44 content,
open relays, acknowledge `connect`, create grants, dispatch a signer or persist session state.

Auth challenge review is the next manual boundary after response-step
normalization. The package renders the remote signer pubkey, client pubkey, and
auth URL into deterministic pages, computes `auth_challenge_digest`, and writes
approval artifacts only when that digest is supplied back. The approval still
records no URL opening, relay I/O, `connect` acknowledgement, grant creation,
signer dispatch, secret storage, or session persistence.

Session lifecycle parsing is a checkpoint contract, not a session engine. It
accepts only the `approved_pending_ack` phase and rejects embedded secret
material, NIP-44 key derivation, relay opening, `connect` acknowledgement,
grant creation, signer dispatch, production secret storage, or persisted
session state. Checkpoint creation validates the review/approval digest pair
and approved-permission subset before returning the same secretless object.

Session request gate evaluation is still non-enabling. It checks that the relay
event sender matches the reviewed client pubkey, that the recipient `p` tag
matches the remote-signer pubkey, that the session has not expired, and that the
decrypted request has a valid permission requirement. The result is a
`connect_ack_pending` NIP-46 error with no session-permission use, relay I/O,
grant creation, signer dispatch, or persistence.

## Runtime session boundary

`Nip46SessionManager` is separate from the metadata helpers. Its caller must
supply an authenticated `remoteSignerPubkey` and a client transport secret.
After a direct connect ack it calls `get_public_key`, validates the returned
curve point and optional `expectedUserPubkey`, and exposes `userPubkey` only
when active. Each signed response must match the submitted template and that
user key, with valid event ID and signature. Transport and user keys may differ.
Changing accounts requires a new manager and caller-owned account selection.
The manager does not grant device approval or establish browser origin permission.

Incoming responses must have the configured transport author, valid signature,
kind 24133, and exactly one matching recipient tag. Unauthenticated, ambiguous,
unknown-ID and replayed responses cannot consume a pending request. IDs contain
a fresh random manager namespace and a counter that never resets on retry;
`randomId`, when supplied, adds only a bounded test suffix. JSON rejects duplicate
members, escaped duplicate names, trailing data and depth above 32. Raw plaintext
is limited to 1,024 UTF-8 bytes, encrypted content to 2,048, and tags to 16 arrays
of at most eight fields of 64 UTF-8 bytes each.

`requestTimeoutMs` defaults to 30,000 (valid range 1..300,000).
`maxPendingRequests` defaults to 32 (valid range 1..256); unsettled adapter
publications have a separate count with the same cap even after logical timeout.
A response succeeds after both publication and authenticated response complete;
the timeout and close remain effective if either never settles. Only one
subscription acquisition can remain unresolved. A timed-out acquisition blocks
retry until it settles; late subscription handles are closed. Other connect
failures return to idle and permit retry. `close()` is terminal, cancels requests,
closes the transport and clears the manager's private copy of its client secret.
The caller's original key buffer is unchanged. JavaScript cannot guarantee wiping
runtime or cryptographic-library copies.

`NostrToolsRelay` provides real relay I/O and `InMemoryRelay` provides test I/O.
The manager independently enforces author binding even if an adapter ignores its
filter. This package holds client transport secrets in RAM; user signing keys
remain at the remote signer. Metadata `SessionStore` records contain no secret
and do not restore an authenticated manager. Token onboarding, auth challenge UI,
relay switching and external-client compatibility are not implemented by this
manager. The Docker relay harness exercises the in-repository signer only.
