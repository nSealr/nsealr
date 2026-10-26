# Public S3 live client/service wiring

This is a named, opt-in public fixture for V01/C01 review. It connects the actual
LocalServiceClient, Commander CLI, one-shot service, route driver and serial-line
transport to the current public S3 image. It closes no product criterion. The
ordinary compatibility/readiness path still requires its current provider;
this path does not invent get_capabilities, reported capabilities, complete-page
observations, USER states or target CPU measurements.

The device source is e7f04215fc97808acdafdbf9420f6ef6d0102c5b; its app SHA256 is
7943dbcf4a1e389718b1959086487b6b13cdb50bb0f577ced9d4539c6d1fd7da.
The independent, published scalar3 pin is
f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9.
These are local admission constants, not an attestation from the connected
device. Never import a real identity into this fixture. Its only signing
template is kind1, created_at1710000000, content "S3 public physical approval",
tags[]; each operation gets a fresh request ID.

## Path and authority

Linux runs the product:

```text
CLI -> LocalServiceClient -> native-message child service
    -> current grant/account selection -> public_s3_stream driver
    -> SerialLineTransport -> local Unix socket
    -> SSH reverse Unix forwarding -> Mac raw USB relay -> S3
```

The Mac script performs bounded byte plumbing and captures bytes. It does not
parse Nostr or approve requests. This lab arrangement does not qualify a Mac
installer, browser, NIP-46 relay, production transport or public client release.

The service opens one stream before the operator prompt. The Mac relay opens
the associated USB port and sends the private ASCII plumbing header
nsealr-public-usb-open-v1 followed by newline only to the Unix stream. The
header is consumed locally and never sent to S3; it is not a firmware message,
readiness response, device attestation or human consent. Opening USB can change
DTR or reset the public device. Root must use the currently associated port.

Only after the CLI has received the service's stream-open message does it ask
the operator to Enable on S3 and press Enter on the host. That setup has a
separate 60s ceiling. While waiting, no LocalServiceClient operation, signing
request, pending reservation or operation clock exists. USB/socket processing
remains asynchronous. Enter starts transmission; S3 alone performs physical
review and Approve/Reject. Enter never approves signing.

After Enter, the CLI samples a continuous monotonic origin before configuration
preflight and LocalServiceClient dispatch. Both service and CLI re-read current
grants/configuration, check the private original pin, bind one connection ID and
generation, and reject changes. The service has one owned pending request and
one write, with no retry. It revalidates after response crypto and actual local
stream destruction. The CLI collects child exit plus stdin finish and stdout/
stderr EOF before verifying again and linking a new result file. Existing
output is refused before setup. Failure, corruption, expiry or revocation
produces no successful result file. Bytes already written or queued cannot be
recalled.

Connection generation is a local observed stream lease, not an S3 boot epoch.
Local close completion is not proof that a remote USB handle has already
closed. Root must inspect the Mac relay report (including USB close return),
tunnel lifetime and actual serial log; the hardware close/reset race remains a
physical gate. An arbitrary same-process callback is part of the host TCB.

## Budgets and limits

This explicit public variant has an absolute continuous host deadline of100s.
It does not increase or replace the native C5000 leaf budget. The service
meters ACTIVE wall time plus its own process CPU during the single external
response phase, with a5s cap and monotonic/counter rollback checks. External
means transport/device work; silence never becomes USER. Device CPU and USER
wall accounting are unavailable, so neither end-to-end C5000 nor the future
human-wait contract is qualified. The CLI also bounds its whole operation
continuously at100s; setup is separate and never subtracted from an active
operation. Event-loop timers cannot forcibly stop arbitrary synchronous code.
A failed operation waits for actual child collection, escalating TERM to KILL
after4s, without a hard cleanup-time claim.

The unmodified S3 uses its real floor-second100tick deadline (up to1s early);
physical review/lock/fresh-edge behavior remains the device's responsibility.
The public e7 instrumentation permits one aux attempt per boot and four startup
diagnostic draws; those are instrumentation budgets, not future session
requirements. A query consumes its own Enabled operation. No query is invented
as a capability or identity-admission signal.

Actual local bounds: request JSON320B, response JSON704B, one newline frame
1024B, no parsed request queue; service stream8192B/nine lines and at most eight
ignored diagnostic lines; IPC payload16384B. Context JSON is a regular file
read with a64KiB ceiling. Setup handshake5s, CLI setup60s, local close grace4s.
The raw relay accepts one connection within120s, then has a separate180s lease
ceiling, 1024B chunks, 64KiB per direction and1s USB/socket write timeout.
Overflow/EOF/error closes the single connection; no reconnect or replay loop.

The named implementation alone admits volatile_session for esp32_no_se.
Existing persistent implementations and their deferred recovery model remain
unchanged. The fixture has no secret backup/recovery claim. The existing
pairing, storage approval and live grant expiry/revocation checks remain in use.

## Prepare the reviewed Linux fixture

