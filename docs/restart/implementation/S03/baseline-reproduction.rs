use nsealr_core::policy::approval_gate::ApprovalGate;
use nsealr_core::qr::envelope::parse_qr_signing_request;
use nsealr_core::review::controls::ReviewButton;
use nsealr_core::review::display::{render_review_page, ReviewDisplayLimits, ReviewPage};
use nsealr_core::review::trusted::TrustedReviewSession;
use nsealr_core::review::types::{ReviewPageAction, ReviewPageLine, ReviewPageList, TrustedReviewPage, TrustedReviewRequest};

fn request(template: &str) -> String {
    format!(r#"{{"version":1,"request_id":"s03-red","method":"sign_event","params":{{"event_template":{template}}}}}"#)
}

#[test]
fn s03_red_duplicate_kind_must_reject() {
    let input=request(r#"{"created_at":0,"kind":0,"k\u0069nd":1,"tags":[],"content":""}"#);
    assert!(parse_qr_signing_request(input.as_bytes()).is_err(), "duplicate decoded member was accepted");
}
#[test]
fn s03_red_nostr_kind_bound_must_reject() {
    let input=request(r#"{"created_at":0,"kind":65536,"tags":[],"content":""}"#);
    assert!(parse_qr_signing_request(input.as_bytes()).is_err(), "kind above NIP01 bound accepted");
}
#[test]
fn s03_red_leading_zero_time_must_reject() {
    let input=request(r#"{"created_at":01,"kind":1,"tags":[],"content":""}"#);
    assert!(parse_qr_signing_request(input.as_bytes()).is_err(), "noncanonical integer accepted");
}
#[test]
fn s03_red_approval_must_not_be_reusable() {
    let mut gate=ApprovalGate::new();
    gate.begin_review("s03-red", "digest"); gate.approve("s03-red", "digest");
    assert!(gate.can_sign("s03-red", "digest"));
    assert!(!gate.can_sign("s03-red", "digest"), "authority remains reusable after its first check");
}
#[test]
fn s03_red_unshown_constructed_review_must_not_authorize() {
    let mut pages=ReviewPageList::new();
    let mut page=TrustedReviewPage::new(); page.title="Decision".parse().unwrap();
    page.action=ReviewPageAction::ApproveOrReject; pages.try_push(page).unwrap();
    let mut review=TrustedReviewSession::new(TrustedReviewRequest{request_id:"s03-red".parse().unwrap(),approval_digest:"caller-digest".parse().unwrap(),pages},ReviewDisplayLimits::default()).unwrap();
    assert!(review.handle_button(ReviewButton::Approve).is_err(), "constructed review authorized without display");
}
#[test]
fn s03_red_truncating_renderer_must_not_report_complete_review() {
    let lines:[ReviewPageLine;1]=["a hidden signed suffix".parse().unwrap()];
    let page=ReviewPage{title:"Content",lines:&lines,action:ReviewPageAction::Next,page_indicator:"",body_line_styles:&[]};
    let result=render_review_page(&page,0,1,ReviewDisplayLimits{max_body_lines:1,max_line_chars:5,..ReviewDisplayLimits::default()});
    assert!(result.is_err(), "renderer silently returned an ellipsis as success");
}
