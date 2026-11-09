//! Bounded wipe-before-free allocation. Install this adapter as the global
//! allocator for every allocation in the sensitive domain, including caller
//! containers. It cannot clean storage allocated through another allocator.
//!
//! Current owned Layout bytes are cleared before backend free. This does not
//! clear live buffers, stack/register copies or physical memory remanence.
#![no_std]

use core::{
    alloc::{GlobalAlloc, Layout},
    mem::MaybeUninit,
    ptr, slice,
    sync::atomic::{AtomicUsize, Ordering},
};
use zeroize::Zeroize;

/// A backend allocator with immutable byte limits and wipe-before-free cleanup.
///
/// Reservations include in-flight backend requests and both blocks during
/// realloc. Shrinking also needs room for old+new; refusal preserves the old
/// allocation. Backend allocation failure rolls back the live reservation.
/// Allocation errors return null; the application owns its OOM/fatal policy.
/// This adapter adds no allocation, lock or unwind path of its own.
pub struct ZeroizingAllocator<A> {
    backend: A,
    max_live_bytes: usize,
    max_single_allocation: usize,
    live: AtomicUsize,
    peak: AtomicUsize,
}

impl<A: GlobalAlloc> ZeroizingAllocator<A> {
    /// Creates an allocator with explicit limits. A zero limit disables allocation.
    /// Layout sizes are checked against both limits without arithmetic wrapping.
    pub const fn new(backend: A, max_live_bytes: usize, max_single_allocation: usize) -> Self {
        Self {
            backend,
            max_live_bytes,
            max_single_allocation,
            live: AtomicUsize::new(0),
            peak: AtomicUsize::new(0),
        }
    }

    /// Live reserved bytes, including in-flight requests and realloc overlap.
    pub fn reserved_bytes(&self) -> usize {
        self.live.load(Ordering::Relaxed)
    }

    /// Reservation high-water mark, conservatively including failed backend calls.
    pub fn peak_reserved_bytes(&self) -> usize {
        self.peak.load(Ordering::Relaxed)
    }

    fn reserve(&self, bytes: usize) -> bool {
        if bytes == 0 || bytes > self.max_single_allocation {
            return false;
        }
        let mut live = self.live.load(Ordering::Relaxed);
        loop {
            let Some(next) = live.checked_add(bytes) else {
                return false;
            };
            if next > self.max_live_bytes {
                return false;
            }
            match self
                .live
                .compare_exchange_weak(live, next, Ordering::AcqRel, Ordering::Relaxed)
            {
                Ok(_) => {
                    self.peak.fetch_max(next, Ordering::Relaxed);
                    return true;
                }
                Err(current) => live = current,
            }
        }
    }

    fn release(&self, bytes: usize) {
        // A caller violating GlobalAlloc's layout/ownership contract cannot wrap
        // the budget; the accounting remains fail-closed on underflow.
        let _ = self
            .live
            .fetch_update(Ordering::AcqRel, Ordering::Relaxed, |live| {
                live.checked_sub(bytes)
            });
    }

    unsafe fn allocate(&self, layout: Layout, zeroed: bool) -> *mut u8 {
        if !self.reserve(layout.size()) {
            return ptr::null_mut();
        }
        let allocation = if zeroed {
            self.backend.alloc_zeroed(layout)
        } else {
            self.backend.alloc(layout)
        };
        if allocation.is_null() {
            self.release(layout.size());
        }
        allocation
    }
}

// SAFETY: Valid GlobalAlloc pointer/layout ownership is forwarded to the backend.
// Each successful allocation has one checked reservation, retained through wipe
// and backend free. Realloc never delegates an unwiped old block to the backend.
unsafe impl<A: GlobalAlloc> GlobalAlloc for ZeroizingAllocator<A> {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        self.allocate(layout, false)
    }

    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        self.allocate(layout, true)
    }

    unsafe fn dealloc(&self, allocation: *mut u8, layout: Layout) {
        // MaybeUninit permits clearing uninitialized capacity and typed padding
        // without reading it or creating invalid initialized-byte references.
        slice::from_raw_parts_mut(allocation.cast::<MaybeUninit<u8>>(), layout.size()).zeroize();
        self.backend.dealloc(allocation, layout);
        self.release(layout.size());
    }

    unsafe fn realloc(&self, allocation: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        let Ok(next_layout) = Layout::from_size_align(new_size, layout.align()) else {
            return ptr::null_mut();
        };
        let next = self.alloc(next_layout);
        if next.is_null() {
            return next;
        }
        ptr::copy_nonoverlapping(allocation, next, layout.size().min(new_size));
        self.dealloc(allocation, layout);
        next
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use core::alloc::GlobalAlloc;

    struct Never;
    unsafe impl GlobalAlloc for Never {
        unsafe fn alloc(&self, _: Layout) -> *mut u8 {
            ptr::null_mut()
        }
        unsafe fn dealloc(&self, _: *mut u8, _: Layout) {}
    }

    #[test]
    fn reservation_overflow_cannot_wrap_or_admit_memory() {
        let allocator = ZeroizingAllocator::new(Never, usize::MAX, usize::MAX);
        allocator.live.store(usize::MAX - 7, Ordering::Relaxed);
        assert!(!allocator.reserve(8));
        assert_eq!(allocator.reserved_bytes(), usize::MAX - 7);
        assert_eq!(allocator.peak_reserved_bytes(), 0);
    }
}
