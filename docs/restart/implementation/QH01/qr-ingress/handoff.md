# Experimental QR ingress guard handoff

The authored component is ready for root's distinct exact review. Runtime and
tests are frozen at `447dd235aab5483e88094eca881457e9c3709d8c`, on accepted main
`5d047b5d3150d58a1a45caf00c8946b7f18364bb`. Only `qr.ts` and `qr.test.ts` change
outside this proof directory. No QH01 criterion or graph status is closed.

[Independent expectations](expectations.json) and all27 test definitions were
committed first at `4e2a732b`. [The actual pre-fix RED](pre-fix-red/command.json)
on unchanged runtime has five failures and22passes, frozen in `988ff636`:
oversized static input reached allocation, malformed oversized input reached
lexical work, an oversized whole animated frame reached split, excessive exact
chunks reached decode, and an over-budget raw collection performed64checksums.
The test bytes/assertions remain exact after implementation. Original golden
vectors and under-limit malformed paths remain active; no negative was weakened.

The correction derives every ceiling from existing provisional codec limits and
format widths. Static length is checked before `slice`. Animated count64 was
already checked early and is retained. A length-only preflight checks each whole
frame and cumulative raw characters before parsing any frame; exact cumulative
chunk characters are then checked before joining/base64 conversion. The one
joined string is reused for canonical validation. All existing integrity,
UTF-8/JSON and frame-set checks remain.

[Focused tests and typecheck](focused-green/commands.json) pass:27/27 QR tests
and existing `pnpm typecheck`. [Affected final checks](final-affected/commands.json)
pass the QR-only existing build argv, docs, plan, frozen1,508/fiveP01 and unchanged
T01 artifact source validation. Initial worktree setup used existing pinned
offline dependencies/frozen lock and the normal package build to supply current
exports, never another checkout's dist. No full product suite, crypto corpus,
hosted CI, PR or physical probe was run. Raw RED output and diff whitespace remain
exact. [Source scope](source-scope.json) and [artifact inventory](artifact-manifest.json)
bind the finite package; the final immutable Git commit binds the proof tail.

These are experimental software codecs, with caller-owned strings/arrays already
allocated before entry. The guards bound later codec work; they do not qualify
image allocation, native scanner/decoder, actual latency/memory or arbitrary
host-JS behavior. Checksums do not authenticate senders or create consent.
Identity/request/output correlation, pending/replay/cancel/client deadlines,
seed-channel separation, actual optical UX and a real-screen/camera comparison
with maintained multipart UR remain QH01 work. No framing freeze, new format,
key/signing/provider/device integration or physical release follows. Root owns
the exact component review and normal protected adoption gates.
