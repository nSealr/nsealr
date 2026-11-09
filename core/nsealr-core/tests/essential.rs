use nsealr_core::{
    event::{Event, CRITICAL, DETAIL, PRIVATE, PROSE},
    identity::Identity,
    json::{hex, hex_string},
    nip19, nip44,
    owner::Owner,
    qr, Error,
};
use serde_json::{json, Value};

fn scalar(value: u8) -> Identity {
    let mut bytes = [0; 32];
    bytes[31] = value;
    Identity::generate(0, &mut bytes, "", 0).unwrap()
}
fn request(id: &str, method: &str, params: Value) -> Vec<u8> {
    serde_json::to_vec(&json!({"id":id,"method":method,"params":params})).unwrap()
}
fn note(pubkey: &[u8; 32], text: &str) -> String {
    json!({"pubkey":hex_string(pubkey),"created_at":1700000000,"kind":1,"tags":[],"content":text})
        .to_string()
}
fn mark(owner: &mut Owner, mask: u32) {
    let generation = owner.generation();
    let fields: Vec<_> = owner
        .fields()
        .iter()
        .enumerate()
        .filter(|(_, f)| f.flags & mask != 0)
        .map(|(i, _)| i)
        .collect();
    for i in fields {
        owner.seen(generation, i).unwrap();
    }
}
fn result(owner: &Owner) -> Value {
    serde_json::from_str::<Value>(owner.response().unwrap()).unwrap()
}

#[test]
fn recovery_matches_independent_keys_and_all_word_counts() {
    let mut rows: Vec<Value> =
        serde_json::from_str(include_str!("../testdata/recovery/nip06-scure.json")).unwrap();
    let extra: Value =
        serde_json::from_str(include_str!("../../../tests/core/recovery-all-counts.json")).unwrap();
    rows.extend(extra["cases"].as_array().unwrap().clone());
    for row in rows {
        let identity = Identity::mnemonic(
            row["mnemonic"].as_str().unwrap(),
            row["passphrase"].as_str().unwrap(),
            row["account"].as_u64().unwrap() as u32,
        )
        .unwrap();
        assert_eq!(hex_string(&identity.public_key()), row["public_key"]);
        let mut secret = hex::<32>(row["private_key"].as_str().unwrap()).unwrap();
        let key = nip19::SecretKey::take_from(&mut secret).unwrap();
        let mut expected = [0; 83];
        let text = nip19::encode_nsec(&key, &mut expected).unwrap();
        let mut backup = [0; 256];
        let len = identity.backup(1, &mut backup).unwrap();
        assert_eq!(&backup[..len], text.as_bytes());
        let restored = Identity::nsec(text).unwrap();
        assert_eq!(restored.public_key(), identity.public_key());
        let len = identity.backup(2, &mut backup).unwrap();
        assert_eq!(&backup[..len], row["mnemonic"].as_str().unwrap().as_bytes());
    }
    assert!(Identity::mnemonic("abandon abandon abandon", "", 0).is_err());
    assert!(Identity::mnemonic("abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",&"x".repeat(257),0).is_err());
}

#[test]
fn generation_and_public_seedqr_backup_roundtrip() {
    let vectors: Value =
        serde_json::from_str(include_str!("../testdata/recovery/seedqr-published.json")).unwrap();
    for words in [12, 24] {
        let mut entropy = [7; 32];
        let id = Identity::generate(words, &mut entropy, "TREZOR", 1).unwrap();
        assert_eq!(entropy, [0; 32]);
        for (kind, compact) in [(3, false), (4, true)] {
            let mut out = [0; 128];
            let n = id.backup(kind, &mut out).unwrap();
            let recovered = Identity::seedqr(&out[..n], compact, "TREZOR", 1).unwrap();
            assert_eq!(id.public_key(), recovered.public_key());
        }
    }
    for row in vectors.as_array().unwrap() {
        let id = Identity::mnemonic(row["mnemonic"].as_str().unwrap(), "", 0).unwrap();
        let mut out = [0; 128];
        let n = id.backup(3, &mut out).unwrap();
        assert_eq!(&out[..n], row["standard"].as_str().unwrap().as_bytes());
        let n = id.backup(4, &mut out).unwrap();
        assert_eq!(hex_string(&out[..n]), row["compact_hex"]);
        let restored = Identity::seedqr(&out[..n], true, "", 0).unwrap();
        assert_eq!(restored.public_key(), id.public_key());
    }
}

