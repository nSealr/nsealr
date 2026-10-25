//! Single trusted-image adapter; no host approval or production secret input.
#![no_std]

use core::{cell::UnsafeCell, mem::MaybeUninit, slice, sync::atomic::{AtomicBool, Ordering}};
use nsealr_core::{
    authorization::{AuthorizationSession, AuthorizationState, AuxiliaryError, AuxiliarySource,
        LocalDisplayError, LocalInput, LocalPresentation, LocalReviewIo, REVIEW_LIFETIME},
    event::{OperationLimits, ParsedRequest, RequestMethod}, nip19::SecretKey,
    qr::envelope::{decode_qr_envelope, encode_qr_envelope_json},
    review::event::InspectionGeometry,
};

const REQUEST: usize = 704;
const FRAME: usize = 947;
const RESPONSE: usize = 1536;
const LIMITS: OperationLimits = OperationLimits { input_bytes: REQUEST, content_bytes: 128,
    tags: 4, fields_per_tag: 4, field_bytes: 64, text_bytes: 384,
    canonical_bytes: 2048, review_pages: 64 };

unsafe extern "C" {
    fn p4_monotonic_ms() -> i64;
    fn p4_memory_internal(pointer: *const u8, length: usize) -> i32;
    fn p4_fatal() -> !;
    fn p4_fixture_auxiliary(destination: *mut u8, capacity: usize) -> isize;
    fn p4_present(decision: u32, label: *const u8, label_len: usize,
        body: *const u8, body_len: usize, position: *const u8, position_len: usize,
        index: usize, total: usize, deadline_ms: u64) -> i32;
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! { unsafe { p4_fatal() } }

struct Engine { owner: AuthorizationSession, last_id: [u8; 32], last_len: usize, response_deadline: u64 }
struct Storage(UnsafeCell<MaybeUninit<Engine>>);
// Only the single worker enters; an atomic guard also rejects re-entry.
unsafe impl Sync for Storage {}
#[link_section = ".dram1.nsealr"]
static STORAGE: Storage = Storage(UnsafeCell::new(MaybeUninit::uninit()));
static ENTERED: AtomicBool = AtomicBool::new(false);
static READY: AtomicBool = AtomicBool::new(false);
struct Entry;
impl Drop for Entry { fn drop(&mut self) { ENTERED.store(false, Ordering::Release); } }
fn enter() -> Result<Entry, i32> {
    ENTERED.compare_exchange(false, true, Ordering::Acquire, Ordering::Relaxed)
        .map(|_| Entry).map_err(|_| -2)
}
fn now() -> Option<u64> { u64::try_from(unsafe { p4_monotonic_ms() }).ok().map(|n| n / 1000) }

struct Ui { deadline: u64 }
impl LocalReviewIo for Ui {
    fn now(&mut self) -> Option<u64> { now() }
    fn present(&mut self, presentation: LocalPresentation<'_>) -> Result<LocalInput, LocalDisplayError> {
        let (decision, frame) = match presentation {
            LocalPresentation::Data(f) => (0, f), LocalPresentation::Decision(f) => (1, f),
        };
        let action = unsafe { p4_present(decision, frame.label().as_ptr(), frame.label().len(),
            frame.body().as_ptr(), frame.body().len(), frame.position().as_ptr(), frame.position().len(),
            frame.index(), frame.total(), self.deadline.saturating_mul(1000)) };
        match action { 0 => Ok(LocalInput::None), 1 => Ok(LocalInput::Next),
            2 => Ok(LocalInput::Back), 3 if decision == 1 => Ok(LocalInput::Approve),
            4 => Ok(LocalInput::Reject), _ => Err(LocalDisplayError) }
    }
}
// Deliberately deterministic public-fixture source, NOT a native identity/entropy provider.
struct PublicFixtureAuxiliary;
impl AuxiliarySource for PublicFixtureAuxiliary {
    fn fill(&mut self, out: &mut [u8; 32]) -> Result<usize, AuxiliaryError> {
        let count = unsafe { p4_fixture_auxiliary(out.as_mut_ptr(), out.len()) };
        if count != 32 { return Err(AuxiliaryError::Provider); }
        Ok(32)
    }
}

#[no_mangle]
pub extern "C" fn p4_engine_init() -> i32 {
    let Ok(_guard) = enter() else { return -2 };
    if READY.load(Ordering::Acquire) { return -2; }
    let location = STORAGE.0.get().cast::<u8>();
    if unsafe { p4_memory_internal(location, core::mem::size_of::<Engine>()) } != 1 { return -3; }
    let Ok(mut owner) = AuthorizationSession::new(LIMITS, InspectionGeometry {columns: 32, lines: 8}) else { return -4 };
    let mut public_fixture = [0x11; 32];
    let Ok(key) = SecretKey::take_from(&mut public_fixture) else { return -4 };
    if owner.select_key(key).is_err() { return -4; }
    unsafe { (*STORAGE.0.get()).write(Engine {owner, last_id: [0; 32], last_len: 0, response_deadline: 0}); }
    READY.store(true, Ordering::Release); 0
}

fn append(buffer: &mut [u8], used: &mut usize, value: &[u8]) -> Result<(), i32> {
    let end = used.checked_add(value.len()).ok_or(-7)?;
    buffer.get_mut(*used..end).ok_or(-7)?.copy_from_slice(value); *used = end; Ok(())
}
fn operate(engine: &mut Engine, envelope: &[u8], output: &mut [u8]) -> Result<usize, i32> {
    let mut decoded = [0u8; REQUEST];
    let data = decode_qr_envelope(envelope, &mut decoded).map_err(|_| -5)?;
    let request = ParsedRequest::parse(data.payload_json, LIMITS).map_err(|_| -5)?;
    let id = request.request_id();
    if request.method() != RequestMethod::SignEvent || id.len() > 32 { return Err(-5); }
    if engine.last_len == id.len() && engine.last_id[..engine.last_len] == *id.as_bytes() { return Err(-6); }
    let start = now().ok_or(-8)?;
    let deadline = start.checked_add(REVIEW_LIFETIME).ok_or(-8)?;
    engine.owner.begin_request(data.payload_json, Some(start)).map_err(|_| -5)?;
    let mut ui = Ui {deadline};
    while engine.owner.state() == AuthorizationState::Reviewing {
        engine.owner.review_step(&mut ui).map_err(|_| -9)?;
    }
    if engine.owner.state() != AuthorizationState::Approved { return Err(-10); }
    let mut event = [0u8; 1024];
    let length = engine.owner.sign_approved(id, &mut now, &mut PublicFixtureAuxiliary, &mut event).map_err(|_| -11)?;
    let mut json = [0u8; 1144]; let mut used = 0;
    for part in [b"{\"version\":2,\"request_id\":\"".as_slice(), id.as_bytes(),
        b"\",\"ok\":true,\"result\":{\"event\":", &event[..length], b"}}"] {
        append(&mut json, &mut used, part)?;
    }
    let mut staged = [0u8; RESPONSE];
    let frame = encode_qr_envelope_json(&json[..used], &mut staged).map_err(|_| -7)?;
    if now().ok_or(-8)? >= deadline || frame.len() > output.len() { return Err(-8); }
    output[..frame.len()].copy_from_slice(frame);
    if now().ok_or(-8)? >= deadline { output.fill(0); return Err(-8); }
    engine.last_id[..id.len()].copy_from_slice(id.as_bytes()); engine.last_len = id.len();
    engine.response_deadline = deadline.checked_mul(1000).ok_or(-8)?;
    Ok(frame.len())
}

/// Trusted worker-only FFI. Pointer ranges must identify distinct live C buffers.
/// There is no entry point that imports a secret, marks pages seen or authorizes.
#[no_mangle]
pub unsafe extern "C" fn p4_engine_run(input: *const u8, length: usize, output: *mut u8, capacity: usize) -> i32 {
    if output.is_null() || capacity != RESPONSE { return -1; }
    let b = output as usize;
    let Some(b_end) = b.checked_add(capacity) else { return -1 };
    let out = slice::from_raw_parts_mut(output, capacity); out.fill(0);
    if input.is_null() || !(8..=FRAME).contains(&length) { return -1; }
    let a = input as usize;
    let Some(a_end) = a.checked_add(length) else { return -1 };
    if a < b_end && b < a_end { return -1; }
    let Ok(_guard) = enter() else { return -2 };
    if !READY.load(Ordering::Acquire) { return -2; }
    let engine = (*STORAGE.0.get()).assume_init_mut();
    engine.response_deadline = 0;
    let result = operate(engine, slice::from_raw_parts(input, length), out);
    engine.owner.cancel();
    match result {Ok(n) => n as i32, Err(e) => {out.fill(0); e}}
}

#[no_mangle]
pub extern "C" fn p4_engine_bytes() -> usize { core::mem::size_of::<Engine>() }

/// Public-result timing diagnostic only; it cannot create or transfer consent.
#[no_mangle]
pub extern "C" fn p4_engine_response_deadline_ms() -> u64 {
    let Ok(_guard) = enter() else { return 0 };
    if !READY.load(Ordering::Acquire) { return 0; }
    unsafe { (*STORAGE.0.get()).assume_init_ref().response_deadline }
}
