# S03 — one canonical operation, one local authorization, one attempt

Preparation candidate, 2026-10-18. Author: `/root/s03_author`. Repository:
`nSealr/nsealr`; input `3cbd818a0bcd4016eb8983dad7605cb57280d913`; branch
`restart/s03-authorization`. This brief, `source-audit.json` and
`acceptance-plan.json` are the entire preparation change. No implementation or
acceptance pass is claimed. Main
`7b5553685dac56029a4379be12054154b6b5e0b5` now records graph revision 11,
P01/S02 integrated and S03 running under issue 17. Comparison of all 43 audited
inputs found 41 byte-identical files; only the task graph and restart README
changed, for lifecycle/handoff guidance. The audit records both changed hashes
and confirms unchanged S03 acceptance. The source input remains pinned above;
distinct approval of this exact specification is still required before code.

The requirement authority is S03's five unchanged acceptance statements in
`docs/restart/work-items.json`, P01 PROD-01/04/05/09/10, the P01 event-review
contract and threat models, and AUTH-01–05 in `development.md`. Source establishes
current behavior, which can be wrong. The accepted P01 candidate is
`df4cff34b4733aaac04db9b176db7c4edfc256d8`; its NIP baseline is
`37db639582d857e12468dcccd99b2c7f1d657da9`. Hashes and inspected symbols are in
the audit. There is no `canonicalwork-items.json`; `work-items.json` is the ledger.

## Deliverable and division of work

Implement the portable parser/canonicalizer, actual custody-derived identity,
complete kind-1 review and consuming authorization state. A complete admitted
kind-1 request must reach a fixture-signed, independently verified result through
the same private attempt boundary used by the production-disabled path. This is
more than a detached state-machine model. It is not a working device release.

The coordinator accepted this task split for specification review: S03 admits
kind-1 plain notes and the explicitly described reference/quote subset below.
All other kinds reject at the authorization boundary, including other members
of P01's eventual public catalog. K01 implements their semantic reviewers,
production signing/output verification, full operation secret-scratch analysis
and initial target final linking. This does not remove K01's parser/consent
integration acceptance: K01 must reuse and retest this boundary. C02 owns the
message/authentication flows. T01 owns per-profile capabilities, readiness
evidence and published transport/limit manifests. Each device task owns real
display/input, reset/clock/entropy, memory placement and timing qualification.

S03 must not accept raw opaque signing, encryption, decryption, recovery import,
policy changes or arbitrary kinds through a signing authorization. Unsupported
recognized semantics reject; there is no raw-review fallback. The existing
serial product continues to answer `signing_disabled`. No readiness flags,
`approved` JSON member, transcript, fixture identity or remote button command
can enable it. There is no S03 production response cache; every retry requires
new review. K01 may add a bounded request-bound completed-result cache whose
read path never invokes signing again.

The old companion `validateRouteSemantics` requirement for persistent grants on
ESP32 USB/custom routes is a host-policy defect to reconcile in T01/F01. It is
neither a S03 input authority nor a compatibility requirement. Manual local
consent remains required regardless of host route/descriptor capability flags.

## Current defects and retained boundaries

`ApprovalGate` is public and Clone, and `can_sign(&self)` repeatedly returns
authority from caller-provided strings. `TrustedReviewSession` and QR/serial
facades clone that state. A caller can construct pages/digest independently;
the display can add ellipses, and logical navigation can reach the decision
without visiting every scroll window. `SignerIdentity` validates a public-key
string; account selection explicitly does not derive it from custody. None of
these is safe signing authority. No `ApprovalTicket` symbol exists in the
inspected tracked main source; the reusable gate is the actual local equivalent.

The envelope scanner overwrites duplicate members, accepts noncanonical number
spellings/trailing commas and kind values above 65535, and skips nested grammar.
The protocol has a second recursive, lenient scanner with no trailing-data
check. The review digest is a legacy review JSON hash, not a NIP-01 event ID.
The source audit identifies exact functions, including protective behavior that
already exists: fixed buffers, bounded envelopes, surrogate validation, opaque
non-Clone S02 secrets and disabled product signing. Preserve those protections.

## Small implementation shape and owned paths after approval

Keep the existing `crates/nsealr-core` workspace location. Add three focused
modules: `event.rs` (immutable template, schema-directed parser, canonical
serialization), `authorization.rs` (one owner and lifecycle), and
`review/event.rs` (kind-1 interpretation and complete review). Factor a private
JSON string/integer reader inside `event.rs`; do not build a generic DOM,
plugin/provider registry, token protocol or second normative engine.

