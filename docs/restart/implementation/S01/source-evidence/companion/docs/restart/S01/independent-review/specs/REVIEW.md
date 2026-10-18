# Specs v1 migration review — pass for the pinned product

Reviewer: `/root/independent_bridge_review`; author: `/root`. Final specs product: `b0022f3dd8b1c2b1bb553c0e5f84e81fb312396a`; evidence-only successor: `062f250268bfde76162b3820acbef33200e253fc`. Input specs: `8bb8cca71355bcf8d81a093bcee9f3fe6915b121`. Interoperability target: Bridge `9e023ccef300ddeb738c377fe68b130a94123477`.

**Verdict: pass for the bounded response-metadata v1 oracle, fixture migration and checkout validation prerequisite.** This is independent engineering review, not an external audit or a session/device authorization claim.

## Specification and implementation assessment

The initial brief `6e7b01e2ad98738c006a08226d6d09e2e02ee597` was independently accepted before implementation. Its refinements explicitly bind nested JSON to 1,024 UTF-8 bytes, 32 containers, duplicate/escaped-alias/trailing rejection and exact output types. The implementation separates the returned user key from the signed outer transport author, verifies the inner canonical ID/signature under its own author, and treats missing expected user as unbound. All-digit hexadecimal keys are recognized as metadata before JSON parsing. Auth, error, pong and relay results have no invented user identity; non-enabling flags remain false. The response dispatch and downstream auth-challenge consumer use v1, while unrelated v0 formats remain intentionally unchanged.

`strict_nip46_result_json` checks size before parsing, scans string escapes when counting depth, and uses duplicate-aware object construction. The strict comparator rejects bool/int substitution, missing/extra fields and changed array order while ignoring object member order. The neutral unsupported-result error matches companion's fixture expectation. No decryption or binding between the supplied plaintext and outer ciphertext is claimed by metadata evaluation.

The checkout-name prerequisite is adequate and implemented narrowly. The local repository's identity is pinned to `specs` instead of inferred from the checkout folder, restoring the CC0 marker and required-directory checks. The real CLI test runs from an arbitrary temporary directory, passes correct structure/license, rejects MIT, and rejects missing vectors. It changes neither the license nor a gate. The original failed gate output remains in author evidence.

## Independent finding and correction

Review of `a3b897bcffab86f4ec1c7d4bd89e5a7068f728db` found that the inherited outer-event check accepted a correctly signed boolean `created_at` because Python considers bool an int. The same independently generated event is rejected by TypeScript. This was a metadata shape-oracle mismatch, not a runtime signing authorization bypass.

The failed 26-case cross-language probe is preserved at `../final/specs-adversarial-before.{json,log}`. It isolated exactly that case; all 72 raw strict-JSON cases agreed. The author retained signed true/false red controls and corrected the predicate to require an actual Python int. The final independent corpus now passes without changing its expected outcomes. No fixture bytes changed for this correction.

## Executed evidence and provenance

- The independent probe generates public-scalar signatures and canonical event IDs without the oracle's `event_id` helper. All 26 metadata cases match independent expected acceptance and TypeScript output, including inner/outer signature/ID failures, boolean timestamps, expected-key shape/mismatch, user/transport separation and non-authorizing result types.
- All 72 strict-JSON cases pass across Python and TypeScript, including escaped duplicate names at every supported depth, surrogate-pair key aliases, exact/above UTF-8 limits, trailing input and nonfinite literals.
- The reviewer ran `make test lint audit docs` in an isolated `git archive` copy of the exact specs product: the verifier and all 92 tests passed. Pinned Python 3.12.15 and its installed secp256k1 dependency were read from the R00 runtime; bytecode writes were disabled. No root-author checkout was modified.
- The unchanged companion CLI was run with explicit `--specs` pointing to that exact snapshot. It verified all selected fixtures, including 10 relay steps and 107 invalid hardening vectors, without falling back to the vendored copy.
- All 22 migration entries were independently checked against both repository baselines and final products. The changed path sets agree exactly, all old/new hashes agree, deleted sender-mismatch fixtures are absent, and all surviving selected fixture bytes are identical between repositories. These are 22 change entries, including two removals and two additions, not 22 surviving files.
- The final author's `make ci` record is independently source/log-hash-verified and reports 92 passing tests. The evidence successor changes no product files. This author execution is distinguished from the reviewer commands above.

Command manifests and artifact hashes accompany this report. `harness-note.txt` records an initial reviewer archive-creation race, corrected by serializing archive creation before rerunning the affected commands; it was not a product failure. The legacy global verifier status text mentioning v0 does not select response-step v0: the inspected dispatch, migrated fixtures and executed CLI controls use response-step v1.

No repository merge or parent-task closure is performed. The coordinator still owns the eventual merged specs pin and core fixture SOURCE/provenance refresh. Changed source or fixture inputs invalidate affected evidence.
