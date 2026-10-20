//! `nsealr1:` QR envelope framing, `nsealr1a:` animated envelopes, and the
//! sign-event signing-request parser.
//!
//! Ported from the C++ reference `host_core` sources `src/qr_envelope.cpp` +
//! `include/nsealr/qr_envelope.hpp` for behaviour parity:
//!
//! - **Static envelope** — `nsealr1:` + unpadded base64url; decode enforces the
//!   base64url alphabet, `len % 4 != 1`, canonical trailing bits, the decoded-size
//!   limit [`MAX_STATIC_QR_DECODED_JSON_BYTES`], valid UTF-8, and a trimmed
//!   `{...}`/`[...]` JSON container shape.
//! - **Animated envelope** — frames shaped
//!   `nsealr1a:<sha256hex(json)>:<index>/<total>:<chunk>:<checksum16>` where the
//!   checksum is `sha256_hex("nsealr1a:" + digest + ":" + index + "/" + total +
//!   ":" + chunk)[..16]`; decode requires one frame per index `1..=total` (any
//!   order, no duplicates), a common digest/total, per-frame chunk limits, then
//!   validates the reassembled payload like the static path plus the whole-JSON
//!   digest, against [`MAX_ANIMATED_QR_DECODED_JSON_BYTES`].
//! - **Signing request** — the shared strict [`crate::event::ParsedRequest`]
//!   reader validates decoded duplicate keys, exact shapes, bounded unsigned
//!   integers and Unicode before producing a diagnostic preview copy.
//!
//! The C++ returned heap strings/vectors. This port writes envelope output into
//! caller buffers, hands animated frames to a callback one at a time, and returns
//! parsed requests as a fixed-capacity struct sized by [`crate::qr::limits`] —
//! keeping the crate `no_std` and allocation-free. Buffer-size errors are
//! reported as [`QrEnvelopeError::OutputTooSmall`] (no C++ analogue).

use crate::base64url::{
    decode_base64url, decoded_len_max, encode_base64url, encoded_len, is_base64url_payload,
    Base64UrlError,
};
use crate::hash::sha256_hex;
use crate::qr::limits::{
    MAX_ANIMATED_QR_DECODED_JSON_BYTES, MAX_ANIMATED_QR_FRAME_COUNT,
    MAX_ANIMATED_QR_FRAME_PAYLOAD_CHARS, MAX_CONTENT_UTF8_BYTES, MAX_DECODED_REQUEST_JSON_BYTES,
    MAX_REQUEST_ID_LENGTH, MAX_STATIC_QR_DECODED_JSON_BYTES, MAX_TAG_COUNT, MAX_TAG_FIELDS_PER_TAG,
    MAX_TAG_FIELD_UTF8_BYTES,
};
use crate::unicode::is_valid_utf8;

/// The static envelope prefix. Mirrors the C++ `kPrefix`.
pub const PREFIX: &[u8] = b"nsealr1:";
/// The animated envelope frame prefix. Mirrors the C++ `kAnimatedPrefix`.
pub const ANIMATED_PREFIX: &[u8] = b"nsealr1a:";

/// Hex characters in a full SHA-256 digest (the animated frame digest field).
const DIGEST_HEX_LEN: usize = 64;
/// Hex characters in the truncated animated-frame checksum.
const CHECKSUM_HEX_LEN: usize = 16;

/// Errors reported by the QR envelope functions. Each variant corresponds to one
/// or more distinct C++ `QrEnvelopeError` messages (named in the doc comments),
/// except [`Self::OutputTooSmall`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum QrEnvelopeError {
    /// C++: "QR envelope must start with nsealr1:".
    MissingPrefix,
    /// C++: "QR envelope payload must be unpadded base64url".
    PayloadNotBase64Url,
    /// C++: "QR envelope payload has invalid base64url length" / "animated QR
    /// payload has invalid base64url length" (`len % 4 == 1`).
    InvalidBase64UrlLength,
    /// C++: "QR envelope payload has invalid trailing bits".
    InvalidTrailingBits,
    /// C++: "QR decoded JSON exceeds max_static_qr_decoded_json_bytes".
    ExceedsStaticJsonBytes,
    /// C++: "animated QR decoded JSON exceeds max_animated_qr_decoded_json_bytes".
    ExceedsAnimatedJsonBytes,
    /// C++: "QR envelope payload must be valid UTF-8" / "animated QR payload must
    /// be valid UTF-8".
    InvalidUtf8,
    /// C++: "QR envelope payload is not valid JSON" (not a `{...}`/`[...]`
    /// container after ASCII-whitespace trim).
    NotJsonContainer,
    /// C++: "animated QR requires at least one frame".
    NoFrames,
    /// C++: "animated QR frame requires nsealr1a prefix".
    AnimatedMissingPrefix,
    /// C++: "animated QR frame is malformed" (not exactly five `:`-fields).
    AnimatedMalformed,
    /// C++: "animated QR digest must be 32-byte lowercase hex".
    AnimatedBadDigest,
    /// C++: "animated QR checksum must be 8-byte lowercase hex".
    AnimatedBadChecksumFormat,
    /// C++: "animated QR index must use index/total".
    AnimatedBadIndexShape,
    /// C++: "animated QR index and total must be decimal" (zero, leading zero,
    /// non-digit, or overflow).
    AnimatedBadIndexValue,
    /// C++: "animated QR frame index is out of range" (`index > total`).
    AnimatedIndexOutOfRange,
    /// C++: "animated QR frame count exceeds max_animated_qr_frame_count".
    AnimatedTooManyFrames,
    /// C++: "animated QR chunk must be unpadded base64url".
    AnimatedChunkNotBase64Url,
    /// C++: "animated QR chunk exceeds max_animated_qr_frame_payload_chars".
    AnimatedChunkTooLong,
    /// C++: "animated QR frame checksum mismatch".
    AnimatedChecksumMismatch,
    /// C++: "animated QR frames must be unique and contiguous" (count != total,
    /// duplicate index, or missing index).
    AnimatedFramesNotContiguous,
    /// C++: "animated QR frame set mismatch" (digest or total differs between
    /// frames).
    AnimatedFrameSetMismatch,
    /// C++: "animated QR decoded digest mismatch".
    AnimatedDigestMismatch,
    /// C++: "animated QR chunk size must be a positive integer".
    AnimatedChunkSizeZero,
    /// C++: "animated QR payload is empty" (encoding an empty payload).
    AnimatedPayloadEmpty,
    /// C++: "QR signing request decoded JSON exceeds max_decoded_request_json_bytes".
    ExceedsRequestJsonBytes,
    /// C++: "QR signing request must be a JSON object".
    RequestNotObject,
    /// C++: the JSON scanner errors — "... JSON string is required" /
    /// "... escape is truncated/invalid" / "... unicode escape is
    /// truncated/invalid" / "... contains control character" / "... string is
    /// unterminated" / "... number is invalid" / "... container is
    /// invalid/unterminated" / "... value is invalid/missing" / "... object member
    /// is missing ':'" / "... object separator is invalid" / "... has trailing
    /// data".
    RequestJsonMalformed,
    /// C++: "QR signing request contains unknown top-level field".
    RequestUnknownField,
    /// C++: "QR signing request version must be 1".
    RequestBadVersion,
    /// C++: "QR signing request request_id is invalid".
    RequestBadRequestId,
    /// C++: "QR signing request method must be sign_event".
    RequestBadMethod,
    /// C++: "QR signing request params object is required".
    RequestParamsRequired,
    /// C++: "QR signing request params contains unknown field".
    RequestParamsUnknownField,
    /// C++: "QR signing request event_template object is required".
    RequestEventTemplateRequired,
    /// C++: "QR signing request event_template must not include id/pubkey/sig".
    RequestEventTemplateForbiddenField,
    /// C++: "QR signing request event_template contains unknown field".
    RequestEventTemplateUnknownField,
    /// C++: "QR signing request event_template created_at is
    /// required/invalid/exceeds max_safe_integer".
    RequestBadCreatedAt,
    /// C++: "QR signing request event_template kind is required/invalid/exceeds
    /// max_safe_integer".
    RequestBadKind,
    /// C++: "QR signing request event_template tags array is required" and the
    /// tags-grammar errors ("tags must be string arrays", "tags array separator is
    /// invalid", "tags array has trailing data").
    RequestBadTags,
    /// C++: "QR signing request event_template content is required".
    RequestBadContent,
    /// C++: "QR signing request event_template content exceeds
    /// max_content_utf8_bytes".
    ContentTooLong,
    /// C++: "QR signing request event_template tag field exceeds
    /// max_tag_field_utf8_bytes".
    TagFieldTooLong,
    /// C++: "QR signing request event_template tag exceeds max_tag_fields_per_tag".
    TooManyTagFields,
    /// C++: "QR signing request event_template tags exceed max_tag_count". (The
    /// C++ also had a "max_total_tag_utf8_bytes" sweep, unreachable behind the
    /// 704-byte request-JSON guard; this port omits that dead check.)
    TooManyTags,
    /// A caller-provided output buffer was too small. No C++ analogue.
    OutputTooSmall,
}

/// A decoded QR envelope: the raw base64url payload text and the decoded JSON.
/// Mirrors the C++ `QrEnvelope` (which owned two `std::string`s); this port
/// borrows the input and the caller's decode buffer.
#[derive(Debug, Clone, Copy)]
pub struct QrEnvelope<'a> {
    /// The unpadded base64url payload (without the `nsealr1:` prefix).
    pub payload_base64url: &'a [u8],
    /// The decoded JSON payload bytes.
    pub payload_json: &'a [u8],
}

/// One field of one tag: which tag it belongs to plus the byte range of its
/// decoded text inside the request's packed tag-field buffer.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct TagField {
    /// Index of the tag this field belongs to (0-based).
    tag: usize,
    /// Byte range `start..end` of the decoded field text.
    start: usize,
    /// End of the byte range.
    end: usize,
}

