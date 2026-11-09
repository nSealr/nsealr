//! Host allocator probe, not a device RAM/remanence qualification.
use nsealr_core::event::Event;
use nsealr_threshold::*;
use std::{
    alloc::{GlobalAlloc, Layout, System},
    sync::atomic::{AtomicBool, AtomicIsize, AtomicU64, AtomicUsize, Ordering},
};
use zeroize::Zeroizing;
static CURRENT: AtomicIsize = AtomicIsize::new(0);
static PEAK: AtomicIsize = AtomicIsize::new(0);
static LARGEST: AtomicUsize = AtomicUsize::new(0);
static ACTIVE: AtomicBool = AtomicBool::new(false);
static PATTERN_COUNT: AtomicUsize = AtomicUsize::new(0);
static PATTERNS: [[AtomicU64; 4]; 3] = [const { [const { AtomicU64::new(0) }; 4] }; 3];
fn patterns(values: &[[u8; 32]]) {
    PATTERN_COUNT.store(0, Ordering::SeqCst);
    for (dst, value) in PATTERNS.iter().zip(values) {
        for (word, chunk) in dst.iter().zip(value.chunks_exact(8)) {
            word.store(
                u64::from_le_bytes(chunk.try_into().unwrap()),
                Ordering::SeqCst,
            );
        }
    }
    PATTERN_COUNT.store(values.len(), Ordering::SeqCst);
}
static RESIDUAL: AtomicUsize = AtomicUsize::new(0);
struct Probe;
unsafe impl GlobalAlloc for Probe {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        // Initialize even spare capacity, so the deallocation probe never reads
        // uninitialized backing bytes. This allocator is test instrumentation only.
        let p = System.alloc_zeroed(layout);
        if !p.is_null() {
            let current = CURRENT.fetch_add(layout.size() as isize, Ordering::SeqCst)
                + layout.size() as isize;
            if ACTIVE.load(Ordering::SeqCst) {
                PEAK.fetch_max(current, Ordering::SeqCst);
                LARGEST.fetch_max(layout.size(), Ordering::SeqCst);
            }
        }
        p
    }
    unsafe fn dealloc(&self, p: *mut u8, layout: Layout) {
        let count = PATTERN_COUNT.load(Ordering::SeqCst);
        // Look only in scalar/byte-vector-sized blocks, avoiding typed-node padding.
        if count > 0 && layout.align() <= 8 && layout.size() >= 32 && layout.size() <= 192 {
            for offset in 0..=layout.size() - 32 {
                for pattern in PATTERNS.iter().take(count) {
                    let mut matches = true;
                    for j in 0..32 {
                        let word = pattern[j / 8].load(Ordering::SeqCst);
                        let byte = ((word >> (8 * (j % 8))) & 255) as u8;
                        if p.add(offset + j).read_volatile() != byte {
                            matches = false;
                            break;
                        }
                    }
                    if matches {
                        RESIDUAL.fetch_add(1, Ordering::SeqCst);
                    }
                }
            }
        }
        CURRENT.fetch_sub(layout.size() as isize, Ordering::SeqCst);
        System.dealloc(p, layout)
    }
    unsafe fn realloc(&self, p: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        let next = self.alloc(Layout::from_size_align(new_size, layout.align()).unwrap());
        if !next.is_null() {
            std::ptr::copy_nonoverlapping(p, next, layout.size().min(new_size));
            self.dealloc(p, layout);
        }
        next
    }
}
#[global_allocator]
static ALLOCATOR: Probe = Probe;
fn measure<T>(name: &str, run: impl FnOnce() -> T) -> T {
    let baseline = CURRENT.load(Ordering::SeqCst);
    PEAK.store(baseline, Ordering::SeqCst);
    LARGEST.store(0, Ordering::SeqCst);
    ACTIVE.store(true, Ordering::SeqCst);
    let result = run();
    ACTIVE.store(false, Ordering::SeqCst);
    let peak = PEAK.load(Ordering::SeqCst) - baseline;
    let largest = LARGEST.load(Ordering::SeqCst);
    println!("{name}: peak_extra={peak} largest_allocation={largest}");
    assert!(
        peak < 32768,
        "phase exceeded measured 32KiB host extra-heap budget"
    );
    assert!(largest < 16384);
    result
}
struct Source(u8);
impl EntropySource for Source {
    fn fill(&mut self, s: &mut [u8; 32]) -> Result<usize, Error> {
        s.fill(self.0);
        self.0 += 1;
        Ok(32)
    }
}
struct Local;
impl ReviewAuthority for Local {
    fn now_ms(&mut self) -> Option<u64> {
        Some(1)
    }
    fn review(&mut self, i: ReviewIntent<'_>) -> Result<ReviewApproval, Error> {
        Ok(i.approve())
    }
    fn check_live(&mut self, _: &ReviewBinding) -> Result<(), Error> {
        Ok(())
    }
    fn admit_round(&mut self, _: &ReviewBinding, _: &SigningRound) -> Result<(), Error> {
        Ok(())
    }
}
fn event(pubkey: &[u8; 32]) -> Event {
    Event::parse(&serde_json::to_vec(&serde_json::json!({"pubkey":hex(pubkey),"created_at":1700000000,"kind":1,"tags":[],"content":"allocation test"})).unwrap(),pubkey).unwrap()
}
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

