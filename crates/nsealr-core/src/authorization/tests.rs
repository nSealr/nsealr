use super::*;
use crate::event::EventTemplate;
use serde_json::{json, Value};
use std::{
    format,
    string::{String, ToString},
    vec,
    vec::Vec,
};
const KEY: &str = "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9";
const KEY_ONE: &str = "79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798";
const EMPTY: &str = r#"{"created_at":0,"kind":1,"tags":[],"content":""}"#;
fn limits() -> OperationLimits {
    OperationLimits::conformance()
}
fn geometry() -> InspectionGeometry {
    InspectionGeometry {
        columns: 32,
        lines: 8,
    }
}
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
fn secret(n: u8) -> SecretKey {
    let mut raw = [0; 32];
    raw[31] = n;
    let key = SecretKey::take_from(&mut raw).unwrap();
    assert_eq!(raw, [0; 32]);
    key
}
fn request(template: &str) -> String {
    format!(
        r#"{{"version":1,"request_id":"r","method":"sign_event","params":{{"event_template":{template}}}}}"#
    )
}
fn template(content: &str, tags: Value) -> String {
    json!({"created_at":0,"kind":1,"tags":tags,"content":content}).to_string()
}
fn session() -> AuthorizationSession {
    let mut s = AuthorizationSession::new(limits(), geometry()).unwrap();
    s.select_key(secret(3)).unwrap();
    s
}
#[derive(Default)]
struct Io {
    input: Option<LocalInput>,
    fail: bool,
    tick: u64,
    after: Option<u64>,
    calls: usize,
    pages: Vec<(String, String, usize, usize)>,
}
impl LocalReviewIo for Io {
    fn now(&mut self) -> Option<u64> {
        Some(if self.calls > 0 {
            self.after.unwrap_or(self.tick)
        } else {
            self.tick
        })
    }
    fn present(&mut self, frame: LocalPresentation<'_>) -> Result<LocalInput, LocalDisplayError> {
        self.calls += 1;
        if self.fail {
            return Err(LocalDisplayError);
        }
        let default = match frame {
            LocalPresentation::Data(f) => {
                assert!(f
                    .label()
                    .lines()
                    .chain(f.body().lines())
                    .all(|line| line.len() <= 32));
                assert!(f.label().lines().count() + f.body().lines().count() < 8);
                assert_eq!(f.position(), format!("{}/{}", f.index() + 1, f.total()));
                self.pages.push((
                    f.label().replace('\n', ""),
                    f.body().to_string(),
                    f.index(),
                    f.total(),
                ));
                LocalInput::Next
            }
            LocalPresentation::Decision(f) => {
                assert!(f.label().starts_with("Decision"));
                assert_eq!(f.body(), "\"Approve?\"");
                assert_eq!(f.index() + 1, f.total());
                LocalInput::Approve
            }
        };
        Ok(self.input.take().unwrap_or(default))
    }
}
fn approve(s: &mut AuthorizationSession) -> Io {
    let mut io = Io::default();
    for _ in 0..1026 {
        if s.state() == AuthorizationState::Approved {
            return io;
        }
        s.review_step(&mut io).unwrap();
    }
    panic!("review did not terminate")
}
fn approved(t: &str) -> AuthorizationSession {
    let mut s = session();
    s.begin_request(request(t).as_bytes(), Some(0)).unwrap();
    approve(&mut s);
    s
}
fn sign(key: &SigningKey, id: &[u8; 32]) -> Result<[u8; 64], AuthorizationError> {
    key.sign_raw(id, &[0; 32])
        .map(|s| s.to_bytes())
        .map_err(|_| AuthorizationError::Backend)
}
fn request_bytes(template: &[u8]) -> Vec<u8> {
    let mut out =
        br#"{"version":1,"request_id":"r","method":"sign_event","params":{"event_template":"#
            .to_vec();
    out.extend_from_slice(template);
    out.extend_from_slice(b"}}");
    out
}
fn serial_rejects(json: &[u8]) -> bool {
    use crate::{
        base64url::encode_base64url,
        protocol::{development_device_protocol_context, handle_serial_frame},
        serial::frame::{decode_serial_frame, encode_serial_frame, FrameType},
    };
    let mut payload = [0; 1024];
    let mut line = [0; 1024];
    let Ok(payload) = encode_base64url(json, &mut payload) else {
        return true;
    };
    let Ok(line) = encode_serial_frame(FrameType::Request, payload, &mut line) else {
        return true;
    };
    match handle_serial_frame(line, &development_device_protocol_context()) {
        Ok(result) => {
            decode_serial_frame(result.as_bytes()).unwrap().frame_type == FrameType::Error
        }
        Err(_) => true,
    }
}
fn parsed(text: &str) -> EventTemplate {
    EventTemplate::parse(text.as_bytes(), limits()).unwrap()
}
fn accepted(tags: Value) -> bool {
    validate_kind1(&parsed(&template("", tags))).is_ok()
}

