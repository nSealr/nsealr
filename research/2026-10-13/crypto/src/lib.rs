#![no_std]
// Non-production feasibility probe, exclusively public test keys.
// Array-returning interfaces below are deliberately NOT a production custody API.
use hmac::{Hmac, KeyInit, Mac};
use sha2::Sha256;

pub fn nip44_extract(raw_x: &[u8; 32]) -> [u8; 32] {
    let mut mac = Hmac::<Sha256>::new_from_slice(b"nip44-v2").unwrap();
    mac.update(raw_x);
    mac.finalize().into_bytes().into()
}

#[cfg(feature = "rustcrypto")]
pub mod rustcrypto {
    use k256::{ecdh::diffie_hellman, schnorr::{SigningKey, VerifyingKey, Signature}, PublicKey, SecretKey};
    pub fn sign(secret: &[u8;32], msg: &[u8], aux: &[u8;32]) -> Option<[u8;64]> {
        let key = SigningKey::from_slice(secret).ok()?;
        Some(key.sign_raw(msg, aux).ok()?.to_bytes())
    }
    pub fn verify(public: &[u8;32], msg: &[u8], signature: &[u8;64]) -> bool {
        let Ok(key) = VerifyingKey::from_slice(public) else { return false };
        let Ok(sig) = Signature::try_from(signature.as_slice()) else { return false };
        key.verify_raw(msg, &sig).is_ok()
    }
    pub fn conversation(secret: &[u8;32], public: &[u8;32]) -> Option<[u8;32]> {
        let key = SecretKey::from_slice(secret).ok()?;
        let mut sec1 = [2u8;33]; sec1[1..].copy_from_slice(public);
        let peer = PublicKey::from_sec1_bytes(&sec1).ok()?;
        let shared = diffie_hellman(key.to_nonzero_scalar(), peer.as_affine());
        Some(crate::nip44_extract(shared.raw_secret_bytes().as_ref()))
    }
}

#[cfg(feature = "libsecp")]
pub mod libsecp {
    use secp256k1::{ecdh, schnorr, Keypair, PublicKey, SecretKey, XOnlyPublicKey};
    pub fn sign(secret: &[u8;32], msg: &[u8], aux: &[u8;32]) -> Option<[u8;64]> {
        let key = Keypair::from_secret_bytes(*secret).ok()?;
        Some(schnorr::sign_with_aux_rand(msg, &key, aux).to_byte_array())
    }
    pub fn verify(public: &[u8;32], msg: &[u8], signature: &[u8;64]) -> bool {
        let Ok(key) = XOnlyPublicKey::from_byte_array(*public) else { return false };
        schnorr::verify(&schnorr::Signature::from_byte_array(*signature), msg, &key).is_ok()
    }
    pub fn conversation(secret: &[u8;32], public: &[u8;32]) -> Option<[u8;32]> {
        let key = SecretKey::from_secret_bytes(*secret).ok()?;
        let mut sec1 = [2u8;33]; sec1[1..].copy_from_slice(public);
        let peer = PublicKey::from_byte_array_compressed(sec1).ok()?;
        let xy = ecdh::shared_secret_point(&peer, &key);
        Some(crate::nip44_extract(xy[..32].try_into().unwrap()))
    }
}
