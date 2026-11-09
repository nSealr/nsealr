//! Authenticated, bounded NIP17 kind-14 receive processing over NIP59/NIP44.
//!
//! This module authenticates input; it does not grant a client permission to
//! receive plaintext. The device owner must separately bind the requesting
//! client, perform complete private local review and obtain a fresh release
//! decision. No public protocol method or raw-cipher permission invokes this API.
//! All decrypted bytes belong in internal memory, never the public QR workspace.

use crate::{
    event::{decimal, fixed_hex, hex, json_string, EventError, Reader, MAX_FIELDS, MAX_TAGS},
    hash::Sha256,
    nip19::SecretKey,
    nip44,
};
use k256::schnorr::{Signature, SigningKey, VerifyingKey};
use zeroize::{Zeroize, Zeroizing};

/// Maximum complete incoming gift-wrap event JSON bytes. A transport envelope
/// must independently fit its own bound including every enclosing field.
pub const MAX_GIFT_WRAP_BYTES: usize = 8192;
/// Maximum decrypted signed seal JSON bytes.
pub const MAX_SEAL_BYTES: usize = 4096;
/// Maximum decrypted unsigned rumor JSON bytes.
pub const MAX_RUMOR_BYTES: usize = 2560;
/// Maximum decoded kind-14 message content in UTF-8 bytes.
pub const MAX_MESSAGE_BYTES: usize = 2048;
const MAX_FIELD_BYTES: usize = 256;

/// Failures contain no plaintext, sender metadata or ciphertext.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Error {
    /// Strict JSON, shape, scalar spelling or resource validation failed.
    Event(EventError),
    /// The outer event was not a valid signed kind-1059 gift wrap.
    GiftWrap,
    /// The sole routing recipient did not match the actual local key.
    Recipient,
    /// The inner signed event was not a valid kind-13 seal with empty tags.
    Seal,
    /// The unsigned kind-14 rumor ID, author or conversation did not match.
    Rumor,
    /// NIP44 authentication or bounded decoding failed.
    Cipher(nip44::Error),
}
impl From<EventError> for Error {
    fn from(value: EventError) -> Self {
        Self::Event(value)
    }
}

/// Caller-owned private storage. Place this in explicitly owned internal RAM.
/// No allocation, formatting, cloning or access to intermediate seals is exposed.
/// Beginning another receive, every failed receive, explicit clear and drop wipe
/// all three arrays. This does not claim erasure of moves, registers or the caller.
pub struct ReceiveWorkspace {
    seal: [u8; MAX_SEAL_BYTES],
    rumor: [u8; MAX_RUMOR_BYTES],
    content: [u8; MAX_MESSAGE_BYTES],
}
impl ReceiveWorkspace {
    /// Empty private storage; the device adapter must verify its placement.
    pub const fn new() -> Self {
        Self {
            seal: [0; MAX_SEAL_BYTES],
            rumor: [0; MAX_RUMOR_BYTES],
            content: [0; MAX_MESSAGE_BYTES],
        }
    }
    /// Wipes every owned byte. An authenticated view prevents concurrent reuse.
    pub fn clear(&mut self) {
        self.seal.zeroize();
        self.rumor.zeroize();
        self.content.zeroize();
    }
}
impl Default for ReceiveWorkspace {
    fn default() -> Self {
        Self::new()
    }
}
impl Drop for ReceiveWorkspace {
    fn drop(&mut self) {
        self.clear();
    }
}

struct MessageMetadata {
    sender: [u8; 32],
    recipient: [u8; 32],
    rumor_id: [u8; 32],
    wrap_id: [u8; 32],
    created_at: u64,
    tags: (usize, usize),
    content_len: usize,
    rumor_len: usize,
}

