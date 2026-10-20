//! Strict, allocation-free event-template parsing and NIP-01 canonical bytes.
//!
//! Text is owned once in a bounded arena. Parsing does not authorize signing.
//! The versioned internal contract is `nsealr.authorization.v1`.
use crate::{hash::Sha256, text::FixedStr, unicode::append_json_unicode_escape};

/// Hard input and aggregate decoded-text ceiling.
pub const MAX_EVENT_BYTES: usize = 4096;
/// Hard number of tags.
pub const MAX_TAGS: usize = 32;
/// Hard fields per tag.
pub const MAX_FIELDS: usize = 8;
/// Hard canonical-byte ceiling.
pub const MAX_CANONICAL_BYTES: usize = 8192;

/// A bounded parse/canonicalization failure. No partial event is returned.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EventError {
    /// Invalid JSON grammar, encoding or numeric spelling.
    Syntax,
    /// Missing, duplicate, unknown or wrongly typed member.
    Shape,
    /// A configured or hard resource bound was exceeded.
    Limit,
    /// Numeric value is outside the admitted range.
    Range,
}

/// Trusted local resource configuration; request bytes cannot configure it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct OperationLimits {
    /// Maximum input bytes.
    pub input_bytes: usize,
    /// Maximum decoded content bytes.
    pub content_bytes: usize,
    /// Maximum number of tags.
    pub tags: usize,
    /// Maximum strings per tag.
    pub fields_per_tag: usize,
    /// Maximum decoded bytes per tag field.
    pub field_bytes: usize,
    /// Maximum content plus tag-string bytes.
    pub text_bytes: usize,
    /// Maximum canonical event bytes.
    pub canonical_bytes: usize,
    /// Maximum complete inspection pages.
    pub review_pages: usize,
}
impl OperationLimits {
    /// Portable conformance ceilings, not measured device/profile admission.
    pub const fn conformance() -> Self {
        Self {
            input_bytes: 4096,
            content_bytes: 2048,
            tags: 32,
            fields_per_tag: 8,
            field_bytes: 256,
            text_bytes: 4096,
            canonical_bytes: 8192,
            review_pages: 1024,
        }
    }
    /// Rejects configurations exceeding the fixed backing capacities.
    pub fn validate(self) -> Result<(), EventError> {
        let max = Self::conformance();
        if self.input_bytes > max.input_bytes
            || self.content_bytes > max.content_bytes
            || self.tags > max.tags
            || self.fields_per_tag > max.fields_per_tag
            || self.field_bytes > max.field_bytes
            || self.text_bytes > max.text_bytes
            || self.canonical_bytes > max.canonical_bytes
            || self.review_pages > max.review_pages
            || self.input_bytes == 0
            || self.canonical_bytes == 0
            || self.review_pages == 0
        {
            return Err(EventError::Limit);
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Default)]
struct Span {
    start: u16,
    len: u16,
}

/// Immutable parsed template. It contains no host-selected identity or authority.
pub struct EventTemplate {
    arena: [u8; MAX_EVENT_BYTES],
    used: u16,
    content: Span,
    fields: [Span; MAX_TAGS * MAX_FIELDS],
    tags: [u16; MAX_TAGS + 1],
    tag_count: u16,
    field_count: u16,
    created_at: u64,
    kind: u16,
    canonical_limit: usize,
    pub(crate) raw_tags: (usize, usize),
}
impl EventTemplate {
    fn empty(limits: OperationLimits) -> Self {
        Self {
            arena: [0; MAX_EVENT_BYTES],
            used: 0,
            content: Span::default(),
            fields: [Span::default(); MAX_TAGS * MAX_FIELDS],
            tags: [0; MAX_TAGS + 1],
            tag_count: 0,
            field_count: 0,
            created_at: 0,
            kind: 0,
            canonical_limit: limits.canonical_bytes,
            raw_tags: (0, 0),
        }
    }
    fn text(&self, span: Span) -> &str {
        // Every arena write came from a strict UTF-8/JSON-string reader.
        core::str::from_utf8(
            &self.arena[usize::from(span.start)..usize::from(span.start) + usize::from(span.len)],
        )
        .expect("validated UTF-8 arena")
    }
    /// Exact decoded content, without normalization.
    pub fn content(&self) -> &str {
        self.text(self.content)
    }
    /// Exact nonnegative timestamp; this is not a trusted clock reading.
    pub fn created_at(&self) -> u64 {
        self.created_at
    }
    /// NIP-01 kind, within 0..65535. Semantic admission is separate.
    pub fn kind(&self) -> u16 {
        self.kind
    }
    /// Ordered number of tags.
    pub fn tag_count(&self) -> usize {
        usize::from(self.tag_count)
    }
    /// Ordered fields of a tag; out-of-range indexes return None.
    pub fn tag(&self, index: usize) -> Option<impl ExactSizeIterator<Item = &str>> {
        if index >= self.tag_count() {
            return None;
        }
        let start = usize::from(self.tags[index]);
        let end = usize::from(self.tags[index + 1]);
        Some(self.fields[start..end].iter().map(|span| self.text(*span)))
    }
    fn string(
        &mut self,
        r: &mut Reader<'_>,
        max: usize,
        limits: OperationLimits,
    ) -> Result<Span, EventError> {
        let start = usize::from(self.used);
        let end = start
            .checked_add(max.min(limits.text_bytes.saturating_sub(start)))
            .ok_or(EventError::Limit)?;
        let len = r.string(&mut self.arena[start..end])?;
        let span = Span {
            start: self.used,
            len: len as u16,
        };
        self.used += span.len;
        Ok(span)
    }
    fn parse_reader(r: &mut Reader<'_>, limits: OperationLimits) -> Result<Self, EventError> {
        let mut event = Self::empty(limits);
        r.object(&["created_at", "kind", "tags", "content"], |r, key| {
            match key {
                0 => event.created_at = r.number(9_007_199_254_740_991)?,
                1 => event.kind = r.number(65535)? as u16,
                2 => {
                    r.ws();
                    let start = r.at;
                    r.take(b'[')?;
                    if !r.eat(b']') {
                        loop {
                            if event.tag_count() >= limits.tags {
                                return Err(EventError::Limit);
                            }
                            r.take(b'[')?;
                            let first = event.field_count;
                            if r.eat(b']') {
                                return Err(EventError::Shape);
                            }
                            loop {
                                if usize::from(event.field_count - first) >= limits.fields_per_tag {
                                    return Err(EventError::Limit);
                                }
                                let span = event.string(r, limits.field_bytes, limits)?;
                                if event.field_count == first && span.len == 0 {
                                    return Err(EventError::Shape);
                                }
                                event.fields[usize::from(event.field_count)] = span;
                                event.field_count += 1;
                                if r.eat(b']') {
                                    break;
                                }
                                r.take(b',')?;
                            }
                            event.tag_count += 1;
                            event.tags[event.tag_count()] = event.field_count;
                            if r.eat(b']') {
                                break;
                            }
                            r.take(b',')?;
                        }
                    }
                    event.raw_tags = (start, r.at);
                }
                _ => event.content = event.string(r, limits.content_bytes, limits)?,
            }
            Ok(())
        })?;
        Ok(event)
    }
    /// Parses exactly one standalone template using trusted local limits.
    pub fn parse(input: &[u8], limits: OperationLimits) -> Result<Self, EventError> {
        let mut reader = Reader::new(input, limits)?;
        let event = Self::parse_reader(&mut reader, limits)?;
        reader.end()?;
        Ok(event)
    }
    fn canonical(
        &self,
        pubkey: &[u8; 32],
        mut emit: impl FnMut(&[u8]) -> Result<(), EventError>,
    ) -> Result<usize, EventError> {
        let mut count = 0usize;
        let mut output = |bytes: &[u8]| {
            count = count.checked_add(bytes.len()).ok_or(EventError::Limit)?;
            if count > self.canonical_limit {
                return Err(EventError::Limit);
            }
            emit(bytes)
        };
        output(b"[0,\"")?;
        let key = hex::<32, 64>(pubkey);
        output(&key)?;
        output(b"\",")?;
        let mut number = [0; 20];
        output(decimal(self.created_at, &mut number))?;
        output(b",")?;
        output(decimal(u64::from(self.kind), &mut number))?;
        output(b",[")?;
        for tag in 0..self.tag_count() {
            if tag != 0 {
                output(b",")?;
            }
            output(b"[")?;
            for (index, field) in self.tag(tag).expect("tag index bounded").enumerate() {
                if index != 0 {
                    output(b",")?;
                }
                json_string(field, &mut output)?;
            }
            output(b"]")?;
        }
        output(b"],")?;
        json_string(self.content(), &mut output)?;
        output(b"]")?;
        Ok(count)
    }
    /// Writes compact NIP-01 bytes into caller-owned output; returns written length.
    pub fn write_canonical(&self, pubkey: &[u8; 32], out: &mut [u8]) -> Result<usize, EventError> {
        let mut at = 0;
        self.canonical(pubkey, |bytes| {
            let end = at + bytes.len();
            let dst = out.get_mut(at..end).ok_or(EventError::Limit)?;
            dst.copy_from_slice(bytes);
            at = end;
            Ok(())
        })
    }
    /// Hashes the exact canonical UTF-8 bytes, without retaining a canonical copy.
    pub fn event_id(&self, pubkey: &[u8; 32]) -> Result<[u8; 32], EventError> {
        let mut hash = Sha256::new();
        self.canonical(pubkey, |bytes| {
            hash.update(bytes);
            Ok(())
        })?;
        Ok(hash.finalize())
    }
}

pub(crate) fn decimal(mut value: u64, out: &mut [u8; 20]) -> &[u8] {
    let mut at = out.len();
    loop {
        at -= 1;
        out[at] = b'0' + (value % 10) as u8;
        value /= 10;
        if value == 0 {
            break;
        }
    }
    &out[at..]
}

pub(crate) fn hex<const N: usize, const M: usize>(bytes: &[u8; N]) -> [u8; M] {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    assert_eq!(M, N * 2);
    let mut out = [0; M];
    for (i, b) in bytes.iter().enumerate() {
        out[i * 2] = HEX[usize::from(b >> 4)];
        out[i * 2 + 1] = HEX[usize::from(b & 15)];
    }
    out
}
fn json_string(
    text: &str,
    emit: &mut impl FnMut(&[u8]) -> Result<(), EventError>,
) -> Result<(), EventError> {
    emit(b"\"")?;
    for byte in text.as_bytes() {
        match byte {
            b'"' => emit(b"\\\"")?,
            b'\\' => emit(b"\\\\")?,
            b'\x08' => emit(b"\\b")?,
            b'\x0c' => emit(b"\\f")?,
            b'\n' => emit(b"\\n")?,
            b'\r' => emit(b"\\r")?,
            b'\t' => emit(b"\\t")?,
            0..=31 => {
                let pair = hex::<1, 2>(&[*byte]);
                emit(b"\\u00")?;
                emit(&pair)?;
            }
            _ => emit(core::slice::from_ref(byte))?,
        }
    }
    emit(b"\"")
}

/// Methods admitted by the legacy envelope; none grants local consent.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RequestMethod {
    /// A strict event template requiring separate semantic review.
    SignEvent,
    /// Diagnostic capabilities.
    Capabilities,
    /// Diagnostic signing status.
    SigningStatus,
    /// Public identity query.
    PublicKey,
}
/// Fully validated envelope with owned decoded values, never approval.
pub struct ParsedRequest {
    pub(crate) request_id: FixedStr<128>,
    pub(crate) method: RequestMethod,
    pub(crate) event: Option<EventTemplate>,
    pub(crate) raw_template: (usize, usize),
}
impl ParsedRequest {
    /// Strict legacy v1 envelope parse, shared by serial and QR adapters.
    pub fn parse(input: &[u8], limits: OperationLimits) -> Result<Self, EventError> {
        let mut r = Reader::new(input, limits)?;
        let mut result = Self {
            request_id: FixedStr::new(),
            method: RequestMethod::PublicKey,
            event: None,
            raw_template: (0, 0),
        };
        let mut params = false;
        let seen =
            r.object_optional(&["version", "request_id", "method", "params"], |r, key| {
                match key {
                    0 => {
                        if r.number(1)? != 1 {
                            return Err(EventError::Range);
                        }
                    }
                    1 => {
                        let mut buf = [0; 128];
                        let len = r.string(&mut buf)?;
                        if len == 0
                            || !buf[..len]
                                .iter()
                                .all(|b| b.is_ascii_alphanumeric() || b"._:-".contains(b))
                        {
                            return Err(EventError::Shape);
                        }
                        result.request_id = core::str::from_utf8(&buf[..len])
                            .map_err(|_| EventError::Syntax)?
                            .parse()
                            .map_err(|_| EventError::Limit)?;
                    }
                    2 => {
                        let mut buf = [0; 24];
                        let len = r.string(&mut buf)?;
                        result.method = match &buf[..len] {
                            b"sign_event" => RequestMethod::SignEvent,
                            b"get_capabilities" => RequestMethod::Capabilities,
                            b"get_signing_status" => RequestMethod::SigningStatus,
                            b"get_public_key" => RequestMethod::PublicKey,
                            _ => return Err(EventError::Shape),
                        };
                    }
                    _ => {
                        params = true;
                        r.object(&["event_template"], |r, _| {
                            r.ws();
                            let start = r.at;
                            result.event = Some(EventTemplate::parse_reader(r, limits)?);
                            result.raw_template = (start, r.at);
                            Ok(())
                        })?;
                    }
                }
                Ok(())
            })?;
        if seen & 7 != 7 || params != (result.method == RequestMethod::SignEvent) {
            return Err(EventError::Shape);
        }
        r.end()?;
        Ok(result)
    }
    /// Caller correlation identifier; it cannot authorize an operation.
    pub fn request_id(&self) -> &str {
        self.request_id.as_str()
    }
    /// Parsed method.
    pub fn method(&self) -> RequestMethod {
        self.method
    }
}

