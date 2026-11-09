//! NIP17 text messages: unsigned rumor -> authenticated seal -> gift wrap.
//! Standard NIP44 calls expose no outer event; the client verifies its routing.
use crate::{
    event::{
        address, client_tag, joined, key, relay, Event, Field, CRITICAL, DETAIL, PRIVATE, PROSE,
    },
    hash::sha256,
    identity::Identity,
    json as strict, nip44, Error,
};
use alloc::{string::ToString, vec, vec::Vec};
use zeroize::Zeroizing;

// Keeps both nested encryptions inside the existing NIP44 plaintext limit.
pub(crate) const MAX_RUMOR: usize = 4096;
pub(crate) const MAX_RECEIPTS: usize = 2;

pub(crate) fn has_event_fields(text: &str) -> Result<bool, Error> {
    if !text.trim_start().starts_with('{') {
        return Ok(false);
    }
    let value = strict::parse(text.as_bytes())?;
    let object = value.as_object().ok_or(Error::Input)?;
    Ok(["kind", "pubkey", "sig"]
        .iter()
        .any(|key| object.contains_key(*key)))
}

pub(crate) struct Rumor {
    event: Event,
    recipient: [u8; 32],
}
impl Rumor {
    pub(crate) fn parse(text: &str) -> Result<Self, Error> {
        if text.len() > MAX_RUMOR {
            return Err(Error::Bounds);
        }
        let mut value = strict::parse(text.as_bytes())?;
        let id = strict::hex::<32>(strict::string(&value["id"])?)?;
        let author = strict::hex::<32>(strict::string(&value["pubkey"])?)?;
        value.as_object_mut().ok_or(Error::Input)?.remove("id");
        let event = Event::from_value(value, &author)?;
        if event.kind() != 14 {
            return Err(Error::Unsupported);
        }
        if event.id() != id {
            return Err(Error::Crypto);
        }
        let mut recipient = None;
        let mut self_tag = false;
        let mut reply = false;
        let mut subject = false;
        for tag in event.tags() {
            match tag[0].as_str() {
                "p" if (2..=3).contains(&tag.len()) => {
                    let peer = strict::hex(&tag[1])?;
                    k256::schnorr::VerifyingKey::from_bytes((&peer).into())
                        .map_err(|_| Error::Input)?;
                    if peer == author && !self_tag {
                        self_tag = true;
                    } else if peer != author && recipient.is_none() {
                        recipient = Some(peer);
                    } else {
                        return Err(Error::Unsupported);
                    }
                    relay_hint(tag)?;
                }
                "e" if !reply && (2..=3).contains(&tag.len()) => {
                    key(&tag[1])?;
                    relay_hint(tag)?;
                    reply = true;
                }
                "q" if (2..=4).contains(&tag.len()) => {
                    if tag[1].contains(':') {
                        address(&tag[1])?;
                    } else {
                        key(&tag[1])?;
                    }
                    relay_hint(tag)?;
                    if tag.len() > 3 && !tag[3].is_empty() {
                        key(&tag[3])?;
                    }
                }
                "subject" if !subject && tag.len() == 2 => subject = true,
                "client" => client_tag(tag)?,
                _ => return Err(Error::Unsupported),
            }
        }
        Ok(Self {
            event,
            recipient: recipient
                .or(if self_tag { Some(author) } else { None })
                .ok_or(Error::Input)?,
        })
    }
    pub(crate) fn outbound(&self, own: &[u8; 32], peer: &[u8; 32]) -> Result<(), Error> {
        if self.event.public_key() != own || (peer != &self.recipient && peer != own) {
            return Err(Error::Identity);
        }
        Ok(())
    }
    fn inbound(&self, own: &[u8; 32], author: &[u8; 32]) -> Result<(), Error> {
        if self.event.public_key() != author || (&self.recipient != own && author != own) {
            return Err(Error::Identity);
        }
        Ok(())
    }
    pub(crate) fn review(&self, action: &str, delivery: &[u8; 32]) -> Vec<Field> {
        let mut fields = vec![
            Field::new("Action", action, CRITICAL),
            Field::new(
                "Message author",
                strict::hex_string(self.event.public_key()),
                CRITICAL | PRIVATE,
            ),
            Field::new(
                "Message recipient",
                strict::hex_string(&self.recipient),
                CRITICAL | PRIVATE,
            ),
            Field::new(
                if delivery == self.event.public_key() {
                    "Sender's own copy"
                } else {
                    "Delivery to"
                },
                strict::hex_string(delivery),
                CRITICAL | PRIVATE,
            ),
            Field::new(
                "Message time",
                self.event.created_at().to_string(),
                CRITICAL | PRIVATE,
            ),
            Field::new("Private message", self.event.content(), PROSE | PRIVATE),
        ];
        for tag in self.event.tags() {
            let (label, flags) = match tag[0].as_str() {
                "p" => ("Recipient and relay hint", CRITICAL),
                "e" => ("Reply to message", CRITICAL),
                "q" => ("Quoted event", CRITICAL),
                "subject" => ("Conversation subject", CRITICAL),
                "client" => ("Client metadata", DETAIL),
                _ => unreachable!(),
            };
            fields.push(Field::new(label, joined(tag), flags | PRIVATE));
        }
        fields.push(Field::new(
            "Exact ordered tags",
            serde_json::to_string(self.event.tags()).expect("strings serialize"),
            DETAIL | PRIVATE,
        ));
        fields
    }
}

