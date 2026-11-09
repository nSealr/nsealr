//! NIP-18 generic repost and NIP-23 article semantics. Limits and complete field
//! inspection remain owned by the common event/review path.
use super::{
    coordinate, decode_hex, public_key, quote, relay, required_relay, unsigned, EventTemplate,
    InspectionError, OperationLimits, SignedOriginal,
};

fn unique<T>(slot: &mut Option<T>, value: T) -> Result<(), InspectionError> {
    if slot.replace(value).is_some() {
        return Err(InspectionError::InvalidTag);
    }
    Ok(())
}

pub(super) fn validate(
    event: &EventTemplate,
    limits: OperationLimits,
) -> Result<(), InspectionError> {
    if event.kind() == 30023 {
        article(event)
    } else {
        repost(event, limits)
    }
}

fn article(event: &EventTemplate) -> Result<(), InspectionError> {
    let mut metadata = [false; 5];
    for index in 0..event.tag_count() {
        let mut fields = event.tag(index).ok_or(InspectionError::InvalidTag)?;
        let name = fields.next().ok_or(InspectionError::InvalidTag)?;
        if let Some(slot) = ["d", "title", "summary", "image", "published_at"]
            .iter()
            .position(|known| *known == name)
        {
            let text = fields.next().ok_or(InspectionError::InvalidTag)?;
            // Different clients can select different duplicates. Reject ambiguity.
            if core::mem::replace(&mut metadata[slot], true) || fields.next().is_some() {
                return Err(InspectionError::InvalidTag);
            }
            if name == "published_at" {
                timestamp(text)?;
            }
            continue;
        }
        match name {
            "e" => {
                decode_hex(fields.next().ok_or(InspectionError::InvalidTag)?)?;
                if let Some(hint) = fields.next() {
                    relay(hint)?;
                }
            }
            "a" => {
                coordinate(fields.next().ok_or(InspectionError::InvalidTag)?)?;
                if let Some(hint) = fields.next() {
                    relay(hint)?;
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
            "t" if fields.next().is_none() => return Err(InspectionError::InvalidTag),
            "emoji" => return Err(InspectionError::Unsupported),
            _ => {}
        }
    }
    if !metadata[0] {
        // The product requires an explicit address, including an intentional empty d.
        return Err(InspectionError::InvalidTag);
    }
    Ok(())
}

fn timestamp(text: &str) -> Result<(), InspectionError> {
    if text.is_empty() || text.len() > 1 && text.starts_with('0') {
        return Err(InspectionError::InvalidTag);
    }
    let mut value = 0u64;
    for byte in text.bytes() {
        if !byte.is_ascii_digit() {
            return Err(InspectionError::InvalidTag);
        }
        value = value
            .checked_mul(10)
            .and_then(|n| n.checked_add(u64::from(byte - b'0')))
            .ok_or(InspectionError::InvalidTag)?;
    }
    if value > 9_007_199_254_740_991 {
        return Err(InspectionError::InvalidTag);
    }
    Ok(())
}

fn repost(event: &EventTemplate, limits: OperationLimits) -> Result<(), InspectionError> {
    let mut target = None;
    let mut author = None;
    let mut kind = None;
    let mut address = None;
    for index in 0..event.tag_count() {
        let mut fields = event.tag(index).ok_or(InspectionError::InvalidTag)?;
        let name = fields.next().ok_or(InspectionError::InvalidTag)?;
        match name {
            "e" => {
                unique(
                    &mut target,
                    decode_hex(fields.next().ok_or(InspectionError::InvalidTag)?)?,
                )?;
                required_relay(fields.next().ok_or(InspectionError::InvalidTag)?)?;
            }
            "p" => {
                unique(
                    &mut author,
                    public_key(fields.next().ok_or(InspectionError::InvalidTag)?)?,
                )?;
                if let Some(hint) = fields.next() {
                    relay(hint)?;
                }
            }
            "k" => {
                unique(
                    &mut kind,
                    unsigned(fields.next().ok_or(InspectionError::InvalidTag)?, 65535)?,
                )?;
                if fields.next().is_some() {
                    return Err(InspectionError::InvalidTag);
                }
            }
            "a" => {
                let text = fields.next().ok_or(InspectionError::InvalidTag)?;
                unique(
                    &mut address,
                    (coordinate(text)?, text.splitn(3, ':').nth(2).unwrap()),
                )?;
                if let Some(hint) = fields.next() {
                    relay(hint)?;
                }
            }
            _ => {}
        }
    }
    let target = target.ok_or(InspectionError::InvalidTag)?;
    // A declared kind is required for meaningful review even without the original.
    let kind = kind.ok_or(InspectionError::InvalidTag)?;
    if kind == 1 || address.is_some_and(|((k, p), _)| k != kind || author.is_some_and(|a| a != p)) {
        return Err(InspectionError::InvalidTag);
    }
    if event.content().is_empty() {
        if matches!(kind, 0 | 3 | 10000..=19999 | 30000..=39999) && address.is_none() {
            return Err(InspectionError::InvalidTag);
        }
        return Ok(());
    }
    let original =
        SignedOriginal::parse(event.content(), limits).map_err(|_| InspectionError::InvalidTag)?;
    original
        .verify_repost()
        .map_err(|_| InspectionError::InvalidTag)?;
    if original.id != target
        || u32::from(original.kind) != kind
        || author.is_some_and(|p| p != original.public_key)
        || address.is_some_and(|((_, p), _)| p != original.public_key)
    {
        return Err(InspectionError::InvalidTag);
    }
    let mut d_tags = 0;
    let mut d_matches = false;
    let mut d_tag = None;
    original
        .visit_tags(&mut |tag, field, text| {
            if field == 0 && text == "d" {
                d_tags += 1;
                d_tag = Some(tag);
            }
            if field == 1 && d_tag == Some(tag) {
                d_matches = address.is_some_and(|(_, id)| text == id);
            }
            Ok(())
        })
        .map_err(|_| InspectionError::InvalidTag)?;
    if let Some(((_, _), identifier)) = address {
        let original_identifier_matches = if (30000..=39999).contains(&kind) {
            d_tags == 1 && d_matches || d_tags == 0 && identifier.is_empty()
        } else {
            identifier.is_empty()
        };
        if !original_identifier_matches {
            return Err(InspectionError::InvalidTag);
        }
    }
    Ok(())
}

pub(super) fn role(kind: u16, name: &str, field: usize) -> Option<&'static str> {
    Some(match (kind, name, field) {
        (16, "e", 1) => "sole repost event ID target",
        (16, "e", 2) => "original relay (unverified)",
        (16, "p", 1) => "original author (checked only if original supplied)",
        (16, "p" | "a", 2) => "unverified relay hint",
        (16, "k", 1) => "reposted event kind (checked if original supplied)",
        (16, "a", 1) => "reposted coordinate (version not implied by coordinate)",
        (30023, "d", 1) => "article identifier (replacement address)",
        (30023, "title", 1) => "article title (not a substitute for full content)",
        (30023, "summary", 1) => "article summary (not a substitute for full content)",
        (30023, "image", 1) => "image URL (image not inspected)",
        (30023, "published_at", 1) => "claimed first publication time in Unix seconds",
        (30023, "t", 1) => "public article topic",
        (30023, "e", 1) => "unverified referenced event ID",
        (30023, "a", 1) => "unverified referenced event coordinate",
        (30023, "p", 1) => "referenced public key",
        (30023, "q", 1) => "unverified quotation target",
        (30023, "e" | "a" | "p" | "q", 2) => "unverified relay hint",
        (30023, "q", 3) => "claimed quotation author",
        _ => return None,
    })
}
