use nsealr_core::{
    event::{Event, CRITICAL, PRIVATE, PROSE},
    identity::Identity,
    json::{hex, hex_string},
    owner::{Owner, LIFETIME_MS},
    qr, Error,
};
use serde_json::{json, Value};

fn identity(n: u8) -> Identity {
    let mut bytes = [0; 32];
    bytes[31] = n;
    Identity::generate(0, &mut bytes, "", 0).unwrap()
}
fn owner(n: u8) -> Owner {
    let mut owner = Owner::default();
    owner.select(identity(n));
    owner
}
fn request(method: &str, params: Value) -> Vec<u8> {
    serde_json::to_vec(&json!({"id":"private-test","method":method,"params":params})).unwrap()
}
fn mark(owner: &mut Owner, flags: u32) {
    for index in 0..owner.fields().len() {
        if owner.fields()[index].flags & flags != 0 {
            owner.seen(owner.generation(), index).unwrap();
        }
    }
}
fn approve(owner: &mut Owner, now: u64) -> String {
    mark(owner, CRITICAL | PROSE);
    owner
        .approve(owner.generation(), false, &mut [now as u8; 32], now)
        .unwrap();
    let value: Value = serde_json::from_str(owner.response().unwrap()).unwrap();
    value["result"].as_str().unwrap().into()
}
fn rumor(text: &str, tags: Value) -> String {
    let mut value = json!({"pubkey":hex_string(&identity(1).public_key()),"created_at":1700000000,"kind":14,"tags":tags,"content":text});
    let event = Event::parse(value.to_string().as_bytes(), &identity(1).public_key()).unwrap();
    value["id"] = hex_string(&event.id()).into();
    value.to_string()
}
fn standard_rumor(text: &str) -> String {
    rumor(text, json!([["p", hex_string(&identity(2).public_key())]]))
}
fn encrypt(owner: &mut Owner, rumor: &str, peer: u8, now: u64) -> String {
    owner
        .request(
            &request(
                "nip44_encrypt",
                json!([hex_string(&identity(peer).public_key()), rumor]),
            ),
            now,
        )
        .unwrap();
    approve(owner, now + 1)
}
fn seal(ciphertext: &str) -> Vec<u8> {
    let template = json!({"pubkey":hex_string(&identity(1).public_key()),"created_at":1699999000,"kind":13,"tags":[],"content":ciphertext});
    request("sign_event", json!([template.to_string()]))
}

#[test]
fn independent_seals_authenticate_before_any_plaintext_release() {
    // Independent nostr-tools2.23.3/Noble corpus, with public keys and provenance.
    let corpus: Value =
        serde_json::from_str(include_str!("../testdata/nip17-selected.json")).unwrap();
    for row in corpus["cases"].as_array().unwrap() {
        let mut secret = hex(row["local_secret"].as_str().unwrap()).unwrap();
        let mut owner = Owner::default();
        owner.select(Identity::generate(0, &mut secret, "", 0).unwrap());
        let wrap: Value = serde_json::from_str(row["gift_wrap"].as_str().unwrap()).unwrap();
        let opened = owner.request(
            &request("nip44_decrypt", json!([wrap["pubkey"], wrap["content"]])),
            1,
        );
        if row["accept"] == false {
            assert!(opened.is_err(), "{}", row["name"]);
            assert!(owner.fields().is_empty());
            let response: Value = serde_json::from_str(owner.response().unwrap()).unwrap();
            assert!(response.get("result").is_none());
            continue;
        }
        opened.unwrap();
        assert!(owner.response().is_err());
        for label in ["Message author", "Message recipient", "Private message"] {
            assert!(owner
                .fields()
                .iter()
                .any(|f| f.label == label && f.flags & PRIVATE != 0));
        }
        let signed: Value = serde_json::from_str(&approve(&mut owner, 2)).unwrap();
        assert_eq!(signed["pubkey"], row["expected"]["sender"]);
        owner.finish_response();
        assert!(owner.response().is_err());
        let next = request(
            "nip44_decrypt",
            json!([signed["pubkey"], signed["content"]]),
        );
        for index in 0..next.len().div_ceil(384) {
            owner
                .receive_frame(qr::encode(&next, index).unwrap().as_bytes(), 3)
                .unwrap();
        }
        assert!(owner.response().is_err());
        let opened: Value = serde_json::from_str(&approve(&mut owner, 4)).unwrap();
        assert_eq!(opened["id"], row["expected"]["rumor_id"]);
        assert_eq!(opened["content"], row["expected"]["content"]);
        assert!(owner.request(&next, 5).is_err(), "receipt cannot replay");

        // A scan-first gift wrap cannot renew its receipt after loading a key.
        owner
            .resume(
                &request("nip44_decrypt", json!([wrap["pubkey"], wrap["content"]])),
                LIFETIME_MS - 2,
                LIFETIME_MS,
            )
            .unwrap();
        approve(&mut owner, LIFETIME_MS - 1);
        owner.finish_response();
        assert_eq!(owner.tick(LIFETIME_MS), Ok(true));
        assert!(owner.request(&next, LIFETIME_MS + 1).is_err());
    }
}

