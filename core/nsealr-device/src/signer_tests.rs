//! Independent public vectors plus the actual C boundary lifecycle.
use super::*;
use crate::threshold_abi::ns_threshold_start;
use alloc::{format, string::String, vec};

#[repr(C, align(16))]
struct Storage([u8; 2048]);
struct Device(Box<Storage>);
impl Device {
    fn new() -> Self {
        let mut device = Self(Box::new(Storage([0; 2048])));
        assert_eq!(unsafe { ns_init(device.0 .0.as_mut_ptr(), 2048) }, 0);
        device
    }
    fn ptr(&mut self) -> *mut Context {
        self.0 .0.as_mut_ptr().cast()
    }
    fn generate(&mut self, key: u8) {
        let mut entropy = [0; 32];
        entropy[31] = key;
        assert_eq!(
            unsafe { ns_generate(self.ptr(), 0, entropy.as_mut_ptr(), ptr::null_mut(), 0, 0) },
            0
        );
        assert_eq!(entropy, [0; 32]);
    }
    fn stage(&mut self, message: &str, now: u64) {
        let count = message.len().div_ceil(qr::CHUNK);
        for i in (0..count).rev() {
            let frame = qr::encode(message.as_bytes(), i).unwrap();
            let result = unsafe { ns_stage_frame(self.ptr(), frame.as_ptr(), frame.len(), now) };
            assert_eq!(result, i32::from(i != 0));
        }
        assert!(unsafe { ns_has_staged_request(self.ptr()) });
        assert_eq!(unsafe { ns_review_count(self.ptr()) }, 0);
    }
    fn backup(&mut self, kind: u32) -> String {
        let mut out = [0; 256];
        let mut len = 0;
        assert_eq!(
            unsafe { ns_backup(self.ptr(), kind, out.as_mut_ptr(), out.len(), &mut len) },
            0
        );
        String::from_utf8(out[..len].to_vec()).unwrap()
    }
    fn public(&mut self) -> String {
        let mut out = [0; 64];
        let mut len = 0;
        assert_eq!(
            unsafe { ns_public_key(self.ptr(), 0, out.as_mut_ptr(), out.len(), &mut len) },
            0
        );
        String::from_utf8(out.to_vec()).unwrap()
    }
}
impl Drop for Device {
    fn drop(&mut self) {
        unsafe { ns_deinit(self.ptr()) };
    }
}

#[test]
fn local_generation_matches_independent_vectors_and_wipes_inputs() {
    let mut d = Device::new();
    for (words, pattern, repeats, suffix, mnemonic, public) in [
        (12, "123456", 8, "12", "unveil nice picture region tragic fault cream strike tourist control recipe tourist", "99b6e95ef71c899a4bd8561a3c2fc1920a5b2da85e50c72a9a054a14168a5435"),
        (24, "654321", 16, "6543", "punch glove verb romance ignore speed warrior purity dizzy vacant inflict toe warm cute title bubble south arch atom exhaust duty enter describe oblige", "46af5629c6dab5ec4c666c94636a1ef5b103008713f0339d517c342df9275cd5"),
    ] {
        let mut rolls = (pattern.repeat(repeats) + suffix).into_bytes();
        assert_eq!(unsafe { ns_generate_dice(d.ptr(), words, rolls.as_mut_ptr(), rolls.len()) }, 0);
        assert!(rolls.iter().all(|value| *value == 0));
        assert_eq!(d.backup(2), mnemonic);
        assert_eq!(d.public(), public);
    }
    for (words, expected) in [
        (
            12,
            "3ed055af87d5546580f4259539cb8ad15b72babac9428a964e2f0388fb7fad3f",
        ),
        (
            24,
            "e9838b7ef3c4a8d5ad44b3dfa97e78200b498c2db0acc2963dd1ec90c7277525",
        ),
    ] {
        let mut image = core::array::from_fn::<_, 32, _>(|i| i as u8 + 1);
        let mut hardware = core::array::from_fn::<_, 32, _>(|i| 255 - i as u8);
        assert_eq!(
            unsafe { ns_generate_photo(d.ptr(), words, image.as_mut_ptr(), hardware.as_mut_ptr()) },
            0
        );
        assert_eq!(image, [0; 32]);
        assert_eq!(hardware, [0; 32]);
        assert_eq!(d.public(), expected);
    }
    for (words, len, value) in [
        (12, 49, b'1'),
        (24, 99, b'1'),
        (24, 101, b'1'),
        (12, 50, b'0'),
        (12, 50, b'7'),
        (15, 50, b'1'),
    ] {
        let mut rolls = vec![value; len];
        assert!(unsafe { ns_generate_dice(d.ptr(), words, rolls.as_mut_ptr(), rolls.len()) } < 0);
        assert!(rolls.iter().all(|value| *value == 0));
        assert!(!unsafe { ns_is_loaded(d.ptr()) });
    }
    let mut image = [1; 32];
    let mut hardware = [0; 32];
    assert_eq!(
        unsafe { ns_generate_photo(d.ptr(), 12, image.as_mut_ptr(), hardware.as_mut_ptr()) },
        Error::Entropy as i32
    );
    assert_eq!(image, [0; 32]);
    let mut image = [2; 32];
    assert!(unsafe { ns_generate_photo(d.ptr(), 12, image.as_mut_ptr(), ptr::null_mut()) } < 0);
    assert_eq!(image, [0; 32]);
}

