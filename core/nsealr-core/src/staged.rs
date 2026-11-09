//! One request scanned before loading a key. It carries bytes, never approval.
use crate::{event::Event, json as strict, owner::LIFETIME_MS, qr::Collector, Error};
use alloc::vec::Vec;
use zeroize::Zeroizing;

#[derive(Default)]
pub struct Staged {
    pub collector: Collector,
    message: Option<Zeroizing<Vec<u8>>>,
    deadline: Option<u64>,
    last_time: u64,
}
impl Staged {
    pub fn clear(&mut self) {
        self.collector.clear();
        self.message = None;
        self.deadline = None;
    }
    pub fn active(&self) -> bool {
        self.deadline.is_some()
    }
    pub fn ready(&self) -> bool {
        self.message.is_some()
    }
    fn clock(&mut self, now: u64) -> Result<(), Error> {
        if now < self.last_time {
            self.clear();
            return Err(Error::Stale);
        }
        self.last_time = now;
        Ok(())
    }
    pub fn tick(&mut self, now: u64) -> Result<bool, Error> {
        self.clock(now)?;
        let expired = self.deadline.is_some_and(|deadline| now >= deadline);
        if expired {
            self.clear();
        }
        Ok(expired)
    }
    pub fn receive(&mut self, frame: &[u8], now: u64) -> Result<bool, Error> {
        let result = (|| {
            if self.tick(now)? || self.message.is_some() {
                return Err(Error::Stale);
            }
            if self.deadline.is_none() {
                self.deadline = Some(now.checked_add(LIFETIME_MS).ok_or(Error::Stale)?);
            }
            match self.collector.accept(frame)? {
                Some(message) => {
                    validate(&message)?;
                    self.message = Some(message);
                    Ok(true)
                }
                None => Ok(false),
            }
        })();
        if result.is_err() {
            self.clear();
        }
        result
    }
    pub fn take(&mut self, now: u64) -> Result<(Zeroizing<Vec<u8>>, u64), Error> {
        let result = (|| {
            if self.tick(now)? {
                return Err(Error::Stale);
            }
            let deadline = self.deadline.ok_or(Error::Stale)?;
            let message = self.message.take().ok_or(Error::Stale)?;
            Ok((message, deadline))
        })();
        self.clear();
        result
    }
}

fn validate(input: &[u8]) -> Result<(), Error> {
    let request = strict::parse(input)?;
    strict::exact_keys(&request, &["id", "method", "params"], &[])?;
    let id = strict::string(&request["id"])?;
    if id.is_empty() || id.len() > 128 {
        return Err(Error::Input);
    }
    let method = strict::string(&request["method"])?;
    let params = request["params"].as_array().ok_or(Error::Input)?;
    match method {
        "get_public_key" if params.is_empty() => Ok(()),
        "sign_event" if params.len() == 1 => {
            // Validate structure now. Its claimed author is untrusted; resume
            // binds that same immutable event to the actual selected identity.
            let event = strict::parse(strict::string(&params[0])?.as_bytes())?;
            let public = strict::hex(strict::string(&event["pubkey"])?)?;
            Event::from_value(event, &public)?;
            Ok(())
        }
        "nip44_encrypt" | "nip44_decrypt" if params.len() == 2 => {
            let _: [u8; 32] = strict::hex(strict::string(&params[0])?)?;
            strict::string(&params[1])?;
            Ok(())
        }
        _ => Err(Error::Unsupported),
    }
}
