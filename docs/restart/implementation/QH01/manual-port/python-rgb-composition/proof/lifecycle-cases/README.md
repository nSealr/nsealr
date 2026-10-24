# Three lifecycle fixtures and default regression

**PASS_SCOPED_THREE_LIFECYCLE_FIXTURES_AND_NORMAL_REGRESSION; review pending.**
Isolated implementation fromf8. Spec precedes code. Three early commands ran on
frozenf4d4d8c5, then one normal make pi-ci on30222891 with identical runtime code.

| Trusted CLI fixture | Actual service result | Actual O/W | Port/timer |
| --- | --- | --- | --- |
| scan_null_after_settlement | signer_transport_failed | O0/W0 | scan1/close1;100clear1/fire0 |
| scan_pending_timeout_after_settlement | signer_transport_timeout | O0/W0 already settled | close0 at timeout; late611 then close1;100clear1/fire1 |
| fixture_cancel_B3_verified_preG | signer_transport_failed | O2/raw512; W-9/raw9, collectorO | PX/G0/Wimage0/API0; scan0/close1;100clear1/fire0 |

Each expected error response was asserted before the diagnostic exited0. Actual
Node/O/W waits, EOF and caller FD restoration were recorded; no owned case
process remains live or quarantined. W71/raw18176 was also source-admitted before
execution; it was not the newly observed outcome. Before the28-byte cancelled
reply, take_result and early reservation refused, O/W were collected and B3 was
explicitly closed. Node used the existing typed SignerTransportError. This is
fixture port cancellation, not an invented public client-abort API.

Timeout observes scan entry after B3 settlement, actual timeout/abort with close0
and an unsettled underlying dispatcher, and one blocked same-context attempt
returning runtime_unavailable without another port/timer. Only then does the
fixture resolve611 and await actual underlying settlement/close1. The terminal
timeout response cannot change. Pre-conversion refusal is source/unchanged-unit
evidence; this compiled fixture has no new decoder-call counter. Already
completed B3 work is not cancelled or recalled in either scan case.

Client time is synthetic0/99/100 with actual timer argument100. O8s/shared4s remain
real; C5000 and13+CORE0 are unchanged. IPC remains ASCII canonical JSON/LF,
2048B/record,4096B stdout/4096B stderr,512B reply and at most5records. Observed
counts were4/5/3, stdout934/1508/923B, stderr0. Trusted CLI enums select test
behavior; frames select no programs, paths or keys. Default positive argv/result
schema remains the regression, with no separate legacy implementation.

Early runs reused W313835a1… and10Bridge/52package dist files explicitly bound to
the old read-only worktree. Seven package trees, Bridge sources, six actual W
build-input bindings and pinned tools equaled this base. Eight unchanged source
and five fixture hashes from5138 were checked. No early Rust/C build or install
was needed; inputs.json records provenance, not a runtime fallback.

The normal regression used THIS checkout's builder/packages/provisioner. Initial
node_modules, Pi.venv and default root/QR targets were absent. Necessary setup
used the unchanged lock offline/frozen with existing baseline store/wheels;
Node24.22.0/Python3.12.15/TS6.0.3/Rust1.95 stayed pinned, with no Cargo target
override. One make pi-ci passed0/45.239295614s with source clean. Pi211, all70owner
records/files,39original final cases, five producer and six pure controls remain.
Its one default positive used current-checkout W95f541ec…, Node/O/W0 and original
259/259/611 with clear1/fire0. No manual positive was added. Different ELFs carry
no worker reproducibility claim.

Coverage is explicit: the three negatives are dedicated commands, NOT newly wired
into normal CI. Normal CI checks the default positive, six pure controls and old
211/70/39. Builder, provisioner, checker, product client/manual/B3/O/W, locks and
graph were not edited. source-correspondence.json binds six unchanged Python
methods including attention/hold/cleanup, production postimages, positive keys
and the normal record's60source hashes to Git30222891.

early.tar.gz retains52original files plus manifest; normal.tar.gz retains81plus
manifest, including the original494891-byte merged normal log and70same-run owner
files. Both archives were read back. Normal raw log SHA256 is
aa21e0725c9656ce0375a18627a08c22d7decf7dbe575de029e97baff445382d.
All three case commands and the normal gate passed first invocation. Root's
separate consumer proof is not copied or executed here.

Unknown-cleanup guards are unchanged, not newly proven as actual quarantine or
recovery. No external/UI/client-abort trigger, camera/display/optics, ARM/Pi,
production provider, new key/signature, framing freeze, task/release closure or
physical claim follows. No full make-ci or hosted CI ran. **STOP distinct review.**