Replace both permissive request scanners with that single strict reader,
retaining existing serial/QR framing. `qr/envelope.rs`, `protocol.rs`,
`review/{mod,types,trusted,display,qr,serial,qr_flow,controls,signer_identity}.rs`,
`policy/{mod,approval_gate,policy_change_review}.rs`, `session/account.rs` and
`lib.rs` are the affected integration surfaces. Remove the public reusable
`ApprovalGate::can_sign` path. Legacy recovery/policy preview builders may retain
ordinary review decisions, clearly named as preview results, with no conversion
into signing authority. Remove authority-looking `can_sign`/`approved_for_signing`
APIs and migrate actual consumers; historical fixture field names may be read
only as historical expectations, never exposed as the new authority contract.
Remove replaced scanners/authority rather than keep parallel active versions.

S02 secret wrappers/keyring remain opaque and consuming. A narrow consuming
intake in `session/account.rs` may move a standalone `SecretKey` into the new
owner; it must not expose raw bytes, add Clone or copy a source into a review
DTO. No BIP-39/NIP-06 derivation is added. The new owner derives its actual x-only
public key with the selected maintained `k256 = 0.14.0`, default features off,
`schnorr` only. Keep the backend key private and non-Clone at our boundary.
Construct it once, drop/wipe the consumed raw owner, and inventory the unavoidable
backend conversion temporaries; do not claim Rust moves or backend Drop erase
all physical copies. S02's documented backend scratch limits remain explicit.
No entropy generation or runtime RNG fallback is added. Deterministic auxiliary
bytes are allowed solely in clearly identified public-fixture tests.

Necessary lock/vendor/license changes accompany that used dependency. Tests
live under `crates/nsealr-core/tests/` plus private unit tests, S03 evidence and
independent oracle files under this task directory. Update only affected
`apps/desktop-simulator/src/replay/` consumers and its tests. Add no board SDK
dependency. A02 rehearsal preserves these crate paths; before any code/import,
the coordinator must reconcile new input trees and shared fixture destinations.
Other repositories, graph/root metadata, CI policy/floors and A02 files are
read-only. Expansion beyond this enumerated scope needs a revised assignment.

## Strict input and canonical event contract

Name the internal contract `nsealr.authorization.v1`; it is not a new supported
wire protocol announcement. Existing framed requests are parsed strictly as
version-1 legacy envelopes and remain signing-disabled. The standalone template
entry point and both legacy adapters use the same implementation.

An envelope has exactly `version`, `request_id`, `method`, and, for `sign_event`,
`params` containing exactly `event_template`. Parameterless existing methods
forbid params. Signing templates have exactly `created_at`, `kind`, `tags`,
`content`; caller `pubkey`, `id`, `sig`, approval and unknown fields reject.
All required members occur once. Compare decoded member names, so escaped
duplicates reject too. Reject unknown fields immediately without recursively
skipping their values. Require one complete object, permitting only RFC 8259
whitespace outside it. Reject BOM, trailing bytes/objects/commas, missing commas,
comments, invalid literals/types and malformed nested arrays.

Input is strict UTF-8; invalid/overlong sequences, surrogate encodings and
unpaired JSON surrogate escapes reject, without replacement characters. Valid
surrogate pairs decode to their scalar. Preserve strings, whitespace within
strings, Unicode normalization form, tag order and duplicate tags exactly.
Empty tags or empty tag identifiers reject. For version/kind/time use decimal
tokens `0` or `[1-9][0-9]*`, checked before conversion: no negative values,
`-0`, plus sign, leading zero, fractions or exponent spellings. Kind is
0..65535; created_at is 0..9007199254740991 as an explicit interoperability
policy, not a claimed NIP-01 maximum or trustworthy current time.

Canonical bytes are compact UTF-8 JSON `[0,pubkey,created_at,kind,tags,content]`
with lowercase 64-hex custody-derived pubkey, canonical decimal integers,
ordered arrays and preserved decoded strings. Escape quote/backslash and the
five named JSON controls using exactly these seven spellings:
quote U+0022 → `\"`, backslash U+005C → `\\`, backspace U+0008 → `\b`,
form feed U+000C → `\f`, line feed U+000A → `\n`, carriage return U+000D →
`\r`, and tab U+0009 → `\t`. Remaining C0 controls use lowercase
`\u00xx` to satisfy JSON grammar. Slash and other Unicode scalars remain
verbatim. The latter C0 choice resolves NIP-01's abbreviated escape list using
RFC 8259, and must be independently vector-tested. Compute SHA-256 with the
S02 `sha2` wrapper; never reuse the legacy approval digest as event ID. The
request ID/session/review metadata are not part of the Nostr event hash but
remain bound to the authorization.