#[test]
fn quiz_indices_and_validation_cover_all_mnemonic_lengths() {
    let mut d = Device::new();
    for (count, last, index) in [
        (12, "about", 3),
        (15, "address", 27),
        (18, "agent", 39),
        (21, "admit", 29),
        (24, "art", 102),
    ] {
        unsafe { ns_lock(d.ptr()) };
        d.stage(
            r#"{"id":"load","method":"get_public_key","params":[]}"#,
            count as u64,
        );
        let phrase = "abandon ".repeat(count - 1) + last;
        let mut check = phrase.clone().into_bytes();
        assert_eq!(
            unsafe { ns_validate_mnemonic(check.as_mut_ptr(), check.len()) },
            0
        );
        assert!(check.iter().all(|value| *value == 0));
        assert!(unsafe { ns_has_staged_request(d.ptr()) });
        let mut input = phrase.into_bytes();
        assert_eq!(
            unsafe {
                ns_import_mnemonic(
                    d.ptr(),
                    input.as_mut_ptr(),
                    input.len(),
                    ptr::null_mut(),
                    0,
                    0,
                )
            },
            0
        );
        assert!(unsafe { ns_has_staged_request(d.ptr()) });
        let mut out = 65535;
        assert_eq!(
            unsafe { ns_backup_word_index(d.ptr(), count as u32 - 1, &mut out) },
            0
        );
        assert_eq!(out, index);
        assert!(unsafe { ns_backup_word_index(d.ptr(), count as u32, &mut out) } < 0);
        assert_eq!(out, 0);
        assert_eq!(unsafe { ns_resume_request(d.ptr(), count as u64 + 1) }, 0);
    }
    let public = d.public();
    let mut invalid = b"abandon ".repeat(12);
    assert!(unsafe { ns_validate_mnemonic(invalid.as_mut_ptr(), invalid.len()) } < 0);
    assert!(invalid.iter().all(|value| *value == 0));
    assert_eq!(d.public(), public);
}

fn sign_request() -> String {
    let key = "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9";
    let text = "Review this exact staged request. ".repeat(30);
    format!(
        r#"{{"id":"staged","method":"sign_event","params":["{{\"pubkey\":\"{key}\",\"created_at\":1710000000,\"kind\":1,\"tags\":[],\"content\":\"{text}\"}}"]}}"#
    )
}

#[test]
fn scan_first_loads_once_binds_identity_and_keeps_original_deadline() {
    let request = sign_request();
    let mut d = Device::new();
    d.stage(&request, 100);
    d.generate(3);
    assert!(unsafe { ns_has_staged_request(d.ptr()) });
    assert_eq!(unsafe { ns_resume_request(d.ptr(), 600000) }, 0);
    assert!(!unsafe { ns_has_staged_request(d.ptr()) });
    let generation = unsafe { ns_review_generation(d.ptr()) };
    assert!(unsafe { ns_review_count(d.ptr()) } > 0);
    for index in 0..unsafe { ns_review_count(d.ptr()) } {
        assert_eq!(unsafe { ns_review_seen(d.ptr(), generation, index) }, 0);
    }
    let mut entropy = [7; 32];
    assert_eq!(
        unsafe { ns_approve(d.ptr(), generation, false, entropy.as_mut_ptr(), 32, 600100) },
        Error::Stale as i32
    );
    assert_eq!(entropy, [0; 32]);
    assert!(unsafe { ns_resume_request(d.ptr(), 600100) } < 0);

    let mut wrong = Device::new();
    wrong.stage(&request, 0);
    wrong.generate(4);
    assert_eq!(
        unsafe { ns_resume_request(wrong.ptr(), 1) },
        Error::Identity as i32
    );
    assert_eq!(unsafe { ns_review_count(wrong.ptr()) }, 0);
    assert!(!unsafe { ns_has_staged_request(wrong.ptr()) });
    let mut reply = Text {
        data: ptr::null(),
        len: 0,
    };
    assert_eq!(unsafe { ns_response(wrong.ptr(), &mut reply) }, 0);
    let reply =
        unsafe { core::str::from_utf8(slice::from_raw_parts(reply.data, reply.len)) }.unwrap();
    assert!(reply.contains("staged") && reply.contains("error"));

    let mut good = Device::new();
    good.stage(&request, 100);
    good.generate(3);
    assert_eq!(unsafe { ns_resume_request(good.ptr(), 101) }, 0);
    let generation = unsafe { ns_review_generation(good.ptr()) };
    for index in 0..unsafe { ns_review_count(good.ptr()) } {
        assert_eq!(unsafe { ns_review_seen(good.ptr(), generation, index) }, 0);
    }
    let mut entropy = [8; 32];
    assert_eq!(
        unsafe { ns_approve(good.ptr(), generation, false, entropy.as_mut_ptr(), 32, 102) },
        0
    );
    let mut signed = Text {
        data: ptr::null(),
        len: 0,
    };
    assert_eq!(unsafe { ns_response(good.ptr(), &mut signed) }, 0);
    let signed =
        unsafe { core::str::from_utf8(slice::from_raw_parts(signed.data, signed.len)) }.unwrap();
    assert!(signed.contains("Review this exact staged request.") && signed.contains("staged"));
    assert_eq!(unsafe { ns_tick(good.ptr(), 600100) }, 1);
    assert!(
        unsafe {
            ns_response(
                good.ptr(),
                &mut Text {
                    data: ptr::null(),
                    len: 0,
                },
            )
        } < 0
    );
}

