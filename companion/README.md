# nSealr companion

Connect Nostr applications to your offline nSealr. The companion displays each
request as QR, scans the device response, and verifies returned event IDs and
signatures before returning them to the application.

## Open the companion

Use Node 24 or later. In this directory:

```sh
npm ci --ignore-scripts
npm run check
npm test
npm run build
npm start
```

Open http://127.0.0.1:8787. Camera access needs localhost or HTTPS. No server
receives your camera frames; the bundled QR decoder runs in the browser.

Select an npub to require that identity, or choose **Read from device** without a
selection to learn its public key. Scan the displayed request with your nSealr,
review it on the device, then use **Scan device response**. Compare the full
public identity with the device or your backup. An npub selected manually is a
public identifier; it does not prove possession of its private key.

Write a note and choose **Review on device**. After approval, scan the response.
The companion checks the exact original event, public key, canonical ID and
BIP340 signature. Choose a relay and **Publish event** to publish. A verified
signature alone does not mean a relay accepted the event.

## Browser extension

Build first. In Chromium's extension settings, enable developer mode and load
`dist/` as an unpacked extension. In Firefox, open `about:debugging`, choose
**This Firefox**, then **Load Temporary Add-on** and select
`dist/firefox/manifest.json`. Temporary Firefox installation ends on restart.
Use Firefox 128 or later. Signed store distribution is a separate installation
step; these instructions do not install or publish an extension automatically.

Reload the Nostr website after installation. Disable another NIP-07 extension
if it already supplies `window.nostr`. The companion tab opens when the website
requests a key or signature. Read the actual website origin in the permission
dialog. Permission admits that method for this session; every operation still
requires a device round trip. Closing the client, cancelling the request,
closing the companion, changing identity or disconnecting invalidates pending
requests. **Revoke** removes a website's permission.

The extension implements `getPublicKey`, `signEvent`, `nip44.encrypt` and
`nip44.decrypt`. It does not expose the identity's private key or implement
legacy NIP-04. Client support depends on the operations it requests; unsupported
device methods, kinds or tags return errors rather than blind signing.

## Mobile and remote clients

Choose a secure `wss://` relay and **Open session**. Paste the pairing link into
the client's remote-signer login. Check the displayed client public key before
allowing the connection. Alternatively, paste the client's `nostrconnect://`
link into the companion; it must include the relay you opened.

The browser generates a separate, disposable NIP-46 transport key. It encrypts
and signs relay messages, while identity signing and NIP-44 requests use the
same QR/device flow as the extension. Client names are not proof of identity.
Pairing links contain a one-use secret; share them only with the intended client.
Keep the companion tab open. Closing or reloading it ends the remote session;
pair again with a fresh link. Session transport keys and permissions are not
saved to browser storage. JavaScript cannot promise physical memory erasure.

NIP-44 decrypt releases plaintext to the requesting client after device consent.
That client can store or disclose it. The device determines which workflows are
admitted. The remote service queues at most four operations for one paired client,
so recipient and sender-copy requests can proceed one device operation at a time.
Cancellation or an identity change invalidates the queued work.

## Private text messages

Enter one to three discovery relays under **Private messages**. The companion
uses signed kind-10050 preferences to find inbox relays for you and the recipient.
It does not send to a guessed inbox. Use **Your message inbox** to sign and publish
your own preferences when needed. A relay list is the newest valid list observed
on your chosen discovery relays; this does not prove there is no newer list elsewhere.

Choose one recipient and write your message. The complete unsigned rumor must fit
4096 UTF8 bytes, including its metadata and JSON escaping. The device reviews each
encryption and seal signature. The companion then makes separate ephemeral gift
wraps for the recipient and your own copy, and publishes each only to its signed
inbox list. Per-copy status distinguishes relay acceptance and failure. Retrying
reuses the same encrypted event and skips relays that already accepted it.

**Load recent inbox** fetches encrypted envelopes from the last 30 days, up to
30 per inbox and 60 total. Nothing is decrypted automatically. Select a message,
review the requests on the device, and scan both responses. The companion verifies
the outer signature and recipient, the seal signature, and the inner author's
identity, recipient set and rumor ID before displaying the selected plaintext.
**Clear local messages** removes it from the interface. Browser memory erasure
is not guaranteed, and another client may keep plaintext after release.

An inbox relay may request NIP-42 authorization. That exact socket's relay URL
and challenge go to the device for approval. Group/file messages, disappearing
message metadata and legacy NIP-04 are not admitted by this text-message flow.
Relay acceptance does not prove the recipient received or read the message.

## Development checks

`npm test` exercises the optical bounds, hostile data, immutable event matching,
signature verification, cancellation and origin permissions. No real identity
keys belong in tests. Browser and device observations must be recorded separately;
a simulated device response is not evidence that the physical signer works.

With Playwright Chromium installed (`npx playwright install chromium`),
`npm run test:browser` opens an isolated profile and the built extension. It scans
QR pixels from a synthetic video stream, checks NIP-07 requests and cancellation,
and waits through the browser's worker idle interval. It does not access a
physical camera or publish test events. Outputs stay under `.cache/`.

`tests/clients.mjs` drives the real Coracle or noStrudel interface with a loaded
extension or NIP-46 session. `tests/messages-browser.mjs` checks composition and
selected receive against the persistent native Rust owner. Both use local relay
models and synthetic camera input. See [client qualification](CLIENTS.md) for
the source pins, commands, observed paths and remaining limits.

Sources: [NIP-01](https://github.com/nostr-protocol/nips/blob/master/01.md),
[NIP-07](https://github.com/nostr-protocol/nips/blob/master/07.md),
[NIP-17](https://github.com/nostr-protocol/nips/blob/master/17.md),
[NIP-19](https://github.com/nostr-protocol/nips/blob/master/19.md),
[NIP-42](https://github.com/nostr-protocol/nips/blob/master/42.md),
[NIP-44](https://github.com/nostr-protocol/nips/blob/master/44.md), and
[NIP-46](https://github.com/nostr-protocol/nips/blob/master/46.md),
[NIP-59](https://github.com/nostr-protocol/nips/blob/master/59.md).

Fonts are unchanged website assets: Inter and JetBrains Mono. Their upstream
OFL licenses are included in `fonts/`. Build dependencies are pinned by the
lockfile; bundled dependency license notices accompany the generated scripts.
