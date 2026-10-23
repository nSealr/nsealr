# Request-engine readiness correction — author result

The [static result and source correspondence](readiness-result.json) bind this
correction to executed source `b75db930d89a7dfbd9c28036c3d345c81aecd1ac`.
The [pre-code contract](readiness-correction.md) and its distinct root review
remain unchanged. B01 affected implementation review and root final delivery /
protected integration are still required.

Only the two existing harness files change. A fresh child loads and verifies
its actual library, emits exactly R+EOF on a separate pipe and waits without
reading a request. The unchanged actual client begins afterward; only controlled
presentation sends the original frame. The real100ms deadline and absolute5000ms
child safety remain unchanged. Initialization is outside the operation timer;
its unchanged synchronous client preparation/final verifier placement is
explicit in the contract. This is a host engineering boundary, not a target
latency or physical optical guarantee.

Two direct Python no-request controls pass. Five separate Node readiness controls
pass with5 children collected,0 requests and0 native reports: ready-unused,
pre-admission refusal, assertion cleanup, wrong hash and a clearly synthetic
malformed handshake. The focused flag runs only those five; the single default Node invocation now
runs them automatically before the original campaign, in separate lexical
scopes with independent counters and explicit5/5 plus14/14 reports. `make -o bridge-ci pi-ci` then passes the entire189-test
Pi CI, automatic five readiness controls and original actual client2 positives/5 verifier negatives/5 currentness
negatives/held timeout-retention-release-fresh-reuse campaign,14children collected.
The -o explicitly reuses source-identical Bridge evidence; it is not a new whole
Bridge/default CI run. The hosted final gate must run all prerequisites normally.

The original hosted timeout and all focused failures remain. In particular, an
incorrect new pre-admission selector initially denied get_public_key instead of
sign_event and caused one real public-fixture signing before its assertion RED;
that run collected both children. It is neither a no-signing PASS nor an intended
warmup, and its output supplied no expectation. A syntax error ran no child; an
extra driver call failed the original provisioning test and was removed without
changing that test. A cache-copy tooling error is separately documented.

Original author/delivery manifests retain their original source IDs and bytes.
The correction addendum and current QP01 metadata describe the new source; all
formal task/resource/release data stay unchanged. Rust/core/provider/fixtures,
actual client/Bridge, limit manifests, locks, coverage floors and prior canary
remain exact. Existing source-identical proof is reused explicitly. No production
keys, camera/physical consent, ARM/Pi/P4/no_std, entropy/custody, secret isolation,
cdylib reproducibility, task completion or physical release follows.
