# Future build and proof recipe

**Not executed or authorized by this file.** First obtain distinct exact-source
admission for this frozen candidate, then a concrete build/runtime assignment.
Do not run cargo/check/test, a canary case, or the oracle just to review this source.
No automatic batch, default CI registration, threshold adjustment or production
route is included. The first proposed tranche is the15 IDs in cases.json.

## Before any command

Use Linux/Tux and the existing pinned R00 environment. Record the actual clean Git
commit/tree, source-freeze.json SHA256, tool hashes/versions, exact argv/environment,
fresh output paths and case inputs in a private pre-launch receipt. Verify all
source-freeze members, unchanged legacy paths and task graph before launch.
The freeze is bound by its containing Git commit; it has no invented self-hash.
Confirm Linux x86_64/glibc, one-thread/no-descendant topology, pidfd/wait4/proc
availability, SC_CLK_TCK=100 and monotonic clock. Missing support stops; no fallback
provider or relaxed cap qualifies the experiment.

The existing baseline tool root is
`/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools`.
Its environment/provenance is historical; inspect and freeze actual tools rather
than claiming a fresh execution from that receipt. Use an independently reviewed
new worktree/output root if the later runtime owner differs from this author.
Never run the old C01 example or import its source into normal targets.

## One build after source admission

The following is a literal proposed command, not a completed build. Set HRT_WORK
to the exact reviewed checkout, HRT_PROOF to a new private absolute directory and
HRT_TOOLS to the existing tool root above. Do not overwrite any existing evidence.

```sh
cd "$HRT_WORK"
env CARGO_HOME="$HRT_TOOLS/cargo" RUSTUP_HOME="$HRT_TOOLS/rustup" \
  RUSTC="$HRT_TOOLS/rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin/rustc" \
  "$HRT_TOOLS/rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin/cargo" \
  build --locked --offline -p nsealr-pi-engine-fixture \
  --example qp01_human_wait_canary --target-dir "$HRT_PROOF/target"
```

Preserve compiler RED and stop before correction/retry. A compiler pass establishes
no actor/timing/OS/ABI/gesture/signature behavior. Record the actual example ELF,
its SHA256, loaded libraries and build inputs separately. Existing reproducibility
proof does not cover this new executable. A new source candidate invalidates its
affected admission; no core/dependency/lock/vendor/default-gate edit is implied.

## One first positive after separate runtime assignment

Set HRT_PY to the pinned verified Linux Python3.12, HRT_SUP to this supervisor's
absolute path, HRT_BINARY to the built regular ELF and HRT_BINARY_SHA256 to its
recorded digest. HRT_PROOF/positive must be absent. This trusted launcher captures
the common origin before exec of S in the same PID; no third live actor is created.
The main supervisor then hashes all frozen files, charges startup and spawns R once.

```sh
"$HRT_PY" -B -c 'import os,sys,time; os.execv(sys.executable, [sys.executable,"-B",*sys.argv[1:],"--origin-ns",str(time.monotonic_ns())])' \
  "$HRT_SUP" run --binary "$HRT_BINARY" --binary-sha256 "$HRT_BINARY_SHA256" \
  --case positive --output "$HRT_PROOF/positive"
```

The first positive must show actual5500ms passive elapsed time, one immutable owner/
raw/catalog/context, zero recorded driver sign-entry/aux events during WAIT,
authoritative ACK/resume ordering, real CPU samples and the unchanged5000ms ledger,
one API entry/aux callback, known raw wait and IO closure, and only a private result.
Lost/incomplete records cannot prove zero entries. Different failure or unknown
ownership remains RED/inconclusive; preserve it and stop. The source intentionally
refuses a monitoring gap over50ms, startup beyond the fixed catalog's tick0, a
CPU/poll cap failure or an expired caller; do not normalize those into a pass.

## Independent oracle after known settlement

This is a separate later invocation, with no R actor alive. It imports only the
existing hash-pinned S03 oracle/reference. It verifies complete expected event,
correlation, identity, canonical ID, signature and original zero-aux expectations.
It cannot recover eligibility, assert backend counters or qualify live publication.

```sh
"$HRT_PY" -B "$HRT_SUP" verify --artifact "$HRT_PROOF/positive"
```

Post-core oracle negatives are separate explicit invocations using `--mutation`
with key/template/signature/id/request-id/trailing. They mutate only the retained
response in memory. They do not inject a Rust backend fault or prove a backend
attempt count; source-identical K01 private test evidence retains its original role.

## Assigned negative tranche

Only after the first result and the actual runtime assignment select each named
case from the15-case first tranche, one fresh output directory per case, using the
same literal launcher and frozen binary. No command loops over all cases. Preserve
exact order and raw s-to-r.bin/r-to-s.bin/stderr.bin, result.json, OS CPU/identity/
ledger trace and real wait/exit facts. Expected-class matching requires the exact
failure and scoped counts implemented by expected_case; any other failure is RED.
A signal request, child label, terminal or EOF is not full settlement.

The false-wait-cpu/guard-before-resume pair separates independently observed CPU
work from the source-level dispatch guard. resume-before-arm must send no gesture.
partial-draw must create no WAIT exemption. caller-100ms must expire on real time.
child-stop must record actual T/t and known subsequent collection; supervisor-gap
is a real75ms sleep/checkpoint gap, explicitly not an OS SIGSTOP experiment.
truncated-result and post-core-cancel must retain no eligible candidate. No backend
hook is added for wrong-correlation/aux-short/policy-change public-API controls.

If cleanup exceeds its shared4s boundary, the same S remains quarantined with
original handles; the caller must retain that ownership and record it. Do not
kill the last owner, replace the actor, retry, reload or label a report timeout
as collection. Unknown status is not an available reservation. Any additional
fault selector, verifier actor, decoder integration or live-publication path needs
its own explicit scope/source/runtime admission; the current source does not
qualify them or change any of the47 task/release criteria.
