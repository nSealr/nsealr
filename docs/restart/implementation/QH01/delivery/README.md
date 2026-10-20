# Manual QR component delivery

This proposal copies B01's exact [manual-port component](../manual-port/handoff.md)
`2b08278adf0047c5e7a230d50590deccfe933511` onto accepted main
`d41a37e25cd0a86d3a47294f8d0ba24913128a21`. The new service-only
`createManualQrRouteDispatcher` accepts an explicitly injected trusted port and
uses the existing client lifecycle and experimental static codec. Only two new
TypeScript files and two existing workspace dependency/link files change outside
proof/navigation/graph metadata. No default route or readiness is enabled.

The existing client retains request/key/template/ID/signature validation,
currentness, deadlines and pending ownership. The factory reserves the injected
port before external callbacks through actual operation settlement; failed open
or cleanup quarantines that owner. The port must enforce native caps, call
currentness immediately at any delayed presentation, and report successful close
only after real quiescence. Host cancellation is not physical recall or consent.

Original author tests/proof and failures are exact copies, not new execution:
58 final manual cases,80 existing cases across six files and typecheck pass on
the declared source. The initial missing-module RED executed zero behavior
cases; the later actual two-openers-versus-one reentry failure is separate and
preserved. The [distinct root review](../../reviews/QH01-manual-port/report.md)
at`bfc6b29a6ad12424df3236a6b225f55e355e4cff` is
`PASS_manual_QR_service_component_only`, with one independent existing58-case
run. Its limited component scope is separate from whole-task acceptance.

The [prior foundation adoption](../../reviews/QP01-current-delivery/adoption/actual-main-acceptance.json)
passed protected PR41/full PR and actual-main CI on exactd41. Its original
historical proposal/pending reports are unchanged. The root descriptive
`test_file` path correction from60b to3e3 changes no actual trace or test result.
This new manual component still needs exact final metadata review, protected
delivery and resulting-main gates.

All five QH01, three QP01 and six Q02 criteria remain incomplete; QH01 and QP01
stay planned with null task reviewer/verdict. Public/synthetic fixtures do not
qualify physical scan/display/input, native buffers, real-client timing,
framing/UR, keys/custody/providers or any Pi/P4 release. No kit facts or physical
admission are inferred. The existing kit/operator follow-up remains pending.

[Result](result.json), [copy inventory](copy-inventory.json) and
[scope](source-scope.json) separate current delivery facts from immutable source
reports. Only root owns final metadata review and protected integration.
