# S01 — Core snapshot and cross-repository integration brief

Author: `/root/baseline_execution`. Specification reviewer: `/root`.
This phase joins independently reviewed Bridge and specs changes to the current
core snapshot. It does not implement another identity policy or close S01 from
metadata tests alone. Implementation starts after review of this exact brief.

## Inputs and ownership

| Repository / role | Exact input |
| --- | --- |
| nsealr core including merged S02 and R00 | `9194e292aa8a3176874cc9bf5814cefc26b6fe1a` |
| specs merged metadata-v1 / Python oracle | `45f8b6ff1123f3f55be4ce457fd1008e91043cc2` |
| companion reviewed product source | `9e023ccef300ddeb738c377fe68b130a94123477` |
| companion reviewed delivery with copied review evidence | `beb8d25da73661e4ede21bf62deb0cdb84406c5f` |
| companion actual merged main | `678796900e462f5504e47fe934e2e5f23d85824f` |
| lab | `3303ab17a28ed32419576627d5abb93db3999635` |
| raspberry | `d1534d9dcfba8fe4a35cea2ed3529e32a5003dc6` |
| smartcard | `ec5da94a05882122e8a794f55f1af3f96a95c696` |
| hardware | `340697d6713a671e9e01b0dc874ec999ab071601` |
| website | `9cec39a89d6a2d2cc5747b8aae9d4b47a52eb7cd` |

The coordinator supplied companion's actual merged main above. Verify its entire
tree equals the reviewed delivery and its product files equal the reviewed source;
do not follow a moving main silently. Core acceptance uses the committed fixture
candidate from this branch, with source correspondence to the core input above.

Editable tracked scope is only `tests/fixtures/specs/vectors/`,
`tests/fixtures/specs/SOURCE.json`, and this `docs/restart/implementation/S01/`
directory. Runtime checkouts, caches and tooling live in its ignored `.work/`.
No canonical task graph, R00 evidence/input, companion/specs source or canonical
lab checkout changes belong to this phase. Root owns readiness, final review,
merge and task closure.

## Snapshot contract

Import the complete tracked upstream `vectors/` tree, including `.gitkeep` and
categories the native simulator explicitly excludes. The current complete tree
has 221 files. The accepted metadata migration changes exactly 22 raw paths:
18 modifications, two removed sender-mismatch names and two added user-mismatch
names. Preserve exact upstream bytes; do not generate substitute expectations.
Record all old/new hashes and enforce no extra or missing files.

Set `SOURCE.json` to the exact specs commit above and regenerate its complete
file-to-SHA256 inventory. Preserve the original CC0 license bytes, repository
identity and complete-snapshot scope. The checker must validate both the source
checkout's actual Git HEAD and the complete upstream/snapshot inventories before
excluding only `SOURCE.json` from ordinary upstream byte comparison. Never
exclude real vectors or accept a partial inventory.

Prove unchanged native product, dependency and CI objects relative to the core
input. The imported metadata does not create new native protocol support or
claim that an explicitly excluded category was executed by the Rust harness.

## Bounded lab consumer overlay

Keep R00's existing CC0 provenance patch and manifest byte-for-byte, verify their
hashes, and apply them only to the pinned isolated lab checkout. Its source
commit check naturally follows the exact new specs HEAD; no hardcoded historical
specs pin is bypassed.

Read-only inspection found `invalid_auth_challenge_relay_step_vectors()` in
`scripts/integration_companion_nip46_cli.py` selects only
`nsealr-nip46-relay-response-step-v0`. Updated v1 negatives would disappear from
that integration path. A second CC0 overlay, stored in this owned directory,
may update only this metadata consumer and its direct tests/discovery guards.
Record its ordered base (after the unchanged R00 patch), exact patch digest,
before/after file hashes and selected-source provenance. Canonical lab stays
untouched; A02 must later decide how to import the selected corrected tooling.

Before correction, execute a check against the actual new specs that exposes
missing required negative cases. The corrected check must compare the complete
expected auth-negative path inventory and execute each case, including the
credential, fragment and wrong-scheme URL negatives. A nonempty result alone is
insufficient. Exercise omissions/version mistakes to prove incomplete discovery
fails; retain malformed/wrong-category exclusions and actual expected CLI
rejection/output-file checks. Do not weaken URL, signature, identity, stderr or
output assertions, and do not introduce a v0 compatibility requirement.

Any additional consumer failure is saved and classified before expanding this
bounded overlay or changing product behavior. An inherited failing gate remains
failed until a concrete correction is independently accepted.

## Execution and acceptance

Create fresh isolated tracked checkouts at exact commits in sibling folders
inside `.work/`, using `firmware/` for the core compatibility path required by
pinned lab scripts. Reuse the R00 pinned Python 3.12.15, Node 24.22.0/npm 11.19.1,
pnpm 10.33.4 and Rust 1.95.0 runtime tuple and recorded dependency caches where
useful. Record reused inputs and versions, use owned runtime/cache paths, and
label this an affected integration run, **not a cold-install replay**. Keep
recursive Make variables in the controlled environment, never command-line
PYTHON/VENV overrides. Preserve quiet npm launcher settings while retaining
unmodified application stderr.

1. Verify exact source commits, clean source states, overlay provenance and
   product-source correspondence. Save original fixture/provenance/discovery
   failures and corrected inventory/hash checks, including meaningful negative
   controls for missing/extra/mismatched vectors and wrong upstream provenance.
2. Run complete core `make ci`, including actual Rust vector parity and the S02
   secret-boundary tests; specs `make ci`; companion `make ci` and fixture
   verification explicitly selecting the isolated specs checkout; lab tests with
   both declared overlays. The existing R00 runner's independent `make -k ci`
   gates may also run the unchanged sibling suites with failure statuses intact.
3. Run one uninterrupted lab `make integration` with all 20 recipe steps. Show
   complete fixture comparisons, exact v1 negative-case discovery/execution and
   the existing browser/native/service/Pi/card simulation assertions. A tail-only
   run or an empty-loop pass cannot substitute for the complete recipe.
4. Preserve argv, working directory, controlled environment, runtime/source
   versions, timestamps, exit codes, raw sanitized output, source before/after
   states, skips and artifact hashes. Commit the fixture candidate separately
   from result metadata where needed. Record exact tested candidate, final
   correspondence and actual final CI; obtain distinct final review.

Existing live relay, installed interactive browser, physical USB/card signing,
camera/GPIO/display/local approval, secure-element custody, provisioning and
entropy/manufacturing exclusions remain explicit. Simulations and host checks
make no hardware claim. If full integration fails, preserve the failure and
keep S01 integration open; do not turn it into acceptance by relabeling the test.
