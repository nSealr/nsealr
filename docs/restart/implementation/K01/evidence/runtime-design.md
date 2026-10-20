# K01 implementation and remaining device limits

This implements the admitted portable engine, on actual T01 main7f. The new
`sign_approved` API requires an explicit synchronous auxiliary source and fresh
local clock callback. Existing serial/QR protocol paths still call the disabled
`attempt_sign` path; no readiness field, environment selector, fixture provider,
production RNG, network workflow or user-key output route was enabled.

The first attempt changes Approved to Spent before calling the clock, checking
correlation/context, or collecting auxiliary bytes. After validation it marks
Executing. It obtains exactly32 bytes once, signs the raw32-byte event ID and
stages complete signed JSON privately. The completion path obtains a fresh clock,
rechecks immutable review/binding/identity/epochs, and verifies the raw signature
under the selected full public key before exposing any bytes. Staging before the
final verification makes that final clock/context check occur after serialization;
unverified staging is never caller-visible. Every returned error wipes the whole
caller slice and requires a new request/review. The operation has no cached result
or retry service. Serialized `&mut` ownership orders cancellation and execution;
a device still has to qualify its interrupt/cooperative cancellation and provider
wait/recovery behavior. No asynchronous cancellation responsiveness is inferred.

| Data | Owner, lifetime and cleanup | Limit or missing proof |
| --- | --- | --- |
| Original scalar | One opaque `SecretKey` retained by the session; input is consumed/wiped, lock/reset/replacement/Drop wipe the current location | Original1/3/n-3 representations are actual private test witnesses; no new secret getter/recovery UI |
| Backend scalar | One scoped `SigningKey` at selection, then one per attempted signing backend call, borrowing the original only inside core | k256 normalizes odd-Y only in this temporary; its Drop clears its owned scalar; compiler moves/other copies are not universally erased |
| Public identity | Cached32-byte x-only key, checked against each scoped backend derivation | Public metadata is not custody or approval authority |
| Auxiliary destination | `Zeroizing<[u8;32]>`; full destination cleared before collection, on every failed/short/oversized report, and on scope exit | Exactly32 is mandatory; no fallback/retry. Provider must cease all writes before returning. DMA, quiescence, terminal recovery, quality and maximum wait remain device obligations |
| Nonce/scalar scratch | Existing pinned k256 `sign_raw` and arithmetic temporaries only | S02 source findings on `t`, `rand`, `NonZeroScalar`, moves/registers remain unresolved for real-key/device admission; no vendor patch or compiler-proof wipe claim |
| Hash state | Existing sha2 zeroize feature and drop chain; event IDs are public | Exact selected source/feature hashes remain pinned in S02/source-inputs; device spill/debug/crash exposure remains unqualified |
| Pending event/review | One owned bounded event arena, private state and commitments; pages regenerated, never collected in the session | Original Pending<=8192/session<=16384 compile assertions remain; hard parse/canonical/page caps unchanged |
| Profile metadata | Nonrecursive stack8, nodes128, members/array entries64; decoded strings and previous-key comparison scratch are local | Root and each child value count for depth; numeric token spelling is preserved. Actual stack/latency remains a device gate |
| Repost original | Borrowed spans/cursors over parent content; one field scratch, public headers only | No second full event arena or retained page copy; shape/ID/raw signature checked once at intake; rendering does not repeat key conversion/verification |
| Completed output | One private9216-byte staging buffer plus caller-owned destination; only complete valid extent is copied after final checks | No retained queue/cache; caller output capacity and simultaneous stack buffers must be budgeted by each adapter. No target peak-RAM/stack or bootable claim |

The engine clock/provider and local review traits are trusted-image interfaces,
not hostile-application isolation. Their concrete implementation and actual
physical display/input binding are external admission obligations. Missing time,
rollback, deadline, provider failure, correlation/context mismatch, bad backend
output and late completion all fail closed; successful public-fixture runs prove
none of those device properties.

The shared metadata/repost visitor and critical clock/provider boundaries use
borrowed trait objects, without allocation, so callbacks share one bounded
implementation rather than duplicate a parser/signing body per caller. The
algorithm/backend/features/dependencies remain unchanged. The original20 S03
families remain, with the five accepted deliberate owner/catalog/engine
extensions. Original8 and new13 mathematical controls remain separate.

`semantic-matrix-observed.json` distinguishes35 complete local simulated reviews
with exact original content/tag-field and role assertions from35 exact-layer
zero-effect failures. This adds execution obligations to the immutable70-case
admission-only first RED; it does not relabel its historical matches. Nested
metadata types, all original repost fields/tags, address remainder colons, final
reaction target and effective relay roles have additional actual assertions.
