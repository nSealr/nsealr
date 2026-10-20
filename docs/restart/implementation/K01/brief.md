# K01 — portable signing engine preparation

Author `/root/b01_final_review`, 20 October 2026; distinct reviewer `/root`.
Input is actual S03 main `dbad656997ad8cf9024ca1489291f5f1d4d3094a`
(tree `bd0fab419ea9be3e633645a4cc195392c1fe5832`). This proposal changes only
`docs/restart/implementation/K01/`. It neither starts implementation nor closes
K01. The six unchanged criteria in the [sole graph](../../../../plan/work-items.json)
govern acceptance; [acceptance-plan.json](acceptance-plan.json) maps them.

S02 selected the backend; S03 supplied the strict parser and consuming owner.
The source review `23d76b2c15d8dd41627f58c7b2018e06d40e821c` accepted
`c358229777d2582964a4f326ce8d15709841a395`, and delivery review
`0a65f077a73d2f157d981dffb00672c059402478` accepted its separate envelope.
Actual adopted main, rather than either historical review alone, is the input
here. Its captured push CI `39428661633`, verify `118647617141`, completed
successfully. [Source bindings](source-inputs.json) preserve these distinct roles.

T01 `cb39bb026d4008b7f3d7abf358b604c79e3b699d` has specification review
`ec97ed294529a9947ee432a0878a99109448012c`; it is being implemented and is not
an adopted API input. **No K01 runtime edit begins until T01 is actually adopted,
its required main gates pass, the affected API/source delta is reconciled once,
and the coordinator admits this scope.** Record that actual tuple and any changed
expectation before affected edits. Do not overwrite a newer graph or re-label a
specification review as implementation acceptance. Routine development thereafter
does not require a new administrative stage for each edit.

## Result and scope

Deliver one bounded, allocation-free engine for local public-key disclosure and
the seven P01 public kinds: 0, 1, 3, 5, 6, 7, 10002. It owns the validated
template, actual identity, full inspection, consuming consent and a verified
public result. [Catalog](catalog.md) fixes the semantic/URI/reference decisions
delegated by P01 before code. Unsupported or uninspectable input rejects; no
generic sign-bytes, unchecked ciphertext or preview-to-authority conversion exists.

The future runtime edit set is the core's `authorization.rs` and its private
tests, `event.rs` and its tests, `review/event.rs`, `lib.rs`, and a narrow private
signing adapter/test module if needed. A necessary crate-private intake change
in `nip19.rs` must preserve the existing opaque owner and codec contract.
Update the corresponding host replay/test consumer only where the actual T01
API requires it; keep the separate host workspace. Scoped K01 tests, independent
data and a link-only probe belong here. Existing S03 code is extended rather than
kept as a second signing engine. Any additional runtime path requires a concrete
scope correction reviewed against the adopted source.

No Board SDK, SE driver, persistence, backup UI, device transport enablement,
client discovery, policy automation or release is added. Existing serial/QR
diagnostics stay unable to authorize or emit a production signature. An engine
result does not change T01 capability/verification evidence to "ready". C02 owns
NIP-44 and the connected 10050/22242/17/59 workflows; 13/14/16/17/27235 and other
noncatalog kinds remain unsupported at this public entry. K01 does not add ECDH,
host grants, NIP-04 fallback or pretend that a signed event has been published.

This milestone signs with a locally supplied valid scalar. Native creation and
backup/recovery user journeys still need D02/Q01 and their device admission;
K01 does not claim all of PROD-02/03 complete. Preserve S02's qualified fallible
generation source, finite rejection of zero/out-of-range scalars and no
modulo-order reduction. The legacy deterministic `generate_*` conversions are
not RNGs. No identity-generation UI or new sampler is added by this scope.

The root/host locks, vendor union, toolchain, source replacement and all existing
fixtures/checkers/gates are inputs. No dependency change is expected. Preserve
the frozen 1,508-file index, all P01 contracts and graph fields. New expectations
are scoped K01 evidence, not silent edits to T01's exact artifact baseline.

## Backend and secret owner

