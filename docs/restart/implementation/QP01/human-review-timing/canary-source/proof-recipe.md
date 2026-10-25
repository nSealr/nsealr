# Future build and proof recipe

**Not executed or authorized by this file.** Distinct affected-source admission
precedes any compiler/build/runtime assignment. This correction preserves197df6f
and resolves its three source findings; it supplies no compiler or actor PASS.
The driver is now `driver.rs` here, outside all Cargo target autodiscovery.
No Cargo/graph/default-gate/core/legacy/plan input changes. Only the existing
15-case first tranche is graded; the18 later selectors cannot return PASS here.

## Frozen inputs before commands

Use Linux/Tux and actual verified pinned R00 tools. Record clean Git commit/tree,
source-freeze SHA256, tool hashes/versions, exact argv/environment, fresh private
paths and selected case before launching anything. Verify all freeze members and
unchanged protected inputs. The containing Git commit binds the freeze; no guessed
self-commit/hash is used. Preserve first RED and stop before correction/retry.

The baseline tool root remains
`/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools`.
Its historical receipt does not establish a fresh tool execution. Confirm actual
Linux x86_64/glibc, HZ100, monotonic clock, pidfd/wait4/proc and exact source/binary
bindings in the separate admission. No old C01 import or fallback provider is used.

## One existing core-host build after source admission

Set HRT_WORK to the reviewed checkout, HRT_PROOF to a new private absolute root,
HRT_TOOLS to the verified existing tool root, and HRT_PY to pinned Python3.12.
Require HRT_PROOF/core-target and the prospective driver ELF to be absent. This
build selects only the existing core package and emits actual artifact JSON.

```sh
cd "$HRT_WORK"
env CARGO_HOME="$HRT_TOOLS/cargo" RUSTUP_HOME="$HRT_TOOLS/rustup" \
  RUSTC="$HRT_TOOLS/rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin/rustc" \
  "$HRT_TOOLS/rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin/cargo" \
  build --locked --offline -p nsealr-core --target x86_64-unknown-linux-gnu \
  --message-format=json --target-dir "$HRT_PROOF/core-target" \
  > "$HRT_PROOF/core-artifacts.jsonl" 2> "$HRT_PROOF/core-build.stderr"
```

Do not continue unless that exact build exits0. Do not guess a hashed filename,
select the first glob match, reuse another checkout's rlib or execute a Cargo
example. The following proposed resolver/link command selects one compiler-artifact
for this exact core manifest/source/host target, records its actual path/hash and
all dependency rlib/rmeta hashes, then invokes pinned rustc by structured argv.
It performs no product runtime and starts no canary. This whole sequence still
requires the distinct source/build assignment; it has not run here.

```sh
"$HRT_PY" -B - "$HRT_WORK" "$HRT_PROOF" \
  "$HRT_TOOLS/rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin/rustc" <<'PY'
from pathlib import Path
import hashlib, json, subprocess, sys
work, proof, rustc = map(lambda value: Path(value).resolve(strict=True), sys.argv[1:])
manifest = work / 'crates/nsealr-core/Cargo.toml'
source = work / 'crates/nsealr-core/src/lib.rs'
hostroot = proof / 'core-target/x86_64-unknown-linux-gnu'
records = [json.loads(line) for line in (proof / 'core-artifacts.jsonl').read_text().splitlines()]
artifacts = [row for row in records if row.get('reason') == 'compiler-artifact'
             and Path(row['manifest_path']).resolve() == manifest
             and row['target']['name'] == 'nsealr_core' and 'lib' in row['target']['kind']
             and Path(row['target']['src_path']).resolve() == source
             and row['profile']['test'] is False]
assert len(artifacts) == 1
rlibs = [Path(value).resolve(strict=True) for value in artifacts[0]['filenames'] if value.endswith('.rlib')]
assert len(rlibs) == 1
rlib = rlibs[0]
assert rlib.is_relative_to(hostroot) and rlib.is_file() and not rlib.is_symlink()
deps = rlib.parent if rlib.parent.name == 'deps' else rlib.parent / 'deps'
assert deps.is_dir() and deps.is_relative_to(hostroot)
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
depfiles = sorted(path for path in deps.iterdir() if path.suffix in ('.rlib', '.rmeta'))
assert depfiles and all(path.is_file() and not path.is_symlink() for path in depfiles)
driver = work / 'docs/restart/implementation/QP01/human-review-timing/canary-source/driver.rs'
binary = proof / 'qp01-human-wait-canary'
assert not binary.exists()
argv = [str(rustc), '--edition=2021', '--crate-name', 'qp01_human_wait_canary',
        '--target', 'x86_64-unknown-linux-gnu', str(driver),
        '--extern', 'nsealr_core=' + str(rlib), '-L', 'dependency=' + str(deps), '-o', str(binary)]
receipt = {'argv': argv, 'artifact': artifacts[0], 'rlib': str(rlib),
           'rlib_sha256': digest(rlib), 'driver_sha256': digest(driver),
           'rustc_sha256': digest(rustc),
           'dependencies': [{'path': str(path), 'sha256': digest(path)} for path in depfiles]}
with (proof / 'driver-link-prelaunch.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
with (proof / 'driver-link.stdout').open('xb') as out, (proof / 'driver-link.stderr').open('xb') as err:
    result = subprocess.run(argv, cwd=work, stdout=out, stderr=err, check=False)
with (proof / 'driver-link-result.json').open('x') as stream:
    json.dump({'exit_code': result.returncode,
               'binary_sha256': digest(binary) if result.returncode == 0 else None}, stream)
raise SystemExit(result.returncode)
PY
```

