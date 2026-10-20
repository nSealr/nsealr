//! Complete, injective inspection of the admitted kind-1 subset.
//!
//! This ASCII inspection baseline does not qualify device Unicode usability.
//! Only the authorization owner can turn completed local inspection into consent.
use crate::{
    event::{decimal, hex, EventTemplate},
    hash::Sha256,
    text::FixedStr,
};

/// Semantic or complete-render failure; raw review is never a fallback.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InspectionError {
    /// No approved reviewer for this kind or known-tag meaning.
    Unsupported,
    /// A known tag has invalid or ambiguous semantics.
    InvalidTag,
    /// Complete inspection exceeds its configured display/page bound.
    Limit,
}

/// Trusted local text-cell geometry, independent of host request data.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct InspectionGeometry {
    /// Columns per line, between 10 and 32 inclusive.
    pub columns: usize,
    /// Total lines, including wrapped role, value and position, at most eight.
    pub lines: usize,
}
impl InspectionGeometry {
    pub(crate) fn validate(self) -> Result<(), InspectionError> {
        if !(10..=32).contains(&self.columns) || !(1..=8).contains(&self.lines) {
            return Err(InspectionError::Limit);
        }
        Ok(())
    }
}

/// A complete fragment with an explicit field role and global page position.
/// Role, value and position together fit the configured geometry. They must all
/// be displayed in full, in that order; their newlines are already wrapped.
pub struct InspectionFrame {
    label: FixedStr<176>,
    body: FixedStr<264>,
    position: FixedStr<9>,
    index: usize,
    total: usize,
}
impl InspectionFrame {
    /// Full field role, including tag/field indexes and fragment index.
    pub fn label(&self) -> &str {
        self.label.as_str()
    }
    /// Quoted, escaped ASCII value fragment. Newlines are wrapping only.
    pub fn body(&self) -> &str {
        self.body.as_str()
    }
    /// Zero-based page position in the complete immutable review.
    pub fn index(&self) -> usize {
        self.index
    }
    /// Number of complete frames, including the distinct final decision.
    pub fn total(&self) -> usize {
        self.total
    }
    /// One-line, one-based `current/total` position, at most nine ASCII cells.
    pub fn position(&self) -> &str {
        self.position.as_str()
    }
}

