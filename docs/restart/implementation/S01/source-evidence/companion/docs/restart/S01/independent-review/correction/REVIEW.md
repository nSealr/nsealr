# Correction review — changes requested

Reviewer `/root/independent_bridge_review` reviewed product candidate `da2869792af862e62022744585e5a4681c422838`, following original finding commit `67804a5d1995504a69d2fe49618da8e263ec3d89`. Root identifies `84a6f10599dee61efe63442cb5fe1eaa69f585b5` as the candidate's author evidence-only successor. The original changes-requested report, failure logs and source pins remain unchanged in the parent review directory.

## F01: original reproduction now passes

The reviewer rebuilt the corrected packages in the isolated review worktree and ran the **unmodified** `async-destroy-cleanup.mjs`. All four synchronous/asynchronous and close-event/suppressed-close configurations now release owned listeners. `original-f01.json` and `.log` record that exact-source passing execution. This resolves the original reproduction only; it is not a final cleanup approval.

Source inspection confirms the correction observes each distinct stream's documented `_destroy` hook, restores its saved property descriptor conditionally, deduplicates completion, forwards the receiver and error, and delays final cleanup through a `setImmediate`. The reviewed [Node v24.22.0 destruction source](https://raw.githubusercontent.com/nodejs/node/v24.22.0/lib/internal/streams/destroy.js) sets public closed/error state before dispatching queued destruction events. The proposed timing handles that distinction without polling or reading private stream state. Full review of expanded lifecycle behavior is interrupted by the newly demonstrated failure below.

## Blocking F02: known input error after EOF is ignored

Location: `packages/transport/src/transport.ts`, `SerialLineStreamPort.onInputClose`.

The callback only consults `input.errored` when `!ended || cancelWrite` is true. If normal EOF has already set `ended` and no write is pending, a later destruction error whose event was suppressed is silently treated as normal EOF. The input can publicly report `.closed === true` and `.errored === fault`, yet `readLine()` returns stale buffered data and the output remains open. This violates S01-QUEUE-03's first-error, discard and peer-teardown contract, including the newly explicit suppression behavior.

The independent reproduction uses a standard `PassThrough` configured with `autoDestroy: false` and a custom asynchronous destruction hook that completes with `callback(null)`. It first receives `end('stale')`, waits until the public `readableEnded` property is true, and then receives `destroy(fault)`. After completion, Node's public `errored` property preserves `fault` although no error event was emitted. The probe performs no private stream-state access and makes no product changes.

The failure occurs with **both** `emitClose: true` and `emitClose: false`. Controls that forward `callback(fault)` correctly reject with that error and destroy the output. All four observations are printed before the assertion fails. Expected outcome is that both suppressed-error cases also reject with the identical fault, discard buffered data, and destroy the peer.

```sh
node docs/restart/S01/independent-review/correction/error-after-eof.mjs
```

Reviewer-observed exit code is 1. Source/brief hashes, environment, command and raw-log hash are preserved in `error-after-eof.json`; the failure is in `error-after-eof.log`. Root confirmed this is blocking contract nonconformance and requested author correction. This is a custom-stream terminal-error gap, not a demonstrated identity or default-relay exploit.

## Remaining work

The corrected candidate needs renewed independent lifecycle review, this probe passing without weakening its oracle, the retained original probe passing, and final affected exact-source integration evidence. The old 13-case and 232-test results remain pinned to `d385ddb0`; they are not relabeled as executions of this candidate. Root/author report 710 full-CI tests, 284 targeted tests and one live-relay test for `da286979`, but this interrupted review has not independently hash-verified those new final gate records or rerun those suites. The metadata change inspected here only makes the unsupported-result error label version-neutral and updates its fixture expectation; it does not change rejection semantics.

The final sibling specs v1 oracle and fixture migration remains pending separate review. No Bridge pass, cross-repository acceptance, merge, task closure, external-client support or physical-device claim is issued.
