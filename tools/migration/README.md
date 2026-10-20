# A02 isolated migration tooling

The coordinator admitted the exact 732f742 package at 0a8bb620 after independent
review b9d5d96e. The original preparation records below remain historical.
`assemble.py` performs only that admitted selected-file import, starting from
empty Git and exact public core ancestry. `transforms.py` declares every later
path, preimage, postimage and mode before mutation. `patches/series.json` is the
ordered exact replay input; transformation authoring templates may have evolved
and must not be rerun as a substitute for those frozen patch bytes.

`replay.py` assembles into an absent private destination, reapplies each exact
patch, verifies each tree and commit, compares the first assembly, bundles the
candidate and restores/checks every allowed object. It never adds a remote or
publishes a package. Source recovery bundles remain private backup, never target
intake. `test_assemble.py` exercises unselected branch and unreachable-object
exclusion; `test_replay.py` checks patch/declaration tampering.

Example (use the pinned interpreter and the protected approved sanitizer output):

```sh
python3 tools/migration/replay.py --author-repo "$PWD" \
  --source-root /home/tux/nsealr \
  --privacy-root "$PWD/tools/migration/.runtime/privacy-01" \
  --destination "$PWD/tools/migration/.runtime/new-replay" \
  --expected-target "$PWD/tools/migration/.runtime/rehearsal-01/repository"
```

The approved two-file exception requires its protected exact sanitized inputs;
never substitute private source history or original excluded document addresses.
Execution exports include only explicit public logs and approved source records.
Actual product acceptance is `make ci` in the assembled repository, using its
pinned bootstrap. Evidence, final distinct review and coordinator adoption remain
separate; no tooling exit code itself changes the task graph or permits archival.

## Historical preparation usage

These tools read exact Git commits, write a protected local inventory, and create
and verify protected recovery bundles. They have no target import, assembly,
remote mutation or publication operation. The accepted specification remains at
`docs/restart/implementation/A02/brief.md`; its four reviewed preparation files are
unchanged. The provisional preflight inputs are deliberately separate from future
admitted import inputs.

`admission-inputs.json` freezes the final `f2ef70f` input after repaired S01 adoption
and successful main CI. It preserves the earlier provisional manifest and records
the corrected overlay chain; it does not grant import admission. From the same
runtime parent, run the following with distinct absent destinations:

```sh
python3 tools/migration/admission.py overlay-chain --manifest docs/restart/implementation/A02/admission-inputs.json --source-root /home/tux/nsealr --destination "$PWD/tools/migration/.runtime/overlays-01"
python3 tools/migration/admission.py recover --manifest docs/restart/implementation/A02/admission-inputs.json --source-root /home/tux/nsealr --destination "$PWD/tools/migration/.runtime/recovery-01"
python3 tools/migration/admission.py public-refs --manifest docs/restart/implementation/A02/admission-inputs.json --source-root /home/tux/nsealr --destination "$PWD/tools/migration/.runtime/public-refs-01"
python3 tools/migration/admission.py canonical-plan --manifest docs/restart/implementation/A02/admission-inputs.json --source-root /home/tux/nsealr --destination "$PWD/tools/migration/.runtime/plan-01"
```

Use the verified pinned Python interpreter when recording acceptance. Recovery
freezes all local ref objects, captures them in a new protected bare repository,
creates and verifies its bundle, restores into another absent bare repository,
then checks every restored ref and the selected commit/tree plus `git fsck`.
Canonical source refs and files remain untouched. These repositories are recovery
copies only; no consolidated product exists. Raw logs, bundles, private ref names
and all restored objects stay in the mode-0700 ignored runtime. Only the sanitized
summary may enter public evidence. Permissions and corruption refusal are tested.

The overlay command checks exact source artifacts and pre/postimage continuity;
it does not claim patches were applied. The canonical-plan command executes the
existing complete validator and its controls against the exact clean canonical
checkout, verifying source/evidence correspondence before and after. Public refs
are queried read-only; evidence tags are review anchors, not release versions.
Every command records tool environment, timestamps, exit status and log digests.
User-space version pins do not make the OS or hosted CI hermetic.

From the author worktree, with an existing ignored runtime parent:

```sh
mkdir -p tools/migration/.runtime
python3 tools/migration/rehearse.py prepare \
  --manifest docs/restart/implementation/A02/preflight-inputs.json \
  --source-root /home/tux/nsealr \
  --destination "$PWD/tools/migration/.runtime/preflight-01"
python3 tools/migration/rehearse.py preflight \
  --destination "$PWD/tools/migration/.runtime/preflight-01"
python3 -m unittest discover -s tools/migration -p 'test_*.py'
```

`prepare` returns 0 when inventory creation succeeds. It creates only three JSON
files inside a new mode-0700 directory, with mode-0600 files. Its summary always
states `import_allowed: false`. `preflight` rechecks source content, manifest,
test-file inventory and closed evidence; it returns **2** for a valid inventory
whose import remains blocked, and **1** for invalid/tampered inputs. No command
can claim the import gate passed in this increment.

Selection rules are ordered and fall back to an explicit disposition. Each file
records source commit/path/blob/mode, chosen rule, reason and proposed destination.
Selected files add SHA-256 and candidate license notices. Excluded private blobs
are not read: their Git identities and exclusion reason suffice for planning.
Root notices are checked against recorded hashes; they do not grant blanket
approval for nested rights or privacy. Destination collisions and snapshot
differences become explicit blockers. Hidden tracked files are never filtered.

The complete local inventory can contain private source path names and local refs.
Keep it in the protected ignored runtime. Publish only the reviewed summary and
hashes; do not copy that inventory, private bundles, source blobs or credentials
into public Git. The script prints a summary without private path lists.

Closed evidence is read from the graph at the supplied current source commit.
Artifact digests, result manifests, acceptance evidence paths, review identities
and input/candidate bindings are checked. Markdown relative links are inventoried;
unresolved historical links remain a reconciliation obligation, never an excuse
to alter frozen evidence. This focused closure check does not replace the plan's
complete structural validator or substantive review. Static test names are an
initial inventory; dynamic/generated cases require framework collection and an
explicit case disposition before import.

Before import can be implemented or enabled, reconcile the final adopted S01 main
tuple and successful main CI; corrected provenance/default bootstrap review;
complete selected-file rights/privacy/map and all current closed evidence;
remote evidence refs, private bundle creation/restoration; and meaningful test
case dispositions. Reuse existing before-state evidence only under the approved
equivalence rules. Complete migrated acceptance must actually execute later.

Any newer main commit, including S03 integration, needs a new explicit source pin
and inventory. Existing-source retention includes newly merged core modules;
never replay an old wholesale tree over them. When the actual migrated CI is
edited, evaluate `push.branches: [main]` alongside `pull_request` and
`workflow_dispatch`, retaining required verify/application checks, normal reviewed
merges and actual main post-integration CI. This increment changes no workflow.
