# @nsealr/transport

Secretless signer transport contracts and adapters.

## Purpose

- Define host-side signer transport interfaces.
- Provide JSON file, JSON-lines stdio, serial-frame, and serial-line helpers.
- Verify successful `sign_event` responses before returning them to callers.

## Example

```ts nsealr-readme-example
import assert from "node:assert/strict";
import { encodeSerialFrame } from "@nsealr/framing";
import { exchangeSerialLineRequest, type SerialLinePort } from "@nsealr/transport";

const request = {
  version: 1,
  request_id: "readme-transport",
  method: "get_public_key"
};
const port: SerialLinePort = {
  async writeLine() {},
  async readLine() {
    return encodeSerialFrame({
      type: "response",
      payload: {
        version: 1,
        request_id: request.request_id,
        ok: false,
        error: {
          code: "signing_disabled",
          message: "No signer connected",
          retryable: false
        }
      }
    });
  }
};

const response = await exchangeSerialLineRequest({
  path: "memory",
  request,
  openPort: () => port,
  responseTimeoutMs: 10
});

assert.equal((response as { ok?: boolean }).ok, false);
```

## Boundary

Production transport code must not depend on software signing helpers and must
not store production signing material. Test-only signing transport lives in
private `@nsealr/dev-signer`.


`SerialLineStreamPort` owns its input/output streams and closes both on terminal
error or explicit close (one shared duplex is supported). `maxBufferedBytes`
limits the total queued decoded UTF-8 data, including delimiters and partial
lines, to 1,024 bytes by default (range 1..1,048,576). `maxBufferedLines` limits
complete lines plus a nonempty tail to 64 (range 1..4,096). An oversized delivery
fails before it is retained. The port pauses while complete lines await reading
and resumes when they drain; upstream stream/driver queues have their own bounds
and producers must honor backpressure.

Only one read and one write may be pending. Output lines including newline are
limited to 1,024 UTF-8 bytes; writes wait for callback and, when required, drain.
The first stream or overflow error clears retained data, cancels pending I/O and
remains the error for future operations. Close is idempotent and cancels with a
closed error. Owned listeners are removed after stream closure. Normal EOF drains
bounded buffered lines and any trailing partial line, then returns null. The
one-shot exchange helper closes its port on success, timeout and error.
A recorded destruction error remains terminal after EOF, even when its error
event is suppressed: retained input is discarded and the output is destroyed.

Streams must be live Node `Readable`/`Writable` instances with replaceable
`_destroy` hooks, exclusively owned by the port. The port temporarily wraps that
documented implementation hook to observe asynchronous destruction even with
`emitClose: false`. It delegates the original hook with its receiver and error,
restores its original property descriptor, and keeps error handlers through
Node's queued destruction errors before removing them. Shared duplex streams
have one wrapper. Constructor rejection (including already destroyed streams or
nonreplaceable hooks) restores any installed hooks and leaves no port listeners.
Do not alter the streams' hooks while the port owns them. A custom hook that never
finishes cannot release its destruction observer; pending port I/O still cancels
immediately. There is no polling or attempt to force that callback to run.
