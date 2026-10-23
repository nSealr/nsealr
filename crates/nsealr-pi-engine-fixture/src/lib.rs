//! Synchronous request-aware host engineering ABI, using only public test-key-1.
//! Trusted callers/presenters/providers are in the same process TCB. No device,
//! production custody, callback preemption or hostile-pointer isolation claim.
#[cfg(panic = "abort")]
compile_error!("the host fixture ABI requires unwind, not abort-only compilation");

use nsealr_core::{
    authorization::{
        AuthorizationError, AuthorizationSession, AuthorizationState, AuxiliaryError,
        AuxiliarySource, LocalDisplayError, LocalInput, LocalPresentation, LocalReviewIo,
        REVIEW_LIFETIME, SIGNED_EVENT_BYTES,
    },
    event::{OperationLimits, ParsedRequest, RequestMethod},
    nip19::SecretKey,
    qr::envelope::{decode_qr_envelope, encode_qr_envelope_json},
    review::event::{InspectionError, InspectionGeometry},
};
use std::{
    cell::Cell,
    panic::{catch_unwind, AssertUnwindSafe},
    sync::atomic::{AtomicBool, Ordering},
};

pub type Present =
    extern "C" fn(u32, u32, u32, *const u8, usize, *const u8, usize, *const u8, usize) -> i32;
pub type Now = extern "C" fn(*mut u64) -> i32;
pub type Aux = extern "C" fn(*mut u8, usize) -> i32;
pub type Cancelled = extern "C" fn() -> i32;
const FRAME: usize = 947;
const JSON: usize = 704;
const ARGUMENT: i32 = -1;
const BUSY: i32 = -2;
const REQUEST: i32 = -3;
const UNSUPPORTED: i32 = -4;
const REJECTED: i32 = -5;
const DISPLAY: i32 = -6;
const CLOCK: i32 = -7;
const AUXILIARY: i32 = -8;
const ENGINE: i32 = -9;
const CAPACITY: i32 = -10;
const CANCELLED: i32 = -11;
const PANIC: i32 = -12;
static ACTIVE: AtomicBool = AtomicBool::new(false);

struct Active;
impl Active {
    fn acquire() -> Result<Self, i32> {
        ACTIVE
            .compare_exchange(false, true, Ordering::Acquire, Ordering::Relaxed)
            .map(|_| Self)
            .map_err(|_| BUSY)
    }
}
impl Drop for Active {
    fn drop(&mut self) {
        ACTIVE.store(false, Ordering::Release);
    }
}
struct Owner(AuthorizationSession);
impl Drop for Owner {
    fn drop(&mut self) {
        self.0.cancel();
        // Fresh owner per call cannot exhaust its session generation.
        let _ = self.0.lock();
    }
}

fn limits() -> OperationLimits {
    OperationLimits {
        input_bytes: JSON,
        content_bytes: 512,
        tags: 16,
        fields_per_tag: 8,
        field_bytes: 64,
        ..OperationLimits::conformance()
    }
}

