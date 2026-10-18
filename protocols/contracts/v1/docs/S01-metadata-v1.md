# S01 metadata-v1 integration brief

Author: `/root`; input specs `8bb8cca71355bcf8d81a093bcee9f3fe6915b121`, companion source `d385ddb0c775a1e863e9db0ee9ae38fee5f19057` (fixture bytes already frozen at `22d04c988918bd5895b76666377bb843cba18760`). This is a bounded S01 consumer/oracle migration, not new runtime signer functionality. Independent specification review precedes implementation; final reviewer is `/root/independent_bridge_review`.

## Contract and source basis

NIP-46 at nostr-protocol/nips `37db639582d857e12468dcccd99b2c7f1d657da9` distinguishes transport and user identity. The inherited Python response oracle incorrectly requires the returned user key and signed-event author to equal the outer transport author, then verifies the user event with that transport key. The corrected metadata-v1 evaluator reports `result_pubkey` separately and an optional explicit expected-user match, while retaining outer signature, inner canonical ID/signature, URL, shape and non-enabling checks.

Metadata does not authenticate a user session or a forwarded decrypted payload. Its outer ciphertext placeholder fixtures are metadata/signature checks, not NIP-44 decryption. Real manager/relay behavior is independently tested in companion. No v0 response compatibility obligation is retained; other unrelated experimental formats remain unchanged in this bounded migration.

## Owned scope and behavior

Own `scripts/verify_specs.py` response-result/oracle and its direct dispatches, focused `tests/test_verify_specs.py` additions, the exact changed companion response-step fixtures and renamed expected-user negatives under `vectors/`, plus this brief/evidence. No new schema/repository split, unrelated policy/custody behavior, relaxed signature checks or wholesale fixture regeneration.

1. Mirror exact versioned fixture bytes and explicit file renames/removals from the pinned companion candidate. Record old/new hashes. Reconcile any other response-step consumer before claiming cross-repository acceptance.
2. Recognize a public-key result before attempting JSON decoding; do not mistake an all-digit hex-shaped string for a JSON number. Metadata shape acceptance is distinct from session curve/authentication validation.
3. Return user-result identity separately from transport author. Verify a signed inner event under its own author; independently compute ID and retain invalid-signature/id failures. If optional expected user is present, validate its shape and reject any user-bearing mismatch. Missing expected identity yields an unbound flag, never inferred equality.
4. Emit only response-step-v1 metadata with the exact field contract; auth/error/pong/relay-list results have no user-result identity. Preserve false non-enabling flags. Update invalid fixture dispatch and auth-challenge source consumption together.
5. Nested raw result JSON is capped at1024 UTF-8 bytes/depth32, rejects duplicate members including escaped aliases, trailing data and nonfinite constants, matching the companion host profile. Structural expected-output comparison preserves array order and exact JSON value types (including bool versus int); object member order is irrelevant. Tests cover behavior, not documentation text.

## Independent acceptance plan

Before correction, show the pinned baseline rejects a valid different user key and a valid inner event author different from transport. Use published fixture keys and signatures generated/verified by the Python crypto implementation, not the TypeScript evaluator. After correction test distinct identities, supplied expected-user mismatch, no expected identity (unbound), invalid inner signature, changed canonical event ID and invalid expected-key shape. Keep a valid same-key control and outer signature failure.

Run the complete specs verifier/unit suite under isolated pinned Python, then companion's unchanged fixture verifier selecting this specs checkout, and relevant affected cross-repository checks. A shared fixture snapshot must not silently override the tested sibling source. Save commands, versions, exit codes, source pins, hashes and exact candidate. Independent review must assess both the Python oracle and synchronized fixture bytes. No hardware, external client or S01 parent closure is claimed solely by this step.

## Checkout-name validation correction

The actual isolated `specs-s01` worktree exposed an inherited structure-checker
bug: `scripts/verify_repo.py` inferred repository identity from the directory
name, expected MIT instead of the actual CC0 license and silently omitted the
specs required-directory checks. The failed unmodified `make ci` output is
preserved in `docs/evidence/S01/specs-ci-baseline-failure.log`. Pin this
repository's identity to `specs`; do not change the license or weaken its marker.
A disposable renamed checkout must pass with the correct structure/license,
reject MIT and reject a missing vectors directory. This is a bounded prerequisite
to executing the same gates from author/reviewer worktrees.

Independent final review found a signed outer event with boolean `created_at`
passed the inherited Python integer check (`bool` subclasses `int`). Preserve
the reviewer reproduction and signed red controls; reject booleans explicitly
while retaining valid integer and signature controls. This restores the outer
shape check required by the response metadata contract.
