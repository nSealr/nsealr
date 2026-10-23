use super::*;
use std::{cell::RefCell, sync::Mutex};

const BASIC: &[u8] = br#"{"version":2,"request_id":"req-kind-1-basic","method":"sign_event","params":{"event_template":{"created_at":1710000000,"kind":1,"tags":[],"content":"nSealr fixture: basic kind 1 event."}}}"#;
const GET: &[u8] = br#"{"version":2,"request_id":"req-get-public-key","method":"get_public_key"}"#;
static SERIAL: Mutex<()> = Mutex::new(());
#[derive(Default)]
struct State {
    clocks: usize,
    cancel_calls: usize,
    pages: Vec<(u32, u32, u32, Vec<u8>, Vec<u8>, Vec<u8>)>,
    providers: usize,
    action: Option<i32>,
    fail_clock: usize,
    cancel_at: usize,
    tick: u64,
    rollback_at: usize,
    expire_at: usize,
    aux_report: Option<i32>,
    prefix: usize,
    reenter_clock: bool,
    reenter_present: bool,
    did_back: bool,
    back: bool,
    invalid_cancel: bool,
}
thread_local! { static STATE: RefCell<State> = RefCell::new(State::default()); }
fn reset() {
    STATE.with(|s| *s.borrow_mut() = State::default());
}
extern "C" fn present(
    kind: u32,
    index: u32,
    total: u32,
    l: *const u8,
    ln: usize,
    b: *const u8,
    bn: usize,
    p: *const u8,
    pn: usize,
) -> i32 {
    STATE.with(|s| {
        let mut s = s.borrow_mut();
        s.pages.push((
            kind,
            index,
            total,
            unsafe { std::slice::from_raw_parts(l, ln).to_vec() },
            unsafe { std::slice::from_raw_parts(b, bn).to_vec() },
            unsafe { std::slice::from_raw_parts(p, pn).to_vec() },
        ));
        if s.reenter_present {
            assert_busy();
        }
        if s.back && index == 1 && !s.did_back {
            s.did_back = true;
            return 3;
        }
        s.action.unwrap_or(if kind == 1 { 1 } else { 0 })
    })
}
extern "C" fn now(tick: *mut u64) -> i32 {
    STATE.with(|s| {
        let mut s = s.borrow_mut();
        s.clocks += 1;
        if s.reenter_clock {
            assert_busy();
        }
        if s.clocks == s.fail_clock {
            return -1;
        }
        unsafe {
            *tick = if s.clocks == s.rollback_at {
                0
            } else if s.clocks == s.expire_at {
                s.tick + 100
            } else {
                s.tick
            };
        }
        0
    })
}
extern "C" fn aux(out: *mut u8, cap: usize) -> i32 {
    assert_eq!(cap, 32);
    STATE.with(|s| {
        let mut s = s.borrow_mut();
        s.providers += 1;
        unsafe {
            std::slice::from_raw_parts_mut(out, cap)[..s.prefix].fill(0x55);
        }
        s.aux_report.unwrap_or(32)
    })
}
extern "C" fn cancelled() -> i32 {
    STATE.with(|s| {
        let mut s = s.borrow_mut();
        s.cancel_calls += 1;
        if s.invalid_cancel {
            -1
        } else {
            i32::from(s.cancel_at == s.cancel_calls)
        }
    })
}
fn encode(json: &[u8]) -> Vec<u8> {
    let mut buffer = [0; FRAME];
    encode_qr_envelope_json(json, &mut buffer).unwrap().to_vec()
}
fn call(input: &[u8], capacity: usize) -> (i32, usize, Vec<u8>) {
    let mut output = vec![0xa5; capacity];
    let mut written = 123;
    let status = unsafe {
        qp01_fixture_request_v1(
            input.as_ptr(),
            input.len(),
            Some(present),
            Some(now),
            Some(aux),
            Some(cancelled),
            output.as_mut_ptr(),
            output.len(),
            &mut written,
        )
    };
    if status != 0 && status != ARGUMENT && status != BUSY {
        assert_eq!(written, 0);
        assert!(output.iter().all(|b| *b == 0));
    }
    if status == 0 {
        assert!(output[written..].iter().all(|b| *b == 0));
    }
    (status, written, output)
}
fn assert_busy() {
    // Invalid addresses are never borrowed: BUSY must precede all validation.
    assert_eq!(
        unsafe {
            qp01_fixture_request_v1(
                std::ptr::null(),
                usize::MAX,
                None,
                None,
                None,
                None,
                std::ptr::null_mut(),
                usize::MAX,
                std::ptr::null_mut(),
            )
        },
        BUSY
    );
}

