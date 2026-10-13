#![no_std]
#![no_main]
// Link-only research artifact, NOT flashable firmware: no startup, linker memory
// map, board peripherals, real entropy, authorization or custody implementation.
#[cfg(all(feature="rustcrypto",not(feature="libsecp")))]
use nsealr_crypto_feasibility_spike::rustcrypto as backend;
#[cfg(all(feature="libsecp",not(feature="rustcrypto")))]
use nsealr_crypto_feasibility_spike::libsecp as backend;
#[cfg(any(all(feature="libsecp",feature="rustcrypto"),not(any(feature="libsecp",feature="rustcrypto"))))]
compile_error!("select exactly one backend for the freestanding probe");
static PUBLIC_FIXTURE_SECRET: [u8;32] = [3;32];
static PUBLIC_FIXTURE_MSG: [u8;32] = [7;32];
static PUBLIC_FIXTURE_PK: [u8;32] = [
  0xf9,0x30,0x8a,0x01,0x92,0x58,0xc3,0x10,0x49,0x34,0x4f,0x85,0xf8,0x9d,0x52,0x29,
  0xb5,0x31,0xc8,0x45,0x83,0x6f,0x99,0xb0,0x86,0x01,0xf1,0x13,0xbc,0xe0,0x36,0xf9];
static mut OUTPUT: [u8;97] = [0;97];
#[no_mangle]
pub extern "C" fn _start() -> ! {
 let sk=unsafe{core::ptr::read_volatile(&PUBLIC_FIXTURE_SECRET)};
 let msg=unsafe{core::ptr::read_volatile(&PUBLIC_FIXTURE_MSG)};
 let pk=unsafe{core::ptr::read_volatile(&PUBLIC_FIXTURE_PK)};
 let sig=backend::sign(&sk,&msg,&[0;32]).unwrap();
 let verified=backend::verify(&pk,&msg,&sig);
 let shared=backend::conversation(&sk,&pk).unwrap();
 let mut output=[0u8;97];output[..64].copy_from_slice(&sig);output[64..96].copy_from_slice(&shared);output[96]=verified as u8;
 unsafe{core::ptr::write_volatile(core::ptr::addr_of_mut!(OUTPUT),output)};
 loop{core::hint::spin_loop()}
}
#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {loop{core::hint::spin_loop()}}