## Admitted kind-1 meaning and complete display

Content is plain signed text; no HTML/Markdown execution, URI expansion,
network fetch, remote image or claim of referenced content verification. All
signed fields are indexed and shown in full, including the exact timestamp,
kind and selected full public key. Request ID and local session/policy context
are visible review metadata. Host labels/origins are not admitted in this
version, so there is no unreviewed transport metadata entering an approval.

* `e`: require a lowercase 64-hex event ID. Optional relay hint is either empty
  or passes the URI subset below. Optional marker is empty (unmarked), `root`
  or `reply`; other markers, including deprecated `mention`, reject. Optional
  author is a valid x-only secp256k1 public key. More than one marked root or
  more than one marked reply rejects, even identical duplicates. A root alone
  is a direct-root reply; root plus distinct reply is threaded context. Reply
  without root, root equal to reply, or mixed marked/unmarked `e` context
  rejects as unsupported ambiguity. Unmarked-only `e` tags remain references
  with explicitly ambiguous reply context; never guess positional semantics.
  No proof is claimed that an unknown referenced event is actually kind 1.
* `p`: require a valid lowercase 64-hex x-only public key, optional relay hint;
  later fields are fully shown uninterpreted extensions. Names gain no trust.
* `q`: this first subset requires target and relay-hint fields. For an event-ID
  target it additionally requires a valid author pubkey; an address target is
  canonical decimal kind, colon, valid pubkey, colon, exact remaining identifier
  (including further colons). Address kind must be replaceable (0, 3,
  10000..19999) with empty identifier or addressable (30000..39999) with any
  identifier. An optional author field on address quotes must match its embedded
  key. Reject malformed prefixes; show targets as unverified quotations.
* Recognized suffix strings after these defined prefixes are indexed adjacent
  extensions marked “additional signed data — meaning not verified”. Unknown
  tags receive the same complete distinct presentation. Neither can replace a
  malformed known tag. `emoji` tags reject in this subset; no custom-emoji
  verification or fetched content is implied. Unknown kinds reject entirely.

For reference relay hints, accept empty or an explicit conservative URI subset:
ASCII `ws://` or `wss://`, DNS labels of 1..63 ASCII letters/digits/hyphens
(hyphen not first/last; total host <=253), or four canonical decimal IPv4
octets 0..255; optional canonical port 1..65535; optional slash path containing
RFC 3986 unreserved characters, sub-delimiters, `:`, `@`, `/` and valid `%HH`
triplets. Reject userinfo, query, fragment, backslash, controls/space, bracketed
IPv6 and Unicode hostnames for this subset. Do not lowercase, decode escapes,
normalize paths or rewrite the signed URI. Syntax acceptance does not
authenticate the host; excluded otherwise valid URIs are explicitly unsupported.
K01 may expand this reviewed grammar with independent cases.

Use an unambiguous ASCII inspection representation: quote string boundaries,
escape literal backslash/quote, use named escapes for named controls and
`\u{HEX}` for all non-ASCII scalars and remaining controls. Thus literal
`\\u{202E}` cannot masquerade as the bidi character `\u{202E}`, and combining
sequences, zero-width characters and confusables remain distinguishable without
a Unicode database or normalization. Render index/role separately from value;
show empty strings explicitly. Bound wrapping without splitting an escape token.
No ellipsis, omitted suffix, collapsed whitespace or “safe replacement” is
permitted in an authority-bearing review. If any field or index cannot be
rendered completely within limits, reject before approval.

This ASCII cursor is a portable conformance and exact-inspection baseline, not
acceptance of public-profile Unicode readability or usability. Product screens
must pass their device and P02 usability/adoption gates. They may combine a
faithful readable Unicode presentation with the exact inspection view, but must
preserve all signed values and their role/index binding. Adding that presentation
requires an owned, reviewed renderer change and evidence for its fonts, shaping,
bidi handling and navigation; normalization, hidden truncation or blind-signing
fallback cannot stand in for readable complete review.

Use one incremental review cursor over the immutable operation, not a stored
copy of every page. Preflight all pages and checked page counts before review;
generate the same pages from the same owner thereafter. An approval requires
successful presentation and local acknowledgement of every flat page, followed
by a distinct decision page; jumping logical sections cannot count as traversal.
A failed display call cannot mark a page seen. Re-rendering/back navigation is
allowed; it cannot change content, reset expiry or mint additional authority.

## Ownership, binding and transitions

