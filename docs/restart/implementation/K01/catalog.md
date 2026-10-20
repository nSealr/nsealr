# K01 public catalog and deterministic rejection rules

This proposed implementation contract realizes the unchanged P01
[requirements](../../../product/requirements.md) and
[event review](../../../product/event-review-contract.md). Its primary NIP pin
is `37db639582d857e12468dcccd99b2c7f1d657da9`; the selected original bodies and
hashes are bound in [source-inputs.json](source-inputs.json). No global NIP
baseline, T01 wire schema or historical fixture is changed by this preparation.

## Shared representation

Accept exactly `created_at`, `kind`, `tags`, `content` once. The engine chooses
pubkey/id/sig. Decode strict UTF-8/JSON; reject decoded duplicate member names,
unknown/missing members, trailing objects/bytes/commas, BOM, surrogate/encoding
errors and wrong types. Integer tokens are `0` or `[1-9][0-9]*`, timestamps
0..2^53-1 and kinds 0..65535. All syntactically valid other kinds still reject
semantic authorization. Canonical bytes are NIP-01 `[0,pubkey,time,kind,tags,content]`,
compact UTF-8, with the existing exact escaping; preserve Unicode form, string
whitespace, tag order and duplicate tags. Do not silently repair input.

Every accepted signed value and suffix is fully indexed and inspectable through
the injective ASCII inspection mechanism; no ellipsis, fetched media, executed
markup, spoofed label or hidden final page. The operation overview states its
actual effect and the selected full public key. The complete additional-data
area says meaning is not verified. A known tag with a malformed defined prefix
cannot fall back to that area. Remaining strings after the kind-specific defined
prefix are shown next to the tag as uninterpreted extensions; they do not replace
or override the prefix. Contradictory recognized context rejects. Fail before
consent if full semantic presentation cannot fit.

Bind the new seven-kind catalog/reviewer revision into the operation context and
inspection commitment, invalidating old reviews on change. The unchanged
`nsealr.authorization.v1` template schema, T01's wire version and this catalog's
review revision are separate identifiers. No old review digest authorizes the
expanded interpretation, even when its event ID is unchanged.

## Reference and relay grammar fixed before code

- An event ID is exactly 64 lowercase hex characters interpreted as 32 bytes.
  It need not lift to a curve point. A public-key reference has that spelling
  **and** must be a valid BIP340 x-only key. Do not interchange the two checks.
- A kind hint is canonical unsigned decimal 0..65535. An address is split at
  its **first two** colons into kind/public-key/remaining identifier. Kind 0, 3
  or 10000..19999 requires empty identifier; 30000..39999 admits the full
  possibly empty identifier, including further colons. Other coordinate kinds
  reject. No Unicode/ID/case normalization occurs.
- Relay URLs use the existing conservative subset: lowercase `ws://` or
  `wss://`; ASCII DNS labels 1..63 bytes, total host <=253, alphanumeric ends
  with internal hyphens, or exactly four canonical decimal IPv4 octets 0..255.
  Optional port is canonical decimal 1..65535. Preserve host case and exact
  spelling. Reject credentials, raw controls/space, backslashes, empty host,
  query/fragment, IPv6 and direct non-ASCII/IDNA names as unsupported in this
  first subset. The optional path uses ASCII RFC3986 pchar plus `/`; percent
  escapes require two hex digits and may not encode C0, DEL or backslash.
  Do not decode/rewrite accepted signed strings. Empty relay is allowed only
  in optional hint positions, never for a required repost/relay-list URL.
  This explicitly strengthens S03's percent-control hint case; it does not
  broaden any prior URI admission or assert general WebSocket support.
- Suffix fields are data, not alternate identities/roles. If supplied checked
  evidence contradicts a defined ID/author/kind/coordinate, reject. The first
  K01 API admits no separately supplied network-evidence object: additional
  envelope/template fields reject. Thus normal references are unverified;
  the included signed event inside kind-6 content is the sole checked original
  evidence in this milestone. No host preview label becomes evidence.

## Seven admitted kinds

