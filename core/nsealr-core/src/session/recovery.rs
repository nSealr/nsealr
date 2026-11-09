//! Bounded English BIP39/NIP06 recovery using RustCrypto primitives.
//!
//! The exact path is `m/44'/1237'/account'/0/0`. Invalid BIP32 master or
//! child keys fail explicitly; recovery never silently advances an index.
//! Current owned storage is wiped on drop. Compiler moves, registers, backend
//! arithmetic scratch and physical RAM erasure require separate qualification.

use crate::{
    bip39,
    nip19::SecretKey,
    session::keyring::{SessionKeySource, SessionKeySourceKind},
};
use hmac::{Hmac, KeyInit, Mac};
use k256::{
    elliptic_curve::{ff::PrimeField, sec1::ToSec1Point},
    Scalar,
};
use sha2::Sha512;
use unicode_normalization::char::{canonical_combining_class, decompose_compatible};
use zeroize::{Zeroize, Zeroizing};

/// UTF-8 byte limit, applied separately before and after NFKD, without truncation.
pub const MAX_PASSPHRASE_BYTES: usize = 256;
/// Last NIP06 account before the BIP32 hardened bit.
pub const MAX_NIP06_ACCOUNT: u32 = (1 << 31) - 1;
const HARDENED: u32 = 1 << 31;
const MNEMONIC_BYTES: usize = 24 * 9 - 1;

/// Recovery failures never echo secret inputs.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RecoveryError {
    /// English mnemonic shape/checksum failed validation.
    Mnemonic(bip39::Bip39Error),
    /// Passphrase exceeds the byte limit, before or after NFKD.
    PassphraseTooLong,
    /// Owned entry bytes were not UTF-8.
    InvalidUtf8,
    /// The account already contains the hardened bit.
    AccountOutOfRange,
    /// A standalone scalar has no BIP39 passphrase or account index.
    UnexpectedDerivation,
    /// The source has been wiped or has an invalid scalar.
    InvalidSource,
    /// BIP32 master scalar was zero or outside the curve order.
    InvalidMaster,
    /// BIP32 child was invalid at this exact serialized index; no retry occurred.
    InvalidChild(u32),
}

/// Non-cloneable passphrase entry storage; caller entry bytes are cleared on take.
///
/// The normalized form exists only during derivation. UI editing, reveal and
/// confirmation are device responsibilities. Spaces and case are preserved.
pub struct Bip39Passphrase {
    bytes: [u8; MAX_PASSPHRASE_BYTES],
    len: usize,
}
impl Bip39Passphrase {
    /// Takes UTF-8 entry bytes, clearing the entire caller slice on every outcome.
    pub fn take_from(entry: &mut [u8]) -> Result<Self, RecoveryError> {
        let result = (|| {
            if entry.len() > MAX_PASSPHRASE_BYTES {
                return Err(RecoveryError::PassphraseTooLong);
            }
            core::str::from_utf8(entry).map_err(|_| RecoveryError::InvalidUtf8)?;
            let mut value = Self {
                bytes: [0; MAX_PASSPHRASE_BYTES],
                len: entry.len(),
            };
            value.bytes[..entry.len()].copy_from_slice(entry);
            // Reject normalization expansion at entry, before admitting storage.
            normalized_passphrase(value.as_str())?;
            Ok(value)
        })();
        entry.zeroize();
        result
    }
    /// Borrow for local derivation only; never send this value to a companion.
    pub fn as_str(&self) -> &str {
        core::str::from_utf8(&self.bytes[..self.len]).expect("validated UTF-8")
    }
    /// Clears current entry storage immediately, leaving an empty passphrase.
    pub fn clear(&mut self) {
        self.bytes.zeroize();
        self.len.zeroize();
    }
}
impl core::fmt::Debug for Bip39Passphrase {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        f.write_str("Bip39Passphrase([REDACTED])")
    }
}
impl Drop for Bip39Passphrase {
    fn drop(&mut self) {
        self.clear();
    }
}

