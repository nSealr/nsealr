# Bounded wipe-before-free allocation

`ZeroizingAllocator<A: GlobalAlloc>` is a no_std adapter with immutable maximum
live reserved bytes and maximum single allocation size. It uses the existing
zeroize dependency and allocates no bookkeeping storage.

Every valid deallocation clears the complete `Layout::size()` byte range before
calling the backend. The wipe uses `MaybeUninit<u8>` storage, so it includes spare
capacity and typed padding without reading uninitialized bytes. It does not
claim inaccessible backend size-class padding beyond the caller's Layout.

Realloc allocates a new block with the original alignment, copies
`min(old_size, new_size)`, then wipes and frees the complete old block. This also
applies to shrink and same-size requests. Both blocks count toward the live
budget until the old backend free completes. A request can therefore fail even
when its final size alone fits. Invalid size, exceeded limits and backend failure
return null and leave the old allocation unchanged.

Checked atomics serialize byte reservations. `reserved_bytes()` includes backend
requests in flight. `peak_reserved_bytes()` is a conservative reservation
high-water mark, including failed backend calls. Both stay within the configured
live limit; a zero limit disables allocation. These counters exclude backend
metadata and do not measure physical RAM or stack usage.

Install the adapter globally for **all** sensitive allocation, including caller
Vec/BTreeMap storage. A library cannot select the allocator of external caller
containers. The backend must satisfy GlobalAlloc's safety, alignment and unwind
contracts and remain usable throughout every allocation's lifetime. For example,
a host test can install:

```rust,ignore
#[global_allocator]
static HEAP: ZeroizingAllocator<System> =
    ZeroizingAllocator::new(System, 1024 * 1024, 64 * 1024);
```

Those host limits are not P4 limits. Firmware still needs a bounded internal-RAM
backend, reserved space for non-heap runtime state, a fatal/OOM policy and target
measurements. Clearing freed heap does not clear live allocations, stack/register
copies, other allocators or memory remanence after reset/power loss.

Boundary tests cover failed allocation, invalid realloc, transient/single/live
limits, preserved alignment, growth/shrink, full Layout cleanup and concurrent
reservations. The threshold raw-storage capture test exercises actual moved-from
Vec and BTreeMap allocations under this globally installed adapter.
