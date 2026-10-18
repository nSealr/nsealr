# S01 snapshot and full integration result

All eight software CI suites and the uninterrupted 20-step lab integration
recipe passed. The complete native fixture snapshot now matches merged specs
`45f8b6ff1123f3f55be4ce457fd1008e91043cc2`, including its metadata-v1 response
vectors. This is integration evidence for independently reviewed Bridge/specs
changes; distinct final review and coordinator acceptance remain required.

The tested core fixture candidate is
`41f5d2d193e4a00227737e1f8d71ce57e39ea889`, based on merged core
`9194e292aa8a3176874cc9bf5814cefc26b6fe1a`. The lab overlay/helper candidate is
`23e8b376ec8bcc7c2c46368aac5b4ac272f8022f`. Companion's actual merged input is
`678796900e462f5504e47fe934e2e5f23d85824f`: its complete tree equals reviewed
delivery `beb8d25da73661e4ede21bf62deb0cdb84406c5f`; changes after reviewed product
source `9e023ccef300ddeb738c377fe68b130a94123477` are evidence/review documents.
[Execution data](execution.json) records all eight exact source inputs.

## Snapshot and bounded tooling corrections

The snapshot contains all 221 upstream vector files. Its 22 raw changed paths
are exactly the accepted upstream delta: 18 modifications and two rename pairs.
`SOURCE.json` records the actual upstream commit and every file's SHA256; the
original CC0 license is unchanged. [Migration hashes](fixture-migration.json)
and [source correspondence](evidence/source-correspondence.json) preserve the
comparison. Twenty native/code/tool top-level objects are unchanged from the
core input; no new native protocol implementation is claimed.

Two declared CC0 overlays apply only to the isolated pinned lab checkout:

1. R00's original provenance overlay is unchanged. It validates the exact specs
   Git HEAD and complete upstream/snapshot inventories and hashes before
   excluding only `SOURCE.json`. All real vector comparisons remain active.
2. The [metadata-v1 overlay](lab-metadata-v1.json) corrects the inherited v0-only
   auth-negative selector. It requires the exact three expected path contents,
   rejects missing, stale-version, extra or partially discovered cases, and
   retains the actual CLI error/output-file assertions. A02 must select and
   review this tooling in its new owner; no canonical lab source was edited.

The [original discovery failure](evidence/overlay-regression/03-metadata-v1-discovery-red.log)
selects zero of the three required v1 cases. The
[corrected discovery](evidence/metadata-v1-regression/04-metadata-v1-discovery-green.log)
and [omission regressions](evidence/metadata-v1-regression/05-metadata-v1-inventory-negatives.log)
pass. The full recipe explicitly records execution of the credentials,
fragment and wrong-scheme auth URL negatives. The original provenance failure
and corrected 24-test provenance suite are also preserved.

## Executed checks

| Gate | Result |
| --- | --- |
| Core full CI | Pass: 227 unit, 4 secret-boundary and 20 simulator tests; lint, target build, dependency checks, coverage and reproducible builds |
| Specs | Pass; 92 tests |
| Companion | Pass; 716 tests, 1 live-relay skip; API freshness/review and browser/package gates pass |
| Raspberry | Pass; 150 tests |
| Archived smartcard | Pass; 40 tests |
| Hardware documentation | Pass; 43 tests |
| Website | Pass; build/check and 9 tests |
| Lab with declared overlays | Pass; 157 tests |
| Full integration | Pass; all 20 steps, 546 fixture comparisons and all three required v1 auth negatives |

The [complete command record](evidence/suites/commands.json),
[full integration output](evidence/suites/08-full-integration.log) and
[step/case summary](evidence/integration-summary.json) preserve the result.
The original R00 companion API freshness failure remains historical evidence;
the independently corrected current companion source passes that gate.

Native simulator parity covers its declared categories. The complete snapshot
also retains categories that harness explicitly excludes; Python/specs and
TypeScript consumers execute metadata-v1 behavior. Host/card/Pi simulation
success does not establish physical acceptance.

## Reproduction, integrity and limits

This was **not a cold-install replay**. Fresh depth-one tracked checkouts used
exact commits in sibling folders, with core named `firmware/` for the legacy
integration layout. Runtime/dependency caches were copied into an owned
directory from the retained R00 installation; no working checkout, virtualenv
or `node_modules` was copied. Retained runtime archive hashes were rechecked and
absolute tool links relocated. Versions remain Python 3.12.15, Node 24.22.0,
npm 11.19.1, pnpm 10.33.4 and Rust 1.95.0.

[Preparation commands](evidence/prepare/commands.json),
[runtime reuse and versions](evidence/runtime-reuse.json), and the
[controlled environment](evidence/environment.json) record the setup. Recreate
the sibling checkouts at [these commits](evidence/source-commits.json), apply the
unchanged R00 provenance patch followed by the hash-checked v1 overlay, and
record their declared source states. Local source-fetch paths in the record may
be replaced by canonical repository URLs while retaining the exact commits.
The existing `tools/baseline/run.py DESTINATION` then runs every software suite
and the full recipe using the destination's environment and source-state files.
Do not use recursive Make command-line PYTHON/VENV overrides or filter
application stderr.

The [artifact index](artifacts.json) hashes preserved inputs, commands, logs and
results. Tracked source stayed unchanged except the four declared lab overlay
files; explicit `compileall` produced untracked bytecode in hardware/website,
recorded in [final source verification](evidence/source-after-verification.json).
No private history or credentials were imported into this evidence.

The [skip record](evidence/suites/skips.json) excludes live relays, installed
interactive browser sessions, identified physical USB/card signing and local
approval, camera/GPIO/display, secure-element custody, provisioning, entropy and
manufacturing qualification. Kernel, system libraries/compiler, TLS roots and
HOME remain host inputs. No hardware resource, S01 task closure or merge is
asserted by this author report.