#[test]
fn s03_identity_is_derived_from_consumed_custody() {
    let mut s = session();
    assert_eq!(hex(&s.public_key().unwrap()), KEY);
    let mut one = AuthorizationSession::new(limits(), geometry()).unwrap();
    one.select_key(secret(1)).unwrap();
    assert_eq!(
        hex(&one.public_key().unwrap()),
        "79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
    );
    // Odd-Y n-3 imports the opposite point but k256 retains the normalized scalar 3.
    let mut odd = [0xff; 32];
    odd.copy_from_slice(&[
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 254, 186, 174,
        220, 230, 175, 72, 160, 59, 191, 210, 94, 140, 208, 54, 65, 62,
    ]);
    s.begin_request(request(EMPTY).as_bytes(), Some(0)).unwrap();
    approve(&mut s);
    let generation = s.account;
    s.select_key(SecretKey::take_from(&mut odd).unwrap())
        .unwrap();
    assert_eq!(odd, [0; 32]);
    assert_eq!(s.account, generation + 1);
    assert_eq!(hex(&s.public_key().unwrap()), KEY);
    assert_eq!(s.state(), AuthorizationState::Idle);
    assert!(s.attempt_sign("r", Some(0)).is_err());
    let normalized = s.key.as_ref().unwrap().to_bytes();
    assert_eq!(normalized[31], 3);
    assert!(normalized[..31].iter().all(|b| *b == 0));
    s.begin_request(request(EMPTY).as_bytes(), Some(0)).unwrap();
    approve(&mut s);
    let sig = s.execute("r", Some(0), sign).unwrap();
    let mut even = approved(EMPTY);
    assert_eq!(sig, even.execute("r", Some(0), sign).unwrap());
    for mut raw in [[0; 32], [0xff; 32]] {
        assert!(SecretKey::take_from(&mut raw).is_err());
        assert_eq!(raw, [0; 32]);
    }
    if let Ok(path) = std::env::var("S03_OBSERVED") {
        let rows = json!([
            {"scalar":"1","pubkey":hex(&one.public_key().unwrap()),"normalized_backend":hex(&one.key.as_ref().unwrap().to_bytes())},
            {"scalar":"3","pubkey":hex(&even.public_key().unwrap()),"normalized_backend":hex(&even.key.as_ref().unwrap().to_bytes())},
            {"scalar":"n-3","pubkey":hex(&s.public_key().unwrap()),"normalized_backend":hex(&normalized),"empty_event_signature":hex(&sig)}]);
        std::fs::write(
            std::path::Path::new(&path).with_extension("keys.json"),
            serde_json::to_vec_pretty(&rows).unwrap(),
        )
        .unwrap();
    }
    assert_eq!(
        s.select_key(SecretKey::empty()),
        Err(AuthorizationError::Key)
    );
    assert_eq!(s.state(), AuthorizationState::Locked);
}

#[test]
fn s03_rejects_duplicate_and_incomplete_json() {
    let good = request(EMPTY);
    assert_eq!(request_bytes(EMPTY.as_bytes()), good.as_bytes());
    assert!(!serial_rejects(good.as_bytes()));
    let bad = [
        good.replace("\"version\":1", "\"version\":1,\"v\\u0065rsion\":1"),
        good.replace("\"kind\":1", "\"kind\":1,\"k\\u0069nd\":2"),
        good.replace(
            "\"event_template\":",
            &format!("\"event_template\":{EMPTY},\"event_template\":"),
        ),
        good.replace(
            "\"params\":",
            &format!("\"params\":{{\"event_template\":{EMPTY}}},\"p\\u0061rams\":"),
        ),
        good.replace("\"kind\":1,", ""),
        good.replace("\"tags\":[]", "\"tags\":[],\"pubkey\":\"x\""),
        format!("{good}{{}}"),
        format!("{good}\0"),
        good.replace("\"kind\":1,", "\"kind\":1"),
        good.replace("\"content\":\"\"", "\"content\":\"\","),
        good.replace("\"params\":{", "\"params\":{\"other\":{},"),
        "{}".to_string(),
        "[]".to_string(),
        format!("\u{feff}{good}"),
    ];
    for input in bad {
        assert!(
            ParsedRequest::parse(input.as_bytes(), limits()).is_err(),
            "{input}"
        );
        assert!(crate::qr::envelope::parse_qr_signing_request(input.as_bytes()).is_err());
        assert!(serial_rejects(input.as_bytes()));
    }
    let reordered=r#" {"params":{"event_template":{"content":"","tags":[],"kind":1,"created_at":0}},"method":"sign_event","request_id":"r","version":1} \n"#.replace("\\n","\n");
    let a = ParsedRequest::parse(good.as_bytes(), limits()).unwrap();
    let b = ParsedRequest::parse(reordered.as_bytes(), limits()).unwrap();
    assert_eq!(
        a.event.unwrap().event_id(&[1; 32]),
        b.event.unwrap().event_id(&[1; 32])
    );
    for suffix in [",", ",]", ",}", "\\", "true", "null"] {
        assert!(ParsedRequest::parse(format!("{good}{suffix}").as_bytes(), limits()).is_err());
    }
    let max_id = good.replace(
        "\"request_id\":\"r\"",
        &format!("\"request_id\":\"{}\"", "a".repeat(128)),
    );
    assert!(ParsedRequest::parse(max_id.as_bytes(), limits()).is_ok());
    for id in [
        "".to_string(),
        "bad id".to_string(),
        "é".to_string(),
        "a".repeat(129),
    ] {
        let bad = good.replace("\"request_id\":\"r\"", &format!("\"request_id\":\"{id}\""));
        assert!(ParsedRequest::parse(bad.as_bytes(), limits()).is_err());
        assert!(serial_rejects(bad.as_bytes()));
    }
}

#[test]
fn s03_integer_tokens_and_kinds_are_exact() {
    for token in [
        "-1",
        "-0",
        "+1",
        "01",
        "1.0",
        "1e0",
        "NaN",
        "Infinity",
        "true",
        "null",
        "\"1\"",
        "18446744073709551616",
        "",
    ] {
        for field in ["created_at", "kind"] {
            let t = EMPTY.replace(
                &format!("\"{field}\":{}", if field == "kind" { 1 } else { 0 }),
                &format!("\"{field}\":{token}"),
            );
            assert!(EventTemplate::parse(t.as_bytes(), limits()).is_err(), "{t}");
            assert!(serial_rejects(request(&t).as_bytes()));
        }
        assert!(ParsedRequest::parse(
            request(EMPTY)
                .replace("\"version\":1", &format!("\"version\":{token}"))
                .as_bytes(),
            limits()
        )
        .is_err());
    }
    for kind in [0, 1, 65535] {
        let t = EMPTY.replace("\"kind\":1", &format!("\"kind\":{kind}"));
        let e = parsed(&t);
        assert_eq!(e.kind(), kind);
        assert_eq!(validate_kind1(&e).is_ok(), kind == 1);
    }
    assert!(EventTemplate::parse(
        EMPTY.replace("\"kind\":1", "\"kind\":65536").as_bytes(),
        limits()
    )
    .is_err());
    assert_eq!(
        parsed(&EMPTY.replace("\"created_at\":0", "\"created_at\":9007199254740991")).created_at(),
        9007199254740991
    );
    assert!(EventTemplate::parse(
        EMPTY
            .replace("\"created_at\":0", "\"created_at\":9007199254740992")
            .as_bytes(),
        limits()
    )
    .is_err());
    for version in [0, 2] {
        assert!(ParsedRequest::parse(
            request(EMPTY)
                .replace("\"version\":1", &format!("\"version\":{version}"))
                .as_bytes(),
            limits()
        )
        .is_err());
    }
}