Use the already present **k256 0.14.0**, defaults off, `schnorr` only;
**sha2 0.11.0** with existing `zeroize`, and **zeroize 1.9.1** defaults off.
Do not enable `std`, RNG/default features, ECDH or another backend. S02's
independent raw BIP340 tests and allocator-free final links support this choice.
The studied secp256k1 0.33.1 / sys 0.14.1 lowmemory alternative remains comparative
evidence, not a new port: its RISC-V C/Rust ABI failure and explicit
`-mabi=ilp32f -march=rv32imafc` correction remain historical. Convenience is not
proof of target timing, side-channel resistance or scratch erasure.

The one long-lived session secret must be the **original valid nsec scalar**,
consumed as S02's non-Clone/non-Copy opaque `SecretKey`. Cache only its public
identity. k256 normalizes odd-Y `d` to `n-d`; deriving a backup from its
`SigningKey` loses the original import. Do not normalize persistent/native
recovery bytes or reconstruct the original from that backend value.

Construct one scoped backend signing key at identity derivation and once per
authorized signing attempt, borrowing the original only inside the core.
Drop that temporary before returning; do not retain both original and normalized
secret owners, recreate keys per page, serialize them through host adapters or
offer a public raw-secret callback/getter. Document this necessary conversion
copy, the original owner, auxiliary bytes, hash state, nonce/scalar intermediates,
failure cleanup and actual lifetime. Lock/reset/replacement/Drop clear the current
owned secret and cancel old work; scalar 3 and n-3 retain different original
nsec despite the same x-only identity. A local test can use existing encoding
internally to prove this. No normal protocol export or new recovery UI is added;
D02/Q01 own later explicit local recovery flows.

S02's scratch warning is still open: vendored `sign_raw` has secret-derived
`t`, `rand` and `NonZeroScalar` temporaries without a universal Drop-wipe
guarantee. A wrapper cannot wipe inaccessible backend memory. K01 must give a
bounded source-derived copy/scratch inventory and a reviewed disposition, not a
claim of compiler-proof erasure. If an exact required secret-memory guarantee
needs upstream/target mitigation, record that missing property and keep real-key
admission blocked until it is proved. Do not silently change the cryptographic
algorithm, patch vendor code, switch libraries or claim public fixtures solve it.
Each device still qualifies internal-memory placement, DMA/debug/crash exposure,
compiler moves, timing and reset behavior on its real binary.

## One-use execution, entropy and output

1. Accept a strictly parsed, owned template under local finite bounds. Select the
   actual full public key, canonicalize inside the owner, preflight all semantic
   and complete inspection work, and bind the review/catalog revision and all
   limits/epochs/deadline. Account, policy, configuration and lifecycle changes
   invalidate pending authority. Host metadata, copied transcripts, diagnostic
   decisions and supported-capability fields cannot construct it.
2. The **first attempt burns Approved to Spent before any fresh clock callback,
   request/context check, entropy request or backend call**. A wrong ID, missing
   provider, display error, timeout or failure cannot preserve retry authority.
   Revalidate context after this point. Trusted monotonic time is independent of
   the event's host-supplied timestamp; clock absence/rollback/overflow fails.
3. Request exactly 32 BIP340 auxiliary bytes from an explicitly supplied fallible
   synchronous provider into an owned zeroizing buffer, after valid consent.
   The provider reports the successful written length; only exactly 32 is
   success. A short/oversized reported success is a provider failure, not a
   successful partially initialized value. Any unavailable, partial,
   interrupted, health/stuck-source or provider failure wipes the **whole**
   destination, produces no result and needs fresh review. A dishonest provider
   can still lie about its count/health; source qualification is not inferred
   from this check. No cached/zero/time/
   SDK-stub fallback or retry loop is allowed. A backend failure is also terminal
   for this consent; no implicit nonce retry policy is introduced.
4. The provider must cease all writes before returning. An asynchronous/DMA
   adapter must quiesce or perform its documented terminal recovery before the
   buffer can be wiped/reused. If it cannot, quarantine the owned storage and
   fail the device session; do not claim that an earlier CPU wipe was durable.
   The core supplies no production RNG. Per-profile maximum wait/cancel/reset,
   actual invocation and source-to-binary provenance remain device gates.
