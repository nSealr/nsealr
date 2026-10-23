# QP01 reviewed host engineering components

QP01 remains **planned**, with all three acceptance criteria incomplete. All
five QH01 and six Q02 criteria also remain incomplete. The recorded kit inventory
is a resource lead; targeted Pi identification remains pending and no physical
availability or qualification follows.

The [request-aware public-fixture engine delivery](request-engine/delivery/README.md)
adds author `e44f957b` and its distinct [implementation/runtime review](../reviews/QP01-request-engine/report.md)
and [provenance review](../reviews/QP01-request-engine-provenance/report.md), based on
accepted main `14d5e370`. Original request bytes enter the real Rust owner,
complete review and consuming authorization; the resulting v2 response reaches
the unchanged actual client verifier. Author and reviewer each ran the full host
Pi suite (189 tests) and two real client round trips with the already-public
fixture identity. Their builds, negative cases and settlement evidence retain
separate source/run identities; this metadata assembly runs no product tests.
Python/native callbacks remain trusted and presentation is synthetic. No default
route, real keys, camera/display/buttons, ARM/Pi/P4, entropy, custody, physical
consent or release is qualified. JSON704/static-frame947 and image-worker512
remain separate limits. The new cdylib has build/SHA evidence, not a
reproducibility result. Final delivery review and protected integration remain
root-owned future gates.

The earlier preparation below is historical source and host-boundary evidence,
accepted through PR41; its original reports and pending fields are unchanged.

The [source brief](brief.md), [source evidence](evidence.json) and
[minimal physical procedure](physical-probe.md) are exact historical copies from
`3330972dd7cc4f36be2622cdafdcfbe8c81adec4`, on its original b159 input. They
separate useful Python camera/decoder/display/GPIO interfaces from the absent
modern camera factory, real presenter, hardware-wired app, Pi image and shared
engine ABI. The [distinct review](../reviews/QP01-source-preparation/report.md)
at `b0cbd1f69caeb7f26a97c61bb657f9adc501e97d` is
`PASS_source_preparation_only`. Old K01-pending statements retain their original
date/source role and are not live instructions.

The [boundary decision](engine-boundary/decision.md), [ABI limits](engine-boundary/abi.md)
and [actual host trace](engine-boundary/checks/host-01/result.json) are exact copies
from `b45812362e2f8340572aaaffd0384a9662fc6fb2`, on actual5d. One fixed-public-key
host canary exchanges all33 actual Rust review frames with Python callbacks,
then signs and independently verifies one344-byte event. Local rejection,
premature approval, display failure, nested Busy and fresh-call recovery retain
their actual source/run identities. No new run is claimed by copying them.

The [code component review](../reviews/QP01-engine-boundary-code/report.md) at
`cabe9f785957e44d124fc1250505fe0842955312` is `PASS_canary_component_only`.
The [source/decision review](../reviews/QP01-engine-boundary-source/report.md) at
`44ee60f3383ae101c5c8e38708ffd71787e01ccf` is
`PASS_source_and_decision_preparation_only`. Neither approves a persistent
import/session/user-key API or physical display/input/entropy. Python and native
adapters remain trusted; the actual library is x86_64/glibc, not an ARM image.

The engine dependency is now [accepted K01 main5d](../reviews/K01-current-delivery/adoption/actual-main-acceptance.json),
tree87a54f18, following protected PR40/full PR and actual-main CI. Original source1aa,
runtimebf51, test-only4bab and their distinct review roles are unchanged. K01
acceptance does not qualify target providers, real keys, transport or a device.

The separate [QH01 ingress component](../QH01/qr-ingress/brief.md) at557fe975 changes
only two QR source/test files: static encoded-length refusal and animated
whole-frame/raw-collection/exact-chunk guards run before the affected conversion
or retained work. Existing provisional limits and framing remain unchanged.
The [distinct review](../reviews/QH01-qr-ingress/report.md) at
`dd7c4685e6da219707b8d567d0d16149be96a304` is
`PASS_QR_ingress_component_only`, separate from the QP01 preparation verdicts.
All five QH01 criteria remain incomplete. No complete client/optical session,
camera/native decoder or screen comparison is qualified.

[Combined preparation proof](delivery/result.json), [exact copy inventory](delivery/copy-inventory.json)
and [scope](delivery/source-scope.json) bind that historical proposal to the actual
accepted5d base. Every original mode/blob/byte and paired relative name is kept.
The copied source packets and reports are immutable; only this entry, current
shared navigation, the exact admitted QR source/test postimages and current graph
fields describe the new delivery. Original194615 remains the immutable standalone
QP01 metadata checkpoint; its old checks are not relabelled as combined-source checks.
That preparation was [accepted on actual main d41](../reviews/QP01-current-delivery/adoption/actual-main-acceptance.json)
after protected PR41 and full PR/resulting-main CI. This acceptance does not
replace the new request-engine delivery gates.
