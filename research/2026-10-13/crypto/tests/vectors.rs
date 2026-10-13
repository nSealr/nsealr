use nsealr_crypto_feasibility_spike::{rustcrypto, libsecp};
fn hex(s: &str) -> Vec<u8> { (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i+2],16).unwrap()).collect() }
fn arr<const N:usize>(s: &str) -> [u8;N] { hex(s).try_into().unwrap() }
include!("nip44_data.rs");
#[test]
fn all_official_bip340_vectors_both_backends() {
    let mut signed=0; let mut valid=0; let mut invalid=0;
    for line in include_str!("../sources/bitcoin/bips/bip-0340/test-vectors.csv").lines().skip(1) {
        let fields:Vec<_>=line.splitn(8,',').collect();
        let pk=arr(fields[2]); let msg=hex(fields[4]); let sig=arr(fields[5]); let expected=fields[6]=="TRUE";
        assert_eq!(rustcrypto::verify(&pk,&msg,&sig),expected,"k256 vector {}",fields[0]);
        assert_eq!(libsecp::verify(&pk,&msg,&sig),expected,"libsecp vector {}",fields[0]);
        if expected { valid+=1 } else { invalid+=1 }
        if !fields[1].is_empty() {
            let sk=arr(fields[1]); let aux=arr(fields[3]);
            assert_eq!(rustcrypto::sign(&sk,&msg,&aux),Some(sig),"k256 sign vector {}",fields[0]);
            assert_eq!(libsecp::sign(&sk,&msg,&aux),Some(sig),"libsecp sign vector {}",fields[0]); signed+=1;
        }
    }
    println!("BIP340: {valid} valid and {invalid} invalid verification vectors; {signed} exact signature vectors per backend");
}
#[test]
fn all_official_nip44_conversation_vectors_both_backends() {
    for &(sk,pk,expected) in NIP44_VALID {
        let (sk,pk,expected)=(arr(sk),arr(pk),arr(expected));
        assert_eq!(rustcrypto::conversation(&sk,&pk),Some(expected));
        assert_eq!(libsecp::conversation(&sk,&pk),Some(expected));
    }
    for &(sk,pk) in NIP44_INVALID {
        let (sk,pk)=(arr(sk),arr(pk));
        assert!(rustcrypto::conversation(&sk,&pk).is_none());
        assert!(libsecp::conversation(&sk,&pk).is_none());
    }
    println!("NIP44 conversation key: {} valid and {} invalid vectors per backend",NIP44_VALID.len(),NIP44_INVALID.len());
}
#[test]
fn integration_traps_are_detected() {
    use k256::schnorr::{SigningKey, signature::Signer};
    let mut sk=[0u8;32]; sk[31]=3; let msg=[0u8;32]; let aux=[0u8;32];
    let key=SigningKey::from_slice(&sk).unwrap();
    let high_level:k256::schnorr::Signature=key.sign(&msg);
    assert_ne!(high_level.to_bytes(),rustcrypto::sign(&sk,&msg,&aux).unwrap());
    assert!(!rustcrypto::verify(&key.verifying_key().to_bytes().into(),&msg,&high_level.to_bytes()));
    let (sk,pk,expected)=NIP44_VALID[0];
    let key=secp256k1::SecretKey::from_secret_bytes(arr(sk)).unwrap();
    let mut sec1=[2u8;33]; sec1[1..].copy_from_slice(&hex(pk));
    let peer=secp256k1::PublicKey::from_byte_array_compressed(sec1).unwrap();
    let hashed=secp256k1::ecdh::SharedSecret::new(&peer,&key).to_secret_bytes();
    assert_ne!(nsealr_crypto_feasibility_spike::nip44_extract(&hashed),arr::<32>(expected));
    println!("Rejected integration traps: double hashing Nostr message; using default hashed libsecp ECDH for NIP44");
}
#[test]
fn host_type_sizes_are_not_target_peak_stack() {
    println!("HOST sizeof k256 SigningKey={} SecretKey={} ; libsecp Keypair={} SecretKey={}",core::mem::size_of::<k256::schnorr::SigningKey>(),core::mem::size_of::<k256::SecretKey>(),core::mem::size_of::<secp256k1::Keypair>(),core::mem::size_of::<secp256k1::SecretKey>());
}
