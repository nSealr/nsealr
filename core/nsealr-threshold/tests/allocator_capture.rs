//! Review-only raw allocator evidence. Every key is a public deterministic fixture.
//! OS write copies raw object representation; Rust never interprets typed padding.
use nsealr_allocator::ZeroizingAllocator;
use nsealr_threshold::*;
use std::{
    alloc::{GlobalAlloc, Layout, System},
    os::fd::AsRawFd,
    sync::atomic::{AtomicI32, Ordering},
};
use zeroize::Zeroizing;
static FD: AtomicI32 = AtomicI32::new(-1);
unsafe extern "C" {
    fn write(fd: i32, buf: *const core::ffi::c_void, count: usize) -> isize;
}
struct Capture;
unsafe impl GlobalAlloc for Capture {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        System.alloc(l)
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        let fd = FD.load(Ordering::SeqCst);
        if fd >= 0 {
            let n = (l.size() as u64).to_le_bytes();
            assert_eq!(write(fd, n.as_ptr().cast(), 8), 8);
            assert_eq!(write(fd, p.cast(), l.size()), l.size() as isize);
        }
        System.dealloc(p, l)
    }
    unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
        let q = self.alloc(Layout::from_size_align(n, l.align()).unwrap());
        if !q.is_null() {
            core::ptr::copy_nonoverlapping(p, q, n.min(l.size()));
            self.dealloc(p, l);
        }
        q
    }
}
#[global_allocator]
static ALLOCATOR: ZeroizingAllocator<Capture> =
    ZeroizingAllocator::new(Capture, 1024 * 1024, 64 * 1024);
struct Source;
impl EntropySource for Source {
    fn fill(&mut self, s: &mut [u8; 32]) -> Result<usize, Error> {
        s.fill(7);
        Ok(32)
    }
}
fn hex(b: &[u8]) -> String {
    b.iter().map(|n| format!("{n:02x}")).collect()
}
#[test]
fn capture_dealer_deallocation_storage() {
    let supplied = std::env::var("THRESHOLD_REVIEW_DIRECTORY").ok();
    let directory = supplied.clone().unwrap_or_else(|| {
        format!(
            "{}/../../.tmp/threshold-allocator-capture-{}",
            env!("CARGO_MANIFEST_DIR"),
            std::process::id()
        )
    });
    std::fs::create_dir_all(&directory).unwrap();
    let file =
        std::fs::File::create(format!("{directory}/dealer-deallocation-storage.bin")).unwrap();
    FD.store(file.as_raw_fd(), Ordering::SeqCst);
    let participants = dealer(3, 5, Some(Zeroizing::new([0x4b; 32])), &mut Source).unwrap();
    FD.store(-1, Ordering::SeqCst);
    println!(
        "Participant={} SecretShare={}",
        std::mem::size_of::<Participant>(),
        std::mem::size_of::<frost_secp256k1_tr::keys::SecretShare>()
    );
    let mut patterns = vec![("full-key".to_owned(), hex(&[0x4b; 32]))];
    for (i, p) in participants.iter().enumerate() {
        patterns.push((format!("share-{i}"), hex(&p.backup().unwrap()[36..68])));
    }
    std::fs::write(
        format!("{directory}/dealer-fixture-patterns.json"),
        serde_json::to_vec_pretty(&patterns).unwrap(),
    )
    .unwrap();
    let data = std::fs::read(format!("{directory}/dealer-deallocation-storage.bin")).unwrap();
    let mut storage = data.as_slice();
    let mut count = 0;
    while !storage.is_empty() {
        let (length, remaining) = storage.split_at(8);
        let size = usize::try_from(u64::from_le_bytes(length.try_into().unwrap())).unwrap();
        let (block, remaining) = remaining.split_at(size);
        assert!(
            block.iter().all(|&byte| byte == 0),
            "freed allocation {count}/{size} was not completely cleared"
        );
        storage = remaining;
        count += 1;
    }
    assert!(count > 0);
    println!("captured_freed_blocks={count}; all Layout bytes zero; peak_reserved={} host_limit=1048576 single_limit=65536",ALLOCATOR.peak_reserved_bytes());
    if supplied.is_none() {
        std::fs::remove_dir_all(directory).unwrap();
    }
}
