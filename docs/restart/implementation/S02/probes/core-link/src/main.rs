//! Link-only exercise. No startup, memory map or entropy; never flash this file.
#![no_std]
#![no_main]

use nsealr_core::{hash::sha256, nip19::SecretKey, session::keyring::StatelessSessionKeyring};

static mut OUTPUT: [u8; 32] = [0; 32];

#[no_mangle]
pub extern "C" fn _start() -> ! {
    let mut fixture = core::hint::black_box([0x11; 32]);
    let key = SecretKey::take_from(&mut fixture).unwrap();
    let mut ring = StatelessSessionKeyring::new();
    ring.add_nsec("PUBLIC FIXTURE", key).unwrap();
    core::hint::black_box(&mut ring);
    let digest = sha256(core::hint::black_box(b"abc"));
    // SAFETY: single link-only entry, exclusively writes this static output.
    unsafe { core::ptr::addr_of_mut!(OUTPUT).write_volatile(digest) };
    ring.clear();
    core::hint::black_box(&mut ring);
    drop(ring);
    loop { core::hint::spin_loop(); }
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! {
    loop { core::hint::spin_loop(); }
}
