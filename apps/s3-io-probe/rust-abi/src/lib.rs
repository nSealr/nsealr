// SPDX-License-Identifier: MIT
//! Public-only target ABI/backend check. This is not a signing API.
//! Scalar3 is published BIP340 test-vector material, never a user identity.
#![no_std]
use nsealr_core::{
    authorization::AuthorizationSession,
    event::OperationLimits,
    hash::sha256,
    nip19::SecretKey,
    review::event::InspectionGeometry,
};

/// Writes SHA256("abc") and BIP340 scalar3's x-only public key.
/// Returns0 on success, -1 for invalid output, -2 for a core rejection.
/// No input or secret is accepted; output is exactly64 public bytes.
///
/// # Safety
/// With capacity64, output must point to64 writable, uniquely borrowed bytes.
/// Other capacities and a null pointer are rejected without dereferencing.
#[no_mangle]
pub unsafe extern "C" fn nsealr_s3_abi_check(output: *mut u8, capacity: usize) -> i32 {
    if output.is_null() || capacity != 64 {
        return -1;
    }
    let digest = sha256(b"abc");
    let mut scalar = [0u8; 32];
    scalar[31] = 3; // Public BIP340 vector0 fixture only.
    let Ok(secret) = SecretKey::take_from(&mut scalar) else { return -2 };
    let Ok(mut owner) = AuthorizationSession::new(
        OperationLimits::conformance(),
        InspectionGeometry { columns: 32, lines: 8 },
    ) else { return -2 };
    if owner.select_key(secret).is_err() {
        return -2;
    }
    let Some(public_key) = owner.public_key() else { return -2 };
    // End fixture custody explicitly. There has been no request or consent.
    if owner.lock().is_err() {
        return -2;
    }
    // SAFETY: the caller contract above grants exactly64 writable bytes.
    let out = unsafe { core::slice::from_raw_parts_mut(output, 64) };
    out[..32].copy_from_slice(&digest);
    out[32..].copy_from_slice(&public_key);
    0
}

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo<'_>) -> ! {
    // The public diagnostic stalls instead of crossing the C boundary/unwinding.
    // A future session firmware must qualify its own panic/reset/dump policy.
    loop { core::hint::spin_loop(); }
}
