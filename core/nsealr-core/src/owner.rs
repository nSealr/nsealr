use crate::{
    event::{Event, Field, CRITICAL, PRIVATE, PROSE},
    identity::Identity,
    json as strict, nip44,
    private::{self, Receipt, Rumor, MAX_RECEIPTS},
    qr::Collector,
    Error, MAX_MESSAGE,
};
use alloc::{
    format,
    string::{String, ToString},
    vec,
    vec::Vec,
};
use serde_json::{json, Value};
use zeroize::{Zeroize, Zeroizing};
pub const LIFETIME_MS: u64 = 600_000;
enum Operation {
    PublicKey,
    Sign(Event),
    Encrypt {
        peer: [u8; 32],
        text: Zeroizing<String>,
        rumor: Option<Rumor>,
    },
    Decrypt {
        plaintext: Zeroizing<String>,
        receipt: Option<Receipt>,
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
    response_deadline: u64,
    receipts: Vec<Receipt>,
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
        self.receipts.clear();
        self.clear_request();
    }
    fn clear_request(&mut self) {
        self.pending = None;
        self.response = None;
        self.collector.clear();
        self.scan_started = None;
        self.generation = self.generation.saturating_add(1);
    }
    pub fn finish_response(&mut self) {
        if self.pending.is_some() || self.scan_started.is_some() {
            self.cancel();
        } else {
            self.response = None;
        }
    }
    /// The firmware calls this from its existing monotonic event loop and clears
    /// any rendered private text when true or an error is returned.
    pub fn tick(&mut self, now: u64) -> Result<bool, Error> {
        self.clock(now)?;
        let expired = self.pending.as_ref().is_some_and(|p| now >= p.deadline)
            || self
                .scan_started
                .is_some_and(|start| now - start >= LIFETIME_MS)
            || self.receipts.iter().any(|r| now >= r.deadline)
            || (self.response.is_some() && now >= self.response_deadline);
        if expired {
            self.cancel();
        }
        Ok(expired)
    }
    pub fn generation(&self) -> u64 {
        self.generation
    }
    pub fn fields(&self) -> &[Field] {
        self.pending.as_ref().map_or(&[], |p| p.fields.as_slice())
    }
    pub fn confirmation(&self) -> Result<&'static str, Error> {
        Ok(
            match &self.pending.as_ref().ok_or(Error::Stale)?.operation {
                Operation::PublicKey => "Share public key",
                Operation::Sign(event) => return event.confirmation(),
                Operation::Encrypt { .. } => "Encrypt message",
                Operation::Decrypt { .. } => "Share plaintext",
            },
        )
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
            if self.pending.is_some() {
                self.receipts.clear();
            }
            self.clear_request();
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
        if self.pending.is_some() || self.scan_started.is_some() {
            self.receipts.clear();
        }
        self.clear_request();
        self.clock(now)?;
        if self.generation == u64::MAX {
            return Err(Error::Stale);
        }
        let mut receipts = core::mem::take(&mut self.receipts);
        receipts.retain(|r| now < r.deadline);
        let request = strict::parse(input)?;
        strict::exact_keys(&request, &["id", "method", "params"], &[])?;
        let id = strict::string(&request["id"])?;
        if id.is_empty() || id.len() > 128 {
            return Err(Error::Input);
        }
        let outcome = self.prepare(&request, now, &mut receipts);
        match outcome {
            Ok(pending) => {
                self.pending = Some(pending);
                self.receipts = receipts;
                Ok(())
            }
            Err(e) => {
                self.response = Some(response_error(id, e.message()));
                self.response_deadline = now.saturating_add(LIFETIME_MS);
                Err(e)
            }
        }
    }
    fn prepare(
        &self,
        request: &Value,
        now: u64,
        receipts: &mut Vec<Receipt>,
    ) -> Result<Pending, Error> {
        let identity = self.identity()?;
        let mut deadline = now.checked_add(LIFETIME_MS).ok_or(Error::Stale)?;
        let method = strict::string(&request["method"])?;
        let params = request["params"].as_array().ok_or(Error::Input)?;
        let (operation, fields) = match method {
            "get_public_key" if params.is_empty() => {
                receipts.clear();
                (
                    Operation::PublicKey,
                    vec![
                        Field::new("Action", "Share public identity", CRITICAL),
                        Field::new("Identity", identity.npub(), CRITICAL),
                    ],
                )
            }
            "sign_event" if params.len() == 1 => {
                let event = Event::parse(
                    strict::string(&params[0])?.as_bytes(),
                    &identity.public_key(),
                )?;
                let fields = if event.kind() == 13 {
                    if !event.tags().is_empty() {
                        return Err(Error::Unsupported);
                    }
                    let index = receipts
                        .iter()
                        .position(|r| r.matches(true, None, event.content()))
                        .ok_or(Error::Stale)?;
                    let receipt = receipts.remove(index);
                    deadline = deadline.min(receipt.deadline);
                    let mut fields = receipt
                        .rumor
                        .review("Sign private-message seal", &receipt.peer);
                    fields.push(Field::new(
                        "Seal time",
                        event.created_at().to_string(),
                        CRITICAL,
                    ));
                    fields.push(Field::new(
                        "Exact encrypted content",
                        event.content(),
                        crate::event::DETAIL,
                    ));
                    fields
                } else {
                    receipts.clear();
                    event.review()?
                };
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
                    let rumor = if private::has_event_fields(text)? {
                        let rumor = Rumor::parse(text)?;
                        rumor.outbound(&identity.public_key(), &peer)?;
                        if receipts.len() >= MAX_RECEIPTS {
                            return Err(Error::Bounds);
                        }
                        fields = rumor.review("Encrypt private message", &peer);
                        Some(rumor)
                    } else {
                        receipts.clear();
                        fields.push(Field::new("Private text", text, PROSE | PRIVATE));
                        None
                    };
                    (
                        Operation::Encrypt {
                            peer,
                            text: Zeroizing::new(text.into()),
                            rumor,
                        },
                        fields,
                    )
                } else {
                    let plaintext = private::decrypt(identity, &peer, text)?;
                    let receipt = if let Some(index) = receipts
                        .iter()
                        .position(|r| r.matches(false, Some(&peer), text))
                    {
                        let receipt = receipts.remove(index);
                        deadline = deadline.min(receipt.deadline);
                        receipt.verify_plaintext(identity, &plaintext)?;
                        fields = receipt
                            .rumor
                            .review("Release verified private message", &identity.public_key());
                        fields.push(Field::new(
                            "Release to client",
                            "The connected client will receive this private message in plaintext.",
                            CRITICAL,
                        ));
                        None
                    } else if private::has_event_fields(&plaintext)? {
                        if receipts.len() >= MAX_RECEIPTS {
                            return Err(Error::Bounds);
                        }
                        let receipt = Receipt::open_seal(
                            identity,
                            &plaintext,
                            now.checked_add(LIFETIME_MS).ok_or(Error::Stale)?,
                        )?;
                        fields = receipt
                            .rumor
                            .review("Open verified private-message seal", &identity.public_key());
                        fields.push(Field::new("Release to client", "Release the signed seal to the client. Releasing its message text requires the next approval.", CRITICAL));
                        Some(receipt)
                    } else {
                        receipts.clear();
                        fields.push(Field::new(
                            "Decrypted text",
                            plaintext.as_str(),
                            PROSE | PRIVATE,
                        ));
                        fields.push(Field::new("Release to client","The connected client will receive this plaintext. Encryption alone does not prove a message's author.",CRITICAL));
                        None
                    };
                    (Operation::Decrypt { plaintext, receipt }, fields)
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
            deadline,
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
        if result.is_err() {
            self.receipts.clear();
        }
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
            let value = match pending.operation {
                Operation::PublicKey => strict::hex_string(&identity.public_key()),
                Operation::Sign(event) => event
                    .signed_json(&identity.sign(&event.id(), randomness.ok_or(Error::Entropy)?)?)?,
                Operation::Encrypt { peer, text, rumor } => {
                    let mut out = Zeroizing::new(vec![0; nip44::MAX_PAYLOAD_BYTES]);
                    let len = nip44::encrypt(
                        &identity.secret,
                        &peer,
                        &text,
                        randomness.ok_or(Error::Entropy)?,
                        &mut out,
                    )
                    .map_err(|_| Error::Crypto)?;
                    let ciphertext =
                        core::str::from_utf8(&out[..len]).map_err(|_| Error::Crypto)?;
                    if let Some(rumor) = rumor {
                        self.receipts.push(Receipt::encrypted(
                            peer,
                            ciphertext,
                            rumor,
                            pending.deadline,
                        ));
                    }
                    ciphertext.into()
                }
                Operation::Decrypt { plaintext, receipt } => {
                    if let Some(receipt) = receipt {
                        self.receipts.push(receipt);
                    }
                    plaintext.as_str().into()
                }
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
                self.response_deadline = pending.deadline;
                Ok(())
            }
            Err(e) => {
                self.receipts.clear();
                self.response = Some(response_error(&pending.id, e.message()));
                self.response_deadline = now.saturating_add(LIFETIME_MS);
                Err(e)
            }
        }
    }
    pub fn reject(&mut self, generation: u64) -> Result<(), Error> {
        self.receipts.clear();
        let pending = self.pending.take().ok_or(Error::Stale)?;
        self.response = None;
        if generation != self.generation {
            return Err(Error::Stale);
        }
        self.response = Some(response_error(&pending.id, "Rejected on device"));
        self.response_deadline = self.last_time.saturating_add(LIFETIME_MS);
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
