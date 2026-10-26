# C01 account key pin: bounded host correction

Input: main de388c9548bc04cdb44ea8ccd2197b2ab29befab.
Author: /root/s3_native_finish; distinct reviewer: /root.
Writable product scope: packages/client/src/service.ts and service.test.ts.
Delivery evidence lives here; no C01 criterion, plan state, hardware readiness,
API/schema, core, S3 image or host-custody change is claimed.

The read-only audit is preserved at activeRoot/intake/client-account-binding-audit.json,
SHA256 d3a691510b73b419f7646e2b147562f4a2d121a8aa66067b36c01f956264a284.
Root authorized this correction after reading its complete public-fixture
counterexample. S3 delivery a1e9052a remains immutable in its own worktree.

The standard service selects the account key and rejects a valid signature from
a different account. Generic raw transports and verify_signer_response do not
select accounts; this change does not invent a pin for those interfaces.

The concrete defect is that the dispatcher receives a mutable route copy, while
the final sync and async response verification reads expected public_key from
that same copy. The currentness guard protects the original account/snapshot/
request, but does not make the copy a private source of truth. A callback can
change, replace or remove the copy's key and return an otherwise valid public
fixture response under another identity.

Retain the original selected public key in private PreparedSignerDispatch state
before any callback. Both final verification paths use only that private pin;
the dispatcher may retain its separate mutable copy. No Object.freeze-based
substitute, identity key custody, crypto algorithm or public API change is used.

Acceptance is finite:
1. Add regressions first, using the existing signed kind-1 fixture B unchanged
   and valid public account key A (secp256k1 scalar1's published generator key).
   Run sync/async cases for changed key, replaced route and removed key.
   Old code must fail all six expected-rejection cases for the identified reason.
   Matching-key and unchanged wrong-key controls must still pass.
2. Apply the private pin, then run focused service/profile/browser/driver checks
   covering positive routing, correlation and currentness/account mutation.
3. Build/typecheck the actual local workspace, verify workspace symlinks resolve
   inside this checkout and not to S3's earlier dist, and run the graph validator.
   Reuse the installed Node/pnpm/shared content-addressed cache and recorder.
   Do not run new USB/entropy/real-key probes, hosted CI, push or merge.
4. Deliver a clean source-bound candidate with RED/GREEN command/results,
   source/tool identities, limitations and distinct root review pending.

A dispatcher is same-process TCB code. The stock serial driver does not perform
the demonstrated mutation; this is an internal account-binding invariant repair,
not a claim that hostile USB bytes currently modify JavaScript route metadata.
The private pin does not authenticate a physical device or qualify all other
possible malicious callback mutations.
