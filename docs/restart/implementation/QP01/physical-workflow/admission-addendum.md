# R1/R2: synthetic local-UI experiment, before implementation

2026-10-25; documentary addendum to immutable `a8367340`/`brief.md` and its
28-source proof. Responds only to distinct admission `c1ffff4a0d79af98fc7b9ba0159d04725a666591`
([report](../../reviews/QP01-physical-workflow-admission/report.md), originally on
its review branch). Neither finding is relabelled as resolved by execution.
No application import, code, build, test, actor, kit action or CI observation now.
The following is a **proposed future code/experiment boundary**, pending admission.

## R1 — One fixed entrypoint and the existing sole C owner

Use the existing top Python `run-composition.py`, adding only a trusted optional
`--synthetic-inspection <enum>` for `--case fixture_request_engine`. Absence keeps
every existing case unchanged; combining it with `--engine-refusal` is invalid.
The single positive invocation shape is:

```sh
"$PYTHON" -B "$ROOT/docs/restart/implementation/QH01/manual-port/python-rgb-composition/run-composition.py" \
  --case fixture_request_engine --synthetic-inspection basic-fresh \
  --output "$OUT" --worker "$W" --sha256 "$W_SHA" --node "$NODE" \
  --bridge "$ROOT/apps/bridge/service/dist" --reuse "$ROOT" \
  --engine-library "$LIB" --engine-sha256 "$LIB_SHA" \
  --engine-module "$PREP/native-leaf.js" --engine-module-sha256 "$LEAF_SHA" \
  --engine-preparation "$PREP/receipt.json"
```

These are required trusted **operator/fixture inputs**, never request fields.
Before any RGB/O/Node/C, freeze their actual absolute paths/argv, current Git
commit/tree, Python/Node identities, source snapshots, W/library actual hashes,
compiler/source/options/output/context receipt and generated Bridge/package
hashes using the existing producer/preparation recipe. No historical runtime
directory or stale binary fallback; source-matched artifacts may be reused only
with those exact bindings. No new Rust, crypto, dependency or helper compiler recipe.
Bind before/after the literal new `synthetic_inspection.py`, `engine_adapter.py`,
`request-engine/exchange.py`, `native-leaf.ts`, `run-composition.py` and
`bridge-child.mjs`, plus the unchanged producer's Rust/lock/vendor inputs and
original request/oracle. The future source freeze must supply actual new hashes;
this documentary checkpoint does not invent a hash for code not written yet.

Writable scope is only a newly absent `$OUT` (0700) and existing explicitly bound
temporary preparation outputs. Root/library/module/source/fixtures are read-only
inputs. Parent creates `$OUT/synthetic-inspection-config.json` before actors;
child writes only `$OUT/inspection-trace.json` within the existing output owner.
Preserve all existing result/raw/settlement files. Do not delete failure output
or unknown-owner evidence, even when a diagnostic write fails. No device paths.

New config is strict JSON<=4096B, exact keys/types, duplicate keys refused:
`{v:1,scope:"QP01_SYNTHETIC_INSPECTION_V1",scenario:<enum>,callback_source_sha256:<lower64hex>,trace_path:<absolute>}`.
`trace_path` must be exactly the non-symlink output sibling above. The source path
is a literal `apps/pi/app/nsealr_vault/synthetic_inspection.py`, **not a config
field**. Parent/Node/C bind config bytes/SHA; Node passes only the two fixed env
names `NSEALR_QP01_SYNTHETIC_INSPECTION_CONFIG` and
`NSEALR_QP01_SYNTHETIC_INSPECTION_CONFIG_SHA256` in its already fixed C environment.
No callable/module name, code, event list, key, clock value, path from QR or
arbitrary import is allowed. The finite selector set is exactly the C scenarios
listed in the R2 table below; pure layout/event controls have no C selector.

The minimum future delta is one static synthetic adapter module plus narrowly
scoped selection/records in `run-composition.py`, `bridge-child.mjs` and C-entry
`request-engine/exchange.py`; source/hash/strict config validation precedes R+EOF
and stdin read. C statically imports the literal adapter only for this selector;
default `present` remains byte-identical. Replace that invocation's local-IO
closure, **not** `EngineAdapter`, Rust, signer, library owner or default provider.
The callback is demonstrably synthetic draw/input, never physical GPIO/Pillow.

