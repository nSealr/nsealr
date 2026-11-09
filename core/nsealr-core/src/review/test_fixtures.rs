//! Shared test fixtures for the M-T3.6 review/protocol tests (test-only).
//!
//! The C++ suite consumed these through the generated vector header
//! (`generate_transport_vector_header.py` over `specs/vectors`); this port
//! projects the authoritative artifact into build output for tests only; no
//! implementation computes these expected answers.

use crate::review::display::ReviewDisplayFrame;
use crate::review::types::{
    ReviewBodyLineStyles, ReviewPageAction, ReviewPageLines, ReviewPageList, TrustedReviewPage,
    TrustedReviewRequest,
};

/// Approval digest copied from the READ-ONLY
/// specs/vectors/review-screens/kind-1-basic.json (`screen_review.approval_digest`).
pub const BASIC_REVIEW_SCREEN_APPROVAL_DIGEST: &str = include_str!(concat!(
    env!("OUT_DIR"),
    "/field-a9dbf5d6f075ebea8a12c272.txt"
));

/// Approval digest copied from the READ-ONLY
/// specs/vectors/review-screens/kind-1-tags.json (`screen_review.approval_digest`).
pub const TAGGED_REVIEW_SCREEN_APPROVAL_DIGEST: &str = include_str!(concat!(
    env!("OUT_DIR"),
    "/field-7c553abbee46c2de6c223a2b.txt"
));

/// Static QR envelope copied from the READ-ONLY
/// specs/vectors/transports/qr-envelope-kind-1-basic.json (`envelope`).
pub const QR_ENVELOPE_KIND_1_BASIC: &str = include_str!(concat!(
    env!("OUT_DIR"),
    "/field-b69c96b873204e5c324385c0.txt"
));

/// Builds one review page from plain literals.
pub fn review_page(
    title: &str,
    lines: &[&str],
    action: ReviewPageAction,
    page_indicator: &str,
    logical_page_id: &str,
) -> TrustedReviewPage {
    let mut page_lines = ReviewPageLines::new();
    for line in lines {
        page_lines.try_push(line).unwrap();
    }
    TrustedReviewPage {
        title: title.parse().unwrap(),
        lines: page_lines,
        action,
        page_indicator: page_indicator.parse().unwrap(),
        body_line_styles: ReviewBodyLineStyles::new(),
        logical_page_id: logical_page_id.parse().unwrap(),
    }
}

/// Builds a trusted-review request from plain literals (empty
/// indicator/styles/logical ids, as the summary pages carry).
pub fn trusted_review_request(
    request_id: &str,
    approval_digest: &str,
    pages: &[(&str, &[&str], ReviewPageAction)],
) -> TrustedReviewRequest {
    let mut page_list = ReviewPageList::new();
    for (title, lines, action) in pages {
        page_list
            .try_push(review_page(title, lines, *action, "", ""))
            .unwrap();
    }
    TrustedReviewRequest {
        request_id: request_id.parse().unwrap(),
        approval_digest: approval_digest.parse().unwrap(),
        pages: page_list,
    }
}

// Basic/tagged pages, digests and limits are extracted from the single artifact.
include!(concat!(env!("OUT_DIR"), "/review-fixtures.rs"));

/// True if any frame body line contains `needle` (the C++ `lines_contain`).
pub fn frame_lines_contain(frame: &ReviewDisplayFrame, needle: &str) -> bool {
    frame
        .body_lines
        .as_slice()
        .iter()
        .any(|line| line.as_str().contains(needle))
}

/// Joins the lines of every page with `title` (the C++
/// `joined_lines_for_title`).
pub fn joined_lines_for_title(pages: &[TrustedReviewPage], title: &str) -> std::string::String {
    let mut joined = std::string::String::new();
    for page in pages {
        if page.title != title {
            continue;
        }
        for line in page.lines.as_slice() {
            joined.push_str(line.as_str());
        }
    }
    joined
}

/// Counts the pages with `title` (the C++ `page_count_with_title`).
pub fn page_count_with_title(pages: &[TrustedReviewPage], title: &str) -> usize {
    pages.iter().filter(|page| page.title == title).count()
}

/// True if any line of any page contains `needle` (the C++ `lines_contain`
/// applied across pages).
pub fn any_page_line_contains(pages: &[TrustedReviewPage], needle: &str) -> bool {
    pages.iter().any(|page| {
        page.lines
            .as_slice()
            .iter()
            .any(|line| line.as_str().contains(needle))
    })
}
