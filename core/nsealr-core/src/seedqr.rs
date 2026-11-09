//! SeedQR decoding — Standard (4-digit-per-word) and Compact (raw entropy).
//!
//! Ported from the C++ reference `host_core` sources `src/seedqr.cpp` +
//! `include/nsealr/seedqr.hpp` for behaviour parity. Both decoders reuse the BIP-39
//! layer ([`crate::bip39`]): the Standard decoder validates the final BIP-39
//! checksum, while the Compact decoder reconstructs the word indexes from the raw
//! entropy plus its SHA-256 checksum bits exactly as the C++ did.
//!
//! Decoded word indexes are returned by value as a [`crate::bip39::WordIndexes`]
//! (at most 24 entries), keeping the crate `no_std` and allocation-free.

use crate::bip39::{self, Bip39Error, WordIndexes};
use crate::hash::sha256;

/// Errors reported by the SeedQR decoders. Each variant corresponds to a distinct
/// C++ `SeedQrError` throw site.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SeedQrError {
    /// The Standard digit stream contained a non-digit character. C++: "Standard
    /// SeedQR digit stream must contain only digits".
    NonDigit,
    /// The Standard digit stream was empty after stripping whitespace. C++:
    /// "Standard SeedQR digit stream must not be empty".
    Empty,
    /// The Standard digit count was not a multiple of four. C++: "Standard SeedQR
    /// digit stream length must contain four digits per word".
    NotFourPerWord,
    /// The Standard word count was not 12 or 24. C++: "SeedQR word count must be 12
    /// or 24".
    InvalidWordCount,
    /// A Standard 4-digit group exceeded 2047. C++: "Standard SeedQR word index is
    /// outside the BIP-39 English wordlist".
    IndexOutOfRange,
    /// The Compact entropy length was not 16 or 32 bytes. C++: "CompactSeedQR byte
    /// length must be 16 or 32".
    InvalidByteLength,
    /// The reconstructed indexes failed BIP-39 validation/checksum. The C++ wrapped
    /// the `Bip39Error` message as `"SeedQR " + what()`; this port carries the
    /// underlying [`Bip39Error`].
    Bip39(Bip39Error),
}

const fn is_seedqr_whitespace(byte: u8) -> bool {
    matches!(byte, b' ' | b'\n' | b'\r' | b'\t')
}

/// Extracts the `bit_index`-th entropy bit (MSB-first within each byte). Mirrors the
/// C++ `entropy_bit`.
fn entropy_bit(entropy: &[u8], bit_index: usize) -> u8 {
    (entropy[bit_index / 8] >> (7 - (bit_index % 8))) & 1
}

/// Extracts the `bit_index`-th digest bit (MSB-first within each byte). The C++
/// `digest_bit` read the hex digest string; reading the raw digest byte is
/// bit-for-bit identical.
fn digest_bit(digest: &[u8; 32], bit_index: usize) -> u8 {
    (digest[bit_index / 8] >> (7 - (bit_index % 8))) & 1
}

/// Decodes a Standard SeedQR digit stream (four decimal digits per word) into its
/// validated word indexes. Mirrors the C++ `decode_standard_seedqr_indexes`.
///
/// Whitespace is ignored. Requires a non-empty stream whose digit count is a
/// multiple of four and whose word count is 12 or 24, each group in `0..=2047`,
/// with a valid BIP-39 checksum.
///
/// # Errors
///
/// [`SeedQrError::NonDigit`], [`SeedQrError::Empty`], [`SeedQrError::NotFourPerWord`],
/// [`SeedQrError::InvalidWordCount`], [`SeedQrError::IndexOutOfRange`] or
/// [`SeedQrError::Bip39`], in the same precedence order as the C++.
pub fn decode_standard_indexes(digits: &str) -> Result<WordIndexes, SeedQrError> {
    let bytes = digits.as_bytes();

    // Pass 1: reject non-digits (whitespace ignored) and count the digits — the C++
    // built the normalized string here, throwing on the first stray character.
    let mut digit_count = 0usize;
    for &byte in bytes {
        if is_seedqr_whitespace(byte) {
            continue;
        }
        if !byte.is_ascii_digit() {
            return Err(SeedQrError::NonDigit);
        }
        digit_count += 1;
    }
    if digit_count == 0 {
        return Err(SeedQrError::Empty);
    }
    if !digit_count.is_multiple_of(4) {
        return Err(SeedQrError::NotFourPerWord);
    }
    let word_count = digit_count / 4;
    if word_count != 12 && word_count != 24 {
        return Err(SeedQrError::InvalidWordCount);
    }

    // Pass 2: fold every four digits into a word index.
    let mut indexes = WordIndexes::new();
    let mut group = zeroize::Zeroizing::new([0u16; 4]);
    let mut in_group = 0usize;
    for &byte in bytes {
        if is_seedqr_whitespace(byte) {
            continue;
        }
        group[in_group] = u16::from(byte - b'0');
        in_group += 1;
        if in_group == 4 {
            let index = group[0] * 1000 + group[1] * 100 + group[2] * 10 + group[3];
            if index > 2047 {
                return Err(SeedQrError::IndexOutOfRange);
            }
            indexes.push(index);
            in_group = 0;
        }
    }

    bip39::require_valid_checksum(indexes.as_slice()).map_err(SeedQrError::Bip39)?;
    Ok(indexes)
}

/// Decodes a CompactSeedQR entropy blob (16 or 32 raw bytes) into its word indexes.
/// Mirrors the C++ `decode_compact_seedqr_indexes`: the entropy bits followed by the
/// leading bits of its SHA-256 form the 11-bit word indexes; no separate checksum
/// check is needed because the checksum is reconstructed here.
///
/// # Errors
///
/// [`SeedQrError::InvalidByteLength`] if `entropy` is not 16 or 32 bytes.
pub fn decode_compact_indexes(entropy: &[u8]) -> Result<WordIndexes, SeedQrError> {
    let checksum_bits = match entropy.len() {
        16 => 4usize,
        32 => 8usize,
        _ => return Err(SeedQrError::InvalidByteLength),
    };
    let entropy_bits = entropy.len() * 8;
    let word_count = (entropy_bits + checksum_bits) / 11;
    let digest = zeroize::Zeroizing::new(sha256(entropy));

    let mut indexes = WordIndexes::new();
    for word in 0..word_count {
        let mut value = 0u16;
        for bit in 0..11 {
            let global_bit = word * 11 + bit;
            let bit_value = if global_bit < entropy_bits {
                entropy_bit(entropy, global_bit)
            } else {
                digest_bit(&digest, global_bit - entropy_bits)
            };
            value = (value << 1) | u16::from(bit_value);
        }
        indexes.push(value);
    }
    Ok(indexes)
}
