use super::*;
use serde_json::Value;
use sha2::Digest;
use std::{string::String, vec, vec::Vec};

const VECTORS: &str = include_str!("../../../../tests/core/nip44-official-vectors.json");

fn vectors() -> Value {
    assert_eq!(
        Sha256::digest(VECTORS.as_bytes()).as_slice(),
        hex::<32>("269ed0f69e4c192512cc779e78c555090cebc7c785b609e338a62afc3ce25040")
    );
    serde_json::from_str(VECTORS).unwrap()
}
fn bytes(value: &str) -> Vec<u8> {
    assert_eq!(value.len() % 2, 0);
    (0..value.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&value[i..i + 2], 16).unwrap())
        .collect()
}
fn hex<const N: usize>(value: &str) -> [u8; N] {
    bytes(value).try_into().unwrap()
}
fn secret(value: &str) -> SecretKey {
    SecretKey::take_from(&mut hex(value)).unwrap()
}
fn public(secret: &SecretKey) -> [u8; 32] {
    k256::schnorr::SigningKey::from_bytes(secret.as_bytes().into())
        .unwrap()
        .verifying_key()
        .to_bytes()
        .into()
}
fn identity(n: u8) -> SecretKey {
    let mut input = [0; 32];
    input[31] = n;
    SecretKey::take_from(&mut input).unwrap()
}

#[test]
fn official_conversation_and_message_keys() {
    let vectors = vectors();
    let valid = &vectors["v2"]["valid"];
    let cases = valid["get_conversation_key"].as_array().unwrap();
    assert_eq!(cases.len(), 35);
    for case in cases {
        let key = conversation_key(
            &secret(case["sec1"].as_str().unwrap()),
            &hex(case["pub2"].as_str().unwrap()),
        )
        .unwrap();
        assert_eq!(*key, hex::<32>(case["conversation_key"].as_str().unwrap()));
    }
    let case = &valid["get_message_keys"];
    let key = hex(case["conversation_key"].as_str().unwrap());
    for row in case["keys"].as_array().unwrap() {
        let output = message_keys(&key, &hex(row["nonce"].as_str().unwrap()));
        assert_eq!(&output[..32], bytes(row["chacha_key"].as_str().unwrap()));
        assert_eq!(
            &output[32..44],
            bytes(row["chacha_nonce"].as_str().unwrap())
        );
        assert_eq!(&output[44..], bytes(row["hmac_key"].as_str().unwrap()));
    }
}

#[test]
fn official_encrypt_decrypt_vectors_and_device_bound() {
    let vectors = vectors();
    let valid = &vectors["v2"]["valid"];
    let cases = valid["encrypt_decrypt"].as_array().unwrap();
    assert_eq!(cases.len(), 10);
    let mut ciphertext = [0xa5; MAX_PAYLOAD_BYTES];
    let mut plaintext = [0xa5; MAX_PLAINTEXT_BYTES];
    for case in cases {
        let alice = secret(case["sec1"].as_str().unwrap());
        let bob = secret(case["sec2"].as_str().unwrap());
        let text = case["plaintext"].as_str().unwrap();
        let expected = case["payload"].as_str().unwrap();
        let nonce = hex(case["nonce"].as_str().unwrap());
        let length = encrypt(&alice, &public(&bob), text, &nonce, &mut ciphertext).unwrap();
        assert_eq!(&ciphertext[..length], expected.as_bytes());
        assert!(ciphertext[length..].iter().all(|&b| b == 0));
        let length = decrypt(&bob, &public(&alice), expected, &mut plaintext).unwrap();
        assert_eq!(&plaintext[..length], text.as_bytes());
        assert!(plaintext[length..].iter().all(|&b| b == 0));
        assert_eq!(
            *conversation_key(&alice, &public(&bob)).unwrap(),
            *conversation_key(&bob, &public(&alice)).unwrap()
        );
    }
    for row in valid["calc_padded_len"].as_array().unwrap() {
        let length = row[0].as_u64().unwrap() as usize;
        if length <= MAX_PLAINTEXT_BYTES {
            assert_eq!(padded_len(length), Ok(row[1].as_u64().unwrap() as usize));
        } else {
            assert_eq!(padded_len(length), Err(Error::InvalidInput));
        }
    }
    // Published 65535-byte cases are deliberately outside the declared device bound.
    for row in valid["encrypt_decrypt_long_msg"].as_array().unwrap() {
        let text = row["pattern"]
            .as_str()
            .unwrap()
            .repeat(row["repeat"].as_u64().unwrap() as usize);
        assert!(text.len() > MAX_PLAINTEXT_BYTES);
        ciphertext.fill(0xa5);
        assert_eq!(
            encrypt(
                &identity(1),
                &public(&identity(2)),
                &text,
                &[0; 32],
                &mut ciphertext
            ),
            Err(Error::InvalidInput)
        );
        assert!(ciphertext.iter().all(|&b| b == 0));
    }
}

