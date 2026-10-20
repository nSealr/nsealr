# A02 forward repair: immutable contract anchors after protected rebase

This bounded preparation follows actual main CI39408038674 failure on d931277.
[Source audit](source-audit.json) binds the failed run, source and exact equal-tree
old/rebased ancestor pairs. PRCI passed on the unrevised ancestry; a cold fetch
of protected rebased main cannot resolve the two original intermediate commits.
The checker must continue rejecting tampered data and forged manifests.

Keep the historical import86569e0 in manifest metadata and its strict identity
check. Add a separately named immutable runtime source-postimage anchor68508ea
for Git comparisons, and pin reviewed baseline59653fc. Both are already permanent
ancestors of current protected main and have exactly the original whole trees;
future rebases on top of main do not rewrite them. Do not point to HEAD, select
arbitrary same-looking ancestors dynamically, trust a current manifest hash,
fetch extra source branches or weaken provenance. No new contract baseline or
semantic/vector revision is proposed.

Allowed implementation: scripts/verify_contracts.py and scripts/test_contracts.py;
new proof under this directory; leading current docs/restart/README.md and
implementation/handoff.md may record actual integration failure/repair state.
Do not edit protocols/contracts/v1 bytes/metadata/consumers, frozen1508 files,
closed7 records, work-items acceptance/dependencies/resources/releases, crates,
apps, locks, toolchains, CI, coverage floors, old rehearsal/template/patch bytes.
Record the historical mapping in proof; keep earlier failed reports unchanged.

Before implementation, a distinct reviewer must accept this exact bounded brief.
Then use one author worktree and retain actual RED from a source fetch of only
main: both old intermediate ids absent, adopted ids present; current checker
fails. Fix the two runtime source/postimage comparisons without changing artifact
identity. Existing isolated tests must patch historical metadata and runtime
anchors separately. Add a meaningful actual-Git rewritten-history/cold-fetch
regression: declared historical import stays in the manifest, its old object is
absent, equal adopted source/postimage objects are reachable, validation passes;
missing/wrong source/postimage anchors still reject. Preserve original forgery,
byte/mode/hidden-file/consumer-scope negative obligations.

Run affected make docs test, artifact tests and actual complete17 integration
obligations using the pinned environment. A new cold source fetch of the coherent
committed repair must pass without extra refs/alternates/hardlinks. Inspect all
remaining current executable historical Git dependencies for the same reachability
class; do not silently broaden the source repair if another issue appears.
Preserve exact commands/environment/logs/failure and postimage correspondence.
A distinct final-diff review and actual full protected PRCI are required before
normal merge. Actual full CI on corrected main is required before A02 can be
accepted or S03 implementation admitted. No old branch reset/admin bypass/retry
of the deterministic failed run, and no task/release/hardware closure here.
