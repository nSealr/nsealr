# Software and release evidence

Use the [task graph](../plan/work-items.json) for accepted results and the
[product requirements](product/README.md) for release criteria. This checklist
is a review aid; it makes no completion or device-qualification claim.

- Bind the exact source, licenses, public ancestry, dependency locks and tool
  versions. Keep excluded private histories and credentials outside public Git.
- Run the complete [product gates](testing.md), preserving failures and skips.
  Verify independent contract consumers and actual packed SDK consumers.
- Keep the two Rust workspaces separate, preserve coverage floors and reproduce
  device and host artifacts from independent clean builds.
- Preserve immutable historical evidence and the sole task graph. Declare
  substantive current-contract changes and obtain their own review.
- Verify production source boundaries, request-bound response checks, rejected
  host approval shortcuts and disabled unqualified signing paths.
- Qualify actual browser/relay/device behavior separately. Bind physical review,
  one-use authorization, key custody, provisioning, entropy, update/debug policy
  and recovery to concrete measurements before a profile can claim support.

The host OS and hosted runner are not immutable or OS-hermetic. Dependency audit
warnings and unavailable index coverage must remain visible in execution evidence.
