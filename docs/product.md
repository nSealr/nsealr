# Product contract

Status: restart design, 2026-11-09. This describes intended behavior, not a
completed implementation.

One offline device protects one Nostr identity or threshold share per session.
Its primary user wants deliberate control over an important personal or shared
identity. It is not a chat application or payment wallet.

The finished product has a finite scope:

| Journey | Required outcome |
| --- | --- |
| Identity and recovery | Create/import nsec or English BIP39, optional passphrase and explicit NIP-06 account, verify text/QR backup, clear and restore the same identity. Create 12/24 words; import all five standard word counts. |
| Public use | Profile, notes/replies, follows, note reposts, reactions, deletion requests and relay preferences. Exact targets and replacement effects must be understandable. |
| Private use | Modern NIP-17/NIP-44 one-to-one text messaging, recipient plus self copy, selected-message history and DM relay preferences. Relay AUTH is bound to the actual service and request. |
| Shared identity | New 2-of-3 group setup, independent event approval, actual BIP340-compatible threshold signing, share backups/restoration and lost-participant recovery. Signing never reconstructs the full key. |
| Client connection | Qualify noStrudel and Coracle through a shared NIP-07 bridge, and Amethyst through the companion's NIP-46 connection. Publish exact tested versions and limits. |

These are release requirements, not a current compatibility claim. Threshold
identities support signing; threshold encrypted messaging needs a separate
protocol and is outside v1. The product must not reconstruct a key or silently
substitute another identity to work around that limitation.

Articles, arbitrary lists/sets, group/file messages, legacy NIP-04, upload/HTTP
authorization, MLS/Marmot, a NIP-55 Android bridge, encrypted-backup variants and
payment-related operations are deferred. Unsupported requests fail explicitly.
No compatibility downgrade or generic blind-signing fallback is allowed.

The device receives the whole event, computes its canonical ID, derives its own
review and signs the same immutable event only after local approval. Review
depends on the action: actual text for posts, recipients for private messages,
and service/scope for authorization. Complete exact details remain accessible.
Counts and byte lengths do not replace meaning. Short text is shown completely;
long text has a clearly partial preview and continuous full reader. An explicit
local choice can approve partially reviewed prose for that request only. It loses
protection against malicious text left unseen; the device cannot claim the person
read it. Recipients, services, targets and other fields that grant authority must
still be shown. The host cannot select this exception. No global hide-content
setting or per-kind configuration matrix is needed.

Exact ordered tags and content remain available, with controls and ambiguous
characters made visible. Unknown kinds/tags are refused until their semantics
are supported. A follow-list diff needs an explicitly confirmed signed baseline;
an old valid signature does not establish that it is the latest list.

The companion owns network communication, client adapters and QR presentation.
It independently checks returned signatures. It does not receive the identity's
secret key. Authorized decryption releases selected plaintext to the client;
offline custody cannot protect that plaintext after release to a compromised host.

Rust owns custody, protocol and approval. ESP-IDF/C and LVGL own the existing
board integration and display. The same native screen sources are previewed on
desktop. TypeScript owns companion integration. A portable core is sufficient
preparation for future hardware; extra products and frameworks are deferred.

A finished release requires complete recovery, named-client flows, review and
cancellation behavior, threshold ceremonies, matched artifacts and hardware
qualification. Simulated optical exchange, public fixtures and host tests are
intermediate evidence. USB-disconnected use, physical controls, camera alignment,
entropy, radio isolation, update/boot and secret cleanup need their own evidence.
