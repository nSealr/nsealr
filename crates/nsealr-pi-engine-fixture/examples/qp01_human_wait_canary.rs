//! Opt-in Linux public-fixture timing actor. SOURCE ONLY until distinct admission.
//! One owner, one synchronous presentation, no exported approval or backend hook.
use nsealr_core::{
    authorization::{
        AuthorizationSession, AuthorizationState, AuxiliaryError, AuxiliarySource,
        LocalDisplayError, LocalInput, LocalPresentation, LocalReviewIo, SIGNED_EVENT_BYTES,
    },
    event::{OperationLimits, ParsedRequest},
    hash::sha256_hex,
    nip19::SecretKey,
    qr::envelope::{decode_qr_envelope, encode_qr_envelope_json},
    review::event::InspectionGeometry,
};
use std::{
    cell::Cell,
    io::{self, Read, Write},
    process::ExitCode,
    time::Duration,
};

#[cfg(not(all(
    target_os = "linux",
    target_arch = "x86_64",
    target_pointer_width = "64"
)))]
compile_error!("HRT canary is Linux x86_64 only; no target/ABI portability claim");

// The only new OS FFI: Linux x86_64/glibc timespec and CLOCK_MONOTONIC.
// It is internal, never exported; it must receive distinct exact-source review.
#[repr(C)]
struct Timespec {
    seconds: i64,
    nanoseconds: i64,
}
unsafe extern "C" {
    fn clock_gettime(clock: i32, value: *mut Timespec) -> i32;
}
fn mono_ns() -> Result<u64, u16> {
    let mut ts = Timespec {
        seconds: 0,
        nanoseconds: 0,
    };
    // SAFETY: live writable correctly aligned repr(C) Linux x86_64 timespec;
    // libc does not retain it. The compile-time target restriction is required.
    let status = unsafe { clock_gettime(1, &mut ts) };
    if status != 0 || ts.seconds < 0 || !(0..1_000_000_000).contains(&ts.nanoseconds) {
        return Err(2);
    }
    (ts.seconds as u64)
        .checked_mul(1_000_000_000)
        .and_then(|v| v.checked_add(ts.nanoseconds as u64))
        .ok_or(2)
}

const MAX_RECORD: usize = 1024;
const MAX_BODY: usize = MAX_RECORD - 4;
const HEADER: usize = 33;
const MAX_RECORDS: u32 = 4096;
const INIT: u8 = 1;
const PRESENT: u8 = 2;
const WAIT_ACK: u8 = 3;
const WAIT_READY: u8 = 4;
const RESUME_ACK: u8 = 5;
const CANCEL: u8 = 6;
const RESULT: u8 = 7;
const TERMINAL: u8 = 8;
const SIGN_ENTRY: u8 = 9;
const AUX_ENTRY: u8 = 10;
const RAW: &[u8] = include_bytes!(
    "../../../docs/restart/implementation/QH01/native-qr-probe/expected/request-kind-1-basic.envelope"
);
const RAW_SHA: &[u8; 64] = b"88a16190a1b1ed033fc9bebe5452af70e9a9783fd6b92305add2ac7134039ff7";

