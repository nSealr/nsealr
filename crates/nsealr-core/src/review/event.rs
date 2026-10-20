//! Complete, injective inspection of the fixed seven-kind public catalog.
//!
//! This ASCII inspection baseline does not qualify device Unicode usability.
//! Only the authorization owner can turn completed local inspection into consent.
use crate::{
    event::{decimal, hex, inspect_metadata, EventTemplate, OperationLimits, SignedOriginal},
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
            let nibble = |b: u8| {
                (b as char)
                    .to_digit(16)
                    .map(|n| n as u8)
                    .ok_or(InspectionError::InvalidTag)
            };
            let first = nibble(bytes.next().ok_or(InspectionError::InvalidTag)?)?;
            let second = nibble(bytes.next().ok_or(InspectionError::InvalidTag)?)?;
            let decoded = first * 16 + second;
            if decoded < 32 || matches!(decoded, 127 | b'\\') {
                return Err(InspectionError::InvalidTag);
            }
        } else if !(b.is_ascii_alphanumeric() || b"-._~!$&'()*+,;=:@/".contains(&b)) {
            return Err(InspectionError::InvalidTag);
        }
    }
    Ok(())
}

fn coordinate(text: &str) -> Result<(u32, [u8; 32]), InspectionError> {
    let mut parts = text.splitn(3, ':');
    let kind = unsigned(parts.next().ok_or(InspectionError::InvalidTag)?, 65535)?;
    let key = public_key(parts.next().ok_or(InspectionError::InvalidTag)?)?;
    let id = parts.next().ok_or(InspectionError::InvalidTag)?;
    if !(matches!(kind, 0 | 3 | 10000..=19999) && id.is_empty() || (30000..=39999).contains(&kind))
    {
        return Err(InspectionError::InvalidTag);
    }
    Ok((kind, key))
}

fn required_relay(text: &str) -> Result<(), InspectionError> {
    if text.is_empty() {
        return Err(InspectionError::InvalidTag);
    }
    relay(text)
}

