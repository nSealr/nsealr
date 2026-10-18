# S01 — Bridge identity and bounded input

Specification reviewed by coordinator `/root` on 2026-10-18 against candidate
`55bee979fff2db784c2cedbad67e24cbb1262d26`, accepted with the explicit curve-point
validation and never-reset retry-counter clarifications incorporated here. This
brief records requirements and experiments, not task completion. The canonical task state remains in the main repository's
`docs/restart/work-items.json`.

## Authority, inputs and scope

Parent: S01, five acceptance statements in graph revision 5. Authority: maintainer
restart authorization, integration `AGENTS.md`, main `AGENTS.md`, and main
`docs/restart/{development,execution,architecture}.md`. Main input inspected:
`768e8a35ae541f53f5da9c7bea7bf5c577fb474d`. Companion baseline is exactly
`13414320537d0208fc3ef8e43bd0723c98c1d5e0`.

Author: `bridge_execution`, isolated companion worktree
`/home/tux/nsealr/.restart-tools/goal/s01`, branch `restart/s01-bridge`.
The coordinator assigns a distinct specification reviewer and final security
reviewer. The author does not update the main task graph or merge its own change.

Primary protocol source: [nostr-protocol/nips at
37db639582d857e12468dcccd99b2c7f1d657da9](https://github.com/nostr-protocol/nips/tree/37db639582d857e12468dcccd99b2c7f1d657da9),
read 2026-10-18:

| File | Reviewed sections | SHA-256 of raw file |
| --- | --- | --- |
| `46.md` | Changes, Terminology, Overview, connection initiation, methods, responses, auth challenges | `e5a3c818eb3bc410541104198d4ebdce6b1720a2da00cb8e71d38ec0b72f01c1` |
| `01.md` | Event structure, canonical serialization, relay subscription filters | `b229fa210af54e4a821c0c483fba88d7dcd2b7a6f26c010b4548039919da266e` |
| `44.md` | Version 2 payload construction, authenticated decryption and size checks | `b5f89374e4e1dbdee7881e8573b4313b6a89430a9c8d518471599ae0660cf0e2` |

NIP-46 separates remote transport and user keys, and requires `get_public_key`
after connecting. A signed outer event does not establish which user key a
client intended to use. Relay filters are routing hints; the manager still owns
the authenticated-peer decision. Numerical limits below are nSealr host profile
limits, not invented Nostr wire requirements.

## Source reconciliation and threat boundary

At the pinned baseline:

- `packages/nip46/src/session-manager.ts` subscribes with an author filter but
  `handleEvent` accepts any decryptable, validly signed event that reaches its
  callback and matches a pending ID. `signEvent` checks event/template/signature
  consistency without an expected user key. `connect` requests only an ack.
- `session-protocol.ts` checks kind, event ID, signature and the presence of a
  matching recipient; it permits multiple recipient tags. It derives the
  conversation key from the delivered event's author.
- `NostrToolsRelay` passes filters into locked `nostr-tools@2.23.3` SimplePool.
  `InMemoryRelay` explicitly applies those filters. The conditional manager gap
  alone is not evidence of a default-adapter exploit. The experiment will pin
  and inspect the dependency's filter enforcement and exercise it independently.
- `nip46.ts`'s exported metadata evaluator incorrectly requires result user keys
  to equal outer transport keys. This is a separate compatibility defect, even
  though the evaluator neither authorizes actions nor drives the manager.
- `SerialLineStreamPort` appends each incoming chunk to a string and checks each
  line independently. Ten thousand `x\n` lines retain 20,000 bytes under a
  configured `maxBufferedBytes=4`; reads and writes can also accumulate without
  a pending-operation limit. An existing test explicitly accepts aggregate
  overflow and must be replaced by a test of the corrected contract.
- Raw NIP-46 and serial payload JSON uses `JSON.parse`, losing duplicate members
  before validation. JSON trailing data is already rejected and must stay so.
- `rg` finds manager instantiation only in `session-manager.test.ts` and
  `session-live.e2e.test.ts`; browser and local-service routes do not currently
  instantiate it. `apps/service/src/index.ts` instantiates the stream port with
  one shared SerialPort duplex as input and output. Public exports include both
  modules. Existing CI therefore proves in-repository consumers, not named
  third-party client interoperability or physical device behavior.

Adversaries can control relay deliveries, serial bytes, response timing, and a
substituted remote user account. They cannot forge the pinned transport key's
signature or the selected user's signature. The configured transport public key
comes from the caller's already authenticated connection setup; this change does
not authenticate an arbitrary untrusted bunker URI or implement token discovery.

Custody: the manager holds a private copy of a client transport secret in RAM,
never the user's signing secret. Its owned copy is cleared on close; JavaScript
cannot guarantee erasure of runtime/library copies. The remote signer owns user
key custody and device approval. A connection ack or host response never grants
device authority. The enclosing browser/service adapter owns origin permission,
selected route and account selection; the manager has no origin argument and
does not claim to establish those permissions. It exposes its resolved user key
so callers can associate it with an account. Optional caller-supplied expected
user identity constrains first resolution; otherwise authenticated first
resolution establishes the session identity. Account switches require a newly
created manager and renewed caller selection, not a server response mutation.

## Required observable behavior

| ID | Contract | Independent negative/control oracle |
| --- | --- | --- |
| S01-ID-01 | Manager checks expected outer author itself before consuming any pending response, then verifies outer ID/signature, kind and exactly one matching `p` recipient. | Signed foreign author injected past filters cannot acknowledge connect, select a user key, fail another request, or return a signature. A later valid response still succeeds. Invalid signature, wrong recipient and ambiguous recipients reject. |
| S01-ID-02 | `connect()` obtains ack, requests `get_public_key`, validates both the discovered user key and optional `expectedUserPubkey` as lowercase 32-byte x-only keys that lift to valid secp256k1 curve points, then enters `session_active`. `userPubkey` remains unavailable until successful resolution. | Failed key discovery, malformed key, a correctly sized hex value that is not a curve point, error, auth challenge and expected-key mismatch never activate. Distinct transport/user keys succeed. |
| S01-ID-03 | Every signed result passes strict shape, requested-template, NIP-01 ID, Schnorr signature and pinned user-key checks. The submitted template is validated and snapshotted before asynchronous work. | A valid signature by a different fixture user is rejected; altering caller template after submission cannot alter the comparison oracle. Matching selected user succeeds. |
| S01-ID-04 | Requests carry a fresh cryptographically random per-manager namespace and a monotonic counter; IDs are never reused, including after failed connect. At most 32 requests are pending by default, configurable within 1..256. Counter exhaustion at 2^32-1 rejects. | Duplicate, late, timed-out, previous-attempt and other-manager responses cannot satisfy a new request. A repeated caller RNG value cannot reuse IDs. Pending count overflow fails before publish. |
| S01-ID-05 | A failed connect closes its subscription, removes/rejects its pending work, leaves the manager idle, and permits retry. `close()` is terminal, cancels pending requests promptly, closes subscriptions acquired concurrently, clears session identity and its secret copy, and cannot be reversed by late completion. | Close during subscribe, publish, ack and user discovery; publish rejects or never settles; timeout and error; concurrent connect; connect retry; repeated close. No unhandled rejection, leaked timer or late activation. |
| S01-ID-06 | Metadata response evaluation separates user identity from outer author. Its new v1 result reports `result_pubkey` and `result_pubkey_bound_to_expected_user`; optional `expected_user_pubkey` constrains user-bearing results. It makes no session-authentication claim. | Distinct transport and user keys parse; supplied expected-user mismatch rejects. Neither metadata flags nor equal keys activate a session. Existing v0 equality fixtures are migrated explicitly. |
| S01-PARSE-01 | NIP-46 raw response JSON, nested signed-event JSON, stringified request params, and decoded serial-frame JSON reject duplicate object keys, including escaped aliases, trailing non-whitespace, invalid JSON and excessive nesting. Check raw UTF-8 size before parsing, preserve existing exact-field validators afterward. | Duplicate `id`, `result`, `pubkey` and nested member; escaped duplicate; valid whitespace/escaped strings; trailing object/token; depth boundary. Duplicate/trailing wire envelopes have no trustworthy correlation ID and are ignored until timeout; well-formed correlated shape errors reject promptly. |
| S01-QUEUE-01 | `maxBufferedBytes` bounds all port-owned decoded UTF-8 bytes, including queued complete lines and the incomplete tail. No over-limit concatenation is retained. A separate `maxBufferedLines` bounds complete lines plus a nonempty partial tail. | Retain at most 4 bytes under the 10,000-short-line reproduction; over-limit delivery is terminal and retains zero bytes. Below/exact/above byte and line limits; UTF-8 multibyte and CRLF; partial lines and EOF. |
| S01-QUEUE-02 | Pause input while complete buffered lines await reads; resume when those lines drain. One read and one write may be pending; further calls reject before queuing. Writes are capped and honor callback/error plus backpressure. | Producer sees pause/resume, flood cannot grow private queue, stalled read/write counts are bounded, write `false` waits for drain, failed write/closed output settles promptly. |
| S01-QUEUE-03 | First I/O/overflow error is terminal: discard data, reject pending and future operations with that error, stop/destroy owned streams, and remove owned data/listener references after closure. Explicit close is idempotent and cancels pending I/O with a closed error. | Error after buffered data returns no stale line; repeated hostile data is not retained; shared duplex teardown; premature close; listener count and pending-operation cleanup. Synchronous/asynchronous destruction with/without close events; queued/delayed destruction errors; thrown/suppressed errors; constructor rollback. Normal EOF drains bounded buffered lines/tail then returns null. |

No new NIP-46 methods or token onboarding flow are promised. The current manager
supports an already selected remote signer that acknowledges connect directly;
auth challenges remain explicit unsupported failures. Relay switching, logout
wire messages, browser UI account-switch approval, and hardware proof remain
outside this bounded fix.

## Versioned resource profile and state

- Retain existing host JSON limits: raw NIP-46 message and nested result each
  <=1,024 UTF-8 bytes; decoded serial JSON <=1,024 bytes, with existing serial
  frame <=1,024 bytes; maximum JSON nesting 32 containers. These do not increase
  existing event content/tag limits. A new shared strict JSON helper in
  `packages/protocol/src/encoding.ts` avoids duplicate parsers across packages.
- Before decrypting a delivered NIP-46 event, require bounded canonical envelope
  structure: at most 16 tags, at most 8 fields per tag, at most 64 UTF-8 bytes per
  tag field, encrypted content <=2,048 UTF-8 bytes. Foreign authors are ignored
  before decryption. These bounds accommodate the current 1,024-byte profile.
- Manager request timeout defaults to 30,000 ms; configured timeouts must be
  finite safe integers in 1..300,000 ms. A blocked publish does not defer this
  deadline or close cancellation. Pending count defaults to 32, maximum 256.
  Unsettled adapter publications have a separate count with the same cap, even
  after logical timeout; only settlement reclaims that count. Publication and
  response must both complete before request success, bounded by the request
  deadline. At most one subscription acquisition can be unresolved; after its
  timeout, retry fails immediately until that acquisition settles, and a late
  handle is closed. This refinement was accepted by reviewer `/root` on
  2026-10-18 after an adversarial retained-callback analysis. It does not promise
  cancellation of arbitrary caller adapter promises.
  IDs fit the existing 128-character ID limit. No replay-history set grows with
  completed requests. Existing `randomId` test customization cannot control the
  mandatory fresh namespace; any retained suffix is validated and bounded.
- Port bytes default to 1,024, configurable in 1..1,048,576; buffered lines
  default to 64, configurable in 1..4,096. Limits include delimiters; a partial
  tail counts as one buffered line. Input already delivered above a limit causes
  terminal overflow rather than silently dropping lines. Backpressure applies
  before further chunks; Node/OS/driver queues outside the port retain their own
  high-water marks and producers must honor their stream contract.
- At most one read and one write can be pending. An output line is <=1,024
  UTF-8 bytes including newline. The enclosing serial exchange retains its
  existing timeout and closes one-shot ports on all paths. This work does not
  claim a global bound on arbitrary caller-owned Readable/Writable objects.

Manager phase remains `idle -> session_active -> session_closed`; `connecting`
is exclusive internal state within idle. Failed connection returns idle unless
close has already made it terminal. A resolved user key is immutable throughout
an active session. The monotonic request counter is never reset within a manager, including after
failed connect; retry continues that counter. A new manager receives a fresh
mandatory namespace. Input overflow never yields a partially accepted
response.

## Owned files and consumers

Implementation may edit `packages/nip46/src/{session-manager,session-protocol,
nip46}.ts` and their tests; add focused security tests there; edit
`packages/transport/src/transport.ts` and its tests;
`packages/protocol/src/encoding.ts` and tests/exports;
`packages/framing/src/serial.ts` and tests; affected local fixture snapshots in
`tests/fixtures/specs/vectors/{nip46-relay-steps,invalid}`; package READMEs,
`docs/{api,api-review,testing}.md`, changelog, and `docs/restart/S01/` evidence.
Update the Docker relay harness's signer to answer `get_public_key` correctly.
The metadata helper's v1 shape is an explicit experimental API break. Generated
API docs and their reviewed digest must be regenerated, not bypassed. Any
additional required source scope is reported before expansion.

Scope extension accepted by reviewer `/root` on 2026-10-18: migrate the metadata
v1 dispatch in `apps/cli/src/index.ts` and the fixture type/assertions in
`packages/fixtures/src/{fixtures.ts,fixtures.test.ts}` atomically. No v0
compatibility layer is required. A subsequent reviewer correction requires the
CLI relay-step comparison to use strict structural JSON equality, with object
key reordering accepted and changed values/types, array order, missing fields
and extra fields rejected. `apps/cli/src/index.test.ts` owns those independent
controls. Event/wire canonicalization is unchanged; unrelated legacy CLI JSON
text comparisons remain an A02 disposition item.

The sibling specs repository contains historical v0 fixtures and is outside this
author's write scope. If integration selects those stale fixtures, report the
version transition to the coordinator; do not silently change selection rules or
weaken assertions. The canonical task graph and main checkout remain untouched.

## Evidence plan and stop conditions

1. Build the exact baseline and preserve environment, command, UTC time, return
   code, source hash and raw output. Save standalone public-key reproductions
   showing changed-user acceptance, conditional foreign-author acceptance and
   exactly 20,000 retained serial bytes. Fixture secret scalars are public test
   material only. Default adapter investigation must distinguish source-level
   filtering and an executed adapter control from broad exploitability claims.
2. Commit failing regressions before fixes and retain logs demonstrating the
   intended failure. Use known fixture public keys as expected identities and
   independent `nostr-tools` verification where useful; never compute the
   expected identity through the manager under test. For serial bounds, observe
   private retained bytes/count only as an adversarial diagnostic, paired with
   public overflow/cancellation behavior.
3. Implement the smallest coherent changes, run targeted checks after each
   boundary, and retain regression logs. Target command with pinned tool PATH:
   `pnpm exec vitest run --maxWorkers=4 packages/nip46 packages/transport packages/protocol packages/framing`.
4. Run `make ci` for all affected consumers, generated API checks, browser
   runtime/security guards, packages, lint and dependency audit. No check may be
   removed or reclassified as passing. Run Docker live e2e if usable; otherwise
   retain the concrete unavailable-resource/skip evidence. This in-repository
   signer harness is not evidence of compatibility with an external client.
5. A distinct reviewer checks the exact committed source candidate against this
   specification and threat, including an independently designed adversarial
   experiment. Evidence/handoff metadata may be committed after the candidate;
   changed source invalidates affected review. Root owns integration review and
   graph closure after all five S01 acceptance statements are supported.

Tool tuple selected with R00: Linux x86-64, Node v24.22.0, bundled npm 11.19.1,
pnpm 10.33.4, lockfile dependencies. Official Node archive
`node-v24.22.0-linux-x64.tar.xz` SHA-256:
`cc2f601cee82d9a5a233302fe307abc600727035fd7d2c3a3571755989e95008`.
Tools and caches live under ignored worktree `.tmp/`. Record actual Python,
OS/kernel, dependency versions and lockfile hash with execution evidence.

Stop implementation for unresolved identity authority, inability to distinguish
transport/user keys, unavailable specification review, or an experiment that
cannot isolate its claimed defect. Inherited CI failures remain explicit until
resolved or assigned; they do not excuse weakening validation. Physical devices,
production keys and release claims are unnecessary and unauthorized by this task.

Rejected alternatives: trusting relay filters leaves custom adapters unsafe;
equating transport and user keys contradicts NIP-46; pinning the first signed
event accepts first-response substitution; clearing an unbounded replay set
permits old IDs; per-line-only bounds do not bound retained queues; silently
dropping overflow lines makes response correlation and diagnosis unreliable.

## F01 destruction completion clarification

Independent review `67804a5d1995504a69d2fe49618da8e263ec3d89` found that
asynchronous `_destroy` completion with `emitClose: false` left both streams'
port-owned error/close listeners attached in candidate `d385ddb0`. The retained
regression also shows that `.closed === true` can precede Node's queued error
event, so removing handlers immediately is unsafe even for synchronous callbacks.

The port owns live Node `Readable`/`Writable` streams and temporarily wraps the
documented `_destroy(error, callback)` implementation hook, once per distinct
stream. The wrapper delegates with the original receiver/error, forwards only
the first completion (including a thrown error), and restores the exact own
property descriptor or inherited lookup only if the installed hook is still its
own. One `setImmediate` after completion retains error handling through Node's
queued destruction error before listener cleanup; there is no polling, private
stream-state read, or undocumented `destroy` callback. Close events can perform
cleanup earlier after Node's error delivery. Suppressed errors and absent close
events still reach completion cleanup; public `errored` preserves a destruction
error whose event was suppressed. Ordinary EOF behavior is unchanged.

Already destroyed streams and hooks that cannot be replaced are rejected by the
constructor. Failure rolls back earlier hook installation and leaves no port
listeners. Ownership excludes callers replacing/freezing hooks during use; the
conditional restore still avoids overwriting a later replacement. The observer
requires no timers while destruction is pending and schedules at most one
completion task per distinct stream. A custom hook that never completes can
retain its observer until it does; port-owned buffers and pending reads/writes
still clear/cancel immediately. This is a lifecycle dependency, not a claim that
the port can force arbitrary stream implementations to finish destruction.

The Node v24.22.0 [stream contract](https://raw.githubusercontent.com/nodejs/node/v24.22.0/doc/api/stream.md),
[destruction implementation](https://raw.githubusercontent.com/nodejs/node/v24.22.0/lib/internal/streams/destroy.js)
and [finished implementation](https://raw.githubusercontent.com/nodejs/node/v24.22.0/lib/internal/streams/end-of-stream.js)
support this timing distinction. Parent review authorized this bounded wrapper
design subject to renewed independent review of the exact candidate. Tests cover
the four synchronous/asynchronous and emit/suppress-close combinations with
separate and shared streams, queued/delayed errors, original receiver/error,
duplicate callbacks, throw/error suppression, descriptor restoration, a later
replacement, and readonly/nonextensible/already-destroying constructor rollback.

F02, independently recorded in review commit
`63cff320864552888c0666f972dacf7ea5ec2084`, further clarifies the existing first-error
rule: a known public `input.errored` value is terminal even after normal EOF and
with no pending write. It takes precedence over tail draining, whether the
destruction hook emits or suppresses the error event and whether `close` is
emitted. The port preserves that error, discards retained input and destroys its
peer; error-free closure after EOF still drains the bounded tail normally. The
fix changes only that error/EOF decision, not the completion wrapper or fixtures.
