//! Serialized native C boundary. See include/nsealr.h: valid initialized storage,
//! live nonoverlapping buffers and a single caller are required for every call.
#![cfg_attr(target_os = "none", no_std)]
#![allow(clippy::missing_safety_doc)]
extern crate alloc;
use alloc::boxed::Box;
mod threshold_abi;
#[cfg(target_os = "none")]
use core::alloc::{GlobalAlloc, Layout};
use core::{ptr, slice};
use nsealr_allocator::ZeroizingAllocator;
use nsealr_core::{bip39, identity::Identity, owner::Owner, qr, Error};
use nsealr_threshold::custody::Custody;
use zeroize::Zeroize;

const HEAP_LIMIT: usize = 256 * 1024;
#[cfg(target_os = "none")]
struct Backend;
#[cfg(target_os = "none")]
unsafe extern "C" {
    fn ns_platform_alloc(size: usize, align: usize) -> *mut u8;
    fn ns_platform_free(ptr: *mut u8, size: usize, align: usize);
    fn ns_platform_abort() -> !;
}
#[cfg(target_os = "none")]
unsafe impl GlobalAlloc for Backend {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        ns_platform_alloc(l.size(), l.align())
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        ns_platform_free(p, l.size(), l.align())
    }
}
#[cfg(target_os = "none")]
#[global_allocator]
static HEAP: ZeroizingAllocator<Backend> = ZeroizingAllocator::new(Backend, HEAP_LIMIT, 65536);
#[cfg(not(target_os = "none"))]
#[global_allocator]
static HEAP: ZeroizingAllocator<std::alloc::System> =
    ZeroizingAllocator::new(std::alloc::System, HEAP_LIMIT, 65536);
#[cfg(target_os = "none")]
#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    unsafe { ns_platform_abort() }
}

const MAGIC: u64 = 0x6e7365616c723031;
#[repr(C, align(16))]
pub struct Context {
    magic: u64,
    owner: Owner,
    custody: Box<Custody>,
    threshold: bool,
}
impl Context {
    fn fields(&self) -> &[nsealr_core::event::Field] {
        if self.threshold {
            self.custody.fields()
        } else {
            self.owner.fields()
        }
    }
    fn raw_generation(&self) -> u64 {
        if self.threshold {
            self.custody.generation()
        } else {
            self.owner.generation()
        }
    }
    fn generation(&self) -> u64 {
        self.raw_generation()
            .checked_mul(2)
            .and_then(|value| value.checked_add(u64::from(self.threshold)))
            .unwrap_or(0)
    }
    fn check_generation(&self, generation: u64) -> Result<u64, Error> {
        if generation == 0 || generation != self.generation() {
            Err(Error::Stale)
        } else {
            Ok(self.raw_generation())
        }
    }
    fn cancel(&mut self) {
        self.owner.cancel();
        self.custody.cancel();
    }
}
const _: () = assert!(core::mem::size_of::<Context>() <= 2048);
#[repr(C)]
pub struct Text {
    data: *const u8,
    len: usize,
}
fn code(result: Result<(), Error>) -> i32 {
    result.map_or_else(|e| e as i32, |_| 0)
}
unsafe fn owner<'a>(ctx: *mut Context) -> Result<&'a mut Owner, Error> {
    Ok(&mut context(ctx)?.owner)
}
unsafe fn context<'a>(ctx: *mut Context) -> Result<&'a mut Context, Error> {
    if ctx.is_null() || !(ctx as usize).is_multiple_of(16) || (*ctx).magic != MAGIC {
        return Err(Error::Input);
    }
    Ok(&mut *ctx)
}
unsafe fn shared<'a>(ctx: *const Context) -> Result<&'a Owner, Error> {
    Ok(&context_ref(ctx)?.owner)
}
unsafe fn context_ref<'a>(ctx: *const Context) -> Result<&'a Context, Error> {
    if ctx.is_null() || !(ctx as usize).is_multiple_of(16) || (*ctx).magic != MAGIC {
        return Err(Error::Input);
    }
    Ok(&*ctx)
}
unsafe fn full_owner<'a>(ctx: *mut Context) -> Result<&'a mut Owner, Error> {
    let c = context(ctx)?;
    c.custody.lock();
    c.threshold = false;
    Ok(&mut c.owner)
}
unsafe fn input<'a>(p: *const u8, n: usize) -> Result<&'a [u8], Error> {
    if n > nsealr_core::MAX_MESSAGE {
        return Err(Error::Bounds);
    }
    if n == 0 {
        return Ok(&[]);
    }
    if p.is_null() {
        return Err(Error::Input);
    }
    Ok(slice::from_raw_parts(p, n))
}
unsafe fn secret<'a>(p: *mut u8, n: usize) -> Result<&'a mut [u8], Error> {
    if n > nsealr_core::MAX_MESSAGE {
        return Err(Error::Bounds);
    }
    if n == 0 {
        return Ok(&mut []);
    }
    if p.is_null() {
        return Err(Error::Input);
    }
    Ok(slice::from_raw_parts_mut(p, n))
}
unsafe fn text(out: *mut Text, value: &str) -> Result<(), Error> {
    if out.is_null() {
        return Err(Error::Input);
    }
    ptr::write(
        out,
        Text {
            data: value.as_ptr(),
            len: value.len(),
        },
    );
    Ok(())
}
unsafe fn copy(
    out: *mut u8,
    capacity: usize,
    written: *mut usize,
    bytes: &[u8],
) -> Result<(), Error> {
    if written.is_null() {
        return Err(Error::Input);
    }
    *written = 0;
    let out = secret(out, capacity)?;
    out.zeroize();
    if bytes.len() > out.len() {
        return Err(Error::Output);
    }
    out[..bytes.len()].copy_from_slice(bytes);
    *written = bytes.len();
    Ok(())
}