Node still calls reviewed `createPrepareNative` once, only after actual B3
settlement/raw `take_result`. Child argv remains exactly
`[python,"-B",ROOT+"/docs/restart/implementation/QP01/request-engine/exchange.py","--ready-fd","4"]`;
no `syntheticArgv` override, second owner, callback thread or direct-CDLL shortcut.
Retain its captured **pre-mock real** timers: literal5000 from spawn through
actual C `close`, C-only safety kill attempt, send once after exact R+EOF, same
947 stdout/262144 diagnostic caps. No claim of hard collection by5s or Node rawwait.
Python retains runtime/op/O/Node; Node retains exact C/helper handle. Unknown
collection enters the same reporting-safe hold, no retry/replacement/Python/O kill.

Trace<=131072B, append with cap-before-retain, then bounded final write **before
stdout release**. It records actual callback entries and exact page bytes,
draw/commit/input ordering, real-clock samples, chosen action, actual native
return/status and output length/hash. Add an auxiliary-entry event only at the
actual zeroaux closure invocation; this counts that callback, not Rust backend
or physical entropy calls. Failure to collect/write valid evidence yields no
usable fixture success. No constructed PASS/status counters replace observations.
Success retains the usual C trace fields for `prepareNative.send` plus config/
adapter/trace hashes; expected native `EngineError` writes its actual status and
empty output, exits C1 without stdout. Node's existing typed failed-transport
path disposes/awaits C; parent reads the bounded trace only after actual known
C/Node/O settlement. Use a distinct `qp01_synthetic_inspection_result` namespace,
not legacy14 `native_observation` or global `case`. Existing modes stay unchanged.
Capture native status separately from actual C code/signal/stdio-close, Node raw
wait/EOF/FDs and O/W waits/EOF. No later or partial output becomes a client frame.

## R2 — Observable full draw and one fresh action

This first fixture uses a **synthetic cell draw sink**, not Pillow's clipping
implementation and not a font-readability claim. Trusted metrics:
viewport240×240; printable ASCII0x20..0x7e; glyph ink/advance6×8px; content
32columns×8rows; x24,y48,line advance16. Header at(24,16) prints exact `kind`,
zero-based `index` and `total`; footer at(24,208) distinguishes data/decision.
Content is `label` lines, then `body` lines, then `position` lines, preserving
every ASCII byte and LF/blank line, without trim/reflow/JSON unescaping/ellipsis.
Preflight all field types, bounds, lines, unsupported bytes and every ink box
before drawing. Exactly32 cells/eight lines fit;33 cells/nine lines refuse.
No acknowledgement after failed fit, partial draw, presenter exception or fake
commit. Store original byte spans and ordered draw calls; geometry evidence
does not establish visible glyphs, panel behavior or physical consent.

Each native invocation creates a fresh **process-local fixture state** capturing
the immutable raw-input hash. Each callback entry creates a new local presentation
epoch and copies its exact `(kind,index,total,label,body,position)`. These are
adapter bookkeeping, not FFI owner/approval handles, context setters or a new
public token. Synthetic input steps are fixed by enum/source, never QR data.
The observable order is:

1. Enter epoch; sample all actions released and queue empty. Preheld/queued input
   refuses immediately. Preflight, draw every field in order, then presenter
   completes and records one `commit` for this exact epoch/tuple.
2. Arm input only after commit. Fixture produces one neutral→single-press→release
   cycle after that point. Record acquisition order and its local epoch. No
   event sourced before commit, wrong epoch/invocation, already consumed or with
   >1 simultaneously pressed action is accepted; refuse rather than prioritise.
3. Consume that cycle once before returning action0Next/1Approve/2Reject. Rust,
   not this fixture, rejects early Approve/Next-at-decision with -9. Back, None,
   scroll, bool and unknown values are explicitly refused by this first adapter
   (-6 through FFI); no Back/None loops or silent scroll mapping.
4. On return/error discard all queued state. Redisplay of the same tuple creates
   another epoch and requires another commit/fresh cycle. A later request creates
   another local state, even for identical request_id/raw bytes; no old events
   or detached consent carry over. No re-entry while the synchronous call is active.