fn decode_hex(text: &str) -> Result<[u8; 32], InspectionError> {
    if text.len() != 64 {
        return Err(InspectionError::InvalidTag);
    }
    let digit = |b| match b {
        b'0'..=b'9' => Ok(b - b'0'),
        b'a'..=b'f' => Ok(b - b'a' + 10),
        _ => Err(InspectionError::InvalidTag),
    };
    let mut out = [0; 32];
    for (dst, pair) in out.iter_mut().zip(text.as_bytes().chunks_exact(2)) {
        *dst = digit(pair[0])? * 16 + digit(pair[1])?;
    }
    Ok(out)
}
fn public_key(text: &str) -> Result<[u8; 32], InspectionError> {
    let key = decode_hex(text)?;
    k256::schnorr::VerifyingKey::from_slice(&key).map_err(|_| InspectionError::InvalidTag)?;
    Ok(key)
}
fn unsigned(text: &str, max: u32) -> Result<u32, InspectionError> {
    if text.is_empty() || text.len() > 1 && text.starts_with('0') {
        return Err(InspectionError::InvalidTag);
    }
    let mut value = 0u32;
    for b in text.bytes() {
        if !b.is_ascii_digit() {
            return Err(InspectionError::InvalidTag);
        }
        value = value
            .checked_mul(10)
            .and_then(|n| n.checked_add(u32::from(b - b'0')))
            .ok_or(InspectionError::InvalidTag)?;
    }
    if value > max {
        return Err(InspectionError::InvalidTag);
    }
    Ok(value)
}
fn relay(text: &str) -> Result<(), InspectionError> {
    if text.is_empty() {
        return Ok(());
    }
    let rest = text
        .strip_prefix("wss://")
        .or_else(|| text.strip_prefix("ws://"))
        .ok_or(InspectionError::InvalidTag)?;
    let (authority, path) = rest.split_once('/').unwrap_or((rest, ""));
    let (host, port) = authority
        .split_once(':')
        .map_or((authority, None), |(h, p)| (h, Some(p)));
    if let Some(port) = port {
        if unsigned(port, 65535)? == 0 {
            return Err(InspectionError::InvalidTag);
        }
    }
    if host.is_empty() || host.len() > 253 {
        return Err(InspectionError::InvalidTag);
    }
    if host.bytes().all(|b| b.is_ascii_digit() || b == b'.') {
        let mut count = 0;
        for part in host.split('.') {
            unsigned(part, 255)?;
            count += 1;
        }
        if count != 4 {
            return Err(InspectionError::InvalidTag);
        }
    } else {
        for label in host.split('.') {
            if label.is_empty()
                || label.len() > 63
                || label.starts_with('-')
                || label.ends_with('-')
                || !label
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'-')
            {
                return Err(InspectionError::InvalidTag);
            }
        }
    }
    let mut bytes = path.bytes();
    while let Some(b) = bytes.next() {
        if b == b'%' {
            if !bytes.next().is_some_and(|b| b.is_ascii_hexdigit())
                || !bytes.next().is_some_and(|b| b.is_ascii_hexdigit())
            {
                return Err(InspectionError::InvalidTag);
            }
        } else if !(b.is_ascii_alphanumeric() || b"-._~!$&'()*+,;=:@/".contains(&b)) {
            return Err(InspectionError::InvalidTag);
        }
    }
    Ok(())
}
fn quote(target: &str, author: Option<&str>) -> Result<(), InspectionError> {
    if !target.contains(':') {
        decode_hex(target)?;
        public_key(author.ok_or(InspectionError::InvalidTag)?)?;
        return Ok(());
    }
    let mut parts = target.splitn(3, ':');
    let kind = unsigned(parts.next().ok_or(InspectionError::InvalidTag)?, 65535)?;
    let key = public_key(parts.next().ok_or(InspectionError::InvalidTag)?)?;
    let identifier = parts.next().ok_or(InspectionError::InvalidTag)?;
    if !(matches!(kind, 0 | 3 | 10000..=19999) && identifier.is_empty()
        || (30000..=39999).contains(&kind))
    {
        return Err(InspectionError::InvalidTag);
    }
    if let Some(author) = author {
        if public_key(author)? != key {
            return Err(InspectionError::InvalidTag);
        }
    }
    Ok(())
}

/// Validates the complete supported kind-1 semantics, without granting authority.
pub fn validate_kind1(event: &EventTemplate) -> Result<(), InspectionError> {
    if event.kind() != 1 {
        return Err(InspectionError::Unsupported);
    }
    let mut root = None;
    let mut reply = None;
    let mut unmarked = false;
    for index in 0..event.tag_count() {
        let mut fields = event.tag(index).ok_or(InspectionError::InvalidTag)?;
        let name = fields.next().ok_or(InspectionError::InvalidTag)?;
        match name {
            "e" => {
                let id = decode_hex(fields.next().ok_or(InspectionError::InvalidTag)?)?;
                if let Some(hint) = fields.next() {
                    relay(hint)?;
                }
                match fields.next().unwrap_or("") {
                    "" => unmarked = true,
                    "root" => {
                        if root.replace(id).is_some() {
                            return Err(InspectionError::InvalidTag);
                        }
                    }
                    "reply" => {
                        if reply.replace(id).is_some() {
                            return Err(InspectionError::InvalidTag);
                        }
                    }
                    _ => return Err(InspectionError::Unsupported),
                }
                if let Some(author) = fields.next() {
                    public_key(author)?;
                }
            }
            "p" => {
                public_key(fields.next().ok_or(InspectionError::InvalidTag)?)?;
                if let Some(hint) = fields.next() {
                    relay(hint)?;
                }
            }
            "q" => {
                let target = fields.next().ok_or(InspectionError::InvalidTag)?;
                relay(fields.next().ok_or(InspectionError::InvalidTag)?)?;
                quote(target, fields.next())?;
            }
            "emoji" => return Err(InspectionError::Unsupported),
            _ => {}
        }
    }
    if reply.is_some() && (root.is_none() || reply == root)
        || unmarked && (root.is_some() || reply.is_some())
    {
        return Err(InspectionError::InvalidTag);
    }
    Ok(())
}

