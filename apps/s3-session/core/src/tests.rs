unsafe extern "C" fn test_aux(out: *mut u8, capacity: usize, supplied: *mut usize) -> i32 {
    if out.is_null() || supplied.is_null() || capacity != 32 {
        return -1;
    }
    unsafe {
        core::slice::from_raw_parts_mut(out, 32).fill(0x42);
        *supplied = 32;
    }
    0
}
use super::*;
use std::{
    sync::atomic::{AtomicI32, AtomicU64, AtomicUsize, Ordering},
    vec::Vec,
};
static MODE: AtomicI32 = AtomicI32::new(0);
static CALLS: AtomicUsize = AtomicUsize::new(0);
static CLOCK_CALLS: AtomicUsize = AtomicUsize::new(0);
static TICK: AtomicU64 = AtomicU64::new(10);
extern "C" fn now(out: *mut u64) -> i32 {
    let n = CLOCK_CALLS.fetch_add(1, Ordering::SeqCst);
    if MODE.load(Ordering::SeqCst) == 9 {
        assert_eq!(nsealr_s3_public_feed(b"x"[0]), BUSY);
        assert_eq!(nsealr_s3_public_reset_input(), BUSY);
        let mut out = [0xa5; FRAME];
        let r = unsafe {
            nsealr_s3_public_exchange(
                out.as_mut_ptr(),
                FRAME,
                Some(present),
                Some(now),
                Some(cancelled),
                Some(test_aux),
            )
        };
        assert_eq!(r.status, BUSY);
        assert!(out.iter().all(|b| *b == 0xa5));
    }
    let m = MODE.load(Ordering::SeqCst);
    if m == 5 {
        return -1;
    }
    let t = if m == 6 && n > 0 {
        9
    } else if m == 7 && n > 0 {
        110
    } else {
        TICK.load(Ordering::SeqCst)
    };
    unsafe { *out = t };
    0
}
extern "C" fn cancelled() -> i32 {
    i32::from(MODE.load(Ordering::SeqCst) == 8 && CLOCK_CALLS.load(Ordering::SeqCst) > 0)
}
extern "C" fn present(
    k: u32,
    i: u32,
    t: u32,
    l: *const u8,
    ln: usize,
    b: *const u8,
    bn: usize,
    p: *const u8,
    pn: usize,
) -> i32 {
    CALLS.fetch_add(1, Ordering::SeqCst);
    assert!(i < t && t <= 128);
    let mut rows = 0;
    for (ptr, len) in [(l, ln), (b, bn), (p, pn)] {
        let bytes = unsafe { core::slice::from_raw_parts(ptr, len) };
        assert!(bytes
            .iter()
            .all(|b| b.is_ascii_graphic() || *b == b' ' || *b == b'\n'));
        for line in bytes.split(|b| *b == b'\n') {
            assert!(line.len() <= 26);
            rows += 1;
        }
    }
    assert!(rows <= 8);
    match MODE.load(Ordering::SeqCst) {
        1 => 4,
        2 => -1,
        3 => 3,
        4 => 0,
        _ => {
            if k == 0 {
                1
            } else {
                3
            }
        }
    }
}
fn reset(mode: i32) {
    MODE.store(mode, Ordering::SeqCst);
    CALLS.store(0, Ordering::SeqCst);
    CLOCK_CALLS.store(0, Ordering::SeqCst);
    TICK.store(10, Ordering::SeqCst);
    assert_eq!(nsealr_s3_public_reset_input(), 0);
}
const REQUEST_JSON:&[u8]=br#"{"version":2,"request_id":"s3-public-1","method":"sign_event","params":{"event_template":{"kind":1,"created_at":1710000000,"content":"S3 public physical approval","tags":[]}}}"#;
fn encoded(json: &[u8]) -> Vec<u8> {
    let mut out = [0u8; FRAME];
    let n = frame_json(FrameType::Request, json, &mut out).unwrap();
    out[..n].to_vec()
}
fn feed(b: &[u8]) {
    for (i, x) in b.iter().enumerate() {
        assert_eq!(
            nsealr_s3_public_feed(*x),
            if i + 1 == b.len() { 1 } else { 0 }
        );
    }
}
fn run(mode: i32, json: &[u8]) -> (ExchangeResult, [u8; 1024]) {
    reset(mode);
    feed(&encoded(json));
    let mut out = [0xa5; FRAME];
    let result = unsafe {
        nsealr_s3_public_exchange(
            out.as_mut_ptr(),
            out.len(),
            Some(present),
            Some(now),
            Some(cancelled),
            Some(test_aux),
        )
    };
    (result, out)
}
fn payload(out: &[u8], n: u32) -> Vec<u8> {
    let f = decode_serial_frame(&out[..n as usize]).unwrap();
    let mut raw = [0; RESPONSE];
    decode_base64url(f.payload_base64url, &mut raw)
        .unwrap()
        .to_vec()
}
#[test]
fn actual_signing_and_complete_26x8_frames() {
    let (r, out) = run(0, REQUEST_JSON);
    assert_eq!(r.status, 0);
    assert!(CALLS.load(Ordering::SeqCst) > 20);
    let j = payload(&out, r.length);
    assert!(j.windows(6).any(|w| w == b"\"sig\":"));
    if let Ok(dir) = std::env::var("NSEALR_S3_TEST_OUTPUT") {
        let p = std::path::Path::new(&dir);
        std::fs::create_dir_all(p).unwrap();
        std::fs::write(p.join("response.serial"), &out[..r.length as usize]).unwrap();
        std::fs::write(p.join("response.json"), &j).unwrap();
        std::fs::write(p.join("request.json"), REQUEST_JSON).unwrap();
    }
}
#[test]
fn get_public_key_uses_actual_fixture_owner() {
    let (r, out) = run(
        0,
        br#"{"version":2,"request_id":"key","method":"get_public_key"}"#,
    );
    assert_eq!(r.status, 0);
    assert_eq!(CALLS.load(Ordering::SeqCst), 0);
    let j = payload(&out, r.length);
    assert!(j
        .windows(64)
        .any(|w| w == b"f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9"));
}
#[test]
fn rejection_and_failed_draw_produce_only_error_frames() {
    for (mode, expected) in [(1, REJECTED), (2, DISPLAY), (3, ENGINE), (4, ENGINE)] {
        let (r, out) = run(mode, REQUEST_JSON);
        assert_eq!(r.status, expected);
        assert_eq!(
            decode_serial_frame(&out[..r.length as usize])
                .unwrap()
                .frame_type,
            FrameType::Error
        );
        assert!(!payload(&out, r.length).windows(6).any(|w| w == b"\"sig\":"));
    }
}
#[test]
fn clock_failure_rollback_expiry_and_cancel_fail_closed() {
    for (mode, expected) in [(5, CLOCK), (6, CLOCK), (7, CLOCK), (8, CANCEL)] {
        let (r, out) = run(mode, REQUEST_JSON);
        assert_eq!(r.status, expected);
        assert_eq!(
            decode_serial_frame(&out[..r.length as usize])
                .unwrap()
                .frame_type,
            FrameType::Error
        );
    }
}
#[test]
fn overflowed_epoch_and_missing_clock_are_not_wrapped() {
    reset(0);
    TICK.store(u64::MAX - 50, Ordering::SeqCst);
    let mut out = [0; FRAME];
    assert_eq!(
        exchange(
            &encoded(REQUEST_JSON),
            present,
            now,
            cancelled,
            &mut out,
            &mut PublicAux
        ),
        Err(CLOCK)
    );
}
#[test]
fn malformed_duplicate_trailing_and_host_approval_reject_before_draw() {
    let cases:[&[u8];5]=[
        br#"{"version":2,"version":2,"request_id":"x","method":"get_public_key"}"#,
        br#"{"version":2,"request_id":"x","method":"get_public_key"}x"#,
        br#"{"version":2,"request_id":"x","method":"get_public_key","approved":true}"#,
        br#"{"version":2,"request_id":"x","method":"import_nsec","params":{"nsec":"public-rejected"}}"#,
        br#"{"version":2,"request_id":"x","method":"sign_event","params":{"event_template":{"kind":65536,"created_at":1,"tags":[],"content":""}}}"#
    ];
    for j in cases {
        let (r, _) = run(0, j);
        assert_eq!(r.status, REQUEST);
        assert_eq!(CALLS.load(Ordering::SeqCst), 0);
    }
}
#[test]
fn capabilities_never_advertise_a_qualified_profile() {
    let (r, _) = run(
        0,
        br#"{"version":2,"request_id":"x","method":"get_capabilities"}"#,
    );
    assert_eq!(r.status, UNSUPPORTED);
    assert_eq!(CALLS.load(Ordering::SeqCst), 0);
}
#[test]
fn ffi_invalid_pointer_capacity_and_callback_preserve_guards() {
    reset(0);
    let mut guarded = [0xa5u8; 1026];
    for cap in [0, 1023, 1025] {
        let r = unsafe {
            nsealr_s3_public_exchange(
                guarded[1..].as_mut_ptr(),
                cap,
                Some(present),
                Some(now),
                Some(cancelled),
                Some(test_aux),
            )
        };
        assert_eq!(r.status, ARG);
        assert!(guarded.iter().all(|b| *b == 0xa5));
    }
    let r = unsafe {
        nsealr_s3_public_exchange(
            core::ptr::null_mut(),
            1024,
            Some(present),
            Some(now),
            Some(cancelled),
            Some(test_aux),
        )
    };
    assert_eq!(r.status, ARG);
    let r = unsafe {
        nsealr_s3_public_exchange(
            guarded[1..].as_mut_ptr(),
            1024,
            None,
            Some(now),
            Some(cancelled),
            Some(test_aux),
        )
    };
    assert_eq!(r.status, ARG);
    assert!(guarded.iter().all(|b| *b == 0xa5));
    assert_eq!(
        unsafe { nsealr_s3_public_key(core::ptr::null_mut(), 32) },
        ARG
    );
    assert_eq!(
        unsafe { nsealr_s3_public_key(guarded.as_mut_ptr(), 31) },
        ARG
    );
    feed(&encoded(REQUEST_JSON));
    let r = unsafe {
        nsealr_s3_public_exchange(
            guarded[1..].as_mut_ptr(),
            1024,
            Some(present),
            Some(now),
            Some(cancelled),
            Some(test_aux),
        )
    };
    assert_eq!(r.status, 0);
    assert_eq!(guarded[0], 0xa5);
    assert_eq!(guarded[1025], 0xa5);
}
#[test]
fn ingress_overflow_drains_and_busy_does_not_replace_complete_frame() {
    reset(0);
    for _ in 0..1024 {
        assert_eq!(nsealr_s3_public_feed(b'x'), 0);
    }
    assert_eq!(nsealr_s3_public_feed(b'x'), 2);
    assert_eq!(nsealr_s3_public_feed(b'\n'), 0);
    feed(&encoded(REQUEST_JSON));
    assert_eq!(nsealr_s3_public_feed(b'x'), BUSY);
    let mut out = [0; FRAME];
    let r = unsafe {
        nsealr_s3_public_exchange(
            out.as_mut_ptr(),
            FRAME,
            Some(present),
            Some(now),
            Some(cancelled),
            Some(test_aux),
        )
    };
    assert_eq!(r.status, 0);
}
struct BadAux(usize);
impl AuxiliarySource for BadAux {
    fn fill(&mut self, d: &mut [u8; 32]) -> Result<usize, AuxiliaryError> {
        d.fill(7);
        if self.0 == 99 {
            Err(AuxiliaryError::Health)
        } else {
            Ok(self.0)
        }
    }
}
#[test]
fn auxiliary_failure_and_short_oversized_reports_release_no_signature() {
    for n in [0, 31, 33, 99] {
        reset(0);
        let mut out = [0u8; FRAME];
        assert_eq!(
            exchange(
                &encoded(REQUEST_JSON),
                present,
                now,
                cancelled,
                &mut out,
                &mut BadAux(n)
            ),
            Err(AUX)
        );
        assert!(out.iter().all(|b| *b == 0));
    }
}
#[test]
fn corrupted_frame_wrong_direction_and_oversized_decoded_json_reject() {
    reset(0);
    let mut bad = encoded(REQUEST_JSON);
    bad[20] ^= 1;
    let mut out = [0u8; FRAME];
    assert_eq!(
        exchange(&bad, present, now, cancelled, &mut out, &mut PublicAux),
        Err(REQUEST)
    );
    let mut b = [0; FRAME];
    let n = frame_json(FrameType::Response, b"{}", &mut b).unwrap();
    assert_eq!(
        exchange(&b[..n], present, now, cancelled, &mut out, &mut PublicAux),
        Err(REQUEST)
    );
    let over = [b' '; 321];
    assert_eq!(
        exchange(
            &encoded(&over),
            present,
            now,
            cancelled,
            &mut out,
            &mut PublicAux
        ),
        Err(REQUEST)
    );
    assert_eq!(CALLS.load(Ordering::SeqCst), 0);
}

