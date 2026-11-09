//! Local seed inputs. Input length is not a measurement of physical entropy.
use crate::{hash::Sha256, identity::Identity, Error};
use zeroize::{Zeroize, Zeroizing};

/// SHA256 of the exact ASCII roll sequence, following SeedSigner's string-hash
/// method. Use 100 rather than 99 rolls for 24 words: 100 fair independent d6 rolls
/// contain about 258.5 bits. Hashing cannot repair biased or predictable rolls.
pub fn dice(words: u32, rolls: &mut [u8]) -> Result<Identity, Error> {
    let result = (|| {
        let expected = match words {
            12 => 50,
            24 => 100,
            _ => return Err(Error::Input),
        };
        if rolls.len() != expected || !rolls.iter().all(|value| (b'1'..=b'6').contains(value)) {
            return Err(Error::Input);
        }
        let mut entropy = Zeroizing::new(crate::hash::sha256(rolls));
        Identity::generate(words, &mut entropy, "", 0)
    })();
    rolls.zeroize();
    result
}

/// Combine a platform-qualified camera digest with fresh hardware randomness.
/// Capture review and raw-frame cleanup belong to the platform. A digest alone
/// cannot establish the entropy of an image or identify a repeated photograph.
pub fn photo(
    words: u32,
    image_digest: &mut [u8; 32],
    hardware: &mut [u8; 32],
) -> Result<Identity, Error> {
    let result = (|| {
        if !matches!(words, 12 | 24) {
            return Err(Error::Input);
        }
        if image_digest.iter().all(|value| *value == 0) || hardware.iter().all(|value| *value == 0)
        {
            return Err(Error::Entropy);
        }
        let mut hash = Sha256::new();
        hash.update(b"nsealr/photo-seed\0");
        hash.update(image_digest);
        hash.update(hardware);
        let mut entropy = Zeroizing::new(hash.finalize());
        Identity::generate(words, &mut entropy, "", 0)
    })();
    image_digest.zeroize();
    hardware.zeroize();
    result
}