// Use maintained Unicode decomposition tables, but keep canonical ordering in
// bounded, wiped storage instead of the library iterator's allocating TinyVec.
fn normalized_passphrase(
    input: &str,
) -> Result<(Zeroizing<[u8; MAX_PASSPHRASE_BYTES]>, usize), RecoveryError> {
    if input.len() > MAX_PASSPHRASE_BYTES {
        return Err(RecoveryError::PassphraseTooLong);
    }
    let mut chars = Zeroizing::new(['\0'; MAX_PASSPHRASE_BYTES]);
    let mut count = 0;
    let mut bytes = 0;
    let mut overflow = false;
    for ch in input.chars() {
        decompose_compatible(ch, |part| {
            if overflow {
                return;
            }
            if bytes + part.len_utf8() > MAX_PASSPHRASE_BYTES {
                overflow = true;
                return;
            }
            let class = canonical_combining_class(part);
            let mut pos = count;
            // Stable canonical ordering, never moving a mark across a starter.
            if class != 0 {
                while pos > 0 && canonical_combining_class(chars[pos - 1]) > class {
                    chars[pos] = chars[pos - 1];
                    pos -= 1;
                }
            }
            chars[pos] = part;
            count += 1;
            bytes += part.len_utf8();
        });
        if overflow {
            return Err(RecoveryError::PassphraseTooLong);
        }
    }
    let mut out = Zeroizing::new([0; MAX_PASSPHRASE_BYTES]);
    let mut offset = 0;
    for ch in &chars[..count] {
        offset += ch.encode_utf8(&mut out[offset..]).len();
    }
    Ok((out, bytes))
}

fn bip39_seed(indexes: &[u16], passphrase: &str) -> Result<Zeroizing<[u8; 64]>, RecoveryError> {
    let (normalized, len) = normalized_passphrase(passphrase)?;
    let mut salt = Zeroizing::new([0; 8 + MAX_PASSPHRASE_BYTES]);
    salt[..8].copy_from_slice(b"mnemonic");
    salt[8..8 + len].copy_from_slice(&normalized[..len]);
    let mut mnemonic = Zeroizing::new([0; MNEMONIC_BYTES]);
    // Validated English words and ASCII spaces are already NFKD.
    let sentence =
        bip39::mnemonic_from_indexes(indexes, &mut *mnemonic).map_err(RecoveryError::Mnemonic)?;
    let mut seed = Zeroizing::new([0; 64]);
    pbkdf2::pbkdf2_hmac::<Sha512>(sentence.as_bytes(), &salt[..8 + len], 2048, &mut *seed);
    Ok(seed)
}

struct ExtendedPrivate {
    key: k256::SecretKey,
    chain: Zeroizing<[u8; 32]>,
}
impl ExtendedPrivate {
    fn master(seed: &[u8]) -> Result<Self, RecoveryError> {
        let mut mac =
            Hmac::<Sha512>::new_from_slice(b"Bitcoin seed").expect("HMAC accepts any key length");
        mac.update(seed);
        Self::master_from_output(&finish_hmac(mac))
    }
    fn master_from_output(output: &[u8; 64]) -> Result<Self, RecoveryError> {
        let key =
            k256::SecretKey::from_slice(&output[..32]).map_err(|_| RecoveryError::InvalidMaster)?;
        let mut chain = Zeroizing::new([0; 32]);
        chain.copy_from_slice(&output[32..]);
        Ok(Self { key, chain })
    }
    fn child(&self, index: u32) -> Result<Self, RecoveryError> {
        let mut mac =
            Hmac::<Sha512>::new_from_slice(&*self.chain).expect("HMAC accepts any key length");
        if index & HARDENED != 0 {
            mac.update(&[0]);
            let bytes = Zeroizing::new(self.key.to_bytes());
            mac.update(&bytes);
        } else {
            // BIP32 requires the actual 02/03 parity, never Schnorr normalization.
            let public = self.key.public_key().to_sec1_point(true);
            mac.update(public.as_bytes());
        }
        mac.update(&index.to_be_bytes());
        self.child_from_output(index, &finish_hmac(mac))
    }
    fn child_from_output(&self, index: u32, output: &[u8; 64]) -> Result<Self, RecoveryError> {
        let mut left = Zeroizing::new(k256::FieldBytes::default());
        left.copy_from_slice(&output[..32]);
        let tweak = Zeroizing::new(
            Option::<Scalar>::from(Scalar::from_repr(*left))
                .ok_or(RecoveryError::InvalidChild(index))?,
        );
        let parent = Zeroizing::new(self.key.to_nonzero_scalar());
        let sum = Zeroizing::new(**parent + *tweak);
        let bytes = Zeroizing::new(sum.to_bytes());
        let key =
            k256::SecretKey::from_bytes(&bytes).map_err(|_| RecoveryError::InvalidChild(index))?;
        let mut chain = Zeroizing::new([0; 32]);
        chain.copy_from_slice(&output[32..]);
        Ok(Self { key, chain })
    }
}
fn finish_hmac(mac: Hmac<Sha512>) -> Zeroizing<[u8; 64]> {
    let mut result = Zeroizing::new([0; 64]);
    hmac::digest::FixedOutput::finalize_into(mac, (&mut *result).into());
    result
}
fn nip06_from_seed(seed: &[u8], account: u32) -> Result<SecretKey, RecoveryError> {
    if account > MAX_NIP06_ACCOUNT {
        return Err(RecoveryError::AccountOutOfRange);
    }
    let mut node = ExtendedPrivate::master(seed)?;
    for index in [44 | HARDENED, 1237 | HARDENED, account | HARDENED, 0, 0] {
        node = node.child(index)?;
    }
    let mut bytes = Zeroizing::new([0; 32]);
    let encoded = Zeroizing::new(node.key.to_bytes());
    bytes.copy_from_slice(&encoded);
    SecretKey::take_from(&mut bytes).map_err(|_| RecoveryError::InvalidSource)
}

