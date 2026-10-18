# Entropy provider contract for device integration

S02-07, version 1. This is an interface and qualification requirement. This core
has **no production entropy provider**, no `getrandom` dependency, no C entropy
symbol and no runtime provider selection. `generate_*_session_source` are legacy
names for deterministic conversion of caller-owned bytes/scalars; they do not
acquire randomness. `SecretKey::take_from` validates a scalar and clears the
mutable input, including on failure. It cannot judge entropy quality.

The next generation/signing adapter must implement a fallible all-or-error fill
operation. Conceptual contract, not a presently exported API:

```rust
fn fill_secret_random(&mut self, destination: &mut [u8]) -> Result<(), EntropyFailure>;
```

The caller owns a fixed-size zeroizing destination and accepts it only on success.
The provider may have partially written on error: every error path wipes the whole
destination, produces no key/nonce/signature/ciphertext and ends the operation.
No previous bytes may be reused. `Unavailable`, `HealthFailure`, `Interrupted`,
`ProviderFailure` and `RejectionLimit` must remain distinguishable operationally
without logging random output. Retrying a user operation requires its own valid
authority; provider failure cannot return an apparently successful response.

The device contract pins maximum fill length, timeout, cancellation and retry
limits. Identity generation samples a full 32-byte scalar, rejects zero and
values at or above secp256k1 order, and stops after a profile-defined finite
number of rejected draws. It never reduces an arbitrary random integer modulo
the order. A syntactically valid repeated scalar does not prove a healthy source.

BIP340 auxiliary randomness and NIP44 nonces need separate requests/purposes and
failure handling. BIP340's ability to accept fixed auxiliary data at the algorithm
level does not authorize silently replacing failed device randomness with zeros.
Public-vector test providers are compiled only into tests/probes. No application
flag/environment variable may switch a production binary to fixture data.

An explicitly selected OS CSPRNG or DRBG is permitted. Its initial seed source,
readiness, reseed/recovery behavior and failure semantics must be documented for
the exact profile. Falling back from a failed hardware source to a clock, MAC
address, unseeded generator, cached bytes or an unqualified SDK stub is forbidden.
Passing statistical randomness tests cannot establish source quality.

## Source-to-device proof, required separately for every profile

1. Pin board/MCU/SDK/OS revisions, configuration and authoritative entropy/errata
   documentation. Record startup preconditions (including RF/clock dependencies),
   health-test ownership, blocking behavior, concurrency and reset state.
2. Trace the actual application call through Rust traits, SDK wrappers, C/FFI,
   weak aliases, static archives, link order, LTO and dynamic/runtime dispatch.
   Name every possible fallback. Explicitly inspect weak default RNG symbols and
   target-specific build scripts; a dependency name or trait bound is insufficient.
3. Bind the final ELF/image hash to features, map, undefined/weak symbols and
   relevant disassembly. Link an intentionally missing provider to establish that
   no silent stub satisfies it. If a platform uses runtime dispatch, record the
   loaded provider identity and configuration rather than treating symbol presence
   as invocation proof.
4. On the identified device and exact binary, instrument the actual provider
   invocation and correlate a requested operation with provider calls, without
   capturing real secret bytes. Use disposable public-test identities only.
5. Inject unavailable, short/partial, interrupted, stuck/repeated and explicit
   health-failure cases at appropriate layers. Verify zero crypto output, cleared
   retained pending state, no weaker fallback, bounded waiting/retry and recovery
   only under the profile's documented rule. Distinguish fault injection from
   proof that the real hardware detects every stuck-source mode.
6. Record operator, equipment, conditions, binary hash, raw traces and limitations
   of instrumentation. Repeat on each release binary/assembly when relevant
   provider or build configuration changes.

Owners: V01/V02/V03 for connected device integrations; Q02/Q03 and their exact
Pi/P4 qualification gates for offline images; B02/B03 for generic Board SDK and
release. An OS-backed Pi and a bare-metal MCU need different proof. Neither may
borrow another profile's provider/health evidence. S02 does not claim actual
provider invocation, hardware randomness, physical erasure or side-channel proof.