#[test]
fn s03_unicode_decode_is_lossless_or_rejected() {
    let raw = template("é😀e\u{301}", json!([]));
    let escaped = raw.replace("é😀e\u{301}", "\\u00e9\\ud83d\\ude00e\\u0301");
    assert_eq!(parsed(&raw).content(), parsed(&escaped).content());
    for bytes in [
        &[0xc0, 0x80][..],
        &[0xed, 0xa0, 0x80],
        &[0xf4, 0x90, 0x80, 0x80],
        &[0xe2, 0x82],
        &[0xff],
    ] {
        let mut input = b"{\"created_at\":0,\"kind\":1,\"tags\":[],\"content\":\"".to_vec();
        input.extend_from_slice(bytes);
        input.extend_from_slice(b"\"}");
        assert!(EventTemplate::parse(&input, limits()).is_err());
        let envelope = request_bytes(&input);
        assert!(crate::qr::envelope::parse_qr_signing_request(&envelope).is_err());
        assert!(serial_rejects(&envelope));
    }
    for bad in [
        "\\ud800",
        "\\udfff",
        "\\ude00\\ud83d",
        "\\uD800x",
        "\\uZZZZ",
        "\\u12",
        "\\q",
        "\n",
        "\t",
        "\0",
    ] {
        let t = EMPTY.replace("\"content\":\"\"", &format!("\"content\":\"{bad}\""));
        assert!(EventTemplate::parse(t.as_bytes(), limits()).is_err(), "{t}");
        assert!(serial_rejects(request(&t).as_bytes()));
    }
    let composed = parsed(&template("é", json!([])));
    let decomposed = parsed(&template("e\u{301}", json!([])));
    assert_ne!(composed.event_id(&[1; 32]), decomposed.event_id(&[1; 32]));
    assert_eq!(
        parsed(&template("\0\u{10ffff}", json!([]))).content(),
        "\0\u{10ffff}"
    );
}

fn vectors() -> Value {
    serde_json::from_str(include_str!(concat!(env!("OUT_DIR"), "/s03-vectors.json"))).unwrap()
}
#[test]
fn s03_nip01_bytes_match_independent_oracle() {
    let key = session().public_key().unwrap();
    for vector in vectors()["vectors"].as_array().unwrap() {
        let event = parsed(vector["template"].as_str().unwrap());
        let mut bytes = [0; 8192];
        let len = event.write_canonical(&key, &mut bytes).unwrap();
        assert_eq!(
            hex(&bytes[..len]),
            vector["canonical_hex"].as_str().unwrap()
        );
        assert_eq!(
            hex(&event.event_id(&key).unwrap()),
            vector["event_id"].as_str().unwrap()
        );
    }
    let all_controls: String = (0..32).map(char::from).collect();
    let event = parsed(&template(&all_controls, json!([])));
    let mut out = [0; 8192];
    let len = event.write_canonical(&key, &mut out).unwrap();
    let text = core::str::from_utf8(&out[..len]).unwrap();
    assert!(text.contains("\\u0000"));
    assert!(text.contains("\\b\\t\\n\\u000b\\f\\r"));
    assert!(text.contains("\\u001f"));
    assert!(event.write_canonical(&key, &mut [0; 5]).is_err());
}

#[test]
fn s03_every_event_mutation_changes_authorized_operation() {
    let key = session().public_key().unwrap();
    let base = parsed(&template("a", json!([["t", "x"], ["t", "y"]])))
        .event_id(&key)
        .unwrap();
    for t in [
        template("b", json!([["t", "x"], ["t", "y"]])),
        template("a", json!([["t", "y"], ["t", "x"]])),
        template("a", json!([["t", "x"], ["t", "y"], ["t", "y"]])),
        template("a", json!([["t", "x", ""], ["t", "y"]])),
        template("a", json!([["t", "x"], ["t", "y"]]))
            .replace("\"created_at\":0", "\"created_at\":1"),
    ] {
        assert_ne!(parsed(&t).event_id(&key).unwrap(), base);
    }
    assert_ne!(
        parsed(&template("a", json!([["t", "x"], ["t", "y"]])))
            .event_id(&[2; 32])
            .unwrap(),
        base
    );
}

#[test]
fn s03_kind1_interprets_exact_reference_subset() {
    assert!(!accepted(json!([[
        "q",
        format!("30023:{KEY}:x"),
        "",
        KEY_ONE
    ]])));
    assert!(accepted(json!([["p", KEY]])));
    let a = "a".repeat(64);
    let b = "b".repeat(64);
    for tags in [
        json!([]),
        json!([["e", a]]),
        json!([["e", a], ["e", b]]),
        json!([["e", a, "", "root", KEY, "extra"]]),
        json!([["e", a, "", "root"], ["e", b, "", "reply"]]),
        json!([["p", KEY, "", "alias"]]),
        json!([["q", a, "", KEY, "extension"]]),
        json!([["q", format!("30023:{KEY}:identifier:with:colons"), ""]]),
        json!([["q", format!("0:{KEY}:"), "", KEY]]),
        json!([["unknown", "x", ""], ["t", "x"], ["t", "x"]]),
    ] {
        assert!(accepted(tags.clone()), "{tags}");
        let reviewed = approved(&template("", tags));
        assert_eq!(reviewed.state(), AuthorizationState::Approved);
    }
    for tags in [
        json!([["e"]]),
        json!([["p"]]),
        json!([["q", a]]),
        json!([["q", a, ""]]),
        json!([["e", "A".repeat(64)]]),
        json!([["p", "0".repeat(64)]]),
        json!([["e", a, "", "mention"]]),
        json!([["e", a, "", "reply"]]),
        json!([["e", a, "", "root"], ["e", a, "", "reply"]]),
        json!([["e", a, "", "root"], ["e", b, "", "root"]]),
        json!([["e", a, "", "root"], ["e", b]]),
        json!([
            ["e", a, "", "root"],
            ["e", b, "", "reply"],
            ["e", b, "", "reply"]
        ]),
        json!([["e", a, "", "root", "bad"]]),
        json!([["emoji", "x", "https://x"]]),
        json!([["q", format!("01:{KEY}:"), ""]]),
        json!([["q", format!("0:{KEY}:not-empty"), ""]]),
        json!([["q", format!("20000:{KEY}:"), ""]]),
        json!([["q", format!("30023:{KEY}"), ""]]),
        json!([["q", format!("30023:{KEY}:x"), "", "0".repeat(64)]]),
    ] {
        assert!(!accepted(tags.clone()), "{tags}");
    }
    for kind in [0, 3, 4, 5, 7, 9735, 10002, 1059, 22242, 30023, 65535] {
        let t = EMPTY.replace("\"kind\":1", &format!("\"kind\":{kind}"));
        let mut s = session();
        assert!(s.begin_request(request(&t).as_bytes(), Some(0)).is_err());
    }
}