One non-Clone `AuthorizationSession` owns one selected key, one pending
operation, a monotonically checked operation generation and local session/policy
generations. No public grant/ticket, serde representation, public approved-state
constructor or detached authorized-operation value exists. Public request data,
review frames and diagnostic status carry no execution authority. The local
display/input facade is a trusted-image interface, never reachable by host
protocol deserialization. Rust cannot distinguish a malicious linked caller
from firmware; hardware trusted-path and process/FFI isolation are not claimed.

Bind immutable canonical operation/event ID, actual identity, request ID,
operation/session/account/policy generations, contract/limit/review versions,
complete generated review plan and fixed deadline. Use a domain-separated,
length-delimited SHA-256 commitment for diagnostic comparison; authority remains
private owned state, not knowledge of that digest. A changed policy/limit/review
version requires invalidation and new review. Do not authorize by comparing
arbitrary caller-supplied pages or hashes.

| State and event | Required result |
| --- | --- |
| Locked / intake | Reject; no key or operation authority. Local consuming key selection derives the identity and opens a fresh idle session. |
| Idle / valid request | Parse, validate, canonicalize and preflight; enter Reviewing. Invalid request leaves no partial pending authority. |
| Reviewing or Approved / another request | Return Busy; do not silently replace the operation or extend its deadline. |
| Reviewing / local displayed-page acknowledgement | Advance bounded traversal; final consent is allowed only after complete successful display. Old request/page-generation events reject. |
| Reviewing / complete local consent | Enter Approved for exactly the bound operation. Duplicate consent is terminal and cannot refresh it. |
| Approved / first execution attempt | Replace Approved with Executing/Spent before context checks or backend invocation. Wrong request/context or any later failure still consumes it. |
| Executing / backend completion | At most one call; verify fixture output against the bound digest/key in tests. Success or failure ends Spent; no automatic retry. |
| Any pending state / cancel, reject, lock, reset, expiry, account/policy/limits change | Invalidate; zero subsequent calls for that operation. Lock/reset/account replacement drop owned key state as applicable. |
| Spent or invalidated / execute, approve, old callback, reconnect replay | Reject; only fresh parsing and a complete new local review can start another operation. |

Exclusive `&mut` ownership serializes portable transitions. Host threads must
share the same owner behind synchronization; a second owner cannot import a
grant. Test both sequential schedules and two threads racing the same protected
owner. The linearization point is leaving Approved: cancellation ordered before
it prevents execution; cancellation ordered after cannot undo a started crypto
operation, but cannot permit another. A completion whose generation has been
invalidated is discarded. An adapter introducing asynchronous execution must
preserve this rule and earns its own integration evidence.

Deadlines use trusted-runtime monotonic ticks, with declared finite duration,
checked addition and comparison; `now >= deadline` expires. Rollback, unavailable
clock or generation/counter overflow fails closed. The engine does not infer
time from created_at or host timestamps. In-process reset increments the checked
session generation and wipes pending/key state; it never resets counters to
reuse an old operation identifier. Reconstructed owners start locked with no
authority. Local input acknowledgements stay inside the owner's live review
call; no detached local-input capability can be transferred to a new owner.
Cold boot restores no UI/grant state, and host-retained bytes cannot act as local
input. No serialization/restoration of reviews or grants exists. Tests use an explicit
fake local clock with a 100-tick lifetime and reset; that proves only the
portable rule and makes no tick-to-wall-time promise.

Production `attempt_sign` enters the same consuming boundary and returns
`SigningUnavailable`, with no output or hidden retry. A private test-only backend
hook invokes k256 raw BIP-340 with public fixture key/auxiliary bytes, and can
inject failure before/after invocation. Do not expose a public callback that
receives the secret or can mint approved state. K01 replaces the disabled
backend, not the authority boundary. No test-only path is enabled by a runtime
flag or shipped feature.

## Finite capacity and proof limits

Use fixed inline storage and checked arithmetic, with an explicit portable
conformance limit tuple; it is not an admitted device profile. Proposed ceilings:
4096 input bytes; 2048 decoded content bytes; 32 tags; 8 fields/tag; 256 bytes
per tag field; 4096 total decoded string bytes; 8192 canonical bytes; 1024 review
pages; one pending operation; no queued operations or result cache. Request IDs
remain 1..128 ASCII `[A-Za-z0-9._:-]`. A 32-column, 8-line test display measures
complete pagination; any supplied geometry is validated against fixed frame
capacity. Template depth is schema-fixed, at most five containers including the
legacy envelope; unsupported nesting fails immediately, without recursion.
Legacy wire frame/envelope limits stay at their existing stricter values; the
new core ceilings do not silently advertise larger serial/QR capacities.