5. Sign the exact **32-byte NIP-01 event ID** with `sign_raw`, not the high-level
   hashing `Signer` API. Independently call `verify_raw` on that ID and the
   selected full public key in release builds; do not rely on backend debug
   assertions. Reject wrong-message/key/malformed output without exposure.
6. Serialize the immutable verified event into one bounded public completed
   result, with the selected pubkey/id/signature and exact signed values. Check
   a **fresh completion clock** and unchanged operation/binding/identity/epochs
   before exposing it. Cancellation or late completion discards it, though a
   started computation cannot be undone. No cached result/retransmission service
   is introduced: a second attempt requires a new request and local review.

Use typed failures without secret values; caller-visible failure returns no
signature or partial result. A public completed buffer may be at most 9,216 bytes,
separate from the retained session and checked before writing; it is not another
queue. The exact adopted T01 response/correlation wrapper is reconciled once.
Fixture auxiliary providers and signing hooks are test/probe-only, with public
keys; no feature, environment variable, successful boolean or host message
selects them in a production image. An application-supplied provider is still a
trusted-image obligation, not proof of healthy hardware entropy.

## Bounded implementation and evidence

Retain the current conformance ceilings: input/text 4,096; content 2,048;
32 tags; eight fields/tag; 256 bytes/field; canonical 8,192; 1,024 review pages.
Keep the stricter transport/profile limits from actual adopted T01. Parsing and
inspection use fixed arenas/spans/cursors and bounded work; no generic heap DOM,
unbounded recursion, saved page collection or duplicate canonical buffer.
Metadata/repost limits are in the catalog. Retained Pending remains <=8 KiB and
session <=16 KiB; a completed public result is separately accounted. Any inability
to meet these ceilings is a reported design failure, not permission to widen
fixtures. Static layout/link evidence is not stack/peak RAM or latency proof.

The first embedded target stays **riscv32imafc-unknown-none-elf**, Rust 1.95.0.
Host tests and an exercised no-allocator final ELF must call the actual K01
intake/review/attempt/sign/verify/output path using public fixtures, not merely
link the old isolated crypto spike or compile an unused rlib. Inspect feature
closure, map/sections, undefined/weak symbols and `readelf`/`nm -u`/`size -A`;
prove a required missing provider fails rather than silently selecting a stub.
This is a link-only probe without startup, a board memory map or qualified
entropy; do not flash it or call it a bootable image. No new hardware/target is
needed for this common milestone.

Before affected runtime edits, preserve the independent semantic decisions and
new expected canonical/signature data in the acceptance plan. Existing eight S03
vectors/oracles stay exact independent controls. Add a separate data-only test
projection for used K01 vectors if needed, never a second normative fixture
inventory. Develop focused failures first, keep real failures, and run the stable
full required gates once coherent. Distinct exact final source review, normal
protected integration and actual resulting-main CI remain required; their future
success is not claimed here. Actual UI, provider, target stack/RAM/latency,
recovery and physical isolation remain each profile's release gates.

## Correction from distinct specification review

Review `e598edab952b6e17df9f1286ff28c760cd0fac37` found K01-SPEC-01:
the proposed unchanged S03 `oracle.py --check` command cannot check this new
fixture set. Its parser-negative substitutions assume the first event is kind 1,
time 0 and empty content; K01's first kind-0 input leaves those mutations
unchanged. The reproduced `accepted invalid input` failure is a checking-plan
defect, not a product result. The original review, reproducer and unmodified
failure are bound by immutable URLs/hashes in `preparation-checks.json`.

Keep the original S03 oracle, eight fixtures and their separate check command
unchanged. Do not reorder K01 vectors to evade the defect. After actual T01
adoption and runtime admission, add only the scoped offline test checker
`K01/check_observed.py` described in the acceptance plan. It reuses the pinned
`template`, `canonical` and hash-checked `reference` primitives, not S03's
sample-specific `check` or `generate`. It consumes the explicit negative inputs
and independent expectations, with strict actual-output/identity/rejection
records and all original cryptographic/adversarial obligations. This admits a
necessary narrow test helper in the existing future scope, not another engine,
registry or an already passing checker. Mathematical inputs and their order are
unchanged; the correction awaits distinct delta review.
