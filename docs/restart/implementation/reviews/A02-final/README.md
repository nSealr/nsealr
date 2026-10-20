# Reviewer evidence

`review.json` and `review.md` bind the final exact author/product and ordered
criteria. `review-artifacts.json` hashes every other file in this directory;
the containing review commit binds that manifest without a circular hash.

`independent-replay/` contains only public command/result/log records from the
new absent owned runtime, including the 39 exact patches and actual bundle
restore/fsck. Repositories, bundles, private inventories and approved private
postimages remain protected in ignored runtime and are not exported.

The saved `probe.py`, `negative-probes.py`, `oracle-probe.py`, `run_checks.py` and
`runtime-checks.py` are exact execution snapshots using the original ignored
runtime layout. Their relative roots and full-source author pin intentionally
identify that run; use their recorded commands in the same layout to repeat it.
Full substantive execution used author f9a09ba before tracked review writes.
`delta-probe.py` runs from the repository root and checks the exact final Git
object correction above that anchor. `case-audit.py` accepts explicit author,
product and output arguments. All first observations, including the reviewer
case-audit enum error and intermediate coordinator stale-index finding, remain.

The original short direct probes recorded log filesystem creation/write times,
not precise process timing; this limit is stated in their provenance receipt.
The test/replay/runtime/case/delta command records contain recorded process
start/end observations. Pinned user-space tools and cached dependencies were
reused explicitly; no new cold-bootstrap or OS-hermetic claim is made.