#[test]
fn staged_requests_are_revoked_by_cancel_lock_replacement_failure_and_expiry() {
    let request = r#"{"id":"key","method":"get_public_key","params":[]}"#;
    for scenario in 0..10 {
        let mut d = Device::new();
        d.stage(request, 10);
        unsafe {
            match scenario {
                0 => ns_cancel(d.ptr()),
                1 => ns_lock(d.ptr()),
                2 => {
                    assert_eq!(ns_tick(d.ptr(), 600010), 1);
                }
                3 => {
                    assert!(ns_tick(d.ptr(), 9) < 0);
                }
                4 => {
                    assert!(ns_request(d.ptr(), b"invalid".as_ptr(), 7, 11) < 0);
                }
                5 => {
                    assert!(ns_receive_frame(d.ptr(), b"invalid".as_ptr(), 7, 11) < 0);
                }
                6 => {
                    let mut bad = *b"bad";
                    assert!(ns_import_nsec(d.ptr(), bad.as_mut_ptr(), bad.len()) < 0);
                }
                7 => {
                    let mut entropy = [9; 32];
                    assert_eq!(ns_threshold_start(d.ptr(), entropy.as_mut_ptr(), 11), 0);
                }
                8 => {
                    let generation = ns_review_generation(d.ptr());
                    let mut entropy = [9; 32];
                    assert!(
                        ns_approve(d.ptr(), generation, false, entropy.as_mut_ptr(), 32, 11) < 0
                    );
                    assert_eq!(entropy, [0; 32]);
                }
                9 => {
                    let generation = ns_review_generation(d.ptr());
                    assert!(ns_reject(d.ptr(), generation) < 0);
                }
                _ => unreachable!(),
            }
            assert!(!ns_has_staged_request(d.ptr()));
            assert!(ns_resume_request(d.ptr(), 600011) < 0);
        }
    }
    let mut d = Device::new();
    let unsupported = r#"{"id":"bad","method":"nsealr_setup","params":[]}"#;
    let frame = qr::encode(unsupported.as_bytes(), 0).unwrap();
    assert!(unsafe { ns_stage_frame(d.ptr(), frame.as_ptr(), frame.len(), 1) } < 0);
    assert!(!unsafe { ns_has_staged_request(d.ptr()) });
}

#[test]
fn camera_frame_hash_matches_openssl_without_allocating_a_frame_copy() {
    static FRAME: [u8; 1280000] = [0x5a; 1280000];
    let mut chain = [0; 32];
    assert_eq!(
        unsafe { ns_photo_frame_hash(chain.as_mut_ptr(), FRAME.as_ptr(), FRAME.len(), false) },
        0
    );
    assert_eq!(
        nsealr_core::json::hex_string(&chain),
        "c23f0a8b9a376949e49f279626bdda6b41ec93966b86379241263b0f0a47c7aa"
    );
    assert_eq!(
        unsafe { ns_photo_frame_hash(chain.as_mut_ptr(), FRAME.as_ptr(), FRAME.len(), true) },
        0
    );
    assert_eq!(
        nsealr_core::json::hex_string(&chain),
        "1c8cf6c61ce914ca7549e75d9241e9e035d236d85e23ff3a2a6459843496d435"
    );
    assert!(
        unsafe { ns_photo_frame_hash(chain.as_mut_ptr(), FRAME.as_ptr(), FRAME.len() - 1, true) }
            < 0
    );
    assert_eq!(chain, [0; 32]);
}
