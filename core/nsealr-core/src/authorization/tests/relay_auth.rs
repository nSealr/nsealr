use super::*;

fn corpus() -> Value {
    serde_json::from_str(include_str!("../../../testdata/relay-auth-vectors.json")).unwrap()
}
fn event_template(event: &Value) -> String {
    json!({"created_at":event["created_at"],"kind":event["kind"],"tags":event["tags"],"content":event["content"]}).to_string()
}

#[test]
fn relay_auth_complete_review_matches_independent_signatures() {
    for case in corpus()["positive"].as_array().unwrap() {
        let event = &case["event"];
        let mut bounded = limits();
        bounded.review_pages = 256;
        let mut owner = AuthorizationSession::new(
            bounded,
            InspectionGeometry {
                columns: 16,
                lines: 8,
            },
        )
        .unwrap();
        owner.select_key(secret(3)).unwrap();
        owner
            .begin_request(request(&event_template(event)).as_bytes(), Some(0))
            .unwrap_or_else(|error| panic!("{}: {error:?}", case["name"]));
        let io = approve(&mut owner);
        let consequences = observed_value(&io, "Operation and consequences");
        assert!(consequences.contains("relay"));
        assert!(consequences.contains("not a public note"));
        assert_eq!(observed_value(&io, "Signed content:"), inspection_quote(""));
        for (tag, fields) in event["tags"].as_array().unwrap().iter().enumerate() {
            for (field, text) in fields.as_array().unwrap().iter().enumerate() {
                assert_eq!(
                    observed_value(&io, &format!("Signed tag {tag} field {field}:")),
                    inspection_quote(text.as_str().unwrap())
                );
            }
        }
        let insecure = event["tags"]
            .as_array()
            .unwrap()
            .iter()
            .any(|tag| tag[0] == "relay" && tag[1].as_str().unwrap().starts_with("ws://"));
        assert_eq!(
            io.pages
                .iter()
                .any(|page| page.0.starts_with("Unencrypted relay transport")),
            insecure
        );
        std::println!("relay-auth {} pages={}", case["name"], io.pages.len() + 1);
        let mut output = [0xa5; SIGNED_EVENT_BYTES];
        let mut aux = Aux::valid(0);
        let n = owner
            .sign_approved("r", &mut || Some(0), &mut aux, &mut output)
            .unwrap();
        assert_eq!(
            serde_json::from_slice::<Value>(&output[..n]).unwrap(),
            *event
        );
        assert_eq!(aux.calls, 1);
        assert!(owner
            .sign_approved("r", &mut || panic!("spent clock"), &mut aux, &mut output)
            .is_err());
        assert_eq!(aux.calls, 1);
        assert!(output.iter().all(|b| *b == 0));
    }
}

#[test]
fn relay_auth_refuses_ambiguous_or_extended_authority_before_review() {
    for case in corpus()["negative"].as_array().unwrap() {
        let mut owner = session();
        let before = backend_calls();
        assert!(
            owner
                .begin_request(request(&event_template(&case["event"])).as_bytes(), Some(0))
                .is_err(),
            "{}",
            case["name"]
        );
        let mut aux = Aux::valid(0);
        let mut output = [0xa5; SIGNED_EVENT_BYTES];
        assert!(owner
            .sign_approved("r", &mut || panic!("rejected clock"), &mut aux, &mut output)
            .is_err());
        assert_eq!(backend_calls(), before);
        assert_eq!(aux.calls, 0);
        assert!(output.iter().all(|b| *b == 0));
    }
}

#[test]
fn relay_auth_cancellation_lock_expiry_and_changed_request_do_not_reuse_consent() {
    let event = corpus()["positive"][0]["event"].clone();
    for stop in ["cancel", "lock", "expiry", "request-id"] {
        let mut owner = approved(&event_template(&event));
        if stop == "cancel" {
            owner.cancel();
        }
        if stop == "lock" {
            owner.lock().unwrap();
        }
        let before = backend_calls();
        let mut aux = Aux::valid(0);
        let mut output = [0xa5; SIGNED_EVENT_BYTES];
        assert!(owner
            .sign_approved(
                if stop == "request-id" { "changed" } else { "r" },
                &mut || Some(if stop == "expiry" { 101 } else { 0 }),
                &mut aux,
                &mut output
            )
            .is_err());
        assert_eq!(backend_calls(), before);
        assert_eq!(aux.calls, 0);
        assert!(output.iter().all(|b| *b == 0));
    }
    let mut owner = approved(&event_template(&event));
    let mut replacement = event.clone();
    replacement["tags"][1][1] = json!("replacement-challenge");
    assert!(matches!(
        owner.begin_request(request(&event_template(&replacement)).as_bytes(), Some(0)),
        Err(AuthorizationError::Busy)
    ));
    owner.cancel();
    owner
        .begin_request(request(&event_template(&replacement)).as_bytes(), Some(0))
        .unwrap();
    let mut aux = Aux::valid(0);
    let mut output = [0xa5; SIGNED_EVENT_BYTES];
    assert!(owner
        .sign_approved("r", &mut || Some(0), &mut aux, &mut output)
        .is_err());
    assert_eq!(aux.calls, 0);
    assert!(output.iter().all(|b| *b == 0));
}

#[test]
fn relay_auth_refuses_incomplete_review_budget() {
    let mut bounded = limits();
    bounded.review_pages = 2;
    let mut owner = AuthorizationSession::new(bounded, geometry()).unwrap();
    owner.select_key(secret(3)).unwrap();
    assert!(owner
        .begin_request(
            request(&event_template(&corpus()["positive"][0]["event"])).as_bytes(),
            Some(0)
        )
        .is_err());
}