#[test]
fn canonical_ids_and_signatures_match_independent_bip340_answers() {
    let data: Value = serde_json::from_str(include_str!(
        "../../../tests/core/authorization-vectors.json"
    ))
    .unwrap();
    let identity = scalar(3);
    for row in data["vectors"].as_array().unwrap() {
        let mut template: Value = serde_json::from_str(row["template"].as_str().unwrap()).unwrap();
        template["pubkey"] = row["pubkey"].clone();
        let event = Event::parse(template.to_string().as_bytes(), &identity.public_key()).unwrap();
        assert_eq!(hex_string(&event.id()), row["event_id"]);
        assert_eq!(
            hex_string(
                &identity
                    .sign(&event.id(), &hex(row["aux_hex"].as_str().unwrap()).unwrap())
                    .unwrap()
            ),
            row["signature"]
        );
    }
}

#[test]
fn review_partial_choice_cannot_skip_authority_and_approval_is_consumed() {
    let mut owner = Owner::default();
    owner.select(scalar(3));
    let pubkey = owner.identity().unwrap().public_key();
    let req = request("a", "sign_event", json!([note(&pubkey, "Full text café")]));
    owner.request(&req, 10).unwrap();
    assert_eq!(owner.confirmation().unwrap(), "Publish note");
    let generation = owner.generation();
    assert_eq!(
        owner.approve(generation, true, &mut [7; 32], 11),
        Err(Error::Review)
    );
    assert_eq!(
        owner.approve(generation, true, &mut [8; 32], 12),
        Err(Error::Stale)
    );
    owner.request(&req, 20).unwrap();
    mark(&mut owner, CRITICAL);
    let generation = owner.generation();
    owner.approve(generation, true, &mut [9; 32], 21).unwrap();
    let event: Value = serde_json::from_str(result(&owner)["result"].as_str().unwrap()).unwrap();
    assert_eq!(event["content"], "Full text café");
    owner.request(&req, 30).unwrap();
    mark(&mut owner, CRITICAL | PROSE);
    let generation = owner.generation();
    assert_eq!(
        owner.approve(generation, false, &mut [9; 32], 31),
        Err(Error::Entropy)
    );
    owner.request(&req, 40).unwrap();
    let stale = owner.generation();
    owner.cancel();
    assert_eq!(owner.confirmation(), Err(Error::Stale));
    assert_eq!(owner.seen(stale, 0), Err(Error::Stale));
    assert!(owner.response().is_err());
    owner.request(&req, 50).unwrap();
    mark(&mut owner, CRITICAL | PROSE);
    let generation = owner.generation();
    assert_eq!(
        owner.approve(generation, false, &mut [10; 32], 600_050),
        Err(Error::Stale)
    );
    owner.lock();
    assert!(owner.identity().is_err());
}

#[test]
fn malformed_unknown_and_wrong_identity_fail_before_review() {
    let mut owner = Owner::default();
    owner.select(scalar(3));
    let pubkey = owner.identity().unwrap().public_key();
    assert!(owner
        .request(
            br#"{"id":"a","id":"b","method":"get_public_key","params":[]}"#,
            1
        )
        .is_err());
    for template in [
        json!({"pubkey":hex_string(&pubkey),"created_at":1.5,"kind":1,"tags":[],"content":"hi"}),
        json!({"pubkey":hex_string(&pubkey),"created_at":1,"kind":999,"tags":[],"content":"hi"}),
        json!({"pubkey":hex_string(&pubkey),"created_at":1,"kind":1,"tags":[["unknown","x"]],"content":"hi"}),
        json!({"pubkey":hex_string(&scalar(2).public_key()),"created_at":1,"kind":1,"tags":[],"content":"hi"}),
    ] {
        assert!(owner
            .request(
                &request("a", "sign_event", json!([template.to_string()])),
                2
            )
            .is_err());
        assert!(owner.fields().is_empty());
    }
    assert!(
        nsealr_core::json::parse(format!("{}0{}", "[".repeat(17), "]".repeat(17)).as_bytes())
            .is_err()
    );
    assert!(nsealr_core::json::parse(format!("[{}[]]", "[],".repeat(2048)).as_bytes()).is_err());
}