#[test]
fn official_invalid_vectors_reach_the_actual_decrypt_path() {
    let vectors = vectors();
    let invalid = &vectors["v2"]["invalid"];
    for row in invalid["decrypt"].as_array().unwrap() {
        let key = hex(row["conversation_key"].as_str().unwrap());
        let mut output = [0; MAX_PLAINTEXT_BYTES];
        assert!(
            decrypt_inner(
                || Ok(Zeroizing::new(key)),
                row["payload"].as_str().unwrap(),
                &mut output
            )
            .is_err(),
            "{}",
            row["note"]
        );
        assert!(output.iter().all(|&b| b == 0));
    }
    for row in invalid["get_conversation_key"].as_array().unwrap() {
        let key: Result<[u8; 32], _> = bytes(row["sec1"].as_str().unwrap()).try_into();
        let peer: Result<[u8; 32], _> = bytes(row["pub2"].as_str().unwrap()).try_into();
        let result = key.map_err(|_| Error::InvalidKey).and_then(|mut key| {
            let key = SecretKey::take_from(&mut key).map_err(|_| Error::InvalidKey)?;
            let peer = peer.map_err(|_| Error::InvalidKey)?;
            conversation_key(&key, &peer)
        });
        assert!(result.is_err(), "{}", row["note"]);
    }
    for length in invalid["encrypt_msg_lengths"].as_array().unwrap() {
        assert_eq!(
            padded_len(length.as_u64().unwrap() as usize),
            Err(Error::InvalidInput)
        );
    }
}

#[test]
fn padding_boundaries_unicode_and_maximum_payload() {
    for n in 1..=MAX_PLAINTEXT_BYTES {
        let padded = padded_len(n).unwrap();
        assert!(padded >= n && padded <= MAX_PLAINTEXT_BYTES);
        if n > 1 {
            assert!(padded >= padded_len(n - 1).unwrap());
        }
    }
    let alice = identity(3);
    let bob = identity(5);
    let mut encoded = [0; MAX_PAYLOAD_BYTES];
    let mut output = [0; MAX_PLAINTEXT_BYTES];
    for size in [
        1, 2, 31, 32, 33, 63, 64, 65, 127, 128, 129, 255, 256, 257, 511, 512, 513, 1023, 1024,
        1025, 2047, 2048, 2049, 2559, 2560, 2561, 3071, 3072, 3073, 3583, 3584, 3585, 4095, 4096,
    ] {
        let message = "x".repeat(size);
        let length = encrypt(&alice, &public(&bob), &message, &[7; 32], &mut encoded).unwrap();
        if size == MAX_PLAINTEXT_BYTES {
            assert_eq!(length, MAX_PAYLOAD_BYTES);
        }
        let size_out = decrypt(
            &bob,
            &public(&alice),
            core::str::from_utf8(&encoded[..length]).unwrap(),
            &mut output,
        )
        .unwrap();
        assert_eq!(&output[..size_out], message.as_bytes());
    }
    for message in ["hello 👋", "é e\u{301}\0\r\n", "中文 العربية"] {
        let n = encrypt(&alice, &public(&bob), message, &[8; 32], &mut encoded).unwrap();
        let len = decrypt(
            &bob,
            &public(&alice),
            core::str::from_utf8(&encoded[..n]).unwrap(),
            &mut output,
        )
        .unwrap();
        assert_eq!(&output[..len], message.as_bytes());
    }
    assert_eq!(padded_len(usize::MAX), Err(Error::InvalidInput));
}

