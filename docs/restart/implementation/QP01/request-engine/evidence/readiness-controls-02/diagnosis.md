The new pre-admission test on312321a9 changed `adapter.methods[1]`, which is
`get_public_key`, not `sign_event`. The actual client correctly admitted the
sign-event request, so the intended `ok == false` assertion failed. The original
raw records show2 actual child settlements: unused-ready child exited1 with no
request; the second child received the public basic request, emitted one actual
611-byte response and exited0. Both were collected. One real native signing
observation occurred; this failed control is not a no-signing PASS, nor an
intentional warmup/preflight or a source for new signature expectations.

The minimal test correction selects the existing method by `id == sign_event`
before changing availability. Original five post-native currentness mutations
remain unchanged: their snapshot-change check does not depend on denying the
selected method. No client, provider, key, expected signature or threshold
changes. This is a new test setup error, not a product defect. Original source,+stdout/stderr and receipt are preserved, including the unexpected execution.