/// Derives actual custody from a validated local source, with finite inputs.
///
/// A borrowed passphrase is not cleared by this function: keep it in
/// [`Bip39Passphrase`] or equivalent wiped local entry storage. The returned
/// scalar retains its original parity/bytes for nsec backup and is consumed by
/// [`crate::authorization::AuthorizationSession::select_key`]. No descriptor,
/// fingerprint or caller-supplied public key participates in derivation.
pub fn derive_source_key(
    source: &SessionKeySource,
    passphrase: &str,
    account: u32,
) -> Result<SecretKey, RecoveryError> {
    match source.kind {
        SessionKeySourceKind::NsecSecretKey => {
            if !passphrase.is_empty() || account != 0 {
                return Err(RecoveryError::UnexpectedDerivation);
            }
            let mut bytes = Zeroizing::new(*source.nsec_secret_key.as_bytes());
            SecretKey::take_from(&mut bytes).map_err(|_| RecoveryError::InvalidSource)
        }
        SessionKeySourceKind::Bip39WordIndexes => {
            if account > MAX_NIP06_ACCOUNT {
                return Err(RecoveryError::AccountOutOfRange);
            }
            let seed = bip39_seed(source.bip39_word_indexes.as_slice(), passphrase)?;
            nip06_from_seed(&*seed, account)
        }
    }
}

