use crate::{
    bip39::{self, WordIndexes},
    nip19::{self, SecretKey},
    recovery, seedqr, Error,
};
use alloc::string::String;
use zeroize::{Zeroize, Zeroizing};

pub struct Identity {
    pub(crate) secret: SecretKey,
    words: Option<WordIndexes>,
    pub account: u32,
}
impl Identity {
    pub fn nsec(input: &str) -> Result<Self, Error> {
        Ok(Self {
            secret: nip19::decode_nsec(input).map_err(|_| Error::Input)?,
            words: None,
            account: 0,
        })
    }
    pub fn mnemonic(input: &str, passphrase: &str, account: u32) -> Result<Self, Error> {
        Self::from_words(
            bip39::parse_mnemonic_indexes(input).map_err(|_| Error::Input)?,
            passphrase,
            account,
        )
    }
    fn from_words(words: WordIndexes, passphrase: &str, account: u32) -> Result<Self, Error> {
        let secret = recovery::derive(words.as_slice(), passphrase, account)?;
        Ok(Self {
            secret,
            words: Some(words),
            account,
        })
    }
    pub fn seedqr(
        input: &[u8],
        compact: bool,
        passphrase: &str,
        account: u32,
    ) -> Result<Self, Error> {
        let words = if compact {
            seedqr::decode_compact_indexes(input)
        } else {
            seedqr::decode_standard_indexes(core::str::from_utf8(input).map_err(|_| Error::Input)?)
        }
        .map_err(|_| Error::Input)?;
        Self::from_words(words, passphrase, account)
    }
    pub fn generate(
        words: u32,
        entropy: &mut [u8; 32],
        passphrase: &str,
        account: u32,
    ) -> Result<Self, Error> {
        let result = (|| {
            if words == 0 {
                if !passphrase.is_empty() || account != 0 {
                    return Err(Error::Input);
                }
                return Ok(Self {
                    secret: SecretKey::take_from(entropy).map_err(|_| Error::Entropy)?,
                    words: None,
                    account: 0,
                });
            }
            let bytes = match words {
                12 => 16,
                24 => 32,
                _ => return Err(Error::Input),
            };
            Self::seedqr(&entropy[..bytes], true, passphrase, account)
        })();
        entropy.zeroize();
        result
    }
    pub fn public_key(&self) -> [u8; 32] {
        k256::schnorr::SigningKey::from_slice(self.secret.as_bytes())
            .expect("validated scalar")
            .verifying_key()
            .to_bytes()
            .into()
    }
    pub fn npub(&self) -> String {
        let mut out = [0; 83];
        nip19::encode_npub(&self.public_key(), &mut out)
            .expect("npub buffer")
            .into()
    }
    pub fn word_count(&self) -> usize {
        self.words.as_ref().map_or(0, |w| w.as_slice().len())
    }
    pub fn word(&self, index: usize) -> Result<&'static str, Error> {
        let word = self.word_index(index)?;
        bip39::word_at(word).map_err(|_| Error::Input)
    }
    pub fn word_index(&self, index: usize) -> Result<u16, Error> {
        self.words
            .as_ref()
            .and_then(|w| w.as_slice().get(index))
            .copied()
            .ok_or(Error::Input)
    }
    /// Local UI only. Caller supplies deliberate physical backup consent and
    /// clears its output/rendering. No optical method exposes this operation.
    pub fn backup(&self, kind: u32, out: &mut [u8]) -> Result<usize, Error> {
        out.zeroize();
        let result = (|| {
            if kind == 1 {
                return nip19::encode_nsec(&self.secret, out)
                    .map(str::len)
                    .map_err(|_| Error::Output);
            }
            let words = self.words.as_ref().ok_or(Error::Unsupported)?.as_slice();
            match kind {
                2 => bip39::mnemonic_from_indexes(words, out)
                    .map(str::len)
                    .map_err(|_| Error::Output),
                3 => {
                    if !matches!(words.len(), 12 | 24) {
                        return Err(Error::Unsupported);
                    }
                    if out.len() < words.len() * 4 {
                        return Err(Error::Output);
                    }
                    for (word, part) in words.iter().zip(out.chunks_exact_mut(4)) {
                        part[0] = b'0' + (word / 1000) as u8;
                        part[1] = b'0' + (word / 100 % 10) as u8;
                        part[2] = b'0' + (word / 10 % 10) as u8;
                        part[3] = b'0' + (word % 10) as u8;
                    }
                    Ok(words.len() * 4)
                }
                4 => {
                    if !matches!(words.len(), 12 | 24) {
                        return Err(Error::Unsupported);
                    }
                    let mut entropy = Zeroizing::new([0; 32]);
                    let bytes = bip39::entropy_from_indexes(words, &mut *entropy)
                        .map_err(|_| Error::Input)?;
                    if out.len() < bytes.len() {
                        return Err(Error::Output);
                    }
                    out[..bytes.len()].copy_from_slice(bytes);
                    Ok(bytes.len())
                }
                _ => Err(Error::Unsupported),
            }
        })();
        if result.is_err() {
            out.zeroize();
        }
        result
    }
    pub fn sign(&self, id: &[u8; 32], aux: &[u8; 32]) -> Result<[u8; 64], Error> {
        let key = k256::schnorr::SigningKey::from_slice(self.secret.as_bytes())
            .map_err(|_| Error::Crypto)?;
        key.sign_raw(id, aux)
            .map(|s| s.to_bytes())
            .map_err(|_| Error::Crypto)
    }
    pub fn encrypt(
        &self,
        peer: &[u8; 32],
        plaintext: &str,
        nonce: &[u8; 32],
        out: &mut [u8],
    ) -> Result<usize, Error> {
        crate::nip44::encrypt(&self.secret, peer, plaintext, nonce, out).map_err(|_| Error::Crypto)
    }
    pub fn decrypt(
        &self,
        peer: &[u8; 32],
        ciphertext: &str,
        out: &mut [u8],
    ) -> Result<usize, Error> {
        crate::nip44::decrypt(&self.secret, peer, ciphertext, out).map_err(|_| Error::Crypto)
    }
}