#[test]
fn bounded_heap_and_secret_vector_cleanup() {
    patterns(&[[0x4b; 32]]);
    let mut participants = measure("dealer-5-of-5", || {
        dealer(5, 5, Some(Zeroizing::new([0x4b; 32])), &mut Source(10)).unwrap()
    });
    patterns(&[]);
    assert_eq!(
        RESIDUAL.load(Ordering::SeqCst),
        0,
        "raw full-key coefficient survived deallocation"
    );
    let group = participants[0].group().clone();
    let ids: Vec<_> = participants
        .iter()
        .take(5)
        .map(Participant::identifier)
        .collect();
    let backup = measure("backup-5", || participants[0].backup().unwrap());
    let secret: [u8; 32] = backup[36..68].try_into().unwrap();
    let mut reversed = secret;
    reversed.reverse();
    patterns(&[[0x4b; 32], secret, reversed]);
    let restored = measure("restore-5", || {
        Participant::restore(&backup, group.identity(), &ids[0]).unwrap()
    });
    drop(backup);
    drop(restored);
    let mut signer = Signer::new();
    signer.select(participants.remove(0));
    let intent = RoundIntent::for_event(&group, &event(group.public_key()), [1; 32], &ids).unwrap();
    let first = measure("commit-5-of-5", || {
        signer
            .begin(
                event(group.public_key()),
                intent.clone(),
                100,
                &mut Local,
                &mut Source(30),
            )
            .unwrap()
    });
    let mut others: Vec<_> = participants
        .into_iter()
        .take(4)
        .map(|p| {
            let mut s = Signer::new();
            s.select(p);
            s
        })
        .collect();
    let mut commitments = vec![first];
    for (index, s) in others.iter_mut().enumerate() {
        commitments.push(
            s.begin(
                event(group.public_key()),
                intent.clone(),
                100,
                &mut Local,
                &mut Source(40 + index as u8),
            )
            .unwrap(),
        );
    }
    let round = measure("round-5-of-5", || {
        SigningRound::new(&intent, &commitments).unwrap()
    });
    let mut shares = vec![measure("sign-5-of-5", || {
        signer.sign(&round, &mut Local).unwrap()
    })];
    shares.extend(
        others
            .iter_mut()
            .map(|s| s.sign(&round, &mut Local).unwrap()),
    );
    measure("aggregate-5-of-5", || {
        round.aggregate(&group, &shares).unwrap()
    });
    signer.lock();
    drop(signer);
    drop(others);
    patterns(&[]);
    assert_eq!(
        RESIDUAL.load(Ordering::SeqCst),
        0,
        "known secret share/preimage survived vector deallocation"
    );
    println!(
        "known_secret_patterns_at_deallocation=0; Signer stack bytes={}",
        std::mem::size_of::<Signer>()
    );
    let ids: Vec<_> = (1..=5)
        .map(|n| {
            let mut id = [0; 32];
            id[31] = n;
            id
        })
        .collect();
    let mut one = Vec::new();
    let mut broadcasts = Vec::new();
    for (index, participant) in ids.iter().enumerate() {
        let start = || {
            dkg::RoundOne::start(
                5,
                &ids,
                *participant,
                [3; 32],
                &mut Source(70 + index as u8),
            )
            .unwrap()
        };
        let (owner, broadcast) = if index == 0 {
            measure("dkg-part1-5-of-5", start)
        } else {
            start()
        };
        one.push(owner);
        broadcasts.push(broadcast);
    }
    let mut two = Vec::new();
    let mut deliveries = Vec::new();
    for (index, (owner, participant)) in one.into_iter().zip(&ids).enumerate() {
        let incoming: Vec<_> = broadcasts
            .iter()
            .filter(|b| &b.sender != participant)
            .map(|b| dkg::Broadcast {
                ceremony: b.ceremony,
                sender: b.sender,
                package: b.package.clone(),
            })
            .collect();
        let advance = || owner.advance(&incoming).unwrap();
        let (owner, out) = if index == 0 {
            measure("dkg-part2-5-of-5", advance)
        } else {
            advance()
        };
        two.push(owner);
        deliveries.extend(out);
    }
    let incoming: Vec<_> = deliveries
        .into_iter()
        .filter(|d| d.recipient == ids[0])
        .collect();
    measure("dkg-part3-5-of-5", || {
        two.remove(0).finish(&incoming).unwrap()
    });
}