#[test]
fn supported_actions_present_authority_and_exact_list_details() {
    let key = scalar(3).public_key();
    let peer = hex_string(&scalar(2).public_key());
    let cases = [
        (0, json!([]), r#"{"name":"Alice","about":"hello"}"#),
        (3, json!([["p", peer]]), ""),
        (5, json!([["e", "11".repeat(32)]]), "remove"),
        (6, json!([["e", "11".repeat(32)], ["p", peer]]), ""),
        (7, json!([["e", "11".repeat(32)], ["p", peer]]), "+"),
        (10002, json!([["r", "wss://relay.example", "read"]]), ""),
        (10050, json!([["relay", "wss://dm.example"]]), ""),
        (
            22242,
            json!([
                ["relay", "wss://relay.example"],
                ["challenge", "fresh challenge"]
            ]),
            "",
        ),
    ];
    for (kind, tags, content) in cases {
        let raw = json!({"pubkey":hex_string(&key),"created_at":1,"kind":kind,"tags":tags,"content":content});
        let event = Event::parse(raw.to_string().as_bytes(), &key).unwrap();
        let fields = event.review().unwrap();
        assert!(fields.iter().filter(|f| f.flags & CRITICAL != 0).count() >= 3);
        let mask = if [3, 10002, 10050].contains(&kind) {
            DETAIL
        } else {
            CRITICAL
        };
        for tag in tags.as_array().unwrap() {
            for value in tag.as_array().unwrap().iter().skip(1) {
                assert!(fields
                    .iter()
                    .filter(|f| f.flags & mask != 0)
                    .any(|f| f.value.contains(value.as_str().unwrap())));
            }
        }
    }
}

#[test]
fn whole_list_consent_is_bounded_and_signs_the_exact_ordered_list() {
    let mut owner = Owner::default();
    owner.select(scalar(3));
    let key = hex_string(&owner.identity().unwrap().public_key());
    let tags: Vec<_> = (0..256)
        .map(|n| json!(["p", format!("{n:064x}")]))
        .collect();
    let mut template =
        json!({"pubkey":key,"created_at":1700000000,"kind":3,"tags":tags,"content":""});
    owner
        .request(
            &request("list", "sign_event", json!([template.to_string()])),
            1,
        )
        .unwrap();
    assert_eq!(owner.confirmation().unwrap(), "Replace follows");
    assert_eq!(
        owner
            .fields()
            .iter()
            .filter(|f| f.flags & CRITICAL != 0)
            .count(),
        5
    );
    assert!(owner
        .fields()
        .iter()
        .any(|f| f.label == "List entries" && f.value.as_str() == "256" && f.flags == CRITICAL));
    mark(&mut owner, CRITICAL);
    owner
        .approve(owner.generation(), false, &mut [19; 32], 2)
        .unwrap();
    let signed: Value = serde_json::from_str(result(&owner)["result"].as_str().unwrap()).unwrap();
    assert_eq!(signed["tags"], template["tags"]);
    template["tags"][255] = json!(["unknown", "not a follow"]);
    assert!(owner
        .request(
            &request("bad", "sign_event", json!([template.to_string()])),
            3
        )
        .is_err());
    assert!(owner.fields().is_empty());
    assert_eq!(owner.confirmation(), Err(Error::Stale));
}

#[test]
fn qr_exact_maximum_reverse_duplicates_conflicts_and_cancel() {
    let message = vec![b'x'; 32768];
    let mut c = qr::Collector::default();
    let frames: Vec<_> = (0..message.len().div_ceil(384))
        .map(|i| qr::encode(&message, i).unwrap())
        .collect();
    assert_eq!(frames.len(), 86);
    for i in (1..86).rev() {
        assert!(c.accept(frames[i].as_bytes()).unwrap().is_none());
        assert!(c.accept(frames[i].as_bytes()).unwrap().is_none());
    }
    assert_eq!(&*c.accept(frames[0].as_bytes()).unwrap().unwrap(), &message);
    assert_eq!(c.received(), 0);
    c.accept(frames[0].as_bytes()).unwrap();
    assert!(c
        .accept(qr::encode(b"other", 0).unwrap().as_bytes())
        .is_err());
    assert_eq!(c.received(), 0);
    let bad = frames[0].replacen(":0:", ":00:", 1);
    assert!(c.accept(bad.as_bytes()).is_err());
    c.accept(frames[0].as_bytes()).unwrap();
    c.clear();
    assert_eq!(c.expected(), 0);
}

#[test]
fn official_nip44_payloads_and_modified_ciphertext_zero_output() {
    let data: Value = serde_json::from_str(include_str!(
        "../../../tests/core/nip44-official-vectors.json"
    ))
    .unwrap();
    for row in data["v2"]["valid"]["encrypt_decrypt"].as_array().unwrap() {
        let mut first = hex::<32>(row["sec1"].as_str().unwrap()).unwrap();
        let key = nip19::SecretKey::take_from(&mut first).unwrap();
        let mut second = hex::<32>(row["sec2"].as_str().unwrap()).unwrap();
        let peer = Identity::generate(0, &mut second, "", 0)
            .unwrap()
            .public_key();
        let mut out = vec![0; nip44::MAX_PAYLOAD_BYTES];
        let nonce = hex(row["nonce"].as_str().unwrap()).unwrap();
        let n = nip44::encrypt(
            &key,
            &peer,
            row["plaintext"].as_str().unwrap(),
            &nonce,
            &mut out,
        )
        .unwrap();
        assert_eq!(&out[..n], row["payload"].as_str().unwrap().as_bytes());
        let mut plain = vec![42; 8192];
        let n = nip44::decrypt(&key, &peer, row["payload"].as_str().unwrap(), &mut plain).unwrap();
        assert_eq!(&plain[..n], row["plaintext"].as_str().unwrap().as_bytes());
        let mut changed = row["payload"].as_str().unwrap().as_bytes().to_vec();
        changed[90] = if changed[90] == b'A' { b'B' } else { b'A' };
        assert!(nip44::decrypt(
            &key,
            &peer,
            core::str::from_utf8(&changed).unwrap(),
            &mut plain
        )
        .is_err());
        assert!(plain.iter().all(|b| *b == 0));
    }
}

#[test]
fn private_plaintext_is_reviewed_before_client_release() {
    for text in ["private café", r#"{"setting":"dark","nested":{"value":1}}"#] {
        let mut sender = Owner::default();
        sender.select(scalar(1));
        let peer = scalar(2).public_key();
        sender
            .request(
                &request("enc", "nip44_encrypt", json!([hex_string(&peer), text])),
                1,
            )
            .unwrap();
        assert!(sender.fields().iter().any(|f| f.flags & PRIVATE != 0));
        mark(&mut sender, CRITICAL | PROSE);
        let generation = sender.generation();
        sender.approve(generation, false, &mut [3; 32], 2).unwrap();
        let ciphertext = result(&sender)["result"].as_str().unwrap().to_owned();
        let mut receiver = Owner::default();
        receiver.select(scalar(2));
        receiver
            .request(
                &request(
                    "dec",
                    "nip44_decrypt",
                    json!([hex_string(&scalar(1).public_key()), ciphertext]),
                ),
                3,
            )
            .unwrap();
        assert!(receiver.response().is_err());
        assert!(receiver
            .fields()
            .iter()
            .any(|f| f.value.as_str() == text && f.flags & PRIVATE != 0));
        mark(&mut receiver, CRITICAL | PROSE);
        let generation = receiver.generation();
        receiver.approve(generation, false, &mut [], 4).unwrap();
        assert_eq!(result(&receiver)["result"], text);
    }
}

#[test]
fn qr_collection_binds_the_limit_and_handles_short_final_frames_first() {
    let data = vec![b'x'; 500];
    let first = qr::encode(&data, 0).unwrap();
    let last = qr::encode(&data, 1).unwrap();
    let mut collector = qr::Collector::default();
    assert!(collector
        .accept_limited(last.as_bytes(), 2048)
        .unwrap()
        .is_none());
    assert!(collector.accept(first.as_bytes()).is_err());
    assert_eq!(collector.received(), 0);
    assert!(collector
        .accept_limited(last.as_bytes(), 500)
        .unwrap()
        .is_none());
    assert_eq!(
        &**collector
            .accept_limited(first.as_bytes(), 500)
            .unwrap()
            .unwrap(),
        &data
    );
}
