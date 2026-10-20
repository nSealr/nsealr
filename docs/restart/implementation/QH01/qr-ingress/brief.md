# QH01 experimental QR ingress guards

Owner `/root/b01_final_review`, Sol6.1 xhigh; input accepted main
`5d047b5d3150d58a1a45caf00c8946b7f18364bb`. Root separately reviews the final
candidate and owns protected delivery. This is one finite codec defect correction,
not QH01 completion or a framing decision.

Q01's optical limits and QH01's unchanged acceptance require bounds before
allocation, expansion and expensive work. Current `decodeQrEnvelope` allocates
decoded bytes and re-encodes before its decoded-byte refusal. The animated parser
splits an unbounded raw frame before its field/chunk checks. Collection count is
already limited to64 before mapping and is sufficient for that property; retain
it. Exact cumulative encoded payload is currently joined/decoded/re-encoded
before the4096byte refusal. Individual256character chunks alone permit a much
larger aggregate. Preserve useful existing checks and independent malformed cases.

Use only unchanged `NSEALR_V0_LIMITS` as provisional software codec ceilings:
704 static bytes,4096 animated bytes,64frames,256ASCII payload characters/frame.
Their derived unpadded base64 ceilings are939/5462characters. Existing framing
syntax gives a97character maximum valid overhead and353character whole frame;
5462 plus97 per supplied frame bounds total raw retained/conversion work before
parsing. Then exact cumulative chunk characters must be bounded before joining
or base64 conversion. These derivations introduce no new capacity or format.
Caller-owned strings/arrays already exist; the guards bound subsequent codec
work and allocation, not scanner image creation or arbitrary JS proxy behavior.

[Expectations](expectations.json) and added tests precede runtime edits. Inputs
use independent Node Buffer/crypto construction and valid checksums/digests;
spies observe actual allocation/conversion boundaries rather than timing guesses.
Max−1/max/max+1 checks are separate from malformed grammar and mixed/duplicate
sets, so an earlier fault cannot stand in for the intended property. Capture
actual pre-fix RED, preserve errors, then run the focused existing Vitest command
and existing typecheck. Fresh pinned offline dependencies/build exports are a
worktree prerequisite, not a new package or a full product campaign.

Only `packages/qr/src/qr.ts`, `qr.test.ts` and this scoped proof are writable.
No protocol, limit, old vector/report, lock, dependency, bootstrap, CI, graph or
shared handoff edits. Checksums do not authenticate senders. All five QH01
criteria remain incomplete: actual request/identity/output binding, full pending
session/replay/cancel/deadline/client behavior, UX and real-screen/camera
single-frame versus maintained multipart comparison remain open. No signing,
key custody, seed import/export, physical/native decoder, UR/fountain or optical
qualification follows from these guards.
