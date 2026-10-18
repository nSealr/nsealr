# Secret flow after the S02 ownership change

This inventory describes portable source, not target memory measurements. All
arrays are bounded inline storage; there is no core allocator. Device code owns
stack/session placement in qualified internal RAM and exclusion from external
RAM, DMA, swap, crash dumps and diagnostics. Moves/registers/compiler temporaries,
panic abort and power loss prevent a blanket physical-erasure claim.

| Boundary | Owned values / intentional copies | Cleanup and visibility |
| --- | --- | --- |
| Local nsec input | Caller `&str`; Bech32 word array; converted byte array; 32-byte scalar scratch; opaque `SecretKey` | All internal arrays use `Zeroizing` or scalar Drop. Mutable scalar intake clears input with zeroize on success/failure. Caller must clear text/camera/input copies. Scalar has fixed redacted Debug and no Clone/Copy/raw public borrow. |
| Mnemonic / SeedQR input | Caller text/entropy; normalized token; decoded word indexes; checksum entropy/digest; four-digit group | Owned arrays/drop guards wipe on exit. `WordIndexes` is opaque, redacted and non-cloneable. Count is public metadata. Encoded input and scalar loop/register temporaries remain caller/compiler boundaries. |
| Pending source / keyring | Source constructors move from a temporary keyring; index insertion copies into bounded session slots then drops its consumed decoder owner | `add_nsec`, `add_bip39_seed`, `add_source` consume. `take_last` transfers. Import consumes pending ownership even on rejection/error. Clear and Drop wipe current slot fields; no post-drop reads. Eight-slot legacy capacity remains, not a claim of a multi-identity product. |
| Fingerprint/checksum | Internal scalar/index borrow; bounded concatenation buffer; maintained SHA256 state | Scratch buffer and SHA256 core/block-buffer Drop are zeroizing. Returned fingerprint is public correlation metadata, not proof of signer identity. SHA adapter exposes no Debug/Clone/state serialization. |
| Backup construction | Intentional mnemonic, SeedQR digits, entropy hex or nsec encodings in one bounded payload; scoped encoding scratch | Payload exists as a drop-wiped owner before fields are filled, so later errors also wipe populated fields. Raw builder is crate-private. Fixed redacted Debug; no Clone; explicit `reveal_*` borrowed methods. |
| Backup flow/IO | Non-IO flow transfers one payload to the local caller; IO borrows once during emission then drops it | IO result contains no retained payload. Rejection/early approval/errors do not emit. Adapter is trusted and owns clearing its framebuffer/QR/render copies. Legacy flow approval is revalidated by S03; API opacity is not physical authority. |
| Errors/reviews/logging | Typed errors contain no secret payload; source/ring/index/payload/result Debug are fixed redacted strings | Public-fixture regression asserts full output. Local labels and fingerprints are ordinary review metadata; callers must not put a secret into a label. The simulator's backup mismatch diagnostic no longer echoes compared values. |
| Crypto candidates | Historical isolated probe contains published test keys and raw arrays | Probe is not a product custody API. Future signing/ECDH integration must inventory all key, nonce, auxiliary randomness, shared-x, HKDF and plaintext buffers and backend internals. |

Explicit local conversion/export APIs (`encode_nsec`, `decode_nsec_hex`, BIP39
mnemonic/entropy output) use caller-owned output buffers. These are entry/backup
codec boundaries, not accessors into the stored source: an external consumer
cannot obtain its scalar/index fields. Output buffers can contain secret data
even after a partial encoding error and must be guarded/wiped by their local
owner. Public fixture replay intentionally compares these encodings; no real
secret is used in the tests or checked-in evidence.

`zeroize 1.9.1` is used without allocation/default features. It narrows current
memory lifetime but cannot remove all copies from Rust moves or hardware. The
private `SecretKey::empty` state is used only for vacant/wiped slots; public
scalar intake rejects it. Both seed insertion paths now verify count, index range
and BIP39 checksum before retaining the source. Existing invalid-backup tests use
explicit crate-private corruption to exercise defensive error handling.