#[test]
fn actual_ffi_effects_and_boundaries() {
    let _serial = SERIAL.lock().unwrap();
    reset();
    let basic = encode(BASIC);
    let get = encode(GET);
    let (status, length, output) = call(&basic, FRAME);
    assert_eq!((status, length), (0, 611));
    let mut decoded = [0; JSON];
    let json = decode_qr_envelope(&output[..length], &mut decoded)
        .unwrap()
        .payload_json;
    assert!(json
        .windows(64)
        .any(|p| p == b"2977f107ad2668dbd9f09b8594eff3b5276e21bfe098e60ae3e905e3c861e4d3"));
    STATE.with(|s| {
        let s = s.borrow();
        assert_eq!(s.providers, 1);
        for (i, p) in s.pages.iter().enumerate() {
            assert_eq!(p.1 as usize, i);
            assert_eq!(p.2 as usize, s.pages.len());
            assert_eq!(p.5, format!("{}/{}", i + 1, s.pages.len()).as_bytes());
        }
        assert_eq!(s.pages.last().unwrap().0, 1);
    });
    let clocks = STATE.with(|s| s.borrow().clocks);
    for stage in 1..=clocks {
        reset();
        STATE.with(|s| s.borrow_mut().fail_clock = stage);
        assert_eq!(call(&basic, FRAME).0, CLOCK);
        assert_eq!(STATE.with(|s| s.borrow().clocks), stage);
        assert_eq!(
            STATE.with(|s| s.borrow().providers),
            usize::from(stage >= clocks - 1)
        );
        reset();
        STATE.with(|s| {
            let mut s = s.borrow_mut();
            s.tick = 1;
            s.rollback_at = stage;
        });
        if stage > 1 {
            assert_eq!(call(&basic, FRAME).0, CLOCK);
        }
        reset();
        STATE.with(|s| s.borrow_mut().expire_at = stage);
        if stage > 1 {
            assert_eq!(call(&basic, FRAME).0, CLOCK);
        }
        reset();
        STATE.with(|s| s.borrow_mut().cancel_at = stage);
        assert_eq!(call(&basic, FRAME).0, CANCELLED);
    }
    reset();
    STATE.with(|s| s.borrow_mut().tick = u64::MAX);
    assert_eq!(call(&get, FRAME).0, CLOCK);
    reset();
    STATE.with(|s| s.borrow_mut().invalid_cancel = true);
    assert_eq!(call(&get, FRAME).0, CLOCK);
    for (action, expected) in [(1, ENGINE), (2, REJECTED), (4, ENGINE), (99, DISPLAY)] {
        reset();
        STATE.with(|s| s.borrow_mut().action = Some(action));
        assert_eq!(call(&basic, FRAME).0, expected);
        assert_eq!(STATE.with(|s| s.borrow().providers), 0);
    }
    reset();
    STATE.with(|s| s.borrow_mut().back = true);
    assert_eq!(call(&basic, FRAME).0, 0);
    STATE.with(|s| {
        let s = s.borrow();
        assert!(s.did_back);
        assert_eq!(s.pages[2].1, 0);
    });
    for prefix in 0..=32 {
        reset();
        STATE.with(|s| {
            let mut s = s.borrow_mut();
            s.prefix = prefix;
            s.aux_report = Some(-1);
        });
        assert_eq!(call(&basic, FRAME).0, AUXILIARY);
        assert_eq!(STATE.with(|s| s.borrow().providers), 1);
    }
    for count in [0, 1, 31, 33] {
        reset();
        STATE.with(|s| s.borrow_mut().aux_report = Some(count));
        assert_eq!(call(&basic, FRAME).0, AUXILIARY);
    }
    reset();
    assert_eq!(call(&get, 197).0, CAPACITY);
    assert_eq!(STATE.with(|s| s.borrow().providers), 0);
    reset();
    assert_eq!(call(&basic, 610).0, CAPACITY);
    assert_eq!(STATE.with(|s| s.borrow().providers), 1);
    reset();
    assert_eq!(call(&get, FRAME).1, 198);
    assert!(STATE.with(|s| s.borrow().pages.is_empty()));
    reset();
    STATE.with(|s| {
        let mut s = s.borrow_mut();
        s.reenter_clock = true;
        s.reenter_present = true;
    });
    assert_eq!(call(&basic, FRAME).0, 0);
    reset();
    assert_eq!(call(&basic, FRAME).0, 0);
    for bad in [
        b"bad".as_slice(),
        b"nsealr1:AA",
        b"nsealr1:e31",
        b"nsealr1:e30=",
    ] {
        reset();
        assert_eq!(call(bad, FRAME).0, REQUEST);
        assert_eq!(STATE.with(|s| s.borrow().clocks), 0);
    }
    for bad in [
        br#"{"version":2,"request_id":"x","method":"no"}"#.as_slice(),
        br#"{"version":2,"version":2,"request_id":"x","method":"get_public_key"}"#,
    ] {
        assert_eq!(call(&encode(bad), FRAME).0, REQUEST);
    }
    assert_eq!(
        call(
            &encode(br#"{"version":2,"request_id":"x","method":"get_capabilities"}"#),
            FRAME
        )
        .0,
        UNSUPPORTED
    );
    let bad_kind = String::from_utf8(BASIC.to_vec())
        .unwrap()
        .replace("\"kind\":1", "\"kind\":4");
    assert_eq!(call(&encode(bad_kind.as_bytes()), FRAME).0, UNSUPPORTED);
    let mut padded = BASIC.to_vec();
    padded.resize(JSON, b' ');
    assert_eq!(call(&encode(&padded), FRAME).0, 0);
    // Large validated correlation plus legal content exceeds only the RESPONSE
    // staging bound: real signing occurs, then no partial response escapes.
    let large = String::from_utf8(BASIC.to_vec())
        .unwrap()
        .replace("req-kind-1-basic", &"r".repeat(128))
        .replace("nSealr fixture: basic kind 1 event.", &"x".repeat(200));
    reset();
    assert_eq!(call(&encode(large.as_bytes()), FRAME).0, CAPACITY);
    assert_eq!(STATE.with(|s| s.borrow().providers), 1);
}

#[test]
fn arguments_do_not_touch_any_live_destination() {
    let _serial = SERIAL.lock().unwrap();
    let input = encode(GET);
    let mut output = [0xa5; FRAME];
    let mut written = 123usize;
    let mut invoke = |p, n, o, c, w| unsafe {
        qp01_fixture_request_v1(
            p,
            n,
            Some(present),
            Some(now),
            Some(aux),
            Some(cancelled),
            o,
            c,
            w,
        )
    };
    for (p, n) in [
        (std::ptr::null(), 1),
        (input.as_ptr(), 0),
        (input.as_ptr(), 948),
        (usize::MAX as *const u8, 2),
    ] {
        assert_eq!(
            invoke(p, n, output.as_mut_ptr(), FRAME, &mut written),
            ARGUMENT
        );
    }
    for (o, c, w) in [
        (std::ptr::null_mut(), 1, &mut written as *mut usize),
        (output.as_mut_ptr(), 0, &mut written),
        (output.as_mut_ptr(), 948, &mut written),
        (output.as_mut_ptr(), FRAME, std::ptr::null_mut()),
        (
            output.as_mut_ptr(),
            FRAME,
            output.as_mut_ptr().wrapping_add(1).cast(),
        ),
        (output.as_mut_ptr(), FRAME, output.as_mut_ptr().cast()),
        (output.as_mut_ptr(), FRAME, input.as_ptr().cast_mut().cast()),
    ] {
        assert_eq!(invoke(input.as_ptr(), input.len(), o, c, w), ARGUMENT);
    }
    assert_eq!(
        invoke(
            input.as_ptr(),
            input.len(),
            input.as_ptr().cast_mut(),
            1,
            &mut written
        ),
        ARGUMENT
    );
    assert_eq!(
        unsafe {
            qp01_fixture_request_v1(
                input.as_ptr(),
                input.len(),
                None,
                Some(now),
                Some(aux),
                Some(cancelled),
                output.as_mut_ptr(),
                FRAME,
                &mut written,
            )
        },
        ARGUMENT
    );
    assert_eq!(written, 123);
    assert_eq!(output, [0xa5; FRAME]);
    assert_eq!(range(1, usize::MAX), None);
}

#[test]
fn unwind_cleanup_and_internal_error_mapping() {
    let _serial = SERIAL.lock().unwrap();
    let mut out = [0xa5; 9];
    {
        let _active = Active::acquire().unwrap();
        assert_eq!(
            settled(&mut out, |out| {
                out[0] = 7;
                panic!("controlled internal Rust unwind")
            }),
            Err(PANIC)
        );
    }
    assert_eq!(out, [0; 9]);
    let _active = Active::acquire().unwrap();
    let fresh = Freshness {
        now,
        cancelled,
        last: Cell::new(None),
        deadline: Cell::new(None),
        failure: Cell::new(0),
    };
    for (error, status) in [
        (AuthorizationError::Clock, CLOCK),
        (AuthorizationError::Expired, CLOCK),
        (
            AuthorizationError::Parse(nsealr_core::event::EventError::Syntax),
            REQUEST,
        ),
        (AuthorizationError::Output, CAPACITY),
    ] {
        assert_eq!(fresh.error(error), status);
    }
    let mut length = usize::MAX;
    assert_eq!(append(&mut out, &mut length, b"x"), Err(CAPACITY));
    fresh.failure.set(CLOCK);
    assert_eq!(fresh.sample(), None);
}
