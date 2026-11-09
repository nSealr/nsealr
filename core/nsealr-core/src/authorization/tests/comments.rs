use super::*;

fn corpus() -> Value {
    serde_json::from_str(include_str!("../../../testdata/comment-vectors.json")).unwrap()
}
fn template(event: &Value) -> String {
    json!({"created_at":event["created_at"],"kind":event["kind"],"tags":event["tags"],"content":event["content"]}).to_string()
}

#[test]
fn comments_preserve_complete_fields_and_independent_signatures() {
    for case in corpus()["positive"].as_array().unwrap() {
        let event = &case["event"];
        let mut owner = AuthorizationSession::new(
            limits(),
            InspectionGeometry {
                columns: 16,
                lines: 8,
            },
        )
        .unwrap();
        owner.select_key(secret(3)).unwrap();
        owner
            .begin_request(request(&template(event)).as_bytes(), Some(0))
            .unwrap_or_else(|error| panic!("{}: {error:?}", case["name"]));
        let io = approve(&mut owner);
        std::println!("comment case={} pages={}", case["name"], io.pages.len() + 1);
        assert!(observed_value(&io, "Operation and consequences").contains("comment"));
        assert_eq!(
            observed_value(&io, "Signed content:"),
            inspection_quote(event["content"].as_str().unwrap())
        );
        for (tag, fields) in event["tags"].as_array().unwrap().iter().enumerate() {
            for (field, text) in fields.as_array().unwrap().iter().enumerate() {
                assert_eq!(
                    observed_value(&io, &format!("Signed tag {tag} field {field}:")),
                    inspection_quote(text.as_str().unwrap())
                );
            }
        }
        if case["name"] == "nested-file-with-mentions" {
            let labels = io
                .pages
                .iter()
                .map(|page| page.0.as_str())
                .collect::<Vec<_>>();
            assert!(labels
                .iter()
                .any(|label| label.contains("tag 5 field 1:")
                    && label.contains("mentioned public key")));
            assert!(labels
                .iter()
                .any(|label| label.contains("tag 6 field 1:")
                    && label.contains("claimed parent author")));
            assert!(labels
                .iter()
                .any(|label| label.contains("tag 7 field 1:")
                    && label.contains("mentioned public key")));
        }
        for (label, body, _, _) in &io.pages {
            // label has been rejoined by the common test observer; body retains wrapping.
            assert!(!label.is_empty());
            assert!(body.lines().all(|line| line.len() <= 16));
        }
        let mut auxiliary = Aux::valid(0);
        let mut output = [0xa5; SIGNED_EVENT_BYTES];
        let written = owner
            .sign_approved("r", &mut || Some(0), &mut auxiliary, &mut output)
            .unwrap();
        assert_eq!(
            serde_json::from_slice::<Value>(&output[..written]).unwrap(),
            *event,
            "{}",
            case["name"]
        );
        assert_eq!(auxiliary.calls, 1);
        assert!(owner
            .sign_approved(
                "r",
                &mut || panic!("spent clock"),
                &mut auxiliary,
                &mut output
            )
            .is_err());
        assert!(output.iter().all(|byte| *byte == 0));
    }
}

#[test]
fn comment_cancel_lock_expiry_and_size_never_reuse_approval() {
    let c = corpus();
    let good = &c["positive"][0]["event"];
    for stop in ["cancel", "lock", "expiry"] {
        let mut owner = approved(&template(good));
        if stop == "cancel" {
            owner.cancel();
        }
        if stop == "lock" {
            owner.lock().unwrap();
        }
        let before = backend_calls();
        let mut auxiliary = Aux::valid(0);
        let mut output = [0xa5; SIGNED_EVENT_BYTES];
        assert!(owner
            .sign_approved("r", &mut || Some(101), &mut auxiliary, &mut output)
            .is_err());
        assert_eq!(before, backend_calls());
        assert_eq!(auxiliary.calls, 0);
        assert!(output.iter().all(|byte| *byte == 0));
    }
    let mut huge = good.clone();
    huge["content"] = json!("x".repeat(limits().content_bytes + 1));
    assert!(session()
        .begin_request(request(&template(&huge)).as_bytes(), Some(0))
        .is_err());
    let mut bounded = limits();
    bounded.review_pages = 2;
    let mut owner = AuthorizationSession::new(bounded, geometry()).unwrap();
    owner.select_key(secret(3)).unwrap();
    assert!(owner
        .begin_request(request(&template(good)).as_bytes(), Some(0))
        .is_err());
}

#[test]
fn external_comment_url_and_scope_shape_are_bounded_and_unambiguous() {
    for target in [
        "https://example.com/\"quote",
        "https://example.com/<html>",
        "https://example.com/`code`",
        "https://example.com/%",
        "https://example.com/%a",
        "https://example.com/%zz",
        "https://example.com/%0D",
        "https://example.com/%5C",
        "https://example.com/#part",
        "https://name:password@example.com/",
        "https:///missing",
        "https://Example.com/",
        "https://127.1/",
        "https://0177.0.0.1/",
        "https://[not-ip]/",
        "https://[::1]suffix/",
        "https://example.com:0/",
        "https://example.com:65536/",
        "https://example.com:080/",
        "https://example..com/",
        "https://-example.com/",
        "https://example.com/has space",
    ] {
        let event = json!({"created_at":0,"kind":1111,"content":"URL must reject","tags":[["I",target],["K","web"],["i",target],["k","web"]]});
        assert!(
            session()
                .begin_request(request(&template(&event)).as_bytes(), Some(0))
                .is_err(),
            "{target}"
        );
    }
    let good = &corpus()["positive"][7]["event"];
    for tag in ["I", "K", "i", "k"] {
        let mut event = good.clone();
        let repeated = event["tags"]
            .as_array()
            .unwrap()
            .iter()
            .find(|t| t[0] == tag)
            .unwrap()
            .clone();
        event["tags"].as_array_mut().unwrap().push(repeated);
        assert!(session()
            .begin_request(request(&template(&event)).as_bytes(), Some(0))
            .is_err());
    }
}

#[test]
fn complete_utf8_comment_fits_the_proposed_public_review_page_bound() {
    let mut event = corpus()["positive"][1]["event"].clone();
    event["content"] = json!("é".repeat(1024));
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
        .begin_request(request(&template(&event)).as_bytes(), Some(0))
        .unwrap();
    let io = approve(&mut owner);
    assert_eq!(
        observed_value(&io, "Signed content:"),
        inspection_quote(event["content"].as_str().unwrap())
    );
    assert!(io.pages.len() < 256);
    std::println!(
        "maximum UTF8 comment: content_bytes=2048 pages={}; host geometry only",
        io.pages.len() + 1
    );
}

#[test]
fn contradictory_comments_fail_before_consent_or_backend_use() {
    for case in corpus()["negative"].as_array().unwrap() {
        let mut owner = session();
        let before = backend_calls();
        assert!(
            owner
                .begin_request(request(&template(&case["event"])).as_bytes(), Some(0))
                .is_err(),
            "{}",
            case["name"]
        );
        let mut auxiliary = Aux::valid(0);
        let mut output = [0xa5; SIGNED_EVENT_BYTES];
        assert!(owner
            .sign_approved(
                "r",
                &mut || panic!("rejected clock"),
                &mut auxiliary,
                &mut output
            )
            .is_err());
        assert_eq!(auxiliary.calls, 0);
        assert_eq!(backend_calls(), before);
        assert!(output.iter().all(|byte| *byte == 0));
    }
}
