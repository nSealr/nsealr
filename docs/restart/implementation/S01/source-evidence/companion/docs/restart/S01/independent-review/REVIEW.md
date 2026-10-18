# Independent S01 review — correction required

Reviewer: `/root/independent_bridge_review`. Product candidate: `d385ddb0c775a1e863e9db0ee9ae38fee5f19057`; baseline: `13414320537d0208fc3ef8e43bd0723c98c1d5e0`. Author evidence commit: `143e6fb260431dc9cb97a72d6c019e3c6c5c6bf1`. This review makes **no final pass, merge, S01 closure, external-client or physical-device claim**.

## Blocking finding F01: listeners survive asynchronous destruction without a close event

`packages/transport/src/transport.ts`, `SerialLineStreamPort.fail`, `onInputClose`, and `onOutputClose` remove owned error/close listeners either synchronously if the stream is already closed, or when its `close` event arrives. A valid Node stream can complete destruction asynchronously with `emitClose: false`. Once that stream is closed, neither cleanup path runs. Both input and output retain the port's `error` and `close` listeners, and those closures retain the port and its stream references. This violates S01-QUEUE-03's explicit removal of owned listener references after closure.

The isolated reproduction uses standard `PassThrough` streams with `emitClose: false` and an asynchronous `destroy(error, callback)` implementation that calls `callback(error)` on `setImmediate`. After `port.close()` and two event-loop turns, both public `.closed` properties are true. Each stream still has one port-owned `error` and one `close` listener; the original `prefinish` listener is correctly treated as inherited. Synchronous destruction and asynchronous destruction with the default `emitClose: true` are passing controls.

Run after the normal package build:

```sh
node docs/restart/S01/independent-review/async-destroy-cleanup.mjs
```

The retained command manifest and raw failure are `async-destroy-cleanup.json` and `.log`. Expected contract outcome is exit 0 and only inherited listeners remaining in all four configurations; observed candidate outcome is exit 1 in the asynchronous, suppressed-close case. This is a generic custom-stream cleanup defect. It is not evidence of an identity bypass, ordinary SerialPort exploit, or default relay exploit. Root classified the cleanup conformance failure as blocking until corrected. Product changes require affected review and final gate evidence again.

## Positive evidence, scoped to the candidate

`adversarial.mjs` is independently authored and uses nostr-tools for wire encryption, outer signing and inner-event signing, rather than the implementation's wire builders. Its 13 cases pass. They cover foreign-author injection during ack/discovery/signing; ambiguous recipient tags; escaped duplicate/trailing/oversized plaintext; changed user/template/id/signature; invalid curve discovery followed by retry; template snapshots; old subscription callbacks carrying the **current** ID; 100 attempts against each stalled publication/acquisition cap; six response/publication/cancel schedules; escaped JSON duplicate aliases at all 32 depths; 30 decoded chunk partitions against an independent byte model; and ordinary stream first-error cancellation/cleanup. The new F01 probe demonstrates that the ordinary cleanup controls were insufficient.

An actual loopback HTTP-upgrade/WebSocket peer deliberately ignores the subscription filters and sends five signed or altered events. The default `NostrToolsRelay` and locked SimplePool deliver only the valid matching event. Source inspection also confirms signature verification and author/kind/recipient filtering before the callback. Thus baseline foreign-author acceptance when a custom adapter bypasses filters remains distinct from default-adapter exploitability.

Independent targeted execution passes 232 tests, with one explicitly gated Docker test skipped. These include the CLI metadata structural comparator's object-key-order control and value/type/array-order/missing/extra failures. The reviewer did not rerun Docker or full `make ci`. The author's exact-source records show full CI (686 pass, one gated skip), targeted (232 pass, one skip), and Docker live relay (one pass). All 20 listed author artifact hashes, three final gate source/log bindings, three pinned NIP raw-file hashes, and the two installed dependency hashes were independently verified. The author evidence commit changes only evidence files relative to the reviewed product source.

## Specification and boundary assessment

The accepted brief adequately distinguishes authenticated outer transport identity, optional expected user selection, immutable resolved identity, canonical signed output, and bounded manager-owned requests. Its timeout semantics explicitly separate logical cancellation from uncancellable adapter promises. The candidate implements the inspected identity and parser rules, but F01 prevents claiming the full stream cleanup contract.

The protocol distinction is supported by [pinned NIP-46](https://raw.githubusercontent.com/nostr-protocol/nips/37db639582d857e12468dcccd99b2c7f1d657da9/46.md), and signed-event verification follows [pinned NIP-01](https://raw.githubusercontent.com/nostr-protocol/nips/37db639582d857e12468dcccd99b2c7f1d657da9/01.md). Protocol hashes are retained in `author-evidence-assessment.json`; no external security certification is implied.

Origin permissions, account-selection UX, device approval, production keys, and arbitrary caller/OS/WebSocket memory or CPU limits remain separate boundaries. Metadata helper v1 reports user-key equality only when an expected key is supplied and leaves authority flags false; its public-key shape check is not session curve authentication. The existing in-repository manager consumers are tests, while the service owns the serial stream path. The local Docker signer is not a named third-party client.

Root's separate specs integration brief `6e7b01e2ad98738c006a08226d6d09e2e02ee597` was reviewed and accepted for its bounded v1 oracle/fixture migration, with explicit guidance to test raw UTF-8 size, depth and escaped duplicates. Its final implementation is **not yet reviewed**. Cross-repository acceptance cannot silently select old v0 response fixtures or be waived by the companion's vendored snapshot.

## Reproduction and provenance limits

All review files are isolated under this directory; no product source or main graph was changed. Node v24.22.0 and pnpm 10.33.4 executables were read from the author's tool installation. Dependency bytes were copied into a private reviewer pnpm store and installed with `--offline --frozen-lockfile` (84 reused, zero downloaded). All package artifacts were rebuilt in this worktree; no author `dist` output or workspace dependency symlink was used. Commands, versions, candidate, dirty state, brief/source hashes and raw-log hashes are recorded by `run.py`. The initial install/build logs and initial 12-case probe log are retained; the later 13-case run adds actual loopback I/O. Fixtures use only public scalar test keys. Independence here is separate author/reviewer work and a separate experiment, not an external human audit.
