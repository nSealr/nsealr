# S01 integration review — changes requested

Reviewer: `/root/independent_bridge_review`; author: `/root/baseline_execution`.
Exact candidate: `ae01a32e8e0aab335115bbd17caad27f29122709`.
Accepted brief SHA256: `009902d3534adfe3287eea01f5dab17af65ad9f9be143a9ef90302905e4e233f`.

The committed fixture bytes and recorded integration results check out, but the
provenance gate does not enforce two explicit requirements of the accepted brief.
This is a **changes_requested** verdict for integration acceptance. It does not
reopen the previously passed Bridge/specs product reviews or assert a runtime
signing exploit. No product files, author worktrees, canonical lab checkout, task
graph, or private source history were changed by this review.

## I01 — deleting SOURCE disables complete-snapshot validation

The selected lab checker calls `validate_provenance()` only when its ordinary
file iterator encounters `SOURCE.json` (patched lines 165–169). Deleting that
file disables the complete inventory and upstream HEAD checks. Legacy required
globs still run, but they do not require the complete core vector tree.

The independent probe uses the exact pinned lab plus both declared overlays,
the actual pinned specs Git HEAD, all five repositories' actual snapshots, and
the default repository list and required globs. The clean control passes 546
comparisons. Removing just core `SOURCE.json` still passes 546. Removing that
file **and** `vectors/nip46-relay-steps/sign-event-response-step.json` still
passes 545. Keeping SOURCE while removing that vector correctly fails.

This is an integration-gate conformance blocker: a partial snapshot can obtain a
passing first integration step despite the brief requiring complete inventory
and provenance validation. Require the complete core snapshot's metadata
independently of encountering the metadata in an iterator. Preserve the
intentional partial-snapshot contracts of other sibling repositories.

## I02 — a dotfile's updated local hash bypasses upstream byte comparison

`iter_snapshot_files()` excludes names starting with `.` (patched line 121).
The provenance loop compares every snapshot hash to its local manifest but does
not compare those hashes/bytes to upstream (lines 130–138). Changing the tracked
`vectors/.gitkeep` to `reviewer tamper\n` and updating its SOURCE hash therefore
passes 546 comparisons. Removing the dotfile, even with the manifest edited,
correctly fails the upstream inventory check.

The current dotfile is a placeholder; this finding establishes no protocol or
cryptographic exploit. It is nevertheless an explicit acceptance mismatch:
the brief includes `.gitkeep`, preserves exact upstream bytes, and permits only
SOURCE to be excluded from upstream comparison. Compare every inventoried vector
to upstream, including dotfiles. R00's historical patch/evidence should remain
unchanged; a separately reviewed narrow followup overlay can enforce this.

## Independent positive evidence

`audit.py` independently verified all 75 author artifact hashes and 46
command-log hashes; all 221 upstream vector bytes and SOURCE inventory entries;
all 22 raw migration paths/hashes; the CC0 license hash; both ordered patches'
before/after hashes; and the unchanged original R00 overlay. Thus neither
finding implies the submitted snapshot is already incomplete or corrupt.

Twenty core/native/dependency/CI top-level objects equal core input
`9194e292aa8a3176874cc9bf5814cefc26b6fe1a`. All 21 final non-doc top-level
objects equal tested fixture candidate `41f5d2d193e4a00227737e1f8d71ce57e39ea889`.
Companion main `678796900e462f5504e47fe934e2e5f23d85824f` has the exact reviewed
delivery tree; all 82 changes since reviewed product `9e023ccef300ddeb738c377fe68b130a94123477`
are S01 docs. Specs main `45f8b6ff1123f3f55be4ce457fd1008e91043cc2` differs from
reviewed product `b0022f3dd8b1c2b1bb553c0e5f84e81fb312396a` only in two docs.

The eight recorded full CI commands and uninterrupted integration command have
zero exit codes and sequential timestamps. The raw integration log has all 20
recipe steps in order, 546 fixture comparisons, the three actual v1 negative
invocation markers, and successful Pi/card simulation tail assertions. The
unchanged CLI rejection function still requires nonzero exit, expected error,
and no output file. The new inventory guard correctly rejects empty/partial,
substituted-content, and duplicate selected lists in the independent probe.
The author's original 0/3 v1 discovery failure remains in its original record.

The independent probe has 20 cases: 17 expected controls pass and the three
unexpected acceptances above fail. It uses fresh exact-object exports in the
reviewer's ignored scratch directory and a fresh shallow specs checkout; only
the previously pinned Python 3.12.15 executable is reused read-only. It does
not use the author's working checkouts, dependency caches or generated output.
No third-party Python packages are needed. The probe exits 1; the independent
evidence/source audit exits 0. Commands and hashes are in `review-result.json`.

## Scope and next acceptance

The eight full suites were inspected and hash-checked, not independently rerun.
The author correctly labels its execution warm-runtime/cache reuse with fresh
tracked sources, not a cold-install replay. Source-state records declare only
the four lab overlay files; hardware/website compileall cache directories are
untracked, disclosed artifacts. The patched lab code does not suppress CLI
stderr or substitute simulated output for those assertions.

This review makes no physical device, installed-browser, external-client,
production-key, provisioning or entropy claim. Prior Bridge local-relay evidence
is a separate reviewed gate. GitHub checks on this exact draft head are green
as captured in `github-pr.json`; they do not repair these provenance bypasses.

After correction, preserve these failed controls, rerun them unchanged against
the exact new overlay, and revalidate the affected complete integration gate.
The branch is behind current main. A later rebase/merge onto current E01/A01
work requires fresh source correspondence and appropriate affected checks;
this review does not approve that future candidate or close S01.