/// Validate semantics under the selected identity before any local consent.
/// Signed originals are verified from borrowed spans, never caller trust flags.
pub(crate) fn validate_catalog(
    event: &EventTemplate,
    selected: &[u8; 32],
    limits: OperationLimits,
) -> Result<(), InspectionError> {
    if event.kind() == 1 {
        return validate_kind1(event);
    }
    if event.kind() == 0 {
        inspect_metadata(event.content(), &mut |_| Ok(()))
            .map_err(|_| InspectionError::InvalidTag)?;
        return Ok(());
    }
    if !matches!(event.kind(), 3 | 5 | 6 | 7 | 10002) {
        return Err(InspectionError::Unsupported);
    }
    let mut target = None;
    let mut target_author = None;
    let mut last_person = None;
    let mut address = None;
    let mut kind_hint = None;
    let mut targets = 0;
    let mut people = 0;
    for index in 0..event.tag_count() {
        let mut fields = event.tag(index).ok_or(InspectionError::InvalidTag)?;
        let name = fields.next().ok_or(InspectionError::InvalidTag)?;
        match (event.kind(), name) {
            (3 | 6 | 7, "p") => {
                last_person = Some(public_key(
                    fields.next().ok_or(InspectionError::InvalidTag)?,
                )?);
                people += 1;
                if let Some(hint) = fields.next() {
                    relay(hint)?;
                }
                // Kind3's optional petname and every suffix remain unverified data.
            }
            (5..=7, "e") => {
                target = Some(decode_hex(
                    fields.next().ok_or(InspectionError::InvalidTag)?,
                )?);
                targets += 1;
                if event.kind() == 6 {
                    required_relay(fields.next().ok_or(InspectionError::InvalidTag)?)?;
                }
                if event.kind() == 7 {
                    if let Some(hint) = fields.next() {
                        relay(hint)?;
                    }
                    target_author = fields.next().map(public_key).transpose()?;
                }
            }
            (5 | 7, "a") => {
                let value = coordinate(fields.next().ok_or(InspectionError::InvalidTag)?)?;
                if event.kind() == 5 {
                    if value.1 != *selected {
                        return Err(InspectionError::InvalidTag);
                    }
                    targets += 1;
                } else {
                    if address.replace(value).is_some() {
                        return Err(InspectionError::InvalidTag);
                    }
                    if let Some(hint) = fields.next() {
                        relay(hint)?;
                    }
                    if let Some(author) = fields.next() {
                        if public_key(author)? != value.1 {
                            return Err(InspectionError::InvalidTag);
                        }
                    }
                }
            }
            (5 | 7, "k") => {
                let value = unsigned(fields.next().ok_or(InspectionError::InvalidTag)?, 65535)?;
                if event.kind() == 7 && kind_hint.replace(value).is_some() {
                    return Err(InspectionError::InvalidTag);
                }
            }
            (7, "emoji") => return Err(InspectionError::Unsupported),
            (10002, "r") => {
                required_relay(fields.next().ok_or(InspectionError::InvalidTag)?)?;
                if let Some(role) = fields.next() {
                    if !matches!(role, "read" | "write") {
                        return Err(InspectionError::InvalidTag);
                    }
                }
            }
            _ => {}
        }
    }
    match event.kind() {
        5 if targets == 0 => return Err(InspectionError::InvalidTag),
        6 => {
            if targets != 1 || people > 1 {
                return Err(InspectionError::InvalidTag);
            }
            if !event.content().is_empty() {
                let original = SignedOriginal::parse(event.content(), limits)
                    .map_err(|_| InspectionError::InvalidTag)?;
                original.verify().map_err(|_| InspectionError::InvalidTag)?;
                if Some(original.id) != target
                    || last_person.is_some_and(|p| p != original.public_key)
                {
                    return Err(InspectionError::InvalidTag);
                }
            }
        }
        7 => {
            if targets == 0 {
                return Err(InspectionError::InvalidTag);
            }
            if target_author.zip(last_person).is_some_and(|(a, b)| a != b)
                || address.is_some_and(|(kind, key)| {
                    kind_hint.is_some_and(|k| k != kind)
                        || last_person.is_some_and(|p| p != key)
                        || target_author.is_some_and(|p| p != key)
                })
            {
                return Err(InspectionError::InvalidTag);
            }
            let content = event.content();
            if content.starts_with(':')
                && content.ends_with(':')
                && content.len() > 2
                && !content[1..content.len() - 1].contains(':')
            {
                return Err(InspectionError::Unsupported);
            }
        }
        _ => {}
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
    pub limits: OperationLimits,
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
        value("Review contract", "nsealr.authorization.v1 / exact ASCII inspection catalog v2; signed values are complete; external claims are unverified")?;
        let operation = match self.event.kind() {
            0 => "Replace the whole public profile. Empty object clears profile fields. Nested values/types are shown; identity/profile claims are not verified.",
            1 => "Publish a kind 1 text note. References and quotations are unverified. Unmarked context is ambiguous; root/reply markers describe reply structure only.",
            3 => "Replace the entire public follow list. Empty p-list unfollows everyone. Repeated entries/order remain signed; relay hints and petnames are unverified.",
            5 => "Publish a deletion request for every e/a target. k values are unpaired hints. Coordinate deletion covers historical versions through created_at. Erasure is not guaranteed; deleting a deletion cannot undo it.",
            6 if self.event.content().is_empty() => "Repost one kind 1 event reference. Original content/signature were not supplied and are unverified. Relay and author hints do not prove real-world identity.",
            6 => "Repost one kind 1 event with checked original ID/signature. The complete original follows. Cryptographic validity does not establish real-world identity or truth.",
            7 => "React to the LAST e target, with LAST p author hint. Earlier references are context. Supplied author/coordinate/k hints agree but external target meaning is unverified. Empty/+ means like; - means dislike; other content is literal.",
            10002 => "Replace the whole public relay list. Empty r-list withdraws all relays. Missing role means read and write. Preserve repeated entries/order. This is not the private-message relay list kind 10050.",
            _ => return Err(InspectionError::Unsupported),
        };
        value("Operation and consequences", operation)?;
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
        let last_named = |name| {
            (0..self.event.tag_count())
                .rev()
                .find(|index| self.event.tag(*index).and_then(|mut f| f.next()) == Some(name))
        };
        let last_event = last_named("e");
        let last_person = last_named("p");
        for tag in 0..self.event.tag_count() {
            let fields = self.event.tag(tag).ok_or(InspectionError::InvalidTag)?;
            let name = self
                .event
                .tag(tag)
                .and_then(|mut f| f.next())
                .ok_or(InspectionError::InvalidTag)?;
            for (index, text) in fields.enumerate() {
                let role = match (self.event.kind(), name, index) {
                    (_, _, 0) => "tag identifier",
                    (1, "e", 1) => "unverified event reference; unmarked context is ambiguous",
                    (1, "e" | "p" | "q", 2) => "relay hint (not authenticated)",
                    (1, "e", 3) => "reply-context marker (empty is ambiguous)",
                    (1, "e", 4) | (1, "q", 3) => "claimed author (not verified)",
                    (1, "p", 1) => "referenced public key",
                    (1, "q", 1) => "unverified quotation target",
                    (3, "p", 1) => "followed public key (list entry)",
                    (3, "p", 2) => "unverified relay hint",
                    (3, "p", 3) => "unverified petname",
                    (5, "e", 1) => "deletion event ID target",
                    (5, "a", 1) => "deletion coordinate owned by selected key",
                    (5, "k", 1) => "unpaired deletion kind hint",
                    (6, "e", 1) => "sole repost event ID target",
                    (6, "e", 2) => "required original relay (unverified)",
                    (6, "p", 1) => "original author hint (checked if original supplied)",
                    (6, "p", 2) => "unverified original author relay hint",
                    (7, "e", 1) if last_event == Some(tag) => "reaction TARGET event ID (last e)",
                    (7, "e", 1) => "earlier reaction context event ID",
                    (7, "p", 1) if last_person == Some(tag) => "TARGET author hint (last p)",
                    (7, "p", 1) => "earlier context author hint",
                    (7, "e" | "p" | "a", 2) => "unverified relay hint",
                    (7, "e" | "a", 3) => "supplied target author (not real-world identity)",
                    (7, "a", 1) => "coherent target coordinate (unverified)",
                    (7, "k", 1) => "coherent target kind hint (unverified)",
                    (10002, "r", 1) => "public relay URL (unverified)",
                    (10002, "r", 2) => "relay role; read or write; absent means both",
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
            if matches!(self.event.kind(), 5 | 7) && name == "a" {
                let address = self
                    .event
                    .tag(tag)
                    .and_then(|mut fields| fields.nth(1))
                    .ok_or(InspectionError::InvalidTag)?;
                for (part, text) in address.splitn(3, ':').enumerate() {
                    let mut label = FixedStr::<160>::new();
                    push(&mut label, "Signed address tag ")?;
                    number(&mut label, tag)?;
                    let role = match part {
                        0 => " kind",
                        1 => " public key",
                        _ => " complete identifier (colons preserved)",
                    };
                    push(&mut label, role)?;
                    value(label.as_str(), text)?;
                }
            }
            if self.event.kind() == 10002 && name == "r" {
                let role = self
                    .event
                    .tag(tag)
                    .and_then(|mut fields| fields.nth(2))
                    .unwrap_or("read and write");
                let mut label = FixedStr::<160>::new();
                push(&mut label, "Signed relay tag ")?;
                number(&mut label, tag)?;
                push(&mut label, " effective use")?;
                value(label.as_str(), role)?;
            }
        }
        if self.event.kind() == 0 {
            inspect_metadata(self.event.content(), &mut |item| {
                let mut label = FixedStr::<160>::new();
                push(&mut label, "Profile node ").map_err(|_| crate::event::EventError::Limit)?;
                number(&mut label, item.node).map_err(|_| crate::event::EventError::Limit)?;
                push(&mut label, " parent ").map_err(|_| crate::event::EventError::Limit)?;
                number(&mut label, item.parent).map_err(|_| crate::event::EventError::Limit)?;
                push(&mut label, " index/count ").map_err(|_| crate::event::EventError::Limit)?;
                number(&mut label, item.index).map_err(|_| crate::event::EventError::Limit)?;
                push(&mut label, ": ").map_err(|_| crate::event::EventError::Limit)?;
                push(&mut label, item.kind).map_err(|_| crate::event::EventError::Limit)?;
                value(label.as_str(), item.text).map_err(|_| crate::event::EventError::Limit)
            })
            .map_err(|_| InspectionError::Limit)?;
        }
        if self.event.kind() == 6 && !self.event.content().is_empty() {
            // Borrow source spans and decode one bounded field at a time. Intake
            // already verified this immutable original; rendering adds no key
            // conversions, second event arena, or repeated signature checks.
            let original = SignedOriginal::parse(self.event.content(), self.limits)
                .map_err(|_| InspectionError::InvalidTag)?;
            value(
                "Checked original public key (not real-world identity)",
                ascii(&hex::<32, 64>(&original.public_key)),
            )?;
            value(
                "Checked original event ID",
                ascii(&hex::<32, 64>(&original.id)),
            )?;
            value(
                "Checked original raw signature",
                ascii(&hex::<64, 128>(&original.signature)),
            )?;
            let mut buf = [0; 20];
            value(
                "Original signed created_at (untrusted)",
                ascii(decimal(original.created_at, &mut buf)),
            )?;
            value(
                "Original signed kind",
                ascii(decimal(u64::from(original.kind), &mut buf)),
            )?;
            original
                .visit_content(&mut |text| {
                    value("Original signed content", text)
                        .map_err(|_| crate::event::EventError::Limit)
                })
                .map_err(|_| InspectionError::Limit)?;
            original
                .visit_tags(&mut |tag, index, text| {
                    let mut label = FixedStr::<160>::new();
                    push(&mut label, "Original signed tag ")
                        .map_err(|_| crate::event::EventError::Limit)?;
                    number(&mut label, tag).map_err(|_| crate::event::EventError::Limit)?;
                    push(&mut label, " field ").map_err(|_| crate::event::EventError::Limit)?;
                    number(&mut label, index).map_err(|_| crate::event::EventError::Limit)?;
                    push(&mut label, ": original signed data, meaning not verified")
                        .map_err(|_| crate::event::EventError::Limit)?;
                    value(label.as_str(), text).map_err(|_| crate::event::EventError::Limit)
                })
                .map_err(|_| InspectionError::Limit)?;
        }
        // At most ten cells with quotes: always one fragment in any admitted
        // value area. Its label, prompt and position are preflighted too.
        value("Decision", "Approve?")?;
        Ok(count)
    }
    pub fn commitment(&self) -> Result<([u8; 32], usize), InspectionError> {
        let mut hash = Sha256::new();
        field(&mut hash, b"nsealr.review.catalog.v2");
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