fn relay_hint(tag: &[alloc::string::String]) -> Result<(), Error> {
    if tag.len() > 2 && !tag[2].is_empty() {
        relay(&tag[2])?;
    }
    Ok(())
}

pub(crate) struct Receipt {
    pub(crate) outbound: bool,
    pub(crate) peer: [u8; 32],
    ciphertext: [u8; 32],
    pub(crate) rumor: Rumor,
    pub(crate) deadline: u64,
}
impl Receipt {
    pub(crate) fn encrypted(peer: [u8; 32], ciphertext: &str, rumor: Rumor, deadline: u64) -> Self {
        Self {
            outbound: true,
            peer,
            ciphertext: sha256(ciphertext.as_bytes()),
            rumor,
            deadline,
        }
    }
    pub(crate) fn matches(
        &self,
        outbound: bool,
        peer: Option<&[u8; 32]>,
        ciphertext: &str,
    ) -> bool {
        self.outbound == outbound
            && peer.is_none_or(|p| p == &self.peer)
            && self.ciphertext == sha256(ciphertext.as_bytes())
    }
    pub(crate) fn open_seal(identity: &Identity, text: &str, deadline: u64) -> Result<Self, Error> {
        let seal = Event::authenticated(text.as_bytes())?;
        if seal.kind() != 13 || !seal.tags().is_empty() {
            return Err(Error::Unsupported);
        }
        let peer = *seal.public_key();
        let plaintext = decrypt(identity, &peer, seal.content())?;
        let rumor = Rumor::parse(&plaintext)?;
        rumor.inbound(&identity.public_key(), &peer)?;
        Ok(Self {
            outbound: false,
            peer,
            ciphertext: sha256(seal.content().as_bytes()),
            rumor,
            deadline,
        })
    }
    pub(crate) fn verify_plaintext(&self, identity: &Identity, text: &str) -> Result<(), Error> {
        let rumor = Rumor::parse(text)?;
        rumor.inbound(&identity.public_key(), &self.peer)?;
        if rumor.event.id() != self.rumor.event.id() {
            return Err(Error::Crypto);
        }
        Ok(())
    }
}

pub(crate) fn decrypt(
    identity: &Identity,
    peer: &[u8; 32],
    text: &str,
) -> Result<Zeroizing<alloc::string::String>, Error> {
    if text.len() > nip44::MAX_PAYLOAD_BYTES {
        return Err(Error::Bounds);
    }
    let mut plain = Zeroizing::new(vec![0; nip44::MAX_PLAINTEXT_BYTES]);
    let len =
        nip44::decrypt(&identity.secret, peer, text, &mut plain).map_err(|_| Error::Crypto)?;
    Ok(Zeroizing::new(
        core::str::from_utf8(&plain[..len])
            .map_err(|_| Error::Input)?
            .into(),
    ))
}
