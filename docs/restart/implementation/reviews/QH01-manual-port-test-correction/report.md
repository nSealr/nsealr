# Retention release test correction: affected review

**PASS_manual_QR_retention_test_correction_only** on exact test source
`ac8b14e54a6c4e028902d8ac3301bb6a1392c5fd`, no open findings.

The previous retention fixture used retained_bytes1. The real client reparses
limits and rejects that manifest before entering the dispatcher, so that test
did not prove factory release. Original actual RED now preserves zero actual
dispatch entries versus one expected. This is a test defect, without a runtime
change. The previous code review bfc6 remains valid for byte-identical runtime,
package and lock inputs; its observed58PASS is historical and not relabelled.

Root read the complete test-only delta and real client/manifest source path.
The corrected independent fixture fits the manifest but is one byte short of
the adapter's logical payload reservation. Explicit entry counts1then2 prove
the first rejection reaches the adapter and the next request recovers; opens
remain zero then one. Existing limits and acceptance criteria are unchanged.

Root independently ran only the two affected cases:2PASS,56unaffected skipped.
[Raw command/output](runtime/command.json) preserves source and environment.
No rebuild/reinstall was needed with identical package/runtime/build inputs.
Four exact old snapshots and the actual RED raw pair are verified. This supplies
the missing retention-release proof without repeating unchanged code reviews
or the full suite. All five QH01 criteria and physical gates remain incomplete.
Final author proof packaging, metadata review and protected PR/main checks
remain separate required gates.