#[test]
fn s03_malformed_known_semantics_never_fall_back() {
    for uri in [
        "",
        "ws://example.com",
        "wss://Relay.Example:443/a%2Fb?q",
        "wss://127.0.0.1:1/",
        "ws://a-b.test/~!$&'()*+,;=:@/%20",
    ] {
        let expected = !uri.contains('?');
        assert_eq!(accepted(json!([["p", KEY, uri]])), expected, "{uri}");
    }
    for uri in [
        "http://x",
        "wss://",
        "wss://user@x",
        "wss://x?x",
        "wss://x/#x",
        "wss://x/\\x",
        "wss://é.test",
        "wss://[::1]",
        "wss://-x",
        "wss://x-",
        "wss://x..y",
        "wss://x.",
        "wss://x:0",
        "wss://x:01",
        "wss://x:65536",
        "wss://x:9999999999999999999999999",
        "wss://x:a",
        "wss://x/a%",
        "wss://x/a%GG",
        "wss://x/space here",
        "wss://x/é",
        "wss://256.0.0.1",
        "wss://01.0.0.1",
        "wss://1.2.3",
    ] {
        assert!(!accepted(json!([["p", KEY, uri]])), "{uri}");
    }
    assert!(!accepted(json!([[
        "p",
        KEY,
        format!("wss://{}", "a".repeat(64))
    ]])));
    let input = template("", json!([["p", KEY, "wss://Relay.Example/a%2fb"]]));
    let event = parsed(&input);
    assert_eq!(
        event.tag(0).unwrap().nth(2).unwrap(),
        "wss://Relay.Example/a%2fb"
    );
}

#[test]
fn s03_review_has_complete_indexed_coverage() {
    let content = "\"\\ literal \\u{202E} actual \u{202e}\u{200d} é e\u{301} 😀\n\r\t\0\x08\x0c  ";
    let mut s = session();
    s.begin_request(
        request(&template(content, json!([["unknown", "a", "", "tail"]]))).as_bytes(),
        Some(0),
    )
    .unwrap();
    let io = approve(&mut s);
    let joined: String = io
        .pages
        .iter()
        .filter(|p| p.0.starts_with("Signed content"))
        .map(|p| p.1.replace('\n', ""))
        .collect();
    assert_eq!(joined,"\"\\\"\\\\ literal \\\\u{202E} actual \\u{202E}\\u{200D} \\u{E9} e\\u{301} \\u{1F600}\\n\\r\\t\\u{0}\\b\\f  \"");
    assert!(io
        .pages
        .iter()
        .any(|p| p.0.contains("field 2") && p.1 == "\"\""));
    assert!(io
        .pages
        .iter()
        .any(|p| p.0.contains("field 3") && p.1 == "\"tail\""));
    assert!(io
        .pages
        .iter()
        .any(|p| p.0.contains("meaning not verified")));
    assert!(io
        .pages
        .iter()
        .any(|p| p.0.starts_with("Selected actual signing identity")));
    for (i, p) in io.pages.iter().enumerate() {
        assert_eq!(p.2, i);
        assert_eq!(p.3, io.pages.len() + 1);
        assert!(p.1.is_ascii());
        assert!(!p.1.contains("..."));
    }
}

#[test]
fn s03_review_escape_spelling_is_injective() {
    let mut s = session();
    s.configure(
        limits(),
        InspectionGeometry {
            columns: 16,
            lines: 8,
        },
    )
    .unwrap();
    let content = "a😀\u{10ffff}tail".repeat(100);
    s.begin_request(request(&template(&content, json!([]))).as_bytes(), Some(0))
        .unwrap();
    let io = approve(&mut s);
    let pages: Vec<_> = io
        .pages
        .iter()
        .filter(|p| p.0.starts_with("Signed content"))
        .collect();
    assert!(pages.len() > 20);
    for p in &pages {
        assert!(p.1.lines().all(|line| line.len() <= 16));
        if p.1.contains("\\u{") {
            assert!(p.1.contains('}'));
        }
    }
    let joined: String = pages.into_iter().map(|p| p.1.replace('\n', "")).collect();
    assert_eq!(
        joined,
        format!("\"{}\"", "a\\u{1F600}\\u{10FFFF}tail".repeat(100))
    );
    assert!(joined.ends_with("tail\""));
}