| Kind | Required interpretation and complete review | Reject / special cases |
| --- | --- | --- |
| 0 | Content is exactly one JSON object; every member, JSON type, nested object/array index and complete value is shown. Known labels carry no identity verification. State whole-profile replacement, including an empty object. All tags are additional signed data. Preserve the original content string in canonical bytes. | Reject duplicate decoded keys at **every** depth, invalid JSON/Unicode/trailing data, nonobject root, unrenderable content and finite-depth/work excess. JSON numeric tokens follow RFC8259 and are shown in full without float conversion or normalization; NaN/Infinity reject. Metadata-only limits: depth <=8, aggregate value nodes <=128, <=64 members/object and <=64 entries/array, within the unchanged 2,048-byte content ceiling. Root counts as depth 1/node 1; each child value counts one node. No member or value is skipped. |
| 1 | Preserve the S03 kind-1 semantics: plain text; `e` ID, optional relay, optional root/reply marker, optional author; `p` key/optional relay; `q` ID-or-address, relay slot, and author when required by the ID form. Show all suffixes and unknown tags. Unmarked `e` means ambiguous reference context, not a guessed reply. Root alone is a direct reply; one distinct root+reply is a deeper reply. References/quotes remain unverified. | Reject malformed known prefix, repeated root/reply markers, reply without root or equal root, mixed marked/unmarked `e`, unsupported marker, invalid reference/relay/author, and `emoji`. For a q-ID the author slot is required; for an address an optional author must match its coordinate. No non-kind-1 reply convention or remote image. The eight original S03 vectors remain unchanged positive controls. |
| 3 | Every `p` is key, optional relay, optional petname; latter strings are unverified hints. Show the entire submitted list, every suffix/tag and content as additional uninterpreted signed data. Explain full-list replacement; an empty p-list explicitly means unfollow all. Preserve repeated entries, never silently deduplicate. | Reject malformed key/hint prefixes; do not interpret petnames as verified identity or synthesize a before/after diff from host state. No previous verified/fresh list is assumed. |
| 5 | Require at least one `e` ID or `a` coordinate. Interpret all `k` kind hints; show every target, hint, reason and extension. This kind's defined e/a/k prefix ends at its value; suffixes are additional data, not a newly invented authenticated relay/author contract. Coordinates retain colons in identifiers. Explain that a coordinate deletion can cover earlier versions up to the request timestamp, and relay/client erasure is not guaranteed. | Reject invalid targets/coordinates/k hints, missing target and contradictions in a defined prefix. A coordinate's explicit author must equal the selected identity; an e-reference alone proves no target ownership. Do not guess pairing between multiple e and k tags. Deletion-request targets/hints receive the explicit limitation that deleting a deletion request cannot undo it. |
| 6 | Exactly one target `e` with a required nonempty relay URL; optional single `p` author hint. The e prefix is ID+relay, and p is key+optional relay; remaining strings are additional data. Empty content is allowed with “referenced content not supplied/verified.” Nonempty content must be the full JSON of one original signed **kind-1** event with exactly pubkey/created_at/kind/tags/content/id/sig. Strictly validate its shape, recomputed ID and raw BIP340 signature; match target e and any supplied p. Show the original author/ID and complete content/tags plus outer signed fields, separating cryptographic validity from real-world authorship. | Reject nonempty arbitrary text, missing/duplicate target, malformed original/duplicates/Unicode, extra event members, wrong ID/signature/key/kind/target/author and any incomplete inspection. No recursive reposts: included kind must be 1. Inner event parsing remains bounded by the parent content and existing ceilings; retain spans/cursors rather than a second full event/page copy. Generic kind 16 rejects. |
| 7 | Require e target(s); the **last** e is the target ID and the **last** p, if present, its author hint. Show every preceding reference, optional relay/author hints, optional a coordinate and k kind hint, all extensions and exact content. Empty or `+` is like, `-` dislike, anything else is a reaction value. Unicode emoji text is literal data, not a fetched custom emoji. | Reject malformed references/hints; at most one a and one k; their explicit kind/author must agree with each other and the final p where applicable. No verified target author/content without checked evidence. Reject recognized `emoji` tags and whole-content custom-emoji spelling: colon, nonempty text containing no further colon, colon. This conservative product rule treats that shape as deferred without fetching an image. Kind17 external-content reactions reject. Do not accidentally select the first e/p. |
| 10002 | Every r is a required nonempty relay URL plus optional role: absent=read+write, otherwise exactly `read` or `write`. Show exact URLs/roles, ordered duplicate entries, all extension/tag data and any content as additional signed text. Explain whole-list replacement; no r entries explicitly withdraws all relay preferences. | Reject malformed URL/role prefix; neither a host label nor successful publication is proven. Do not merge/deduplicate/rewrite URLs or infer a trustworthy previous list. This is not the connected-only DM relay-list action 10050. |

An included kind-6 original uses the same exact integer, string and tag-shape
rules; its pubkey/ID are 64 lowercase hex and its signature is 128 lowercase
hex decoded to exactly 64 bytes. Invalid public points or BIP340 r/s values
reject. Verification does not mean a real-world author/name or relay was trusted.
For kind 7, any explicit final-e author, final p and a-coordinate author must
agree where provided; earlier contextual references remain separately shown.
The e-ID alone cannot establish that an unverified coordinate describes the
same event. Show the coordinate as supplied context, not cryptographic proof.

For kind 7 e/a fields the defined optional hints are relay then author; for its p
fields the defined optional hint is relay. A kind 1 e marker is not an author
slot in a kind 7 e. Validate the syntax of every provided known position; empty
placeholders are allowed only where the optional field permits them. Supplied
author hints must be real x-only keys, and an a-author hint must match the
coordinate. Any additional fields remain adjacent uninterpreted data.

Local public-key disclosure returns the actual selected full key under the local
session rule; it is not login approval, publication or a hardware attestation.
Other public kinds, opaque bytes, NIP-44/04 calls, connected-only 10050 and 22242,
gift-wrap/seal/rumor and authorization/payment methods reject here. No catalog
item can inherit consent from a host flag, diagnostic preview or another item.

## Independent expected inputs

[independent-inputs.json](independent-inputs.json) contains new public-fixture
canonical/signature expectations derived with the already pinned Python/hashlib
and BIP340 reference, plus semantic negative expectations chosen from this
contract before runtime edits. They are input expectations, not observed K01
results or proof that its semantic reviewer exists. Existing S03 vectors remain
at their original path/hash; they are neither regenerated nor overwritten.
Every kind additionally needs the common fixture families in the acceptance plan
and actual full-frame/one-use checks. Physical screens, keys and clocks are not
qualified by these mathematical fixtures.
