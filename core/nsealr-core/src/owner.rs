use crate::{
    event::{Event, Field, CRITICAL, PRIVATE, PROSE},
    identity::Identity,
    json as strict, nip44,
    qr::Collector,
    Error, MAX_MESSAGE,
};
use alloc::{format, string::String, vec, vec::Vec};
use serde_json::{json, Value};
use zeroize::{Zeroize, Zeroizing};
pub const LIFETIME_MS: u64 = 600_000;
enum Operation {
    PublicKey,
    Sign(Event),
    Encrypt {
        peer: [u8; 32],
        text: Zeroizing<String>,
    },
    Decrypt {
        plaintext: Zeroizing<String>,
    },
}
struct Pending {
    id: String,
    operation: Operation,
    fields: Vec<Field>,
    seen: Vec<bool>,
    deadline: u64,
}
#[derive(Default)]
pub struct Owner {
    identity: Option<Identity>,
    pending: Option<Pending>,
    response: Option<Zeroizing<String>>,
    generation: u64,
    last_time: u64,
    last_entropy: [u8; 32],
    pub collector: Collector,
    scan_started: Option<u64>,
}
impl Owner {
    pub fn identity(&self) -> Result<&Identity, Error> {
        self.identity.as_ref().ok_or(Error::Locked)
    }
    pub fn select(&mut self, identity: Identity) {
        self.lock();
        self.identity = Some(identity);
    }
    pub fn lock(&mut self) {
        self.cancel();
        self.identity = None;
    }
    pub fn cancel(&mut self) {
        self.pending = None;
        self.response = None;
        self.collector.clear();
        self.scan_started = None;
        self.generation = self.generation.saturating_add(1);
    }
    pub fn generation(&self) -> u64 {
        self.generation
    }
    pub fn fields(&self) -> &[Field] {
        self.pending.as_ref().map_or(&[], |p| p.fields.as_slice())
    }
    pub fn response(&self) -> Result<&str, Error> {
        self.response
            .as_deref()
            .map(|s| s.as_str())
            .ok_or(Error::Stale)
    }
    fn clock(&mut self, now: u64) -> Result<(), Error> {
        if now < self.last_time {
            self.cancel();
            return Err(Error::Stale);
        }
        self.last_time = now;
        Ok(())
    }
    pub fn receive_frame(&mut self, frame: &[u8], now: u64) -> Result<bool, Error> {
        self.clock(now)?;
        if self.scan_started.is_none() {
            self.cancel();
            self.scan_started = Some(now);
        }
        if now - self.scan_started.ok_or(Error::Stale)? >= LIFETIME_MS {
            self.cancel();
            return Err(Error::Stale);
        }
        match self.collector.accept(frame) {
            Ok(Some(message)) => {
                self.scan_started = None;
                self.request(&message, now)?;
                Ok(true)
            }
            Ok(None) => Ok(false),
            Err(e) => {
                self.cancel();
                Err(e)
            }
        }
    }
    pub fn request(&mut self, input: &[u8], now: u64) -> Result<(), Error> {
        self.cancel();
        self.clock(now)?;
        if self.generation == u64::MAX {
            return Err(Error::Stale);
        }
        let request = strict::parse(input)?;
        strict::exact_keys(&request, &["id", "method", "params"], &[])?;
        let id = strict::string(&request["id"])?;
        if id.is_empty() || id.len() > 128 {
            return Err(Error::Input);
        }
        let outcome = self.prepare(&request, now);
        match outcome {
            Ok(pending) => {
                self.pending = Some(pending);
                Ok(())
            }
            Err(e) => {
                self.response = Some(response_error(id, e.message()));
                Err(e)
            }
        }
    }
    fn prepare(&self, request: &Value, now: u64) -> Result<Pending, Error> {
        let identity = self.identity()?;
        let method = strict::string(&request["method"])?;
        let params = request["params"].as_array().ok_or(Error::Input)?;
        let (operation, fields) = match method {
            "get_public_key" if params.is_empty() => (
                Operation::PublicKey,
                vec![
                    Field::new("Action", "Share public identity", CRITICAL),
                    Field::new("Identity", identity.npub(), CRITICAL),
                ],
            ),
            "sign_event" if params.len() == 1 => {
                let event = Event::parse(
                    strict::string(&params[0])?.as_bytes(),
                    &identity.public_key(),
                )?;
                let fields = event.review()?;
                (Operation::Sign(event), fields)
            }
            "nip44_encrypt" | "nip44_decrypt" if params.len() == 2 => {
                let peer = strict::hex::<32>(strict::string(&params[0])?)?;
                k256::schnorr::VerifyingKey::from_bytes((&peer).into())
                    .map_err(|_| Error::Input)?;
                let text = strict::string(&params[1])?;
                let mut fields = vec![
                    Field::new(
                        "Action",
                        if method == "nip44_encrypt" {
                            "Encrypt private text"
                        } else {
                            "Release decrypted text"
                        },
                        CRITICAL,
                    ),
                    Field::new("Identity", identity.npub(), CRITICAL),
                    Field::new("Other identity", strict::hex_string(&peer), CRITICAL),
                ];
                if method == "nip44_encrypt" {
                    if text.is_empty() || text.len() > nip44::MAX_PLAINTEXT_BYTES {
                        return Err(Error::Bounds);
                    }
                    fields.push(Field::new("Private text", text, PROSE | PRIVATE));
                    (
                        Operation::Encrypt {
                            peer,
                            text: Zeroizing::new(text.into()),
                        },
                        fields,
                    )
                } else {
                    if text.len() > nip44::MAX_PAYLOAD_BYTES {
                        return Err(Error::Bounds);
                    }
                    let mut plain = Zeroizing::new(vec![0; nip44::MAX_PLAINTEXT_BYTES]);
                    let len = nip44::decrypt(&identity.secret, &peer, text, &mut plain)
                        .map_err(|_| Error::Crypto)?;
                    let text = core::str::from_utf8(&plain[..len]).map_err(|_| Error::Input)?;
                    fields.push(Field::new("Decrypted text", text, PROSE | PRIVATE));
                    fields.push(Field::new("Release to client","The connected client will receive this plaintext. Encryption alone does not prove a message's author.",CRITICAL));
                    (
                        Operation::Decrypt {
                            plaintext: Zeroizing::new(text.into()),
                        },
                        fields,
                    )
                }
            }
            _ => return Err(Error::Unsupported),
        };
        let seen = vec![false; fields.len()];
        Ok(Pending {
            id: strict::string(&request["id"])?.into(),
            operation,
            fields,
            seen,
            deadline: now.checked_add(LIFETIME_MS).ok_or(Error::Stale)?,
        })
    }
    pub fn seen(&mut self, generation: u64, index: usize) -> Result<(), Error> {
        if generation != self.generation {
            return Err(Error::Stale);
        }
        *self
            .pending
            .as_mut()
            .and_then(|p| p.seen.get_mut(index))
            .ok_or(Error::Stale)? = true;
        Ok(())
    }
    pub fn approve(
        &mut self,
        generation: u64,
        partial: bool,
        entropy: &mut [u8],
        now: u64,
    ) -> Result<(), Error> {
        let result = self.approve_inner(generation, partial, entropy, now);
        entropy.zeroize();
        result
    }
    fn approve_inner(
        &mut self,
        generation: u64,
        partial: bool,
        entropy: &[u8],
        now: u64,
    ) -> Result<(), Error> {
        // Taking the pending operation precedes every approval check and backend
        // call. Even a failed or stale attempt cannot reuse the approval.
        let mut pending = self.pending.take().ok_or(Error::Stale)?;
        self.response = None;
        let result = (|| {
            self.clock(now)?;
            if generation != self.generation || now >= pending.deadline {
                return Err(Error::Stale);
            }
            for (field, seen) in pending.fields.iter().zip(&pending.seen) {
                if !seen && (field.flags & CRITICAL != 0 || field.flags & PROSE != 0 && !partial) {
                    return Err(Error::Review);
                }
            }
            pending.fields.clear();
            pending.seen.clear();
            let randomness = if matches!(
                pending.operation,
                Operation::Sign(_) | Operation::Encrypt { .. }
            ) {
                let bytes: &[u8; 32] = entropy.try_into().map_err(|_| Error::Entropy)?;
                let tag = crate::hash::sha256(bytes);
                if tag == self.last_entropy {
                    return Err(Error::Entropy);
                }
                self.last_entropy = tag;
                Some(bytes)
            } else {
                None
            };
            let identity = self.identity()?;
            let value = match &pending.operation {
                Operation::PublicKey => strict::hex_string(&identity.public_key()),
                Operation::Sign(event) => event
                    .signed_json(&identity.sign(&event.id(), randomness.ok_or(Error::Entropy)?)?)?,
                Operation::Encrypt { peer, text } => {
                    let mut out = Zeroizing::new(vec![0; nip44::MAX_PAYLOAD_BYTES]);
                    let len = nip44::encrypt(
                        &identity.secret,
                        peer,
                        text,
                        randomness.ok_or(Error::Entropy)?,
                        &mut out,
                    )
                    .map_err(|_| Error::Crypto)?;
                    core::str::from_utf8(&out[..len])
                        .map_err(|_| Error::Crypto)?
                        .into()
                }
                Operation::Decrypt { plaintext } => plaintext.as_str().into(),
            };
            let value = Zeroizing::new(value);
            let response = serde_json::to_string(&json!({"id":pending.id,"result":value.as_str()}))
                .map_err(|_| Error::Output)?;
            if response.len() > MAX_MESSAGE {
                return Err(Error::Bounds);
            }
            Ok(Zeroizing::new(response))
        })();
        match result {
            Ok(value) => {
                self.response = Some(value);
                Ok(())
            }
            Err(e) => {
                self.response = Some(response_error(&pending.id, e.message()));
                Err(e)
            }
        }
    }
    pub fn reject(&mut self, generation: u64) -> Result<(), Error> {
        let pending = self.pending.take().ok_or(Error::Stale)?;
        self.response = None;
        if generation != self.generation {
            return Err(Error::Stale);
        }
        self.response = Some(response_error(&pending.id, "Rejected on device"));
        Ok(())
    }
}
fn response_error(id: &str, message: &str) -> Zeroizing<String> {
    Zeroizing::new(format!(
        "{{\"id\":{},\"error\":{}}}",
        serde_json::to_string(id).expect("string"),
        serde_json::to_string(message).expect("string")
    ))
}