Record the resulting ELF, actual loaded libraries and exact source/build receipts
separately. No typecheck, symbol/libc resolution, reproducibility or runtime fact
is inferred from this recipe. A changed source candidate needs affected admission.
No normal Cargo target or default CI command discovers the documentation driver.

## One positive only after separate runtime assignment

Set HRT_SUP to supervisor.py, HRT_BINARY to the admitted ELF and HRT_BINARY_SHA256
to its recorded digest. HRT_PROOF/positive must be absent. The trusted launcher
captures the common origin before exec of S in the same PID, so no third live
protocol actor is added. All S/R startup is charged from this origin.

```sh
"$HRT_PY" -B -c 'import os,sys,time; os.execv(sys.executable, [sys.executable,"-B",*sys.argv[1:],"--origin-ns",str(time.monotonic_ns())])' \
  "$HRT_SUP" run --binary "$HRT_BINARY" --binary-sha256 "$HRT_BINARY_SHA256" \
  --case positive --output "$HRT_PROOF/positive"
```

The15 first-case predicates require discriminating stream/stage/ACK/count evidence,
not the selected name or reason string. Positive requires original INIT binding,
full31-frame/ACK review, real5500ms wait, complete terminal1/1, known wait/EOF and
fresh retention/ledger<=5000ms before the private candidate is eligible. Preserve
raw captures and the compact report: origin/deadline, identities, baseline/raw CPU
samples including failures, phase endpoints and final completed guard/retention
allow independent reconstruction. A missing counter is not zero. SIGKILL collection
itself does not require a terminal, and a lost count cannot be fabricated.

## Separate oracle after known settlement

```sh
"$HRT_PY" -B "$HRT_SUP" verify --artifact "$HRT_PROOF/positive"
```

This later invocation imports only the existing hash-pinned S03 oracle/reference
and checks complete expected event, correlation, actual key, canonical ID and
zero-aux signature expectation. It cannot restore eligibility, infer backend
counters or qualify live publication. With complete positive terminal and verified
signature it closes the actual positive path; a before-call marker alone does not.
Post-core mutations key/template/signature/id/request-id/trailing are separate
explicit oracle invocations, never backend fault injection or an automatic batch.

## Remaining assigned first-tranche negatives

After inspecting the actual first positive and receiving its concrete assignment,
select each case from the unchanged15 IDs, one fresh directory and literal launcher
per case. Do not loop over all33. The18 later selectors remain source-only and
are deliberately ungraded here. Preserve first RED or inconclusive evidence.

case27 supervisor-gap is now the actual75ms delay INSIDE the final retention guard
after OS/trace work, following full review/signing/settlement. Its fresh completed
sample must reject the gap; an inside-budget entry timestamp cannot qualify it.
false-wait-cpu must retain the raw offending sample/upper bound and first-WAIT/
no-resume/proven0/0 evidence. partial-draw requires no commit/exemption/gesture;
post-core-cancel requires the complete scoped result hash/length and complete1/1.
Pre-sign zero requires coherent complete terminal or truly complete source-bound
write-before-sign barrier. Marker presence without terminal is a possible-attempt
witness, not proof of an actual call/backend count. Truncation keeps total counts
unavailable while retaining positive prefix witnesses and actual collection.

All old25/50ms,5000ms active+CPU,5500ms wait, CPU/record/trace and4s shared cleanup
caps remain. Do not normalize an unrelated failure, relax a threshold, freeze a
clock, replace/retry the actor or label a report/kill request as collection. Unknown
ownership keeps the same S/handles/reservation quarantined. Additional actors,
decoder/live-publication work and any wider runtime campaign require their own
source/runtime admission; no formal task/release criterion is closed here.