struct Freshness {
    now: Now,
    cancelled: Cancelled,
    last: Cell<Option<u64>>,
    deadline: Cell<Option<u64>>,
    failure: Cell<i32>,
}
impl Freshness {
    fn sample(&self) -> Option<u64> {
        if self.failure.get() != 0 {
            return None;
        }
        let mut tick = 0;
        let failure = match (self.cancelled)() {
            0 => {
                if (self.now)(&mut tick) != 0
                    || self.last.get().is_some_and(|last| tick < last)
                    || self.deadline.get().is_some_and(|deadline| tick >= deadline)
                {
                    CLOCK
                } else {
                    0
                }
            }
            1 => CANCELLED,
            _ => CANCELLED,
        };
        self.failure.set(failure);
        if failure != 0 {
            return None;
        }
        self.last.set(Some(tick));
        Some(tick)
    }
    fn error(&self, error: AuthorizationError) -> i32 {
        if self.failure.get() != 0 {
            return self.failure.get();
        }
        match error {
            AuthorizationError::Clock | AuthorizationError::Expired => CLOCK,
            AuthorizationError::Auxiliary => AUXILIARY,
            AuthorizationError::Display => DISPLAY,
            AuthorizationError::Parse(_) => REQUEST,
            AuthorizationError::Inspection(InspectionError::Unsupported) => UNSUPPORTED,
            AuthorizationError::Output => CAPACITY,
            _ => ENGINE,
        }
    }
}
struct Ui<'a> {
    present: Present,
    fresh: &'a Freshness,
}
impl LocalReviewIo for Ui<'_> {
    fn now(&mut self) -> Option<u64> {
        self.fresh.sample()
    }
    fn present(
        &mut self,
        presentation: LocalPresentation<'_>,
    ) -> Result<LocalInput, LocalDisplayError> {
        let (kind, page) = match presentation {
            LocalPresentation::Data(page) => (0, page),
            LocalPresentation::Decision(page) => (1, page),
        };
        match (self.present)(
            kind,
            page.index() as u32,
            page.total() as u32,
            page.label().as_ptr(),
            page.label().len(),
            page.body().as_ptr(),
            page.body().len(),
            page.position().as_ptr(),
            page.position().len(),
        ) {
            0 => Ok(LocalInput::Next),
            1 => Ok(LocalInput::Approve),
            2 => Ok(LocalInput::Reject),
            3 => Ok(LocalInput::Back),
            4 => Ok(LocalInput::None),
            _ => Err(LocalDisplayError),
        }
    }
}
struct Auxiliary(Aux);
impl AuxiliarySource for Auxiliary {
    fn fill(&mut self, destination: &mut [u8; 32]) -> Result<usize, AuxiliaryError> {
        usize::try_from((self.0)(destination.as_mut_ptr(), destination.len()))
            .map_err(|_| AuxiliaryError::Provider)
    }
}

fn append(out: &mut [u8], length: &mut usize, bytes: &[u8]) -> Result<(), i32> {
    let end = length.checked_add(bytes.len()).ok_or(CAPACITY)?;
    out.get_mut(*length..end)
        .ok_or(CAPACITY)?
        .copy_from_slice(bytes);
    *length = end;
    Ok(())
}

