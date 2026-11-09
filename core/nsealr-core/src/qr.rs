//! A single bounded QR message. A transport checksum grants no authority.
use crate::{
    hash::sha256,
    json::{hex, hex_string},
    Error, MAX_MESSAGE,
};
use alloc::{format, string::String, vec, vec::Vec};
use base64ct::{Base64UrlUnpadded, Encoding};
use zeroize::Zeroizing;
pub const CHUNK: usize = 384;
pub const MAX_FRAMES: usize = MAX_MESSAGE.div_ceil(CHUNK);
pub const MAX_FRAME: usize = 586;

#[derive(Default)]
pub struct Collector {
    id: Option<[u8; 32]>,
    count: usize,
    received: u128,
    bytes: Zeroizing<Vec<u8>>,
    last_len: usize,
}
impl Collector {
    pub fn clear(&mut self) {
        *self = Self::default();
    }
    pub fn received(&self) -> usize {
        self.received.count_ones() as usize
    }
    pub fn expected(&self) -> usize {
        self.count
    }
    pub fn accept(&mut self, frame: &[u8]) -> Result<Option<Zeroizing<Vec<u8>>>, Error> {
        self.accept_limited(frame, MAX_MESSAGE)
    }
    pub fn accept_limited(
        &mut self,
        frame: &[u8],
        limit: usize,
    ) -> Result<Option<Zeroizing<Vec<u8>>>, Error> {
        let result = self.accept_inner(frame, limit);
        if result.is_err() {
            self.clear();
        }
        result
    }
    fn accept_inner(
        &mut self,
        frame: &[u8],
        limit: usize,
    ) -> Result<Option<Zeroizing<Vec<u8>>>, Error> {
        if frame.len() > MAX_FRAME || limit == 0 || limit > MAX_MESSAGE {
            return Err(Error::Bounds);
        }
        let text = core::str::from_utf8(frame).map_err(|_| Error::Input)?;
        let mut parts = text.split(':');
        if parts.next() != Some("ns") {
            return Err(Error::Input);
        }
        let id = hex(parts.next().ok_or(Error::Input)?)?;
        let index = number(parts.next().ok_or(Error::Input)?)?;
        let count = number(parts.next().ok_or(Error::Input)?)?;
        let chunk = parts.next().ok_or(Error::Input)?;
        if parts.next().is_some() || count == 0 || count > limit.div_ceil(CHUNK) || index >= count {
            return Err(Error::Input);
        }
        let mut decoded = Zeroizing::new([0; CHUNK]);
        let bytes = Base64UrlUnpadded::decode(chunk, &mut *decoded).map_err(|_| Error::Input)?;
        if bytes.is_empty()
            || index + 1 < count && bytes.len() != CHUNK
            || index + 1 == count && (count - 1) * CHUNK + bytes.len() > limit
        {
            return Err(Error::Bounds);
        }
        if let Some(current) = self.id {
            if id != current || count != self.count || self.bytes.len() != limit {
                return Err(Error::Input);
            }
        } else {
            self.id = Some(id);
            self.count = count;
            self.bytes = Zeroizing::new(vec![0; limit]);
        }
        let offset = index * CHUNK;
        if self.received & (1u128 << index) != 0 {
            if &self.bytes[offset..offset + bytes.len()] != bytes
                || index + 1 == count && bytes.len() != self.last_len
            {
                return Err(Error::Input);
            }
            return Ok(None);
        }
        self.bytes[offset..offset + bytes.len()].copy_from_slice(bytes);
        self.received |= 1u128 << index;
        if index + 1 == count {
            self.last_len = bytes.len();
        }
        if self.received() != count {
            return Ok(None);
        }
        let len = (count - 1) * CHUNK + self.last_len;
        if sha256(&self.bytes[..len]) != id {
            return Err(Error::Input);
        }
        let mut message = core::mem::take(&mut self.bytes);
        message.truncate(len);
        self.clear();
        Ok(Some(message))
    }
}
fn number(value: &str) -> Result<usize, Error> {
    if value.is_empty()
        || value.len() > 2
        || !value.bytes().all(|b| b.is_ascii_digit())
        || (value.len() > 1 && value.starts_with('0'))
    {
        return Err(Error::Input);
    }
    value.parse().map_err(|_| Error::Input)
}
pub fn encode(message: &[u8], index: usize) -> Result<String, Error> {
    if message.is_empty() || message.len() > MAX_MESSAGE {
        return Err(Error::Bounds);
    }
    let count = message.len().div_ceil(CHUNK);
    if index >= count {
        return Err(Error::Input);
    }
    let start = index * CHUNK;
    let end = (start + CHUNK).min(message.len());
    let mut base64 = Zeroizing::new([0; 512]);
    let chunk =
        Base64UrlUnpadded::encode(&message[start..end], &mut *base64).map_err(|_| Error::Output)?;
    Ok(format!(
        "ns:{}:{index}:{count}:{chunk}",
        hex_string(&sha256(message))
    ))
}
