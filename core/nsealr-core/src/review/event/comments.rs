//! NIP22 public thread references. External targets and ancestry remain claims.
use super::{
    coordinate, decode_hex, public_key, quote, relay, unsigned, EventTemplate, InspectionError,
};

#[derive(Default)]
struct Scope<'a> {
    id: Option<&'a str>,
    address: Option<&'a str>,
    external: Option<&'a str>,
    kind: Option<&'a str>,
    inline_author: Option<&'a str>,
    author: Option<&'a str>,
}
fn unique<'a>(slot: &mut Option<&'a str>, value: &'a str) -> Result<(), InspectionError> {
    if slot.replace(value).is_some() {
        return Err(InspectionError::InvalidTag);
    }
    Ok(())
}
fn field<'a>(fields: &mut impl Iterator<Item = &'a str>) -> Result<&'a str, InspectionError> {
    fields.next().ok_or(InspectionError::InvalidTag)
}
fn key(text: &str) -> Result<(), InspectionError> {
    public_key(text).map(|_| ())
}

/// Explicit ASCII HTTP(S) references; never fetch, normalize or authenticate them.
pub(super) fn web(text: &str, fragment: bool) -> Result<(), InspectionError> {
    let rest = text
        .strip_prefix("https://")
        .or_else(|| text.strip_prefix("http://"))
        .ok_or(InspectionError::InvalidTag)?;
    if !fragment && text.contains('#') {
        return Err(InspectionError::InvalidTag);
    }
    let authority = rest
        .split(['/', '?', '#'])
        .next()
        .ok_or(InspectionError::InvalidTag)?;
    if authority.is_empty() || authority.contains('@') {
        return Err(InspectionError::InvalidTag);
    }
    let (host, port) = if let Some(ip) = authority.strip_prefix('[') {
        let (address, suffix) = ip.split_once(']').ok_or(InspectionError::InvalidTag)?;
        address
            .parse::<core::net::Ipv6Addr>()
            .map_err(|_| InspectionError::InvalidTag)?;
        (
            "",
            if suffix.is_empty() {
                None
            } else {
                Some(
                    suffix
                        .strip_prefix(':')
                        .ok_or(InspectionError::InvalidTag)?,
                )
            },
        )
    } else {
        let (host, port) = authority
            .split_once(':')
            .map_or((authority, None), |(h, p)| (h, Some(p)));
        if host.is_empty()
            || host.len() > 253
            || host.split('.').any(|part| {
                part.is_empty()
                    || part.len() > 63
                    || part.starts_with('-')
                    || part.ends_with('-')
                    || !part
                        .bytes()
                        .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
            })
        {
            return Err(InspectionError::InvalidTag);
        }
        (host, port)
    };
    if !host.is_empty() && host.bytes().all(|b| b.is_ascii_digit() || b == b'.') {
        host.parse::<core::net::Ipv4Addr>()
            .map_err(|_| InspectionError::InvalidTag)?;
    }
    if port.is_some_and(|p| unsigned(p, 65535).map_or(true, |n| n == 0)) {
        return Err(InspectionError::InvalidTag);
    }
    let mut bytes = text.bytes();
    while let Some(b) = bytes.next() {
        if !(b.is_ascii_alphanumeric() || b"-._~:/?#[]@!$&'()*+,;=%".contains(&b)) {
            return Err(InspectionError::InvalidTag);
        }
        if b == b'%' {
            let digit = |b: u8| (b as char).to_digit(16).ok_or(InspectionError::InvalidTag);
            let decoded = digit(bytes.next().ok_or(InspectionError::InvalidTag)?)? * 16
                + digit(bytes.next().ok_or(InspectionError::InvalidTag)?)?;
            if decoded < 32 || decoded == 127 || decoded == u32::from(b'\\') {
                return Err(InspectionError::InvalidTag);
            }
        }
    }
    Ok(())
}

