# @nsealr/service

Private native-messaging host scaffold for the nSealr local companion service.

## Purpose

- Run the length-prefixed native-messaging stdio loop used by browser hosts.
- Return deterministic malformed-frame errors instead of unstructured output.
- Carry grant-gated local-service requests, including deterministic
  `signer_route_unavailable` dispatch refusal when no reviewed signer driver is
  configured.
- Await package-owned async local-service dispatch so future reviewed signer
  drivers can use asynchronous I/O without changing the native-messaging
  framing contract.
- Load explicit storage-approved secretless route-driver stores for reviewed
  host-owned drivers. The first supported driver is exact account/route/USB
  serial-line dispatch.
- Normalize serial-line driver open, timeout, protocol, I/O, close, and
  fallback failures into deterministic local-service transport error codes.
- Render validated Chromium and Firefox native-host manifest JSON from the
  shared `@nsealr/client` manifest contract for future installer work.
- Render digest-bound native-host install approval JSON from a reviewed install
  plan without installing manifest files.
- Execute an approved native-host manifest install only when the caller supplies
  the approval artifact and reviewed install digest; the command creates the
  reviewed parent directory and writes the reviewed manifest path with
  `write_new` semantics.

## Manifest Example

```sh
pnpm --filter @nsealr/service service -- --native-host-manifest chromium \
  --host-path /Applications/nSealr/nsealr-service \
  --extension-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

pnpm --filter @nsealr/service service -- --native-host-install-plan chromium \
  --host-path /Applications/nSealr/nsealr-service \
  --manifest-path "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts/dev.nsealr.companion.json" \
  --extension-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

pnpm --filter @nsealr/service service -- --native-host-install-approval ./native-host-install-plan.json \
  --reviewed-install-digest <digest-hex> \
  --approved-at 1900000000

pnpm --filter @nsealr/service service -- --native-host-install-execute ./native-host-install-approval.json \
  --reviewed-install-digest <digest-hex>
```

## Explicit Context Example

```sh
pnpm --filter @nsealr/service service -- \
  --grant-store "$PWD/local-grants.json" \
  --account-store "$PWD/local-accounts.json" \
  --route-driver-store "$PWD/local-route-drivers.json" \
  --storage-approval "$PWD/local-storage-approval.json"
```

Context files are loaded only from explicit paths covered by a storage approval
artifact. The service validates the storage approval, secretless grant-store,
account-store, and route-driver formats before entering the stdio loop. The
reviewed paths must be absolute and already expanded before use.
They may authorize route selection, request validation, response verification,
or dispatch. Route-driver stores must also be explicit, secretless, and exact:
each serial-line driver names `account_id`, `route_type`, `transport: "usb"`,
and a local serial path. A route-driver store is accepted only together with an
account-store that contains the same account id, route type, and transport, so
stale driver files fail during context loading instead of later at dispatch
time. The service never writes those files, chooses a default storage location,
or approves a client by loading a file.

A route-driver store uses this shape:

```json
{
  "format": "nsealr-service-route-driver-store-v0",
  "updated_at": 1900000000,
  "contains_secret_material": false,
  "routes": [
    {
      "account_id": "acct-esp32-usb-slot-0",
      "route_type": "esp32_usb_nip46",
      "transport": "usb",
      "driver": "serial_line",
      "serial_line": {
        "path": "/dev/cu.usbmodem1101",
        "response_timeout_ms": 30000
      }
    }
  ]
}
```

Route-driver files reject QR-vault route types, non-USB transports, empty route
sets, duplicate account/route/transport entries, unsupported fields, broad or
remote serial paths, and secret field names such as `nsec`, `mnemonic`, or
`passphrase`. The parser also bounds `max_ignored_lines` to at most 128 and
`response_timeout_ms` to at most 120,000, so an approved driver file cannot
turn native-host dispatch into an unbounded wait or log-skip loop. Accepted
serial paths are local device identifiers only:
`/dev/cu*`, `/dev/tty*`, `/dev/serial/by-id/*`, `/dev/serial/by-path/*`,
`COMn`, or Windows `\\.\COMn` paths encoded in JSON as `\\\\.\\COMn`.

## Boundary

This app is private and secretless. It does not persist grants, write account
stores, open relays, configure signer drivers by default, or hold production
signing material. Its async stdio path only awaits an explicitly configured
or injected dispatcher. The serial-line route driver opens only the exact path
provided in an explicit route-driver store and still relies on the device to
own trusted review, approval, and signing refusal or signing behavior. Manifest
generation and install-plan generation only print JSON. Install approvals are
also JSON-only and keep `writes_files=false`; the separate install execution
command is the only path that writes a native-host manifest, and it writes only
the reviewed path from the approval artifact with exclusive create semantics.
File-backed context loading is an explicit storage-approved read-only developer
and integration harness until approval UX and production driver acceptance are
specified.