/// A fully authenticated private message borrowed from one exclusive workspace.
/// Its inspection methods grant no release authority. It cannot be cloned or
/// formatted; dropping it wipes all workspace arrays before another use.
pub struct AuthenticatedMessage<'a> {
    workspace: &'a mut ReceiveWorkspace,
    metadata: MessageMetadata,
}
impl AuthenticatedMessage<'_> {
    /// Authenticated seal and rumor author, not the ephemeral wrapping key.
    pub fn sender(&self) -> &[u8; 32] {
        &self.metadata.sender
    }
    /// Recipient derived from the actual local secret, never a caller claim.
    pub fn recipient(&self) -> &[u8; 32] {
        &self.metadata.recipient
    }
    /// Validated unsigned rumor hash, useful for conversation deduplication.
    pub fn rumor_id(&self) -> &[u8; 32] {
        &self.metadata.rumor_id
    }
    /// Validated outer ID. Neither ID is a replay or release permission.
    pub fn gift_wrap_id(&self) -> &[u8; 32] {
        &self.metadata.wrap_id
    }
    /// Sender-provided rumor time; not a trusted local-clock sample.
    pub fn created_at(&self) -> u64 {
        self.metadata.created_at
    }
    /// Whether this is the sender's own encrypted conversation copy.
    pub fn is_sender_copy(&self) -> bool {
        self.metadata.sender == self.metadata.recipient
    }
    /// Complete decoded message for private local inspection. No normalization
    /// or truncation is applied. Controls require explicit rendering by the UI.
    pub fn content(&self) -> &str {
        core::str::from_utf8(&self.workspace.content[..self.metadata.content_len])
            .expect("authenticated UTF-8")
    }
    /// Visits every ordered tag field for complete private review, including
    /// unfamiliar tags. Temporary decoded fields are wiped after the callback.
    /// Returning an error does not release plaintext or renew any owner deadline.
    pub fn visit_tags(
        &self,
        emit: &mut dyn FnMut(usize, usize, &str) -> Result<(), EventError>,
    ) -> Result<(), EventError> {
        let (start, end) = self.metadata.tags;
        let mut reader = Reader::new_bounded(
            &self.workspace.rumor[..self.metadata.rumor_len][start..end],
            MAX_RUMOR_BYTES,
        )?;
        walk_tags(&mut reader, emit)?;
        reader.end()
    }
}
impl Drop for AuthenticatedMessage<'_> {
    fn drop(&mut self) {
        self.workspace.clear();
        self.metadata.sender.zeroize();
        self.metadata.recipient.zeroize();
        self.metadata.rumor_id.zeroize();
        self.metadata.wrap_id.zeroize();
        self.metadata.created_at.zeroize();
        self.metadata.tags.zeroize();
        self.metadata.content_len.zeroize();
        self.metadata.rumor_len.zeroize();
    }
}

/// Verify both signed layers before their respective decryption, then verify
/// the unsigned rumor hash, exact author and local conversation membership.
///
/// Supports kind-14 text messages only. Kind-15 files, other rumor kinds, raw
/// NIP07 decryption and ephemeral wraps are not silently treated as text chats.
/// Sender self-copies need not list the sender in `p` tags. Other recipients
/// must occur exactly once in the rumor's valid, nonempty participant list.
/// Expiration tags at any layer are unsupported until the device has a complete
/// qualified time policy; even malformed or future expiration tags are refused.
/// Every error wipes the workspace. Successful views wipe it on drop; the owner
/// still needs client binding, deadlines, review and a separate release decision.
pub fn receive<'a>(
    secret: &SecretKey,
    gift_wrap_json: &[u8],
    workspace: &'a mut ReceiveWorkspace,
) -> Result<AuthenticatedMessage<'a>, Error> {
    workspace.clear();
    let result = receive_inner(secret, gift_wrap_json, workspace);
    workspace.seal.zeroize();
    match result {
        Ok(metadata) => Ok(AuthenticatedMessage {
            workspace,
            metadata,
        }),
        Err(error) => {
            workspace.clear();
            Err(error)
        }
    }
}

fn receive_inner(
    secret: &SecretKey,
    input: &[u8],
    workspace: &mut ReceiveWorkspace,
) -> Result<MessageMetadata, Error> {
    let wrap = Layer::parse(input, MAX_GIFT_WRAP_BYTES, nip44::MAX_PAYLOAD_BYTES, true)?;
    if wrap.kind != 1059 || wrap.has_expiration()? || wrap.verify().is_err() {
        return Err(Error::GiftWrap);
    }
    let local = SigningKey::from_bytes(secret.as_bytes().into()).map_err(|_| Error::Recipient)?;
    let recipient: [u8; 32] = local.verifying_key().to_bytes().into();
    drop(local);
    wrap.recipients(&recipient, true)?;
    let seal_len = wrap.content(&mut |payload| {
        nip44::decrypt(secret, &wrap.public_key, payload, &mut workspace.seal)
            .map_err(Error::Cipher)
    })?;
    let seal = Layer::parse(
        &workspace.seal[..seal_len],
        MAX_SEAL_BYTES,
        nip44::MAX_PAYLOAD_BYTES,
        true,
    )?;
    if seal.kind != 13 || seal.tag_count != 0 || seal.verify().is_err() {
        return Err(Error::Seal);
    }
    let rumor_len = seal.content(&mut |payload| {
        nip44::decrypt(secret, &seal.public_key, payload, &mut workspace.rumor)
            .map_err(Error::Cipher)
    })?;
    let rumor = Layer::parse(
        &workspace.rumor[..rumor_len],
        MAX_RUMOR_BYTES,
        MAX_MESSAGE_BYTES,
        false,
    )?;
    if rumor.kind != 14
        || rumor.public_key != seal.public_key
        || rumor.has_expiration()?
        || rumor.verify().is_err()
    {
        return Err(Error::Rumor);
    }
    rumor.recipients(&recipient, false)?;
    let content_len = rumor.content(&mut |content| {
        workspace.content[..content.len()].copy_from_slice(content.as_bytes());
        Ok(content.len())
    })?;
    Ok(MessageMetadata {
        sender: rumor.public_key,
        recipient,
        rumor_id: rumor.id,
        wrap_id: wrap.id,
        created_at: rumor.created_at,
        tags: rumor.tags,
        content_len,
        rumor_len,
    })
}

