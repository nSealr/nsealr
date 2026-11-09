# Product contract

Status: restart design, 2026-11-09. This describes intended behavior, not a
completed implementation.

One offline device protects one Nostr identity or threshold share per session.
Its primary user wants deliberate control over an important personal or shared
identity. It is not a chat application or payment wallet.

The finished product needs complete create/import, backup, clear and recovery
flows; nsec and English BIP39 with optional passphrase; readable public-event
approval; practical QR/client exchange; and genuine Nostr-compatible threshold
signing. Exact supported workflows and measured limits will be stated explicitly.

The device receives the whole event, computes its canonical ID, derives its own
review and signs the same immutable event only after local approval. Review
depends on the action: actual text for posts, recipients for private messages,
and service/scope for authorization. Complete exact details remain accessible.
Counts and byte lengths do not replace meaning. Unknown operations are refused
clearly rather than silently becoming blind signing.

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
