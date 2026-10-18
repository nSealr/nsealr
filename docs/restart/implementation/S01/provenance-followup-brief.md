# S01 — Provenance follow-up addendum

Author: `/root/baseline_execution`. Distinct specification/final reviewers are
assigned by `/root`. Implementation awaits approval of this committed addendum.
It extends the accepted `integration-brief.md` without rewriting that brief or
its original artifact index. S01 remains open.

## Finding, inputs and authority

Independent review of `ae01a32e8e0aab335115bbd17caad27f29122709` preserved in
review commit `30ae87dd31c3c292b22f4758d4fad9fea63a7b37` found three provenance
bypasses: deleting core `SOURCE.json`; deleting that manifest and an otherwise
unrequired real vector; and modifying a tracked `.gitkeep` while forging its
manifest digest. The checker accepts all three because manifest validation is
conditional on encountering the file, and ordinary iteration skips dotfiles.
The independent probe SHA-256 is
`39bce90e92a473930768d7b92aa76b70c8163ad495ea8fbdd1e9976e65ab4caf`.
Its 17 passing controls, three bypasses, and the earlier 8-suite/20-step results
remain historical evidence; they do not establish corrected gate acceptance.

All repository/runtime pins in the original brief remain unchanged. Current
fixture source is specs `45f8b6ff1123f3f55be4ce457fd1008e91043cc2` and the tested
fixture candidate is `41f5d2d193e4a00227737e1f8d71ce57e39ea889`. Companion remains
`678796900e462f5504e47fe934e2e5f23d85824f`; lab remains
`3303ab17a28ed32419576627d5abb93db3999635`. No fixture or core product change is
expected. This is tooling integrity work within S01 integration acceptance.

## Bounded correction and active callers

Add one selected CC0 follow-up patch and provenance manifest under
`tools/baseline/overlays/`, changing only the isolated lab's
`scripts/check_fixture_snapshots.py` and `tests/test_fixture_snapshots.py`.
Preserve the original R00 patch and manifest byte-for-byte, including patch hash
`da2f2e821a6c484f22aaeeeb78fad42949c9870b6d54135de292bcde6c5e4bc8`.
Preserve the S01 metadata-v1 patch/manifest, whose patch hash is
`e6b4d86b553bdaa655a7850727d76268a1d7e29b04f8e2be0f95849c3f0a098c`.
Record source LICENSE digest, before/after hashes and ordered dependencies.

The S01 tuple applies original R00 provenance, metadata-v1, then this third
overlay. The third patch touches different files from metadata-v1 and must also
apply directly after the original R00 patch without needing metadata-v1.
`tools/baseline/bootstrap.py` is an active caller that currently applies only
the vulnerable original patch. Its actual CLI offers only destination,
`--mirrors` and `--core-only`; there is no configurable input-profile option.
Update active `tools/baseline/inputs.json` to the exact current specs and companion
commits above, changing no other repository/runtime pins. Extend the default
caller to apply and verify all three overlays in the S01 order, reading the
existing metadata-v1 patch/manifest at their current S01 paths without rewriting
or duplicating them. Retain the original overlay record and add distinct v1 and
follow-up records. A small shared application function may remove the
duplicate verification sequence; no optional disable switch or absence fallback
is permitted. Add meaningful boundary tests in `tools/baseline/test_bootstrap.py`
and update `tools/baseline/README.md` to explain the ordered correction and the
historical reproduction refs. Do not add a generic profile system or silently
follow repository main branches. `run.py` already verifies the complete recorded source diff;
it needs no change merely to support another declared patch.

This narrowly expands editable scope to those bootstrap, active inputs, README,
test and new overlay files, plus new S01 addendum/evidence files. Historical R00
input pins remain immutable at their existing evidence refs; original R00
patches/evidence and the original S01 75 indexed artifacts stay byte-identical.
Document the verified remote refs `evidence/r00-full-20261018` (`f853757a5080003036aacb797999410398816f16`)
and `evidence/r00-reviewed-20261018` (`303b4c9d9386147220abaf2cf754c5c47e458dff`)
for historical tooling, pins, inherited failures and observations. Their old
provenance limitation remains disclosed; new correction evidence is additive.
Canonical lab and other author trees remain read-only. A02 must independently
select/import the corrected tooling tuple before replacing these overlays.

