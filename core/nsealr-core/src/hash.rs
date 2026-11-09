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

#[cfg(test)]
mod tests {
    use super::*;

    fn assert_hex(input: &[u8], expected: &str) {
        let out = sha256_hex(input);
        assert_eq!(core::str::from_utf8(&out).unwrap(), expected);
    }

    #[test]
    fn nist_known_answer_vectors() {
        assert_hex(
            b"",
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        );
        assert_hex(
            b"abc",
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        );
        // 448-bit (56-byte) two-block NIST message.
        assert_hex(
            b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
            "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
        );
        // 896-bit (112-byte) NIST message.
        assert_hex(
            b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu",
            "cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1",
        );
    }

    #[test]
    fn block_boundary_padding_paths() {
        // 55 bytes: 0x80 + length fit in the same (single) final block.
        assert_hex(
            &[b'a'; 55],
            "9f4390f8d30c2dd92ec9f095b65e2b9ae9b0a925a5258e241c9f1e910f734318",
        );
        // 56 bytes: padding forces a second final block.
        assert_hex(
            &[b'a'; 56],
            "b35439a4ac6f0948b6d6f9e3c6af0f5f590ce20f1bde7090ef7970686ec6738a",
        );
        // Exactly one full 64-byte block, then a whole padding block.
        assert_hex(
            &[b'a'; 64],
            "ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb",
        );
        // Long multi-block input.
        assert_hex(
            &[b'a'; 1000],
            "41edece42d63e8d9bf515a9ba6932e1c20cbc9f5a5d134645adb5db1b9737ea3",
        );
    }

    #[test]
    fn raw_digest_bytes() {
        assert_eq!(
            sha256(b""),
            [
                0xe3, 0xb0, 0xc4, 0x42, 0x98, 0xfc, 0x1c, 0x14, 0x9a, 0xfb, 0xf4, 0xc8, 0x99, 0x6f,
                0xb9, 0x24, 0x27, 0xae, 0x41, 0xe4, 0x64, 0x9b, 0x93, 0x4c, 0xa4, 0x95, 0x99, 0x1b,
                0x78, 0x52, 0xb8, 0x55,
            ],
        );
        let abc = sha256(b"abc");
        assert_eq!(abc[0], 0xba);
        assert_eq!(abc[31], 0xad);
    }

    // The incremental hasher matches the one-shot digest for every chunking of
    // the same input, including chunks that straddle block boundaries (M-T3.6
    // addition; the KATs above already pin the shared compression path).
    #[test]
    fn incremental_updates_match_one_shot() {
        let input: std::vec::Vec<u8> = (0..1000u32).map(|i| (i % 251) as u8).collect();
        let expected = sha256(&input);
        for chunk_size in [1usize, 3, 55, 56, 63, 64, 65, 128, 999] {
            let mut hasher = Sha256::new();
            for chunk in input.chunks(chunk_size) {
                hasher.update(chunk);
            }
            assert_eq!(hasher.finalize(), expected);
        }
        let mut hex_hasher = Sha256::default();
        hex_hasher.update(b"abc");
        assert_eq!(
            core::str::from_utf8(&hex_hasher.finalize_hex()).unwrap(),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        );
        let empty = Sha256::new();
        assert_eq!(
            core::str::from_utf8(&empty.finalize_hex()).unwrap(),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        );
    }

    // Byte-for-byte cross-primitive parity with a READ-ONLY specs/vectors
    // fixture: specs/vectors/transports/qr-animated-response-kind-1-basic.json
    // asserts `decoded_json_sha256 == sha256(base64url_decode(payload_base64url))`.
    // Both literals are copied verbatim from that fixture.
    #[test]
    fn specs_vector_sha256_over_decoded_base64url_payload() {
        const PAYLOAD: &[u8] = b"eyJ2ZXJzaW9uIjoxLCJyZXF1ZXN0X2lkIjoicmVxLWtpbmQtMS1iYXNpYyIsIm9rIjp0cnVlLCJyZXN1bHQiOnsiZXZlbnQiOnsiaWQiOiIyOTc3ZjEwN2FkMjY2OGRiZDlmMDliODU5NGVmZjNiNTI3NmUyMWJmZTA5OGU2MGFlM2U5MDVlM2M4NjFlNGQzIiwicHVia2V5IjoiNGYzNTViZGNiN2NjMGFmNzI4ZWYzY2NlYjk2MTVkOTA2ODRiYjViMmNhNWY4NTlhYjBmMGI3MDQwNzU4NzFhYSIsImNyZWF0ZWRfYXQiOjE3MTAwMDAwMDAsImtpbmQiOjEsInRhZ3MiOltdLCJjb250ZW50IjoiblNlYWxyIGZpeHR1cmU6IGJhc2ljIGtpbmQgMSBldmVudC4iLCJzaWciOiIyZWVjMDM1MWViMWQ2NTExNDA5MjJkNGIxZjFiZDgxMzVmNDQ3NGFhYmY0MmVjNWJkYTcwMTEwODdjMWEwNzJkNzFiZTg2MzY0NmRjMTYyZTRkOTZlYWNmMTRhZmVlZDI2MThhNGFjYjBlMTEzNGEyNzNhMmI4ZTczMDM5ZTY1NCJ9fX0";
        const EXPECTED: &str = "e4ed45466ba40f9e902bf988eb5aab58082b17586b0da47f45f67ce0a4211ec3";
        let mut raw = [0u8; 512];
        let decoded = crate::base64url::decode_base64url(PAYLOAD, &mut raw).expect("decode fits");
        let hex = sha256_hex(decoded);
        assert_eq!(core::str::from_utf8(&hex).unwrap(), EXPECTED);
    }
}