#[test]
fn s03_failed_or_skipped_display_cannot_approve() {
    let mut s = session();
    s.begin_request(request(EMPTY).as_bytes(), Some(0)).unwrap();
    {
        let p = s.pending.as_ref().unwrap();
        let doc = s.document(p);
        assert!(doc.frame(p.pages + 1, p.pages + 1).is_err());
        assert!(doc.frame(0, p.pages + 2).is_err());
        let mut constrained = s.document(p);
        constrained.max_pages = 0;
        assert!(constrained.frame(0, p.pages + 1).is_err());
    }
    let mut io = Io {
        fail: true,
        ..Io::default()
    };
    assert_eq!(s.review_step(&mut io), Err(AuthorizationError::Display));
    assert_eq!(s.pending.as_ref().unwrap().seen, 0);
    io.fail = false;
    io.input = Some(LocalInput::Approve);
    assert_eq!(
        s.review_step(&mut io),
        Err(AuthorizationError::InvalidState)
    );
    assert_eq!(s.state(), AuthorizationState::Spent);
    s.begin_request(request(EMPTY).as_bytes(), Some(0)).unwrap();
    io.input = Some(LocalInput::None);
    s.review_step(&mut io).unwrap();
    assert_eq!(s.pending.as_ref().unwrap().cursor, 0);
    io.input = Some(LocalInput::Back);
    s.review_step(&mut io).unwrap();
    assert_eq!(s.pending.as_ref().unwrap().cursor, 0);
    io.input = Some(LocalInput::Next);
    s.review_step(&mut io).unwrap();
    io.input = Some(LocalInput::Back);
    s.review_step(&mut io).unwrap();
    assert_eq!(s.pending.as_ref().unwrap().seen, 1);
    let deadline = s.pending.as_ref().unwrap().deadline;
    approve(&mut s);
    assert_eq!(s.pending.as_ref().unwrap().deadline, deadline);
    assert_eq!(
        s.review_step(&mut Io::default()),
        Err(AuthorizationError::InvalidState)
    );
    assert!(s.attempt_sign("r", Some(0)).is_err());
}

#[test]
fn s03_host_and_transcript_cannot_mint_authority() {
    for name in [
        "approved",
        "button",
        "trusted",
        "approval_digest",
        "persistent_grants",
        "origin",
        "descriptor",
    ] {
        let input = request(EMPTY).replacen('{', &format!("{{\"{name}\":true,"), 1);
        let mut s = session();
        assert!(s.begin_request(input.as_bytes(), Some(0)).is_err());
        assert!(crate::qr::envelope::parse_qr_signing_request(input.as_bytes()).is_err());
        assert!(serial_rejects(input.as_bytes()));
    }
    let mut diagnostic = session();
    assert_eq!(
        diagnostic.begin_request(
            br#"{"version":1,"request_id":"r","method":"get_capabilities"}"#,
            Some(0)
        ),
        Err(AuthorizationError::InvalidState)
    );
    let s = session();
    assert_eq!(s.state(), AuthorizationState::Idle);
    let copied_status = AuthorizationState::Approved;
    assert_ne!(s.state(), copied_status);
    // A fabricated legacy preview approves only a diagnostic record.
    let mut preview = crate::policy::approval_gate::ReviewDecisionState::new();
    preview.begin_review("r", "chosen");
    preview.approve("r", "chosen");
    assert!(preview.review_approved("r", "chosen"));
    let mut s = session();
    assert!(s.attempt_sign("r", Some(0)).is_err());
    s.begin_request(request(EMPTY).as_bytes(), Some(0)).unwrap();
    approve(&mut s);
    assert_eq!(s.state(), AuthorizationState::Approved);
}

#[test]
fn s03_attempt_binds_context_and_consumes_mismatch() {
    for mutation in 0..28 {
        let mut s = approved(EMPTY);
        match mutation {
            0 => s.session += 1,
            1 => s.account += 1,
            2 => s.policy += 1,
            3 => s.operation += 1,
            4 => s.limit_version += 1,
            5 => s.review_version += 1,
            6 => s.geometry.columns -= 1,
            7 => s.limits.content_bytes -= 1,
            8 => s.key = Some(SigningKey::from_slice(secret(1).as_bytes()).unwrap()),
            n => {
                let p = s.pending.as_mut().unwrap();
                match n {
                    9 => p.deadline += 1,
                    10 => p.context[0] += 1,
                    11 => p.public_key[0] ^= 1,
                    12 => p.event_id[0] ^= 1,
                    13 => p.review[0] ^= 1,
                    14 => p.binding[0] ^= 1,
                    15 => p.pages += 1,
                    16 => p.cursor = 0,
                    17 => p.seen = 0,
                    18 => p.request.request_id = "other".parse().unwrap(),
                    19 => {
                        p.request.event = Some(parsed(
                            &EMPTY.replace("\"created_at\":0", "\"created_at\":1"),
                        ))
                    }
                    20 => {
                        p.request.event = Some(parsed(&EMPTY.replace("\"kind\":1", "\"kind\":2")))
                    }
                    21 => p.request.event = Some(parsed(&template("changed", json!([])))),
                    22 => p.request.event = Some(parsed(&template("", json!([["t", "x"]])))),
                    23 => p.request.event = None,
                    24 => p.context[19] += 1,
                    25 => p.context[20] += 1,
                    26 => p.request.method = RequestMethod::PublicKey,
                    _ => p.pages = usize::MAX,
                }
            }
        }
        let mut calls = 0;
        assert!(
            s.execute("r", Some(0), |_, _| {
                calls += 1;
                Err(AuthorizationError::Backend)
            })
            .is_err(),
            "mutation {mutation}"
        );
        assert_eq!(calls, 0);
        assert_eq!(s.state(), AuthorizationState::Spent);
        assert!(s
            .execute("r", Some(0), |_, _| {
                calls += 1;
                Err(AuthorizationError::Backend)
            })
            .is_err());
        assert_eq!(calls, 0);
    }
    let mut s = approved(EMPTY);
    assert_eq!(
        s.attempt_sign("wrong", Some(0)),
        Err(AuthorizationError::Binding)
    );
    assert!(s.attempt_sign("r", Some(0)).is_err());
    for mutation in 0..3 {
        let mut s = approved(EMPTY);
        let mut execution = s.start_execution("r", Some(0)).unwrap();
        let result = sign(execution.owner.key.as_ref().unwrap(), &execution.event_id);
        match mutation {
            0 => execution.binding[0] ^= 1,
            1 => execution.event_id[0] ^= 1,
            _ => execution.public_key[0] ^= 1,
        }
        assert_eq!(
            AuthorizationSession::finish_execution(execution, result, Some(0)),
            Err(AuthorizationError::Binding)
        );
        assert!(s.attempt_sign("r", Some(0)).is_err());
    }
}