struct Record {
    opcode: u8,
    invocation: u32,
    epoch: u32,
    payload: Vec<u8>,
}
struct Wire {
    input: io::Stdin,
    output: io::Stdout,
    nonce: Option<[u8; 16]>,
    incoming: u32,
    outgoing: u32,
}
fn number32(bytes: &[u8]) -> Result<u32, u16> {
    Ok(u32::from_be_bytes(bytes.try_into().map_err(|_| 1u16)?))
}
fn number64(bytes: &[u8]) -> Result<u64, u16> {
    Ok(u64::from_be_bytes(bytes.try_into().map_err(|_| 1u16)?))
}
impl Wire {
    fn read(&mut self) -> Result<Record, u16> {
        let mut prefix = [0; 4];
        self.input.read_exact(&mut prefix).map_err(|_| 1u16)?;
        let length = number32(&prefix)? as usize;
        if !(HEADER..=MAX_BODY).contains(&length) || self.incoming >= MAX_RECORDS {
            return Err(1);
        }
        let mut body = vec![0; length];
        self.input.read_exact(&mut body).map_err(|_| 1u16)?;
        let nonce: [u8; 16] = body[9..25].try_into().map_err(|_| 1u16)?;
        if &body[..4] != b"HRT1" || number32(&body[4..8])? != self.incoming + 1 {
            return Err(1);
        }
        if self.nonce.is_some_and(|previous| previous != nonce) {
            return Err(1);
        }
        self.nonce = Some(nonce);
        self.incoming += 1;
        Ok(Record {
            opcode: body[8],
            invocation: number32(&body[25..29])?,
            epoch: number32(&body[29..33])?,
            payload: body[HEADER..].to_vec(),
        })
    }
    fn encode(
        &mut self,
        opcode: u8,
        invocation: u32,
        epoch: u32,
        payload: &[u8],
    ) -> Result<Vec<u8>, u16> {
        if payload.len() > MAX_BODY - HEADER || self.outgoing >= MAX_RECORDS {
            return Err(1);
        }
        self.outgoing += 1;
        let mut bytes = Vec::with_capacity(4 + HEADER + payload.len());
        bytes.extend_from_slice(&((HEADER + payload.len()) as u32).to_be_bytes());
        bytes.extend_from_slice(b"HRT1");
        bytes.extend_from_slice(&self.outgoing.to_be_bytes());
        bytes.push(opcode);
        bytes.extend_from_slice(&self.nonce.ok_or(1u16)?);
        bytes.extend_from_slice(&invocation.to_be_bytes());
        bytes.extend_from_slice(&epoch.to_be_bytes());
        bytes.extend_from_slice(payload);
        Ok(bytes)
    }
    fn send(&mut self, opcode: u8, invocation: u32, epoch: u32, payload: &[u8]) -> Result<(), u16> {
        let bytes = self.encode(opcode, invocation, epoch, payload)?;
        self.output.write_all(&bytes).map_err(|_| 1u16)?;
        self.output.flush().map_err(|_| 1u16)
    }
}
#[derive(Clone, Copy, PartialEq, Eq)]
enum Phase {
    Active,
    Waiting,
    Resumed,
}
fn dispatch_guard(phase: Phase) -> Result<(), u16> {
    if phase == Phase::Resumed {
        Ok(())
    } else {
        Err(3)
    }
}
#[derive(Default)]
struct Metrics {
    sign_entries: Cell<u32>,
    auxiliary_calls: Cell<u32>,
    review_calls: Cell<u16>,
    case: Cell<u16>,
}
struct Clock {
    origin: u64,
    deadline: u64,
    last: Cell<Option<u64>>,
    review_started: Cell<bool>,
    presented: Cell<bool>,
    case: u16,
}
impl Clock {
    fn sample(&self) -> Option<u64> {
        let now = mono_ns().ok()?;
        if now < self.origin || self.last.get().is_some_and(|v| now < v) || now >= self.deadline {
            return None;
        }
        self.last.set(Some(now));
        // Explicit negative clock-provider simulations, never the positive clock.
        if self.presented.get() {
            match self.case {
                18 => return None,
                19 => return Some(0),
                20 => return Some(100),
                _ => (),
            }
        }
        if self.case == 19 && self.review_started.get() {
            return Some(1);
        }
        Some((now - self.origin) / 1_000_000_000)
    }
}
struct Ui<'a> {
    wire: &'a mut Wire,
    clock: &'a Clock,
    metrics: &'a Metrics,
    case: u16,
    invocation: u32,
    serial: u32,
    phase: Phase,
    waited: bool,
}
impl Ui<'_> {
    fn present_inner(&mut self, view: LocalPresentation<'_>) -> Result<LocalInput, u16> {
        self.invocation = self.invocation.checked_add(1).ok_or(1u16)?;
        if self.invocation > 1024 {
            return Err(1);
        }
        self.metrics.review_calls.set(self.invocation as u16);
        self.phase = Phase::Active;
        let (kind, frame) = match view {
            LocalPresentation::Data(v) => (0u8, v),
            LocalPresentation::Decision(v) => (1u8, v),
        };
        let fields = [
            frame.label().as_bytes(),
            frame.body().as_bytes(),
            frame.position().as_bytes(),
        ];
        if fields[0].len() > 176
            || fields[1].len() > 264
            || fields[2].len() > 9
            || frame.total() > 1024
        {
            return Err(1);
        }
        let mut payload = vec![kind];
        payload.extend_from_slice(&(frame.index() as u16).to_be_bytes());
        payload.extend_from_slice(&(frame.total() as u16).to_be_bytes());
        for field in fields {
            payload.extend_from_slice(&(field.len() as u16).to_be_bytes());
        }
        for field in fields {
            payload.extend_from_slice(field);
        }
        self.wire
            .send(PRESENT, self.invocation, self.invocation, &payload)?;
        loop {
            let record = self.wire.read()?;
            if record.invocation != self.invocation || record.epoch != self.invocation {
                return Err(1);
            }
            if record.opcode == CANCEL && record.payload.is_empty() {
                return Err(4);
            }
            if record.opcode == WAIT_ACK {
                if self.waited || frame.index() != 0 || !record.payload.is_empty() {
                    return Err(1);
                }
                self.waited = true;
                self.phase = Phase::Waiting;
                self.wire
                    .send(WAIT_READY, self.invocation, self.invocation, &[])?;
                if self.case == 12 {
                    dispatch_guard(self.phase)?;
                }
                if self.case == 10 {
                    let start = mono_ns()?;
                    while mono_ns()?.checked_sub(start).ok_or(2u16)? < 500_000_000 {
                        std::hint::spin_loop();
                    }
                }
                continue;
            }
            if record.opcode != RESUME_ACK || record.payload.len() != 6 {
                return Err(1);
            }
            let action = record.payload[0];
            let serial = number32(&record.payload[1..5])?;
            let cycle = record.payload[5];
            if self.case == 30 && action == 4 && serial == 0 && cycle == 0 {
                self.clock.presented.set(true);
                return Ok(LocalInput::None);
            }
            if cycle != 7 || serial != self.serial.checked_add(1).ok_or(1u16)? {
                return Err(1);
            }
            self.serial = serial;
            self.phase = Phase::Resumed;
            dispatch_guard(self.phase)?;
            self.clock.presented.set(true);
            return match (kind, action) {
                (0, 0) => Ok(LocalInput::Next),
                (1, 1) => Ok(LocalInput::Approve),
                (_, 2) => Ok(LocalInput::Reject),
                _ => Err(1),
            };
        }
    }
}
impl LocalReviewIo for Ui<'_> {
    fn now(&mut self) -> Option<u64> {
        self.clock.sample()
    }
    fn present(&mut self, view: LocalPresentation<'_>) -> Result<LocalInput, LocalDisplayError> {
        self.present_inner(view).map_err(|_| LocalDisplayError)
    }
}
struct Auxiliary<'a> {
    wire: &'a mut Wire,
    metrics: &'a Metrics,
    case: u16,
}
impl AuxiliarySource for Auxiliary<'_> {
    fn fill(&mut self, output: &mut [u8; 32]) -> Result<usize, AuxiliaryError> {
        self.metrics
            .auxiliary_calls
            .set(self.metrics.auxiliary_calls.get() + 1);
        self.wire
            .send(
                AUX_ENTRY,
                0,
                0,
                &self.metrics.auxiliary_calls.get().to_be_bytes(),
            )
            .map_err(|_| AuxiliaryError::Provider)?;
        match self.case {
            13 => {
                output[..31].fill(0);
                Ok(31)
            }
            14 => Err(AuxiliaryError::Provider),
            15 => loop {
                std::thread::sleep(Duration::from_millis(25));
            },
            _ => {
                output.fill(0);
                Ok(32)
            }
        }
    }
}
struct Owner(AuthorizationSession);
impl Drop for Owner {
    fn drop(&mut self) {
        self.0.cancel();
        let _ = self.0.lock();
    }
}
enum Outcome {
    Normal,
    Silent,
}
fn run(wire: &mut Wire, metrics: &Metrics) -> Result<Outcome, u16> {
    let init = wire.read()?;
    if init.opcode != INIT || init.invocation != 0 || init.epoch != 0 || init.payload.len() != 279 {
        return Err(1);
    }
    let origin = number64(&init.payload[..8])?;
    let caller_deadline = number64(&init.payload[8..16])?;
    let case = u16::from_be_bytes(init.payload[16..18].try_into().map_err(|_| 1u16)?);
    let length = u16::from_be_bytes(init.payload[18..20].try_into().map_err(|_| 1u16)?) as usize;
    let raw = &init.payload[20..];
    if case > 32 || length != 259 || raw != RAW || &sha256_hex(raw) != RAW_SHA {
        return Err(1);
    }
    metrics.case.set(case);
    let now = mono_ns()?;
    if now < origin || now - origin >= 1_000_000_000 {
        return Err(2);
    }
    let deadline = origin
        .checked_add(100_000_000_000)
        .ok_or(2u16)?
        .min(caller_deadline);
    let clock = Clock {
        origin,
        deadline,
        last: Cell::new(None),
        review_started: Cell::new(false),
        presented: Cell::new(false),
        case,
    };
    let intake = clock.sample().ok_or(2u16)?;
    if intake != 0 {
        return Err(2);
    } // Fixed inherited catalog context, never reset time.
    if case == 25 {
        std::process::exit(3);
    }
    if case == 9 {
        wire.send(WAIT_READY, 0, 0, &[])?;
        return Err(1);
    }
    if case == 29 {
        wire.output
            .write_all(&1021u32.to_be_bytes())
            .map_err(|_| 1u16)?;
        wire.output.flush().map_err(|_| 1u16)?;
        return Ok(Outcome::Silent);
    }
    let limits = OperationLimits {
        input_bytes: 704,
        content_bytes: 512,
        tags: 16,
        fields_per_tag: 8,
        field_bytes: 64,
        ..OperationLimits::conformance()
    };
    let mut decoded = [0; 704];
    let envelope = decode_qr_envelope(raw, &mut decoded).map_err(|_| 5u16)?;
    let request = ParsedRequest::parse(envelope.payload_json, limits).map_err(|_| 5u16)?;
    let request_id = request.request_id().to_owned();
    let mut owner = Owner(
        AuthorizationSession::new(
            limits,
            InspectionGeometry {
                columns: 32,
                lines: 8,
            },
        )
        .map_err(|_| 5u16)?,
    );
    let mut key = [0x11; 32];
    owner
        .0
        .select_key(SecretKey::take_from(&mut key).map_err(|_| 5u16)?)
        .map_err(|_| 5u16)?;
    owner
        .0
        .begin_request(envelope.payload_json, Some(intake))
        .map_err(|_| 5u16)?;
    clock.review_started.set(true);
    {
        let mut ui = Ui {
            wire,
            clock: &clock,
            metrics,
            case,
            invocation: 0,
            serial: 0,
            phase: Phase::Active,
            waited: false,
        };
        while owner.0.state() == AuthorizationState::Reviewing {
            owner.0.review_step(&mut ui).map_err(|_| 5u16)?;
        }
        if owner.0.state() != AuthorizationState::Approved {
            return Err(5);
        }
        dispatch_guard(ui.phase)?;
    }
    if case == 21 {
        owner.0.policy_changed().map_err(|_| 5u16)?;
    }
    metrics.sign_entries.set(metrics.sign_entries.get() + 1);
    wire.send(SIGN_ENTRY, 0, 0, &metrics.sign_entries.get().to_be_bytes())?;
    let mut output = [0; SIGNED_EVENT_BYTES];
    let written = {
        let mut auxiliary = Auxiliary {
            wire,
            metrics,
            case,
        };
        let destination = if case == 17 {
            &mut output[..16]
        } else {
            &mut output[..]
        };
        let id = if case == 16 {
            "wrong-request"
        } else {
            &request_id
        };
        owner
            .0
            .sign_approved(id, &mut || clock.sample(), &mut auxiliary, destination)
            .map_err(|_| 5u16)?
    };
    let event = std::str::from_utf8(&output[..written]).map_err(|_| 5u16)?;
    let json = format!("{{\"version\":2,\"request_id\":\"{request_id}\",\"ok\":true,\"result\":{{\"event\":{event}}}}}");
    if json.len() > 704 || clock.sample().is_none() {
        return Err(2);
    }
    let mut encoded = [0; 947];
    let result = encode_qr_envelope_json(json.as_bytes(), &mut encoded).map_err(|_| 5u16)?;
    if clock.sample().is_none() {
        return Err(2);
    }
    if case == 22 {
        let bytes = wire.encode(RESULT, 0, 0, result)?;
        wire.output
            .write_all(&bytes[..bytes.len() - 7])
            .map_err(|_| 1u16)?;
        wire.output.flush().map_err(|_| 1u16)?;
        return Ok(Outcome::Silent);
    }
    wire.send(RESULT, 0, 0, result)?;
    Ok(Outcome::Normal)
}
fn main() -> ExitCode {
    let arguments: Vec<_> = std::env::args_os().collect();
    if arguments.len() != 2 || arguments[1] != "--hrt-source-admitted-v1" {
        eprintln!("opt-in public fixture only; separate source/runtime admission required");
        return ExitCode::from(2);
    }
    let mut wire = Wire {
        input: io::stdin(),
        output: io::stdout(),
        nonce: None,
        incoming: 0,
        outgoing: 0,
    };
    let metrics = Metrics::default();
    let outcome = run(&mut wire, &metrics);
    if matches!(&outcome, Ok(Outcome::Silent)) {
        return ExitCode::SUCCESS;
    }
    let status = outcome.err().unwrap_or(0);
    let mut report = Vec::with_capacity(12);
    report.extend_from_slice(&status.to_be_bytes());
    report.extend_from_slice(&metrics.sign_entries.get().to_be_bytes());
    report.extend_from_slice(&metrics.auxiliary_calls.get().to_be_bytes());
    report.extend_from_slice(&metrics.review_calls.get().to_be_bytes());
    if wire.send(TERMINAL, 0, 0, &report).is_err() {
        return ExitCode::from(2);
    }
    if metrics.case.get() == 23 && wire.send(TERMINAL, 0, 0, &report).is_err() {
        return ExitCode::from(2);
    }
    if metrics.case.get() == 24 {
        loop {
            std::thread::sleep(Duration::from_millis(25));
        }
    }
    ExitCode::SUCCESS
}
