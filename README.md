# nSealr

**Keep your Nostr key offline.**

nSealr is an open-source Nostr signer for the Waveshare ESP32-P4 3.5-inch board.
Use the device to create or load an identity, review requests and return signatures
by QR. The companion connects your device to Nostr clients.

- Generate recovery words from a fresh camera capture or physical dice rolls.
- Recover an identity from an nsec or BIP39 words, with an optional passphrase.
- Copy a SeedQR to paper and scan it back to check your backup.
- Read the action and content before you sign. Open exact details when needed.
- Keep the identity key on the device during normal use.
- Connect browser and remote clients through NIP-07 and NIP-46.
- Review private text messages before encryption or release.
- Share custody across three devices, sign with two, and recover a lost share.

## Use

Use battery power and disconnect both USB cables before loading a key. Scan a
request first or load your key, review on the device, then return the response
by QR. Clear the key when you finish.

See the [device guide](https://nsealr.com/docs/device/) for hardware and the
[companion guide](companion/README.md) for browser and remote client connections.

## Source

- `core/`: identity, Nostr events and signing.
- `firmware/`: device application and native screen renderer.
- `companion/`: client connection and QR exchange.

To check the core and companion together, use Rust from `rust-toolchain.toml`
and Node 24.22 or later:

```sh
npm --prefix companion ci --ignore-scripts
node tools/check_integration.mjs
```

This native check exchanges real optical frames between the Rust signer and the
browser verifier. It uses a public test key; it does not test a physical camera.

MIT license. Third-party code retains its own licenses.