#[test]
fn two_copy_interleaving_accepts_actual_client_tags_and_binds_exact_ciphertext() {
    let a = hex_string(&identity(1).public_key());
    let b = hex_string(&identity(2).public_key());
    let text = rumor(
        "Private café",
        json!([
            ["p", a],
            ["p", b],
            ["client", "noStrudel"],
            ["subject", "Dinner"]
        ]),
    );
    let mut sender = owner(1);
    let remote = encrypt(&mut sender, &text, 2, 1);
    sender.finish_response();
    let local = encrypt(&mut sender, &text, 1, 3);
    for (cipher, time) in [(&remote, 5), (&local, 7)] {
        sender.request(&seal(cipher), time).unwrap();
        assert!(sender
            .fields()
            .iter()
            .any(|f| f.value.as_str() == "Private café" && f.flags & PRIVATE != 0));
        let signed: Value = serde_json::from_str(&approve(&mut sender, time + 1)).unwrap();
        assert_eq!(signed["content"], cipher.as_str());
        let key =
            k256::schnorr::VerifyingKey::from_bytes((&identity(1).public_key()).into()).unwrap();
        let sig = hex::<64>(signed["sig"].as_str().unwrap()).unwrap();
        key.verify_raw(
            &hex::<32>(signed["id"].as_str().unwrap()).unwrap(),
            &k256::schnorr::Signature::try_from(sig.as_slice()).unwrap(),
        )
        .unwrap();
    }
    assert_eq!(sender.request(&seal(&remote), 9), Err(Error::Stale));
    let remote = encrypt(&mut sender, &text, 2, 10);
    let mut changed = remote.clone();
    changed.replace_range(30..31, if &remote[30..31] == "A" { "B" } else { "A" });
    assert_eq!(sender.request(&seal(&changed), 12), Err(Error::Stale));
    assert_eq!(sender.request(&seal(&remote), 13), Err(Error::Stale));
}

#[test]
fn cancel_replacement_failure_lock_and_expiry_destroy_private_receipts() {
    for action in 0..7 {
        let mut sender = owner(1);
        let cipher = encrypt(&mut sender, &standard_rumor("hello"), 2, 1);
        match action {
            0 => sender.cancel(),
            1 => {
                sender.lock();
                sender.select(identity(1));
            }
            2 => {
                assert!(sender.request(b"invalid", 3).is_err());
            }
            3 => {
                sender
                    .request(&request("get_public_key", json!([])), 3)
                    .unwrap();
                sender.finish_response();
            }
            4 => {
                sender.request(&seal(&cipher), 3).unwrap();
                assert_eq!(
                    sender.approve(sender.generation(), true, &mut [4; 32], 4),
                    Err(Error::Review)
                );
            }
            5 => {
                sender.request(&seal(&cipher), 3).unwrap();
                sender.request(&seal(&cipher), 4).unwrap_err();
            }
            6 => {
                sender.request(&seal(&cipher), LIFETIME_MS + 1).unwrap_err();
            }
            _ => unreachable!(),
        }
        let now = if action == 6 { LIFETIME_MS + 2 } else { 5 };
        assert_eq!(
            sender.request(&seal(&cipher), now),
            Err(Error::Stale),
            "action {action}"
        );
    }
}

