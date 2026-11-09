use super::*;

fn corpus() -> Value {
    serde_json::from_str(include_str!("../../../testdata/social-vectors.json")).unwrap()
}
fn event_template(event: &Value) -> String {
    json!({"created_at":event["created_at"],"kind":event["kind"],"tags":event["tags"],"content":event["content"]}).to_string()
}
fn rejects(event: &Value) {
    let mut owner = session();
    let calls = backend_calls();
    assert!(
        owner
            .begin_request(request(&event_template(event)).as_bytes(), Some(0))
            .is_err(),
        "{event}"
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
    assert_eq!(backend_calls(), calls);
    assert!(output.iter().all(|b| *b == 0));
}

#[test]
fn articles_and_generic_reposts_match_independent_full_event_vectors() {
    for event in corpus()["events"].as_array().unwrap() {
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
            .begin_request(request(&event_template(event)).as_bytes(), Some(0))
            .unwrap();
        let io = approve(&mut owner);
        if event["tags"]
            .as_array()
            .unwrap()
            .iter()
            .any(|tag| tag[0] == "-")
        {
            assert!(observed_value(&io, "Protected publication").contains("not encryption"));
        }
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
        if event["kind"] == 16 {
            let original: Value = serde_json::from_str(event["content"].as_str().unwrap()).unwrap();
            assert_eq!(
                observed_value(&io, "Original signed content"),
                inspection_quote(original["content"].as_str().unwrap())
            );
            for (tag, fields) in original["tags"].as_array().unwrap().iter().enumerate() {
                for (field, text) in fields.as_array().unwrap().iter().enumerate() {
                    assert_eq!(
                        observed_value(&io, &format!("Original signed tag {tag} field {field}:")),
                        inspection_quote(text.as_str().unwrap())
                    );
                }
            }
            assert!(observed_value(&io, "Operation and consequences").contains("does not execute"));
        } else {
            assert!(observed_value(&io, "Operation and consequences").contains("replace"));
            assert!(io.pages.iter().any(|p| p.0.contains("article identifier")));
        }
        let mut auxiliary = Aux::valid(0);
        let mut output = [0; SIGNED_EVENT_BYTES];
        let written = owner
            .sign_approved("r", &mut || Some(0), &mut auxiliary, &mut output)
            .unwrap();
        let actual: Value = serde_json::from_slice(&output[..written]).unwrap();
        assert_eq!(actual, *event);
        assert_eq!(auxiliary.calls, 1);
        assert!(owner
            .sign_approved(
                "r",
                &mut || panic!("spent clock"),
                &mut auxiliary,
                &mut output
            )
            .is_err());
        assert!(output.iter().all(|b| *b == 0));
    }
}

#[test]
fn protected_originals_cannot_be_embedded_by_either_repost_kind() {
    for original in corpus()["protectedOriginals"].as_array().unwrap() {
        let original_text = original.to_string();
        let checked = crate::event::SignedOriginal::parse(&original_text, limits()).unwrap();
        checked.verify().unwrap(); // Real independently signed original, not a bad-signature rejection.
        assert!(checked.verify_repost().is_err());
        let generic = original["kind"] != 1;
        let mut tags = json!([
            ["e", original["id"], "wss://relay.example"],
            ["p", original["pubkey"]]
        ]);
        if generic {
            tags.as_array_mut().unwrap().push(json!(["k", "30023"]));
            tags.as_array_mut()
                .unwrap()
                .push(json!(["a", format!("30023:{KEY}:protected")]));
        }
        let mut repost = json!({"created_at":0,"kind":if generic {16} else {6},"tags":tags,"content":original_text});
        rejects(&repost);
        repost["content"] = json!("");
        approved(&event_template(&repost)); // A reference does not redistribute the protected JSON.
    }
    for kind in [0, 1, 3, 30023] {
        let mut tags = if kind == 30023 {
            json!([["d", "x"]])
        } else {
            json!([])
        };
        tags.as_array_mut()
            .unwrap()
            .push(json!(["-", "not-a-valid-marker"]));
        rejects(
            &json!({"created_at":0,"kind":kind,"tags":tags,"content":if kind==0 {"{}"} else {""}}),
        );
    }
}

#[test]
fn article_ambiguity_and_invalid_known_references_fail_before_authority() {
    let good = corpus()["events"][4].clone();
    for tags in [
        json!([]),
        json!([["d"]]),
        json!([["d", "x", "suffix"]]),
        json!([["d", "x"], ["d", "x"]]),
        json!([["d", "x"], ["title", "A"], ["title", "B"]]),
        json!([["d", "x"], ["published_at", "01"]]),
        json!([["d", "x"], ["published_at", "-1"]]),
        json!([["d", "x"], ["published_at", "9007199254740992"]]),
        json!([["d", "x"], ["published_at", "18446744073709551616"]]),
        json!([["d", "x"], ["published_at", "1.0"]]),
        json!([["d", "x"], ["e", "a"]]),
        json!([["d", "x"], ["p", "0".repeat(64)]]),
        json!([["d", "x"], ["a", format!("1:{KEY}:invalid")]]),
        json!([
            ["d", "x"],
            ["q", "ab".repeat(32), "", KEY_ONE],
            ["q", "cd".repeat(32)]
        ]),
        json!([["d", "x"], ["t"]]),
    ] {
        let mut event = good.clone();
        event["tags"] = tags;
        rejects(&event);
    }
}

#[test]
fn generic_repost_checks_full_original_kind_identity_coordinate_and_duplicates() {
    let good = corpus()["events"][3].clone();
    for field in [
        "content",
        "created_at",
        "kind",
        "tags",
        "id",
        "sig",
        "pubkey",
    ] {
        let mut original: Value = serde_json::from_str(good["content"].as_str().unwrap()).unwrap();
        match field {
            "created_at" | "kind" => original[field] = json!(0),
            "tags" => original[field] = json!([["d", "other"]]),
            "pubkey" => original[field] = json!(KEY_ONE),
            _ => original[field] = json!("changed"),
        }
        let mut event = good.clone();
        event["content"] = json!(original.to_string());
        rejects(&event);
    }
    for tags in [
        json!([]),
        json!([["e", good["tags"][0][1], "wss://relay.example"]]),
        json!([["e", good["tags"][0][1], "wss://relay.example"], ["k", "1"]]),
        json!([["e", good["tags"][0][1], ""], ["k", "30023"]]),
        json!([
            ["e", good["tags"][0][1], "wss://relay.example"],
            ["k", "30023"],
            ["p", KEY_ONE]
        ]),
        json!([
            ["e", good["tags"][0][1], "wss://relay.example"],
            ["k", "30023"],
            ["a", format!("30023:{KEY}:wrong")]
        ]),
        json!([
            ["e", good["tags"][0][1], "wss://relay.example"],
            ["k", "30023"],
            ["a", format!("30023:{KEY_ONE}:article:日本")]
        ]),
    ] {
        let mut event = good.clone();
        event["tags"] = tags;
        rejects(&event);
    }
    for index in 0..4 {
        let mut event = good.clone();
        let duplicate = event["tags"][index].clone();
        event["tags"].as_array_mut().unwrap().push(duplicate);
        rejects(&event);
    }
    // Preserve the old kind-6 contract despite the shared original parser extension.
    let mut kind6 = good.clone();
    kind6["kind"] = json!(6);
    rejects(&kind6);
    let mut no_original = good.clone();
    no_original["content"] = json!("");
    approved(&event_template(&no_original));
    no_original["tags"].as_array_mut().unwrap().pop();
    rejects(&no_original); // Replaceable reference needs a coordinate or full original.
}