#[no_mangle]
pub unsafe extern "C" fn ns_init(storage: *mut u8, bytes: usize) -> i32 {
    if storage.is_null() || !(storage as usize).is_multiple_of(16) || bytes < 2048 {
        return Error::Input as i32;
    }
    ptr::write(
        storage.cast::<Context>(),
        Context {
            magic: MAGIC,
            owner: Owner::default(),
            custody: Box::default(),
            threshold: false,
        },
    );
    0
}
#[no_mangle]
pub unsafe extern "C" fn ns_deinit(ctx: *mut Context) {
    if owner(ctx).is_ok() {
        ptr::drop_in_place(ctx);
        slice::from_raw_parts_mut(
            ctx.cast::<core::mem::MaybeUninit<u8>>(),
            core::mem::size_of::<Context>(),
        )
        .zeroize();
    }
}
#[no_mangle]
pub unsafe extern "C" fn ns_lock(ctx: *mut Context) {
    if let Ok(c) = context(ctx) {
        c.owner.lock();
        c.custody.lock();
        c.threshold = false;
    }
}
#[no_mangle]
pub unsafe extern "C" fn ns_cancel(ctx: *mut Context) {
    if let Ok(c) = context(ctx) {
        c.cancel();
    }
}
#[no_mangle]
pub unsafe extern "C" fn ns_is_loaded(ctx: *const Context) -> bool {
    context_ref(ctx).is_ok_and(|c| {
        if c.threshold {
            c.custody.loaded()
        } else {
            c.owner.identity().is_ok()
        }
    })
}
#[no_mangle]
pub extern "C" fn ns_error_text(error: i32) -> *const core::ffi::c_char {
    let msg: &[u8] = match error {
        -1 => b"Malformed input\0",
        -2 => b"Request exceeds device limits\0",
        -3 => b"Load an identity first\0",
        -4 => b"Unsupported operation or event semantics\0",
        -5 => b"Wrong identity\0",
        -6 => b"Review required fields\0",
        -7 => b"Request cancelled or expired\0",
        -8 => b"Cryptographic verification failed\0",
        -9 => b"Fresh randomness required\0",
        -10 => b"Output buffer is too small\0",
        _ => b"Device operation failed\0",
    };
    msg.as_ptr().cast()
}
#[no_mangle]
pub unsafe extern "C" fn ns_import_nsec(ctx: *mut Context, p: *mut u8, len: usize) -> i32 {
    let Ok(bytes) = secret(p, len) else {
        return Error::Input as i32;
    };
    let result = (|| {
        let o = full_owner(ctx)?;
        o.lock();
        let s = core::str::from_utf8(bytes).map_err(|_| Error::Input)?;
        o.select(Identity::nsec(s)?);
        Ok(())
    })();
    bytes.zeroize();
    code(result)
}
#[no_mangle]
pub unsafe extern "C" fn ns_import_mnemonic(
    ctx: *mut Context,
    p: *mut u8,
    len: usize,
    pass: *mut u8,
    passlen: usize,
    account: u32,
) -> i32 {
    import(ctx, 0, p, len, pass, passlen, account)
}
#[no_mangle]
pub unsafe extern "C" fn ns_import_secret_qr(
    ctx: *mut Context,
    kind: u32,
    p: *mut u8,
    len: usize,
    pass: *mut u8,
    passlen: usize,
    account: u32,
) -> i32 {
    import(ctx, kind, p, len, pass, passlen, account)
}
unsafe fn import(
    ctx: *mut Context,
    kind: u32,
    p: *mut u8,
    len: usize,
    pass: *mut u8,
    passlen: usize,
    account: u32,
) -> i32 {
    let Ok(bytes) = secret(p, len) else {
        return Error::Input as i32;
    };
    let Ok(password) = secret(pass, passlen) else {
        bytes.zeroize();
        return Error::Input as i32;
    };
    let result = (|| {
        let o = full_owner(ctx)?;
        o.lock();
        let pass = core::str::from_utf8(password).map_err(|_| Error::Input)?;
        let id = match kind {
            0 => Identity::mnemonic(
                core::str::from_utf8(bytes).map_err(|_| Error::Input)?,
                pass,
                account,
            )?,
            1 => {
                if !pass.is_empty() || account != 0 {
                    return Err(Error::Input);
                }
                Identity::nsec(core::str::from_utf8(bytes).map_err(|_| Error::Input)?)?
            }
            2 | 3 => Identity::seedqr(bytes, kind == 3, pass, account)?,
            _ => return Err(Error::Input),
        };
        o.select(id);
        Ok(())
    })();
    bytes.zeroize();
    password.zeroize();
    code(result)
}
#[no_mangle]
pub unsafe extern "C" fn ns_generate(
    ctx: *mut Context,
    words: u32,
    p: *mut u8,
    pass: *mut u8,
    passlen: usize,
    account: u32,
) -> i32 {
    let Ok(bytes) = secret(p, 32) else {
        return Error::Input as i32;
    };
    let Ok(password) = secret(pass, passlen) else {
        bytes.zeroize();
        return Error::Input as i32;
    };
    let result = (|| {
        let o = full_owner(ctx)?;
        o.lock();
        let pass = core::str::from_utf8(password).map_err(|_| Error::Input)?;
        o.select(Identity::generate(
            words,
            bytes.try_into().map_err(|_| Error::Input)?,
            pass,
            account,
        )?);
        Ok(())
    })();
    bytes.zeroize();
    password.zeroize();
    code(result)
}
#[no_mangle]
pub unsafe extern "C" fn ns_public_key(
    ctx: *const Context,
    format: u32,
    out: *mut u8,
    cap: usize,
    written: *mut usize,
) -> i32 {
    code((|| {
        let c = context_ref(ctx)?;
        let public = if c.threshold {
            *c.custody.public_key()?
        } else {
            c.owner.identity()?.public_key()
        };
        let mut npub = [0; 83];
        let value = match format {
            0 => nsealr_core::json::hex_string(&public),
            1 => nsealr_core::nip19::encode_npub(&public, &mut npub)
                .map_err(|_| Error::Output)?
                .into(),
            _ => return Err(Error::Input),
        };
        copy(out, cap, written, value.as_bytes())
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_word_count(ctx: *const Context) -> u32 {
    shared(ctx)
        .and_then(|o| o.identity())
        .map_or(0, |id| id.word_count() as u32)
}
#[no_mangle]
pub unsafe extern "C" fn ns_wordlist_word(index: u32, out: *mut Text) -> i32 {
    code((|| {
        if index >= 2048 {
            return Err(Error::Input);
        }
        text(out, bip39::word_at(index as u16).map_err(|_| Error::Input)?)
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_wordlist_find(
    p: *const u8,
    len: usize,
    indices: *mut u16,
    cap: usize,
    written: *mut usize,
) -> i32 {
    code((|| {
        if cap > 2048 || written.is_null() || indices.is_null() {
            return Err(Error::Input);
        }
        *written = 0;
        let prefix = core::str::from_utf8(input(p, len)?).map_err(|_| Error::Input)?;
        if prefix.len() > 8 || !prefix.bytes().all(|b| b.is_ascii_lowercase()) {
            return Err(Error::Input);
        }
        for i in 0..2048 {
            if bip39::word_at(i)
                .map_err(|_| Error::Input)?
                .starts_with(prefix)
            {
                if *written == cap {
                    break;
                }
                *indices.add(*written) = i;
                *written += 1;
            }
        }
        Ok(())
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_backup(
    ctx: *const Context,
    kind: u32,
    out: *mut u8,
    cap: usize,
    written: *mut usize,
) -> i32 {
    code((|| {
        if written.is_null() {
            return Err(Error::Input);
        }
        *written = 0;
        let out = secret(out, cap)?;
        out.zeroize();
        *written = shared(ctx)?.identity()?.backup(kind, out)?;
        Ok(())
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_backup_word(
    ctx: *const Context,
    index: u32,
    out: *mut u8,
    cap: usize,
    written: *mut usize,
) -> i32 {
    code((|| {
        if written.is_null() {
            return Err(Error::Input);
        }
        *written = 0;
        secret(out, cap)?.zeroize();
        copy(
            out,
            cap,
            written,
            shared(ctx)?.identity()?.word(index as usize)?.as_bytes(),
        )
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_request(ctx: *mut Context, p: *const u8, len: usize, now: u64) -> i32 {
    code((|| {
        let c = context(ctx)?;
        match input(p, len) {
            Ok(bytes) => {
                if c.threshold {
                    c.custody.public_request(bytes, now)
                } else {
                    c.owner.request(bytes, now)
                }
            }
            Err(error) => {
                c.cancel();
                Err(error)
            }
        }
    })())
}
/// Dismiss completed output; cancellation and locking still destroy all receipts.
#[no_mangle]
pub unsafe extern "C" fn ns_finish_response(ctx: *mut Context) {
    if let Ok(c) = context(ctx) {
        if c.threshold {
            c.custody.finish_response();
        } else {
            c.owner.finish_response();
        }
    }
}
#[no_mangle]
pub unsafe extern "C" fn ns_tick(ctx: *mut Context, now: u64) -> i32 {
    match context(ctx).and_then(|c| {
        if c.threshold {
            c.custody.tick(now)
        } else {
            c.owner.tick(now)
        }
    }) {
        Ok(expired) => i32::from(expired),
        Err(error) => error as i32,
    }
}
#[no_mangle]
pub unsafe extern "C" fn ns_receive_frame(
    ctx: *mut Context,
    p: *const u8,
    len: usize,
    now: u64,
) -> i32 {
    match (|| {
        let c = context(ctx)?;
        let bytes = input(p, len).inspect_err(|_| c.cancel())?;
        if c.threshold {
            c.custody.receive_frame(bytes, &mut [], now)
        } else {
            c.owner.receive_frame(bytes, now)
        }
    })() {
        Ok(true) => 0,
        Ok(false) => 1,
        // Each owner revokes failed input; keep a validated request's error reply.
        Err(e) => e as i32,
    }
}
#[no_mangle]
pub unsafe extern "C" fn ns_frames_received(ctx: *const Context) -> u32 {
    context_ref(ctx).map_or(0, |c| if c.threshold {c.custody.collector.received()} else {c.owner.collector.received()} as u32)
}
#[no_mangle]
pub unsafe extern "C" fn ns_frames_expected(ctx: *const Context) -> u32 {
    context_ref(ctx).map_or(0, |c| if c.threshold {c.custody.collector.expected()} else {c.owner.collector.expected()} as u32)
}
#[no_mangle]
pub unsafe extern "C" fn ns_review_generation(ctx: *const Context) -> u64 {
    context_ref(ctx).map_or(0, |c| c.generation())
}
#[no_mangle]
pub unsafe extern "C" fn ns_review_count(ctx: *const Context) -> u32 {
    context_ref(ctx).map_or(0, |c| c.fields().len() as u32)
}
#[no_mangle]
pub unsafe extern "C" fn ns_review_confirmation(ctx: *const Context, label: *mut Text) -> i32 {
    code((|| {
        let c = context_ref(ctx)?;
        text(
            label,
            if c.threshold {
                c.custody.confirmation()?
            } else {
                c.owner.confirmation()?
            },
        )
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_review_item(
    ctx: *const Context,
    index: u32,
    label: *mut Text,
    value: *mut Text,
    flags: *mut u32,
) -> i32 {
    code((|| {
        if flags.is_null() {
            return Err(Error::Input);
        }
        let field = context_ref(ctx)?
            .fields()
            .get(index as usize)
            .ok_or(Error::Input)?;
        text(label, &field.label)?;
        text(value, &field.value)?;
        *flags = field.flags;
        Ok(())
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_review_seen(ctx: *mut Context, generation: u64, index: u32) -> i32 {
    code((|| {
        let c = context(ctx)?;
        let generation = c.check_generation(generation)?;
        if c.threshold {
            c.custody.seen(generation, index as usize)
        } else {
            c.owner.seen(generation, index as usize)
        }
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_approve(
    ctx: *mut Context,
    generation: u64,
    partial: bool,
    entropy: *mut u8,
    len: usize,
    now: u64,
) -> i32 {
    let Ok(bytes) = secret(entropy, len) else {
        if let Ok(c) = context(ctx) {
            c.cancel();
        }
        return Error::Input as i32;
    };
    let result = (|| {
        let c = context(ctx)?;
        let generation = c.check_generation(generation).inspect_err(|_| c.cancel())?;
        if c.threshold {
            c.custody.approve(generation, partial, bytes, now)
        } else {
            c.owner.approve(generation, partial, bytes, now)
        }
    })();
    bytes.zeroize();
    code(result)
}
#[no_mangle]
pub unsafe extern "C" fn ns_reject(ctx: *mut Context, generation: u64) -> i32 {
    code((|| {
        let c = context(ctx)?;
        let generation = c.check_generation(generation).inspect_err(|_| c.cancel())?;
        if c.threshold {
            c.custody.reject(generation)
        } else {
            c.owner.reject(generation)
        }
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_response(ctx: *const Context, out: *mut Text) -> i32 {
    code((|| {
        let c = context_ref(ctx)?;
        text(
            out,
            if c.threshold {
                c.custody.outputs().first().ok_or(Error::Stale)?
            } else {
                c.owner.response()?
            },
        )
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_encode_frame(
    p: *const u8,
    len: usize,
    index: u32,
    out: *mut u8,
    cap: usize,
    written: *mut usize,
) -> i32 {
    code((|| {
        let frame = qr::encode(input(p, len)?, index as usize)?;
        copy(out, cap, written, frame.as_bytes())
    })())
}
#[no_mangle]
pub extern "C" fn ns_heap_reserved() -> usize {
    HEAP.reserved_bytes()
}
#[no_mangle]
pub extern "C" fn ns_heap_peak() -> usize {
    HEAP.peak_reserved_bytes()
}