#[test]
fn complete_envelope_boundary_keeps_authentication_and_cleanup() {
    let alice = identity(1);
    let bob = identity(2);
    let message = "é".repeat(2048);
    assert_eq!(message.len(), 4096);
    assert_eq!(MAX_PAYLOAD_BYTES, 5552);
    let mut encoded = [0xa5; MAX_PAYLOAD_BYTES];
    let length = encrypt(&alice, &public(&bob), &message, &[9; 32], &mut encoded).unwrap();
    assert_eq!(length, 5552);
    let payload = core::str::from_utf8(&encoded).unwrap();
    let mut output = [0xa5; MAX_PLAINTEXT_BYTES + 32];
    let n = decrypt(&bob, &public(&alice), payload, &mut output).unwrap();
    assert_eq!(&output[..n], message.as_bytes());
    assert!(output[n..].iter().all(|&b| b == 0));
    output.fill(0xa5);
    assert_eq!(
        decrypt(&bob, &public(&alice), payload, &mut output[..4095]),
        Err(Error::OutputTooSmall)
    );
    assert!(output[..4095].iter().all(|&b| b == 0));
    assert!(output[4095..].iter().all(|&b| b == 0xa5));
    assert_eq!(
        decrypt(&identity(3), &public(&alice), payload, &mut output),
        Err(Error::Authentication)
    );
    assert!(output.iter().all(|&b| b == 0));
    let mut binary = [0; MAX_BINARY_BYTES];
    let length = Base64::decode(payload, &mut binary).unwrap().len();
    binary[length - 1] ^= 1;
    let payload = Base64::encode(&binary[..length], &mut encoded).unwrap();
    assert_eq!(
        decrypt(&bob, &public(&alice), payload, &mut []),
        Err(Error::Authentication)
    );
    encoded.fill(0xa5);
    assert_eq!(
        encrypt(
            &alice,
            &public(&bob),
            &(message + "a"),
            &[9; 32],
            &mut encoded
        ),
        Err(Error::InvalidInput)
    );
    assert!(encoded.iter().all(|&b| b == 0));
}

#[test]
fn modified_binary_and_wrong_peer_never_release_plaintext() {
    let alice = identity(1);
    let bob = identity(2);
    let mut encoded = [0; MAX_PAYLOAD_BYTES];
    let n = encrypt(
        &alice,
        &public(&bob),
        "public fixture",
        &[11; 32],
        &mut encoded,
    )
    .unwrap();
    let payload = core::str::from_utf8(&encoded[..n]).unwrap();
    let mut binary = [0; MAX_BINARY_BYTES];
    let len = Base64::decode(payload, &mut binary).unwrap().len();
    let mut output = [0xa5; MAX_PLAINTEXT_BYTES];
    assert_eq!(
        decrypt(&identity(3), &public(&alice), payload, &mut output),
        Err(Error::Authentication)
    );
    assert!(output.iter().all(|&b| b == 0));
    for i in 0..len {
        for bit in [1, 128] {
            binary[i] ^= bit;
            let payload = Base64::encode(&binary[..len], &mut encoded).unwrap();
            output.fill(0xa5);
            assert!(decrypt(&bob, &public(&alice), payload, &mut output).is_err());
            assert!(output.iter().all(|&b| b == 0));
            binary[i] ^= bit;
        }
    }
}

#[test]
fn early_rejection_buffers_and_utf8() {
    let alice = identity(1);
    let bob = identity(2);
    let mut encoded = [0; MAX_PAYLOAD_BYTES];
    let n = encrypt(&alice, &public(&bob), "a", &[12; 32], &mut encoded).unwrap();
    let payload = String::from_utf8(encoded[..n].to_vec()).unwrap();
    let mut small = [0xa5; 1];
    assert_eq!(
        encrypt(&alice, &public(&bob), "a", &[12; 32], &mut small),
        Err(Error::OutputTooSmall)
    );
    assert_eq!(small, [0]);
    assert_eq!(
        decrypt(&bob, &public(&alice), &payload, &mut []),
        Err(Error::OutputTooSmall)
    );
    assert_eq!(
        decrypt_inner(
            || panic!("oversize input must reject before ECDH"),
            &"A".repeat(MAX_PAYLOAD_BYTES + 4),
            &mut small
        ),
        Err(Error::InvalidInput)
    );
    assert_eq!(
        decrypt(&bob, &public(&alice), "#future", &mut small),
        Err(Error::UnsupportedVersion)
    );
    let mut binary = [0; MAX_BINARY_BYTES];
    let len = Base64::decode(&payload, &mut binary).unwrap().len();
    // A MAC-valid sender can encrypt malformed UTF-8. Reject before copying it out.
    binary[35] ^= b'a' ^ 0xff;
    let nonce = binary[1..33].try_into().unwrap();
    let keys = message_keys(&conversation_key(&alice, &public(&bob)).unwrap(), &nonce);
    let end = len - 32;
    let tag = mac(&keys[44..], &nonce, &binary[33..end])
        .finalize()
        .into_bytes();
    binary[end..len].copy_from_slice(&tag);
    let payload = Base64::encode(&binary[..len], &mut encoded).unwrap();
    let mut output = vec![0xa5; 32];
    assert_eq!(
        decrypt(&bob, &public(&alice), payload, &mut output),
        Err(Error::InvalidInput)
    );
    assert!(output.iter().all(|&b| b == 0));
}