/// The parsed `event_template`. Mirrors the C++ `QrEventTemplate`, with the heap
/// `tags_json`/`content` strings replaced by a byte range into the request JSON
/// (raw span) and accessors on [`QrSigningRequest`] (decoded text).
#[derive(Debug, Clone, Copy)]
pub struct QrEventTemplate {
    /// The `created_at` value.
    pub created_at: u64,
    /// The `kind` value, restricted to 0..=65535 by the shared strict reader.
    pub kind: i32,
    /// Raw byte range of the `tags` array inside the request JSON.
    pub tags_json: (usize, usize),
    /// Number of tags.
    pub tag_count: usize,
}

/// A parsed QR signing request. Mirrors the C++ `QrSigningRequest`; the
/// `request_id`/`content`/tag-field texts live in fixed internal buffers exposed
/// through accessors, and the raw `event_template` JSON is exposed as a byte
/// range into the request JSON.
#[derive(Debug, Clone, Copy)]
pub struct QrSigningRequest {
    /// Always 1 on success. Mirrors the C++ field.
    pub version: i32,
    request_id: [u8; MAX_REQUEST_ID_LENGTH],
    request_id_len: usize,
    /// `true` when `params` was present (always, on success). Mirrors the C++.
    pub has_params: bool,
    /// `true` when `params.event_template` was present (always, on success).
    pub has_event_template: bool,
    /// Raw byte range of the `event_template` object inside the request JSON.
    pub event_template_json: (usize, usize),
    /// The parsed event template.
    pub event_template: QrEventTemplate,
    content: [u8; MAX_CONTENT_UTF8_BYTES],
    content_len: usize,
    // Sized by the request-JSON limit, not MAX_TOTAL_TAG_UTF8_BYTES: decoded tag
    // text never exceeds its JSON source, which is bounded to 704 bytes here.
    tag_fields_text: [u8; MAX_DECODED_REQUEST_JSON_BYTES],
    tag_fields_text_len: usize,
    tag_fields: [TagField; MAX_TAG_COUNT * MAX_TAG_FIELDS_PER_TAG],
    tag_field_count: usize,
}

impl QrSigningRequest {
    /// The decoded `request_id`.
    #[must_use]
    pub fn request_id(&self) -> &[u8] {
        &self.request_id[..self.request_id_len]
    }

    /// The method. Only `sign_event` is accepted, so this is constant on success.
    /// Mirrors the C++ `method` field.
    #[must_use]
    pub fn method(&self) -> &'static str {
        "sign_event"
    }

    /// The decoded `content` text (escapes resolved to UTF-8).
    #[must_use]
    pub fn content(&self) -> &[u8] {
        &self.content[..self.content_len]
    }

    /// Iterates the decoded fields of tag `tag` (0-based), in order.
    pub fn tag(&self, tag: usize) -> impl Iterator<Item = &[u8]> {
        self.tag_fields[..self.tag_field_count]
            .iter()
            .filter(move |field| field.tag == tag)
            .map(|field| &self.tag_fields_text[field.start..field.end])
    }
}

/// Strips leading/trailing ASCII whitespace (space, LF, CR, tab). Mirrors the
/// C++ `trim_ascii`.
fn trim_ascii(value: &[u8]) -> &[u8] {
    let is_ws = |b: &u8| matches!(*b, b' ' | b'\n' | b'\r' | b'\t');
    let start = value.iter().position(|b| !is_ws(b));
    match start {
        None => &[],
        Some(start) => {
            let end = value.len() - value.iter().rev().position(|b| !is_ws(b)).unwrap();
            &value[start..end]
        }
    }
}

/// Requires the trimmed payload to be a `{...}` or `[...]` container. Mirrors
/// the C++ `require_json_container`.
fn require_json_container(decoded: &[u8]) -> Result<(), QrEnvelopeError> {
    let trimmed = trim_ascii(decoded);
    if trimmed.len() < 2 {
        return Err(QrEnvelopeError::NotJsonContainer);
    }
    let (first, last) = (trimmed[0], trimmed[trimmed.len() - 1]);
    if !((first == b'{' && last == b'}') || (first == b'[' && last == b']')) {
        return Err(QrEnvelopeError::NotJsonContainer);
    }
    Ok(())
}

/// The shared request-id rule (1..=[`MAX_REQUEST_ID_LENGTH`] bytes of
/// `A-Z a-z 0-9 . _ : -`). Mirrors the C++ `is_request_id`, duplicated verbatim
/// in `qr_envelope.cpp` and `qr_response_display.cpp`; shared here.
pub(crate) fn is_request_id(value: &[u8]) -> bool {
    if value.is_empty() || value.len() > MAX_REQUEST_ID_LENGTH {
        return false;
    }
    value.iter().all(|&b| {
        b.is_ascii_uppercase()
            || b.is_ascii_lowercase()
            || b.is_ascii_digit()
            || matches!(b, b'.' | b'_' | b':' | b'-')
    })
}

/// Maps a payload base64url decode failure. Mirrors the C++
/// `decode_qr_payload_base64url` catch clause (trailing bits get their own
/// message; anything else is "must be unpadded base64url"), plus the
/// buffer-size case this port adds.
fn map_payload_decode_error(error: Base64UrlError) -> QrEnvelopeError {
    match error {
        Base64UrlError::InvalidTrailingBits => QrEnvelopeError::InvalidTrailingBits,
        Base64UrlError::InvalidCharacter => QrEnvelopeError::PayloadNotBase64Url,
        Base64UrlError::OutputTooSmall => QrEnvelopeError::OutputTooSmall,
    }
}

/// True iff `value` is exactly `size` lowercase-hex characters. Mirrors the C++
/// `is_lower_hex`.
fn is_lower_hex(value: &[u8], size: usize) -> bool {
    value.len() == size
        && value
            .iter()
            .all(|&b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

/// Parses a positive decimal with no leading zeros. Mirrors the C++
/// `parse_positive_decimal` (which also rejected values overflowing `size_t`).
fn parse_positive_decimal(value: &[u8]) -> Result<usize, QrEnvelopeError> {
    if value.is_empty() || value[0] == b'0' {
        return Err(QrEnvelopeError::AnimatedBadIndexValue);
    }
    let mut parsed = 0usize;
    for &byte in value {
        if !byte.is_ascii_digit() {
            return Err(QrEnvelopeError::AnimatedBadIndexValue);
        }
        parsed = parsed
            .checked_mul(10)
            .and_then(|v| v.checked_add(usize::from(byte - b'0')))
            .ok_or(QrEnvelopeError::AnimatedBadIndexValue)?;
    }
    Ok(parsed)
}

/// Formats `value` as decimal into `buf`, returning the written text.
fn write_decimal(buf: &mut [u8; 20], value: usize) -> &[u8] {
    let mut at = buf.len();
    let mut rest = value;
    loop {
        at -= 1;
        buf[at] = b'0' + (rest % 10) as u8;
        rest /= 10;
        if rest == 0 {
            break;
        }
    }
    &buf[at..]
}

/// One parsed animated frame header, borrowing the frame line. (The chunk text
/// is re-sliced from the raw frame during reassembly, so it is not stored.)
struct AnimatedFrame<'f> {
    digest: &'f [u8],
    index: usize,
    total: usize,
}

/// Parses and validates one animated frame line. Mirrors the C++
/// `parse_animated_qr_frame`, including the validation order (prefix → shape →
/// digest → checksum format → index shape → decimal → range → frame count →
/// chunk alphabet → chunk size → checksum).
fn parse_animated_qr_frame(frame: &[u8]) -> Result<AnimatedFrame<'_>, QrEnvelopeError> {
    let body = frame
        .strip_prefix(ANIMATED_PREFIX)
        .ok_or(QrEnvelopeError::AnimatedMissingPrefix)?;
    // The C++ split the whole frame into five ':'-fields (parts[0] is the
    // prefix text itself); an equivalent split of the post-prefix body must
    // yield exactly four fields.
    let mut parts = [&[][..]; 4];
    let mut count = 0usize;
    for part in body.split(|&b| b == b':') {
        if count == parts.len() {
            return Err(QrEnvelopeError::AnimatedMalformed);
        }
        parts[count] = part;
        count += 1;
    }
    if count != parts.len() {
        return Err(QrEnvelopeError::AnimatedMalformed);
    }
    let [digest, index_total, chunk, checksum] = parts;
    if !is_lower_hex(digest, DIGEST_HEX_LEN) {
        return Err(QrEnvelopeError::AnimatedBadDigest);
    }
    if !is_lower_hex(checksum, CHECKSUM_HEX_LEN) {
        return Err(QrEnvelopeError::AnimatedBadChecksumFormat);
    }
    let slash = index_total
        .iter()
        .position(|&b| b == b'/')
        .ok_or(QrEnvelopeError::AnimatedBadIndexShape)?;
    if index_total[slash + 1..].contains(&b'/') {
        return Err(QrEnvelopeError::AnimatedBadIndexShape);
    }
    let index = parse_positive_decimal(&index_total[..slash])?;
    let total = parse_positive_decimal(&index_total[slash + 1..])?;
    if index > total {
        return Err(QrEnvelopeError::AnimatedIndexOutOfRange);
    }
    if total > MAX_ANIMATED_QR_FRAME_COUNT {
        return Err(QrEnvelopeError::AnimatedTooManyFrames);
    }
    if !is_base64url_payload(chunk) {
        return Err(QrEnvelopeError::AnimatedChunkNotBase64Url);
    }
    if chunk.len() > MAX_ANIMATED_QR_FRAME_PAYLOAD_CHARS {
        return Err(QrEnvelopeError::AnimatedChunkTooLong);
    }
    // The checksum pre-image ("nsealr1a:" + digest + ":" + index + "/" + total +
    // ":" + chunk) is exactly the frame minus its ":checksum" suffix, because
    // parse_positive_decimal only accepts the canonical decimal spelling.
    let preimage = &frame[..frame.len() - (CHECKSUM_HEX_LEN + 1)];
    if checksum != &sha256_hex(preimage)[..CHECKSUM_HEX_LEN] {
        return Err(QrEnvelopeError::AnimatedChecksumMismatch);
    }
    Ok(AnimatedFrame {
        digest,
        index,
        total,
    })
}