pub(crate) struct ReviewDocument<'a> {
    pub event: &'a EventTemplate,
    pub public_key: &'a [u8; 32],
    pub event_id: &'a [u8; 32],
    pub request_id: &'a str,
    pub context: &'a [u64],
    pub geometry: InspectionGeometry,
    pub max_pages: usize,
}
// Used only for bytes produced by the local decimal/hex/ASCII-label formatters.
fn ascii(bytes: &[u8]) -> &str {
    core::str::from_utf8(bytes).expect("generated ASCII")
}
fn push<const N: usize>(text: &mut FixedStr<N>, value: &str) -> Result<(), InspectionError> {
    text.try_push_str(value).map_err(|_| InspectionError::Limit)
}
fn number<const N: usize>(text: &mut FixedStr<N>, value: usize) -> Result<(), InspectionError> {
    text.try_push_usize(value)
        .map_err(|_| InspectionError::Limit)
}
fn field(hash: &mut Sha256, bytes: &[u8]) {
    hash.update(&(bytes.len() as u64).to_be_bytes());
    hash.update(bytes);
}

impl ReviewDocument<'_> {
    fn pages(&self, mut emit: impl FnMut(InspectionFrame)) -> Result<usize, InspectionError> {
        self.geometry.validate()?;
        let mut count = 0;
        let mut value = |label: &str, text: &str| -> Result<(), InspectionError> {
            const FRAGMENT: &str = " / fragment ";
            // Four fixed digits suffice for <=1024 pages and prevent the label
            // from stealing a value row when the fragment number grows.
            let header_lines = (label.len() + FRAGMENT.len() + 4).div_ceil(self.geometry.columns);
            let value_lines = self
                .geometry
                .lines
                .checked_sub(header_lines + 1)
                .filter(|lines| *lines > 0)
                .ok_or(InspectionError::Limit)?;
            let mut body = FixedStr::new();
            let mut column = 0;
            let mut line = 0;
            let mut fragment = 0;
            let mut flush = |body: &mut FixedStr<264>| -> Result<(), InspectionError> {
                if count >= self.max_pages {
                    return Err(InspectionError::Limit);
                }
                let mut flat = FixedStr::<160>::new();
                push(&mut flat, label)?;
                push(&mut flat, FRAGMENT)?;
                let mut digits = [0; 20];
                let digits = decimal(fragment as u64, &mut digits);
                for _ in digits.len()..4 {
                    push(&mut flat, "0")?;
                }
                push(&mut flat, ascii(digits))?;
                let mut full = FixedStr::new();
                for (i, chunk) in flat
                    .as_str()
                    .as_bytes()
                    .chunks(self.geometry.columns)
                    .enumerate()
                {
                    if i > 0 {
                        push(&mut full, "\n")?;
                    }
                    push(&mut full, ascii(chunk))?;
                }
                emit(InspectionFrame {
                    label: full,
                    body: core::mem::take(body),
                    position: FixedStr::new(),
                    index: count,
                    total: 0,
                });
                count += 1;
                fragment += 1;
                Ok(())
            };
            let mut token = |token: &str| -> Result<(), InspectionError> {
                if column + token.len() > self.geometry.columns {
                    column = 0;
                    line += 1;
                    if line == value_lines {
                        flush(&mut body)?;
                        line = 0;
                    } else {
                        push(&mut body, "\n")?;
                    }
                }
                push(&mut body, token)?;
                column += token.len();
                Ok(())
            };
            token("\"")?;
            for ch in text.chars() {
                match ch {
                    '"' => token("\\\"")?,
                    '\\' => token("\\\\")?,
                    '\x08' => token("\\b")?,
                    '\x0c' => token("\\f")?,
                    '\n' => token("\\n")?,
                    '\r' => token("\\r")?,
                    '\t' => token("\\t")?,
                    ' '..='~' => {
                        let mut buf = [0; 4];
                        token(ch.encode_utf8(&mut buf))?;
                    }
                    _ => {
                        let mut buf = [0u8; 10];
                        buf[..3].copy_from_slice(b"\\u{");
                        let mut digits = [0; 6];
                        let mut n = ch as u32;
                        let mut at = 6;
                        loop {
                            at -= 1;
                            digits[at] = b"0123456789ABCDEF"[(n & 15) as usize];
                            n >>= 4;
                            if n == 0 {
                                break;
                            }
                        }
                        let len = 6 - at;
                        buf[3..3 + len].copy_from_slice(&digits[at..]);
                        buf[3 + len] = b'}';
                        token(ascii(&buf[..4 + len]))?;
                    }
                }
            }
            token("\"")?;
            flush(&mut body)
        };
        value("Review contract","nsealr.authorization.v1 / exact ASCII inspection v1; kind 1 text note; references and quotations are unverified")?;
        value("Request ID (host correlation only)", self.request_id)?;
        let key = hex::<32, 64>(self.public_key);
        value("Selected actual signing identity", ascii(&key))?;
        let id = hex::<32, 64>(self.event_id);
        value("Canonical event ID", ascii(&id))?;
        for (index, n) in self.context.iter().enumerate() {
            const LABELS: [&str; 21] = [
                "Local contract version",
                "Local session generation",
                "Local account generation",
                "Local policy generation",
                "Local operation generation",
                "Local limits generation",
                "Local review generation",
                "Local fixed deadline (ticks)",
                "Limit: input bytes",
                "Limit: content bytes",
                "Limit: tag count",
                "Limit: fields per tag",
                "Limit: field bytes",
                "Limit: aggregate text bytes",
                "Limit: canonical bytes",
                "Limit: review pages",
                "Display columns",
                "Display total lines",
                "Review contract version",
                "Limits contract version",
                "Fixed lifetime (ticks)",
            ];
            let label = LABELS.get(index).ok_or(InspectionError::Limit)?;
            let mut buf = [0; 20];
            value(label, ascii(decimal(*n, &mut buf)))?;
        }
        for (label, n) in [
            ("Signed kind", u64::from(self.event.kind())),
            (
                "Signed created_at (untrusted timestamp)",
                self.event.created_at(),
            ),
            ("Signed tag count", self.event.tag_count() as u64),
        ] {
            let mut buf = [0; 20];
            value(label, ascii(decimal(n, &mut buf)))?;
        }
        value("Signed content (plain text)", self.event.content())?;
        for tag in 0..self.event.tag_count() {
            let fields = self.event.tag(tag).ok_or(InspectionError::InvalidTag)?;
            let name = self
                .event
                .tag(tag)
                .and_then(|mut f| f.next())
                .ok_or(InspectionError::InvalidTag)?;
            for (index, text) in fields.enumerate() {
                let role = match (name, index) {
                    ("e" | "p" | "q", 0) => "tag identifier",
                    ("e", 1) => "unverified event reference; unmarked context is ambiguous",
                    ("e" | "p" | "q", 2) => "relay hint (not authenticated)",
                    ("e", 3) => "reply-context marker (empty is ambiguous)",
                    ("e", 4) | ("q", 3) => "claimed author (not verified)",
                    ("p", 1) => "referenced public key",
                    ("q", 1) => "unverified quotation target",
                    _ => "additional signed data - meaning not verified",
                };
                let mut label = FixedStr::<160>::new();
                push(&mut label, "Signed tag ")?;
                number(&mut label, tag)?;
                push(&mut label, " field ")?;
                number(&mut label, index)?;
                push(&mut label, ": ")?;
                push(&mut label, role)?;
                value(label.as_str(), text)?;
            }
        }
        // At most ten cells with quotes: always one fragment in any admitted
        // value area. Its label, prompt and position are preflighted too.
        value("Decision", "Approve?")?;
        Ok(count)
    }
    pub fn commitment(&self) -> Result<([u8; 32], usize), InspectionError> {
        let mut hash = Sha256::new();
        field(&mut hash, b"nsealr.review.v1");
        let count = self.pages(|frame| {
            field(&mut hash, frame.label().as_bytes());
            field(&mut hash, frame.body().as_bytes());
        })?;
        field(&mut hash, &(count as u64).to_be_bytes());
        Ok((hash.finalize(), count))
    }
    pub fn frame(&self, index: usize, total: usize) -> Result<InspectionFrame, InspectionError> {
        let mut found = None;
        let count = self.pages(|mut frame| {
            if frame.index == index {
                frame.total = total;
                // Both counts were preflighted against the 1024-page ceiling.
                frame
                    .position
                    .try_push_usize(index + 1)
                    .expect("bounded index");
                frame
                    .position
                    .try_push_str("/")
                    .expect("position separator");
                frame.position.try_push_usize(total).expect("bounded total");
                found = Some(frame);
            }
        })?;
        if count != total {
            return Err(InspectionError::Limit);
        }
        found.ok_or(InspectionError::Limit)
    }
}