Retained decoded strings use one compact 4096-byte arena shared by content and
tag fields. Store checked offsets/lengths into it: at most 256 four-byte spans
(`u16` offset and length, 1024 bytes), one content span, and 33 `u16` tag
boundaries (66 bytes). Request ID has its separate bounded 128-byte storage.
Equivalent compact layouts are acceptable; allocating a 256-byte `FixedStr`
for every tag-field slot is not. That Cartesian layout would consume 65536
bytes before content despite the aggregate limit. No allocator framework is
needed, and the parser writes each decoded value once into the checked arena.

The retained `PendingOperation` budget is **8192 bytes**, and the complete
`AuthorizationSession` budget is **16384 bytes**, counting its pending operation
once and including all inline metadata, review cursor/frame and backend-key
fields. The approximately 5.2 KiB arena/span/tag-index/request-ID base leaves
room in the pending budget for public identity, hashes, numeric fields and
alignment; the session budget leaves room for lifecycle/display state without
another operation copy. Canonicalization streams from the immutable arena;
neither the up-to-8192 canonical bytes nor all review pages are retained in the
owner. Record actual `size_of` values and enforce these bounds in L01 before
acceptance, rather than infer memory cost from logical byte limits.

Record the backend key's contribution within the retained total. Separately
inventory caller-owned input buffers, any temporary canonical-output
buffer/writer, one-page rendering scratch and hashing/backend scratch.
Those transient/external buffers are not a hidden retained queue and
must not be described as covered by the 16 KiB owner budget. The whole-program
stack/peak RAM remains a measured device gate. An implementation exceeding the
chosen retained budgets requires revised specification and review before code
continues; do not silently raise the bounds.

Check input length before decoding/storing and individual/aggregate capacity
before each write. Count canonical/review expansion with checked arithmetic
before consent. Bound preflight and page work by explicit byte/page limits; use
deterministic operation counters in adversarial tests rather than elapsed host
time as a hardware speed claim. A caller can configure stricter local limits,
never exceed hard capacities; host request fields cannot configure them. T01 and
each target must replace these conformance settings with qualified versioned
profile values. Record `size_of` retained structures and exercised no_std build
results; actual stack, peak RAM, latency and readable screens remain unproven.

## Verification and stop conditions

`acceptance-plan.json` maps every S03 acceptance and AUTH obligation through
source gaps to named behavioral cases, commands and independently generated
expected results. Save initial failing cases before repair; a compile failure
caused solely by a not-yet-created API is not the behavioral reproduction.
Existing unsafe functions get direct baseline repros; new surfaces get reviewed
oracle-first cases. Expected canonical bytes/IDs come from a strict independent
Python standard-library oracle plus hand-checked tiny byte strings, never from
Rust output. Independently verify raw BIP-340 output with pinned upstream
reference code or libsecp; preserve source/license/hash provenance. Only public
disposable keys enter artifacts.

Run targeted security tests, affected simulator regressions, no_std build and
then `make ci` once the candidate is coherent. Do not lower coverage or other
gates. Preserve command/environment/exit codes and bounded logs, source hashes,
oracle fixture hashes and failed-to-fixed observations. Distinct final review
must inspect the actual exported API, mutations and lifecycle schedules, not
only the author's pass count. No S03 acceptance closes while an admitted path
still has reusable authority, misleading review, parser ambiguity or unverifiable
canonical output. Changed inputs, broadened kinds/URI grammar or architectural
scope require specification reconciliation before implementation proceeds.

Primary sources consulted 2026-10-18: [NIP-01 events/signatures and tags](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/01.md),
[NIP-10 marked references and quotes](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/10.md),
[NIP-18 quote syntax](https://github.com/nostr-protocol/nips/blob/37db639582d857e12468dcccd99b2c7f1d657da9/18.md),
[RFC 8259 sections 4–9](https://www.rfc-editor.org/rfc/rfc8259.html),
[RFC 3986 URI character/authority/path grammar](https://www.rfc-editor.org/rfc/rfc3986.html),
[Unicode TR36 revision 15 sections 2.5 and 3.1–3.6](https://www.unicode.org/reports/tr36/tr36-15.html),
[BIP-340 specification](https://github.com/bitcoin/bips/blob/927b6de9915c9262615a6399de51b200f81e5aa4/bip-0340.mediawiki).
These establish protocol/security facts; the narrower admission grammar,
display spelling and numeric/capacity rules above are explicit product choices.
