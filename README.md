# nSealr

**Keep your Nostr key offline.**

nSealr is an open-source Nostr signer for the Waveshare ESP32-P4 3.5-inch board.
Use the device to create or load an identity, review requests and return signatures
by QR. The companion connects your device to Nostr clients.

- Recover an identity from an nsec or BIP39 words, with an optional passphrase.
- Read the action and content before you sign. Open exact details when needed.
- Keep the identity key on the device during normal use.
- Use standard Nostr events and client APIs.

## Source

- `core/`: identity, Nostr events and signing.
- `firmware/`: device application and native screen renderer.
- `companion/`: client connection and QR exchange.

MIT license. Third-party code retains its own licenses.
