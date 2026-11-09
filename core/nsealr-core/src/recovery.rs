//! Bounded BIP39/NIP06 derivation using the pinned RustCrypto primitives.
use crate::{bip39, nip19::SecretKey, Error};
use hmac::{Hmac, KeyInit, Mac};
use k256::{
    elliptic_curve::{ff::PrimeField, sec1::ToSec1Point},
    Scalar,
};
use sha2::Sha512;
use unicode_normalization::char::{canonical_combining_class, decompose_compatible};
use zeroize::Zeroizing;
const MAX_PASSPHRASE_BYTES: usize = 256;
const MAX_NIP06_ACCOUNT: u32 = (1 << 31) - 1;
const HARDENED: u32 = 1 << 31;
const MNEMONIC_BYTES: usize = 24 * 9 - 1;
fn normalized_passphrase(
    input: &str,
) -> Result<(Zeroizing<[u8; MAX_PASSPHRASE_BYTES]>, usize), Error> {
    if input.len() > MAX_PASSPHRASE_BYTES {
        return Err(Error::Bounds);
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
            return Err(Error::Bounds);
        }
    }
    let mut out = Zeroizing::new([0; MAX_PASSPHRASE_BYTES]);
    let mut offset = 0;
    for ch in &chars[..count] {
        offset += ch.encode_utf8(&mut out[offset..]).len();
    }
    Ok((out, bytes))
}

fn bip39_seed(indexes: &[u16], passphrase: &str) -> Result<Zeroizing<[u8; 64]>, Error> {
    let (normalized, len) = normalized_passphrase(passphrase)?;
    let mut salt = Zeroizing::new([0; 8 + MAX_PASSPHRASE_BYTES]);
    salt[..8].copy_from_slice(b"mnemonic");
    salt[8..8 + len].copy_from_slice(&normalized[..len]);
    let mut mnemonic = Zeroizing::new([0; MNEMONIC_BYTES]);
    // Validated English words and ASCII spaces are already NFKD.
    let sentence =
        bip39::mnemonic_from_indexes(indexes, &mut *mnemonic).map_err(|_| Error::Input)?;
    let mut seed = Zeroizing::new([0; 64]);
    pbkdf2::pbkdf2_hmac::<Sha512>(sentence.as_bytes(), &salt[..8 + len], 2048, &mut *seed);
    Ok(seed)
}

struct ExtendedPrivate {
    key: k256::SecretKey,
    chain: Zeroizing<[u8; 32]>,
}
impl ExtendedPrivate {
    fn master(seed: &[u8]) -> Result<Self, Error> {
        let mut mac =
            Hmac::<Sha512>::new_from_slice(b"Bitcoin seed").expect("HMAC accepts any key length");
        mac.update(seed);
        Self::master_from_output(&finish_hmac(mac))
    }
    fn master_from_output(output: &[u8; 64]) -> Result<Self, Error> {
        let key = k256::SecretKey::from_slice(&output[..32]).map_err(|_| Error::Crypto)?;
        let mut chain = Zeroizing::new([0; 32]);
        chain.copy_from_slice(&output[32..]);
        Ok(Self { key, chain })
    }
    fn child(&self, index: u32) -> Result<Self, Error> {
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
    fn child_from_output(&self, _index: u32, output: &[u8; 64]) -> Result<Self, Error> {
        let mut left = Zeroizing::new(k256::FieldBytes::default());
        left.copy_from_slice(&output[..32]);
        let tweak =
            Zeroizing::new(Option::<Scalar>::from(Scalar::from_repr(*left)).ok_or(Error::Crypto)?);
        let parent = Zeroizing::new(self.key.to_nonzero_scalar());
        let sum = Zeroizing::new(**parent + *tweak);
        let bytes = Zeroizing::new(sum.to_bytes());
        let key = k256::SecretKey::from_bytes(&bytes).map_err(|_| Error::Crypto)?;
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
fn nip06_from_seed(seed: &[u8], account: u32) -> Result<SecretKey, Error> {
    if account > MAX_NIP06_ACCOUNT {
        return Err(Error::Bounds);
    }
    let mut node = ExtendedPrivate::master(seed)?;
    for index in [44 | HARDENED, 1237 | HARDENED, account | HARDENED, 0, 0] {
        node = node.child(index)?;
    }
    let mut bytes = Zeroizing::new([0; 32]);
    let encoded = Zeroizing::new(node.key.to_bytes());
    bytes.copy_from_slice(&encoded);
    SecretKey::take_from(&mut bytes).map_err(|_| Error::Crypto)
}

pub fn derive(indexes: &[u16], passphrase: &str, account: u32) -> Result<SecretKey, Error> {
    let seed = bip39_seed(indexes, passphrase)?;
    nip06_from_seed(&*seed, account)
}
