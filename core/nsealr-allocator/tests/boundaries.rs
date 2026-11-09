use nsealr_allocator::ZeroizingAllocator;
use std::{
    alloc::{GlobalAlloc, Layout, System},
    sync::{
        atomic::{AtomicBool, AtomicUsize, Ordering},
        Barrier,
    },
};

#[derive(Default)]
struct State {
    fail: AtomicBool,
    allocations: AtomicUsize,
    frees: AtomicUsize,
    dirty_bytes_at_free: AtomicUsize,
}
struct Probe<'a>(&'a State);
unsafe impl GlobalAlloc for Probe<'_> {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        self.0.allocations.fetch_add(1, Ordering::SeqCst);
        if self.0.fail.load(Ordering::SeqCst) {
            return std::ptr::null_mut();
        }
        let pointer = System.alloc(layout);
        if !pointer.is_null() {
            pointer.write_bytes(0xa5, layout.size());
        }
        pointer
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        // The adapter must have initialized every byte, including typed padding.
        let bytes = std::slice::from_raw_parts(pointer, layout.size());
        self.0
            .dirty_bytes_at_free
            .fetch_add(bytes.iter().filter(|&&b| b != 0).count(), Ordering::SeqCst);
        self.0.frees.fetch_add(1, Ordering::SeqCst);
        System.dealloc(pointer, layout);
    }
    unsafe fn realloc(&self, _: *mut u8, _: Layout, _: usize) -> *mut u8 {
        panic!("the adapter must not delegate an unwiped realloc");
    }
}

#[test]
fn complete_layout_padding_and_zeroed_allocation() {
    #[repr(C)]
    struct Padded {
        marker: u8,
        secret: u64,
    }
    let state = State::default();
    let allocator = ZeroizingAllocator::new(Probe(&state), 1024, 512);
    unsafe {
        let layout = Layout::new::<Padded>();
        let pointer = allocator.alloc(layout).cast::<Padded>();
        assert!(!pointer.is_null());
        std::ptr::addr_of_mut!((*pointer).marker).write(9);
        std::ptr::addr_of_mut!((*pointer).secret).write(0x1122334455667788);
        allocator.dealloc(pointer.cast(), layout);
        let layout = Layout::from_size_align(257, 512).unwrap();
        let pointer = allocator.alloc_zeroed(layout);
        assert!(!pointer.is_null());
        assert_eq!(pointer as usize % 512, 0);
        assert!(std::slice::from_raw_parts(pointer, layout.size())
            .iter()
            .all(|&b| b == 0));
        pointer.write_bytes(0x63, layout.size());
        allocator.dealloc(pointer, layout);
    }
    assert_eq!(state.frees.load(Ordering::SeqCst), 2);
    assert_eq!(state.dirty_bytes_at_free.load(Ordering::SeqCst), 0);
    assert_eq!(allocator.reserved_bytes(), 0);
}

#[test]
fn growth_and_shrink_copy_prefix_preserve_alignment_and_wipe_old_blocks() {
    let state = State::default();
    let allocator = ZeroizingAllocator::new(Probe(&state), 512, 256);
    unsafe {
        let original = Layout::from_size_align(80, 256).unwrap();
        let pointer = allocator.alloc(original);
        assert!(!pointer.is_null());
        pointer.write_bytes(0x42, 80);
        let grown = allocator.realloc(pointer, original, 96);
        assert!(!grown.is_null());
        assert_eq!(grown as usize % 256, 0);
        assert!(std::slice::from_raw_parts(grown, 80)
            .iter()
            .all(|&b| b == 0x42));
        grown.write_bytes(0x43, 96);
        let shrunk = allocator.realloc(grown, Layout::from_size_align(96, 256).unwrap(), 24);
        assert!(!shrunk.is_null());
        assert_eq!(shrunk as usize % 256, 0);
        assert!(std::slice::from_raw_parts(shrunk, 24)
            .iter()
            .all(|&b| b == 0x43));
        allocator.dealloc(shrunk, Layout::from_size_align(24, 256).unwrap());
    }
    assert_eq!(state.frees.load(Ordering::SeqCst), 3);
    assert_eq!(state.dirty_bytes_at_free.load(Ordering::SeqCst), 0);
    assert_eq!(allocator.peak_reserved_bytes(), 176);
    assert_eq!(allocator.reserved_bytes(), 0);
}