#[test]
fn s03_first_attempt_is_irrevocable() {
    for outcome in 0..5 {
        let mut s = approved(EMPTY);
        let mut calls = 0;
        let result = s.execute("r", Some(0), |key, id| {
            calls += 1;
            match outcome {
                0 => sign(key, id),
                1 => Err(AuthorizationError::Backend),
                2 => Ok([0; 64]),
                3 => sign(&SigningKey::from_slice(secret(1).as_bytes()).unwrap(), id),
                _ => sign(key, &crate::hash::sha256(id)),
            }
        });
        assert_eq!(result.is_ok(), outcome == 0);
        assert_eq!(calls, 1);
        assert_eq!(s.state(), AuthorizationState::Spent);
        assert!(s
            .execute("r", Some(0), |_, _| {
                calls += 1;
                Err(AuthorizationError::Backend)
            })
            .is_err());
        assert_eq!(calls, 1);
        // Reused host request IDs require a new complete review, never a cache hit.
        s.begin_request(request(EMPTY).as_bytes(), Some(0)).unwrap();
        assert_eq!(s.state(), AuthorizationState::Reviewing);
        assert!(s.attempt_sign("r", Some(0)).is_err());
    }
}

fn invalidate(s: &mut AuthorizationSession, event: usize) {
    match event {
        0 => s.cancel(),
        1 => s.lock().unwrap(),
        2 => s.reset().unwrap(),
        3 => s.policy_changed().unwrap(),
        4 => s.select_key(secret(3)).unwrap(),
        5 => s.select_key(secret(1)).unwrap(),
        6 => s.configure(limits(), geometry()).unwrap(),
        7 => {
            assert_eq!(s.time(Some(100)), Err(AuthorizationError::Expired));
        }
        _ => {
            s.geometry.columns = 31;
            s.configure(limits(), s.geometry).unwrap();
        }
    }
}
#[test]
fn s03_each_lifecycle_event_invalidates_pending_work() {
    for state in 0..3 {
        for event in 0..9 {
            let mut s = session();
            s.begin_request(request(EMPTY).as_bytes(), Some(0)).unwrap();
            if state > 0 {
                approve(&mut s);
            }
            let execution = if state == 2 {
                Some(s.start_execution("r", Some(0)).unwrap())
            } else {
                None
            };
            if let Some(execution) = execution {
                invalidate(execution.owner, event);
                assert!(
                    AuthorizationSession::finish_execution(execution, Ok([0; 64]), Some(100))
                        .is_err()
                );
            } else {
                invalidate(&mut s, event);
            }
            let mut calls = 0;
            assert!(s
                .execute("r", Some(100), |_, _| {
                    calls += 1;
                    Err(AuthorizationError::Backend)
                })
                .is_err());
            assert_eq!(calls, 0);
            if event == 1 || event == 2 {
                assert!(s.public_key().is_none());
            }
        }
    }
    let mut s = session();
    s.begin_request(request(EMPTY).as_bytes(), Some(0)).unwrap();
    s.review_step(&mut Io {
        input: Some(LocalInput::Reject),
        ..Io::default()
    })
    .unwrap();
    assert_eq!(s.state(), AuthorizationState::Spent);
}

#[test]
fn s03_two_attempts_and_cancel_linearize_once() {
    use std::sync::{
        atomic::{AtomicUsize, Ordering},
        Arc, Barrier, Mutex,
    };
    let owner = Arc::new(Mutex::new(approved(EMPTY)));
    let barrier = Arc::new(Barrier::new(3));
    let calls = Arc::new(AtomicUsize::new(0));
    let mut threads = Vec::new();
    for _ in 0..2 {
        let owner = owner.clone();
        let barrier = barrier.clone();
        let calls = calls.clone();
        threads.push(std::thread::spawn(move || {
            barrier.wait();
            owner
                .lock()
                .unwrap()
                .execute("r", Some(0), |key, id| {
                    calls.fetch_add(1, Ordering::SeqCst);
                    sign(key, id)
                })
                .is_ok()
        }));
    }
    barrier.wait();
    let successes: usize = threads
        .into_iter()
        .map(|t| usize::from(t.join().unwrap()))
        .sum();
    assert_eq!(successes, 1);
    assert_eq!(calls.load(Ordering::SeqCst), 1);
    for cancel_first in [true, false] {
        let mut s = approved(EMPTY);
        let mut calls = 0;
        if cancel_first {
            s.cancel();
            assert!(s.start_execution("r", Some(0)).is_err());
        } else {
            let execution = s.start_execution("r", Some(0)).unwrap();
            calls += 1;
            let result = sign(execution.owner.key.as_ref().unwrap(), &execution.event_id);
            execution.owner.cancel();
            assert_eq!(
                AuthorizationSession::finish_execution(execution, result, Some(0)),
                Err(AuthorizationError::Binding)
            );
        }
        assert_eq!(calls, usize::from(!cancel_first));
        assert!(s.attempt_sign("r", Some(0)).is_err());
    }
    for cancel_first in [true, false] {
        let owner = Arc::new(Mutex::new(approved(EMPTY)));
        let calls = Arc::new(AtomicUsize::new(0));
        let (done_tx, done_rx) = std::sync::mpsc::channel();
        let first_owner = owner.clone();
        let first_calls = calls.clone();
        let first = std::thread::spawn(move || {
            let mut s = first_owner.lock().unwrap();
            if cancel_first {
                s.cancel();
            } else {
                assert!(s
                    .execute("r", Some(0), |k, id| {
                        first_calls.fetch_add(1, Ordering::SeqCst);
                        sign(k, id)
                    })
                    .is_ok());
            }
            drop(s);
            done_tx.send(()).unwrap();
        });
        let second = std::thread::spawn(move || {
            done_rx.recv().unwrap();
            let mut s = owner.lock().unwrap();
            if cancel_first {
                assert!(s
                    .execute("r", Some(0), |_, _| {
                        calls.fetch_add(1, Ordering::SeqCst);
                        Err(AuthorizationError::Backend)
                    })
                    .is_err());
            } else {
                s.cancel();
            }
            calls.load(Ordering::SeqCst)
        });
        first.join().unwrap();
        assert_eq!(second.join().unwrap(), usize::from(!cancel_first));
    }
}

