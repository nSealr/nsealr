//! Deterministic public fixtures for the external nostr-tools oracle. Never use
//! these identities or nonces for private messages. This is a host-only example.
use nsealr_core::{nip19::SecretKey, nip44};
use serde_json::json;

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
fn identity(n: u8) -> (SecretKey, [u8; 32]) {
    let mut bytes = [0u8; 32];
    bytes[31] = n;
    let key = k256::schnorr::SigningKey::from_bytes((&bytes).into()).unwrap();
    let public = key.verifying_key().to_bytes().into();
    (SecretKey::take_from(&mut bytes).unwrap(), public)
}
fn main() {
    let lengths = [
        1, 31, 32, 33, 63, 64, 65, 127, 128, 129, 255, 256, 257, 511, 512, 513, 1023, 1024, 1025,
        2047, 2048, 2049, 2559, 2560, 2561, 3071, 3072, 3073, 3583, 3584, 3585, 4095, 4096,
    ];
    for case in 0..64u8 {
        let (alice, alice_public) = identity(case + 1);
        let (bob, bob_public) = identity(case + 65);
        let text = if case >= 60 {
            ["é\0\r\n", "中文 العربية", "👋 e\u{301}", "a"]
                .get((case - 60) as usize)
                .unwrap()
                .to_string()
        } else {
            "p".repeat(lengths[case as usize % lengths.len()])
        };
        let nonce = [case + 1; 32];
        let mut payload = [0u8; nip44::MAX_PAYLOAD_BYTES];
        let length = nip44::encrypt(&alice, &bob_public, &text, &nonce, &mut payload).unwrap();
        let payload = core::str::from_utf8(&payload[..length]).unwrap();
        let mut plaintext = zeroize::Zeroizing::new([0u8; nip44::MAX_PLAINTEXT_BYTES]);
        let length = nip44::decrypt(&bob, &alice_public, payload, &mut *plaintext).unwrap();
        assert_eq!(&plaintext[..length], text.as_bytes());
        println!(
            "{}",
            json!({"case":case,"alice":hex(&alice_public),"bob":hex(&bob_public),"nonce":hex(&nonce),"plaintext":text,"payload":payload})
        );
    }
}
