use nsealr_core::{
    authorization::{
        AuthorizationError as E, AuthorizationSession, AuthorizationState as S, LocalDisplayError,
        LocalInput, LocalPresentation, LocalReviewIo,
    },
    base64url::{decode_base64url, encode_base64url},
    event::{OperationLimits, ParsedRequest},
    nip19::SecretKey,
    protocol::{development_device_protocol_context, handle_serial_frame_with_review_preview},
    qr::envelope::parse_qr_signing_request,
    review::{controls::ReviewButton, display::ReviewDisplayLimits, event::InspectionGeometry},
    serial::frame::{decode_serial_frame, encode_serial_frame, FrameType},
};
use serde_json::{json, Value};

fn request(content: &str, tags: Value) -> Vec<u8> {
    serde_json::to_vec(&json!({"version":1,"request_id":"r","method":"sign_event",
        "params":{"event_template":{"created_at":0,"kind":1,"tags":tags,"content":content}}}))
    .unwrap()
}
fn owner() -> AuthorizationSession {
    let mut raw = [0; 32];
    raw[31] = 3;
    let key = SecretKey::take_from(&mut raw).unwrap();
    let mut owner = AuthorizationSession::new(
        OperationLimits::conformance(),
        InspectionGeometry {
            columns: 32,
            lines: 8,
        },
    )
    .unwrap();
    owner.select_key(key).unwrap();
    owner
}
fn serial(raw: &[u8]) -> nsealr_core::protocol::SerialFrameHandlingResult {
    let mut encoded = [0; 8192];
    let mut frame = [0; 8192];
    let encoded = encode_base64url(raw, &mut encoded).unwrap();
    let frame = encode_serial_frame(FrameType::Request, encoded, &mut frame).unwrap();
    handle_serial_frame_with_review_preview(
        frame,
        &development_device_protocol_context(),
        ReviewDisplayLimits::default(),
    )
    .unwrap()
}
#[derive(Default)]
struct Io {
    tick: u64,
    expire_on_decision: bool,
    frames: Vec<(String, String)>,
}
impl LocalReviewIo for Io {
    fn now(&mut self) -> Option<u64> {
        Some(self.tick)
    }
    fn present(&mut self, frame: LocalPresentation<'_>) -> Result<LocalInput, LocalDisplayError> {
        let (f, decision) = match frame {
            LocalPresentation::Data(f) => (f, false),
            LocalPresentation::Decision(f) => (f, true),
        };
        self.frames
            .push((f.label().replace('\n', ""), f.body().replace('\n', "")));
        if decision && self.expire_on_decision {
            self.tick = 100;
        }
        Ok(if decision {
            LocalInput::Approve
        } else {
            LocalInput::Next
        })
    }
}

#[test]
fn legacy_limits_stay_narrower_than_internal_parser() {
    let controls = [
        request(&"a".repeat(513), json!([])),
        request("", json!([["x", "a".repeat(65)]])),
        request("", Value::Array((0..17).map(|_| json!(["x"])).collect())),
        request(&"😀".repeat(129), json!([])),
    ];
    for raw in controls {
        assert!(
            raw.len() <= 704,
            "control must exercise decoded field/count limit, not outer input size"
        );
        assert!(ParsedRequest::parse(&raw, OperationLimits::conformance()).is_ok());
        assert!(parse_qr_signing_request(&raw).is_err());
        assert_eq!(
            decode_serial_frame(serial(&raw).response_frame.as_bytes())
                .unwrap()
                .frame_type,
            FrameType::Error
        );
    }
    for raw in [
        request(&"a".repeat(512), json!([])),
        request("", json!([["x", "a".repeat(64)]])),
        request("", Value::Array((0..16).map(|_| json!(["x"])).collect())),
    ] {
        assert!(raw.len() <= 704);
        assert!(parse_qr_signing_request(&raw).is_ok());
        assert_ne!(
            decode_serial_frame(serial(&raw).response_frame.as_bytes())
                .unwrap()
                .frame_type,
            FrameType::Error
        );
    }
}

#[test]
fn input_mutation_after_intake_cannot_retarget_owned_review() {
    let mut raw = request("before", json!([]));
    let mut owner = owner();
    owner.begin_request(&raw, Some(0)).unwrap();
    let at = raw.windows(6).position(|w| w == b"before").unwrap();
    raw[at..at + 6].copy_from_slice(b"after!");
    let mut io = Io::default();
    for _ in 0..1025 {
        if owner.state() == S::Approved {
            break;
        }
        owner.review_step(&mut io).unwrap();
    }
    assert_eq!(owner.state(), S::Approved);
    let content = io
        .frames
        .iter()
        .filter(|(l, _)| l.starts_with("Signed content (plain text) / fragment "))
        .map(|(_, b)| b.as_str())
        .collect::<String>();
    assert_eq!(content, "\"before\"");
    let id = io
        .frames
        .iter()
        .filter(|(l, _)| l.starts_with("Canonical event ID / fragment "))
        .map(|(_, b)| b.as_str())
        .collect::<String>();
    // Independently computed Python json/hashlib expectation, not this Rust canonicalizer.
    assert_eq!(
        id,
        "\"0ae996affd028446aed52e4a93683e55878b5154e08e9ddd0fb7b2a07af722b3\""
    );
    assert_eq!(owner.attempt_sign("r", Some(0)), Err(E::SigningUnavailable));
    assert_eq!(owner.attempt_sign("r", Some(0)), Err(E::InvalidState));
}

#[test]
fn consent_arriving_at_deadline_is_rejected_before_acceptance() {
    let mut owner = owner();
    owner
        .begin_request(&request("late", json!([])), Some(0))
        .unwrap();
    let mut io = Io {
        expire_on_decision: true,
        ..Io::default()
    };
    let mut terminal = None;
    for _ in 0..1025 {
        if let Err(e) = owner.review_step(&mut io) {
            terminal = Some(e);
            break;
        }
    }
    assert_eq!(terminal, Some(E::Expired));
    assert_eq!(owner.state(), S::Spent);
    assert_eq!(owner.attempt_sign("r", Some(100)), Err(E::InvalidState));
}

#[test]
fn actual_serial_preview_approval_does_not_enable_output_or_authority() {
    let mut result = serial(&request("preview", json!([])));
    let frame = decode_serial_frame(result.response_frame.as_bytes()).unwrap();
    let mut raw = [0; 2048];
    let raw = decode_base64url(frame.payload_base64url, &mut raw).unwrap();
    let response: Value = serde_json::from_slice(raw).unwrap();
    assert_eq!(response["error"]["code"], "signing_disabled");
    assert_eq!(response["ok"], false);
    assert!(response.get("result").is_none() && response.get("sig").is_none());
    let preview = result.review_session.as_mut().unwrap();
    for _ in 0..1025 {
        if preview.current_frame().unwrap().title == "Decision" {
            break;
        }
        preview.handle_button(ReviewButton::Next).unwrap();
    }
    assert_eq!(
        preview.handle_button(ReviewButton::Approve).unwrap(),
        Some(true)
    );
    assert!(preview.review_approved());
    let mut execution_owner = owner();
    assert_eq!(
        execution_owner.attempt_sign("r", Some(0)),
        Err(E::InvalidState)
    );
    assert_eq!(execution_owner.state(), S::Spent);
}