#[test]
fn reentrant_callbacks_cannot_mutate_ingress_or_create_another_exchange() {
    let (r, out) = run(9, REQUEST_JSON);
    assert_eq!(r.status, 0);
    let json = payload(&out, r.length);
    assert!(json.windows(11).any(|w| w == b"s3-public-1"));
}

#[test]
fn callback_auxiliary_wipes_errors_and_inexact_counts_without_fallback() {
    unsafe extern "C" fn unavailable(out: *mut u8, _: usize, count: *mut usize) -> i32 {
        unsafe {
            core::slice::from_raw_parts_mut(out, 32).fill(0x61);
            *count = 32;
        }
        -2
    }
    unsafe extern "C" fn short(out: *mut u8, _: usize, count: *mut usize) -> i32 {
        unsafe {
            core::slice::from_raw_parts_mut(out, 32).fill(0x62);
            *count = 31;
        }
        0
    }
    unsafe extern "C" fn oversized(out: *mut u8, _: usize, count: *mut usize) -> i32 {
        unsafe {
            core::slice::from_raw_parts_mut(out, 32).fill(0x63);
            *count = 33;
        }
        0
    }
    unsafe extern "C" fn interrupted(out: *mut u8, _: usize, count: *mut usize) -> i32 {
        unsafe {
            core::slice::from_raw_parts_mut(out, 32).fill(0x64);
            *count = 1;
        }
        -7
    }
    for callback in [unavailable as Auxiliary, short, oversized, interrupted] {
        let mut guarded = [0xa7u8; 34];
        let destination: &mut [u8; 32] = (&mut guarded[1..33]).try_into().unwrap();
        assert!(CallbackAux(callback).fill(destination).is_err());
        assert_eq!(&guarded[1..33], &[0; 32]);
        assert_eq!(guarded[0], 0xa7);
        assert_eq!(guarded[33], 0xa7);
    }
}

#[test]
fn private_ffi_requires_auxiliary_and_releases_no_signature_on_provider_error() {
    reset(0);
    let mut untouched = [0xa7u8; FRAME];
    let absent = unsafe {
        nsealr_s3_public_exchange(
            untouched.as_mut_ptr(),
            FRAME,
            Some(present),
            Some(now),
            Some(cancelled),
            None,
        )
    };
    assert_eq!(absent.status, ARG);
    assert_eq!(untouched, [0xa7; FRAME]);
    unsafe extern "C" fn fail(out: *mut u8, _: usize, count: *mut usize) -> i32 {
        unsafe {
            core::slice::from_raw_parts_mut(out, 32).fill(0x71);
            *count = 31;
        }
        -8
    }
    feed(&encoded(REQUEST_JSON));
    let result = unsafe {
        nsealr_s3_public_exchange(
            untouched.as_mut_ptr(),
            FRAME,
            Some(present),
            Some(now),
            Some(cancelled),
            Some(fail),
        )
    };
    assert_eq!(result.status, AUX);
    let json = payload(&untouched, result.length);
    assert!(!json.windows(6).any(|b| b == b"\"sig\":"));
    assert!(json.windows(21).any(|b| b == b"auxiliary_unavailable"));
}
