//! SHA-256 adapter over the pinned RustCrypto implementation.
//!
//! State may absorb secret import/checksum material. It is neither cloneable nor
//! formattable; the dependency's `zeroize` feature wipes its current core and
//! block buffer on drop. Moves/registers and caller input remain outside that
//! guarantee. No heap allocation is needed.

use sha2::Digest;

/// An incremental SHA-256 state with drop wiping enabled in the dependency.
pub struct Sha256(sha2::Sha256);

impl Sha256 {
    /// Creates a fresh hasher.
    #[must_use]
    pub fn new() -> Self {
        Self(sha2::Sha256::new())
    }

    /// Absorbs input into the running state.
    pub fn update(&mut self, input: &[u8]) {
        self.0.update(input);
    }

    /// Finalizes the hash, returning its 32-byte digest.
    #[must_use]
    pub fn finalize(self) -> [u8; 32] {
        self.0.finalize().into()
    }

    /// Finalizes as lowercase ASCII hex.
    #[must_use]
    pub fn finalize_hex(self) -> [u8; 64] {
        to_hex(self.finalize())
    }
}

impl Default for Sha256 {
    fn default() -> Self {
        Self::new()
    }
}

/// Encodes a raw digest as 64 lowercase ASCII hex bytes.
fn to_hex(digest: [u8; 32]) -> [u8; 64] {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = [0u8; 64];
    for (byte, slot) in digest.iter().zip(out.chunks_exact_mut(2)) {
        slot[0] = HEX[usize::from(byte >> 4)];
        slot[1] = HEX[usize::from(byte & 0x0f)];
    }
    out
}

/// Computes the SHA-256 digest of `input`, returning the raw 32 bytes.
pub fn sha256(input: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(input);
    hasher.finalize()
}

/// Computes the SHA-256 digest of `input` and returns it as 64 lowercase ASCII
/// hex bytes, matching the string the C++ `sha256_hex` produced.
pub fn sha256_hex(input: &[u8]) -> [u8; 64] {
    to_hex(sha256(input))
}
