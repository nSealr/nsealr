//! Actual engine link probe. No startup/memory map/entropy/device qualification.
//! Never flash this ELF; the sole key and providers are public fixture inputs.
#![no_std]
#![no_main]
use nsealr_core::{
    authorization::{
        AuthorizationSession, AuthorizationState, AuxiliaryError, AuxiliarySource,
        LocalDisplayError, LocalInput, LocalPresentation, LocalReviewIo, SIGNED_EVENT_BYTES,
    },
    event::OperationLimits,
    hash::sha256,
    nip19::SecretKey,
    review::event::InspectionGeometry,
};
#[no_mangle]
#[used]
pub static K01_RETAINED_LAYOUT: [usize; 4] = [
    core::mem::size_of::<AuthorizationSession>(),
    core::mem::size_of::<nsealr_core::event::EventTemplate>(),
    core::mem::size_of::<nsealr_core::review::event::InspectionFrame>(),
    SIGNED_EVENT_BYTES,
];
static mut OBSERVED: [u8; 32] = [0; 32];
struct Fixture;
impl AuxiliarySource for Fixture {
    fn fill(&mut self, out: &mut [u8; 32]) -> Result<usize, AuxiliaryError> {
        out.fill(0);
        Ok(32)
    }
}
struct Missing;
impl AuxiliarySource for Missing {
    fn fill(&mut self, out: &mut [u8; 32]) -> Result<usize, AuxiliaryError> {
        out.fill(0xa5);
        Err(AuxiliaryError::Unavailable)
    }
}
struct Simulated;
impl LocalReviewIo for Simulated {
    fn now(&mut self) -> Option<u64> {
        Some(0)
    }
    fn present(&mut self, page: LocalPresentation<'_>) -> Result<LocalInput, LocalDisplayError> {
        Ok(match page {
            LocalPresentation::Data(frame) => {
                core::hint::black_box((frame.label(), frame.body(), frame.position()));
                LocalInput::Next
            }
            LocalPresentation::Decision(_) => LocalInput::Approve,
        })
    }
}
fn reviewed() -> AuthorizationSession {
    let mut scalar = core::hint::black_box([0; 32]);
    scalar[31] = 3;
    let mut owner = AuthorizationSession::new(
        OperationLimits::conformance(),
        InspectionGeometry {
            columns: 32,
            lines: 8,
        },
    )
    .unwrap();
    owner
        .select_key(SecretKey::take_from(&mut scalar).unwrap())
        .unwrap();
    let input=core::hint::black_box(br#"{"version":2,"request_id":"probe","method":"sign_event","params":{"event_template":{"created_at":0,"kind":0,"tags":[],"content":"{}"}}}"#);
    owner.begin_request(input, Some(0)).unwrap();
    let mut io = Simulated;
    while owner.state() == AuthorizationState::Reviewing {
        owner.review_step(&mut io).unwrap();
    }
    assert_eq!(owner.state(), AuthorizationState::Approved);
    owner
}
#[no_mangle]
pub extern "C" fn _start() -> ! {
    core::hint::black_box(&K01_RETAINED_LAYOUT);
    let mut output = [0xa5; SIGNED_EVENT_BYTES];
    let mut missing = reviewed();
    assert!(missing
        .sign_approved("probe", &mut || Some(0), &mut Missing, &mut output)
        .is_err());
    assert!(output.iter().all(|b| *b == 0));
    assert_eq!(missing.state(), AuthorizationState::Spent);
    let mut owner = reviewed();
    let len = owner
        .sign_approved("probe", &mut || Some(0), &mut Fixture, &mut output)
        .unwrap();
    let digest = sha256(core::hint::black_box(&output[..len]));
    // SAFETY: the single link-only entry owns the sole write to this static.
    unsafe { core::ptr::addr_of_mut!(OBSERVED).write_volatile(digest) };
    core::hint::black_box(len);
    owner.lock().unwrap();
    core::hint::black_box(owner);
    loop {
        core::hint::spin_loop();
    }
}
#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! {
    loop {
        core::hint::spin_loop();
    }
}

// A separate actual target compile must fail: there is no implicit provider API.
#[cfg(k01_missing_provider)]
fn no_provider(owner: &mut AuthorizationSession, output: &mut [u8]) {
    let _ = owner.sign_approved("probe", &mut || Some(0), output);
}
