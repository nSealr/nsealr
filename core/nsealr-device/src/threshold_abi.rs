use super::*;

#[no_mangle]
pub unsafe extern "C" fn ns_threshold_start(ctx: *mut Context, entropy: *mut u8, now: u64) -> i32 {
    let Ok(bytes) = secret(entropy, 32) else {
        ns_cancel(ctx);
        return Error::Input as i32;
    };
    let result = (|| {
        let c = context(ctx)?;
        c.owner.lock();
        c.threshold = true;
        c.custody.start(bytes, now)
    })();
    bytes.zeroize();
    code(result)
}
#[no_mangle]
pub unsafe extern "C" fn ns_threshold_receive(
    ctx: *mut Context,
    p: *const u8,
    len: usize,
    entropy: *mut u8,
    now: u64,
) -> i32 {
    receive(ctx, p, len, entropy, now, false)
}
#[no_mangle]
pub unsafe extern "C" fn ns_threshold_receive_frame(
    ctx: *mut Context,
    p: *const u8,
    len: usize,
    entropy: *mut u8,
    now: u64,
) -> i32 {
    receive(ctx, p, len, entropy, now, true)
}
unsafe fn receive(
    ctx: *mut Context,
    p: *const u8,
    len: usize,
    entropy: *mut u8,
    now: u64,
    frame: bool,
) -> i32 {
    let Ok(bytes) = secret(entropy, 32) else {
        ns_cancel(ctx);
        return Error::Input as i32;
    };
    let result = (|| {
        let c = context(ctx)?;
        if !c.threshold {
            return Err(Error::Unsupported);
        }
        let input = input(p, len)?;
        if frame {
            c.custody.receive_frame(input, bytes, now)
        } else {
            c.custody.receive(input, bytes, now).map(|()| true)
        }
    })();
    bytes.zeroize();
    match result {
        Ok(true) => 0,
        Ok(false) => 1,
        Err(e) => {
            ns_cancel(ctx);
            e as i32
        }
    }
}
#[no_mangle]
pub unsafe extern "C" fn ns_threshold_state(ctx: *const Context) -> u32 {
    context_ref(ctx).map_or(0, |c| if c.threshold { c.custody.state() } else { 0 })
}
#[no_mangle]
pub unsafe extern "C" fn ns_threshold_progress(ctx: *const Context) -> u32 {
    context_ref(ctx).map_or(0, |c| if c.threshold { c.custody.progress() } else { 0 })
}
#[no_mangle]
pub unsafe extern "C" fn ns_threshold_output_count(ctx: *const Context) -> u32 {
    context_ref(ctx).map_or(0, |c| {
        if c.threshold {
            c.custody.outputs().len() as u32
        } else {
            0
        }
    })
}
#[no_mangle]
pub unsafe extern "C" fn ns_threshold_output(
    ctx: *const Context,
    index: u32,
    out: *mut Text,
) -> i32 {
    code((|| {
        let c = context_ref(ctx)?;
        if !c.threshold {
            return Err(Error::Unsupported);
        }
        text(
            out,
            c.custody
                .outputs()
                .get(index as usize)
                .ok_or(Error::Input)?,
        )
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_threshold_backup(
    ctx: *const Context,
    out: *mut u8,
    cap: usize,
    written: *mut usize,
) -> i32 {
    code((|| {
        if !written.is_null() {
            *written = 0;
        }
        secret(out, cap)?.zeroize();
        let c = context_ref(ctx)?;
        if !c.threshold {
            return Err(Error::Unsupported);
        }
        let backup = c.custody.backup()?;
        copy(out, cap, written, backup.as_bytes())
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_threshold_import(
    ctx: *mut Context,
    p: *mut u8,
    len: usize,
    now: u64,
) -> i32 {
    let Ok(bytes) = secret(p, len) else {
        ns_lock(ctx);
        return Error::Input as i32;
    };
    let result = (|| {
        let c = context(ctx)?;
        c.owner.lock();
        c.threshold = true;
        c.custody.import(bytes, now)
    })();
    bytes.zeroize();
    code(result)
}
#[no_mangle]
pub unsafe extern "C" fn ns_threshold_import_frame(
    ctx: *mut Context,
    p: *mut u8,
    len: usize,
    now: u64,
) -> i32 {
    backup_frame(ctx, p, len, now, false)
}
#[no_mangle]
pub unsafe extern "C" fn ns_threshold_check_backup_frame(
    ctx: *mut Context,
    p: *mut u8,
    len: usize,
    now: u64,
) -> i32 {
    backup_frame(ctx, p, len, now, true)
}
unsafe fn backup_frame(ctx: *mut Context, p: *mut u8, len: usize, now: u64, check: bool) -> i32 {
    let Ok(bytes) = secret(p, len) else {
        ns_cancel(ctx);
        return Error::Input as i32;
    };
    let result = (|| {
        let c = context(ctx)?;
        if check && !c.threshold {
            return Err(Error::Unsupported);
        }
        if !check {
            c.owner.lock();
            c.threshold = true;
        }
        c.custody.backup_frame(bytes, check, now)
    })();
    bytes.zeroize();
    match result {
        Ok(true) => 0,
        Ok(false) => 1,
        Err(error) => {
            ns_cancel(ctx);
            error as i32
        }
    }
}
#[no_mangle]
pub unsafe extern "C" fn ns_threshold_record(
    ctx: *const Context,
    out: *mut u8,
    capacity: usize,
    written: *mut usize,
) -> i32 {
    code((|| {
        copy(out, capacity, written, &[])?;
        let c = context_ref(ctx)?;
        if !c.threshold {
            return Err(Error::Unsupported);
        }
        copy(out, capacity, written, c.custody.record()?.as_bytes())
    })())
}
#[no_mangle]
pub unsafe extern "C" fn ns_threshold_info(
    ctx: *const Context,
    out: *mut u8,
    member: *mut u32,
) -> i32 {
    code((|| {
        secret(out, 64)?.zeroize();
        if member.is_null() {
            return Err(Error::Input);
        }
        *member = 0;
        let c = context_ref(ctx)?;
        if !c.threshold {
            return Err(Error::Unsupported);
        }
        let group = nsealr_core::json::hex_string(c.custody.group()?);
        let mut written = 0;
        copy(out, 64, &mut written, group.as_bytes())?;
        *member = c.custody.member()?;
        Ok(())
    })())
}
