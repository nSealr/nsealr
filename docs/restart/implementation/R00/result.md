# R00 executed baseline — 18 October 2026

The cold bootstrap and complete integration recipe passed. The software baseline
still contains the inherited companion API-document freshness failure; the
aggregate runner correctly returns failure. This report does not claim an
all-green multi-repository CI run, a repaired host security boundary or a
qualified physical device.

Code candidate: `7bcb9fb5685feae458be62e0b888ffe912a2e065`, rebased onto reviewed
coordinator documentation at `61b0c39`. [Draft PR 9](https://github.com/nSealr/nsealr/pull/9)
tracks delivery. [Execution data](execution.json) records all eight repository
inputs; [the artifact index](artifacts.json) hashes 302 preserved files.
Independent final review and integration are recorded separately by the
coordinator. The author has not self-approved task closure.

## Reproduction and isolation

Use [the bootstrap instructions](../../../../tools/baseline/README.md).
The one entry point installs Python **3.12.15**, Node **24.22.0**, npm **11.19.1**,
pnpm **10.33.4**, rustup **1.29.1**, Rust **1.95.0**, cargo-deny **0.20.2** and
cargo-llvm-cov **0.9.1**. Runtime archives and Python wheels are hash checked;
Node dependencies use frozen lockfiles. Later legacy Python setup reads only
an isolated wheelhouse with exact constraints. Rust utilities are explicitly
prebuilt official release binaries; the core itself compiles from source.
The final core CI Python patch is also pinned, and `make test` now runs the
bootstrap boundary suite.

Five recorded installations used different absent destination directories and
separate dependency/config/cache trees. The first exposed the provenance issue;
the second confirmed the original cold-install procedure. The corrected full
run and its fresh-Git-clone replay used `f853757a5080003036aacb797999410398816f16`.
The tested commits remain reachable through Git tags
`evidence/r00-full-20261018` and `evidence/r00-relative-20261018`.
The final relative-mirror correction was independently cold-installed and smoke
tested at `e1336ef4c062ef37cecd00c96e20f551c02ecd31` with `--mirrors ../../..`.
Source transport reused authorized local Git objects through fresh fetches;
working-tree contents, dependency stores and installed runtimes were not copied.

The host was Debian 13.7, x86_64, glibc 2.41, GCC 14.2.0, GNU Make 4.4.1 and
Git 2.47.3. Kernel, system libraries, compiler, TLS trust roots and Git credential
configuration for source access remain host inputs. This is cold user-space
installation evidence, not a hermetic operating system or container claim.
Full migration integration requires access to its source repositories;
`--core-only` provides a separate public-core route without that access.

Repositories are siblings **within** the new destination. The public nsealr
repository deliberately uses the local `firmware/` compatibility folder expected
by pinned legacy integrations. The old private workspace bootstrap instead
nested clones under `workspace/` and installed no toolchains. No maintainer
checkout, source repository history or product/vector behavior was modified.

## Observed checks

The full run used `make -k ci` in each repository, preserving failure while
continuing later independent gates. It then ran one uninterrupted lab
`make integration`, without command-line PYTHON/VENV overrides.

| Check | Observed result |
| --- | --- |
| Core CI | Pass: formatting, clippy, 226 core tests, 20 simulator tests, std/target build, dependency checks, coverage ratchet and reproducible builds |
| Specs | Pass; 79 tests |
| Companion | 611 tests pass, 1 live-relay test skipped; package/browser/examples/type checks and audit pass; API freshness makes CI exit 2 |
| Raspberry | Pass; 150 tests |
| Archived smartcard | Pass; 40 tests |
| Hardware documentation | Pass; 43 tests; no PCB/assembly qualification |
| Website | Pass; build/check and 9 tests |
| Lab with declared overlay | Pass; 156 tests |
| Full integration | Pass: all 20 recipe steps, including 546 fixture comparisons, browser/native-message boundaries and simulated Pi/card flows |
| Fresh-clone replay | Cold install, core test/target smoke, fixture comparisons and integration-helper negatives pass |
| Relative-mirror replay | Cold install and the same smoke pass |
| Tool boundaries | 4 tests pass; occupied destination, incorrect download hash, inherited environment contamination and retained failing output |
| Provenance regression | Original checker fails valid metadata for the expected reason; corrected 24-test snapshot suite passes including bad commit/inventory/hash/vector cases |
| Final rebased controls | `make test lint audit docs` and drift audit over changed files pass |

The reproducible device rlib SHA-256 was
`bc2c4cfb3886f976aa19e8d812b653fc3cfa36f2fc1c42ad54dba4251ac3c369` across two
clean same-path builds and a separate filesystem path. This is a core library
artifact, not a qualified device application.

See [full command results](evidence/final/suites/commands.json),
[full integration output](evidence/final/suites/08-full-integration.log),
[environment manifest](evidence/final/environment-manifest.json) and
[replay results](evidence/final-replay/smoke/result.json). Timestamps, argv,
working directories, environment overrides, exit codes and raw log hashes are
preserved, including the unsuccessful observations.

## Failure dispositions

1. **Stale generated API:** fresh companion CI fails `docs/api.md` freshness.
   A disposable regeneration adds omitted core crypto/session exports and
   passes freshness, but its API-review checker then correctly rejects the old
   review digest. Original and generated document hashes and the exact delta
   are [preserved](evidence/diagnostics/api-drift.json). No source document or
   review digest was silently rewritten. S01/source disposition must review
   the eventual exported surface; R00 only classifies this inherited failure.
2. **Launcher stderr:** the controlled Node 26.4.0/npm 12.0.2 diagnostic runs
   the same original service-context assertions twice. At npm log level
   `notice`, empty-input service exit is zero but stderr contains npm notices
   and an npm configuration warning; the strict quiet assertion fails.
   Changing only npm logging to `error` produces empty stdout/stderr and all
   service-context negative checks pass. [Captured subprocess outputs](evidence/launcher-controlled/notice-empty-input.json)
   and the [quiet control](evidence/launcher-controlled/error-empty-input.json)
   retain the original bytes. Application stderr is never filtered. The pinned
   Node 24/npm 11 tuple passes with that environment too.
3. **Recursive Make overrides:** historical PYTHON/VENV command-line overrides
   installed Raspberry into the outer audit virtualenv while its launcher
   expected `raspberry/.venv`. This bootstrap uses environment-selected runtime
   paths and each repository's own unmodified setup variables. The complete
   Pi/card tail passes in the same full invocation. No tail-only rerun stands
   in for full integration.
4. **Fixture provenance:** the new core's `SOURCE.json` was mistaken for an
   upstream specs fixture by the pinned lab checker. The
   [bounded addendum](fixture-provenance-addendum.md) and hash-bound CC0 overlay
   validate the actual specs commit, complete source/snapshot vector inventory
   and every recorded hash before excluding exactly that metadata file.
   Existing real-fixture byte checks and required-glob checks remain. Original
   failure, red/green regression and the entire corrected integration are saved.

## Candidate coverage and limits

The full-run candidate preceded the mirror path fix, CI hook and rebase. The
[coverage record](evidence/candidate-equivalence.json) verifies identical Git
objects for `crates`, `apps`, `vendor`, fixtures, Cargo inputs, Rust pin and core
CI scripts. Later source changes are the relative mirror resolution, CI test
hook/Python pin and reviewed coordinator documentation/control records. The
relative-path cold replay and final affected checks cover those changes.
Exact remote CI belongs to the final candidate's GitHub check record, not an
old readiness CI result. Metadata commits following this report do not change
the reviewed implementation scope.

Tracked source files remain unchanged except the two explicitly declared lab
overlay files. Hardware/site `compileall` produced untracked Python bytecode;
that output is recorded rather than mistaken for product source drift.

The [skip record](evidence/final/suites/skips.json) explicitly excludes live
relay qualification, installed interactive browser sessions, real USB/card
signing, local physical review/input, camera/GPIO/display, secure-element
custody, provisioning, manufacturing and entropy qualification. The separate
[host safe-probe output](evidence/safe-probe/probe.json) reports
`ready_for_hardware_acceptance=false`, blocked Pi hardware/modules and a failed
host swap check. A successful safe-probe assertion validates its report shape
and disabled production flags; it does not make those blocked checks pass.

No security defect is waived by this baseline. Existing vectors and passing
simulators describe current behavior; accepted product requirements, S01–S03
and actual device gates still determine correct and releasable behavior.