fn run(
    input: &[u8],
    present: Present,
    now: Now,
    aux: Aux,
    cancelled: Cancelled,
    output: &mut [u8],
) -> Result<usize, i32> {
    // Copy all original bytes before the first external callback.
    let mut frame = [0u8; FRAME];
    frame[..input.len()].copy_from_slice(input);
    let mut raw = [0u8; JSON];
    let decoded = decode_qr_envelope(&frame[..input.len()], &mut raw).map_err(|_| REQUEST)?;
    let request = ParsedRequest::parse(decoded.payload_json, limits()).map_err(|_| REQUEST)?;
    if request.method() == RequestMethod::Capabilities {
        return Err(UNSUPPORTED);
    }
    let fresh = Freshness {
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
    let mut scalar = [0x11; 32]; // Already published test-key-1. No secret crosses FFI.
    let key = SecretKey::take_from(&mut scalar).expect("fixed nonzero public test scalar");
    let mut owner = Owner(
        AuthorizationSession::new(
            limits(),
            InspectionGeometry {
                columns: 32,
                lines: 8,
            },
        )
        .expect("fixed validated conformance subset"),
    );
    owner
        .0
        .select_key(key)
        .expect("fixed valid public fixture key");
    let mut event = [0u8; SIGNED_EVENT_BYTES];
    let mut public = [0u8; 64];
    let result: &[u8] = match request.method() {
        RequestMethod::PublicKey => {
            for (pair, byte) in public
                .chunks_exact_mut(2)
                .zip(owner.0.public_key().expect("selected key"))
            {
                pair[0] = b"0123456789abcdef"[(byte >> 4) as usize];
                pair[1] = b"0123456789abcdef"[(byte & 15) as usize];
            }
            &public
        }
        // Capabilities was refused before any external callback.
        _ => {
            owner
                .0
                .begin_request(decoded.payload_json, Some(intake))
                .map_err(|e| fresh.error(e))?;
            let mut ui = Ui {
                present,
                fresh: &fresh,
            };
            for _ in 0..1024 {
                if owner.0.state() != AuthorizationState::Reviewing {
                    break;
                }
                owner.0.review_step(&mut ui).map_err(|e| fresh.error(e))?;
            }
            match owner.0.state() {
                AuthorizationState::Spent => return Err(REJECTED),
                AuthorizationState::Approved => (),
                _ => return Err(ENGINE),
            }
            // Core consumes approval BEFORE invoking fresh.sample/cancel/provider.
            let length = owner
                .0
                .sign_approved(
                    request.request_id(),
                    &mut || fresh.sample(),
                    &mut Auxiliary(aux),
                    &mut event,
                )
                .map_err(|e| fresh.error(e))?;
            &event[..length]
        }
    };
    let mut json = [0u8; JSON];
    let mut length = 0;
    let is_key = request.method() == RequestMethod::PublicKey;
    for part in [
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
        append(&mut json, &mut length, part)?;
    }
    let mut staged = [0u8; FRAME];
    let encoded = encode_qr_envelope_json(&json[..length], &mut staged).map_err(|_| CAPACITY)?;
    if encoded.len() > output.len() {
        return Err(CAPACITY);
    }
    // Last logical admission sample after all private serialization/staging.
    // It is not a hard-real-time return bound or an interruptible callback.
    fresh.sample().ok_or_else(|| fresh.failure.get())?;
    output[..encoded.len()].copy_from_slice(encoded);
    Ok(encoded.len())
}

fn range(start: usize, length: usize) -> Option<(usize, usize)> {
    if start == 0 || length == 0 || length > isize::MAX as usize {
        return None;
    }
    Some((start, start.checked_add(length)?))
}
fn disjoint(a: (usize, usize), b: (usize, usize)) -> bool {
    a.1 <= b.0 || b.1 <= a.0
}

fn settled(
    output: &mut [u8],
    operation: impl FnOnce(&mut [u8]) -> Result<usize, i32>,
) -> Result<usize, i32> {
    let result = catch_unwind(AssertUnwindSafe(|| operation(output))).unwrap_or(Err(PANIC));
    if result.is_err() {
        output.fill(0);
    }
    result
}

/// Run the actual request using only the already-public fixture11x32 identity.
///
/// # Safety
/// Input/output/written must be live, aligned as required, nonoverlapping and
/// unaliased for this synchronous call. Address checks do not prove validity.
/// Callbacks must remain alive, never unwind across C, never retain spans, and
/// cease all writes before return. The entire Python/native process is trusted.
/// ARGUMENT/BUSY touch no pointers. Admitted failure zeroes whole output/written.
#[no_mangle]
pub unsafe extern "C" fn qp01_fixture_request_v1(
    input: *const u8,
    input_bytes: usize,
    present: Option<Present>,
    now: Option<Now>,
    aux: Option<Aux>,
    cancelled: Option<Cancelled>,
    output: *mut u8,
    capacity: usize,
    written: *mut usize,
) -> i32 {
    let _active = match Active::acquire() {
        Ok(active) => active,
        Err(status) => return status,
    };
    let (Some(i), Some(o), Some(w), Some(present), Some(now), Some(aux), Some(cancelled)) = (
        range(input as usize, input_bytes),
        range(output as usize, capacity),
        range(written as usize, size_of::<usize>()),
        present,
        now,
        aux,
        cancelled,
    ) else {
        return ARGUMENT;
    };
    if input_bytes > FRAME
        || capacity > FRAME
        || !written.is_aligned()
        || !disjoint(i, o)
        || !disjoint(i, w)
        || !disjoint(o, w)
    {
        return ARGUMENT;
    }
    // SAFETY: caller live/aligned/unaliased contract plus validated sizes/ranges.
    let output = unsafe { std::slice::from_raw_parts_mut(output, capacity) };
    let input = unsafe { std::slice::from_raw_parts(input, input_bytes) };
    output.fill(0);
    unsafe {
        *written = 0;
    }
    match settled(output, |output| {
        run(input, present, now, aux, cancelled, output)
    }) {
        Ok(length) => {
            unsafe {
                *written = length;
            }
            0
        }
        Err(status) => status,
    }
}

#[cfg(test)]
mod tests;
