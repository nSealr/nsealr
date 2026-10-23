# Distinct cold-integration review

**PASS for the scoped host software cold integration**, final author candidate
`3494f43d0c96dbdfa1a941f5b14f642c1733353c`, tree
`9adda99d718b3f791aad9b2ac2d7b2946a4b2c42`. There are no open findings.

The review covers the SDK author's cold producer, current-checkout QR package and
vendored closure, explicit artifact initialization, third audit graph, Make
integration and current metadata. The executable input independently exercised is
`9d39469209afc8e35535cf8ba58dbe668a3f3224` / tree
`ae40e5a3f6b0c8d13238f2477a9f643ee5eda466`. The final package binding and verdict
are recorded in `review.json` and `final-source-correspondence.json`.

The reviewer authored the earlier operational-owner component, but did not author
these integration changes. This review reuses root's distinct component review
`032cbab9ac3fa2ce27463ed43c05b09df108c162` of `92913a83…`; it does not substitute
for that review. Root separately owns the completed-capture checker and its
mutation controls. Its internals are excluded here.

## Source findings

No source finding was found in the affected integration perimeter.

* The QR Rust source is byte-exact to the accepted RGB source `9220db12…`, SHA
  `e60b3bc2baec2eded7ee474e101cfa8debd1a88be76d6d7cffce31b4e3e1dcf1`.
  The standalone package changes only its own name/description/license metadata;
  `publish=false`, the isolated workspace, release profile and `rqrr=0.11.0`
  without default features remain. The lock changes only the local package name;
  all eleven registry package versions/checksums remain exact.
* Eleven actual cached crate archives were hashed against that lock and their
  regular members compared with the vendored closure. The closure contains 329
  files including eleven Cargo checksum maps; eight added directories contain
  211 files. The three reused directories and all 1,914 pre-existing vendor files
  remain byte-exact. Archive filtering and license filenames are itemized in
  `initial-source-vendor.json`. Root/host locks, existing Cargo source replacement,
  deny policy and R00 toolchain are unchanged.
* The finite producer builds from the current root checkout with `--locked
  --offline --release --message-format=json`. It selects exactly one matching
  compiler artifact, verifies source and manifest identities, checks that input
  hashes did not change during the build, requires ELF bytes and executable mode
  for the worker, then supplies actual paths and SHA-256 values. There is no
  retained-worker or historical-ref fallback. The native `exchange()` body is
  unchanged. The real producer and five cause-specific synthetic rejection
  controls were both independently exercised.
* Node requires the trusted absolute worker path, hash, ELF bytes and executable
  mode before creating C/O. The initialization-v2 contract keeps the old `1a4…`
  hash as historical provenance. The operational O and accepted lifecycle rules
  are unchanged. The two new C log keys separate this gate's observations from
  the original default client campaign; they do not alter timers or settlement.
* Make retains Bridge-before-Pi and the seventeen original obligations. It adds
  QR formatting, strict Clippy and three arithmetic/property tests, runs producer
  controls, provisions once, runs the whole Pi suite, then the original default
  5+14 client scopes and the separate first-owner gate. The audit wrapper adds
  the QR manifest to its existing standard fetch/check sequence. Fresh audit-data
  acquisition remains separate from vendored offline compilation; missing index
  metadata remains fatal through `--deny index-failure`. Four existing wrapper
  controls now cover all six command boundaries across three graphs.

## Independent execution

`preflight.json`, the six command/receipt directories and `execution-checks.json`
bind the actual run. A Git archive of source `9d…` was exported without `.git`.
CargoHome and the target directory started empty, and the build used only the
tracked vendor tree with the unchanged R00 tools. The recorded HOME is the
existing `/home/tux`; this is not a claim of an empty machine or an empty Node
store. The offline Node install used the explicit existing R00 store.

The actual unmodified producer ran once. `provision-observer.py` only records the
real Cargo invocation and returned JSON; it does not supply synthetic output or
alter build arguments. Both selected compiler-artifact records were non-fresh
release builds. The resulting native ELF is
`35a419a611a94817a7a6682cda5899b9400dff7c83ce4120aaa88171a364e23c`
(649,048 bytes), and the QR ELF is
`8b3ee7a24d643cae75a02383f5d84138cd011b4990aa8de47308a8890b103019`
(668,728 bytes). Raw Cargo JSON, actual filenames, source/manifest paths, ELF
inspection and the tool identities are retained. Different build-directory
hashes are accepted as observations, not forced into a reproducibility claim.