fn external(kind: &str, identifier: &str) -> Result<(), InspectionError> {
    if identifier.is_empty() || identifier.chars().any(char::is_control) {
        return Err(InspectionError::InvalidTag);
    }
    if kind == "web" {
        return web(identifier, false);
    }
    let tail = if kind == "#" {
        identifier.strip_prefix('#')
    } else {
        identifier
            .strip_prefix(kind)
            .and_then(|s| s.strip_prefix(':'))
    };
    let valid = match (kind, tail) {
        ("#", Some(t)) => {
            !t.is_empty() && !t.chars().any(|c| c.is_uppercase() || c.is_whitespace())
        }
        ("geo", Some(t)) => {
            !t.is_empty()
                && t.bytes()
                    .all(|b| b"0123456789bcdefghjkmnpqrstuvwxyz".contains(&b))
        }
        ("iso3166", Some(t)) => {
            let (country, sub) = t.split_once('-').map_or((t, None), |(c, s)| (c, Some(s)));
            country.len() == 2
                && country.bytes().all(|b| b.is_ascii_uppercase())
                && sub.is_none_or(|s| {
                    !s.is_empty()
                        && s.len() <= 3
                        && s.bytes()
                            .all(|b| b.is_ascii_uppercase() || b.is_ascii_digit())
                })
        }
        ("isbn", Some(t)) => {
            t.len() == 13 && t.bytes().all(|b| b.is_ascii_digit())
                || t.len() == 10
                    && t.as_bytes()[..9].iter().all(u8::is_ascii_digit)
                    && (t.as_bytes()[9].is_ascii_digit() || t.as_bytes()[9] == b'X')
        }
        ("isan", Some(t)) => {
            let mut parts = t.split('-');
            (t.len() == 17
                && t.as_bytes()[..16].iter().all(u8::is_ascii_hexdigit)
                && t.as_bytes()[16].is_ascii_alphanumeric())
                || (0..4).all(|_| {
                    parts
                        .next()
                        .is_some_and(|p| p.len() == 4 && p.bytes().all(|b| b.is_ascii_hexdigit()))
                }) && parts
                    .next()
                    .is_some_and(|p| p.len() == 1 && p.bytes().all(|b| b.is_ascii_alphanumeric()))
                    && parts.next().is_none()
        }
        ("doi", Some(t)) => {
            t.strip_prefix("10.")
                .and_then(|s| s.split_once('/'))
                .is_some_and(|(prefix, suffix)| {
                    !prefix.is_empty()
                        && prefix.bytes().all(|b| b.is_ascii_digit())
                        && !suffix.is_empty()
                })
                && !t.chars().any(|c| c.is_uppercase() || c.is_whitespace())
        }
        ("podcast:guid" | "podcast:item:guid" | "podcast:publisher:guid", Some(t)) => {
            !t.is_empty() && !t.chars().any(char::is_whitespace)
        }
        _ => {
            let (chain, action) = kind.split_once(':').ok_or(InspectionError::Unsupported)?;
            if chain.is_empty()
                || !chain
                    .bytes()
                    .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
                || !matches!(action, "tx" | "address")
            {
                return Err(InspectionError::Unsupported);
            }
            let mut parts = identifier.split(':');
            if parts.next() != Some(chain) {
                return Err(InspectionError::InvalidTag);
            }
            let next = parts.next().ok_or(InspectionError::InvalidTag)?;
            if next != action
                && (next.is_empty()
                    || next.len() > 1 && next.starts_with('0')
                    || !next.bytes().all(|b| b.is_ascii_digit())
                    || parts.next() != Some(action))
            {
                return Err(InspectionError::InvalidTag);
            }
            let value = parts.next().ok_or(InspectionError::InvalidTag)?;
            if parts.next().is_some() || value.is_empty() {
                return Err(InspectionError::InvalidTag);
            }
            if action == "tx" {
                let value = value.strip_prefix("0x").unwrap_or(value);
                !value.is_empty()
                    && value.len() % 2 == 0
                    && value
                        .bytes()
                        .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
            } else {
                value.bytes().all(|b| b.is_ascii_alphanumeric())
            }
        }
    };
    if valid {
        Ok(())
    } else {
        Err(InspectionError::InvalidTag)
    }
}

impl Scope<'_> {
    fn validate(&self) -> Result<(), InspectionError> {
        let kind = self.kind.ok_or(InspectionError::InvalidTag)?;
        if let Some(identifier) = self.external {
            if self.id.is_some()
                || self.address.is_some()
                || self.author.is_some()
                || self.inline_author.is_some()
            {
                return Err(InspectionError::InvalidTag);
            }
            return external(kind, identifier);
        }
        let kind = unsigned(kind, 65535)?;
        if self.id.is_none() && self.address.is_none() {
            return Err(InspectionError::InvalidTag);
        }
        if let Some(address) = self.address {
            let (k, p) = coordinate(address)?;
            if k != kind
                || self.author.is_some_and(|a| decode_hex(a).ok() != Some(p))
                || self
                    .inline_author
                    .is_some_and(|a| decode_hex(a).ok() != Some(p))
            {
                return Err(InspectionError::InvalidTag);
            }
        }
        if self.author.is_some()
            && self.inline_author.is_some()
            && self.author != self.inline_author
        {
            return Err(InspectionError::InvalidTag);
        }
        Ok(())
    }
    fn same_target(&self, other: &Self) -> bool {
        self.kind == other.kind
            && match (self.external, other.external) {
                (Some(a), Some(b)) => a == b,
                (None, None) => {
                    (self.id.is_some() && self.id == other.id
                        || self.address.is_some() && self.address == other.address)
                        && !(self.id.is_some() && other.id.is_some() && self.id != other.id)
                        && !(self.address.is_some()
                            && other.address.is_some()
                            && self.address != other.address)
                }
                _ => false,
            }
    }
}

