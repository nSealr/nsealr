# crypto-bigint yank remediation contract

Author /root/pi_runtime; distinct review/integration /root.
Base: PR53 source 220aa0d4e4e0f5f58b02ae66164661aaa48da988.
The yank is observed on current official registry data, after the original
0.7.6 remediation. Preserve earlier source/artifact/runtime records.

Use the minimum non-yanked compatible patch (candidate 0.7.9) with Rust1.95,
k2560.14.0 and elliptic-curve0.14.1 unchanged unless actual source/resolution
proves a further dependency mandatory. Authenticate the official archive against
the official sparse record and API SHA, inspect complete 0.7.6->0.7.9 runtime
diff, verify the advertised NonZero invariant change in upstream PR1373 and its
downstream uses. No yank-ignore, policy/threshold/toolchain/algorithm rewrite.

Writable code: root/desktop locks and one official vendored crypto-bigint subtree;
any actually necessary transitive update must be explicit, never hidden.
QR worker graph, manifests, application sources, audit policy, phase1-scope and
plan/work-items.json stay unchanged. Frozen Pi/P4/S3 trees/artifacts are inputs,
not writable destinations. Produce explicit lock deltas bound to the exact
frozen P4/S3 commits, and identify affected binaries/reviews separately from
unchanged camera/UI/QR-worker evidence.

Verify coherent graph and checksums, current unchanged deny gate, host core and
desktop vector tests, no_std RISC-V build, independent S03/K01 outputs and
C-ABI adapter tests as applicable. Inspect upstream regression tests and run
the relevant original library controls using existing tooling. No full make-ci
or hosted CI/push/PR. No Pi image rebuild, SD/USB/hardware operation or production
keys. Source/build results cannot qualify target timing or constant-time behavior
on every architecture. Deliver one commit sequence with proofs, exact limits,
original failures and the affected-artifact list for root's distinct review.
