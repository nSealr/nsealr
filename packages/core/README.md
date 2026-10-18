# @nsealr/core

Core Nostr event helpers for nSealr host software.

## Purpose

- Compute NIP-01 event ids from canonical event serialization.
- Verify BIP-340 Schnorr signatures for signed Nostr events.
- Verify that a signer response matches the original nSealr signing request.

## Example

```ts nsealr-readme-example
import assert from "node:assert/strict";
import { computeEventId } from "@nsealr/core";

const eventId = computeEventId({
  pubkey: "0".repeat(64),
  created_at: 1_710_000_000,
  kind: 1,
  tags: [],
  content: "hello from nSealr"
});

assert.equal(eventId.length, 64);
```

## Boundary

This package never creates, imports, stores, or exports production private keys.
It is safe to use in host-side verification code, browser-provider code, CLI
tools, and tests.

Test-only signing lives in private `@nsealr/dev-signer`, not here.