struct Reader<'a> {
    input: &'a [u8],
    at: usize,
}
impl<'a> Reader<'a> {
    fn new(input: &'a [u8], limits: OperationLimits) -> Result<Self, EventError> {
        limits.validate()?;
        if input.len() > limits.input_bytes {
            return Err(EventError::Limit);
        }
        core::str::from_utf8(input).map_err(|_| EventError::Syntax)?;
        Ok(Self { input, at: 0 })
    }
    fn ws(&mut self) {
        while self
            .input
            .get(self.at)
            .is_some_and(|b| b" \t\r\n".contains(b))
        {
            self.at += 1;
        }
    }
    fn eat(&mut self, b: u8) -> bool {
        self.ws();
        if self.input.get(self.at) == Some(&b) {
            self.at += 1;
            true
        } else {
            false
        }
    }
    fn take(&mut self, b: u8) -> Result<(), EventError> {
        if self.eat(b) {
            Ok(())
        } else {
            Err(EventError::Syntax)
        }
    }
    fn end(&mut self) -> Result<(), EventError> {
        self.ws();
        if self.at == self.input.len() {
            Ok(())
        } else {
            Err(EventError::Syntax)
        }
    }
    fn string(&mut self, out: &mut [u8]) -> Result<usize, EventError> {
        self.take(b'"')?;
        let mut len = 0usize;
        loop {
            let b = *self.input.get(self.at).ok_or(EventError::Syntax)?;
            self.at += 1;
            if b == b'"' {
                return Ok(len);
            }
            if b < 32 {
                return Err(EventError::Syntax);
            }
            let mut scratch = [0; 4];
            let bytes = if b == b'\\' {
                let escaped = *self.input.get(self.at).ok_or(EventError::Syntax)?;
                self.at += 1;
                if escaped == b'u' {
                    append_json_unicode_escape(self.input, &mut self.at, &mut scratch)
                        .map_err(|_| EventError::Syntax)?
                } else {
                    scratch[0] = match escaped {
                        b'"' | b'\\' | b'/' => escaped,
                        b'b' => 8,
                        b'f' => 12,
                        b'n' => 10,
                        b'r' => 13,
                        b't' => 9,
                        _ => return Err(EventError::Syntax),
                    };
                    &scratch[..1]
                }
            } else {
                scratch[0] = b;
                &scratch[..1]
            };
            let end = len.checked_add(bytes.len()).ok_or(EventError::Limit)?;
            out.get_mut(len..end)
                .ok_or(EventError::Limit)?
                .copy_from_slice(bytes);
            len = end;
        }
    }
    fn number(&mut self, max: u64) -> Result<u64, EventError> {
        self.ws();
        let start = self.at;
        let mut value = 0u64;
        while let Some(b'0'..=b'9') = self.input.get(self.at) {
            value = value
                .checked_mul(10)
                .and_then(|v| v.checked_add(u64::from(self.input[self.at] - b'0')))
                .ok_or(EventError::Range)?;
            self.at += 1;
        }
        if self.at == start || self.at > start + 1 && self.input[start] == b'0' {
            return Err(EventError::Syntax);
        }
        if value > max {
            return Err(EventError::Range);
        }
        Ok(value)
    }
    fn object(
        &mut self,
        keys: &[&str],
        member: impl FnMut(&mut Self, usize) -> Result<(), EventError>,
    ) -> Result<(), EventError> {
        let seen = self.object_optional(keys, member)?;
        if seen == (1u8 << keys.len()) - 1 {
            Ok(())
        } else {
            Err(EventError::Shape)
        }
    }
    fn object_optional(
        &mut self,
        keys: &[&str],
        mut member: impl FnMut(&mut Self, usize) -> Result<(), EventError>,
    ) -> Result<u8, EventError> {
        self.take(b'{')?;
        let mut seen = 0u8;
        if self.eat(b'}') {
            return Ok(seen);
        }
        loop {
            let mut key = [0; 16];
            let len = self.string(&mut key)?;
            let index = keys
                .iter()
                .position(|k| k.as_bytes() == &key[..len])
                .ok_or(EventError::Shape)?;
            if seen & (1 << index) != 0 {
                return Err(EventError::Shape);
            }
            seen |= 1 << index;
            self.take(b':')?;
            member(self, index)?;
            if self.eat(b'}') {
                return Ok(seen);
            }
            self.take(b',')?;
        }
    }
}
