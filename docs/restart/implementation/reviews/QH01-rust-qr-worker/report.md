# Independent fixed-image Rust QR worker review

**PASS_host_fixed_Rust_QR_worker_experiment_only** on author candidate `5fa5ec3afd0cf1f343743fe347b61728a242b15c`, tree `938646d04c397c60989273b1b413142e732a5670`. No blocking source or runtime finding was identified in this finite experiment. This is an independent build and fixed-public-image result, not product decoder selection, integration or task acceptance.

Reviewer `/root/a02_resume` is distinct from B01. The entire new105-line Rust worker,292-line Python controller, pre-code brief/expectations/parameters, Cargo manifest/lock and build commands were read before execution. Root separately owns the whole118-file author packet, archive/license inventory and claims review. This review checks the inputs actually used for its independent build/run and does not duplicate that whole-packet audit.

## Source and supervision

The worker source has no fixture names, known envelope bytes or fixture-specific output selection. After its real `setsid`, it waits for one-byte G, reads the fixed172800-byte RGB input, checks equal channels, and passes the first channel through `PreparedImage::prepare_from_greyscale(240,240,...)`. It calls actual rqrr0.11.0 `detect_grids`, requires exactly one grid and calls `decode_to` with a fixed512-byte `Write` implementation. No decode-to-String intermediate is used.

The writer checks `input.len() > CAP - len` before copying each supplied chunk. It returns WriteZero and records overflow without appending that chunk. `decode_to` can write partial output before failure; all such bytes remain in the private fixed staging array. Only successful complete decode reaches stdout publication. The611-byte fixture therefore has a distinct writer-overflow exit42 and zero publication; blank has no-grid exit20. The512 cap remains an experimental input, not a new product requirement. Upstream detector/internal allocation/work budgets remain unqualified.

