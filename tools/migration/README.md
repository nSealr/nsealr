# A02 inventory and preflight

This first tooling increment reads exact Git commits and writes a protected local
inventory. It has no import, assembly, bundle-creation, remote mutation or
publication operation. The accepted specification remains at
`docs/restart/implementation/A02/brief.md`; its four reviewed preparation files are
unchanged. The provisional preflight inputs are deliberately separate from future
admitted import inputs.

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
