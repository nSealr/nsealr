# PR45 readiness correction scope review

PASS for pre-code checkpoint aca364addf102abc86b37aac5623f4018255d249 only.
[Structured review](review.json) records exact eight-file delta, six source
bindings, all nine original failed-CI archive members and byte-exact failed-step
raw, plus the genuinely missing readiness-interface RED at61796c7f. Every5c
postimage remains unchanged. Root executed no native/client/test campaign.

The client real100ms deadline remains unchanged. Explicit process/library setup
may move before actual client invocation; no request/native operation may move
there. The dedicated readiness boundary, uninterrupted5000ms child safety and
all owned-child cleanup/actual settlement paths must be implemented and proven.
The unchanged cold path failed; that does not measure its internal timing costs.

Only the two named harness files may change, plus a small source-bound correction
addendum and necessary QP01 checkpoint/artifact references. No client/Bridge/core,
provider, fixture, thresholds, prior negative case, historical report/manifest,
formal task criterion/resource/release or physical guarantee is changed. The
actual correction must still receive stable proof, independent B01 affected
review and root-owned protected PR/actual-main acceptance. This review is not
that future acceptance.
