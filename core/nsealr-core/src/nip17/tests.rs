use super::*;
use serde_json::{json, Value};
use std::{string::String, vec::Vec};

const FIXTURES: &str = include_str!("../../testdata/nip17-receive.json");

fn hex_bytes<const N: usize>(text: &str) -> [u8; N] {
    fixed_hex(text.as_bytes()).unwrap()
}
fn fixtures() -> Value {
    assert_eq!(
        crate::hash::sha256_hex(FIXTURES.as_bytes()).as_slice(),
        b"b5fd0dccaa51cc7a9a4ebf8fe08770e456d3c7064bb61bed7a429366a6bb2b40"
    );
    serde_json::from_str(FIXTURES).unwrap()
}
fn key(case: &Value) -> SecretKey {
    SecretKey::take_from(&mut hex_bytes(case["local_secret"].as_str().unwrap())).unwrap()
}
fn dirty(workspace: &mut ReceiveWorkspace) {
    workspace.seal.fill(0xa5);
    workspace.rumor.fill(0xa5);
    workspace.content.fill(0xa5);
}
fn cleared(workspace: &ReceiveWorkspace) {
    assert!(workspace.seal.iter().all(|b| *b == 0));
    assert!(workspace.rumor.iter().all(|b| *b == 0));
    assert!(workspace.content.iter().all(|b| *b == 0));
}

#[test]
fn independent_nostr_tools_and_published_layer_vectors() {
    let data = fixtures();
    let cases = data["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 84);
    let mut workspace = ReceiveWorkspace::new();
    let mut accepted = 0;
    for case in cases {
        dirty(&mut workspace);
        let result = receive(
            &key(case),
            case["gift_wrap"].as_str().unwrap().as_bytes(),
            &mut workspace,
        );
        if case["accept"] == true {
            let message = result.unwrap_or_else(|e| panic!("{}: {e:?}", case["name"]));
            accepted += 1;
            let expected = &case["expected"];
            assert_eq!(
                message.sender(),
                &hex_bytes::<32>(expected["sender"].as_str().unwrap())
            );
            assert_eq!(
                message.recipient(),
                &hex_bytes::<32>(expected["recipient"].as_str().unwrap())
            );
            assert_eq!(
                message.rumor_id(),
                &hex_bytes::<32>(expected["rumor_id"].as_str().unwrap())
            );
            assert_eq!(
                message.gift_wrap_id(),
                &hex_bytes::<32>(expected["gift_wrap_id"].as_str().unwrap())
            );
            assert_eq!(
                message.created_at(),
                expected["created_at"].as_u64().unwrap()
            );
            assert_eq!(message.content(), expected["content"].as_str().unwrap());
            assert_eq!(
                message.is_sender_copy(),
                expected["sender_copy"].as_bool().unwrap()
            );
            let mut tags: Vec<Vec<String>> = Vec::new();
            message
                .visit_tags(&mut |tag, field, text| {
                    if field == 0 {
                        assert_eq!(tags.len(), tag);
                        tags.push(Vec::new());
                    }
                    assert_eq!(tags[tag].len(), field);
                    tags[tag].push(String::from(text));
                    Ok(())
                })
                .unwrap();
            assert_eq!(json!(tags), expected["tags"]);
            assert!(message.workspace.seal.iter().all(|b| *b == 0));
            assert!(message.workspace.rumor[message.metadata.rumor_len..]
                .iter()
                .all(|b| *b == 0));
            assert!(message.workspace.content[message.metadata.content_len..]
                .iter()
                .all(|b| *b == 0));
            drop(message);
        } else {
            assert!(result.is_err(), "unexpected acceptance: {}", case["name"]);
            drop(result);
        }
        cleared(&workspace);
    }
    assert_eq!(accepted, 22);
}

#[test]
fn every_truncation_invalid_utf8_and_replacement_clear_complete_workspace() {
    let data = fixtures();
    let case = &data["cases"][1];
    let key = key(case);
    let raw = case["gift_wrap"].as_str().unwrap().as_bytes();
    let mut workspace = ReceiveWorkspace::new();
    for end in 0..raw.len() {
        dirty(&mut workspace);
        assert!(
            receive(&key, &raw[..end], &mut workspace).is_err(),
            "prefix {end}"
        );
        cleared(&workspace);
    }
    for input in [&b"\xff"[..], &b"\"\xff\""[..], &b"{}\xff"[..]] {
        dirty(&mut workspace);
        assert!(receive(&key, input, &mut workspace).is_err());
        cleared(&workspace);
    }
    for _ in 0..3 {
        let message = receive(&key, raw, &mut workspace).unwrap();
        assert_eq!(message.content(), "x");
        drop(message); // Cancellation/expiry/rebinding by the future owner drops this view.
        cleared(&workspace);
        assert!(receive(&key, b"{}", &mut workspace).is_err());
        cleared(&workspace);
    }
    dirty(&mut workspace);
    workspace.clear();
    cleared(&workspace);
}

#[test]
fn private_inspection_failure_and_unwind_release_no_transport_authority() {
    let data = fixtures();
    let case = &data["cases"][1];
    let key = key(case);
    let input = case["gift_wrap"].as_str().unwrap().as_bytes();
    let mut workspace = ReceiveWorkspace::new();
    let message = receive(&key, input, &mut workspace).unwrap();
    assert_eq!(
        message.visit_tags(&mut |_, _, _| Err(EventError::Shape)),
        Err(EventError::Shape)
    );
    drop(message);
    cleared(&workspace);
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let message = receive(&key, input, &mut workspace).unwrap();
        message
            .visit_tags(&mut |_, _, _| panic!("synthetic private renderer failure"))
            .unwrap();
    }));
    assert!(result.is_err());
    cleared(&workspace);
}

#[test]
fn private_bounds_are_separate_and_ordinary_request_limits_unchanged() {
    assert_eq!(core::mem::size_of::<ReceiveWorkspace>(), 8704);
    let limits = crate::event::OperationLimits::conformance();
    assert_eq!(limits.input_bytes, 4096);
    assert!(crate::event::OperationLimits {
        input_bytes: 8192,
        ..limits
    }
    .validate()
    .is_err());
    assert_eq!(MAX_GIFT_WRAP_BYTES, 8192);
    assert_eq!(MAX_SEAL_BYTES, nip44::MAX_PLAINTEXT_BYTES);
    assert_eq!(MAX_MESSAGE_BYTES, 2048);
}

#[test]
fn expiration_identifiers_refuse_at_every_layer_without_a_time_policy() {
    let fixture = include_str!("../../testdata/nip17-expiration.json");
    assert_eq!(
        crate::hash::sha256_hex(fixture.as_bytes()).as_slice(),
        b"0135b9fcd8b246f904f3f906401e007e44f13bcb45bf71afe09931d0872e23d7"
    );
    let data: Value = serde_json::from_str(fixture).unwrap();
    let cases = data["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 28);
    let mut workspace = ReceiveWorkspace::new();
    let mut unexpected_accepts = Vec::new();
    for case in cases {
        dirty(&mut workspace);
        let result = receive(
            &key(case),
            case["gift_wrap"].as_str().unwrap().as_bytes(),
            &mut workspace,
        );
        if case["accept"] == true {
            assert!(result.is_ok(), "control must remain valid");
        } else if result.is_ok() {
            unexpected_accepts.push(String::from(case["name"].as_str().unwrap()));
        }
        drop(result);
        cleared(&workspace);
    }
    assert!(
        unexpected_accepts.is_empty(),
        "unsupported expiration authenticated: {unexpected_accepts:?}"
    );
}