/// Decodes a static `nsealr1:` envelope. Mirrors the C++ `decode_qr_envelope`.
/// `json_out` receives the decoded JSON (size it with
/// [`MAX_STATIC_QR_DECODED_JSON_BYTES`]).
///
/// # Errors
///
/// See [`QrEnvelopeError`]. The accept/reject *sets* are identical to the C++;
/// the error-variant precedence can differ on multi-fault inputs (this port
/// checks the exact decoded size before decoding, so e.g. an oversized payload
/// with non-canonical trailing bits reports [`QrEnvelopeError::ExceedsStaticJsonBytes`]
/// where the C++ reported the trailing-bits error).
pub fn decode_qr_envelope<'a>(
    envelope: &'a [u8],
    json_out: &'a mut [u8],
) -> Result<QrEnvelope<'a>, QrEnvelopeError> {
    let payload = envelope
        .strip_prefix(PREFIX)
        .ok_or(QrEnvelopeError::MissingPrefix)?;
    if !is_base64url_payload(payload) {
        return Err(QrEnvelopeError::PayloadNotBase64Url);
    }
    if payload.len() % 4 == 1 {
        return Err(QrEnvelopeError::InvalidBase64UrlLength);
    }
    // For unpadded base64url the decoded size is exact, so the size limit can be
    // enforced before decoding (the C++ decoded into a growable string first;
    // same accept/reject set).
    if decoded_len_max(payload.len()) > MAX_STATIC_QR_DECODED_JSON_BYTES {
        return Err(QrEnvelopeError::ExceedsStaticJsonBytes);
    }
    let decoded = decode_base64url(payload, json_out).map_err(map_payload_decode_error)?;
    if !is_valid_utf8(decoded) {
        return Err(QrEnvelopeError::InvalidUtf8);
    }
    require_json_container(decoded)?;
    Ok(QrEnvelope {
        payload_base64url: payload,
        payload_json: decoded,
    })
}

/// Reassembles and decodes an animated `nsealr1a:` frame set. Mirrors the C++
/// `decode_animated_qr_envelope_frames`. `frames` yields each scanned frame line;
/// `payload_out` receives the concatenated base64url payload and `json_out` the
/// decoded JSON (size with `encoded_len(MAX_ANIMATED_QR_DECODED_JSON_BYTES)` and
/// [`MAX_ANIMATED_QR_DECODED_JSON_BYTES`]).
///
/// # Errors
///
/// See [`QrEnvelopeError`]. The accept/reject *sets* are identical to the C++
/// (including the unique-and-contiguous index rule and the whole-payload digest
/// check); the error-variant precedence can differ on multi-fault frame sets
/// (e.g. a wrong frame count combined with a digest mismatch reports
/// [`QrEnvelopeError::AnimatedFrameSetMismatch`] — this port's in-loop mismatch
/// check runs before its count check — where the C++ checked the count first and
/// reported the not-contiguous error; the exact-size guard runs before decoding
/// as in the static path).
pub fn decode_animated_qr_envelope_frames<'a>(
    frames: &[&[u8]],
    payload_out: &'a mut [u8],
    json_out: &'a mut [u8],
) -> Result<QrEnvelope<'a>, QrEnvelopeError> {
    if frames.is_empty() {
        return Err(QrEnvelopeError::NoFrames);
    }
    // First pass: per-frame validation, in input order (C++ parsed every frame
    // into a vector before any set-level check).
    let first = parse_animated_qr_frame(frames[0])?;
    let (digest, total) = (first.digest, first.total);
    // Frame position holding each 1-based index (usize::MAX = not seen yet).
    let mut position_of_index = [usize::MAX; MAX_ANIMATED_QR_FRAME_COUNT];
    for (position, frame) in frames.iter().enumerate() {
        let parsed = parse_animated_qr_frame(frame)?;
        if parsed.digest != digest || parsed.total != total {
            return Err(QrEnvelopeError::AnimatedFrameSetMismatch);
        }
        if position_of_index[parsed.index - 1] != usize::MAX {
            return Err(QrEnvelopeError::AnimatedFramesNotContiguous);
        }
        position_of_index[parsed.index - 1] = position;
    }
    if frames.len() != total {
        return Err(QrEnvelopeError::AnimatedFramesNotContiguous);
    }
    // With exactly `total` distinct indexes in 1..=total, every index is present.
    // Second pass: locate each chunk (between the third ':' and the ":checksum"
    // suffix of its already-validated frame) and run the whole-payload length
    // checks before any copying.
    let chunk_of = |frame: &'_ [u8]| -> core::ops::Range<usize> {
        let chunk_end = frame.len() - (CHECKSUM_HEX_LEN + 1);
        let index_total_end = ANIMATED_PREFIX.len() + DIGEST_HEX_LEN + 1;
        let chunk_start = index_total_end
            + frame[index_total_end..chunk_end]
                .iter()
                .position(|&b| b == b':')
                .expect("frame shape validated above")
            + 1;
        chunk_start..chunk_end
    };
    let total_payload_len: usize = position_of_index[..total]
        .iter()
        .map(|&position| chunk_of(frames[position]).len())
        .sum();
    if total_payload_len % 4 == 1 {
        return Err(QrEnvelopeError::InvalidBase64UrlLength);
    }
    // Exact-size guard before decoding, as in the static path.
    if decoded_len_max(total_payload_len) > MAX_ANIMATED_QR_DECODED_JSON_BYTES {
        return Err(QrEnvelopeError::ExceedsAnimatedJsonBytes);
    }
    if total_payload_len > payload_out.len() {
        return Err(QrEnvelopeError::OutputTooSmall);
    }
    let mut payload_len = 0usize;
    for &position in &position_of_index[..total] {
        let chunk = &frames[position][chunk_of(frames[position])];
        payload_out[payload_len..payload_len + chunk.len()].copy_from_slice(chunk);
        payload_len += chunk.len();
    }
    let payload = &payload_out[..payload_len];
    let decoded = decode_base64url(payload, json_out).map_err(map_payload_decode_error)?;
    if sha256_hex(decoded).as_slice() != digest {
        return Err(QrEnvelopeError::AnimatedDigestMismatch);
    }
    if !is_valid_utf8(decoded) {
        return Err(QrEnvelopeError::InvalidUtf8);
    }
    require_json_container(decoded)?;
    Ok(QrEnvelope {
        payload_base64url: payload,
        payload_json: decoded,
    })
}

/// Encodes `payload_json` as a static `nsealr1:` envelope into `out`, returning
/// the written prefix. Mirrors the C++ `encode_qr_envelope_json`.
///
/// # Errors
///
/// [`QrEnvelopeError::ExceedsStaticJsonBytes`], [`QrEnvelopeError::InvalidUtf8`],
/// [`QrEnvelopeError::NotJsonContainer`], [`QrEnvelopeError::OutputTooSmall`].
pub fn encode_qr_envelope_json<'o>(
    payload_json: &[u8],
    out: &'o mut [u8],
) -> Result<&'o [u8], QrEnvelopeError> {
    if payload_json.len() > MAX_STATIC_QR_DECODED_JSON_BYTES {
        return Err(QrEnvelopeError::ExceedsStaticJsonBytes);
    }
    if !is_valid_utf8(payload_json) {
        return Err(QrEnvelopeError::InvalidUtf8);
    }
    require_json_container(payload_json)?;
    let total = PREFIX.len() + encoded_len(payload_json.len());
    if out.len() < total {
        return Err(QrEnvelopeError::OutputTooSmall);
    }
    out[..PREFIX.len()].copy_from_slice(PREFIX);
    encode_base64url(payload_json, &mut out[PREFIX.len()..total])
        .map_err(map_payload_decode_error)?;
    Ok(&out[..total])
}

