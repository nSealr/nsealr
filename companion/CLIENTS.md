# Client qualification

Observed 2026-11-09 on macOS, Node 24.22.0 and Playwright Chromium. These are
specific integration observations, not blanket compatibility or endorsement.

| Client source | Observed path | Evidence boundary |
| --- | --- | --- |
| [noStrudel fa560a51](https://github.com/hzrd149/nostrudel/tree/fa560a51f9702728be3bb85a1203cb9fd7adff60) | NIP-07 and NIP-46 login and creation/publication of a plain text note | Actual client UI, packaged extension or encrypted remote session; Rust host approval, synthetic camera and local relay |
| [Coracle 81581be7](https://github.com/coracle-social/coracle/tree/81581be7d1dec59e274dea2d65096ad5774c7eab) | NIP-07 and NIP-46 login and creation/publication of a plain text note | Actual client UI, packaged extension or encrypted remote session; same host boundaries |
| [Amethyst e3f14a9c](https://github.com/vitorpamplona/amethyst/tree/e3f14a9c8f1efa5d0a1362719f55c3e0fc7d0610) and its [Quartz 48ef376c](https://github.com/vitorpamplona/quartz/tree/48ef376cf41ed10bcb850142dd2022bda4bf6db4) | Source inspection of NIP-46 and concurrent recipient/self-copy requests | Android runtime not tested |

The observed notes had kind 1 and no tags. The browser decoded actual
displayed request QR pixels; the Rust owner generated response frames. A
synthetic video stream then passed those response pixels through the production
scanner. The client received the verified exact event and published it to an
intercepted local relay. No real identity, public relay post or physical camera
was used. Automatic host approval does not test human review on the device.

Source inspection found two ordinary private-message behaviors that affect
interoperability. noStrudel includes both sender and correspondent p tags in its
one-to-one rumor. Amethyst's pinned Quartz implementation can request both seals
concurrently. The device admits that bounded recipient shape; the companion
serializes at most four remote requests. Bulk history decryption, every client
tag/feature, Android UI and Firefox runtime remain separate qualification work.
The Firefox package builds; that alone does not establish browser behavior.

The companion's own private-message UI passed recipient/self composition and
selected two-stage receive against the persistent Rust owner. Both encrypted
copies were independently decrypted and their signatures/rumor IDs checked.
Clearing local messages removed the displayed plaintext. This flow uses the
same synthetic camera and local relay boundaries described above. Full-size
request chunks exposed a decoding failure at the original 384-pixel canvas;
request QR codes now render with whole five-pixel modules, and the browser
regression uses a multipart public note.

## Reproduce the checked paths

Build the companion first. Build the native host runner from the repository root
with `node tools/check_integration.mjs`; it appears at `.cache/integration/optical`.
This runner uses the public scalar-3 test identity and automatically approves
review fields. It is test infrastructure, not a production signer application.

Clone the selected client at the exact pin above and install its frozen lockfile.
Coracle uses pnpm 10.33.0; noStrudel uses pnpm 11.2.2. Coracle's git-pinned
`nostr-signer-capacitor-plugin` at
`be4bb90a1a15c8eec0934f2f66ce9e82ecc72d51` requires its normal TypeScript/Rollup
build. An install with all scripts disabled leaves its browser entry absent;
build that exact dependency rather than replacing the client's signing API.

From this directory, with Playwright Chromium installed:

```sh
CLIENT=nostrudel CLIENT_ROOT=/path/to/nostrudel CORE_RUNNER=/path/to/optical node tests/clients.mjs
CLIENT=coracle CLIENT_ROOT=/path/to/coracle CORE_RUNNER=/path/to/optical node tests/clients.mjs
```

Set `CLIENT_MODE=nip46` to exercise the actual remote-signer login instead of
the loaded NIP-07 extension. All nonlocal HTTP requests are blocked and relay
WebSockets are intercepted. Source code and signing APIs are unchanged. The
client's Vite server and browser caches are local artifacts. Screenshots, public
test requests, returned events and errors stay in ignored `.cache/` directories.

For the companion's own private-message UI:

```sh
CORE_RUNNER=/path/to/optical node tests/messages-browser.mjs
```

This uses the runner's persistent `--session` mode so encryption receipts remain
available to subsequent seal signatures and selected decryptions. The test
independently decrypts and verifies both outgoing copies, then opens the sender's
copy through the actual two-stage UI. It does not test a public relay's retention,
recipient availability, physical optical quality or disconnected operation.
