# Bridge implementation boundaries

Current product requirements live in [the product contract](../product/contract.md).
This document describes the integrated host implementation. The generated
[SDK API inventory](api.md) and [API boundary review](api-review.md) identify the
actual public surface and its limits. Original companion architecture prose is
preserved in source history at commit 678796900e462f5504e47fe934e2e5f23d85824f.

`apps/bridge` owns the CLI, local service, browser extension and development
consumer examples. `packages` contains private implementation modules and the
sole public `@nsealr/sdk`. The SDK root and browser entrypoint contain browser-safe
namespaces. The explicit Node entrypoint adds host client, framing and NIP-46
helpers. Packed runtime and declarations contain owned code, with explicit
third-party production dependencies and their original license distributions.
Fixtures and development signing helpers are outside the production package.

Bridge prepares requests and untrusted previews, transports messages and verifies
responses. It cannot approve device actions or hold user signing keys. Identity
selection, origin permission, local grants and device consent are separate
boundaries. Host policy metadata cannot silently mutate authoritative device
policy. Route dispatch is unavailable until an explicit dispatcher is supplied;
responses bind the original request and selected public key before acceptance.

The local client keeps bounded request correlation, cancellation and timeout
handling. Native messaging is an explicitly injected exchange. Pairing, storage
and native-host installation use digest-bound review and approval artifacts;
file output uses the reviewed destination. These software APIs do not establish
production installer UX, storage custody or physical transport qualification.
Card routes and APDU implementations are retired. Host review acknowledgements
are unsupported and cannot bypass an active route's review requirements.

The protocol module owns request and response validation. Core owns event
serialization, hashing and verification. QR and serial framing handle bounded
encoding, checksums and payload parsing before routing. Serial stream adapters
retain their byte, line, pending-operation and lifecycle bounds. The Pi harness
and Rust host harness consume the same authoritative contracts while preserving
independent cryptographic/review implementations. No sibling fixture snapshot is
an accepted fallback.

Pure NIP-46 helpers parse descriptor or already-decrypted metadata and validate
request/response steps. The explicit Node session manager and relay adapter have
separate runtime side effects: authenticated transport authors, independently
resolved user identity, signed encrypted messages, bounded pending requests,
terminal close and wiping of the owned client transport-key copy. Metadata does
not restore or authenticate a runtime session. Transport credentials are not
user signing-key custody. Detailed S01 identity, retry and resource bounds remain
in the API boundary review and retained tests.

Browser extension permission, review and approval controls remain secretless.
Deterministic package manifests and VM/DOM checks do not prove installed browser
compatibility. The retained Firefox target still uses a service-worker manifest;
Firefox background execution needs separate C01/P02 qualification and repair.
No universal Firefox compatibility is claimed by package test success.