Use this checkout's existing toolchain and built service dependencies. From the
repository root, create a new private absolute LAB directory. Copy the adjacent
accounts.example.json and drivers.example.json into it as accounts.json and
drivers.json. The example driver uses /tmp/nsealr-s3-public-root.sock; review
that exact endpoint and its owner. No example contains a grant or approval.

Request and inspect the actual pairing intent:

```sh
pnpm nsealr local public-s3-pairing --out "$LAB/intent.json"
pnpm nsealr local review-pairing --intent "$LAB/intent.json" --out "$LAB/pairing-review.json"
```

Read the review and confirm its client identity and four operations. Then use
the digest actually reviewed, current UTC integer seconds and a short expiry
(for this run, ten minutes is suitable):

```sh
pnpm nsealr local approve-pairing --intent "$LAB/intent.json" --reviewed-pairing-digest "$PAIRING_DIGEST" --approved-at "$NOW" --expires-at "$EXPIRES" --out "$LAB/pairing-approval.json"
pnpm nsealr local review-storage --grant-store "$LAB/grants.json" --grant-store-output "$LAB/grants.json" --account-store "$LAB/accounts.json" --route-driver-store "$LAB/drivers.json" --out "$LAB/storage-review.json"
```

Read the exact paths/access modes and storage digest. Only after that review:

```sh
pnpm nsealr local approve-storage --review "$LAB/storage-review.json" --reviewed-storage-digest "$STORAGE_DIGEST" --approved-at "$NOW" --out "$LAB/storage-approval.json"
pnpm nsealr local grant-store append-approval --approval "$LAB/pairing-approval.json" --storage-approval "$LAB/storage-approval.json" --updated-at "$NOW" --out "$LAB/grants.json"
```

The read-only and write-new grant paths are both explicitly reviewed. Public
dispatch rejects --now and requires real current time. Reusing a revoked or
expired grant fails. A changed file requires a fresh setup rather than silently
changing an in-flight selection. These are host approvals for service access,
not device approval.

## Root-only Mac plumbing and physical run

These are reviewable instructions, not a record of an executed hardware run.
Root alone opens USB after distinct candidate review. Close other openers.
Copy the exact reviewed tools/bridge/public_s3_usb_relay.py to the Mac and compare
its hash with the source receipt. With a new capture directory whose parent
exists and a root-associated private port:

```sh
/Users/vincenzo/Projects/nsealr/tools/esptool-5.6.0/bin/python public_s3_usb_relay.py --port "$ASSOCIATED_S3_PORT" --socket /tmp/nsealr-s3-public-mac.sock --capture-dir "$NEW_CAPTURE_DIR"
```

In another Mac terminal, establish only a local Unix forwarding endpoint:

```sh
ssh -N -o ExitOnForwardFailure=yes -o StreamLocalBindUnlink=no -o StreamLocalBindMask=0177 -R /tmp/nsealr-s3-public-root.sock:/tmp/nsealr-s3-public-mac.sock tux
```

This creates no TCP/public listener. Refuse existing socket paths and inspect
old owners; never blindly unlink another process's socket. The relay removes
only the socket inode it bound. Root owns SSH shutdown and removal of its exact
forwarding endpoint after process close. It is a one-operation relay; start
new reviewed plumbing for another run.

On Linux, after the tunnel is ready:

```sh
pnpm nsealr local dispatch-public-s3 --grant-store "$LAB/grants.json" --account-store "$LAB/accounts.json" --route-driver-store "$LAB/drivers.json" --storage-approval "$LAB/storage-approval.json" --expected-public-key f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9 --out "$LAB/result.json"
```

Wait for the stream-open/Enable prompt, perform fresh physical Enable, then
press Enter. Inspect every device page and use only the physical Approve or
Reject gesture. For a public-key query, add --method get_public_key; the image
supports it, not get_capabilities. Use a fresh Enabled operation for each query
or signature. Root must respect current public-image instrumentation and its
own known boot state; this client never resets or retries the device.

A successful result records the actual generated request, response and local
settlement. Root should retain the original relay RX/TX/report, tunnel/child
closure observation and device UI observations, then use the existing independent
BIP340 oracle on the captured actual request/response. Host socket fixtures and
existing captured-device playback are not this live physical run.

## Evidence boundary

Focused host checks cover the real Commander/LocalServiceClient/child-service/
Unix-stream path using a public scalar3 test responder, including a real delay
above5s, unsupported admission, pin/request/event/checksum substitution,
revocation, setup EOF, bounded setup/operation timeout and actual stream-close
completion. Draft compiled regressions are retained as expected REDs; subsequent
affected source checks establish the corrections. They do not measure S3 CPU,
physical USB resets, DTR/suspend behavior, installed UX, entropy quality or
custody. Human-wait source81 and its original positives/14negative readback remain
historical experimental inputs, not adopted APIv2 production behavior. S04,
native C5000, firmware source/core and other device scopes remain unchanged.
