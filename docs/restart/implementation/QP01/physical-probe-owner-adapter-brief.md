# Python RGB owner adapter: bounded admission proposal

Spec only, 2026-10-24; owner `/root/sdk_dependency_probe`; root admission is
required before code or execution. Base `8f0c4bc54f72ea62e201fdf19be9380f4b20c877`,
tree `6ef6e4fd8ff682b0bca352865ed3ba11cf53b85a`. One proposed module:
`apps/pi/app/nsealr_vault/qr_owner_adapter.py`. Result: a reusable, opt-in Python
consumer of existing O/W, prerequisite to [physical-probe.md](physical-probe.md)
steps 3–5. No complete physical runner or provider selection is admitted here.

## Boundary and API

Reuse unchanged `qr_worker.py` O and `apps/pi/qr-worker` W. Python runtime needs
no Node/TypeScript. The accepted `host-coordinator/first-gate.ts` stays an
independent conformance observer, without refactoring. No default factory,
native C, signer, key/entropy, approval, client route/profile or business-rule
change. All 13 existing worker constraints plus CORE0 remain; AS 268435456,
CPU 1/2s, eligibility 8s from P, cleanup 4s from first O invalidation, chunk 4096,
stdout/stderr 512, JSON704/static947, client100ms and C5000ms are unchanged.

Single-threaded, single-use API, driven by its owning caller:

- `op = RgbOwnerDecode(worker_path, worker_sha256)`: reserve the operation before
  child effects. Trusted caller initializes an absolute regular executable path
  and lowercase64hex actual build SHA **before any frame/request**; no defaults,
  old1a4 fallback, request fields or self-reported identity. Verify hash before
  spawn; O separately verifies it. Interpreter and fixed packaged O source are
  trusted/source-bound, not selectable from frame data. No hostile-host claim.
- `op.open()`: start O; poll for exact readiness before presenting any frame.
- `op.start(rgb: bytes)`: exactly 240×240 packed RGB888, row-major top-to-bottom,
  R/G/B byte order, stride 720, length 172800, no header/padding/JPEG/path.
  Reject wrong type/length before P/W; no crop/resize/colour inference.
- `op.poll(wait_ms)` with integer 0..50: advance nonblocking bounded I/O and
  return pending, owner-ready, verified-worker-ready, settled or quarantined;
  50 bounds selector waiting, not hard scheduling latency. Retain at most one
  immutable frame; no queue/retry.
- `op.acknowledge()`: one G only after verified-worker-ready while locally
  eligible. Withholding G does not stop polling or reset 8s; G is not human consent.
- `op.cancel()` irrevocably invalidates local result eligibility, stops image
  writes, coalesces one X while O is active, and continues draining/collection
  through `poll`. After known settlement, cancellation only discards locally.
  `op.close()` requests Q if unused, otherwise cancellation, and reports settled
  only after actual cleanup; it cannot destroy a live owner.
- `op.take_result()`: once only, after complete valid settlement and a final
  local-cancellation check with no callback/await between check and release.
  Return exact immutable envelope bytes plus the object from existing
  `qr.decode_qr_envelope`; invalid framing is a settled refusal. Bytes and parsed
  data stay private beforehand. Static-envelope framing only, no signing authority.

## Protocol, parser and ownership

Fixed descriptors 0=image,1=result,2=diagnostic,3=control,4=ready,5=status; child FD
mapping must not leak other descriptors. Exact R+EOF precedes P/image. Send P,
write 4096-byte chunks/EOF; validate actual pre-G `worker_ready`, then send G only
while locally eligible. No W before exact ingress/EOF. Bind every record to this
actual O PID/owned pipes; only O owns, signals and collects W. Python collects O
by its actual child handle, never a group/foreign PID or status default.

Use `host-coordinator/control-contract.json` wire-v1 fields, exact order/types and relations,
plus `first-gate.ts:19–112,114–229` observer obligations. There is **no reusable
Python phase/terminal validator**: implement an independent stdlib JSON consumer,
not a TS import or copied worker/signer logic. Translate only wire constants;
docs are not runtime dependencies. Checks must survive `python -O`, not `assert`.
Reject duplicate keys, bool-as-int, floats/nonfinite values,
noncanonical compact ASCII+LF, extra/reordered keys,
records after terminal, missing/extra EOF and all identity/wait/count/hash/IO/time
contradictions. Preserve 512+sentinel output/diagnostic,4096+sentinel cumulative
status and at most 2 records. Reuse public `qr.decode_qr_envelope` directly;
its private request-JSON parser cannot parse O status (negative signal exits have
a different grammar). Pure parser tests are not process evidence.

Success requires decoded terminal, prior verified phase/G, actual W terminal0,
all W IO settled, output count/hash/input hash equality, O0, all channel EOF,
empty O diagnostic and actual O collection. Partial/late/cancelled results are
discarded without rewriting factual O records. A settled refusal retains real
statuses; exit0 alone proves nothing. Unknown/malformed/missing cleanup or
unexpected O exit poisons the operation and caller's admission: retain exact
handles/live O if present, forbid replacement/reuse/result release, report
quarantine. No O watchdog/kill, automatic recovery, destructor/context-manager
cleanup claim, caller exit abandoning live O, or PID rediscovery. The owning
caller must remain alive and preserve this handle pending separately admitted
recovery; no O-death recovery is promised. Neither 4s nor any observation timeout
is a whole-operation cleanup guarantee; poll bounds do not invent startup or
hard-time guarantees.

