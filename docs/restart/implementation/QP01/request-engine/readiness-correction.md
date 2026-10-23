# PR45 harness readiness correction — pre-code checkpoint

PR45 run39976046826/check120490782049 fails on source5c after the whole Pi189
suite passes. The first actual client positive receives `signer_transport_timeout`
at `client-exchange.ts:132`. The [original capture](evidence/pr45-red-01/capture.json)
binds all nine ZIP members; the complete [product-stage raw](evidence/pr45-red-01/complete-product-acceptance.log)
is copied byte-exact. The existing full archive remains at the capture location.
This is a real RED, with no rerun or later campaign PASS inferred.

The inline `cases.limits_manifest` object supplies100ms for every method and
transport. `service.ts` creates a real `setTimeout` around the outstanding
dispatcher even though this fixture's synthetic currentness ticks remain0.
The harness starts its Python child from controlled `present()`: interpreter
startup/imports, request reading, library hash/load/binding and the real native
exchange/child settlement all precede the awaited dispatcher result. The log
does not separate those costs or prove startup alone exceeded the deadline.
The observed correction scope is the harness initialization boundary, not a
demonstrated core/provider/client defect. Previous local host passes remain real
source-bound observations, but did not establish reliability of this cold path.

The [finite proposed contract](readiness-correction.json) permits only the two
existing harness files to change after root scope review. Prepare one fresh
child and initialize its real hash-verified library before calling the actual
client. A dedicated pipe returns exactly `R` then closes, after initialization
and before any stdin request read or native request/callback. The parent sends
no frame until the unchanged dispatcher calls `present()` and its currentness
check passes. No signing preflight, warmup request or replay response is allowed.

The actual100ms timer and all thresholds/cases stay unchanged. Readiness setup
is explicitly outside that timer. Existing synchronous client preparation and
the initial dispatcher prefix occur before timer creation; final synchronous
response verification follows its clearing. Neither is newly moved or claimed
to be covered by that timer. The asynchronous manual-port exchange, actual Rust
review/signing, streams, child close and dispatcher settlement remain in its
existing wait. This is not a real-time or target latency guarantee. The existing
5000ms child safety timer must still run from spawn through close without reset.

Retain all negative cases and the actual held-child100ms timeout, reservation,
separate-context refusal, explicit release, close/pending settlement and fresh
child recovery. A complete campaign still requires14 children collected. Any
ready-but-unused child must also be collected if pre-presentation admission or
an assertion fails; preparation must not create queued requests or early reuse.

The [executable regression](readiness-regression.py) sends **zero request bytes**.
Its initial RED on unchanged5c is the missing readiness interface, not a
synthetic reproduction or attribution of the hosted timing failure. After an
approved correction it checks real library readiness with no response, idle EOF
refusal/collection, and separately the real wrong-library-hash refusal before
readiness. No signature is computed by this control. The full actual client
campaign is still required before any correction PASS.

Original e44/5c manifests and reports keep their source identities. The current
plan has no direct artifact rows for these two harness paths; root withdrew an
initial contrary assumption. Any necessary QP01 checkpoint/artifact references
for the small correction addendum require explicit scope approval. No formal
task, criterion, resource, release, core/provider, actual client/Bridge, fixture
or limit manifest changes are proposed. B01 remains the distinct affected
reviewer and root owns hosted CI. No hardware, physical consent or release
qualification follows.