/// Computes the Nostr x-only public identity from an actual local scalar.
pub fn source_public_key(secret: &SecretKey) -> Result<[u8; 32], RecoveryError> {
    let backend = k256::schnorr::SigningKey::from_slice(secret.as_bytes())
        .map_err(|_| RecoveryError::InvalidSource)?;
    Ok(backend.verifying_key().to_bytes().into())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::session::{
        account::*, import_review::session_key_source_fingerprint,
        keyring::StatelessSessionKeyring, source_qr::*,
    };
    use std::{format, string::String, vec::Vec};
    use unicode_normalization::UnicodeNormalization;

    const MNEMONIC: &str =
        "leader monkey parrot ring guide accident before fence cannon height naive bean";
    fn hex(input: &str) -> Vec<u8> {
        input
            .as_bytes()
            .chunks_exact(2)
            .map(|p| {
                let digit = |c| match c {
                    b'0'..=b'9' => c - b'0',
                    b'a'..=b'f' => c - b'a' + 10,
                    _ => panic!("fixture hex"),
                };
                digit(p[0]) * 16 + digit(p[1])
            })
            .collect()
    }
    fn fixture(input: &str) -> serde_json::Value {
        serde_json::from_str(input).unwrap()
    }
    fn source(words: &str) -> SessionKeySource {
        parse_session_source_bytes(
            "public fixture",
            SessionSourceFormat::EnglishMnemonic,
            words.as_bytes(),
        )
        .unwrap()
    }
    fn normalized(input: &str) -> String {
        let (bytes, len) = normalized_passphrase(input).unwrap();
        core::str::from_utf8(&bytes[..len]).unwrap().into()
    }

    #[test]
    fn published_bip39_english_seeds() {
        let vectors = fixture(include_str!("../../testdata/recovery/bip39-english.json"));
        let vectors = vectors.as_array().unwrap();
        assert_eq!(vectors.len(), 24);
        for row in vectors {
            let indexes = bip39::parse_mnemonic_indexes(row[1].as_str().unwrap()).unwrap();
            let seed = bip39_seed(indexes.as_slice(), "TREZOR").unwrap();
            assert_eq!(&seed[..], hex(row[2].as_str().unwrap()));
        }
    }

    #[test]
    fn published_bip32_nodes_include_odd_parents_and_leading_zeroes() {
        let vectors = fixture(include_str!("../../testdata/recovery/bip32-published.json"));
        let vectors = vectors.as_array().unwrap();
        assert_eq!(vectors.len(), 17);
        let mut odd = false;
        let mut leading_zero = false;
        for row in vectors {
            let mut node = ExtendedPrivate::master(&hex(row["seed"].as_str().unwrap())).unwrap();
            for part in row["path"].as_str().unwrap().split('/').skip(1) {
                let hardened = part.ends_with('\'');
                let index: u32 = part.trim_end_matches('\'').parse().unwrap();
                node = node
                    .child(index | if hardened { HARDENED } else { 0 })
                    .unwrap();
            }
            let private = Zeroizing::new(node.key.to_bytes());
            let public = node.key.public_key().to_sec1_point(true);
            assert_eq!(&private[..], hex(row["private_key"].as_str().unwrap()));
            assert_eq!(&node.chain[..], hex(row["chain_code"].as_str().unwrap()));
            assert_eq!(
                public.as_bytes(),
                hex(row["compressed_public_key"].as_str().unwrap())
            );
            odd |= public.as_bytes()[0] == 3;
            leading_zero |= private[0] == 0;
        }
        assert!(odd && leading_zero);
    }

    #[test]
    fn nip06_identity_matches_published_and_independent_matrix() {
        let vectors = fixture(include_str!("../../testdata/recovery/nip06-scure.json"));
        let vectors = vectors.as_array().unwrap();
        assert_eq!(vectors.len(), 36);
        for row in vectors {
            let source = source(row["mnemonic"].as_str().unwrap());
            let secret = derive_source_key(
                &source,
                row["passphrase"].as_str().unwrap(),
                row["account"].as_u64().unwrap() as u32,
            )
            .unwrap();
            assert_eq!(
                secret.as_bytes().as_slice(),
                hex(row["private_key"].as_str().unwrap())
            );
            assert_eq!(
                source_public_key(&secret).unwrap().as_slice(),
                hex(row["public_key"].as_str().unwrap())
            );
        }
    }

    #[test]
    fn unicode18_official_nfkd_conformance_all_five_columns() {
        let mut rows = 0;
        for line in include_str!("../../testdata/recovery/unicode18-nfkd.txt")
            .lines()
            .filter(|line| !line.starts_with('#'))
        {
            let columns: Vec<String> = line
                .split(';')
                .take(5)
                .map(|s| {
                    s.split_whitespace()
                        .map(|v| char::from_u32(u32::from_str_radix(v, 16).unwrap()).unwrap())
                        .collect()
                })
                .collect();
            assert_eq!(columns.len(), 5);
            for input in &columns {
                assert_eq!(normalized(input), columns[4], "Unicode row {}", rows);
            }
            rows += 1;
        }
        assert_eq!(rows, 20171);
    }

    #[test]
    fn bounded_nfkd_matches_library_iterator_for_every_unicode_scalar() {
        for value in 0..=0x10ffff {
            if let Some(ch) = char::from_u32(value) {
                let mut bytes = [0; 4];
                let text = ch.encode_utf8(&mut bytes);
                assert_eq!(
                    normalized(text),
                    text.nfkd().collect::<String>(),
                    "U+{value:X}"
                );
            }
        }
        for text in [
            "\u{301}\u{323}x\u{315}\u{300}",
            "\u{ac01}\u{212b}\u{fb03}",
            "a\u{301}\u{300}\u{323}",
            "\0\n\r \u{1f600}",
        ] {
            assert_eq!(normalized(text), text.nfkd().collect::<String>());
        }
    }

    #[test]
    fn passphrase_limits_are_bytes_before_and_after_nfkd_and_entry_is_cleared() {
        assert_eq!(normalized(&"a".repeat(256)), "a".repeat(256));
        assert_eq!(
            normalized_passphrase(&"a".repeat(257)).unwrap_err(),
            RecoveryError::PassphraseTooLong
        );
        assert_eq!(normalized(&"é".repeat(85)).len(), 255);
        assert_eq!(
            normalized_passphrase(&"é".repeat(86)).unwrap_err(),
            RecoveryError::PassphraseTooLong
        );
        for mut bytes in [
            std::vec![0xff],
            std::vec![b'a'; 257],
            "é".repeat(86).into_bytes(),
        ] {
            assert!(Bip39Passphrase::take_from(&mut bytes).is_err());
            assert!(bytes.iter().all(|&b| b == 0));
        }
        let mut entry = *b"  TREZOR  ";
        let mut passphrase = Bip39Passphrase::take_from(&mut entry).unwrap();
        assert_eq!(entry, [0; 10]);
        assert_eq!(passphrase.as_str(), "  TREZOR  ");
        assert_eq!(format!("{passphrase:?}"), "Bip39Passphrase([REDACTED])");
        passphrase.clear();
        assert!(passphrase.bytes.iter().all(|&b| b == 0));
        assert_eq!(passphrase.as_str(), "");
        assert_eq!(normalized("café"), normalized("cafe\u{301}"));
    }

    #[test]
    fn invalid_bip32_master_and_child_fail_at_exact_index_without_retry() {
        let order = hex("fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141");
        for scalar in [std::vec![0; 32], order.clone(), std::vec![0xff; 32]] {
            let mut output = [0; 64];
            output[..32].copy_from_slice(&scalar);
            assert!(matches!(
                ExtendedPrivate::master_from_output(&output),
                Err(RecoveryError::InvalidMaster)
            ));
        }
        let mut output = [0; 64];
        output[31] = 1;
        let node = ExtendedPrivate::master_from_output(&output).unwrap();
        for index in [0, MAX_NIP06_ACCOUNT, u32::MAX] {
            for scalar in [&order[..], &[0xff; 32][..]] {
                output[..32].copy_from_slice(scalar);
                assert!(
                    matches!(node.child_from_output(index, &output), Err(RecoveryError::InvalidChild(i)) if i == index)
                );
            }
            output[..32].copy_from_slice(&order);
            output[31] -= 1;
            assert!(
                matches!(node.child_from_output(index, &output), Err(RecoveryError::InvalidChild(i)) if i == index)
            );
        }
        // IL=0 is valid for a child (unlike a master): preserve parent bytes.
        output.fill(0);
        assert_eq!(node.child_from_output(0, &output).unwrap().key, node.key);
    }

    #[test]
    fn verified_account_rejects_wrong_identity_passphrase_alias_and_wiped_source() {
        let mut ring = StatelessSessionKeyring::new();
        ring.add_source(source(MNEMONIC)).unwrap();
        let fingerprint = session_key_source_fingerprint(ring.source_at(0).unwrap());
        let descriptor = SessionAccountDescriptor {
            account_id: "recovery",
            route_type: ESP32_QR_VAULT_ROUTE_TYPE,
            public_key: "17162c921dc4d2518f9a101db33695df1afb56ab82f5ff3e5da6eec3ca5cd917",
            source_index: 0,
            source_fingerprint: fingerprint.as_str(),
            recovery_kind: SessionAccountRecoveryKind::Nip06,
            derivation_path: "m/44'/1237'/0'/0/0",
            account_index: 0,
        };
        assert!(
            !select_session_account(&ring, &descriptor)
                .unwrap()
                .source_public_key_proof_verified
        );
        let recovered = recover_session_account(&ring, &descriptor, "").unwrap();
        assert!(recovered.selected().source_public_key_proof_verified);
        assert_eq!(
            source_public_key(&recovered.into_secret_key())
                .unwrap()
                .as_slice(),
            hex(descriptor.public_key)
        );
        assert!(matches!(
            recover_session_account(&ring, &descriptor, "wrong"),
            Err(SessionAccountError::PublicKeyMismatch)
        ));
        let mut wrong = descriptor;
        wrong.public_key = "d41b22899549e1f3d335a31002cfd382174006e166d3e658e3a5eecdb6463573";
        assert!(matches!(
            recover_session_account(&ring, &wrong, ""),
            Err(SessionAccountError::PublicKeyMismatch)
        ));
        wrong = descriptor;
        wrong.account_index = HARDENED;
        assert!(matches!(
            recover_session_account(&ring, &wrong, ""),
            Err(SessionAccountError::AccountOutOfRange)
        ));
        assert_eq!(
            derive_source_key(ring.source_at(0).unwrap(), "", u32::MAX).unwrap_err(),
            RecoveryError::AccountOutOfRange
        );
        let mut removed = ring.take_last().unwrap();
        removed.wipe();
        assert_eq!(
            derive_source_key(&removed, "", 0).unwrap_err(),
            RecoveryError::InvalidSource
        );
        assert!(ring.source_at(0).is_err());
    }
}