/// Encodes `payload_json` as animated `nsealr1a:` frames, invoking `emit` once
/// per frame with (frame bytes, 0-based frame index, total frame count). Mirrors
/// the C++ `encode_animated_qr_envelope_json`, which returned a
/// `std::vector<std::string>`; the callback keeps this port allocation-free.
///
/// # Errors
///
/// See [`QrEnvelopeError`]; parity with the C++ rejection order (chunk size →
/// json size → UTF-8 → container → empty payload → frame count).
pub fn encode_animated_qr_envelope_json(
    payload_json: &[u8],
    chunk_size_chars: usize,
    emit: &mut dyn FnMut(&[u8], usize, usize),
) -> Result<(), QrEnvelopeError> {
    if chunk_size_chars == 0 {
        return Err(QrEnvelopeError::AnimatedChunkSizeZero);
    }
    if chunk_size_chars > MAX_ANIMATED_QR_FRAME_PAYLOAD_CHARS {
        return Err(QrEnvelopeError::AnimatedChunkTooLong);
    }
    if payload_json.len() > MAX_ANIMATED_QR_DECODED_JSON_BYTES {
        return Err(QrEnvelopeError::ExceedsAnimatedJsonBytes);
    }
    if !is_valid_utf8(payload_json) {
        return Err(QrEnvelopeError::InvalidUtf8);
    }
    require_json_container(payload_json)?;

    // The C++ heap-allocated the full base64url payload; this port stack-buffers
    // it (5.4 KiB, bounded by the animated JSON limit). The container check above
    // guarantees a non-empty JSON, so the payload is never empty (the C++ had a
    // dead "animated QR payload is empty" guard here; omitted as unreachable).
    let mut payload_buf = [0u8; encoded_len(MAX_ANIMATED_QR_DECODED_JSON_BYTES)];
    let payload =
        encode_base64url(payload_json, &mut payload_buf).map_err(map_payload_decode_error)?;
    let chunk_count = payload.len().div_ceil(chunk_size_chars);
    if chunk_count > MAX_ANIMATED_QR_FRAME_COUNT {
        return Err(QrEnvelopeError::AnimatedTooManyFrames);
    }

    let digest = sha256_hex(payload_json);
    // Frame scratch: prefix + digest + ":index/total:" + chunk + ":" + checksum.
    let mut frame = [0u8; ANIMATED_PREFIX.len()
        + DIGEST_HEX_LEN
        + 1
        + 20
        + 1
        + 20
        + 1
        + MAX_ANIMATED_QR_FRAME_PAYLOAD_CHARS
        + 1
        + CHECKSUM_HEX_LEN];
    for (offset, chunk) in payload.chunks(chunk_size_chars).enumerate() {
        let mut at = 0usize;
        let push = |frame: &mut [u8], at: &mut usize, bytes: &[u8]| {
            frame[*at..*at + bytes.len()].copy_from_slice(bytes);
            *at += bytes.len();
        };
        let mut decimal = [0u8; 20];
        push(&mut frame, &mut at, ANIMATED_PREFIX);
        push(&mut frame, &mut at, &digest);
        push(&mut frame, &mut at, b":");
        let index_text_len = write_decimal(&mut decimal, offset + 1).len();
        push(&mut frame, &mut at, &decimal[20 - index_text_len..]);
        push(&mut frame, &mut at, b"/");
        let total_text_len = write_decimal(&mut decimal, chunk_count).len();
        push(&mut frame, &mut at, &decimal[20 - total_text_len..]);
        push(&mut frame, &mut at, b":");
        push(&mut frame, &mut at, chunk);
        // Checksum over everything so far (the pre-image is the frame minus its
        // ":checksum" suffix; see parse_animated_qr_frame).
        let checksum_hex = sha256_hex(&frame[..at]);
        push(&mut frame, &mut at, b":");
        push(&mut frame, &mut at, &checksum_hex[..CHECKSUM_HEX_LEN]);
        emit(&frame[..at], offset, chunk_count);
    }
    Ok(())
}
/// Parses the legacy-size envelope with the shared strict event reader.
/// This copied preview record carries no execution authority. Detailed legacy
/// scanner error precedence is retired; invalid JSON/shape/range is malformed.
pub fn parse_qr_signing_request(payload_json: &[u8]) -> Result<QrSigningRequest, QrEnvelopeError> {
    use crate::event::{OperationLimits, ParsedRequest, RequestMethod};
    if payload_json.len() > MAX_DECODED_REQUEST_JSON_BYTES {
        return Err(QrEnvelopeError::ExceedsRequestJsonBytes);
    }
    let limits = OperationLimits {
        input_bytes: MAX_DECODED_REQUEST_JSON_BYTES,
        content_bytes: MAX_CONTENT_UTF8_BYTES,
        tags: MAX_TAG_COUNT,
        fields_per_tag: MAX_TAG_FIELDS_PER_TAG,
        field_bytes: MAX_TAG_FIELD_UTF8_BYTES,
        ..OperationLimits::conformance()
    };
    let parsed = ParsedRequest::parse(payload_json, limits)
        .map_err(|_| QrEnvelopeError::RequestJsonMalformed)?;
    if parsed.method() != RequestMethod::SignEvent {
        return Err(QrEnvelopeError::RequestBadMethod);
    }
    let event = parsed
        .event
        .as_ref()
        .ok_or(QrEnvelopeError::RequestEventTemplateRequired)?;
    let mut request = QrSigningRequest {
        version: 2,
        request_id: [0; MAX_REQUEST_ID_LENGTH],
        request_id_len: parsed.request_id().len(),
        has_params: true,
        has_event_template: true,
        event_template_json: parsed.raw_template,
        event_template: QrEventTemplate {
            created_at: event.created_at(),
            kind: i32::from(event.kind()),
            tags_json: event.raw_tags,
            tag_count: event.tag_count(),
        },
        content: [0; MAX_CONTENT_UTF8_BYTES],
        content_len: event.content().len(),
        tag_fields_text: [0; MAX_DECODED_REQUEST_JSON_BYTES],
        tag_fields_text_len: 0,
        tag_fields: [TagField {
            tag: 0,
            start: 0,
            end: 0,
        }; MAX_TAG_COUNT * MAX_TAG_FIELDS_PER_TAG],
        tag_field_count: 0,
    };
    request.request_id[..request.request_id_len].copy_from_slice(parsed.request_id().as_bytes());
    request.content[..request.content_len].copy_from_slice(event.content().as_bytes());
    for tag in 0..event.tag_count() {
        for field in event.tag(tag).expect("bounded tag index") {
            let start = request.tag_fields_text_len;
            let end = start + field.len();
            request.tag_fields_text[start..end].copy_from_slice(field.as_bytes());
            request.tag_fields[request.tag_field_count] = TagField { tag, start, end };
            request.tag_field_count += 1;
            request.tag_fields_text_len = end;
        }
    }
    Ok(request)
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use crate::qr::limits::{
        MAX_QR_RESPONSE_DISPLAY_CYCLES, MAX_SAFE_INTEGER, MAX_SERIAL_FRAME_BYTES,
        MAX_TOTAL_TAG_UTF8_BYTES,
    };
    use std::string::String;
    use std::vec::Vec;

    // Byte-for-byte fixtures copied from
    // specs/vectors/transports/qr-envelope-kind-1-basic.json (`envelope`,
    // `payload_base64url`).
    pub(crate) const KIND1_BASIC_ENVELOPE: &[u8] = include_bytes!(concat!(
        env!("OUT_DIR"),
        "/field-b69c96b873204e5c324385c0.txt"
    ));
    const KIND1_BASIC_PAYLOAD: &[u8] = include_bytes!(concat!(
        env!("OUT_DIR"),
        "/field-7bc474eb9fd65cd1f1cdfd09.txt"
    ));

    // Byte-for-byte fixture copied from
    // specs/vectors/transports/qr-envelope-kind-1-long-events-many-tags.json
    // (`envelope`): a maximal valid request (nine tags, 281-byte content).
    const KIND1_LONG_MANY_TAGS_ENVELOPE: &[u8] = include_bytes!(concat!(
        env!("OUT_DIR"),
        "/field-fd77c72125a90d057af49e71.txt"
    ));

    // Animated fixture copied from
    // specs/vectors/transports/qr-animated-response-kind-1-basic.json (`frames`,
    // `payload_base64url`; ANIMATED_JSON is the same fixture's `decoded` in the
    // canonical serialization pinned by the C++ kAnimatedQrResponseKind1BasicJson).
    pub(crate) const ANIMATED_FRAME_1: &[u8] = include_bytes!(concat!(
        env!("OUT_DIR"),
        "/field-cb806983fcebd0885ee3bd03.txt"
    ));
    pub(crate) const ANIMATED_FRAME_2: &[u8] = include_bytes!(concat!(
        env!("OUT_DIR"),
        "/field-be6cb4d91daa59ce1e0697cb.txt"
    ));
    pub(crate) const ANIMATED_FRAME_3: &[u8] = include_bytes!(concat!(
        env!("OUT_DIR"),
        "/field-f119cf383068a629770f4634.txt"
    ));
    pub(crate) const ANIMATED_PAYLOAD: &[u8] = include_bytes!(concat!(
        env!("OUT_DIR"),
        "/field-a6eb1c7c7419fbd99df6825c.txt"
    ));
    pub(crate) const ANIMATED_JSON: &[u8] = include_bytes!(concat!(
        env!("OUT_DIR"),
        "/field-155b661f07a03facadcc50eb.txt"
    ));

    // Shared-invalid QR-envelope fixtures copied from specs/vectors/invalid/
    // qr-envelope-{padded,malformed,invalid-utf8}.json (`envelope`); the oversized
    // fixture (qr-envelope-oversized.json) is `nsealr1:` + 940 'A's (948 bytes),
    // rebuilt programmatically below, byte-identical to the fixture.
    const INVALID_PADDED: &[u8] = include_bytes!(concat!(
        env!("OUT_DIR"),
        "/field-bcf1804c40fb794ae802d43c.txt"
    ));
    const INVALID_MALFORMED: &[u8] = b"nsealr:abc";
    const INVALID_UTF8: &[u8] = b"nsealr1:_w";

    fn oversized_envelope() -> Vec<u8> {
        let mut envelope = Vec::from(PREFIX);
        envelope.extend(core::iter::repeat_n(b'A', 940));
        assert_eq!(envelope.len(), 948); // matches the fixture byte count
        envelope
    }

    pub(crate) fn decode_static(envelope: &[u8]) -> Result<(Vec<u8>, Vec<u8>), QrEnvelopeError> {
        let mut json = [0u8; MAX_STATIC_QR_DECODED_JSON_BYTES];
        let decoded = decode_qr_envelope(envelope, &mut json)?;
        Ok((
            Vec::from(decoded.payload_base64url),
            Vec::from(decoded.payload_json),
        ))
    }

    pub(crate) fn decode_animated(frames: &[&[u8]]) -> Result<(Vec<u8>, Vec<u8>), QrEnvelopeError> {
        let mut payload = [0u8; encoded_len(MAX_ANIMATED_QR_DECODED_JSON_BYTES)];
        let mut json = [0u8; MAX_ANIMATED_QR_DECODED_JSON_BYTES];
        let decoded = decode_animated_qr_envelope_frames(frames, &mut payload, &mut json)?;
        Ok((
            Vec::from(decoded.payload_base64url),
            Vec::from(decoded.payload_json),
        ))
    }

    pub(crate) fn encode_animated_to_vec(
        payload_json: &[u8],
        chunk_size_chars: usize,
    ) -> Result<Vec<Vec<u8>>, QrEnvelopeError> {
        let mut frames = Vec::new();
        encode_animated_qr_envelope_json(payload_json, chunk_size_chars, &mut |frame, _, _| {
            frames.push(Vec::from(frame));
        })?;
        Ok(frames)
    }

    fn contains(haystack: &[u8], needle: &[u8]) -> bool {
        haystack.windows(needle.len()).any(|w| w == needle)
    }

    /// Builds a syntactically valid animated frame (correct per-frame checksum)
    /// from a digest field, an `index/total` text, and a chunk.
    fn build_frame(digest: &[u8], index_total: &[u8], chunk: &[u8]) -> Vec<u8> {
        let mut preimage = Vec::from(ANIMATED_PREFIX);
        preimage.extend_from_slice(digest);
        preimage.push(b':');
        preimage.extend_from_slice(index_total);
        preimage.push(b':');
        preimage.extend_from_slice(chunk);
        let hex = sha256_hex(&preimage);
        let mut frame = preimage;
        frame.push(b':');
        frame.extend_from_slice(&hex[..CHECKSUM_HEX_LEN]);
        frame
    }

    // C++ test_qr_envelope_decodes_shared_vector.
    #[test]
    fn qr_envelope_decodes_shared_vector() {
        let (payload, json) = decode_static(KIND1_BASIC_ENVELOPE).unwrap();
        assert_eq!(payload, KIND1_BASIC_PAYLOAD);
        assert!(contains(&json, br#""request_id":"req-kind-1-basic""#));
        assert!(contains(&json, br#""method":"sign_event""#));
    }

    // C++ test_animated_qr_envelope_decodes_shared_vector.
    #[test]
    fn animated_qr_envelope_decodes_shared_vector() {
        let (payload, json) =
            decode_animated(&[ANIMATED_FRAME_1, ANIMATED_FRAME_2, ANIMATED_FRAME_3]).unwrap();
        assert_eq!(payload, ANIMATED_PAYLOAD);
        assert_eq!(json, ANIMATED_JSON);
    }

    // C++ test_qr_envelope_encodes_signed_response_vectors_without_signing.
    #[test]
    fn qr_envelope_encodes_signed_response_vectors_without_signing() {
        let mut buf = [0u8; PREFIX.len() + encoded_len(MAX_ANIMATED_QR_DECODED_JSON_BYTES)];
        let static_envelope = encode_qr_envelope_json(ANIMATED_JSON, &mut buf).unwrap();
        let mut expected = Vec::from(PREFIX);
        expected.extend_from_slice(ANIMATED_PAYLOAD);
        assert_eq!(static_envelope, expected);

        let frames =
            encode_animated_to_vec(ANIMATED_JSON, MAX_ANIMATED_QR_FRAME_PAYLOAD_CHARS).unwrap();
        assert_eq!(
            frames,
            [
                Vec::from(ANIMATED_FRAME_1),
                Vec::from(ANIMATED_FRAME_2),
                Vec::from(ANIMATED_FRAME_3)
            ],
        );

        let static_envelope = Vec::from(static_envelope);
        let (_, json) = decode_static(&static_envelope).unwrap();
        assert_eq!(json, ANIMATED_JSON);
        let (_, json) =
            decode_animated(&frames.iter().map(Vec::as_slice).collect::<Vec<_>>()).unwrap();
        assert_eq!(json, ANIMATED_JSON);
    }

    // C++ test_qr_envelope_parses_sign_event_request_metadata.
    #[test]
    fn qr_envelope_parses_sign_event_request_metadata() {
        let (_, json) = decode_static(KIND1_BASIC_ENVELOPE).unwrap();
        let request = parse_qr_signing_request(&json).unwrap();
        assert_eq!(request.version, 2);
        assert_eq!(
            request.request_id(),
            include_bytes!(concat!(
                env!("OUT_DIR"),
                "/field-ef8f1cdc03d2b7514fa6d71d.txt"
            ))
        );
        assert_eq!(request.method(), "sign_event");
        assert!(request.has_params);
    }

    // C++ test_qr_envelope_extracts_event_template_boundary.
    #[test]
    fn qr_envelope_extracts_event_template_boundary() {
        let (_, json) = decode_static(KIND1_BASIC_ENVELOPE).unwrap();
        let request = parse_qr_signing_request(&json).unwrap();
        assert!(request.has_event_template);
        let (start, end) = request.event_template_json;
        let template = &json[start..end];
        assert!(contains(template, br#""kind":1"#));
        assert!(contains(
            template,
            br#""content":"nSealr fixture: basic kind 1 event.""#
        ));
    }

    // C++ test_qr_envelope_parses_event_template_fields.
    #[test]
    fn qr_envelope_parses_event_template_fields() {
        let (_, json) = decode_static(KIND1_BASIC_ENVELOPE).unwrap();
        let request = parse_qr_signing_request(&json).unwrap();
        assert_eq!(request.event_template.created_at, 1_710_000_000);
        assert_eq!(request.event_template.kind, 1);
        assert_eq!(
            request.content(),
            include_bytes!(concat!(
                env!("OUT_DIR"),
                "/field-1b208157932014fa782660ac.txt"
            ))
        );
        let (start, end) = request.event_template.tags_json;
        assert_eq!(&json[start..end], b"[]");
    }

    // C++ test_qr_signing_request_tolerates_escaped_event_content.
    #[test]
    fn qr_signing_request_tolerates_escaped_event_content() {
        let json = br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event","params":{"event_template":{"created_at":1710000000,"kind":1,"tags":[],"content":"Quote: \"nostr\"\nNext line"}}}"#;
        let request = parse_qr_signing_request(json).unwrap();
        assert!(request.has_event_template);
        assert_eq!(request.content(), b"Quote: \"nostr\"\nNext line");
        let (start, end) = request.event_template_json;
        assert!(contains(
            &json[start..end],
            br#""content":"Quote: \"nostr\"\nNext line""#,
        ));
    }

    // C++ test_qr_signing_request_preserves_json_unicode_escapes (the
    // request-level assertions; the review-pages half of the C++ case drives
    // qr_review.cpp, which is M-T3.6 surface — deferred to that milestone).
    #[test]
    fn qr_signing_request_preserves_json_unicode_escapes() {
        // The C++ fed a raw string, so the JSON carries the *escape sequences*
        // (backslash-u00e8, backslash-uD83D backslash-uDE00) literally; the
        // parser decodes them to UTF-8.
        let json = br#"{"version":2,"request_id":"req-unicode-escapes","method":"sign_event","params":{"event_template":{"created_at":1710000400,"kind":1,"tags":[["t","caf\u00e8"],["emoji","\uD83D\uDE00"]],"content":"caf\u00e8 \uD83D\uDE00"}}}"#;
        let request = parse_qr_signing_request(json).unwrap();
        assert_eq!(request.content(), "caf\u{e8} \u{1f600}".as_bytes());
        assert_eq!(request.event_template.tag_count, 2);
        let tag0: Vec<&[u8]> = request.tag(0).collect();
        assert_eq!(tag0, [&b"t"[..], "caf\u{e8}".as_bytes()]);
        let tag1: Vec<&[u8]> = request.tag(1).collect();
        assert_eq!(tag1, [&b"emoji"[..], "\u{1f600}".as_bytes()]);
    }

    // C++ test_qr_envelope_rejections.
    #[test]
    fn qr_envelope_rejections() {
        assert_eq!(
            decode_static(b"nostr:abc").unwrap_err(),
            QrEnvelopeError::MissingPrefix,
        );
        assert_eq!(
            decode_static(b"nsealr1:abc=").unwrap_err(),
            QrEnvelopeError::PayloadNotBase64Url,
        );
        assert_eq!(
            decode_static(b"nsealr1:not+base64url").unwrap_err(),
            QrEnvelopeError::PayloadNotBase64Url,
        );
        assert_eq!(
            decode_static(b"nsealr1:A").unwrap_err(),
            QrEnvelopeError::InvalidBase64UrlLength,
        );
        assert_eq!(
            decode_static(b"nsealr1:bm90LWpzb24").unwrap_err(),
            QrEnvelopeError::NotJsonContainer,
        );
    }

    // C++ test_qr_envelope_rejects_shared_invalid_qr_vectors.
    #[test]
    fn qr_envelope_rejects_shared_invalid_qr_vectors() {
        assert_eq!(
            decode_static(&oversized_envelope()).unwrap_err(),
            QrEnvelopeError::ExceedsStaticJsonBytes,
        );
        assert_eq!(
            decode_static(INVALID_PADDED).unwrap_err(),
            QrEnvelopeError::PayloadNotBase64Url,
        );
        assert_eq!(
            decode_static(INVALID_MALFORMED).unwrap_err(),
            QrEnvelopeError::MissingPrefix,
        );
        assert_eq!(
            decode_static(INVALID_UTF8).unwrap_err(),
            QrEnvelopeError::InvalidUtf8,
        );
    }

    // C++ test_animated_qr_envelope_rejections.
    #[test]
    fn animated_qr_envelope_rejections() {
        assert_eq!(decode_animated(&[]).unwrap_err(), QrEnvelopeError::NoFrames);
        assert_eq!(
            decode_animated(&[ANIMATED_FRAME_2, ANIMATED_FRAME_3]).unwrap_err(),
            QrEnvelopeError::AnimatedFramesNotContiguous,
        );
        let mut tampered = Vec::from(ANIMATED_FRAME_1);
        let last = tampered.last_mut().unwrap();
        *last = if *last == b'0' { b'1' } else { b'0' };
        assert_eq!(
            decode_animated(&[tampered.as_slice(), ANIMATED_FRAME_2, ANIMATED_FRAME_3])
                .unwrap_err(),
            QrEnvelopeError::AnimatedChecksumMismatch,
        );
        let frame: &[u8] = b"nsealr1a:0000000000000000000000000000000000000000000000000000000000000000:1/65:AA:0000000000000000";
        assert_eq!(
            decode_animated(&[frame]).unwrap_err(),
            QrEnvelopeError::AnimatedTooManyFrames,
        );
        let mut oversized_chunk_frame = Vec::from(
            &b"nsealr1a:0000000000000000000000000000000000000000000000000000000000000000:1/1:"[..],
        );
        oversized_chunk_frame.extend(core::iter::repeat_n(
            b'A',
            MAX_ANIMATED_QR_FRAME_PAYLOAD_CHARS + 1,
        ));
        oversized_chunk_frame.extend_from_slice(b":0000000000000000");
        assert_eq!(
            decode_animated(&[oversized_chunk_frame.as_slice()]).unwrap_err(),
            QrEnvelopeError::AnimatedChunkTooLong,
        );
        let frame: &[u8] = b"nsealr1a:0000000000000000000000000000000000000000000000000000000000000000:184467440737095516160/1:AA:0000000000000000";
        assert_eq!(
            decode_animated(&[frame]).unwrap_err(),
            QrEnvelopeError::AnimatedBadIndexValue,
        );
    }

    // C++ test_qr_envelope_encoder_rejections.
    #[test]
    fn qr_envelope_encoder_rejections() {
        let mut big = [0u8; 8 * 1024];
        let mut oversized_static = Vec::from(&br#"{"x":""#[..]);
        oversized_static.extend(core::iter::repeat_n(b'x', MAX_STATIC_QR_DECODED_JSON_BYTES));
        oversized_static.extend_from_slice(br#""}"#);
        assert_eq!(
            encode_qr_envelope_json(&oversized_static, &mut big).unwrap_err(),
            QrEnvelopeError::ExceedsStaticJsonBytes,
        );

        let mut oversized_animated = Vec::from(&br#"{"x":""#[..]);
        oversized_animated.extend(core::iter::repeat_n(
            b'x',
            MAX_ANIMATED_QR_DECODED_JSON_BYTES,
        ));
        oversized_animated.extend_from_slice(br#""}"#);
        assert_eq!(
            encode_animated_to_vec(&oversized_animated, MAX_ANIMATED_QR_FRAME_PAYLOAD_CHARS)
                .unwrap_err(),
            QrEnvelopeError::ExceedsAnimatedJsonBytes,
        );

        assert_eq!(
            encode_animated_to_vec(b"{}", 0).unwrap_err(),
            QrEnvelopeError::AnimatedChunkSizeZero,
        );
        assert_eq!(
            encode_animated_to_vec(b"{}", MAX_ANIMATED_QR_FRAME_PAYLOAD_CHARS + 1).unwrap_err(),
            QrEnvelopeError::AnimatedChunkTooLong,
        );
        assert_eq!(
            encode_qr_envelope_json(b"{\"x\":\"\xff\"}", &mut big).unwrap_err(),
            QrEnvelopeError::InvalidUtf8,
        );
    }

    // C++ test_qr_limits_match_shared_profile: every constant pinned against the
    // shared limits profile specs/vectors/limits/nsealr-v0.json (`limits`), plus
    // the display-cycles constant from qr_response_display.hpp.
    #[test]
    fn qr_limits_match_shared_profile() {
        assert_eq!(MAX_REQUEST_ID_LENGTH, 128);
        assert_eq!(MAX_DECODED_REQUEST_JSON_BYTES, 704);
        assert_eq!(MAX_STATIC_QR_DECODED_JSON_BYTES, 704);
        assert_eq!(MAX_ANIMATED_QR_DECODED_JSON_BYTES, 4096);
        assert_eq!(MAX_ANIMATED_QR_FRAME_PAYLOAD_CHARS, 256);
        assert_eq!(MAX_ANIMATED_QR_FRAME_COUNT, 64);
        assert_eq!(MAX_SERIAL_FRAME_BYTES, 1024);
        assert_eq!(MAX_CONTENT_UTF8_BYTES, 512);
        assert_eq!(MAX_TAG_COUNT, 16);
        assert_eq!(MAX_TAG_FIELDS_PER_TAG, 8);
        assert_eq!(MAX_TAG_FIELD_UTF8_BYTES, 64);
        assert_eq!(MAX_TOTAL_TAG_UTF8_BYTES, 4096);
        assert_eq!(MAX_SAFE_INTEGER, 9_007_199_254_740_991);
        assert_eq!(MAX_QR_RESPONSE_DISPLAY_CYCLES, 16);
    }

    // C++ test_qr_signing_request_rejections.
    #[test]
    fn qr_signing_request_rejections() {
        let cases: &[(&[u8], QrEnvelopeError)] = &[
            (
                br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event","params":{}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"bad id","method":"sign_event","params":{}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"req-kind-1-basic","method":"get_public_key"}"#,
                QrEnvelopeError::RequestBadMethod,
            ),
            (
                br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event"}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event","params":{}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event","params":{"event_template":[]}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event","params":{"event_template":{"created_at":1710000000,"kind":1,"tags":[],"content":"","id":"00"}}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event","params":{"event_template":{"created_at":1710000000,"kind":1,"tags":[],"content":"","pubkey":"00"}}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event","params":{"event_template":{"created_at":1710000000,"kind":1,"tags":[],"content":"","sig":"00"}}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event","params":{"event_template":{"kind":1,"tags":[],"content":""}}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event","params":{"event_template":{"created_at":1710000000,"kind":"1","tags":[],"content":""}}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event","params":{"event_template":{"created_at":1710000000,"kind":1,"tags":{},"content":""}}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event","params":{"event_template":{"created_at":1710000000,"kind":1,"tags":[]}}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"req-invalid-unicode","method":"sign_event","params":{"event_template":{"created_at":1710000000,"kind":1,"tags":[],"content":"\uD83D"}}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
            (
                br#"{"version":2,"request_id":"req-invalid-unicode","method":"sign_event","params":{"event_template":{"created_at":1710000000,"kind":1,"tags":[],"content":"\uDE00"}}}"#,
                QrEnvelopeError::RequestJsonMalformed,
            ),
        ];
        for (index, (json, expected)) in cases.iter().enumerate() {
            assert_eq!(
                parse_qr_signing_request(json).unwrap_err(),
                *expected,
                "case {index}",
            );
        }
    }

    // C++ test_qr_signing_request_rejects_shared_invalid_request_vectors. Each
    // request_json literal is copied byte-for-byte from the matching
    // specs/vectors/invalid/<name>.json fixture (`request`, canonical
    // serialization as pinned by the C++ generated vector header).
    #[test]
    fn qr_signing_request_rejects_shared_invalid_request_vectors() {
        let vectors: &[(&str, &[u8])] = &[
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-24c565533b2c031cce3404d6.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-88270f2336c3bec26b9b8102.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-343dfba9674203b8ae5e049f.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-692fd02b9af23295ea9e3f54.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-a9f28b492e9d40dcbb54c161.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-392edda1d20e90455b184512.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-a33c1ff0bff84fd58102c97e.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-8035bcb7ff6c7b69d10d9005.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-d01a036c56103bac5db2833c.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-e2d8d202b6a418eb3e27a8e4.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-a13fcba3d0d0645295d4b83e.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-6d36b8ad33903e0c72537245.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-0187d5ed5d3b8b77e48ef519.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-567d875b28f2f1c9dcd84c4c.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-fc6215b9edc02850921efd59.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-a639ba28eef6d1ce4f06e1bd.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-01183b580c2afd82aee32f20.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-245bbf0348274249096379c6.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-f3f5f97a7f0c05599c615490.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-4b05e434cfd67cd9a75ecb4b.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-5936ea3644e2c886e6c18700.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-f1b6d702634ac412d6ac89ce.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-88730efa77091611955c71b7.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-bfb321d6d7c2a5aa3703dd9c.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-85a8b70c362257648b261d39.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-0af857de4a48d6ec2d683150.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-47633ca2891092f5a178a3cf.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-4e2e8353b45bb26b551944be.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-a8e4d74626214bd56a3873ba.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-a0ead41b24fcf49b107f5ee6.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-e5248f375a7cdce2c8aa721d.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-15a804309e663e5eb2bc4791.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-8c23f2b7b75b9f3fdf57fc8e.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-0a36357aaf25b74bcc5a133d.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-8db3104d26d8106b5f55d616.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-2cef7d540519e1d0667de472.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-3c7557ad4529bd78fe06da9a.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-6b33788fa062b8aa8c163525.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-bd723d16fe4c12661fa410af.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-9f12fcb31538612f9548d6c4.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-c557f62900487f92ed686095.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-694f49d5b74d9e18fb5d344e.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-96b3432119f33bc1e3678da0.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-85d66b86eaf4b9800deff84a.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-a39b76315e5cc2d5abf10106.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-91956a747800a262375e2b7e.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-0c791d113112c983e86db3ba.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-d398a64ecb2d39f66153a5b1.txt"
                )),
            ),
            (
                include_str!(concat!(
                    env!("OUT_DIR"),
                    "/field-f87a96b2d9df38ed94b99fe4.txt"
                )),
                include_bytes!(concat!(
                    env!("OUT_DIR"),
                    "/field-bfe77a9543df538a8b0265f4.txt"
                )),
            ),
        ];
        for (name, json) in vectors {
            assert!(
                parse_qr_signing_request(json).is_err(),
                "unexpectedly accepted invalid request vector: {name}",
            );
        }
    }

    // --- Supplementary direct tests (fixture replay + branch coverage) ---

    // Replays specs/vectors/transports/qr-envelope-kind-1-long-events-many-tags.json
    // end to end: decode + full signing-request parse of a maximal valid request.
    #[test]
    fn long_events_many_tags_shared_vector_parses() {
        let (_, json) = decode_static(KIND1_LONG_MANY_TAGS_ENVELOPE).unwrap();
        let request = parse_qr_signing_request(&json).unwrap();
        assert_eq!(
            request.request_id(),
            include_bytes!(concat!(
                env!("OUT_DIR"),
                "/field-1371212056e9e66ac9642836.txt"
            ))
        );
        assert_eq!(request.event_template.created_at, 1_710_000_120);
        assert_eq!(request.event_template.tag_count, 9);
        let tag0: Vec<&[u8]> = request.tag(0).collect();
        assert_eq!(tag0.len(), 4);
        assert_eq!(tag0[0], b"e");
        assert_eq!(tag0[2], b"");
        assert_eq!(tag0[3], b"root");
        let tag8: Vec<&[u8]> = request.tag(8).collect();
        assert_eq!(tag8, [&b"t"[..], &b"test"[..]]);
        assert_eq!(request.content().len(), 281);
    }

    #[test]
    fn animated_frames_accepted_out_of_order() {
        let (payload, json) =
            decode_animated(&[ANIMATED_FRAME_3, ANIMATED_FRAME_1, ANIMATED_FRAME_2]).unwrap();
        assert_eq!(payload, ANIMATED_PAYLOAD);
        assert_eq!(json, ANIMATED_JSON);
    }

    #[test]
    fn animated_structural_rejections() {
        let zero_digest = [b'0'; DIGEST_HEX_LEN];
        // Wrong prefix.
        assert_eq!(
            decode_animated(&[&b"nsealr1:AA"[..]]).unwrap_err(),
            QrEnvelopeError::AnimatedMissingPrefix,
        );
        // Not five fields.
        assert_eq!(
            decode_animated(&[&b"nsealr1a:00:1/1:AA"[..]]).unwrap_err(),
            QrEnvelopeError::AnimatedMalformed,
        );
        assert_eq!(
            decode_animated(&[&b"nsealr1a:00:1/1:AA:00:extra"[..]]).unwrap_err(),
            QrEnvelopeError::AnimatedMalformed,
        );
        // Bad digest (short / uppercase).
        assert_eq!(
            decode_animated(&[&b"nsealr1a:0000:1/1:AA:0000000000000000"[..]]).unwrap_err(),
            QrEnvelopeError::AnimatedBadDigest,
        );
        let mut upper_digest = Vec::from(ANIMATED_FRAME_1);
        upper_digest[ANIMATED_PREFIX.len()] = b'E';
        assert_eq!(
            decode_animated(&[upper_digest.as_slice()]).unwrap_err(),
            QrEnvelopeError::AnimatedBadDigest,
        );
        // Bad checksum format.
        let mut frame = Vec::from(&b"nsealr1a:"[..]);
        frame.extend_from_slice(&zero_digest);
        frame.extend_from_slice(b":1/1:AA:00");
        assert_eq!(
            decode_animated(&[frame.as_slice()]).unwrap_err(),
            QrEnvelopeError::AnimatedBadChecksumFormat,
        );
        // Index/total shape errors: no slash, two slashes.
        for index_total in [&b"11"[..], &b"1/1/1"[..]] {
            let mut frame = Vec::from(&b"nsealr1a:"[..]);
            frame.extend_from_slice(&zero_digest);
            frame.push(b':');
            frame.extend_from_slice(index_total);
            frame.extend_from_slice(b":AA:0000000000000000");
            assert_eq!(
                decode_animated(&[frame.as_slice()]).unwrap_err(),
                QrEnvelopeError::AnimatedBadIndexShape,
                "index_total {index_total:?}",
            );
        }
        // Decimal errors: empty, leading zero, non-digit.
        for index_total in [&b"/1"[..], &b"01/1"[..], &b"1/x"[..]] {
            let mut frame = Vec::from(&b"nsealr1a:"[..]);
            frame.extend_from_slice(&zero_digest);
            frame.push(b':');
            frame.extend_from_slice(index_total);
            frame.extend_from_slice(b":AA:0000000000000000");
            assert_eq!(
                decode_animated(&[frame.as_slice()]).unwrap_err(),
                QrEnvelopeError::AnimatedBadIndexValue,
                "index_total {index_total:?}",
            );
        }
        // index > total.
        let mut frame = Vec::from(&b"nsealr1a:"[..]);
        frame.extend_from_slice(&zero_digest);
        frame.extend_from_slice(b":2/1:AA:0000000000000000");
        assert_eq!(
            decode_animated(&[frame.as_slice()]).unwrap_err(),
            QrEnvelopeError::AnimatedIndexOutOfRange,
        );
        // Chunk not base64url.
        let mut frame = Vec::from(&b"nsealr1a:"[..]);
        frame.extend_from_slice(&zero_digest);
        frame.extend_from_slice(b":1/1:A+:0000000000000000");
        assert_eq!(
            decode_animated(&[frame.as_slice()]).unwrap_err(),
            QrEnvelopeError::AnimatedChunkNotBase64Url,
        );
    }

    #[test]
    fn animated_frame_set_rejections() {
        // Duplicate index (frame 1 twice, total 3): count==total but duplicate.
        assert_eq!(
            decode_animated(&[ANIMATED_FRAME_1, ANIMATED_FRAME_1, ANIMATED_FRAME_2]).unwrap_err(),
            QrEnvelopeError::AnimatedFramesNotContiguous,
        );
        // Mixed digest: a self-consistent frame 2 with a different digest.
        let other_digest = [b'f'; DIGEST_HEX_LEN];
        let mixed = build_frame(&other_digest, b"2/3", b"AA");
        assert_eq!(
            decode_animated(&[ANIMATED_FRAME_1, mixed.as_slice(), ANIMATED_FRAME_3]).unwrap_err(),
            QrEnvelopeError::AnimatedFrameSetMismatch,
        );
    }

    #[test]
    fn animated_digest_and_length_rejections() {
        // "e30" decodes to "{}"; digest field is all zeros (valid hex, wrong value).
        let zero_digest = [b'0'; DIGEST_HEX_LEN];
        let frame = build_frame(&zero_digest, b"1/1", b"e30");
        assert_eq!(
            decode_animated(&[frame.as_slice()]).unwrap_err(),
            QrEnvelopeError::AnimatedDigestMismatch,
        );

        // Reassembled payload with len % 4 == 1 (chunks "e3" + "0aa" -> "e30aa").
        let f1 = build_frame(&zero_digest, b"1/2", b"e3");
        let f2 = build_frame(&zero_digest, b"2/2", b"0aa");
        assert_eq!(
            decode_animated(&[f1.as_slice(), f2.as_slice()]).unwrap_err(),
            QrEnvelopeError::InvalidBase64UrlLength,
        );
    }

    #[test]
    fn animated_payload_content_rejections() {
        // Non-UTF-8 payload: "_w" decodes to [0xFF]; use the real digest of [0xFF]
        // so the digest check passes and the UTF-8 check is reached.
        let real_digest = sha256_hex(&[0xffu8]);
        let frame = build_frame(&real_digest, b"1/1", b"_w");
        assert_eq!(
            decode_animated(&[frame.as_slice()]).unwrap_err(),
            QrEnvelopeError::InvalidUtf8,
        );

        // Valid UTF-8 but not a JSON container: "ok" -> "b2s".
        let real_digest = sha256_hex(b"ok");
        let frame = build_frame(&real_digest, b"1/1", b"b2s");
        assert_eq!(
            decode_animated(&[frame.as_slice()]).unwrap_err(),
            QrEnvelopeError::NotJsonContainer,
        );

        // Non-canonical trailing bits: "e3" + "1" would be len 3 (ok%4) — use "e31"
        // whose final char has non-zero trailing bits ('1' = 53 -> bits 110101,
        // 3 chars = 18 bits, 2 bytes + 2 leftover bits = 01 != 0).
        let real_digest = sha256_hex(b"{}"); // digest never reached
        let frame = build_frame(&real_digest, b"1/1", b"e31");
        assert_eq!(
            decode_animated(&[frame.as_slice()]).unwrap_err(),
            QrEnvelopeError::InvalidTrailingBits,
        );

        // Oversized decoded JSON via many max-size chunks of 'A's: 4096+ decoded
        // bytes from 5464 payload chars (22 chunks of 256 -> 5632 chars -> 4224
        // bytes decoded > 4096).
        let chunk = [b'A'; MAX_ANIMATED_QR_FRAME_PAYLOAD_CHARS];
        let zero_digest = [b'0'; DIGEST_HEX_LEN];
        let mut frames = Vec::new();
        for index in 1..=22usize {
            let index_total = std::format!("{index}/22");
            frames.push(build_frame(&zero_digest, index_total.as_bytes(), &chunk));
        }
        assert_eq!(
            decode_animated(&frames.iter().map(Vec::as_slice).collect::<Vec<_>>()).unwrap_err(),
            QrEnvelopeError::ExceedsAnimatedJsonBytes,
        );

        // Round-trip sanity for the frame builder used above.
        let frames = encode_animated_to_vec(b"{}", 64).unwrap();
        let (_, json) =
            decode_animated(&frames.iter().map(Vec::as_slice).collect::<Vec<_>>()).unwrap();
        assert_eq!(json, b"{}");
    }

    #[test]
    fn animated_encoder_rejects_too_many_frames_and_bad_payloads() {
        // 102-byte JSON at chunk size 1 -> 136 chunks > 64 frames.
        let mut json = Vec::from(&b"["[..]);
        json.extend(core::iter::repeat_n(b'1', 100));
        json.push(b']');
        assert_eq!(
            encode_animated_to_vec(&json, 1).unwrap_err(),
            QrEnvelopeError::AnimatedTooManyFrames,
        );
        assert_eq!(
            encode_animated_to_vec(b"not json", 64).unwrap_err(),
            QrEnvelopeError::NotJsonContainer,
        );
        assert_eq!(
            encode_animated_to_vec(b"{\"x\":\"\xff\"}", 64).unwrap_err(),
            QrEnvelopeError::InvalidUtf8,
        );
    }

    #[test]
    fn static_encoder_and_container_shapes() {
        // Arrays are accepted; leading/trailing ASCII whitespace tolerated.
        let mut buf = [0u8; 1024];
        let envelope = encode_qr_envelope_json(b" [1,2] \n", &mut buf).unwrap();
        assert!(envelope.starts_with(b"nsealr1:"));
        // Too-short (< 2 chars trimmed) is not a container.
        assert_eq!(
            encode_qr_envelope_json(b" { ", &mut buf).unwrap_err(),
            QrEnvelopeError::NotJsonContainer,
        );
        // Trailing-bits canonicality is enforced on static decode.
        assert_eq!(
            decode_static(b"nsealr1:AB").unwrap_err(),
            QrEnvelopeError::InvalidTrailingBits,
        );
        // OutputTooSmall from the static encoder.
        let mut tiny = [0u8; 4];
        assert_eq!(
            encode_qr_envelope_json(b"{}", &mut tiny).unwrap_err(),
            QrEnvelopeError::OutputTooSmall,
        );
    }

    // Direct coverage of the request-parser tolerance rules the C++ exercises via
    // its JSON scanner: whitespace, the full escape set, nested containers skipped
    // with strict schema validation.
    #[test]
    fn request_parser_tolerances() {
        // Whitespace everywhere; escape set \" \\ \/ \b \f \n \r \t in content.
        let json = b" { \"version\" : 2 , \"request_id\" : \"req-ws\" , \"method\" : \"sign_event\" , \"params\" : { \"event_template\" : { \"created_at\" : 1 , \"kind\" : 0 , \"tags\" : [ ] , \"content\" : \"q\\\"b\\\\s\\/f\\bg\\fh\\nn\\rr\\tt\" } } } ";
        let request = parse_qr_signing_request(json).unwrap();
        assert_eq!(request.content(), b"q\"b\\s/f\x08g\x0ch\nn\rr\tt");
        assert_eq!(request.event_template.kind, 0);

        // Nested containers inside strings are data; a nested object inside content
        // passes untouched (C++ parse_simple_json_string semantics).
        let json = br#"{"version":2,"request_id":"req-nested","method":"sign_event","params":{"event_template":{"created_at":1710000000,"kind":1,"tags":[["a","{[not json}"]],"content":"{\"nested\":[1,2,{}]}"}}}"#;
        let request = parse_qr_signing_request(json).unwrap();
        assert_eq!(request.event_template.tag_count, 1);

        // Empty top-level object -> version required.
        assert_eq!(
            parse_qr_signing_request(b"{}").unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );

        // Literals (true/false/null) parse as top-level value tokens; the
        // unknown-field check still fires.
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"sign_event","params":{},"extra":null}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );

        // A key longer than any known member name is an unknown field (the
        // decoder rejects it at the known-key bound).
        assert_eq!(
            parse_qr_signing_request(br#"{"version":2,"a_key_longer_than_any_known_member":1}"#)
                .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );

        // String values everywhere a non-string is expected: version as a string
        // is a version mismatch, params as a string is a missing params object,
        // and string-valued unknown members (top-level and template) are still
        // unknown-field errors.
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":"1","request_id":"r","method":"sign_event","params":{}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"sign_event","params":"x"}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
        assert_eq!(
            parse_qr_signing_request(br#"{"version":2,"extra":"v"}"#).unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":1,"kind":1,"tags":[],"content":"","extra":"v"}}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );

        // A method value longer than the comparison buffer is just a mismatch.
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"a_method_longer_than_the_buffer","params":{}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );

        // params with an unknown member (event_template present too).
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":1,"kind":1,"tags":[],"content":""},"other":1}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );

        // event_template with an unknown (non-forbidden) member.
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":1,"kind":1,"tags":[],"content":"","extra":1}}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
    }

    #[test]
    fn request_parser_grammar_rejections() {
        let cases: &[&[u8]] = &[
            b"[]",                          // not an object
            b"",                            // empty
            b"{\"version\"1}",              // missing ':'
            b"{\"version\":2 \"x\":2}",     // bad separator
            b"{\"version\":}",              // missing value
            b"{\"version\":either}",        // bad literal
            b"{\"version\":-}",             // bad number
            b"{\"version\":2}extra",        // trailing data
            b"{\"unterminated",             // unterminated key string
            b"{\"bad\\escape\":1}",         // invalid escape
            b"{\"trunc\\",                  // truncated escape
            b"{\"ctl\x01\":1}",             // control character in string
            b"{\"k\":{\"unterminated\":1}", // unterminated container
            b"{\"k\":[1",                   // unterminated array container
            b"{\"k\":",                     // value missing at end of input
            b"{\"version\":2,\"request_id\":\"r\",\"method\":\"sign_event\",\"params\":{\"event_template\":{\"created_at\":18446744073709551616,\"kind\":1,\"tags\":[],\"content\":\"\"}}}", // u64 overflow
        ];
        for (index, json) in cases.iter().enumerate() {
            assert!(
                parse_qr_signing_request(json).is_err(),
                "case {index} unexpectedly accepted",
            );
        }
        // Grammar failures inside specific member values, exercising each
        // scanner error edge: bad escape in request_id / method values, and a
        // missing ':' inside params and event_template sub-objects (their outer
        // container skip only depth-checks, so the sub-parse reports it).
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"\q","method":"sign_event","params":{}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"\q","params":{}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
        assert_eq!(
            parse_qr_signing_request(br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template" 1}}"#)
                .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
        assert_eq!(
            parse_qr_signing_request(br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at" 1}}}"#)
                .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
        // A bad literal as the content value: invisible to the outer container
        // skip (which only validates strings/depth), caught by the sub-parse.
        assert_eq!(
            parse_qr_signing_request(br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":1,"kind":1,"tags":[],"content":nope}}}"#)
                .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );

        // Tag element that is not an array, and a bad separator between fields.
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":1,"kind":1,"tags":["x"],"content":""}}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":1,"kind":1,"tags":[["a" "b"]],"content":""}}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
        // content that is not a string.
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":1,"kind":1,"tags":[],"content":7}}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
        // kind fits u64 and MAX_SAFE_INTEGER but exceeds i32::MAX -> kind invalid.
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":1,"kind":2147483648,"tags":[],"content":""}}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
        // Tags-array grammar: separator junk between tags (C++ "tags array
        // separator is invalid").
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":1,"kind":1,"tags":[["a"];["b"]],"content":""}}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
    }

    #[test]
    fn request_limit_rejections() {
        // request_id over MAX_REQUEST_ID_LENGTH.
        let mut long_id = String::from(r#"{"version":2,"request_id":""#);
        long_id.extend(core::iter::repeat_n('a', MAX_REQUEST_ID_LENGTH + 1));
        long_id.push_str(r#"","method":"sign_event","params":{}}"#);
        assert_eq!(
            parse_qr_signing_request(long_id.as_bytes()).unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );

        // Request JSON over MAX_DECODED_REQUEST_JSON_BYTES (checked before parsing).
        let mut over = String::from(
            r#"{"version":2,"request_id":"r","method":"sign_event","params":{"filler":""#,
        );
        over.extend(core::iter::repeat_n('x', MAX_DECODED_REQUEST_JSON_BYTES));
        over.push_str(r#""}}"#);
        assert_eq!(
            parse_qr_signing_request(over.as_bytes()).unwrap_err(),
            QrEnvelopeError::ExceedsRequestJsonBytes,
        );

        // Tag fields per tag over the limit (9 fields).
        assert_eq!(
            parse_qr_signing_request(
                br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":1,"kind":1,"tags":[["1","2","3","4","5","6","7","8","9"]],"content":""}}}"#
            )
            .unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
    }

    // Content over MAX_CONTENT_UTF8_BYTES *within* the request-JSON budget (the
    // shared "request-content-over-limit" vector is also over the total budget, so
    // it exercises whichever guard fires first; this exercises ContentTooLong
    // specifically, like the C++ event-template content check).
    #[test]
    fn content_over_limit_within_request_budget() {
        let mut json = String::from(
            r#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":1,"kind":1,"tags":[],"content":""#,
        );
        json.extend(core::iter::repeat_n('x', MAX_CONTENT_UTF8_BYTES + 1));
        json.push_str(r#""}}}"#);
        assert!(json.len() <= MAX_DECODED_REQUEST_JSON_BYTES);
        assert_eq!(
            parse_qr_signing_request(json.as_bytes()).unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
    }

    // Direct contract tests for private helpers whose remaining branches are
    // unreachable through the public surface but part of the ported C++ contract.
    #[test]
    fn helper_contracts() {
        // trim_ascii on all-whitespace input (C++ returned "").
        let mut buf = [0u8; 64];
        assert_eq!(
            encode_qr_envelope_json(b" \n\r\t ", &mut buf).unwrap_err(),
            QrEnvelopeError::NotJsonContainer,
        );
        // map_payload_decode_error covers every base64url decode failure (the
        // InvalidCharacter arm is pre-empted by is_base64url_payload on the
        // public paths, as in the C++ catch clause).
        assert_eq!(
            map_payload_decode_error(Base64UrlError::InvalidCharacter),
            QrEnvelopeError::PayloadNotBase64Url,
        );
        assert_eq!(
            map_payload_decode_error(Base64UrlError::InvalidTrailingBits),
            QrEnvelopeError::InvalidTrailingBits,
        );
        assert_eq!(
            map_payload_decode_error(Base64UrlError::OutputTooSmall),
            QrEnvelopeError::OutputTooSmall,
        );
    }

    // Undersized caller buffers surface OutputTooSmall (no C++ analogue; the
    // C++ used growable strings).
    #[test]
    fn undersized_output_buffers() {
        let mut tiny_json = [0u8; 4];
        assert_eq!(
            decode_qr_envelope(KIND1_BASIC_ENVELOPE, &mut tiny_json).unwrap_err(),
            QrEnvelopeError::OutputTooSmall,
        );
        let mut tiny_payload = [0u8; 8];
        let mut json = [0u8; MAX_ANIMATED_QR_DECODED_JSON_BYTES];
        assert_eq!(
            decode_animated_qr_envelope_frames(
                &[ANIMATED_FRAME_1, ANIMATED_FRAME_2, ANIMATED_FRAME_3],
                &mut tiny_payload,
                &mut json,
            )
            .unwrap_err(),
            QrEnvelopeError::OutputTooSmall,
        );
    }

    // Tag-field byte limit uses *decoded* bytes (escapes resolved), like the C++
    // which checked field.size() after unescaping: 33 'è' escapes -> 66 bytes > 64.
    #[test]
    fn tag_field_limit_uses_decoded_bytes() {
        let mut json = String::from(
            r#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":1,"kind":1,"tags":[["t",""#,
        );
        for _ in 0..33 {
            json.push_str("\\u00e8");
        }
        json.push_str(r#""]],"content":""}}}"#);
        assert_eq!(
            parse_qr_signing_request(json.as_bytes()).unwrap_err(),
            QrEnvelopeError::RequestJsonMalformed,
        );
    }
}