pub(super) fn validate(event: &EventTemplate) -> Result<(), InspectionError> {
    let mut root = Scope::default();
    let mut parent = Scope::default();
    let mut first_person = None;
    let mut multiple_people = false;
    for index in 0..event.tag_count() {
        let mut fields = event.tag(index).ok_or(InspectionError::InvalidTag)?;
        let name = field(&mut fields)?;
        let scope = if matches!(name, "E" | "A" | "I" | "K" | "P") {
            &mut root
        } else {
            &mut parent
        };
        match name {
            "E" | "e" => {
                let id = field(&mut fields)?;
                decode_hex(id)?;
                unique(&mut scope.id, id)?;
                if let Some(hint) = fields.next() {
                    relay(hint)?;
                }
                if let Some(author) = fields.next() {
                    key(author)?;
                    scope.inline_author = Some(author);
                }
            }
            "A" | "a" => {
                let address = field(&mut fields)?;
                coordinate(address)?;
                unique(&mut scope.address, address)?;
                if let Some(hint) = fields.next() {
                    relay(hint)?;
                }
            }
            "I" | "i" => {
                unique(&mut scope.external, field(&mut fields)?)?;
                if let Some(hint) = fields.next().filter(|s| !s.is_empty()) {
                    web(hint, true)?;
                }
            }
            "K" | "k" => {
                unique(&mut scope.kind, field(&mut fields)?)?;
                if fields.next().is_some() {
                    return Err(InspectionError::InvalidTag);
                }
            }
            "P" | "p" => {
                let author = field(&mut fields)?;
                key(author)?;
                if name == "P" {
                    unique(&mut root.author, author)?;
                } else if let Some(first) = first_person {
                    multiple_people |= first != author;
                } else {
                    first_person = Some(author);
                }
                if let Some(hint) = fields.next() {
                    relay(hint)?;
                }
            }
            "q" => {
                let target = field(&mut fields)?;
                relay(field(&mut fields)?)?;
                quote(target, fields.next())?;
            }
            "emoji" => return Err(InspectionError::Unsupported),
            _ => {}
        }
    }
    root.validate()?;
    parent.validate()?;
    if root.external.is_none() && root.author.is_none() {
        return Err(InspectionError::InvalidTag);
    }
    let direct = parent.kind != Some("1111");
    if direct && !root.same_target(&parent) {
        return Err(InspectionError::InvalidTag);
    }
    if parent.external.is_none() {
        let expected = parent
            .inline_author
            .or_else(|| parent.address.and_then(|a| a.split(':').nth(1)))
            .or(if direct { root.author } else { None })
            .or(if multiple_people { None } else { first_person })
            .ok_or(InspectionError::InvalidTag)?;
        if !(0..event.tag_count()).any(|i| {
            event
                .tag(i)
                .is_some_and(|mut f| f.next() == Some("p") && f.next() == Some(expected))
        }) {
            return Err(InspectionError::InvalidTag);
        }
        if direct && root.author != Some(expected) {
            return Err(InspectionError::InvalidTag);
        }
        // Parent coordinates identify a replaceable item; e binds the exact claimed version.
        if parent.address.is_some() && parent.id.is_none() {
            return Err(InspectionError::InvalidTag);
        }
    }
    Ok(())
}

fn parent_author(event: &EventTemplate) -> Option<&str> {
    let value = |name, field| {
        (0..event.tag_count()).find_map(|i| {
            let mut fields = event.tag(i)?;
            (fields.next() == Some(name))
                .then(|| fields.nth(field))
                .flatten()
        })
    };
    // Intake already checked coherence and disambiguated p mentions. Rendering
    // only reads borrowed strings; it does not repeat curve/key validation.
    if value("i", 0).is_some() {
        return None;
    }
    value("e", 2)
        .or_else(|| value("a", 0).and_then(|a| a.split(':').nth(1)))
        .or_else(|| {
            (value("k", 0) != Some("1111"))
                .then(|| value("P", 0))
                .flatten()
        })
        .or_else(|| value("p", 0))
}

pub(super) fn role(
    event: &EventTemplate,
    name: &str,
    field: usize,
    text: &str,
) -> Option<&'static str> {
    Some(match (name, field) {
        ("E", 1) => "root event ID (target not fetched)",
        ("A", 1) => "root coordinate (target not fetched)",
        ("I", 1) => "root external identifier (unverified)",
        ("K", 1) => "claimed root kind or external type",
        ("P", 1) => "claimed root author (unverified)",
        ("e", 1) => "parent event ID (ancestry unverified)",
        ("a", 1) => "parent coordinate (version mapping unverified)",
        ("i", 1) => "parent external identifier (unverified)",
        ("k", 1) => "claimed parent kind or external type",
        ("p", 1) if parent_author(event) == Some(text) => "claimed parent author (unverified)",
        ("p", 1) => "mentioned public key (unverified)",
        ("q", 1) => "quotation target (unverified)",
        ("E" | "e", 3) => "claimed target author (not authenticated)",
        ("q", 3) => "claimed quotation author (unverified)",
        ("E" | "A" | "P" | "e" | "a" | "p" | "q", 2) => "relay hint (unverified)",
        ("I" | "i", 2) => "web page hint (unverified)",
        _ => return None,
    })
}