## Observable contract

1. The default complete core consumer (`firmware` sibling in the lab layout)
   requires a regular readable `SOURCE.json` before ordinary fixture iteration.
   Missing or malformed metadata fails explicitly. Core cannot silently become
   a generic partial consumer by losing its manifest or using empty required
   globs. Other named consumers retain their existing partial snapshot/glob
   contract; any manifest they do supply is validated, not silently ignored.
2. Resolve the exact specs Git HEAD and its complete tracked `vectors/` file
   inventory. The nonempty inventory must equal the manifest keys, actual source
   file inventory and actual snapshot file inventory, including dotfiles.
   Missing, extra or unsupported nonregular vector entries reject. Compare each
   actual upstream and snapshot byte sequence, and require its SHA-256 to equal
   the recorded digest. Anchor upstream bytes to the committed Git object too,
   so changing both working copies and forging a digest cannot masquerade as
   the claimed commit. Repository and commit checks remain mandatory.
3. Only validated `SOURCE.json` is excluded as local provenance metadata.
   Ordinary real-fixture comparison remains active, including dotfiles; existing
   generic partial-consumer behavior and required-glob coverage remain tested.
   A change in reported comparison count must be explained by newly counted
   hidden files, never omitted vectors. No URL/signature/identity/CLI assertion
   changes belong to this repair.
4. Bootstrap verifies ordered patch digests, pinned lab commit, preimage and
   postimage hashes, recording all three overlays. Wrong source, modified patch or
   modified target must fail before the affected patch is applied. Public core
   CI continues to execute bootstrap boundary tests without private source.

## Evidence and acceptance

Before applying the repair, reproduce all three reviewer bypasses against the
existing two-overlay tuple in owned disposable data and save failing controls.
Add regression cases using real small Git repositories, not mocked Git HEADs:
missing manifest alone; missing manifest plus v1 vector; missing vector with
retained/forged inventory; hidden-file removal/tamper with recomputed digest;
extra ordinary/hidden files; changed ordinary bytes; incorrect digest, repository
or commit; and simultaneous source/snapshot byte tamper with a forged digest.
Include clean complete and partial-consumer controls. Repeat the independent
reviewer's exact mutation semantics after correction, including v1 discovery.

Exercise the actual bootstrap overlay helper with a fresh lab preimage and the
historical core/specs pair (core `9194e292aa8a3176874cc9bf5814cefc26b6fe1a`, specs
`8bb8cca71355bcf8d81a093bcee9f3fe6915b121`) using only R00 plus follow-up, proving
the correction is independent of metadata-v1. Do not force v1 into the old tuple.
Verify historical refs and their exact original inputs remain reachable. A
deliberately mismatched current-core/old-specs control must still reject, while
the active current default must succeed with its coherent pinned tuple.

For the current S01 tuple, preserve commands, environments, hashes, UTC times,
exit codes and source states in new evidence files. From the committed repair,
run the real public default bootstrap entry point into an absent owned directory:
`python3 tools/baseline/bootstrap.py ABSENT_DEST --mirrors /home/tux/nsealr`.
Mirrors provide only Git transport; do not inject caches or replace the default
pins/overlay path in this positive acceptance. Require successful fresh source
checkout, pinned installation, all three overlay records and runtime manifest.
This bounded new installation uses the same R00 runtime pins and does not rewrite
or retroactively upgrade historical cold-run evidence. Host/kernel/TLS/compiler
and authorized Git transport remain declared external inputs.

Use that freshly bootstrapped current tuple to run the complete affected
lab CI, explicit actual fixture parity and v1 discovery guards, bootstrap
boundary suite and one uninterrupted final `make integration` with all 20
steps. Run affected core CI for bootstrap changes. Reconcile unchanged product
objects to the prior eight-suite evidence instead of claiming a second run.
Earlier S01 runs reused runtime/cache inputs and remain labeled accordingly;
the new installation's actual isolation and executed gates are reported separately.
Retain live, interactive browser and physical hardware exclusions.

Commit repair separately from final result metadata; preserve old evidence
and supersede its acceptance conclusion in a new report. Push the exact
candidate, run actual CI and obtain renewed distinct final review. A bypass,
unexplained source difference, omitted recipe step or failed gate keeps S01
integration open. Root owns merge and task closure.
