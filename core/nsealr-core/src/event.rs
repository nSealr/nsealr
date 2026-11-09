use crate::{
    hash::sha256, json as strict, Error, MAX_CONTENT, MAX_MESSAGE, MAX_TAGS, MAX_TAG_FIELDS,
};
use alloc::{
    format,
    string::{String, ToString},
    vec::Vec,
};
use serde_json::{json, Value};
use zeroize::{Zeroize, Zeroizing};

pub const CRITICAL: u32 = 1;
pub const PROSE: u32 = 2;
pub const DETAIL: u32 = 4;
pub const PRIVATE: u32 = 8;
pub struct Field {
    pub label: String,
    pub value: Zeroizing<String>,
    pub flags: u32,
}
impl Field {
    pub fn new(label: impl Into<String>, value: impl Into<String>, flags: u32) -> Self {
        Self {
            label: label.into(),
            value: Zeroizing::new(value.into()),
            flags,
        }
    }
}

pub struct Event {
    pubkey: [u8; 32],
    created_at: u64,
    kind: u32,
    tags: Vec<Vec<String>>,
    content: String,
}
impl Drop for Event {
    fn drop(&mut self) {
        self.content.zeroize();
        for tag in &mut self.tags {
            for field in tag {
                field.zeroize();
            }
        }
    }
}
impl Event {
    pub fn public_key(&self) -> &[u8; 32] {
        &self.pubkey
    }
    pub fn kind(&self) -> u32 {
        self.kind
    }
    pub fn content(&self) -> &str {
        &self.content
    }
    pub fn parse(input: &[u8], expected: &[u8; 32]) -> Result<Self, Error> {
        let mut value = strict::parse(input)?;
        strict::exact_keys(
            &value,
            &["pubkey", "created_at", "kind", "tags", "content"],
            &[],
        )?;
        let pubkey = strict::hex(strict::string(&value["pubkey"])?)?;
        if &pubkey != expected {
            return Err(Error::Identity);
        }
        let kind = u32::try_from(strict::integer(&value["kind"])?).map_err(|_| Error::Input)?;
        let created_at = strict::integer(&value["created_at"])?;
        let content = match value["content"].take() {
            Value::String(v) => v,
            _ => return Err(Error::Input),
        };
        if content.len() > MAX_CONTENT {
            return Err(Error::Bounds);
        }
        let rows = match value["tags"].take() {
            Value::Array(v) => v,
            _ => return Err(Error::Input),
        };
        if rows.len() > MAX_TAGS {
            return Err(Error::Bounds);
        }
        let mut tags = Vec::with_capacity(rows.len());
        let mut total = content.len();
        for row in rows {
            let fields = match row {
                Value::Array(v) => v,
                _ => return Err(Error::Input),
            };
            if fields.is_empty() || fields.len() > MAX_TAG_FIELDS {
                return Err(Error::Bounds);
            }
            let mut tag = Vec::with_capacity(fields.len());
            for field in fields {
                let text = match field {
                    Value::String(v) => v,
                    _ => return Err(Error::Input),
                };
                total = total.checked_add(text.len()).ok_or(Error::Bounds)?;
                if text.len() > MAX_CONTENT || total > 24_576 {
                    return Err(Error::Bounds);
                }
                tag.push(text);
            }
            tags.push(tag);
        }
        Ok(Self {
            pubkey,
            created_at,
            kind,
            tags,
            content,
        })
    }
    pub fn id(&self) -> [u8; 32] {
        sha256(
            &serde_json::to_vec(&(
                0,
                strict::hex_string(&self.pubkey),
                self.created_at,
                self.kind,
                &self.tags,
                &self.content,
            ))
            .expect("JSON values serialize"),
        )
    }
    pub fn signed_json(&self, signature: &[u8; 64]) -> Result<String, Error> {
        let value = json!({"pubkey":strict::hex_string(&self.pubkey),"created_at":self.created_at,
            "kind":self.kind,"tags":self.tags,"content":self.content,"id":strict::hex_string(&self.id()),"sig":strict::hex_string(signature)});
        let out = serde_json::to_string(&value).map_err(|_| Error::Output)?;
        if out.len() > MAX_MESSAGE {
            return Err(Error::Bounds);
        }
        Ok(out)
    }
    pub fn review(&self) -> Result<Vec<Field>, Error> {
        let action = match self.kind {
            0 => "Replace profile",
            1 => "Publish note",
            3 => "Replace follows",
            5 => "Request deletion",
            6 => "Repost note",
            7 => "React to note",
            10002 => "Replace relay preferences",
            10050 => "Replace private-message relays",
            22242 => "Authorize relay connection",
            _ => return Err(Error::Unsupported),
        };
        let mut fields = Vec::new();
        fields.push(Field::new("Action", action, CRITICAL));
        fields.push(Field::new(
            "Identity",
            strict::hex_string(&self.pubkey),
            CRITICAL,
        ));
        fields.push(Field::new(
            "Created at",
            self.created_at.to_string(),
            CRITICAL,
        ));
        match self.kind {
            0 => {
                if !self.tags.is_empty() {
                    return Err(Error::Unsupported);
                }
                let profile = strict::parse(self.content.as_bytes())?;
                let map = profile.as_object().ok_or(Error::Input)?;
                for (key, value) in map {
                    if ![
                        "name",
                        "display_name",
                        "about",
                        "picture",
                        "banner",
                        "website",
                        "nip05",
                        "lud06",
                        "lud16",
                    ]
                    .contains(&key.as_str())
                    {
                        return Err(Error::Unsupported);
                    }
                    let value = strict::string(value)?;
                    fields.push(Field::new(
                        format!("Profile: {key}"),
                        value,
                        if key == "about" { PROSE } else { CRITICAL },
                    ));
                }
                fields.push(Field::new(
                    "Effect",
                    "Replaces the complete profile; omitted fields are removed",
                    CRITICAL,
                ));
            }
            1 => {
                fields.push(Field::new("Note", self.content.as_str(), PROSE));
                for tag in &self.tags {
                    note_tag(tag, &mut fields)?;
                }
            }
            3 => {
                if !self.content.is_empty() {
                    return Err(Error::Unsupported);
                }
                fields.push(Field::new(
                    "Effect",
                    "Replaces the complete follow list; no previous-list comparison is claimed",
                    CRITICAL,
                ));
                for tag in &self.tags {
                    if tag[0] != "p" || !(2..=4).contains(&tag.len()) {
                        return Err(Error::Unsupported);
                    }
                    key(&tag[1])?;
                    if tag.len() > 2 && !tag[2].is_empty() {
                        relay(&tag[2])?;
                    }
                    fields.push(Field::new("Follow", joined(tag), CRITICAL));
                }
            }
            5 => {
                if self.tags.is_empty() {
                    return Err(Error::Input);
                }
                fields.push(Field::new("Deletion reason", self.content.as_str(), PROSE));
                let mut targets = 0;
                for tag in &self.tags {
                    match tag[0].as_str() {
                        "e" if tag.len() == 2 => {
                            key(&tag[1])?;
                            targets += 1;
                        }
                        "k" if tag.len() == 2 => {
                            numeric(&tag[1])?;
                        }
                        _ => return Err(Error::Unsupported),
                    }
                    fields.push(Field::new("Deletion target", joined(tag), CRITICAL));
                }
                if targets == 0 {
                    return Err(Error::Input);
                }
                fields.push(Field::new(
                    "Effect",
                    "Requests relay deletion; copies may remain elsewhere",
                    CRITICAL,
                ));
            }
            6 => {
                let (event, author) = reference_pair(&self.tags)?;
                if !self.content.is_empty() {
                    verify_original(&self.content, &event, &author)?;
                }
                for tag in &self.tags {
                    fields.push(Field::new("Repost target", joined(tag), CRITICAL));
                }
                if !self.content.is_empty() {
                    fields.push(Field::new("Original event", self.content.as_str(), PROSE));
                }
            }
            7 => {
                reference_pair(&self.tags)?;
                if self.content.len() > 256 {
                    return Err(Error::Bounds);
                }
                fields.push(Field::new("Reaction", self.content.as_str(), CRITICAL));
                for tag in &self.tags {
                    fields.push(Field::new("Reaction target", joined(tag), CRITICAL));
                }
            }
            10002 | 10050 => {
                if !self.content.is_empty() {
                    return Err(Error::Input);
                }
                fields.push(Field::new(
                    "Effect",
                    "Replaces the complete relay list",
                    CRITICAL,
                ));
                for tag in &self.tags {
                    if self.kind == 10002 {
                        if tag[0] != "r"
                            || !(2..=3).contains(&tag.len())
                            || (tag.len() == 3 && !["read", "write"].contains(&tag[2].as_str()))
                        {
                            return Err(Error::Unsupported);
                        }
                    } else if tag[0] != "relay" || tag.len() != 2 {
                        return Err(Error::Unsupported);
                    }
                    relay(&tag[1])?;
                    fields.push(Field::new("Relay", joined(tag), CRITICAL));
                }
            }
            22242 => {
                if !self.content.is_empty() || self.tags.len() != 2 {
                    return Err(Error::Input);
                }
                let mut service = false;
                let mut challenge = false;
                for tag in &self.tags {
                    if tag.len() != 2 {
                        return Err(Error::Input);
                    }
                    match tag[0].as_str() {
                        "relay" if !service => {
                            relay(&tag[1])?;
                            service = true;
                        }
                        "challenge" if !challenge && !tag[1].is_empty() => {
                            challenge = true;
                        }
                        _ => return Err(Error::Unsupported),
                    }
                    fields.push(Field::new(
                        if tag[0] == "relay" {
                            "Authorize service"
                        } else {
                            "Connection challenge"
                        },
                        tag[1].as_str(),
                        CRITICAL,
                    ));
                }
                if !service || !challenge {
                    return Err(Error::Input);
                }
                fields.push(Field::new(
                    "Effect",
                    "Proves this identity to the displayed relay for this challenge",
                    CRITICAL,
                ));
            }
            _ => unreachable!(),
        }
        fields.push(Field::new(
            "Exact ordered tags",
            serde_json::to_string(&self.tags).map_err(|_| Error::Output)?,
            DETAIL,
        ));
        if self.kind != 1 && !self.content.is_empty() {
            fields.push(Field::new("Exact content", self.content.as_str(), DETAIL));
        }
        Ok(fields)
    }
}
fn key(value: &str) -> Result<(), Error> {
    strict::hex::<32>(value).map(|_| ())
}
fn numeric(value: &str) -> Result<u32, Error> {
    if value.is_empty()
        || !value.bytes().all(|b| b.is_ascii_digit())
        || (value.len() > 1 && value.starts_with('0'))
    {
        return Err(Error::Input);
    }
    value.parse().map_err(|_| Error::Input)
}
fn relay(value: &str) -> Result<(), Error> {
    let host = value
        .strip_prefix("wss://")
        .or_else(|| value.strip_prefix("ws://"))
        .ok_or(Error::Input)?;
    if host.is_empty()
        || host.starts_with('/')
        || value.chars().any(|c| c.is_whitespace() || c.is_control())
        || host.contains('@')
        || host.contains('#')
    {
        return Err(Error::Input);
    }
    Ok(())
}
fn joined(tag: &[String]) -> String {
    serde_json::to_string(tag).expect("strings serialize")
}
fn note_tag(tag: &[String], fields: &mut Vec<Field>) -> Result<(), Error> {
    let label = match tag[0].as_str() {
        "e" if (2..=5).contains(&tag.len()) => {
            key(&tag[1])?;
            if tag.len() > 2 && !tag[2].is_empty() {
                relay(&tag[2])?;
            }
            if tag.len() > 3 && !["root", "reply", "mention"].contains(&tag[3].as_str()) {
                return Err(Error::Unsupported);
            }
            if tag.len() > 4 {
                key(&tag[4])?;
            }
            "Note reference"
        }
        "p" if (2..=4).contains(&tag.len()) => {
            key(&tag[1])?;
            if tag.len() > 2 && !tag[2].is_empty() {
                relay(&tag[2])?;
            }
            "Mentioned identity"
        }
        "q" if (2..=4).contains(&tag.len()) => {
            key(&tag[1])?;
            if tag.len() > 2 && !tag[2].is_empty() {
                relay(&tag[2])?;
            }
            if tag.len() > 3 {
                key(&tag[3])?;
            }
            "Quoted event"
        }
        "t" | "r" | "subject" | "content-warning" if tag.len() == 2 => "Note metadata",
        _ => return Err(Error::Unsupported),
    };
    fields.push(Field::new(label, joined(tag), CRITICAL));
    Ok(())
}
fn reference_pair(tags: &[Vec<String>]) -> Result<([u8; 32], [u8; 32]), Error> {
    let mut event = None;
    let mut author = None;
    for tag in tags {
        match tag[0].as_str() {
            "e" if event.is_none() && (2..=3).contains(&tag.len()) => {
                event = Some(strict::hex(&tag[1])?);
                if tag.len() == 3 && !tag[2].is_empty() {
                    relay(&tag[2])?;
                }
            }
            "p" if author.is_none() && (2..=3).contains(&tag.len()) => {
                author = Some(strict::hex(&tag[1])?);
                if tag.len() == 3 && !tag[2].is_empty() {
                    relay(&tag[2])?;
                }
            }
            "k" if tag.len() == 2 && tag[1] == "1" => (),
            _ => return Err(Error::Unsupported),
        }
    }
    Ok((event.ok_or(Error::Input)?, author.ok_or(Error::Input)?))
}
fn verify_original(text: &str, expected_id: &[u8; 32], author: &[u8; 32]) -> Result<(), Error> {
    let mut value = strict::parse(text.as_bytes())?;
    strict::exact_keys(
        &value,
        &[
            "pubkey",
            "created_at",
            "kind",
            "tags",
            "content",
            "id",
            "sig",
        ],
        &[],
    )?;
    let id = strict::hex::<32>(strict::string(&value["id"])?)?;
    let signature = strict::hex::<64>(strict::string(&value["sig"])?)?;
    value.as_object_mut().ok_or(Error::Input)?.remove("id");
    value.as_object_mut().ok_or(Error::Input)?.remove("sig");
    let event = Event::parse(
        &serde_json::to_vec(&value).map_err(|_| Error::Input)?,
        author,
    )?;
    if event.kind != 1
        || event.id() != id
        || &id != expected_id
        || event.tags.iter().any(|t| t[0] == "-")
    {
        return Err(Error::Input);
    }
    let key = k256::schnorr::VerifyingKey::from_bytes(author.into()).map_err(|_| Error::Crypto)?;
    let sig =
        k256::schnorr::Signature::try_from(signature.as_slice()).map_err(|_| Error::Crypto)?;
    key.verify_raw(&id, &sig).map_err(|_| Error::Crypto)
}