#[test]
fn s03_old_session_aliases_and_time_fail_closed() {
    for tick in [99, 100, 101] {
        let mut s = approved(EMPTY);
        let result = s.execute("r", Some(tick), sign);
        assert_eq!(result.is_ok(), tick == 99);
    }
    let mut s = approved(EMPTY);
    let execution = s.start_execution("r", Some(0)).unwrap();
    execution.owner.reset().unwrap();
    execution.owner.select_key(secret(3)).unwrap();
    execution
        .owner
        .begin_request(request(EMPTY).as_bytes(), Some(0))
        .unwrap();
    approve(execution.owner);
    // A later operation may complete, but the old operation cannot follow it.
    assert!(execution.owner.execute("r", Some(0), sign).is_ok());
    assert!(AuthorizationSession::finish_execution(execution, Ok([0; 64]), Some(0)).is_err());
    // A separately reconstructed owner has no transferable callback surface.
    let mut reconstructed = AuthorizationSession::new(limits(), geometry()).unwrap();
    assert_eq!(
        reconstructed.begin_request(request(EMPTY).as_bytes(), Some(0)),
        Err(AuthorizationError::Locked)
    );
    for now in [None, Some(9)] {
        let mut s = session();
        s.begin_request(request(EMPTY).as_bytes(), Some(10))
            .unwrap();
        assert_eq!(s.time(now), Err(AuthorizationError::Clock));
        assert!(s.pending.is_none());
    }
    let mut s = session();
    assert_eq!(
        s.begin_request(request(EMPTY).as_bytes(), Some(u64::MAX)),
        Err(AuthorizationError::Clock)
    );
    let mut s = session();
    s.begin_request(request(EMPTY).as_bytes(), Some(0)).unwrap();
    let deadline = s.pending.as_ref().unwrap().deadline;
    assert_eq!(
        s.begin_request(request(EMPTY).as_bytes(), Some(90)),
        Err(AuthorizationError::Busy)
    );
    assert_eq!(s.pending.as_ref().unwrap().deadline, deadline);
    let mut io = Io {
        tick: 90,
        after: Some(100),
        ..Io::default()
    };
    assert_eq!(s.review_step(&mut io), Err(AuthorizationError::Expired));
    let mut s = session();
    s.operation = u64::MAX;
    assert_eq!(
        s.begin_request(request(EMPTY).as_bytes(), Some(0)),
        Err(AuthorizationError::Exhausted)
    );
    assert!(s.public_key().is_none());
    assert_eq!(s.select_key(secret(3)), Err(AuthorizationError::Exhausted));
    assert_eq!(
        s.begin_request(request(EMPTY).as_bytes(), Some(0)),
        Err(AuthorizationError::Exhausted)
    );
    let mut fresh = AuthorizationSession::new(limits(), geometry()).unwrap();
    assert_eq!(
        fresh.attempt_sign("r", Some(0)),
        Err(AuthorizationError::InvalidState)
    );
    assert_eq!(
        fresh.begin_request(request(EMPTY).as_bytes(), Some(0)),
        Err(AuthorizationError::Locked)
    );
}