#[test]
fn private_review_never_skips_recipient_and_flow_limits_fail_closed() {
    let mut sender = owner(1);
    let text = standard_rumor("hello");
    let req = request(
        "nip44_encrypt",
        json!([hex_string(&identity(2).public_key()), text]),
    );
    sender.request(&req, 1).unwrap();
    mark(&mut sender, PROSE);
    assert_eq!(
        sender.approve(sender.generation(), true, &mut [1; 32], 2),
        Err(Error::Review)
    );
    sender.request(&req, 3).unwrap();
    mark(&mut sender, CRITICAL);
    sender
        .approve(sender.generation(), true, &mut [2; 32], 4)
        .unwrap();
    encrypt(&mut sender, &text, 1, 5);
    assert_eq!(sender.request(&req, 7), Err(Error::Bounds));
    let mut large: Value = serde_json::from_str(&text).unwrap();
    large["content"] = "x".repeat(4097).into();
    assert_eq!(
        sender.request(
            &request(
                "nip44_encrypt",
                json!([hex_string(&identity(2).public_key()), large.to_string()])
            ),
            8
        ),
        Err(Error::Bounds)
    );
    let group = rumor(
        "hello",
        json!([
            ["p", hex_string(&identity(2).public_key())],
            ["p", hex_string(&identity(3).public_key())]
        ]),
    );
    assert_eq!(
        sender.request(
            &request(
                "nip44_encrypt",
                json!([hex_string(&identity(2).public_key()), group])
            ),
            9
        ),
        Err(Error::Unsupported)
    );
    assert_eq!(
        sender.request(
            &request(
                "nip44_encrypt",
                json!([hex_string(&identity(3).public_key()), text])
            ),
            10
        ),
        Err(Error::Identity)
    );
}

#[test]
fn periodic_expiry_clears_receipts_pending_output_and_scan() {
    let mut sender = owner(1);
    let cipher = encrypt(&mut sender, &standard_rumor("hello"), 2, 1);
    sender.finish_response();
    assert_eq!(sender.tick(LIFETIME_MS), Ok(false));
    assert_eq!(sender.tick(LIFETIME_MS + 1), Ok(true));
    assert_eq!(
        sender.request(&seal(&cipher), LIFETIME_MS + 2),
        Err(Error::Stale)
    );
    sender.cancel();
    let next = request("get_public_key", json!([]));
    sender.request(&next, LIFETIME_MS + 3).unwrap();
    assert_eq!(sender.tick(2 * LIFETIME_MS + 3), Ok(true));
    assert!(sender.fields().is_empty());
    sender.request(&next, 2 * LIFETIME_MS + 4).unwrap();
    approve(&mut sender, 2 * LIFETIME_MS + 5);
    assert_eq!(sender.tick(3 * LIFETIME_MS + 4), Ok(true));
    assert!(sender.response().is_err());
    sender
        .receive_frame(
            qr::encode(&vec![b'x'; 512], 0).unwrap().as_bytes(),
            3 * LIFETIME_MS + 5,
        )
        .unwrap();
    assert_eq!(sender.tick(4 * LIFETIME_MS + 5), Ok(true));
    assert_eq!(sender.collector.received(), 0);
    assert!(sender.identity().is_ok());
    assert_eq!(sender.tick(0), Err(Error::Stale));
}
