// SPDX-License-Identifier: MIT
//! Public scalar-3 serial adapter. No arbitrary identity or secret endpoint.
#![cfg_attr(not(test), no_std)]
use core::{
    cell::{Cell, UnsafeCell},
    sync::atomic::{AtomicU32, Ordering},
};
use nsealr_core::{
    authorization::{
        AuthorizationSession, AuthorizationState, AuxiliaryError, AuxiliarySource,
        LocalDisplayError, LocalInput, LocalPresentation, LocalReviewIo, REVIEW_LIFETIME,
        SIGNED_EVENT_BYTES,
    },
    base64url::{decode_base64url, encode_base64url},
    event::{OperationLimits, ParsedRequest, RequestMethod},
    nip19::SecretKey,
    review::event::InspectionGeometry,
    serial::{
        frame::{decode_serial_frame, encode_serial_frame, FrameType},
        input::{SerialInputEvent, SerialLineInput},
    },
};
pub type Present =
    extern "C" fn(u32, u32, u32, *const u8, usize, *const u8, usize, *const u8, usize) -> i32;
pub type Now = extern "C" fn(*mut u64) -> i32;
pub type Cancelled = extern "C" fn() -> i32;
const FRAME: usize = 1024;
const JSON: usize = 320;
const RESPONSE: usize = 704;
const ARG: i32 = -1;
const BUSY: i32 = -2;
const REQUEST: i32 = -3;
const UNSUPPORTED: i32 = -4;
const REJECTED: i32 = -5;
const DISPLAY: i32 = -6;
const CLOCK: i32 = -7;
const AUX: i32 = -8;
const ENGINE: i32 = -9;
const CAPACITY: i32 = -10;
const CANCEL: i32 = -11;
#[repr(C)]
pub struct ExchangeResult {
    pub status: i32,
    pub length: u32,
}
struct Ingress {
    input: SerialLineInput,
    ready: [u8; FRAME],
    length: usize,
}
struct Shared(UnsafeCell<Ingress>);
// All exported accesses acquire ACTIVE; no callback is permitted to bypass it.
unsafe impl Sync for Shared {}
static INGRESS: Shared = Shared(UnsafeCell::new(Ingress {
    input: SerialLineInput::new(),
    ready: [0; FRAME],
    length: 0,
}));
static ACTIVE: AtomicU32 = AtomicU32::new(0);
struct Guard;
impl Guard {
    fn take() -> Result<Self, i32> {
        ACTIVE
            .compare_exchange(0, 1, Ordering::Acquire, Ordering::Relaxed)
            .map(|_| Self)
            .map_err(|_| BUSY)
    }
}
impl Drop for Guard {
    fn drop(&mut self) {
        ACTIVE.store(0, Ordering::Release);
    }
}
struct Owner(AuthorizationSession);
impl Drop for Owner {
    fn drop(&mut self) {
        self.0.cancel();
        let _ = self.0.lock();
    }
}
fn limits() -> OperationLimits {
    OperationLimits {
        input_bytes: JSON,
        content_bytes: 128,
        tags: 4,
        fields_per_tag: 4,
        field_bytes: 64,
        text_bytes: 160,
        canonical_bytes: 1024,
        review_pages: 128,
    }
}
fn fixture() -> SecretKey {
    let mut scalar = [0u8; 32];
    scalar[31] = 3;
    SecretKey::take_from(&mut scalar).expect("published scalar 3")
}
fn owner() -> Result<Owner, i32> {
    let mut o = Owner(
        AuthorizationSession::new(
            limits(),
            InspectionGeometry {
                columns: 26,
                lines: 8,
            },
        )
        .map_err(|_| ENGINE)?,
    );
    o.0.select_key(fixture()).map_err(|_| ENGINE)?;
    Ok(o)
}
struct Fresh {
    now: Now,
    cancelled: Cancelled,
    last: Cell<Option<u64>>,
    deadline: Cell<Option<u64>>,
    failure: Cell<i32>,
}
impl Fresh {
    fn sample(&self) -> Option<u64> {
        if self.failure.get() != 0 {
            return None;
        }
        let mut t = 0;
        let e = if (self.cancelled)() != 0 {
            CANCEL
        } else if (self.now)(&mut t) != 0
            || self.last.get().is_some_and(|p| t < p)
            || self.deadline.get().is_some_and(|d| t >= d)
        {
            CLOCK
        } else {
            0
        };
        if e != 0 {
            self.failure.set(e);
            None
        } else {
            self.last.set(Some(t));
            Some(t)
        }
    }
    fn error(&self, e: nsealr_core::authorization::AuthorizationError) -> i32 {
        use nsealr_core::authorization::AuthorizationError as E;
        if self.failure.get() != 0 {
            return self.failure.get();
        }
        match e {
            E::Clock | E::Expired => CLOCK,
            E::Display => DISPLAY,
            E::Auxiliary => AUX,
            E::Parse(_) | E::Inspection(_) => REQUEST,
            E::Output => CAPACITY,
            _ => ENGINE,
        }
    }
}
struct Ui<'a> {
    present: Present,
    fresh: &'a Fresh,
}
impl LocalReviewIo for Ui<'_> {
    fn now(&mut self) -> Option<u64> {
        self.fresh.sample()
    }
    fn present(&mut self, p: LocalPresentation<'_>) -> Result<LocalInput, LocalDisplayError> {
        let (kind, f) = match p {
            LocalPresentation::Data(f) => (0, f),
            LocalPresentation::Decision(f) => (1, f),
        };
        let action = (self.present)(
            kind,
            f.index() as u32,
            f.total() as u32,
            f.label().as_ptr(),
            f.label().len(),
            f.body().as_ptr(),
            f.body().len(),
            f.position().as_ptr(),
            f.position().len(),
        );
        match action {
            0 => Ok(LocalInput::None),
            1 => Ok(LocalInput::Next),
            2 => Ok(LocalInput::Back),
            3 => Ok(LocalInput::Approve),
            4 => Ok(LocalInput::Reject),
            _ => Err(LocalDisplayError),
        }
    }
}
/// Deterministic only with already-public scalar 3. Not a production RNG.
#[cfg(test)]
struct PublicAux;
#[cfg(test)]
impl AuxiliarySource for PublicAux {
    fn fill(&mut self, d: &mut [u8; 32]) -> Result<usize, AuxiliaryError> {
        d.fill(0x42);
        Ok(32)
    }
}
/// Private synchronous app callback, never supplied by USB or a host request.
pub type Auxiliary = unsafe extern "C" fn(*mut u8, usize, *mut usize) -> i32;
struct CallbackAux(Auxiliary);
impl AuxiliarySource for CallbackAux {
    fn fill(&mut self, destination: &mut [u8; 32]) -> Result<usize, AuxiliaryError> {
        let mut supplied = 0usize;
        let status = unsafe { (self.0)(destination.as_mut_ptr(), 32, &mut supplied) };
        if status == 0 && supplied == 32 {
            return Ok(32);
        }
        for byte in destination.iter_mut() {
            unsafe { core::ptr::write_volatile(byte, 0) };
        }
        core::sync::atomic::compiler_fence(Ordering::SeqCst);
        Err(match status {
            -2 | -3 | -4 => AuxiliaryError::Unavailable,
            -6 => AuxiliaryError::Health,
            -7 => AuxiliaryError::Interrupted,
            _ => AuxiliaryError::Provider,
        })
    }
}
fn append(out: &mut [u8], at: &mut usize, b: &[u8]) -> Result<(), i32> {
    let end = at.checked_add(b.len()).ok_or(CAPACITY)?;
    out.get_mut(*at..end).ok_or(CAPACITY)?.copy_from_slice(b);
    *at = end;
    Ok(())
}
fn frame_json(kind: FrameType, json: &[u8], out: &mut [u8]) -> Result<usize, i32> {
    let mut b64 = [0u8; 960];
    let b = encode_base64url(json, &mut b64).map_err(|_| CAPACITY)?;
    encode_serial_frame(kind, b, out)
        .map(|b| b.len())
        .map_err(|_| CAPACITY)
}
fn exchange(
    frame: &[u8],
    present: Present,
    now: Now,
    cancelled: Cancelled,
    out: &mut [u8],
    aux: &mut dyn AuxiliarySource,
) -> Result<usize, i32> {
    // Own all bytes before invoking any external callback.
    let mut original = [0u8; FRAME];
    original
        .get_mut(..frame.len())
        .ok_or(REQUEST)?
        .copy_from_slice(frame);
    let f = decode_serial_frame(&original[..frame.len()]).map_err(|_| REQUEST)?;
    if f.frame_type != FrameType::Request {
        return Err(REQUEST);
    }
    let mut raw = [0u8; JSON];
    let decoded = decode_base64url(f.payload_base64url, &mut raw).map_err(|_| REQUEST)?;
    let request = ParsedRequest::parse(decoded, limits()).map_err(|_| REQUEST)?;
    if request.method() == RequestMethod::Capabilities {
        return Err(UNSUPPORTED);
    }
    let fresh = Fresh {
        now,
        cancelled,
        last: Cell::new(None),
        deadline: Cell::new(None),
        failure: Cell::new(0),
    };
    let intake = fresh.sample().ok_or_else(|| fresh.failure.get())?;
    fresh
        .deadline
        .set(Some(intake.checked_add(REVIEW_LIFETIME).ok_or(CLOCK)?));
    let mut o = owner()?;
    let mut event = [0u8; SIGNED_EVENT_BYTES];
    let mut public = [0u8; 64];
    let is_key = request.method() == RequestMethod::PublicKey;
    let result: &[u8] = if is_key {
        for (pair, b) in public
            .chunks_exact_mut(2)
            .zip(o.0.public_key().ok_or(ENGINE)?)
        {
            pair[0] = b"0123456789abcdef"[(b >> 4) as usize];
            pair[1] = b"0123456789abcdef"[(b & 15) as usize];
        }
        &public
    } else {
        o.0.begin_request(decoded, Some(intake))
            .map_err(|e| fresh.error(e))?;
        let mut ui = Ui {
            present,
            fresh: &fresh,
        };
        for _ in 0..1024 {
            if o.0.state() != AuthorizationState::Reviewing {
                break;
            }
            o.0.review_step(&mut ui).map_err(|e| fresh.error(e))?;
        }
        match o.0.state() {
            AuthorizationState::Approved => (),
            AuthorizationState::Spent => return Err(REJECTED),
            _ => return Err(ENGINE),
        }
        let n =
            o.0.sign_approved(
                request.request_id(),
                &mut || fresh.sample(),
                aux,
                &mut event,
            )
            .map_err(|e| fresh.error(e))?;
        &event[..n]
    };
    let mut json = [0u8; RESPONSE];
    let mut at = 0;
    for b in [
        b"{\"version\":2,\"request_id\":\"".as_slice(),
        request.request_id().as_bytes(),
        b"\",\"ok\":true,\"result\":{",
        if is_key {
            b"\"public_key\":\""
        } else {
            b"\"event\":"
        },
        result,
        if is_key { b"\"}}" } else { b"}}" },
    ] {
        append(&mut json, &mut at, b)?;
    }
    let mut staged = [0u8; FRAME];
    let n = frame_json(FrameType::Response, &json[..at], &mut staged)?;
    fresh.sample().ok_or_else(|| fresh.failure.get())?;
    out.get_mut(..n)
        .ok_or(CAPACITY)?
        .copy_from_slice(&staged[..n]);
    Ok(n)
}
fn error_frame(e: i32, out: &mut [u8]) -> usize {
    let msg: &[u8] = match e {
        UNSUPPORTED => b"{\"error\":\"unqualified_public_test\"}",
        REJECTED => b"{\"error\":\"rejected\"}",
        CLOCK => b"{\"error\":\"expired_or_clock\"}",
        DISPLAY => b"{\"error\":\"display_failed\"}",
        AUX => b"{\"error\":\"auxiliary_unavailable\"}",
        CANCEL => b"{\"error\":\"cancelled\"}",
        _ => b"{\"error\":\"invalid_request\"}",
    };
    frame_json(FrameType::Error, msg, out).unwrap_or(0)
}
/// One byte, one fixed-capacity accumulator. 1 means complete, 2 means drained overflow.
#[no_mangle]
pub extern "C" fn nsealr_s3_public_feed(byte: u8) -> i32 {
    let Ok(_guard) = Guard::take() else {
        return BUSY;
    };
    // SAFETY: exclusive guard, no callbacks or retained references.
    let s = unsafe { &mut *INGRESS.0.get() };
    if s.length != 0 {
        return BUSY;
    }
    match s.input.push_byte(byte, FRAME) {
        Ok(SerialInputEvent::None) => 0,
        Ok(SerialInputEvent::OverlongFrame) => 2,
        Ok(SerialInputEvent::FrameReady(b)) => {
            s.ready[..b.len()].copy_from_slice(b);
            s.length = b.len();
            1
        }
        Err(_) => REQUEST,
    }
}
#[no_mangle]
pub extern "C" fn nsealr_s3_public_reset_input() -> i32 {
    let Ok(_g) = Guard::take() else {
        return BUSY;
    };
    let s = unsafe { &mut *INGRESS.0.get() };
    s.input = SerialLineInput::new();
    s.ready.fill(0);
    s.length = 0;
    0
}
/// Trusted-image ABI: output is uniquely writable and callbacks are synchronous.
/// Invalid pointer/capacity/absent callback rejects without touching output.
#[no_mangle]
pub unsafe extern "C" fn nsealr_s3_public_exchange(
    output: *mut u8,
    capacity: usize,
    present: Option<Present>,
    now: Option<Now>,
    cancelled: Option<Cancelled>,
    auxiliary: Option<Auxiliary>,
) -> ExchangeResult {
    let bad = |status| ExchangeResult { status, length: 0 };
    if output.is_null() || capacity != FRAME {
        return bad(ARG);
    }
    let (Some(p), Some(n), Some(c), Some(a)) = (present, now, cancelled, auxiliary) else {
        return bad(ARG);
    };
    let Ok(_g) = Guard::take() else {
        return bad(BUSY);
    };
    let out = unsafe { core::slice::from_raw_parts_mut(output, capacity) };
    out.fill(0);
    let s = unsafe { &mut *INGRESS.0.get() };
    let result = exchange(&s.ready[..s.length], p, n, c, out, &mut CallbackAux(a));
    s.ready.fill(0);
    s.length = 0;
    match result {
        Ok(length) => ExchangeResult {
            status: 0,
            length: length as u32,
        },
        Err(status) => {
            out.fill(0);
            ExchangeResult {
                status,
                length: error_frame(status, out) as u32,
            }
        }
    }
}
#[no_mangle]
pub unsafe extern "C" fn nsealr_s3_public_key(output: *mut u8, capacity: usize) -> i32 {
    if output.is_null() || capacity != 32 {
        return ARG;
    }
    let Ok(_g) = Guard::take() else {
        return BUSY;
    };
    let o = match owner() {
        Ok(o) => o,
        Err(e) => return e,
    };
    let Some(key) = o.0.public_key() else {
        return ENGINE;
    };
    unsafe { core::slice::from_raw_parts_mut(output, 32) }.copy_from_slice(&key);
    0
}
#[cfg(not(test))]
#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
#[cfg(test)]
mod tests;