## First proof and finite acceptance after admission

Freeze minimal adapter source/inputs, then **one real host O/W positive before
completing the implementation**: build only current W from root cwd using
Rust 1.95.0, fresh target/CARGO_HOME, root vendor and
`cargo build --manifest-path apps/pi/qr-worker/Cargo.toml --locked --offline --release --message-format=json`.
Reuse `request-engine/exchange.py:23–55` `build_artifact` with its worker arguments
at 67–73 for source/manifest/compiler-artifact/before-after/ELF/SHA binding;
do not call `provision()`/`ci()` or build/run C/Node. Supply actual path/SHA before
the frame. Retain command/env/source/tool/vendor/input hashes, raw channels,
O/W IDs, phase/policy, real wait/EOF/FD closure and actual result. Frozen oracle:
172800B RGB SHA `64d9be602c821c31c0dfd6e952199a328325acdbf9a7e1b3494921942a11055f`
→259B envelope SHA `88a16190a1b1ed033fc9bebe5452af70e9a9783fd6b92305add2ac7134039ff7`,
paths in `control-contract.json#independent_oracle`. Expected bytes never reach
O/W. This proves O/W host integration only; no native611/signature/client claim.

Then retain the 929 contract's exact applicable negatives, with explicit roles:

- Real O/W: FG0 Q/unused with zero W; FG3 X before P, after real phase with G
  withheld, and late private-result discard; FG6 hex5a, PP, premature G, and
  control EOF pre-G. Require zero caller-released bytes and actual cleanup/status
  or quarantine; late O decoded259 may remain a factual private result.
  Exercise O's actual 8s wall with G withheld separately; never label it the
  FG2 client100ms timeout or change its clock/window.
- FG7 no-W helpers: `ready-extra`, `ready-missing`, `status-missing`,
  `status-truncated`, `status-overflow`(4097), `wrong-owner`, `wrong-worker`,
  `contradictory-IO`, `duplicate-key`, `duplicate-terminal`, `phase-after-terminal`.
  Require intended defect, actual helper completion and no W-success claim.
  Reuse all 9 exact synthetic relation mutations at `first-gate.ts:609–623`,
  including phase-before-P/after-Q, unused/phase/worker and counter/overflow
  contradictions; identify their fabricated PID fields as parser-only.

FG2 client100ms/real110ms guard, FG4 compatibility generation and FG5 C-death
remain in the unchanged TS/C gate; no C exists in this adapter. New Python
negative checks cannot claim those roles or replay the whole 39-case matrix.
Finish with affected Pi checks, normal mandatory full gates and distinct review;
no new dependency, inventory, graph/status/release or budget change.

Capture RGB acquisition and concrete SPI/GPIO binding remain blocked on the
existing kit/image/operator facts. Current 480-JPEG/Pyzbar factory is incompatible
with raw W input; displays require an actual `present_image` provider. Do not
invent either or call a file flow physical. Human rendering/input happens only
in a later admitted consumer after O/W settlement, with explicit diagnostic
bounds; client100ms/C5000ms are not human-review budgets. No ARM/image/optical,
physical consent, production profile, reproducibility or QP01/Q02 closure follows.

Source anchors: current contract SHA
`bf88746e00337186ef22bbfc5d2f5e378aaf4c32e183fa52bafb87c93b9bffef`;
original929 contract SHA
`7359501512aad3473732b7f6cd0d7ca609d4bcc60e5342463ebfbafc15cefd60`
(only initialization/identities/schema/status differ; wire/bounds/cases/oracles
identical). O SHA
`d7a245a9a558cce3ec8271ec42fc49664c094320c6465a537aa3a49c83558d50`;
TS observer SHA `711c7ebebfa4c98ebb9334d7e583c77f58ef58491fb983e2f118f5a44885ab67`.

## Root admission — 24 October 2026

ADMITTED: minimal source freeze and **one real worker-only O/W host positive**
before completing the adapter. Scope and every exclusion above stay exact.
Root independently checked all current contract/O/TS hashes and the actual
172800/259-byte files; the original transport vector has identical envelope bytes
and numeric version2. No worker or signing call produced those expectations.

Preserve existing parent descriptors, including live3/4/5; do not `dup2` into
those descriptors in the parent. Do not require a globally single-threaded Python
process through `preexec_fn`: camera libraries may own threads. Use one trusted
child-only mapping mechanism and prove actual pipe/EOF/descriptor ownership in
the first real positive. No new selectable bootstrap or frame-derived command.

Make the owning runtime/admission object explicit and strongly retain the active
or quarantined operation there; no process-global registry, hidden replacement,
automatic recovery or destructor guarantee. Fresh-operation admission requires
known prior collection. The single-threaded API concerns calls, not a claim that
no other Python/library thread exists. Code remains Linux-host diagnostic only.

Use the real current root-vendor producer and actual default target semantics
(or explicitly demonstrate both relevant default and overridden paths), record
source status before/after and actual artifact identity, and send the minimal
frozen source/command/result tuple to root. Do not start the full negative matrix,
Pi/fullCI or next hardware/capture/display layer until that first result is
reviewed; this is a finite implementation checkpoint, not new parent acceptance.