The controller hashes the original corrected06d supervisor before importing it. `Owner`, `raw_wait`, `open_fds`, `context`, limits, child environment and small serialization/hash helpers are reused directly from unchanged bytes. The new baseline dictionary must equal the old one at import. The [prior independent review ccf1850d](https://github.com/nSealr/nsealr/blob/ccf1850d65e995722493554af97f54d021e000c2/docs/restart/implementation/reviews/QH01-linux-worker-correction/report.md) remains applicable to those unchanged helpers; its old22 campaign and delayed-admission regression were not rerun or attributed to this adaptation.

The adapted supervision body was reviewed in full: exact fixture relation/hash checks before child creation; trusted absolute native argv with no QR bytes; CLOEXEC pipe actions; bounded parent polling of kernel SID=PGID=ownedPID; unchanged prlimit/readback before G and image; current identity before each write; concurrent nonblocking streams and4096-byte requests; at most512 retained bytes per stream; owned positive-PID signalling; actual inherited `wait4` status collection; selector/FD closure before known-owner release; unknown status quarantines. Success and the two expected negative classifications each take a fresh monotonic sample after settlement and require it before the unchanged8-second deadline. This is a logical classification/admission point, not a hard-return or real-time guarantee. Failure stops subsequent cases.

## Independent build and executable binding

The [preflight](source-validation.json) checks candidate/tree,16 pinned runtime/source inputs, eight source-history bindings, all13 unchanged baseline values and CORE0. The original expectations remain byte-identical to pre-code commit `0751088f44756dcab4feb74c3beed9d86f6eafee`; runtime source/manifest/lock bytes equal `142135cd70f920e104aa01841ceeeca794256440`.

Exactly one [release build](build-command.json) ran with the immutable R00 Rust1.95.0 toolchain, unchanged flags, `--locked --offline`, and `--manifest-path` from `/home/tux`, outside the product workspace. Only11 checksum-matched Cargo archives plus the offline index were copied from the authorized author cache. No extracted source directory or target artifact was copied. Cargo extracted dependencies locally and compiled into an absent, fresh review target. Exit0; command elapsed1.269103 seconds. No fetch, install, product config/vendor/lock or R00 mutation occurred.

The independent ELF is669136 bytes, SHA256 `b794d46b724cfa0dbd1fd2dfb8b36a27624325ed2cd73f4e77972b97a06a1eaf`. The author's ELF hash `d0bd5e36d9303cab7c33aebf868e5f52394265b95f3b851a3366f2a8203db559` differs. Build directory identities differ; no flags were changed to force equality and no general reproducibility claim is made. [Binary context](binary-context.json) records the actual compiler, feature graph, ELF64 x86-64 PIE, interpreter, version requirements, dynamic library hashes and host link-tool context. ELF `.comment` identifies LLD22.1.2; the recorded host `cc`/`ld` lookup is context, not an actual linker-exec trace. The binary has no setuid/setgid bits or file capabilities.

The unchanged controller hard-codes its native executable path. Root explicitly authorized the [external wrapper](run-controller.py) to bind only module `BINARY` to this review-local ELF. It verifies the controller hash and ELF hash, imports the unchanged controller, sets that sole runtime input, invokes its normal `main()` with unchanged five-case order, and verifies the ELF hash afterwards. The [runtime command](runtime-command.json), controller context and all five `os.posix_spawn` argv records bind that same absolute path/hash. No controller threshold, check, worker byte or test case was modified. A live `/proc/PID/exe` sample or kernel exec trace was not collected.

## One independent five-case campaign

Exactly one full campaign used the pinned R00 CPython3.12.15 environment with only scoped temp/cache/no-bytecode overrides. First198 passed before the dependent rows. Command exit0, elapsed0.132345 seconds; all5 rows PASS, none masked. These are finite host timings, not client/device latency qualification.

| Existing public13949 image | Independent observed stdout | Actual exit | Outcome |
| --- | --- | --- | --- |
| response-get-public-key | 198 exact original bytes | 0 | Complete decode eligible |
| request-get-public-key | 98 exact original bytes | 0 | Complete decode eligible |
| request-kind-1-basic | 259 exact original bytes | 0 | Complete decode eligible |
| response-kind-1-basic | 0 bytes | 42 | `output_overflow retained=512 limit=512 refused_chunk=1` |
| blank | 0 bytes | 20 | `no_qr grids=0` |

For each row the actual kernel session was established before policy readback, G and image input; initial inherited identities are separate observations. Each wrote1 control byte plus172800 image bytes, with44 actual identity checks before writes. Read/write requests stayed within4096, retained stdout/stderr stayed≤512, and no parent signal, parent stream overflow, deadline invalidation or harness error masked the intended outcome.

Actual acquired status and FD/callback settlement preceded each fresh admission/classification sample. The same owner progressed through generations1–5, including reuse after writer refusal; live and acquired-status/pre-settlement reacquisition both refused. All5 direct children were collected, all5 `/proc` entries plus the controller entry were absent after return, actual final thread count was1, and parent identity/limits/FD invariants passed. [runtime-analysis.json](runtime-analysis.json) records29 independent checks against the raw traces and retained stream files. All input/toolchain/config hashes were unchanged afterwards.

## Limits and recovery

This result is restricted to the five existing fixed greyscale digital RGB assets and this trusted Linux x86_64 worker. The adapted controller's broader fault paths receive source review here; the old22 fault campaign remains evidence on its original corrected Python experiment only. No second regression, stress/corpus run or target fault campaign is implied.

There is no full rqrr allocation/work API contract, RSS/cumulative allocation bound, arbitrary-descendant containment or secrets sandbox claim. No keys, signing, crypto or real client interoperability ran. This does not select a final decoder, enable a route, change a product cap/framing/profile, port TypeScript/product code, qualify ARM/Pi/P4/camera/physical hardware or complete any of the47 task criteria/releases. No CI or PR was started.

The full Git whitespace check returned2 for native `readelf`/`cc` raw-output formatting; its initial check wrapper consequently exited1. [whitespace.json](whitespace.json) preserves the exact diagnostic and raw-file hashes. Those three tool logs remain byte-for-byte unchanged; a separate check of authored review text/code/JSON passed. This is a packaging observation, not a hidden build or campaign failure.

Only this new review prefix is written. Original worker/source/expectations, historical failures and earlier reviews remain unchanged. The ignored local Cargo cache and independent ELF remain recoverable under `.runtime/`, described in [runtime-retention.json](runtime-retention.json); all commands completed and no experiment process remains. Root owns its separate source/provenance review and any later integration decision.