struct Layer<'a> {
    input: &'a [u8],
    public_key: [u8; 32],
    id: [u8; 32],
    signature: Option<[u8; 64]>,
    created_at: u64,
    kind: u16,
    tags: (usize, usize),
    tag_count: usize,
    content: (usize, usize),
    content_max: usize,
}
impl Drop for Layer<'_> {
    fn drop(&mut self) {
        self.public_key.zeroize();
        self.id.zeroize();
        if let Some(signature) = &mut self.signature {
            signature.zeroize();
        }
        self.created_at.zeroize();
        self.kind.zeroize();
        self.tags.zeroize();
        self.content.zeroize();
        self.tag_count.zeroize();
        self.content_max.zeroize();
    }
}
impl<'a> Layer<'a> {
    fn parse(
        input: &'a [u8],
        max: usize,
        content_max: usize,
        signed: bool,
    ) -> Result<Self, EventError> {
        let mut reader = Reader::new_bounded(input, max)?;
        let mut layer = Self {
            input,
            public_key: [0; 32],
            id: [0; 32],
            signature: None,
            created_at: 0,
            kind: 0,
            tags: (0, 0),
            tag_count: 0,
            content: (0, 0),
            content_max,
        };
        let mut buffer = Zeroizing::new([0; nip44::MAX_PAYLOAD_BYTES]);
        let keys = [
            "pubkey",
            "created_at",
            "kind",
            "tags",
            "content",
            "id",
            "sig",
        ];
        reader.object(&keys[..if signed { 7 } else { 6 }], |r, key| {
            match key {
                0 => {
                    let len = r.string(&mut buffer[..64])?;
                    layer.public_key = fixed_hex(&buffer[..len])?;
                }
                1 => layer.created_at = r.number(9_007_199_254_740_991)?,
                2 => layer.kind = r.number(65535)? as u16,
                3 => {
                    r.ws();
                    let start = r.at;
                    walk_tags(r, &mut |tag, _, _| {
                        layer.tag_count = tag + 1;
                        Ok(())
                    })?;
                    layer.tags = (start, r.at);
                }
                4 => {
                    r.ws();
                    let start = r.at;
                    r.string(&mut buffer[..content_max])?;
                    layer.content = (start, r.at);
                }
                5 => {
                    let len = r.string(&mut buffer[..64])?;
                    layer.id = fixed_hex(&buffer[..len])?;
                }
                _ => {
                    let len = r.string(&mut buffer[..128])?;
                    layer.signature = Some(fixed_hex(&buffer[..len])?);
                }
            }
            Ok(())
        })?;
        reader.end()?;
        Ok(layer)
    }
    fn content<T>(&self, emit: &mut impl FnMut(&str) -> Result<T, Error>) -> Result<T, Error> {
        let mut r = Reader::new_bounded(
            &self.input[self.content.0..self.content.1],
            MAX_GIFT_WRAP_BYTES,
        )?;
        let mut buffer = Zeroizing::new([0; nip44::MAX_PAYLOAD_BYTES]);
        let len = r.string(&mut buffer[..self.content_max])?;
        r.end()?;
        let text = core::str::from_utf8(&buffer[..len]).map_err(|_| EventError::Syntax)?;
        emit(text)
    }
    fn tags(
        &self,
        emit: &mut dyn FnMut(usize, usize, &str) -> Result<(), EventError>,
    ) -> Result<(), EventError> {
        let mut r =
            Reader::new_bounded(&self.input[self.tags.0..self.tags.1], MAX_GIFT_WRAP_BYTES)?;
        walk_tags(&mut r, emit)?;
        r.end()
    }
    fn verify(&self) -> Result<(), Error> {
        let key = VerifyingKey::from_slice(&self.public_key).map_err(|_| EventError::Shape)?;
        let mut hash = Sha256::new();
        let mut count = 0usize;
        let mut emit = |bytes: &[u8]| {
            count = count.checked_add(bytes.len()).ok_or(EventError::Limit)?;
            if count > MAX_GIFT_WRAP_BYTES {
                return Err(EventError::Limit);
            }
            hash.update(bytes);
            Ok(())
        };
        emit(b"[0,\"")?;
        let public_hex = Zeroizing::new(hex::<32, 64>(&self.public_key));
        emit(&public_hex[..])?;
        emit(b"\",")?;
        let mut number = Zeroizing::new([0; 20]);
        emit(decimal(self.created_at, &mut number))?;
        emit(b",")?;
        emit(decimal(u64::from(self.kind), &mut number))?;
        emit(b",[")?;
        self.tags(&mut |tag, field, text| {
            if field == 0 {
                if tag != 0 {
                    emit(b"],")?;
                }
                emit(b"[")?;
            } else {
                emit(b",")?;
            }
            json_string(text, &mut emit)
        })?;
        if self.tag_count != 0 {
            emit(b"]")?;
        }
        emit(b"],")?;
        self.content(&mut |content| json_string(content, &mut emit).map_err(Error::Event))?;
        emit(b"]")?;
        let computed = Zeroizing::new(hash.finalize());
        if *computed != self.id {
            return Err(EventError::Shape.into());
        }
        if let Some(signature) = &self.signature {
            let signature =
                Signature::try_from(signature.as_slice()).map_err(|_| EventError::Shape)?;
            key.verify_raw(&self.id, &signature)
                .map_err(|_| EventError::Shape)?;
        }
        Ok(())
    }
    fn has_expiration(&self) -> Result<bool, EventError> {
        let mut expiration = false;
        self.tags(&mut |_, field, text| {
            expiration |= field == 0 && text == "expiration";
            Ok(())
        })?;
        Ok(expiration)
    }
    fn recipients(&self, local: &[u8; 32], outer: bool) -> Result<(), Error> {
        let mut keys = Zeroizing::new([[0u8; 32]; MAX_TAGS]);
        let mut count = 0usize;
        let mut p = false;
        let mut fields = 0usize;
        self.tags(&mut |_, field, text| {
            if field == 0 {
                if p && fields < 2 {
                    return Err(EventError::Shape);
                }
                p = text == "p";
                fields = 1;
            } else {
                fields += 1;
                if p {
                    if field == 1 {
                        let key = Zeroizing::new(fixed_hex::<32>(text.as_bytes())?);
                        VerifyingKey::from_slice(&key[..]).map_err(|_| EventError::Shape)?;
                        if keys[..count].contains(&*key) {
                            return Err(EventError::Shape);
                        }
                        keys[count] = *key;
                        count += 1;
                    } else if field > 2 {
                        return Err(EventError::Shape);
                    }
                }
            }
            Ok(())
        })?;
        if p && fields < 2 || count == 0 {
            return Err(if outer {
                Error::Recipient
            } else {
                Error::Rumor
            });
        }
        let member = keys[..count].contains(local);
        if outer {
            if count != 1 || !member {
                return Err(Error::Recipient);
            }
        } else if !member && self.public_key != *local {
            return Err(Error::Rumor);
        }
        Ok(())
    }
}

fn walk_tags(
    r: &mut Reader<'_>,
    emit: &mut dyn FnMut(usize, usize, &str) -> Result<(), EventError>,
) -> Result<(), EventError> {
    r.take(b'[')?;
    if r.eat(b']') {
        return Ok(());
    }
    let mut tag = 0usize;
    loop {
        if tag == MAX_TAGS {
            return Err(EventError::Limit);
        }
        r.take(b'[')?;
        if r.eat(b']') {
            return Err(EventError::Shape);
        }
        let mut field = 0usize;
        loop {
            if field == MAX_FIELDS {
                return Err(EventError::Limit);
            }
            let mut buffer = Zeroizing::new([0; MAX_FIELD_BYTES]);
            let len = r.string(&mut *buffer)?;
            if field == 0 && len == 0 {
                return Err(EventError::Shape);
            }
            emit(
                tag,
                field,
                core::str::from_utf8(&buffer[..len]).map_err(|_| EventError::Syntax)?,
            )?;
            field += 1;
            if r.eat(b']') {
                break;
            }
            r.take(b',')?;
        }
        tag += 1;
        if r.eat(b']') {
            return Ok(());
        }
        r.take(b',')?;
    }
}

#[cfg(test)]
mod tests;
