# QH01 manual static-QR service port

Owner `/root/b01_final_review`, Sol6.1 xhigh. Preparation input is source-under-PR
`2da6938171b2133e0796d946906cb84a0f8c90f0`, tree
`2b45fde5247e75412f257fe288312b7bdccf8348`. It is not actual-main adoption.
Runtime edits wait for root's explicit actual-main source-adoption message;
these source/expectation roles remain historical after an identical-tree rebase.

The smallest sufficient seam is a service-only `createManualQrRouteDispatcher`
in new `apps/bridge/service/src/manual-qr.ts`, with its adjacent meaningful tests.
It returns an existing `createRouteDispatcher` for one exact account/QR route.
Actual `handleLocalServiceRequestAsync` keeps grants, account/capability snapshot,
monotonic deadline, pending reservation until actual settlement, expected-key,
canonical-ID and signature verification. Do not duplicate that lifecycle.
`packages/transport` has Node file/stdio/serial adapters and no required manual
mechanism; no change or browser export of it is needed. No default route or CLI
configuration/readiness is enabled. Direct service dependencies on existing
`@nsealr/qr` and `@nsealr/protocol` require only two workspace importer links in
the lockfile; root authorizes that exact delta after actual-main adoption.

The fixed interface is an injected opener receiving `ManualQrPortControl`:
account ID, QR route type, request ID, expected public key, abort signal,
`before_present`, maximum response raw-frame bytes and decoded-JSON bytes.
It returns one `ManualQrPort` with `present(envelope)`, one `scan()` returning an
original static-envelope string or null, and required `close()`. Methods may be
asynchronous. Only public get-key/sign-event work is admitted by this adapter.
Original scan bytes reach the existing strict QR/protocol validators; do not
deserialize/re-encode first. Independent expectations reuse existing public
signed fixtures, with Node Buffer for expected envelope bytes and Node hashing
only for the synthetic local review-plan observation. No identity key or signing
operation exists on the host.

The service revalidates immediately before calling presentation. A trusted port
that delays actual presentation must call `before_present` again immediately
before exposing the request. This is the existing host-currentness hook, never
physical consent, evidence or device-side recall. The injected port owns native
buffer/callback cleanup and must enforce the supplied caps before its own
allocation/decoding. The software adapter independently checks raw length before
conversion, exact decoded size before base64/JSON parsing and actual cumulative
exchange work. It reserves request JSON/frame plus bounded response JSON/frame
payload bytes against both effective retention limits before opening. This is
logical public payload accounting, not a JS heap/physical RAM measurement.

One exclusive port reservation spans actual open, present, single scan and close
settlement. There is no adapter timer, pending/session engine, queue, retry or
result/approval cache. Host timeout/abort promptly invalidates the existing
client hook, but an uncooperative promise remains reserved until it really
settles. The adapter discards late scans before conversion. The supplied port
must not be shared through another owner/factory. A rejecting opener or cleanup
cannot establish reusable native state: quarantine this owner; do not equate a
settled rejection with closed hardware or automatically retry it. Cleanup errors
preserve any primary failure. Only confirmed successful close allows reuse.

All expectations/test definitions precede runtime edits. Because the new adapter
does not yet exist, initial RED may be module absence, not execution of the
declared behavioral cases; record that distinction. Final tests must exercise
the real client path, exact public fixtures, identity/request/output tampering,
late and repeated scans, individual effective dimensions and cleanup across
every asynchronous phase. Preserve failures and source/environment bindings.
Use existing focused service/client tests and typecheck, no fullCI/corpus/poll.

Writable runtime scope after root's source gate: the two new service files,
service package manifest and only the two justified existing workspace lock
links. All other product/graph/shared-handoff/protocol/limit/core/QP/old-proof,
registry/vendor/bootstrap/CI source stays unchanged. This package does not
qualify camera/UI/native resources, a real Nostr client's timing, framing/UR,
seed custody, provider, device recall or physical release. All five QH01 criteria
remain incomplete; root separately reviews/adopts the exact final component.