#[test]
fn backend_failure_and_invalid_capacity_preserve_original_bytes_and_budget() {
    let state = State::default();
    let allocator = ZeroizingAllocator::new(Probe(&state), 256, 128);
    unsafe {
        let layout = Layout::from_size_align(64, 64).unwrap();
        let original = allocator.alloc(layout);
        assert!(!original.is_null());
        original.write_bytes(0x71, 64);
        state.fail.store(true, Ordering::SeqCst);
        assert!(allocator.realloc(original, layout, 128).is_null());
        assert_eq!(allocator.reserved_bytes(), 64);
        let calls = state.allocations.load(Ordering::SeqCst);
        for invalid in [0, 129, usize::MAX] {
            assert!(allocator.realloc(original, layout, invalid).is_null());
            assert_eq!(state.allocations.load(Ordering::SeqCst), calls);
            assert_eq!(allocator.reserved_bytes(), 64);
            assert!(std::slice::from_raw_parts(original, 64)
                .iter()
                .all(|&b| b == 0x71));
        }
        assert_eq!(state.frees.load(Ordering::SeqCst), 0);
        allocator.dealloc(original, layout);
    }
    assert_eq!(allocator.reserved_bytes(), 0);
    assert_eq!(allocator.peak_reserved_bytes(), 192);
    assert_eq!(state.dirty_bytes_at_free.load(Ordering::SeqCst), 0);
}

#[test]
fn disabled_single_and_transient_realloc_bounds_fail_without_backend_calls() {
    let state = State::default();
    let disabled = ZeroizingAllocator::new(Probe(&state), 0, 64);
    let single = ZeroizingAllocator::new(Probe(&state), 64, 0);
    let allocator = ZeroizingAllocator::new(Probe(&state), 64, 64);
    unsafe {
        let layout = Layout::from_size_align(64, 8).unwrap();
        assert!(disabled.alloc(layout).is_null());
        assert!(single.alloc(layout).is_null());
        assert_eq!(state.allocations.load(Ordering::SeqCst), 0);
        let original = allocator.alloc(layout);
        assert!(!original.is_null());
        original.write_bytes(0x72, 64);
        assert!(allocator.alloc(layout).is_null());
        // Allocate-copy-wipe-free needs room for both blocks, even on shrink.
        assert!(allocator.realloc(original, layout, 32).is_null());
        assert_eq!(state.allocations.load(Ordering::SeqCst), 1);
        assert!(std::slice::from_raw_parts(original, 64)
            .iter()
            .all(|&b| b == 0x72));
        allocator.dealloc(original, layout);
    }
    assert_eq!(allocator.reserved_bytes(), 0);
    assert_eq!(allocator.peak_reserved_bytes(), 64);
    assert_eq!(state.dirty_bytes_at_free.load(Ordering::SeqCst), 0);
}

#[test]
fn concurrent_requests_cannot_overcommit_atomic_budget() {
    let state = State::default();
    let allocator = ZeroizingAllocator::new(Probe(&state), 256, 64);
    let attempted = Barrier::new(8);
    let successes = AtomicUsize::new(0);
    std::thread::scope(|scope| {
        for _ in 0..8 {
            scope.spawn(|| unsafe {
                let layout = Layout::from_size_align(64, 64).unwrap();
                let pointer = allocator.alloc(layout);
                if !pointer.is_null() {
                    successes.fetch_add(1, Ordering::SeqCst);
                }
                attempted.wait(); // Keep every successful block live through all attempts.
                if !pointer.is_null() {
                    allocator.dealloc(pointer, layout);
                }
            });
        }
    });
    assert_eq!(successes.load(Ordering::SeqCst), 4);
    assert_eq!(state.allocations.load(Ordering::SeqCst), 4);
    assert_eq!(allocator.peak_reserved_bytes(), 256);
    assert_eq!(allocator.reserved_bytes(), 0);
    assert_eq!(state.dirty_bytes_at_free.load(Ordering::SeqCst), 0);
}
