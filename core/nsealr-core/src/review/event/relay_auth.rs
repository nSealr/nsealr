//! Closed NIP42 AUTH scope. No relay connection or wall-clock claim follows.
use super::{comments, EventTemplate, FixedStr, InspectionError};

pub(super) fn validate(event: &EventTemplate) -> Result<(), InspectionError> {
    if !event.content().is_empty() || event.tag_count() != 2 {
        return Err(InspectionError::InvalidTag);
    }
    let mut seen_relay = false;
    let mut seen_challenge = false;
    for index in 0..event.tag_count() {
        let mut fields = event.tag(index).ok_or(InspectionError::InvalidTag)?;
        let name = fields.next().ok_or(InspectionError::InvalidTag)?;
        let value = fields.next().ok_or(InspectionError::InvalidTag)?;
        if value.is_empty() || fields.next().is_some() {
            return Err(InspectionError::InvalidTag);
        }
        match name {
            "relay" if !seen_relay => {
                seen_relay = true;
                let (scheme, rest) = if let Some(rest) = value.strip_prefix("wss://") {
                    ("https://", rest)
                } else if let Some(rest) = value.strip_prefix("ws://") {
                    ("http://", rest)
                } else {
                    return Err(InspectionError::InvalidTag);
                };
                // At most256 signed URL bytes plus the two-character scheme
                // difference. Only this validation temporary is transformed.
                let mut url = FixedStr::<258>::new();
                url.try_push_str(scheme)
                    .map_err(|_| InspectionError::Limit)?;
                url.try_push_str(rest).map_err(|_| InspectionError::Limit)?;
                comments::web(url.as_str(), false)?;
            }
            "challenge" if !seen_challenge => seen_challenge = true,
            _ => return Err(InspectionError::InvalidTag),
        }
    }
    if !seen_relay || !seen_challenge {
        return Err(InspectionError::InvalidTag);
    }
    Ok(())
}