#[test]
fn s03_all_limits_bound_storage_and_work() {
    assert!(core::mem::size_of::<Pending>() <= 8192);
    assert!(core::mem::size_of::<AuthorizationSession>() <= 16384);
    std::println!("S03 retained bytes: EventTemplate={} Pending={} AuthorizationSession={} Execution={} InspectionFrame={}",core::mem::size_of::<EventTemplate>(),core::mem::size_of::<Pending>(),core::mem::size_of::<AuthorizationSession>(),core::mem::size_of::<Execution<'_>>(),core::mem::size_of::<InspectionFrame>());
    for which in 0..8 {
        for delta in [0, 1] {
            let mut l = limits();
            match which {
                0 => l.input_bytes = 4096 + delta,
                1 => l.content_bytes = 2048 + delta,
                2 => l.tags = 32 + delta,
                3 => l.fields_per_tag = 8 + delta,
                4 => l.field_bytes = 256 + delta,
                5 => l.text_bytes = 4096 + delta,
                6 => l.canonical_bytes = 8192 + delta,
                _ => l.review_pages = 1024 + delta,
            }
            assert_eq!(l.validate().is_ok(), delta == 0);
        }
    }
    for (field, bound) in [(0, EMPTY.len()), (1, 3), (2, 1), (3, 2), (4, 3), (5, 4)] {
        for delta in [-1isize, 0, 1] {
            let mut l = limits();
            let input = match field {
                0 => EMPTY.to_string(),
                1 => template("abc", json!([])),
                2 => template("", json!([["t"]])),
                3 => template("", json!([["t", "x"]])),
                4 => template("", json!([["t", "abc"]])),
                _ => template("ab", json!([["t", "x"]])),
            };
            let v = (bound as isize + delta) as usize;
            match field {
                0 => l.input_bytes = v,
                1 => l.content_bytes = v,
                2 => l.tags = v,
                3 => l.fields_per_tag = v,
                4 => l.field_bytes = v,
                _ => l.text_bytes = v,
            }
            assert_eq!(
                EventTemplate::parse(input.as_bytes(), l).is_ok(),
                delta >= 0,
                "field {field} delta {delta}"
            );
        }
    }
    let mut out = [0; 8192];
    let key = session().public_key().unwrap();
    let canonical = parsed(EMPTY).write_canonical(&key, &mut out).unwrap();
    for delta in [-1isize, 0, 1] {
        let mut l = limits();
        l.canonical_bytes = (canonical as isize + delta) as usize;
        let e = EventTemplate::parse(EMPTY.as_bytes(), l).unwrap();
        assert_eq!(e.event_id(&key).is_ok(), delta >= 0);
    }
    let s = approved(EMPTY);
    let pages = s.pending.as_ref().unwrap().pages + 1;
    for delta in [-1isize, 0, 1] {
        let mut s = session();
        let mut l = limits();
        l.review_pages = (pages as isize + delta) as usize;
        s.configure(l, geometry()).unwrap();
        assert_eq!(
            s.begin_request(request(EMPTY).as_bytes(), Some(0)).is_ok(),
            delta >= 0
        );
    }
    for g in [
        InspectionGeometry {
            columns: 9,
            lines: 8,
        },
        InspectionGeometry {
            columns: 33,
            lines: 8,
        },
        InspectionGeometry {
            columns: 32,
            lines: 0,
        },
        InspectionGeometry {
            columns: 32,
            lines: 9,
        },
    ] {
        assert!(AuthorizationSession::new(limits(), g).is_err());
    }
    for field in 0..3 {
        let mut l = limits();
        match field {
            0 => l.input_bytes = 0,
            1 => l.canonical_bytes = 0,
            _ => l.review_pages = 0,
        };
        assert!(l.validate().is_err());
    }
    let many = template("", json!(vec![vec!["x"; 8]; 32]));
    assert_eq!(parsed(&many).tag_count(), 32);
    assert!(EventTemplate::parse(
        template("", json!(vec![vec!["x"; 8]; 33])).as_bytes(),
        limits()
    )
    .is_err());
    for tags in [
        json!([[]]),
        json!([[""]]),
        json!([["t", true]]),
        json!(["t"]),
        json!([vec!["x"; 9]]),
    ] {
        assert!(EventTemplate::parse(template("", tags).as_bytes(), limits()).is_err());
    }
    let deep = format!("{}{}", "[".repeat(2000), "]".repeat(2000));
    assert!(EventTemplate::parse(deep.as_bytes(), limits()).is_err());
    assert!(parsed(EMPTY).tag(0).is_none());
    let maximal = template(&"x".repeat(2048), json!(vec![vec!["x"; 8]; 32]));
    assert!(request(&maximal).len() <= 4096);
    let mut exact = limits();
    exact.text_bytes = 2304;
    assert!(EventTemplate::parse(maximal.as_bytes(), exact).is_ok());
    exact.text_bytes = 2303;
    assert!(EventTemplate::parse(maximal.as_bytes(), exact).is_err());
    let maximum_owner = approved(&maximal);
    assert_eq!(
        maximum_owner
            .pending
            .as_ref()
            .unwrap()
            .request
            .event
            .as_ref()
            .unwrap()
            .tag_count(),
        32
    );
    let mut padded = EMPTY.to_string();
    padded.push_str(&" ".repeat(4096 - EMPTY.len()));
    assert!(EventTemplate::parse(padded.as_bytes(), limits()).is_ok());
    padded.push(' ');
    assert!(EventTemplate::parse(padded.as_bytes(), limits()).is_err());
}

#[test]
fn s03_legacy_status_never_enables_product_signing() {
    use crate::policy::signing_policy::{
        evaluate_signing_readiness, SigningGateNames, SigningReadiness,
    };
    let claim = SigningReadiness {
        runtime_signing_feature_enabled: true,
        parser_limits_enforced: true,
        trusted_review_display_accepted: true,
        physical_approval_controls_accepted: true,
        approval_digest_binding_verified: true,
        unicode_review_rendering_accepted: true,
        key_provisioning_ready: true,
        source_public_key_proof_ready: true,
        secure_boot_enabled: true,
        flash_encryption_enabled: true,
        debug_locked: true,
        companion_signed_output_verification_ready: true,
        development_accepted_gates: SigningGateNames::new(),
    };
    assert!(evaluate_signing_readiness(&claim).signing_enabled);
    let mut s = approved(EMPTY);
    assert_eq!(
        s.attempt_sign("r", Some(0)),
        Err(AuthorizationError::SigningUnavailable)
    );
    assert_eq!(s.state(), AuthorizationState::Spent);
    assert!(s.attempt_sign("r", Some(0)).is_err());
    use crate::{
        base64url::{decode_base64url, encode_base64url},
        protocol::{development_device_protocol_context, handle_serial_frame},
        serial::frame::{decode_serial_frame, encode_serial_frame, FrameType},
    };
    let mut payload = [0; 2048];
    let mut line = [0; 2048];
    let mut decoded = [0; 2048];
    for method in ["get_signing_status", "sign_event"] {
        let json = if method == "sign_event" {
            request(EMPTY)
        } else {
            format!(r#"{{"version":1,"request_id":"r","method":"{method}"}}"#)
        };
        let payload = encode_base64url(json.as_bytes(), &mut payload).unwrap();
        let line = encode_serial_frame(FrameType::Request, payload, &mut line).unwrap();
        let response = handle_serial_frame(line, &development_device_protocol_context()).unwrap();
        let frame = decode_serial_frame(response.as_bytes()).unwrap();
        let bytes = decode_base64url(frame.payload_base64url, &mut decoded).unwrap();
        let text = core::str::from_utf8(bytes).unwrap();
        assert!(text.contains(if method == "sign_event" {
            "signing_disabled"
        } else {
            "\"signing_enabled\":false"
        }));
        assert!(!text.contains("\"sig\""));
    }
    let oversized_field = request(&template("", json!([["t", "x".repeat(65)]])));
    let payload = encode_base64url(oversized_field.as_bytes(), &mut payload).unwrap();
    let line = encode_serial_frame(FrameType::Request, payload, &mut line).unwrap();
    let response = handle_serial_frame(line, &development_device_protocol_context()).unwrap();
    assert_eq!(
        decode_serial_frame(response.as_bytes()).unwrap().frame_type,
        FrameType::Error
    );
}

#[test]
fn s03_independent_event_id_and_signature_agree() {
    let mut observed = Vec::new();
    for v in vectors()["vectors"].as_array().unwrap() {
        let mut s = approved(v["template"].as_str().unwrap());
        let p = s.pending.as_ref().unwrap();
        let mut bytes = [0; 8192];
        let len = p
            .request
            .event
            .as_ref()
            .unwrap()
            .write_canonical(&p.public_key, &mut bytes)
            .unwrap();
        let public = hex(&p.public_key);
        let event_id = hex(&p.event_id);
        let canonical = hex(&bytes[..len]);
        let signature = s.execute("r", Some(0), sign).unwrap();
        assert_eq!(hex(&signature), v["signature"].as_str().unwrap());
        assert_eq!(event_id, v["event_id"].as_str().unwrap());
        assert_eq!(public, v["pubkey"].as_str().unwrap());
        observed.push(json!({"id":v["id"],"pubkey":public,"canonical_hex":canonical,"event_id":event_id,"signature":hex(&signature)}));
    }
    if let Ok(path) = std::env::var("S03_OBSERVED") {
        std::fs::write(path, serde_json::to_vec_pretty(&observed).unwrap()).unwrap();
    }
}
