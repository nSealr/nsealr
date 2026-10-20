//! Host-only fixed-public-identity ABI experiment, never a product/device API.
//! No caller-selected key, request, provider, clock or transport is accepted.
use nsealr_core::{
    authorization::{
        AuthorizationError, AuthorizationSession, AuthorizationState, AuxiliaryError,
        AuxiliarySource, LocalDisplayError, LocalInput, LocalPresentation, LocalReviewIo,
        SIGNED_EVENT_BYTES,
    },
    event::OperationLimits,
    nip19::SecretKey,
    review::event::InspectionGeometry,
};
use std::{
    panic::{catch_unwind, AssertUnwindSafe},
    sync::atomic::{AtomicBool, Ordering},
};

// The callback borrows PUBLIC frame bytes only until it returns. No Rust
// reference/enum/layout, secret, owner pointer or detached consent crosses ABI.
type Present =
    extern "C" fn(u32, u32, u32, *const u8, usize, *const u8, usize, *const u8, usize) -> i32;
const REQUEST: &[u8] = include_bytes!("../../request.json");
const ARGUMENT: i32 = -1;
const BUSY: i32 = -2;
const REJECTED: i32 = -3;
const REVIEW: i32 = -4;
const DISPLAY: i32 = -5;
const PANIC: i32 = -6;
const ENGINE: i32 = -7;
static ACTIVE: AtomicBool = AtomicBool::new(false);

struct Active;
impl Drop for Active {
    fn drop(&mut self) {
        ACTIVE.store(false, Ordering::Release);
    }
}
struct PublicFixture {
    calls: u32,
}
impl AuxiliarySource for PublicFixture {
    fn fill(&mut self, destination: &mut [u8; 32]) -> Result<usize, AuxiliaryError> {
        self.calls += 1;
        destination.fill(0);
        Ok(32)
    }
}
struct PythonUi(Present);
impl LocalReviewIo for PythonUi {
    fn now(&mut self) -> Option<u64> {
        // Public host fixture clock only; not target monotonic-time evidence.
        Some(0)
    }
    fn present(
        &mut self,
        presentation: LocalPresentation<'_>,
    ) -> Result<LocalInput, LocalDisplayError> {
        let (kind, frame) = match presentation {
            LocalPresentation::Data(frame) => (0, frame),
            LocalPresentation::Decision(frame) => (1, frame),
        };
        let action = (self.0)(
            kind,
            frame.index() as u32,
            frame.total() as u32,
            frame.label().as_ptr(),
            frame.label().len(),
            frame.body().as_ptr(),
            frame.body().len(),
            frame.position().as_ptr(),
            frame.position().len(),
        );
        match action {
            0 => Ok(LocalInput::Next),
            1 => Ok(LocalInput::Approve),
            2 => Ok(LocalInput::Reject),
            3 => Ok(LocalInput::Back),
            _ => Err(LocalDisplayError),
        }
    }
}

fn run(present: Present, output: &mut [u8]) -> Result<usize, i32> {
    let mut scalar = [0; 32];
    scalar[31] = 3; // Existing public K01/BIP340 fixture, never a user key API.
    let secret = SecretKey::take_from(&mut scalar).map_err(|_| ENGINE)?;
    if scalar != [0; 32] {
        return Err(ENGINE);
    }
    let mut owner = AuthorizationSession::new(
        OperationLimits::conformance(),
        InspectionGeometry {
            columns: 32,
            lines: 8,
        },
    )
    .map_err(|_| ENGINE)?;
    owner.select_key(secret).map_err(|_| ENGINE)?;
    let result = (|| {
        owner.begin_request(REQUEST, Some(0)).map_err(|_| ENGINE)?;
        let mut ui = PythonUi(present);
        // Finite host canary loop; a native/Python callback can still block.
        for _ in 0..1024 {
            if owner.state() != AuthorizationState::Reviewing {
                break;
            }
            owner.review_step(&mut ui).map_err(|e| {
                if e == AuthorizationError::Display {
                    DISPLAY
                } else {
                    REVIEW
                }
            })?;
        }
        let mut auxiliary = PublicFixture { calls: 0 };
        if owner.state() == AuthorizationState::Spent {
            // Actual engine refusal AFTER Python's local rejection, not a
            // wrapper-only status. No provider invocation or public output.
            let refused = owner.sign_approved(
                "qp01-public-fixture",
                &mut || Some(0),
                &mut auxiliary,
                output,
            );
            return if refused == Err(AuthorizationError::InvalidState)
                && auxiliary.calls == 0
                && output.iter().all(|b| *b == 0)
            {
                Err(REJECTED)
            } else {
                Err(ENGINE)
            };
        }
        if owner.state() != AuthorizationState::Approved {
            return Err(REVIEW);
        }
        let written = owner
            .sign_approved(
                "qp01-public-fixture",
                &mut || Some(0),
                &mut auxiliary,
                output,
            )
            .map_err(|_| ENGINE)?;
        if auxiliary.calls != 1 {
            return Err(ENGINE);
        }
        // sign_approved includes actual raw-ID/identity verification and fresh
        // completion before releasing this complete public serialized event.
        Ok(written)
    })();
    owner.cancel();
    owner.lock().map_err(|_| ENGINE)?;
    result
}

/// Run ONLY the fixed public fixture in one synchronous Rust-owned lifetime.
///
/// # Safety
/// `output` must designate exactly `capacity` writable, live bytes, distinct
/// from aligned writable `written`; both remain valid and unaliased for this
/// call. Capacity must equal SIGNED_EVENT_BYTES. `present` must remain alive,
/// must not unwind, and must not retain borrowed frame pointers after return.
/// Pointer validity cannot be established by ctypes or this ABI's null checks.
#[no_mangle]
pub unsafe extern "C" fn qp01_public_fixture_run(
    present: Option<Present>,
    output: *mut u8,
    capacity: usize,
    written: *mut usize,
) -> i32 {
    if output.is_null()
        || written.is_null()
        || !written.is_aligned()
        || capacity != SIGNED_EVENT_BYTES
    {
        return ARGUMENT;
    }
    // SAFETY: caller's explicit FFI allocation/lifetime/non-alias contract.
    let output = unsafe { std::slice::from_raw_parts_mut(output, capacity) };
    output.fill(0);
    unsafe {
        *written = 0;
    }
    let Some(present) = present else {
        return ARGUMENT;
    };
    if ACTIVE
        .compare_exchange(false, true, Ordering::Acquire, Ordering::Relaxed)
        .is_err()
    {
        return BUSY;
    }
    let _active = Active;
    match catch_unwind(AssertUnwindSafe(|| run(present, output))) {
        Ok(Ok(length)) => {
            unsafe {
                *written = length;
            }
            0
        }
        Ok(Err(status)) => {
            output.fill(0);
            status
        }
        Err(_) => {
            output.fill(0);
            PANIC
        }
    }
}
