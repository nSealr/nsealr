# First real Python O/W integration checkpoint

Author `/root/sdk_dependency_probe`, admission540c4802; **PASS for one host
positive only**, pending root review of this checkpoint. Source frozen at
`1fd951c37be5705aaedae46031f2e19d89c490fb`; the recorder-only PIPE correction is
`579577dc0a18ddeb98bdffbd066e84e776296ca8`, tree
`bd35cde69861447a7bf303e92ac402513090b6ff`. Module, minimal tests, O/W, framing,
oracles and budgets are byte-identical between those commits. No source edit
followed the real execution; this tail adds only proof/limits.

The opt-in module exposes an explicit `RgbOwnerRuntime.reserve` admission owner.
It strongly retains its single-use operation, including quarantine, and admits
replacement only after explicit close and known collection. API calls share one
thread; the process may have unrelated threads. The fixed trusted child bootstrap
maps six fresh inherited pipe ends >=6 to child0..5 with `dup2`, then execs the
fixed O. `Popen(close_fds=True, pass_fds=...)` supplies the ends; no parent `dup2`
or `preexec_fn` is used. Only O owns/collects/signals W. This is not hostile-host
isolation, an installed runtime provider or a production process supervisor.

## Original RED and actual positive

`evidence/micro-01/outer.stderr.log` preserves exit1 on original1fd: the local
transparent recorder proxy omitted `subprocess.PIPE`. `build_artifact` failed
while evaluating its arguments, before calling Cargo; there was no actual build,
O or W. Correction579 adds the real PIPE constant and updates only its source
binding. The whole existing helper uses `run` and `PIPE`; neither it nor its
source/manifest/artifact checks was modified. The accepted review's
`provision-observer.py` also records the real `subprocess.run`, but its entrypoint
calls both native and worker provisioning, outside this worker-only proof.

Actual command, from the clean implementation worktree:

```sh
python3 -B docs/restart/implementation/QP01/python-owner-adapter/micro/run-micro.py /home/tux/nsealr/.restart-tools/goal/qp01-python-owner-adapter-runtime-2026-10-24/micro-02 579577dc0a18ddeb98bdffbd066e84e776296ca8
```

`micro-02/command.json` records source/tree, actual argv/cwd, Python3.13.5,
Rust1.95.0/Cargo version and fresh CARGO_HOME. The nested default target was
absent; no CARGO_TARGET_DIR/CARGO_BUILD_TARGET override was admitted. The producer
built only W with root vendor, locked/offline, using the actual default
`apps/pi/qr-worker/target/release/nsealr-qr-worker`. The tracked exact ignore
pattern was checked with global excludes disabled. Cargo's real JSON stdout,
original stderr and actual artifact binding are retained. Compiler actions are
not claimed reproducible or equivalent to a second build.

One actual O2234199/W2234200 then passed:

- Independent172800B RGB `64d9be60…` → exact259B `88a16190…`; bytes and parsed
  object equal the original transport vector with numeric version2. Expected
  bytes are never supplied to O/W.
- Live W ELF SHA `3c92a8be8a5102a67da1d8eef6c4232872849774722c572796ec33053c46e1b8`;
  source/manifest/compiler-artifact/before-after binding, phase PPID/SID/PGID,
  AS268435456, CPU1/2, CORE0 and actual W fd0/1/2 identities match. The actual
  ELF is retained as data in `actual-worker.elf`, not a product entrypoint.
- O reports actual W raw wait0/collectorO and all W IO settled; the adapter
  independently collects O with raw wait0. Readiness R+EOF, status records,
  private result, all four reader EOFs and parent-owned FD closure are retained.
  A later positive-PID wait gets ECHILD only after that known actual collection.
- Parent live3/4/5 identities, inheritable flags and sentinel contents remain
  unchanged. `/proc/O/fd` proves the new pipe mapping (fd4 wrote R and closed);
  the parent FD baseline is restored while an unrelated real thread stays alive.
  The runtime still strongly references the same operation after collection.

`evidence/micro-02/result.json`, `owner-ready.json`, `worker-ready.json`,
`settlement.json` and raw `status-wire.jsonl` contain the original records.
Outer exit0 and clean source before/after are recorded. Build tooling has its own
compiler children; the diagnostic itself created exactly one O and one W, with
zero C/Node processes. Post-run environment context is explicitly separate from
the actual command environment.

Three pre-child checks pass on the frozen source: invalid worker config,
invalid RGB and strong reservation/replacement refusal. Their mocked spawn must
never be called; they are not process-success evidence. Original development
and final qualified preflight outputs are retained separately.

## Limits and stop point

This checkpoint runs no cancellation/timeout/quarantine/helper/parser-negative
matrix, full Pi suite, full makeci or hosted CI. Failure paths remain unqualified;
no quarantine recovery, destructor guarantee or hard-time guarantee is claimed.
The independent TS/C conformance gate remains unchanged. All13+CORE0,8s/4s,
512/704/947,client100ms/C5000ms are unchanged; no human-review budget is inferred.
No new dependency, registry, default factory, signer/key/native C, camera/SPI/GPIO
provider or UI is added. Python3.13.5 host evidence is not a Python3.9/3.12/ARM
support result. Existing kit/image/operator facts remain pending; no physical,
optical, custody, production, task-criterion or release qualification follows.

Stop here for the admitted root checkpoint review before any negative matrix,
Pi/fullCI or provider layer. The source still requires distinct affected review
and normal mandatory integration gates before adoption.
