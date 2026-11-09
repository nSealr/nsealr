# Threshold allocation contract

Threshold currently uses upstream Vec/BTreeMap allocations and caller-owned
containers. Drop implementations alone do not clear bytes left by Rust moves or
reallocation. The independently captured public dealer fixture retained all five
shares in freed Vec/BTreeMap storage and four in a moved-from participant buffer.

Install `nsealr_allocator::ZeroizingAllocator` globally over a qualified backend
before constructing any threshold owner or caller container. Every allocation
that can contain keys, shares, nonces, intermediate polynomial data or serialized
secrets must use this allocation domain. Merely adding a library dependency does
not install the adapter and cannot control an external caller's allocator.

The adapter wipes complete Layout bytes before backend free, and realloc uses
allocate/copy/wipe/free for both growth and shrink. The live reservation limit
includes the temporary old+new blocks. Allocation failure preserves old live
storage; it does not clear it. The application owns fatal/OOM cleanup and must
not resume secret signing state after an uncontrolled allocation error.

The host capture test globally installs an instrumented backend with a 1 MiB
live reservation cap and a 64 KiB single-allocation cap. It captures every byte
of every freed block during the original deterministic `dealer(3,5)` fixture,
including Vec/BTreeMap storage and old realloc blocks. It asserts all captured
bytes are zero and exports the same raw format and five-share pattern manifest
used by the independent review. No allocation size or container is excluded.

To reproduce from the repository root after loading the workspace environment:

```sh
cargo test -p nsealr-allocator --locked --offline
cargo test -p nsealr-allocator --release --locked --offline
cargo build -p nsealr-allocator --release --locked --offline --target riscv32imafc-unknown-none-elf
THRESHOLD_REVIEW_DIRECTORY=<debug-output> cargo test -p nsealr-threshold --test allocator_capture --locked --offline -- --nocapture
THRESHOLD_REVIEW_DIRECTORY=<release-output> cargo test -p nsealr-threshold --test allocator_capture --release --locked --offline -- --nocapture
```

Without an output directory, the test uses and removes a temporary directory
inside the repository. The raw capture asserts full-block zeroization separately
from the existing narrow known-pattern test. Its allocator is host proof only.
Firmware integration must install this adapter; these host tests do not
establish that integration.

P4 integration needs a measured bounded internal-memory backend, complete
allocator coverage, total live/peak budget including realloc overlap, backend
metadata, stack/DMA reservations, and fatal/OOM handling. Host zero-at-free
evidence does not establish live-buffer, stack/register, reset/debug, physical RAM
or power-remanence cleanup. Those remain separate acceptance requirements.
