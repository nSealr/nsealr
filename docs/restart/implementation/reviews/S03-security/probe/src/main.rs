use nsealr_core::{
    authorization::{
        AuthorizationError as E, AuthorizationSession, AuthorizationState as S, LocalDisplayError,
        LocalInput, LocalPresentation, LocalReviewIo,
    },
    event::{EventTemplate, OperationLimits, ParsedRequest},
    nip19::SecretKey,
    review::event::{validate_kind1, InspectionGeometry},
};
use serde_json::{json, Value};
use std::io::{self, BufRead};

fn geometry() -> InspectionGeometry {
    InspectionGeometry {
        columns: 32,
        lines: 8,
    }
}
fn secret() -> SecretKey {
    let mut raw = [0; 32];
    raw[31] = 3;
    let secret = SecretKey::take_from(&mut raw).unwrap();
    assert_eq!(raw, [0; 32]);
    secret
}
fn owner(g: InspectionGeometry) -> AuthorizationSession {
    let mut s = AuthorizationSession::new(OperationLimits::conformance(), g).unwrap();
    s.select_key(secret()).unwrap();
    s
}
fn request(t: &[u8]) -> Vec<u8> {
    let mut r =
        br#"{"version":1,"request_id":"r","method":"sign_event","params":{"event_template":"#
            .to_vec();
    r.extend_from_slice(t);
    r.extend_from_slice(b"}}");
    r
}
struct Io {
    pages: Vec<Value>,
    now: Option<u64>,
    after: Option<Option<u64>>,
    action: Option<LocalInput>,
    fail: bool,
}
impl Default for Io {
    fn default() -> Self {
        Self {
            pages: vec![],
            now: Some(0),
            after: None,
            action: None,
            fail: false,
        }
    }
}
impl LocalReviewIo for Io {
    fn now(&mut self) -> Option<u64> {
        self.now
    }
    fn present(&mut self, f: LocalPresentation<'_>) -> Result<LocalInput, LocalDisplayError> {
        let (f, decision) = match f {
            LocalPresentation::Data(f) => (f, false),
            LocalPresentation::Decision(f) => (f, true),
        };
        self.pages.push(json!({"label":f.label(),"body":f.body(),"index":f.index(),"total":f.total(),"position":f.position(),"decision":decision}));
        if let Some(after) = self.after {
            self.now = after;
        }
        if self.fail {
            return Err(LocalDisplayError);
        }
        Ok(self.action.take().unwrap_or(if decision {
            LocalInput::Approve
        } else {
            LocalInput::Next
        }))
    }
}
fn approve(s: &mut AuthorizationSession, io: &mut Io) {
    for _ in 0..1025 {
        if s.state() == S::Approved {
            return;
        }
        s.review_step(io).unwrap();
    }
    panic!("unbounded review");
}
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
fn serial_accepts(request: &[u8]) -> bool {
    use nsealr_core::{
        base64url::encode_base64url,
        protocol::{development_device_protocol_context, handle_serial_frame},
        serial::frame::{decode_serial_frame, encode_serial_frame, FrameType},
    };
    let mut payload = [0; 8192];
    let mut frame = [0; 8192];
    let payload = match encode_base64url(request, &mut payload) {
        Ok(v) => v,
        Err(_) => return false,
    };
    let frame = match encode_serial_frame(FrameType::Request, payload, &mut frame) {
        Ok(v) => v,
        Err(_) => return false,
    };
    match handle_serial_frame(frame, &development_device_protocol_context()) {
        Ok(response) => {
            decode_serial_frame(response.as_bytes()).unwrap().frame_type != FrameType::Error
        }
        Err(_) => false,
    }
}
fn probe(v: Value) -> Value {
    let bytes: Vec<u8> = serde_json::from_value(v["bytes"].clone()).unwrap();
    let r = if v["envelope"] == true {
        bytes.clone()
    } else {
        request(&bytes)
    };
    let mut out = json!({"parsed_request":ParsedRequest::parse(&r,OperationLimits::conformance()).is_ok(),"qr":nsealr_core::qr::envelope::parse_qr_signing_request(&r).is_ok(),"serial":serial_accepts(&r)});
    if v["envelope"] != true {
        match EventTemplate::parse(&bytes, OperationLimits::conformance()) {
            Ok(t) => {
                out["template"] = json!(true);
                out["kind1"] = json!(validate_kind1(&t).is_ok());
                let mut g = geometry();
                if let Some(x) = v["columns"].as_u64() {
                    g.columns = x as usize;
                }
                if let Some(x) = v["lines"].as_u64() {
                    g.lines = x as usize;
                }
                let mut s = owner(g);
                let mut canonical = [0; 8192];
                if let Ok(len) = t.write_canonical(&s.public_key().unwrap(), &mut canonical) {
                    out["canonical"] = json!(String::from_utf8(canonical[..len].to_vec()).unwrap());
                    out["event_id"] = json!(hex(&t.event_id(&s.public_key().unwrap()).unwrap()));
                }
                if v["review"] == true {
                    match s.begin_request(&r, Some(0)) {
                        Ok(()) => {
                            let mut io = Io::default();
                            approve(&mut s, &mut io);
                            out["frames"] = json!(io.pages);
                            out["production"] =
                                json!(format!("{:?}", s.attempt_sign("r", Some(0))));
                            out["retry"] = json!(format!("{:?}", s.attempt_sign("r", Some(0))));
                        }
                        Err(e) => out["review_error"] = json!(format!("{e:?}")),
                    }
                }
            }
            Err(e) => {
                out["template"] = json!(false);
                out["error"] = json!(format!("{e:?}"));
            }
        }
    }
    out
}
fn main() {
    for line in io::stdin().lock().lines() {
        let v: Value = serde_json::from_str(&line.unwrap()).unwrap();
        println!("{}", probe(v));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    const T: &[u8] = br#"{"created_at":0,"kind":1,"tags":[],"content":"state-control"}"#;
    fn approved() -> AuthorizationSession {
        let mut s = owner(geometry());
        s.begin_request(&request(T), Some(0)).unwrap();
        approve(&mut s, &mut Io::default());
        s
    }
    #[test]
    fn unavailable_positive_control_and_terminal_first_attempt() {
        for (id, tick, expected) in [
            ("r", Some(99), E::SigningUnavailable),
            ("wrong", Some(99), E::Binding),
            ("r", None, E::Clock),
            ("r", Some(100), E::Expired),
        ] {
            let mut s = approved();
            assert_eq!(s.attempt_sign(id, tick), Err(expected));
            assert_eq!(s.state(), S::Spent);
            assert_eq!(s.attempt_sign("r", Some(100)), Err(E::InvalidState));
        }
    }
    #[test]
    fn rejected_configuration_and_same_key_replacement_destroy_old_consent() {
        for action in 0..8 {
            let mut s = approved();
            match action {
                0 => s.cancel(),
                1 => {
                    s.lock().unwrap();
                }
                2 => {
                    s.reset().unwrap();
                }
                3 => {
                    s.policy_changed().unwrap();
                }
                4 => {
                    s.select_key(secret()).unwrap();
                }
                5 => {
                    s.configure(OperationLimits::conformance(), geometry())
                        .unwrap();
                }
                6 => {
                    let mut l = OperationLimits::conformance();
                    l.input_bytes = 4097;
                    assert!(s.configure(l, geometry()).is_err());
                }
                _ => {
                    assert!(s
                        .configure(
                            OperationLimits::conformance(),
                            InspectionGeometry {
                                columns: 9,
                                lines: 8
                            }
                        )
                        .is_err());
                }
            }
            assert_eq!(s.attempt_sign("r", Some(0)), Err(E::InvalidState));
            s.reset().unwrap();
            s.select_key(secret()).unwrap();
            s.begin_request(&request(T), Some(0)).unwrap();
            approve(&mut s, &mut Io::default());
            assert_eq!(s.attempt_sign("r", Some(0)), Err(E::SigningUnavailable));
        }
    }
    #[test]
    fn failed_last_frame_and_clock_loss_never_acknowledge() {
        for fail_decision in [false, true] {
            let mut s = owner(geometry());
            s.begin_request(&request(T), Some(0)).unwrap();
            let mut io = Io::default();
            loop {
                let mut one = Io {
                    action: Some(LocalInput::None),
                    ..Io::default()
                };
                s.review_step(&mut one).unwrap();
                let p = &one.pages[0];
                let wanted = if fail_decision {
                    p["decision"] == true
                } else {
                    p["index"].as_u64().unwrap() + 2 == p["total"].as_u64().unwrap()
                };
                if wanted {
                    break;
                }
                s.review_step(&mut io).unwrap();
            }
            let mut failing = Io {
                fail: true,
                ..Io::default()
            };
            assert_eq!(s.review_step(&mut failing), Err(E::Display));
            assert_eq!(s.state(), S::Reviewing);
            if !fail_decision {
                let mut early = Io {
                    action: Some(LocalInput::Approve),
                    ..Io::default()
                };
                assert_eq!(s.review_step(&mut early), Err(E::InvalidState));
            } else {
                let mut clock = Io {
                    after: Some(None),
                    ..Io::default()
                };
                assert_eq!(s.review_step(&mut clock), Err(E::Clock));
            }
            assert_eq!(s.attempt_sign("r", Some(0)), Err(E::InvalidState));
        }
    }
    #[test]
    fn backtracking_busy_replay_and_duplicate_consent_are_terminal() {
        let mut s = owner(geometry());
        s.begin_request(&request(T), Some(0)).unwrap();
        let mut io = Io::default();
        s.review_step(&mut io).unwrap();
        assert_eq!(s.begin_request(&request(T), Some(1)), Err(E::Busy));
        let mut io = Io {
            now: Some(1),
            action: Some(LocalInput::Back),
            ..Io::default()
        };
        s.review_step(&mut io).unwrap();
        io.action = Some(LocalInput::Approve);
        assert_eq!(s.review_step(&mut io), Err(E::InvalidState));
        let mut s = approved();
        assert_eq!(s.review_step(&mut Io::default()), Err(E::InvalidState));
        assert_eq!(s.attempt_sign("r", Some(0)), Err(E::InvalidState));
        let mut s = owner(geometry());
        s.begin_request(&request(T), Some(10)).unwrap();
        let mut io = Io {
            now: Some(9),
            ..Io::default()
        };
        assert_eq!(s.review_step(&mut io), Err(E::Clock));
        assert!(io.pages.is_empty());
    }
}