The synthetic sink may inject a step only after the adapter actually requests
it; expected ordering is checked independently, not fabricated as a transcript.
Exception/BaseException from draw/input crosses `EngineAdapter` as invalid display
action (-6). Cancellation is sampled by the actual native cancelled callback,
not equated with an event label. Before-consent failures have no actual auxiliary
entry; after-consent failures may have consumed authority and still release zero.

## Finite future oracle, not executed here

Native statuses below are actual `EngineError.status`, not shell exits. Known
C refusal is code1/signalnull/stdout0; successful C is code0/signalnull/611bytes.
Both require actual stdio-close, Node/O/W settlement/EOF/FD restoration. Unexpected
status, missing trace, late bytes or unknown cleanup is a failed/held experiment.

| Selector or pure control | Frozen expectation |
| --- | --- |
| `basic-fresh` | Original raw259/SHA88a161…; actual real `MonotonicSeconds` samples, zeroaux;31 ordered pages0..30, total31, kinds30data+decision. Commit precedes each distinct fresh action; one actual auxiliary callback entry; exact611/SHA250167… and independent complete event/key4f35/client verification. |
| `reject-data`, `reject-decision` | Fresh Reject at page0 or30; native-5, no auxiliary entry, no response. |
| `approve-data`, `next-decision` | Fresh but wrong-phase action at page0 or30; native-9, no auxiliary entry/response; no skip or detached approval. |
| `draw-before`, `draw-partial`, `draw-decision`, `presenter-error` | Failure before first draw, after first field of page0, at decision, or from presenter. No successful commit/action for affected epoch; native-6, no auxiliary entry/response. |
| `input-error`, `input-baseexception` | Exception or explicit KeyboardInterrupt after successful draw; native-6, no action/auxiliary entry/response. |
| `preheld`, `queued`, `stale-page`, `duplicate-event`, `simultaneous` | Inject respectively at page0,0,1,1,30. Refuse-6; no affected acknowledgement/auxiliary entry/response. Duplicate is the previously consumed cycle; simultaneous includes Approve+Reject and has no priority rule. |
| `back-refused`, `none-refused`, `bool-refused`, `unknown-refused` | After page0 commit inject Back, None, True or99; adapter refuses-6, no auxiliary entry/response. |
| `cancel-after-commit` | Set actual local cancellation flag at page0 commit, finish the callback without blocking; native sample after callback returns-11, no auxiliary entry/response. No new clientAbort API. |
| `clock-unavailable` | Explicit **fault injection**, clock raises on the sample after page0 callback: native-7, no auxiliary entry/response. Actual C5000 remains real; this is not real-time expiry. |
| Pure fit controls, zero child |32-cell/eight-line complete frame→one commit, exact bytes/order;33-cell/nine-line/non-ASCII/invalid geometry→local display refusal before any draw/commit/event. Do not label these native execution/status evidence. |
| Pure stale-request/redisplay controls, zero child | Reuse old local event across two fixture states or callback epochs→refusal with no action. New neutral cycle after a new complete commit→usable0/1/2 as appropriate; identical raw/correlation never exempts fresh review. No FFI one-use handle is claimed. |

Keep the exact full hashes/oracles in the original proof/expectations; actual
response SHA is `250167d1137f6da25676b00b62913a3d8f29391a1ff5331d64f7079d953f5ded`.
No new golden/identity; W512/JSON704/static947, parent512, Node2048/4096/4096/max5,
O8/shared4, client100synthetic and C5000 unchanged. Positive is actual real-clock
execution, not constant0 or simulated expiry. Do **not** wait100 real seconds
inside C5 or claim such expiry; reuse old core currentness/consume-first tests
(`authorization/tests.rs:591,667,756,846,1038`) and existing ABI callback tests
only for their original scope. No source setter or renderer coverage is inferred.
If real C5000 expires, retain actual code/signal/close; no native -7/returned
status is invented and no output is released. Missing close retains exact handles.

This closes only the missing documentary choices for affected review. Full human
time-domain separation/request/catalog/identity/currentness/one-use binding remains
**OPEN**; this synthetic callback experiment cannot qualify it. No physical callback,
full runner/default provider, source implementation or execution is authorized here.
Original brief/source proof/reviewer report and all47/physical gates stay unchanged.
