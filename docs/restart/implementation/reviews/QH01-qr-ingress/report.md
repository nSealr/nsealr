# QH01 QR ingress component review

**PASS_QR_ingress_component_only; no findings.** Exact candidate
`557fe9758154e622a41dabbda5c3ceca3871e43d`, tree
`471f9c951f8fc68557d06f6638d5788167aa1308`; author
`/root/b01_final_review`, reviewer `/root`, Sol6.1 xhigh. This accepts the
bounded correction to existing experimental codecs, not completion of QH01.

The static whole-envelope length guard precedes `.slice`, lexical work and
base64 conversion. The animated path retains the existing early 64-frame count
guard, then inspects every frame's length and the cumulative raw length before
any `.map`, split or checksum. Its private parser has one caller, after this
preflight. Accumulated chunk length is checked before joining, decoding or
canonical re-encoding, and the single joined string is reused. The unchanged
704/4096-byte, 64-frame and 256-character ceilings yield 939/5462 payload
characters, 97 maximum header characters and 353 whole-frame characters. The
conservative raw budget is finite; the later exact chunk budget handles shorter
headers. Original checksum, digest, canonical trailing bits, strict UTF-8/JSON
and frame-set/index checks remain in place. No framing or capacity is newly
qualified.

The unchanged test definitions were fixed at
`4e2a732b81b3e44c30645f9d1f14768e386af24e` before runtime changes. Original
`988ff6367a82a3200d8a2131579066e88daddf9c` retains byte-exact old runtime and
actual 5-failure/22-pass output. Node Buffer/crypto construct independent valid
inputs, digests and checksums. Max-minus-one/max/max-plus-one and under-limit
malformed cases separate the intended rejection layers. Spies show the
expensive operations occurred before the old refusal and are absent at the new
early guards; this is stronger than only checking an error message. The new
runtime/test source `447dd235aab5483e88094eca881457e9c3709d8c` is unchanged in
the candidate. Root verified all 32 manifest members, seven original source
bindings, two runtime postimages and ten original command/raw-log pairs. Only
two existing QR source/test paths and 33 scoped proof files differ from input5d.

One distinct run of the existing focused test file from this isolated review
checkout passed all 27 tests, exit0, in a 0.557-second command. The existing
pinned offline install and workspace build were prerequisites, both exit0;
tracked sources and locks stayed clean. See [checks/commands.json](checks/commands.json)
and [validation.json](validation.json). No whole test suite, crypto corpus or
hosted CI was rerun. Author typecheck/build/metadata proof is reused within its
unchanged source scope. The author's final-print packaging error is preserved.
Reviewer launch and ANSI-summary reader assumptions were also corrected and
recorded under `checks/`; neither was a product/test failure, and neither changed
test expectations, source, thresholds or raw evidence.

Caller-owned strings and arrays already exist before this API. The checks bound
subsequent codec work/allocation, not caller allocation, arbitrary hostile JS
accessors, native camera/decoder resources, elapsed time or encoder-side input
construction. Session/identity/request correlation, replay/cancel/client
deadlines, seed-channel separation and the full scanner/UI workflow remain
separate implementation requirements. Actual screen/camera comparison against
maintained multipart UR is still required before framing freeze. All five QH01
criteria remain incomplete; no signing/provider/key/custody/device or physical
release is admitted. Normal protected integration and actual-main gates remain.