The offline Node install/build, one 39-subcase first-owner campaign, five producer
controls and four audit controls all exited zero. The 161 matrix records prove
that the newly built QR executable was observed at the actual kernel pre-G
phase, and all three native calls consumed the newly built library. Those calls
used the independently frozen 259-byte request and produced the expected
611-byte response. The real elapsed-deadline subcase kept 259 decoded bytes
private after W/O collection, while the timer callback had not yet aborted the
signal; the same currentness guard refused and C received zero bytes.

Process accounting is by unique PID: 20 native C processes, one C handshake
helper, 21 real O processes, 11 real W processes, and 11 no-W O helpers, totaling
64. W phase and terminal records refer to the same eleven PIDs, not 22 workers.
Every real W has an actual terminal wait (seven exit 0, four signal 9) and all
worker IO settled. Nine additional pure parser controls spawn no process.
All original PIDs were absent during the subsequent read-only observation.
The raw harness label still says `host_author_only`; this particular invocation
is an independent reviewer execution, and the raw label is preserved verbatim.

The reviewer did not repeat full Pi, full Make CI, or acquire fresh audit data.
The author's full local `make ci` at exact `9d…` exited zero in 319.01655 seconds
with clean source before and after. Its 492,016-byte raw log is SHA-256
`2de2df5f9efa5f99c2fdf87e1387d2a85ab08529fb77bcf3c5fd6bd231157fd8`.
The three real audit graphs have distinct standard fetch/check commands and
success results; all seventeen original obligations, unchanged coverage floors,
Pi194, original default5+14 and first39 remain covered by that author run. Its
fresh audit acquisition is not the reviewer's cached snapshot. The existing
repro check still covers core/host artifacts, not the new QR ELF or fixture
cdylib. Root's later normal hosted validation remains separate evidence.
Read-only post-execution verification confirms all
9,139 exported tracked blobs and executable bits remained exact to `9d…`.

All 226 declared runtime/gate postimages match `9d…` in the final candidate.
All 47 task states/formal criteria/dependencies/resources/releases and top-level
graph properties are unchanged; the other 45 task records are byte-equivalent
as JSON values to the component base. R00 changes only its three admitted current
artifact hashes. QP01 preserves old artifact/checkpoint entries and adds the
scoped current evidence; the index changes only its graph digest.

## Preserved limitations and errors

The early author producer-order test RED, stale-R00-metadata full-CI RED and
checker-format errors remain historical evidence with their original roles.
No old report has been rewritten as a run on this source.

Final packaging initially had one blocking metadata finding,
`QP01-COLD-REVIEW-01`: candidate `afc686e8…` listed an ignored, absent Python
cache file as an artifact. The author's `3494f43d…` correction changes exactly
one manifest: it removes that entry and changes 42 members to 41. All remaining
members match tracked Git bytes and the prefix contains exactly those 41 plus
the manifest. The rejected candidate and exact `git cat-file` witness remain
accessible in `packaging-finding.json`; this was not a product/runtime failure
and required no replay.

The first reviewer evidence-verifier invocation incorrectly obtained an empty
path-filtered Git tree from its untracked review subdirectory, so its source
inventory loop covered zero files despite an exit-zero summary. That claim is
explicitly invalidated. `verifier-initial/` retains the exact script, result and
log. Adding `--full-tree` and a nonempty-inventory assertion corrected this
read-only evidence check; no product source or runtime campaign changed.

The complete whitespace check exits 2 because the original `readelf` output has
trailing spaces and final blank lines. The separately recorded authored-file
scope exits 0; `whitespace.json` lists the exact generated raw exclusions. Both
outputs are retained, and no raw log is normalized to manufacture a clean check.

This is a host software integration result for fixed public fixtures. It is not
a default product route, UI integration, physical Pi/ARM/P4 qualification,
camera/lighting/framing or final-cap qualification, secret-key sandbox, timing
guarantee, distribution/ELF reproducibility claim, O-death recovery guarantee or
proof of the unknown-cleanup quarantine branch. No task criterion or physical
release is completed. The 100 ms client deadline, C's 5,000 ms safety timer,
thirteen worker parameters plus CORE=0 and all existing negative cases remain.
